"""
tests/registry/test_capabilities_backup.py — REST integration tests for
Phase 4's backup capabilities. Covers what's testable end-to-end without a
live daemon: capability registration, RBAC, and 404 behavior for backups
that don't exist. Server-lifecycle-style flows that need a real daemon call
(actually creating a backup) are covered at the service layer instead
(tests/test_backup_service.py, with an injected fake DaemonClient) — the
same documented boundary as hosting.server.create in PHASE2_CHANGES.md.
"""
import pytest

from tests.conftest import ADMIN_HEADERS
from tests.registry.conftest import session_headers_for_role


@pytest.mark.asyncio
async def test_backup_capabilities_are_listed(client):
    response = await client.get("/api/v1/capabilities")
    names = {c["name"] for c in response.json()}
    assert {
        "hosting.backup.create", "hosting.backup.list", "hosting.backup.restore", "hosting.backup.delete",
    } <= names


@pytest.mark.asyncio
async def test_backup_create_denied_without_permission(client, db_session):
    headers = await session_headers_for_role(db_session, "member")
    response = await client.post(
        "/api/v1/capabilities/hosting.backup.create/invoke",
        json={"server_id": "00000000-0000-0000-0000-000000000000"},
        headers=headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_backup_list_for_unknown_server_returns_empty_not_error(client):
    # list_backups filters by server_id with no existence check of its own
    # (a nonexistent server simply has no backups) — proves that's true
    # rather than assuming it.
    response = await client.post(
        "/api/v1/capabilities/hosting.backup.list/invoke",
        json={"server_id": "00000000-0000-0000-0000-000000000000"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_backup_restore_of_unknown_backup_returns_404(client):
    response = await client.post(
        "/api/v1/capabilities/hosting.backup.restore/invoke",
        json={"backup_id": "00000000-0000-0000-0000-000000000000"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 404
    assert response.json()["code"] == "BACKUP_ERROR"


@pytest.mark.asyncio
async def test_backup_delete_of_unknown_backup_returns_404(client):
    response = await client.post(
        "/api/v1/capabilities/hosting.backup.delete/invoke",
        json={"backup_id": "00000000-0000-0000-0000-000000000000"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 404
