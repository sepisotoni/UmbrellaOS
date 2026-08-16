"""
capabilities/webhooks.py — CRUD for WebhookSubscription rows (Phase 7 item
2). Declared as capabilities, not a bespoke router, so this is
automatically reachable over REST/CLI/AI the moment it's registered — see
docs/design/public-rest-api-and-webhooks.md, Decision 4, and
docs/adr/0001-capability-registry.md for why that's the rule for every
capability in this codebase, not just this one.

Actual delivery (the part that talks to the subscriber's URL) lives in
services/webhooks/service.py::WebhookDeliveryService and is invoked by the
global event subscriber in services/events/subscribers.py, not from here —
these capabilities only manage the subscription rows.
"""
from __future__ import annotations

from pydantic import BaseModel

from registry.context import CallContext
from registry.decorator import capability
from services.webhooks.service import WebhookService
from models import User
from sqlalchemy import select


async def _resolve_created_by(ctx: CallContext) -> str | None:
    """Same actor-resolution pattern as capabilities/identity.py's
    create_api_key: only staff (dashboard-authenticated) actors resolve to
    a real user id; an API-key-authenticated caller creating a webhook
    subscription for itself has no dashboard user to attribute it to."""
    if ctx.actor_type == "staff":
        result = await ctx.db.execute(select(User).where(User.discord_id == ctx.actor_id))
        user = result.scalar_one_or_none()
        return user.id if user else None
    return None


class WebhookSubscriptionResult(BaseModel):
    id: str
    topic: str
    url: str
    active: bool
    secret: str | None = None  # only populated on creation — see WebhookService.create's docstring

    @classmethod
    def from_model(cls, subscription, secret: str | None = None) -> "WebhookSubscriptionResult":
        return cls(
            id=subscription.id,
            topic=subscription.topic,
            url=subscription.url,
            active=subscription.active,
            secret=secret,
        )


# --------------------------------------------------------------------------
# webhooks.subscription.create
# --------------------------------------------------------------------------


class CreateWebhookSubscriptionParams(BaseModel):
    topic: str
    url: str


@capability(
    name="webhooks.subscription.create",
    summary="Register a URL to receive signed HTTP POST deliveries whenever the given topic is dispatched.",
    params_model=CreateWebhookSubscriptionParams,
    result_model=WebhookSubscriptionResult,
    required_permission="webhooks.subscription.manage",
    destructive=False,
    audit_category="webhooks",
)
async def create_subscription(
    ctx: CallContext, params: CreateWebhookSubscriptionParams
) -> WebhookSubscriptionResult:
    """The returned `secret` is shown exactly once, here — it is not
    recoverable afterward. `webhooks.subscription.list` never includes it.
    Callers must save it immediately to verify future deliveries'
    X-Umbrella-Signature header."""
    created_by = await _resolve_created_by(ctx)
    subscription, secret = await WebhookService.create(
        ctx.db, topic=params.topic, url=params.url, created_by=created_by
    )
    return WebhookSubscriptionResult.from_model(subscription, secret=secret)


# --------------------------------------------------------------------------
# webhooks.subscription.list
# --------------------------------------------------------------------------


class ListWebhookSubscriptionsParams(BaseModel):
    topic: str | None = None


@capability(
    name="webhooks.subscription.list",
    summary="List webhook subscriptions, optionally filtered by topic (never includes the signing secret).",
    params_model=ListWebhookSubscriptionsParams,
    result_model=list[WebhookSubscriptionResult],
    required_permission="webhooks.subscription.view",
    destructive=False,
    audited=False,
)
async def list_subscriptions(
    ctx: CallContext, params: ListWebhookSubscriptionsParams
) -> list[WebhookSubscriptionResult]:
    subscriptions = await WebhookService.list_all(ctx.db, topic=params.topic)
    return [WebhookSubscriptionResult.from_model(s) for s in subscriptions]


# --------------------------------------------------------------------------
# webhooks.subscription.update
# --------------------------------------------------------------------------


class UpdateWebhookSubscriptionParams(BaseModel):
    subscription_id: str
    url: str | None = None
    active: bool | None = None

    def audit_target(self) -> str:
        return self.subscription_id


@capability(
    name="webhooks.subscription.update",
    summary="Update a webhook subscription's URL and/or active state.",
    params_model=UpdateWebhookSubscriptionParams,
    result_model=WebhookSubscriptionResult,
    required_permission="webhooks.subscription.manage",
    destructive=False,
    audit_category="webhooks",
)
async def update_subscription(
    ctx: CallContext, params: UpdateWebhookSubscriptionParams
) -> WebhookSubscriptionResult:
    subscription = await WebhookService.update(
        ctx.db, params.subscription_id, url=params.url, active=params.active
    )
    return WebhookSubscriptionResult.from_model(subscription)


# --------------------------------------------------------------------------
# webhooks.subscription.delete
# --------------------------------------------------------------------------


class DeleteWebhookSubscriptionParams(BaseModel):
    subscription_id: str

    def audit_target(self) -> str:
        return self.subscription_id


class DeleteWebhookSubscriptionResult(BaseModel):
    deleted: bool


@capability(
    name="webhooks.subscription.delete",
    summary="Permanently delete a webhook subscription.",
    params_model=DeleteWebhookSubscriptionParams,
    result_model=DeleteWebhookSubscriptionResult,
    required_permission="webhooks.subscription.manage",
    destructive=True,
    reversible=False,
    audit_category="webhooks",
)
async def delete_subscription(
    ctx: CallContext, params: DeleteWebhookSubscriptionParams
) -> DeleteWebhookSubscriptionResult:
    await WebhookService.delete(ctx.db, params.subscription_id)
    return DeleteWebhookSubscriptionResult(deleted=True)
