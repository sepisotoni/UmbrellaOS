import pytest

from tests.conftest import ADMIN_HEADERS
from tests.registry.conftest import session_headers_for_role


@pytest.mark.asyncio
async def test_automation_capabilities_are_listed(client):
    response = await client.get("/api/v1/capabilities")
    names = {c["name"] for c in response.json()}
    assert {
        "automation.schedule.create", "automation.schedule.list",
        "automation.schedule.set_enabled", "automation.schedule.delete",
    } <= names


@pytest.mark.asyncio
async def test_create_schedule_via_rest(client):
    response = await client.post(
        "/api/v1/capabilities/automation.schedule.create/invoke",
        json={
            "name": "nightly-whoami",
            "cron_expression": "0 3 * * *",
            "capability_name": "platform.system.whoami",
        },
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["enabled"] is True


@pytest.mark.asyncio
async def test_create_schedule_rejects_unknown_capability(client):
    response = await client.post(
        "/api/v1/capabilities/automation.schedule.create/invoke",
        json={"name": "bad", "cron_expression": "0 3 * * *", "capability_name": "does.not.exist"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "SCHEDULE_ERROR"


@pytest.mark.asyncio
async def test_create_schedule_denied_without_permission(client, db_session):
    headers = await session_headers_for_role(db_session, "member")
    response = await client.post(
        "/api/v1/capabilities/automation.schedule.create/invoke",
        json={"name": "x", "cron_expression": "0 3 * * *", "capability_name": "platform.system.whoami"},
        headers=headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_disable_then_enable_schedule(client):
    create_response = await client.post(
        "/api/v1/capabilities/automation.schedule.create/invoke",
        json={"name": "toggle-me", "cron_expression": "0 3 * * *", "capability_name": "platform.system.whoami"},
        headers=ADMIN_HEADERS,
    )
    schedule_id = create_response.json()["id"]

    disable_response = await client.post(
        "/api/v1/capabilities/automation.schedule.set_enabled/invoke",
        json={"schedule_id": schedule_id, "enabled": False},
        headers=ADMIN_HEADERS,
    )
    assert disable_response.json()["enabled"] is False

    enable_response = await client.post(
        "/api/v1/capabilities/automation.schedule.set_enabled/invoke",
        json={"schedule_id": schedule_id, "enabled": True},
        headers=ADMIN_HEADERS,
    )
    assert enable_response.json()["enabled"] is True


@pytest.mark.asyncio
async def test_delete_schedule_via_rest(client):
    create_response = await client.post(
        "/api/v1/capabilities/automation.schedule.create/invoke",
        json={"name": "delete-me", "cron_expression": "0 3 * * *", "capability_name": "platform.system.whoami"},
        headers=ADMIN_HEADERS,
    )
    schedule_id = create_response.json()["id"]

    delete_response = await client.post(
        "/api/v1/capabilities/automation.schedule.delete/invoke",
        json={"schedule_id": schedule_id},
        headers=ADMIN_HEADERS,
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True

    list_response = await client.post(
        "/api/v1/capabilities/automation.schedule.list/invoke", json={}, headers=ADMIN_HEADERS
    )
    assert schedule_id not in {s["id"] for s in list_response.json()}
