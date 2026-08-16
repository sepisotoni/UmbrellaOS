"""
models/webhook.py — WebhookSubscription: an admin-registered external HTTP
endpoint that should receive a signed POST whenever a matching topic is
dispatched on the event bus (Phase 7 item 2, see
docs/design/public-rest-api-and-webhooks.md, Decision 4).

One row = one (topic, url) pairing. A subscriber wanting multiple topics
creates multiple rows (see the design doc's "deliberately out of scope"
section for why wildcard topics aren't supported here).

`secret` is generated once at creation, shown to the caller exactly once
(same pattern as ApiKey's plaintext key — see services/api_key_service.py),
and used to HMAC-SHA256-sign every delivered payload so a receiver can
verify a request genuinely came from this UmbrellaOS instance. Unlike
ApiKey, the secret itself IS stored (not just a hash) — it has to be, since
it must be usable to compute a fresh HMAC on every delivery, not just
verified against a one-time presented value the way a login credential is.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.engine import Base
from models.user import User  # noqa: F401 - resolves the "User" forward reference below


class WebhookSubscription(Base):
    __tablename__ = "webhook_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Exact topic string this subscription delivers for — e.g.
    # "staff_escalation.created". Indexed since the delivery handler looks
    # up active subscriptions by topic on every dispatched event.
    topic: Mapped[str] = mapped_column(String(150), nullable=False, index=True)

    url: Mapped[str] = mapped_column(String(2048), nullable=False)

    # Used to HMAC-sign delivered payloads. See module docstring for why
    # this is stored in recoverable form, unlike ApiKey.key_hash.
    secret: Mapped[str] = mapped_column(String(128), nullable=False)

    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    creator: Mapped["User | None"] = relationship("User")

    def __repr__(self) -> str:
        return f"<WebhookSubscription id={self.id!r} topic={self.topic!r} url={self.url!r}>"
