"""
tests/registry/test_capabilities_webhooks.py — REST integration tests for
Phase 7's webhook subscription CRUD capabilities, through the real FastAPI
app, registry, and database.
"""
import pytest

from tests.conftest import ADMIN_HEADERS
from tests.registry.conftest import session_headers_for_role


@pytest.mark.asyncio
async def test_create_subscription_returns_secret_once(client):
    response = await client.post(
        "/api/v1/capabilities/webhooks.subscription.create/invoke",
        json={"topic": "staff_escalation.created", "url": "https://example.com/hook"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["topic"] == "staff_escalation.created"
    assert body["url"] == "https://example.com/hook"
    assert body["active"] is True
    assert body["secret"] is not None
    assert len(body["secret"]) > 20


@pytest.mark.asyncio
async def test_create_subscription_rejects_non_http_url(client):
    response = await client.post(
        "/api/v1/capabilities/webhooks.subscription.create/invoke",
        json={"topic": "test.topic", "url": "not-a-url"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "WEBHOOK_ERROR"


@pytest.mark.asyncio
async def test_list_subscriptions_never_includes_secret(client):
    await client.post(
        "/api/v1/capabilities/webhooks.subscription.create/invoke",
        json={"topic": "list.no.secret", "url": "https://example.com/a"},
        headers=ADMIN_HEADERS,
    )
    response = await client.post(
        "/api/v1/capabilities/webhooks.subscription.list/invoke", json={}, headers=ADMIN_HEADERS
    )
    assert response.status_code == 200
    subscriptions = response.json()
    assert any(s["topic"] == "list.no.secret" for s in subscriptions)
    for subscription in subscriptions:
        assert subscription["secret"] is None


@pytest.mark.asyncio
async def test_list_subscriptions_filters_by_topic(client):
    await client.post(
        "/api/v1/capabilities/webhooks.subscription.create/invoke",
        json={"topic": "filter.topic.a", "url": "https://example.com/a"},
        headers=ADMIN_HEADERS,
    )
    await client.post(
        "/api/v1/capabilities/webhooks.subscription.create/invoke",
        json={"topic": "filter.topic.b", "url": "https://example.com/b"},
        headers=ADMIN_HEADERS,
    )
    response = await client.post(
        "/api/v1/capabilities/webhooks.subscription.list/invoke",
        json={"topic": "filter.topic.a"},
        headers=ADMIN_HEADERS,
    )
    subscriptions = response.json()
    assert all(s["topic"] == "filter.topic.a" for s in subscriptions)
    assert len(subscriptions) >= 1


@pytest.mark.asyncio
async def test_update_subscription_can_deactivate_and_change_url(client):
    create_response = await client.post(
        "/api/v1/capabilities/webhooks.subscription.create/invoke",
        json={"topic": "update.topic", "url": "https://example.com/old"},
        headers=ADMIN_HEADERS,
    )
    subscription_id = create_response.json()["id"]

    update_response = await client.post(
        "/api/v1/capabilities/webhooks.subscription.update/invoke",
        json={"subscription_id": subscription_id, "url": "https://example.com/new", "active": False},
        headers=ADMIN_HEADERS,
    )
    assert update_response.status_code == 200
    body = update_response.json()
    assert body["url"] == "https://example.com/new"
    assert body["active"] is False


@pytest.mark.asyncio
async def test_update_nonexistent_subscription_returns_404(client):
    response = await client.post(
        "/api/v1/capabilities/webhooks.subscription.update/invoke",
        json={"subscription_id": "does-not-exist", "active": False},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_subscription_removes_it_from_list(client):
    create_response = await client.post(
        "/api/v1/capabilities/webhooks.subscription.create/invoke",
        json={"topic": "delete.topic", "url": "https://example.com/gone"},
        headers=ADMIN_HEADERS,
    )
    subscription_id = create_response.json()["id"]

    delete_response = await client.post(
        "/api/v1/capabilities/webhooks.subscription.delete/invoke",
        json={"subscription_id": subscription_id},
        headers=ADMIN_HEADERS,
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True

    list_response = await client.post(
        "/api/v1/capabilities/webhooks.subscription.list/invoke", json={}, headers=ADMIN_HEADERS
    )
    ids = [s["id"] for s in list_response.json()]
    assert subscription_id not in ids


@pytest.mark.asyncio
async def test_webhook_capabilities_denied_without_permission(client, db_session):
    headers = await session_headers_for_role(db_session, "member")
    response = await client.post(
        "/api/v1/capabilities/webhooks.subscription.create/invoke",
        json={"topic": "denied.topic", "url": "https://example.com/denied"},
        headers=headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_webhook_view_permission_allows_list_but_not_create(client, db_session):
    """helper doesn't have webhooks.subscription.view either, so this uses
    moderator, which also lacks it by design (webhooks are an ops/
    integration concern, not a moderation one — see
    services/roles_service.py's comment on the new permission keys). This
    test exists to document that deliberate exclusion, not to test a role
    that has view-only access (no default role currently does)."""
    headers = await session_headers_for_role(db_session, "moderator")
    response = await client.post(
        "/api/v1/capabilities/webhooks.subscription.list/invoke", json={}, headers=headers
    )
    assert response.status_code == 403
