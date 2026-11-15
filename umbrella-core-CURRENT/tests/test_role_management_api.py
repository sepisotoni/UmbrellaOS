"""API tests for staff-editable role permission presets."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models import Session, User
from models.permissions import Permission, Role


async def _owner_headers(db_session):
    async with db_session() as db:
        role = await db.scalar(select(Role).where(Role.name == "owner"))
        user = User(
            discord_id="role-api-owner",
            username="RoleApiOwner",
            role_id=role.id,
        )
        db.add(user)
        await db.flush()
        db.add(
            Session(
                user_id=user.id,
                token="role-api-owner-token",
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
        )
        await db.commit()
    return {"Authorization": "Bearer role-api-owner-token"}


@pytest.mark.asyncio
async def test_role_permission_update_invalidates_assigned_user_claims(
    client, db_session
):
    owner_headers = await _owner_headers(db_session)

    async with db_session() as db:
        helper_role = await db.scalar(
            select(Role)
            .where(Role.name == "helper")
            .options(selectinload(Role.permissions))
        )
        permission = await db.scalar(
            select(Permission).where(Permission.permission_key == "players.view")
        )
        user = User(
            discord_id="role-claim-user",
            username="RoleClaimUser",
            role_id=helper_role.id,
            authz_version=4,
        )
        db.add(user)
        await db.commit()
        role_id = helper_role.id
        user_id = user.id
        permission_key = permission.permission_key

    response = await client.put(
        f"/api/v1/roles/{role_id}/permissions",
        json={"permissions": [permission_key]},
        headers=owner_headers,
    )

    assert response.status_code == 200
    assert response.json()["permissions"] == [permission_key]
    async with db_session() as db:
        user = await db.get(User, user_id)
        assert user.authz_version == 5


@pytest.mark.asyncio
async def test_role_permission_update_rejects_unknown_permission(client, db_session):
    owner_headers = await _owner_headers(db_session)

    async with db_session() as db:
        helper_role = await db.scalar(
            select(Role)
            .where(Role.name == "helper")
            .options(selectinload(Role.permissions))
        )
        role_id = helper_role.id
        previous_permissions = {
            permission.permission_key for permission in helper_role.permissions
        }

    response = await client.put(
        f"/api/v1/roles/{role_id}/permissions",
        json={"permissions": ["not.a.real.permission"]},
        headers=owner_headers,
    )

    assert response.status_code == 400
    async with db_session() as db:
        helper_role = await db.scalar(
            select(Role)
            .where(Role.id == role_id)
            .options(selectinload(Role.permissions))
        )
        assert {
            permission.permission_key for permission in helper_role.permissions
        } == previous_permissions


@pytest.mark.asyncio
async def test_owner_role_permissions_cannot_be_changed(client, db_session):
    owner_headers = await _owner_headers(db_session)
    async with db_session() as db:
        owner_role = await db.scalar(select(Role).where(Role.name == "owner"))
        role_id = owner_role.id

    response = await client.put(
        f"/api/v1/roles/{role_id}/permissions",
        json={"permissions": []},
        headers=owner_headers,
    )

    assert response.status_code == 409
