"""
models/ai.py — Phase 5's AI operating-system layer: model registry with
health tracking, the constitution (tiered behavioral rules), and the
decision log every AI-generated output is recorded to.

Provider credentials and per-provider enabled/disabled toggles live in the
existing DB-backed Setting model (category="ai"), not here — see
services/ai/provider_factory.py. What lives here is the *routing* layer on
top of those credentials: which (provider, model) pairs are candidates for
which task types, and each candidate's independently-tracked health.
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class ConstitutionTier(enum.IntEnum):
    """Lower value = higher priority (wins on conflict). PLATFORM_SAFETY is
    the floor every other tier is layered on top of — see
    services/ai/action_guard.py for the parts of it that are enforced in
    code, not just as a prompt instruction the model could ignore."""

    PLATFORM_SAFETY = 0
    CORE_PLATFORM = 1
    SERVER = 2
    ROLE = 3
    TASK = 4


class AIModelConfig(Base):
    """One candidate (provider, model) pair the router may select for a
    task, with health tracked independently per row — a model's failures
    on one task type don't affect its candidacy for another."""

    __tablename__ = "ai_model_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider: Mapped[str] = mapped_column(String(32), nullable=False)  # "openrouter" | "anthropic" | "gemini"
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    # Health tracking — updated by ModelRouter on every real call, not a
    # separate background health-check process; the router learns a
    # model's health from actually using it.
    is_healthy: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<AIModelConfig {self.provider}/{self.model_name} task={self.task_type!r}>"


class ConstitutionRule(Base):
    """One rule in the tiered constitution. Seed rules
    (`is_seed_rule=True`) can be disabled here for prompt-visibility
    purposes, but the platform-safety invariants they describe are also
    independently, unconditionally enforced in code
    (services/ai/action_guard.py) — disabling a DB row never makes a
    forbidden action possible, it only removes the prompt-level
    instruction, which was never the only line of defense."""

    __tablename__ = "constitution_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tier: Mapped[ConstitutionTier] = mapped_column(Enum(ConstitutionTier), nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_seed_rule: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<ConstitutionRule tier={self.tier.name} title={self.title!r}>"


class AIDecisionLog(Base):
    """Every AI-generated output that went through the orchestrator —
    single- or dual-reviewed, confidence, agreement, and whether it was
    escalated. This is what Phase 5's novel capabilities (AI-authored
    postmortems, the security-audit job) and any future dashboard AI
    activity view read from."""

    __tablename__ = "ai_decision_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    requested_by: Mapped[str | None] = mapped_column(String(64), nullable=True)  # CallContext.actor_id

    input_summary: Mapped[str] = mapped_column(Text, nullable=False)
    output_summary: Mapped[str] = mapped_column(Text, nullable=False)

    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retrieval_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    primary_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    primary_model: Mapped[str] = mapped_column(String(128), nullable=False)
    secondary_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    secondary_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    dual_review_agreement: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    escalated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    # Python-side default, not server_default=func.now() — same
    # microsecond-precision-ordering reasoning as Backup.created_at
    # (ADR-0005); decision logs can plausibly be written in rapid
    # succession by the orchestrator too.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<AIDecisionLog task={self.task_type!r} confidence={self.confidence} escalated={self.escalated}>"
