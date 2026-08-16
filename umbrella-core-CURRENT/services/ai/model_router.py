"""
services/ai/model_router.py - Selects a (provider, model) candidate for a
task type, in priority order, skipping unhealthy candidates and recording
health on every real call. This is what turns "three providers exist" into
"a temporary OpenRouter outage doesn't take down AI features that could
just as well run on Anthropic."

Health is learned from actual usage, not a separate background health-check
loop: every call to `generate()` either records a success (resetting
consecutive_failures) or a failure (incrementing it, and marking the
candidate unhealthy once it crosses the configured threshold). An unhealthy
candidate isn't skipped forever - after `ai_model_health_cooldown_seconds`
has passed since its last failure, it's given another chance (a "half-open"
retry), so a transient outage self-heals without an operator's intervention.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import case, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models.ai import AIModelConfig
from services.ai.base import GenerationResult, ProviderError, truncate_for_error
from services.ai.provider_factory import ProviderFactory

logger = logging.getLogger(__name__)


class NoAvailableModelError(Exception):
    """Raised when every candidate for a task_type failed, or none exist."""


@dataclass(frozen=True)
class RoutedGeneration:
    result: GenerationResult
    provider: str
    model_name: str


class ModelRouter:
    @staticmethod
    async def _candidates(db: AsyncSession, task_type: str) -> list[AIModelConfig]:
        result = await db.execute(
            select(AIModelConfig)
            .where(AIModelConfig.task_type == task_type, AIModelConfig.enabled.is_(True))
            .order_by(AIModelConfig.priority.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    def _is_eligible(config: AIModelConfig, now: datetime) -> bool:
        """A candidate is eligible if it's currently healthy, OR it's
        unhealthy but its cooldown window has elapsed (half-open retry)."""
        if config.is_healthy:
            return True
        if config.last_failure_at is None:
            return True
        settings = get_settings()
        last_failure = config.last_failure_at
        if last_failure.tzinfo is None:
            last_failure = last_failure.replace(tzinfo=timezone.utc)
        elapsed = (now - last_failure).total_seconds()
        return elapsed >= settings.ai_model_health_cooldown_seconds

    @staticmethod
    async def _record_success(db: AsyncSession, config: AIModelConfig, latency_ms: int) -> None:
        config.is_healthy = True
        config.consecutive_failures = 0
        config.last_success_at = datetime.now(timezone.utc)
        config.last_latency_ms = latency_ms
        await db.flush()

    @staticmethod
    async def _record_failure(db: AsyncSession, config: AIModelConfig) -> None:
        """
        Increment consecutive_failures and, if it crosses the configured
        threshold, mark the candidate unhealthy - as a single atomic SQL
        UPDATE rather than a Python read-modify-write.

        Why this matters: config was SELECTed once in _candidates(), then
        an external API call (provider.generate(), potentially seconds
        long) happened before we get here. Two concurrent requests routed
        to the same candidate can both hold that same stale in-memory
        consecutive_failures value. `config.consecutive_failures += 1;
        await db.flush()` would let the second writer's flush overwrite
        the first's increment - a lost update that delays (or in the worst
        case, indefinitely defers) the unhealthy threshold from ever being
        reached under real concurrent load.

        Doing the increment in the UPDATE statement itself
        (`consecutive_failures + 1`, evaluated by the database, not by
        Python) closes that race: the database serializes the two
        row-level writes, so neither increment is lost, without either
        request needing to block waiting for the other.

        Deliberately NOT using `SELECT ... FOR UPDATE` at read time
        instead: that would hold a row lock for the entire duration of the
        upstream provider.generate() call (this can be many seconds for a
        slow LLM response), serializing every concurrent request routed to
        the same candidate behind that lock. For a hot task_type under
        real load, that would hurt throughput far more than the rare lost
        increment this fixes. The atomic UPDATE gets the same correctness
        guarantee for the one value that actually needs it, with no lock
        held across the slow network call.
        """
        settings = get_settings()
        now = datetime.now(timezone.utc)
        threshold = settings.ai_model_unhealthy_after_failures
        new_failure_count = AIModelConfig.consecutive_failures + 1
        # Captured before the UPDATE below: a Core-style update() causes
        # SQLAlchemy to expire attributes on any matching ORM instance
        # already in the session's identity map (not just the ones in
        # .values() - the case() expression for is_healthy can't be
        # evaluated in-Python by the ORM's synchronize_session logic, so
        # it falls back to expiring the whole row). Re-reading an expired
        # attribute afterward would trigger an implicit, synchronous
        # lazy-load that an async session can't perform outside an
        # `await` (raises MissingGreenlet). None of these four change
        # during this call in a way that requires re-reading them from
        # the row after the update, so capturing them up front avoids
        # that entirely rather than working around it after the fact.
        task_type = config.task_type
        provider = config.provider
        model_name = config.model_name
        was_healthy_before = config.is_healthy

        stmt = (
            update(AIModelConfig)
            .where(AIModelConfig.id == config.id)
            .values(
                consecutive_failures=new_failure_count,
                last_failure_at=now,
                # Only flips healthy->unhealthy on crossing the threshold;
                # otherwise leaves is_healthy exactly as the row currently
                # has it (so an already-unhealthy candidate isn't
                # accidentally revived, and a healthy one below threshold
                # is untouched) - evaluated in SQL against the *new*,
                # just-incremented count, not the stale in-memory one.
                is_healthy=case(
                    (new_failure_count >= threshold, False),
                    else_=AIModelConfig.is_healthy,
                ),
            )
            .returning(AIModelConfig.consecutive_failures, AIModelConfig.is_healthy)
        )
        result = await db.execute(stmt)
        row = result.one()

        # Keep the in-memory object the caller already holds consistent
        # with what was actually persisted. A Core-style UPDATE like the
        # one above does not automatically refresh ORM instances already
        # loaded into the session's identity map, so without this the
        # caller's `config` would silently show stale values after this
        # call returns.
        config.consecutive_failures = row.consecutive_failures
        config.last_failure_at = now
        config.is_healthy = row.is_healthy

        if was_healthy_before and not row.is_healthy:
            # Only fires on the actual healthy->unhealthy transition, not
            # on every subsequent failure while already unhealthy - the
            # signal an operator needs is "this just went down," not one
            # log line per failed retry during an ongoing outage.
            logger.warning(
                "AI model %s/%s marked unhealthy after %d consecutive failures "
                "(task_type=%s, cooldown=%ds)",
                provider,
                model_name,
                row.consecutive_failures,
                task_type,
                settings.ai_model_health_cooldown_seconds,
            )

    @staticmethod
    async def generate(
        db: AsyncSession,
        task_type: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        exclude_providers: set[str] | None = None,
    ) -> RoutedGeneration:
        """
        Try each registered candidate for task_type, in priority order,
        skipping ones whose provider is disabled/unkeyed or whose model is
        currently unhealthy (and not yet past cooldown). Returns the first
        success. `exclude_providers` lets the dual-review orchestrator ask
        for "a second opinion from a different provider than the first
        one," without needing its own separate candidate-selection logic.
        """
        exclude_providers = exclude_providers or set()
        now = datetime.now(timezone.utc)
        candidates = await ModelRouter._candidates(db, task_type)

        attempted: list[str] = []
        for config in candidates:
            if config.provider in exclude_providers:
                continue
            if not ModelRouter._is_eligible(config, now):
                continue
            if not await ProviderFactory.is_enabled(db, config.provider):
                continue
            if not await ProviderFactory.has_key_configured(db, config.provider):
                continue

            attempted.append(f"{config.provider}/{config.model_name}")
            try:
                provider = await ProviderFactory.build(db, config.provider)
                result = await provider.generate(
                    config.model_name, system_prompt, user_prompt, max_tokens, temperature
                )
            except ProviderError as exc:
                logger.info(
                    "AI provider %s/%s failed for task_type=%s, trying next candidate: %s",
                    config.provider,
                    config.model_name,
                    task_type,
                    truncate_for_error(str(exc)),
                )
                await ModelRouter._record_failure(db, config)
                continue

            await ModelRouter._record_success(db, config, result.latency_ms)
            return RoutedGeneration(result=result, provider=config.provider, model_name=config.model_name)

        logger.error(
            "no available AI model for task_type=%s (tried: %s)",
            task_type,
            ", ".join(attempted) if attempted else "no eligible candidates configured",
        )
        raise NoAvailableModelError(
            f"no available model for task_type {task_type!r}"
            + (f" (tried: {', '.join(attempted)})" if attempted else " (no eligible candidates configured)")
        )
