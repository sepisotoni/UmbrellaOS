"""
api/routers/webhooks_rest.py — Thin REST facades over the webhooks capability system.

GET    /api/v1/webhooks             → list subscriptions
POST   /api/v1/webhooks             → create a subscription
PATCH  /api/v1/webhooks/{id}        → update URL / active state (FIX-F008: added)
DELETE /api/v1/webhooks/{id}        → delete a subscription
POST   /api/v1/webhooks/{id}/test   → deliver a test event

These facades exist because the dashboard calls these simple REST paths rather
than the capabilities invoke endpoint (POST /api/v1/capabilities/.../invoke).
They delegate directly to the same service layer the capabilities use.

FIX (FINDING-008): added PATCH /{id} so callers can pause (active=false) or
update the URL after creation — previously the only path was capability invoke.
created_by is now passed from the real auth identity rather than hardcoded None.

FIX (FINDING-009): delete previously caught every exception as 404. DB errors,
programming errors, and unexpected WebhookError were all silently reported as
'not found'. Now only ResourceNotFoundException maps to 404; everything else
re-raises (FastAPI's error handler returns 500).
"""
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from api.dependencies.permissions import require_permission
from api.middleware.errors import ResourceNotFoundException
from models import User
from services.webhooks.service import WebhookService, WebhookDeliveryService, WebhookDeliveryError

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


class WebhookSubscriptionSchema(BaseModel):
    id: str
    topic: str
    url: str
    active: bool
    secret: Optional[str] = None  # only returned on creation

    class Config:
        from_attributes = True


class CreateWebhookRequest(BaseModel):
    topic: str
    url: str


class UpdateWebhookRequest(BaseModel):
    url: Optional[str] = None
    active: Optional[bool] = None


class DeletedResponse(BaseModel):
    deleted: bool
    id: str


class TestWebhookResponse(BaseModel):
    success: bool
    message: str


@router.get("", response_model=list[WebhookSubscriptionSchema])
async def list_webhooks(
    topic: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_permission("webhooks.subscription.view")),
) -> list[WebhookSubscriptionSchema]:
    """List webhook subscriptions (never includes the signing secret)."""
    subs = await WebhookService.list_all(db, topic=topic)
    return [WebhookSubscriptionSchema(id=s.id, topic=s.topic, url=s.url, active=s.active) for s in subs]


@router.post("", response_model=WebhookSubscriptionSchema, status_code=201)
async def create_webhook(
    body: CreateWebhookRequest,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_permission("webhooks.subscription.manage")),
) -> WebhookSubscriptionSchema:
    """Register a new webhook subscription.
    The returned secret is shown once — save it to verify future deliveries.

    FIX (FINDING-008): created_by is now set from the real auth identity
    (username for session users, 'admin' for key callers) instead of None.
    """
    # FIX-F008: pass real creator identity
    created_by = auth.username if isinstance(auth, User) else "admin"
    subscription, secret = await WebhookService.create(
        db, topic=body.topic, url=body.url, created_by=created_by
    )
    await db.commit()
    return WebhookSubscriptionSchema(
        id=subscription.id, topic=subscription.topic, url=subscription.url,
        active=subscription.active, secret=secret,
    )


@router.patch("/{subscription_id}", response_model=WebhookSubscriptionSchema)
async def update_webhook(
    subscription_id: str,
    body: UpdateWebhookRequest,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_permission("webhooks.subscription.manage")),
) -> WebhookSubscriptionSchema:
    """Update a webhook subscription's URL and/or active state.

    FIX (FINDING-008): this endpoint did not exist — the only way to pause
    or change a subscription's URL was through capability invoke. Added here
    so the dashboard can manage subscriptions entirely over REST.
    """
    try:
        subscription = await WebhookService.update(
            db, subscription_id, url=body.url, active=body.active
        )
    except ResourceNotFoundException as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await db.commit()
    return WebhookSubscriptionSchema(
        id=subscription.id, topic=subscription.topic,
        url=subscription.url, active=subscription.active,
    )


@router.delete("/{subscription_id}", response_model=DeletedResponse)
async def delete_webhook(
    subscription_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_permission("webhooks.subscription.manage")),
) -> DeletedResponse:
    """Permanently delete a webhook subscription.

    FIX (FINDING-009): previous code caught every exception as 404.
    DB errors, programming errors, and unexpected WebhookError were all
    silently reported as 'not found', making a failed DELETE look like the
    subscription never existed. Now only ResourceNotFoundException maps to
    404; everything else propagates to FastAPI's error handler (500).
    """
    try:
        await WebhookService.delete(db, subscription_id)
    except ResourceNotFoundException as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    # Other exceptions (DB error, etc.) propagate as 500 — correct behaviour.
    await db.commit()
    return DeletedResponse(deleted=True, id=subscription_id)


@router.post("/{subscription_id}/test", response_model=TestWebhookResponse)
async def test_webhook(
    subscription_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_permission("webhooks.subscription.manage")),
) -> TestWebhookResponse:
    """Send a test ping event to a webhook subscription URL."""
    try:
        subscription = await WebhookService.get(db, subscription_id)
    except ResourceNotFoundException as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    test_payload = {
        "event": "webhook.test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "subscription_id": subscription_id,
        "message": "This is a test delivery from UmbrellaOS.",
    }
    try:
        await WebhookDeliveryService.deliver(
            subscription,
            topic="webhook.test",
            event_id=f"test-{subscription_id}",
            payload=test_payload,
        )
        return TestWebhookResponse(success=True, message="Test delivery succeeded.")
    except WebhookDeliveryError as exc:
        return TestWebhookResponse(success=False, message=str(exc))
