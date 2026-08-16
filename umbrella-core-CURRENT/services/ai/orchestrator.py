"""
services/ai/orchestrator.py - The single entry point every AI-facing
capability calls into. Ties together the constitution (system prompt),
the model router (provider selection + failover), and - for task types
configured to require it - dual review: two independent models must
produce answers a simple similarity check agrees are consistent before the
result is treated as confident, or the call is escalated for staff review.

This is not a second place permissions/audit happen - an orchestrator call
is always made from inside a capability handler, which already went
through the Capability Registry's own permission check and audit write
(registry/registry.py). What this module owns is AI-specific: which
model(s) answered, whether they agreed, and the resulting confidence -
recorded to AIDecisionLog for every call, successful or escalated.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models.ai import AIDecisionLog
from services.ai.constitution_service import ConstitutionService
from services.ai.model_router import ModelRouter, NoAvailableModelError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OrchestrationResult:
    text: str
    confidence: float
    escalated: bool
    primary_provider: str
    primary_model: str
    secondary_provider: str | None
    secondary_model: str | None
    dual_review_agreement: bool | None
    decision_log_id: str


def _similarity(a: str, b: str) -> float:
    """A cheap, dependency-free agreement heuristic between two model
    outputs - good enough to catch "the two models gave substantively
    different answers" without needing a third model call just to compare
    the first two. Not a semantic-equivalence judgment; a low score means
    "these look different enough to escalate," not "one is wrong.\""""
    return SequenceMatcher(None, a, b).ratio()


class Orchestrator:
    @staticmethod
    async def run(
        db: AsyncSession,
        task_type: str,
        task_prompt: str,
        requested_by: str | None = None,
        require_dual_review: bool | None = None,
        agreement_threshold: float = 0.55,
        agreement_fn: Callable[[str, str], float] | None = None,
    ) -> OrchestrationResult:
        """
        require_dual_review=None defers to the global
        settings.dual_review_enabled default; passing an explicit True/False
        lets a specific capability opt in/out of the platform default when
        its own risk profile warrants it (e.g. a low-stakes summarization
        task might reasonably skip dual review even with the platform
        default on).

        agreement_fn overrides the default raw-text SequenceMatcher
        comparison (_similarity above) with a caller-supplied one, for task
        types whose output has real structure worth comparing directly
        rather than as opaque text - e.g. comparing two responses' JSON
        `recommended_action` field, where differently-worded surrounding
        text would otherwise score a low text-similarity ratio despite the
        models having reached the same actual conclusion. Must return a
        float in [0, 1], compared against agreement_threshold exactly like
        _similarity's return value. Defaults to None (the existing
        text-similarity behavior) - every existing caller is unaffected.
        """
        settings = get_settings()
        dual_review = settings.dual_review_enabled if require_dual_review is None else require_dual_review
        compare = agreement_fn or _similarity

        system_prompt = await ConstitutionService.build_system_prompt(db, task_prompt)

        primary = await ModelRouter.generate(db, task_type, system_prompt, task_prompt)

        secondary = None
        agreement: bool | None = None
        confidence = 1.0

        if dual_review:
            try:
                secondary = await ModelRouter.generate(
                    db, task_type, system_prompt, task_prompt, exclude_providers={primary.provider}
                )
                score = compare(primary.result.text, secondary.result.text)
                agreement = score >= agreement_threshold
                confidence = score
            except NoAvailableModelError:
                # Only one provider is actually available right now - dual
                # review can't happen, so this call proceeds single-reviewed
                # but at reduced confidence, which the escalation check
                # below will likely catch rather than silently treating a
                # single-model answer as fully confident.
                confidence = 0.5
                logger.info(
                    "dual review requested for task_type=%s but only one provider (%s) "
                    "is currently available - proceeding single-reviewed at reduced confidence",
                    task_type,
                    primary.provider,
                )

        escalated = confidence < settings.confidence_escalation_threshold or agreement is False

        log = AIDecisionLog(
            task_type=task_type,
            requested_by=requested_by,
            input_summary=task_prompt[:2000],
            output_summary=primary.result.text[:2000],
            confidence=confidence,
            primary_provider=primary.provider,
            primary_model=primary.model_name,
            secondary_provider=secondary.provider if secondary else None,
            secondary_model=secondary.model_name if secondary else None,
            dual_review_agreement=agreement,
            escalated=escalated,
        )
        db.add(log)
        await db.flush()

        if escalated:
            logger.warning(
                "AI decision escalated for staff review (task_type=%s, confidence=%.2f, "
                "dual_review_agreement=%s, decision_log_id=%s)",
                task_type,
                confidence,
                agreement,
                log.id,
            )

        # TODO(action-guard-integration): `run()` currently only generates
        # and dual-reviews text - it still never invokes a capability
        # itself, so there is nothing here yet for services.ai.action_guard
        # to guard directly. registry/adapters/ai.py:call_tool() now exists
        # as the actual, tested integration point (it validates params,
        # runs action_guard.require_autonomous_allowed(), then
        # registry.call() - the same path every other adapter uses) for
        # whichever future phase adds "the AI layer proposes/executes a
        # specific capability call based on this result." That future code
        # must call call_tool() rather than registry.call() directly - do
        # not let a future capability-execution feature bypass it.

        return OrchestrationResult(
            text=primary.result.text,
            confidence=confidence,
            escalated=escalated,
            primary_provider=primary.provider,
            primary_model=primary.model_name,
            secondary_provider=secondary.provider if secondary else None,
            secondary_model=secondary.model_name if secondary else None,
            dual_review_agreement=agreement,
            decision_log_id=log.id,
        )
