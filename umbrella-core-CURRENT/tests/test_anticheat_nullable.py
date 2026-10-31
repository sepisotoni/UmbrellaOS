"""Regression: historic anticheat flags survive deleted player records."""

import pytest

from models.anticheat_violation import AnticheatViolation
from tests.conftest import ADMIN_HEADERS


@pytest.mark.asyncio
async def test_list_violations_preserves_rows_with_deleted_player(client, db_session):
    async with db_session() as db:
        db.add(
            AnticheatViolation(
                player_uuid=None,
                player_name="deleted-user",
                server_id="survival-1",
                check_name="Fly",
                verbose="historical evidence",
                vl=7,
            )
        )
        await db.commit()

    response = await client.get(
        "/api/v1/anticheat/violations", headers=ADMIN_HEADERS
    )
    assert response.status_code == 200
    records = response.json()
    assert len(records) == 1
    assert records[0]["player_uuid"] is None
    assert records[0]["player_name"] == "deleted-user"
