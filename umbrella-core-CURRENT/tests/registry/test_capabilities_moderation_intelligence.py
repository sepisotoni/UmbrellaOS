"""
tests/registry/test_capabilities_moderation_intelligence.py — REST
integration tests for the moderation_intelligence capabilities, exercised
through the real FastAPI app, the real Capability Registry, and the real
(seeded, in-memory) database.

report.analyze is tested at the service layer already
(tests/test_moderation_intelligence.py, with ModelRouter.generate
monkeypatched) - these tests focus on the REST/RBAC/registry plumbing:
that the capabilities are listed, that permissions are enforced per role,
and that create/get/escalation-list/resolve round-trip correctly through
the real HTTP stack.
"""
import pytest

from tests.conftest import ADMIN_HEADERS
from tests.registry.conftest import session_headers_for_role


@pytest.mark.asyncio
async def test_moderation_intelligence_capabilities_are_listed(client):
    response = await client.get("/api/v1/capabilities")
    assert response.status_code == 200
    names = {c["name"] for c in response.json()}
    assert "moderation_intelligence.report.create" in names
    assert "moderation_intelligence.report.analyze" in names
    assert "moderation_intelligence.escalation.resolve" in names


@pytest.mark.asyncio
async def test_create_report_via_admin_key(client):
    response = await client.post(
        "/api/v1/capabilities/moderation_intelligence.report.create/invoke",
        json={"reported_user_id": "discord-999", "reason": "Spamming links"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["reported_user_id"] == "discord-999"
    assert body["status"] == "pending"
    assert body["reporter_id"] == "admin-key"  # REST admin-key calls attribute normally; only AI-sourced calls don't


@pytest.mark.asyncio
async def test_create_report_via_ai_tool_registry_does_not_self_attribute(db_session):
    """The actual case create_report's ctx.source == "ai" branch exists
    for: a system-generated report (e.g. from a heuristic detector,
    routed through the AI Tool Registry) shouldn't be attributed to
    whichever superuser identity happened to be used to call it."""
    import capabilities  # noqa: F401 - registers @capability decorators
    from registry.adapters.ai import call_tool
    from tests.conftest import TEST_SECRET_KEY

    async with db_session() as db:
        result = await call_tool(
            "moderation_intelligence.report.create",
            {"reported_user_id": "discord-995", "reason": "System-flagged spam"},
            acting_on_behalf_of=TEST_SECRET_KEY,
            db=db,
            autonomous_mode=True,
        )
    assert result["reporter_id"] is None


@pytest.mark.asyncio
async def test_create_report_via_moderator_attributes_reporter(client, db_session):
    headers = await session_headers_for_role(db_session, "moderator")
    response = await client.post(
        "/api/v1/capabilities/moderation_intelligence.report.create/invoke",
        json={"reported_user_id": "discord-998", "reason": "Harassment"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["reporter_id"] == "discord-moderator"


@pytest.mark.asyncio
async def test_create_report_denied_for_member_role(client, db_session):
    headers = await session_headers_for_role(db_session, "member")
    response = await client.post(
        "/api/v1/capabilities/moderation_intelligence.report.create/invoke",
        json={"reported_user_id": "discord-997", "reason": "Test"},
        headers=headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_report_requires_view_permission(client, db_session):
    create_resp = await client.post(
        "/api/v1/capabilities/moderation_intelligence.report.create/invoke",
        json={"reported_user_id": "discord-996", "reason": "Test"},
        headers=ADMIN_HEADERS,
    )
    report_id = create_resp.json()["id"]

    helper_headers = await session_headers_for_role(db_session, "helper")
    response = await client.post(
        "/api/v1/capabilities/moderation_intelligence.report.get/invoke",
        json={"report_id": report_id},
        headers=helper_headers,
    )
    # "helper" has no moderation_intelligence permissions at all - denied.
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_nonexistent_report_returns_404(client):
    response = await client.post(
        "/api/v1/capabilities/moderation_intelligence.report.get/invoke",
        json={"report_id": "does-not-exist"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_escalation_list_and_resolve_round_trip(client, db_session):
    from models.moderation_intelligence import StaffEscalation

    async with db_session() as db:
        escalation = StaffEscalation(source="moderation", summary="Needs a human look", confidence=0.4)
        db.add(escalation)
        await db.flush()
        await db.commit()
        escalation_id = escalation.id

    list_resp = await client.post(
        "/api/v1/capabilities/moderation_intelligence.escalation.list/invoke",
        json={},
        headers=ADMIN_HEADERS,
    )
    assert list_resp.status_code == 200
    ids = {e["id"] for e in list_resp.json()["escalations"]}
    assert escalation_id in ids

    resolve_resp = await client.post(
        "/api/v1/capabilities/moderation_intelligence.escalation.resolve/invoke",
        json={"escalation_id": escalation_id},
        headers=ADMIN_HEADERS,
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["resolved"] is True

    list_resp_after = await client.post(
        "/api/v1/capabilities/moderation_intelligence.escalation.list/invoke",
        json={},
        headers=ADMIN_HEADERS,
    )
    ids_after = {e["id"] for e in list_resp_after.json()["escalations"]}
    assert escalation_id not in ids_after  # resolved escalations aren't "open" anymore


@pytest.mark.asyncio
async def test_new_escalations_have_null_notified_at(client, db_session):
    from models.moderation_intelligence import StaffEscalation

    async with db_session() as db:
        escalation = StaffEscalation(source="moderation", summary="Fresh one", confidence=0.4)
        db.add(escalation)
        await db.flush()
        await db.commit()
        escalation_id = escalation.id

    list_resp = await client.post(
        "/api/v1/capabilities/moderation_intelligence.escalation.list/invoke",
        json={},
        headers=ADMIN_HEADERS,
    )
    entry = next(e for e in list_resp.json()["escalations"] if e["id"] == escalation_id)
    assert entry["notified_at"] is None


@pytest.mark.asyncio
async def test_mark_notified_sets_timestamp_and_is_reflected_in_list(client, db_session):
    from models.moderation_intelligence import StaffEscalation

    async with db_session() as db:
        escalation = StaffEscalation(source="investigation", summary="Needs a look", confidence=0.6)
        db.add(escalation)
        await db.flush()
        await db.commit()
        escalation_id = escalation.id

    mark_resp = await client.post(
        "/api/v1/capabilities/moderation_intelligence.escalation.mark_notified/invoke",
        json={"escalation_id": escalation_id},
        headers=ADMIN_HEADERS,
    )
    assert mark_resp.status_code == 200
    assert mark_resp.json()["notified_at"] is not None

    list_resp = await client.post(
        "/api/v1/capabilities/moderation_intelligence.escalation.list/invoke",
        json={},
        headers=ADMIN_HEADERS,
    )
    entry = next(e for e in list_resp.json()["escalations"] if e["id"] == escalation_id)
    assert entry["notified_at"] is not None


@pytest.mark.asyncio
async def test_mark_notified_for_unknown_escalation_returns_404(client):
    response = await client.post(
        "/api/v1/capabilities/moderation_intelligence.escalation.mark_notified/invoke",
        json={"escalation_id": "does-not-exist"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_mark_notified_denied_without_manage_permission(client, db_session):
    from models.moderation_intelligence import StaffEscalation

    async with db_session() as db:
        escalation = StaffEscalation(source="moderation", summary="x", confidence=0.5)
        db.add(escalation)
        await db.flush()
        await db.commit()
        escalation_id = escalation.id

    headers = await session_headers_for_role(db_session, "member")
    response = await client.post(
        "/api/v1/capabilities/moderation_intelligence.escalation.mark_notified/invoke",
        json={"escalation_id": escalation_id},
        headers=headers,
    )
    assert response.status_code == 403
