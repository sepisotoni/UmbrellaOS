"""
tests/registry/test_capabilities_dashboard_layout.py — REST integration
tests for Phase 10 step 6's dashboard.layout.* capabilities, through the
real FastAPI app, registry, and database. Same shape as
test_capabilities_identity.py's MFA tests, which this domain deliberately
mirrors (see capabilities/dashboard_layout.py's module docstring).
"""
import pytest

from tests.conftest import ADMIN_HEADERS
from tests.registry.conftest import session_headers_for_role


@pytest.mark.asyncio
async def test_get_layout_with_no_saved_row_returns_none_widgets(client, db_session):
    headers = await session_headers_for_role(db_session, "owner", suffix="-layout-empty")

    response = await client.post(
        "/api/v1/capabilities/dashboard.layout.get/invoke",
        json={"page_id": "dashboard"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["page_id"] == "dashboard"
    assert body["widgets"] is None


@pytest.mark.asyncio
async def test_set_then_get_round_trips_the_saved_layout(client, db_session):
    headers = await session_headers_for_role(db_session, "owner", suffix="-layout-roundtrip")

    widgets = [
        {"widget_key": "pluginA:pluginA.stats", "visible": True},
        {"widget_key": "pluginB:pluginB.status", "visible": False},
    ]
    set_response = await client.post(
        "/api/v1/capabilities/dashboard.layout.set/invoke",
        json={"page_id": "dashboard", "widgets": widgets},
        headers=headers,
    )
    assert set_response.status_code == 200
    assert set_response.json()["widgets"] == widgets

    get_response = await client.post(
        "/api/v1/capabilities/dashboard.layout.get/invoke",
        json={"page_id": "dashboard"},
        headers=headers,
    )
    assert get_response.status_code == 200
    assert get_response.json()["widgets"] == widgets


@pytest.mark.asyncio
async def test_set_twice_replaces_rather_than_duplicates(client, db_session):
    headers = await session_headers_for_role(db_session, "owner", suffix="-layout-replace")

    first = [{"widget_key": "pluginA:pluginA.stats", "visible": True}]
    second = [{"widget_key": "pluginA:pluginA.stats", "visible": False}]

    await client.post(
        "/api/v1/capabilities/dashboard.layout.set/invoke",
        json={"page_id": "dashboard", "widgets": first},
        headers=headers,
    )
    await client.post(
        "/api/v1/capabilities/dashboard.layout.set/invoke",
        json={"page_id": "dashboard", "widgets": second},
        headers=headers,
    )
    get_response = await client.post(
        "/api/v1/capabilities/dashboard.layout.get/invoke",
        json={"page_id": "dashboard"},
        headers=headers,
    )
    assert get_response.json()["widgets"] == second


@pytest.mark.asyncio
async def test_reset_deletes_saved_layout(client, db_session):
    headers = await session_headers_for_role(db_session, "owner", suffix="-layout-reset")

    await client.post(
        "/api/v1/capabilities/dashboard.layout.set/invoke",
        json={"page_id": "dashboard", "widgets": [{"widget_key": "a:b", "visible": True}]},
        headers=headers,
    )
    reset_response = await client.post(
        "/api/v1/capabilities/dashboard.layout.reset/invoke",
        json={"page_id": "dashboard"},
        headers=headers,
    )
    assert reset_response.status_code == 200
    assert reset_response.json()["reset"] is True

    get_response = await client.post(
        "/api/v1/capabilities/dashboard.layout.get/invoke",
        json={"page_id": "dashboard"},
        headers=headers,
    )
    assert get_response.json()["widgets"] is None


@pytest.mark.asyncio
async def test_reset_with_no_saved_layout_is_a_no_op_not_an_error(client, db_session):
    headers = await session_headers_for_role(db_session, "owner", suffix="-layout-reset-noop")

    response = await client.post(
        "/api/v1/capabilities/dashboard.layout.reset/invoke",
        json={"page_id": "dashboard"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["reset"] is False


@pytest.mark.asyncio
async def test_layout_is_per_user_not_shared(client, db_session):
    headers_a = await session_headers_for_role(db_session, "owner", suffix="-layout-user-a")
    headers_b = await session_headers_for_role(db_session, "admin", suffix="-layout-user-b")

    await client.post(
        "/api/v1/capabilities/dashboard.layout.set/invoke",
        json={"page_id": "dashboard", "widgets": [{"widget_key": "a:b", "visible": True}]},
        headers=headers_a,
    )
    get_b = await client.post(
        "/api/v1/capabilities/dashboard.layout.get/invoke",
        json={"page_id": "dashboard"},
        headers=headers_b,
    )
    assert get_b.json()["widgets"] is None


@pytest.mark.asyncio
async def test_non_customizable_page_id_is_rejected(client, db_session):
    headers = await session_headers_for_role(db_session, "owner", suffix="-layout-bad-page")

    response = await client.post(
        "/api/v1/capabilities/dashboard.layout.get/invoke",
        json={"page_id": "topology"},
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "DASHBOARD_LAYOUT_ERROR"


@pytest.mark.asyncio
async def test_layout_denied_for_admin_key_actor(client):
    """Same reasoning as identity.mfa's admin-key rejection: the admin-key
    bootstrap tier has no underlying User row for a personal layout to
    attach to."""
    response = await client.post(
        "/api/v1/capabilities/dashboard.layout.get/invoke",
        json={"page_id": "dashboard"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "DASHBOARD_LAYOUT_ERROR"
