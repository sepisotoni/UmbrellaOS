"""
api/routers/webhooks_rest.py — Thin REST facades over the webhooks capability system.

GET    /api/v1/webhooks        → webhooks.subscription.list capability
POST   /api/v1/webhooks        → webhooks.subscription.create capability
DELETE /api/v1/webhooks/{id}   → webhooks.subscription.delete capability
POST   /api/v1/webhooks/{id}/test → delivers a test event to the subscription

These facades exist because the dashboard calls these simple REST paths rather
than the capabilities invoke endpoint (POST /api/v1/capabilities/.../invoke).
They delegate directly to the same service layer the capabilities use.
"""
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from api.dependencies.permissions import require_permission
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
    _auth=Depends(require_permission("webhooks.subscription.manage")),
) -> WebhookSubscriptionSchema:
    """Register a new webhook subscription.
    The returned secret is shown once — save it to verify future deliveries.
    """
    subscription, secret = await WebhookService.create(db, topic=body.topic, url=body.url, created_by=None)
    await db.commit()
    return WebhookSubscriptionSchema(
        id=subscription.id, topic=subscription.topic, url=subscription.url,
        active=subscription.active, secret=secret,
    )


@router.delete("/{subscription_id}", response_model=DeletedResponse)
async def delete_webhook(
    subscription_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_permission("webhooks.subscription.manage")),
) -> DeletedResponse:
    """Permanently delete a webhook subscription."""
    try:
        await WebhookService.delete(db, subscription_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
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
    except Exception as exc:
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
