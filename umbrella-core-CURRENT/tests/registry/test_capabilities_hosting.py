"""
tests/registry/test_capabilities_hosting.py — REST integration tests for
Phase 2's hosting capabilities, exercised through the real FastAPI app, the
real Capability Registry, and the real (seeded, in-memory) database.

Covers the non-daemon-touching capabilities end-to-end (node/template/
allocation registration and listing) plus RBAC enforcement — proving,
among other things, that domain-specific exceptions (NodeError,
AllocationError, etc.) surface their correct HTTP status codes rather than
collapsing to a generic 500 (a real bug caught and fixed during this
phase's development; see PHASE2_CHANGES.md).

Server lifecycle capabilities (create/start/stop/restart/kill/stats,
which call out to a node's daemon) are covered thoroughly at the service
layer instead (tests/test_hosting_services.py, using an injected fake
DaemonClient) — exercising them through the full REST stack would require
either a live daemon or daemon-URL-level HTTP mocking the capability layer
doesn't currently expose a seam for; noted as a reasonable follow-up rather
than built speculatively now.
"""
import pytest

from tests.conftest import ADMIN_HEADERS
from tests.registry.conftest import session_headers_for_role


@pytest.mark.asyncio
async def test_hosting_capabilities_are_listed(client):
    response = await client.get("/api/v1/capabilities")
    assert response.status_code == 200
    names = {c["name"] for c in response.json()}
    assert "hosting.node.register" in names
    assert "hosting.server.create" in names


@pytest.mark.asyncio
async def test_register_node_via_admin_key_returns_signing_secret(client):
    response = await client.post(
        "/api/v1/capabilities/hosting.node.register/invoke",
        json={"name": "node-rest-1", "daemon_url": "https://node1:8443"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "node-rest-1"
    assert body["status"] == "pending"
    assert body["signing_secret"] is not None
    assert len(body["signing_secret"]) >= 32


@pytest.mark.asyncio
async def test_list_nodes_never_exposes_signing_secret(client):
    await client.post(
        "/api/v1/capabilities/hosting.node.register/invoke",
        json={"name": "node-rest-2", "daemon_url": "https://node2:8443"},
        headers=ADMIN_HEADERS,
    )
    response = await client.post(
        "/api/v1/capabilities/hosting.node.list/invoke", json={}, headers=ADMIN_HEADERS
    )
    assert response.status_code == 200
    for node in response.json():
        assert node["signing_secret"] is None


@pytest.mark.asyncio
async def test_register_node_denied_without_permission(client, db_session):
    headers = await session_headers_for_role(db_session, "member")
    response = await client.post(
        "/api/v1/capabilities/hosting.node.register/invoke",
        json={"name": "node-rest-denied", "daemon_url": "https://node:8443"},
        headers=headers,
    )
    assert response.status_code == 403
    assert response.json()["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_register_duplicate_node_returns_409_not_500(client):
    await client.post(
        "/api/v1/capabilities/hosting.node.register/invoke",
        json={"name": "node-dup-rest", "daemon_url": "https://node:8443"},
        headers=ADMIN_HEADERS,
    )
    response = await client.post(
        "/api/v1/capabilities/hosting.node.register/invoke",
        json={"name": "node-dup-rest", "daemon_url": "https://node-other:8443"},
        headers=ADMIN_HEADERS,
    )
    # This is the specific regression this test guards: NodeError must
    # surface its real 409, not collapse into a generic 500 by falling
    # through to the catch-all exception handler.
    assert response.status_code == 409
    assert response.json()["code"] == "NODE_ERROR"


@pytest.mark.asyncio
async def test_get_missing_node_returns_404_not_500(client):
    response = await client.post(
        "/api/v1/capabilities/hosting.node.get/invoke",
        json={"node_id": "00000000-0000-0000-0000-000000000000"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 404
    assert response.json()["code"] == "NODE_ERROR"


@pytest.mark.asyncio
async def test_create_and_list_templates(client):
    create_response = await client.post(
        "/api/v1/capabilities/hosting.template.create/invoke",
        json={"name": "Paper 1.21", "image": "itzg/minecraft-server:java21"},
        headers=ADMIN_HEADERS,
    )
    assert create_response.status_code == 200
    assert create_response.json()["version"] == 1

    list_response = await client.post(
        "/api/v1/capabilities/hosting.template.list/invoke", json={}, headers=ADMIN_HEADERS
    )
    assert list_response.status_code == 200
    names = {t["name"] for t in list_response.json()}
    assert "Paper 1.21" in names


@pytest.mark.asyncio
async def test_create_allocation_and_duplicate_returns_409(client):
    node_response = await client.post(
        "/api/v1/capabilities/hosting.node.register/invoke",
        json={"name": "node-alloc-rest", "daemon_url": "https://node:8443"},
        headers=ADMIN_HEADERS,
    )
    node_id = node_response.json()["id"]

    first = await client.post(
        "/api/v1/capabilities/hosting.allocation.create/invoke",
        json={"node_id": node_id, "port": 25565},
        headers=ADMIN_HEADERS,
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/v1/capabilities/hosting.allocation.create/invoke",
        json={"node_id": node_id, "port": 25565},
        headers=ADMIN_HEADERS,
    )
    assert second.status_code == 409
    assert second.json()["code"] == "ALLOCATION_ERROR"


@pytest.mark.asyncio
async def test_create_allocation_rejects_invalid_port(client):
    node_response = await client.post(
        "/api/v1/capabilities/hosting.node.register/invoke",
        json={"name": "node-badport", "daemon_url": "https://node:8443"},
        headers=ADMIN_HEADERS,
    )
    node_id = node_response.json()["id"]

    response = await client.post(
        "/api/v1/capabilities/hosting.allocation.create/invoke",
        json={"node_id": node_id, "port": 999999},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_hosting_actions_are_audited(client, db_session):
    await client.post(
        "/api/v1/capabilities/hosting.node.register/invoke",
        json={"name": "node-audit-check", "daemon_url": "https://node:8443"},
        headers=ADMIN_HEADERS,
    )
    response = await client.post(
        "/api/v1/capabilities/platform.audit.search/invoke",
        json={"action": "hosting.node.register", "limit": 50},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
