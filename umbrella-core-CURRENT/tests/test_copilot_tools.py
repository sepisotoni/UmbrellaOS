"""
tests/test_copilot_tools.py — Tests for services/ai/copilot_tools.py.

No coverage existed for this before it was written — it's a brand new
feature (2026-09-01, closing the "copilot has zero tools" gap [HEAD]
confirmed live). Covers: tool-request parsing from a model's fenced JSON
block, permission-scoped execution of each of the three tools, and the
common failure shapes (missing player, missing permission, unknown tool,
malformed JSON) without ever calling a real provider.
"""
from datetime import datetime, timezone

import pytest

from registry.context import CallContext
from models.player import Player, Punishment
from models.anticheat_violation import AnticheatViolation
from services.ai.copilot_tools import (
    parse_requested_tools,
    execute_tool_calls,
    format_tool_results_block,
    ToolCallResult,
)


def _ctx(db, permissions: set[str] | None = None, is_superuser: bool = False) -> CallContext:
    return CallContext(
        actor_id="test-staff-1",
        actor_type="staff",
        source="ai",
        permissions=permissions or set(),
        is_superuser=is_superuser,
        db=db,
    )


# ---------------------------------------------------------------------------
# parse_requested_tools
# ---------------------------------------------------------------------------

def test_parse_requested_tools_extracts_fenced_json_array():
    text = 'Sure, let me check.\n```json\n[{"tool": "lookup_player", "username": "Steve"}]\n```\n'
    parsed = parse_requested_tools(text)
    assert parsed == [{"tool": "lookup_player", "username": "Steve"}]


def test_parse_requested_tools_extracts_multiple_calls():
    text = '```json\n[{"tool": "lookup_player", "username": "Steve"}, {"tool": "get_punishment_history", "player_uuid": "abc"}]\n```'
    parsed = parse_requested_tools(text)
    assert len(parsed) == 2
    assert parsed[0]["tool"] == "lookup_player"
    assert parsed[1]["tool"] == "get_punishment_history"


def test_parse_requested_tools_returns_none_when_no_fenced_block():
    text = "The ban policy for griefing is a 7-day temp ban on first offense."
    assert parse_requested_tools(text) is None


def test_parse_requested_tools_returns_none_on_malformed_json():
    text = '```json\n[{"tool": "lookup_player", oops invalid}]\n```'
    assert parse_requested_tools(text) is None


def test_parse_requested_tools_returns_none_when_fenced_block_is_not_a_list():
    text = '```json\n{"tool": "lookup_player"}\n```'
    assert parse_requested_tools(text) is None


def test_parse_requested_tools_filters_out_non_dict_items():
    text = '```json\n[{"tool": "lookup_player", "username": "Steve"}, "garbage", 42]\n```'
    parsed = parse_requested_tools(text)
    assert parsed == [{"tool": "lookup_player", "username": "Steve"}]


# ---------------------------------------------------------------------------
# execute_tool_calls — lookup_player
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lookup_player_returns_player_data(db_session):
    async with db_session() as db:
        db.add(Player(uuid="11111111-1111-1111-1111-111111111111", username="Notch", risk_score=5, suspicion_score=2))
        await db.commit()

        results = await execute_tool_calls(
            _ctx(db, {"players.view"}), [{"tool": "lookup_player", "username": "Notch"}]
        )
        assert len(results) == 1
        assert results[0].tool == "lookup_player"
        assert results[0].result["uuid"] == "11111111-1111-1111-1111-111111111111"
        assert results[0].result["risk_score"] == 5


@pytest.mark.asyncio
async def test_lookup_player_is_case_insensitive(db_session):
    async with db_session() as db:
        db.add(Player(uuid="22222222-2222-2222-2222-222222222222", username="Dinnerbone"))
        await db.commit()

        results = await execute_tool_calls(
            _ctx(db, {"players.view"}), [{"tool": "lookup_player", "username": "dinnerbone"}]
        )
        assert results[0].result["username"] == "Dinnerbone"


@pytest.mark.asyncio
async def test_lookup_player_missing_player_returns_not_found_string(db_session):
    async with db_session() as db:
        results = await execute_tool_calls(
            _ctx(db, {"players.view"}), [{"tool": "lookup_player", "username": "NoSuchPlayer"}]
        )
        assert "no player found" in results[0].result


@pytest.mark.asyncio
async def test_lookup_player_denied_without_permission(db_session):
    async with db_session() as db:
        results = await execute_tool_calls(
            _ctx(db, set()), [{"tool": "lookup_player", "username": "Notch"}]
        )
        assert "error" in results[0].result
        assert "players.view" in results[0].result


@pytest.mark.asyncio
async def test_lookup_player_allowed_for_superuser_without_explicit_permission(db_session):
    async with db_session() as db:
        db.add(Player(uuid="33333333-3333-3333-3333-333333333333", username="Grumm"))
        await db.commit()

        results = await execute_tool_calls(
            _ctx(db, set(), is_superuser=True), [{"tool": "lookup_player", "username": "Grumm"}]
        )
        assert results[0].result["username"] == "Grumm"


# ---------------------------------------------------------------------------
# execute_tool_calls — get_punishment_history
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_punishment_history_returns_rows_most_recent_first(db_session):
    async with db_session() as db:
        player = Player(uuid="44444444-4444-4444-4444-444444444444", username="Xisuma")
        db.add(player)
        db.add(Punishment(
            player_uuid=player.uuid, type="ban", reason="Cheating", staff_id="staff-1",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ))
        db.add(Punishment(
            player_uuid=player.uuid, type="mute", reason="Spam", staff_id="staff-2",
            created_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        ))
        await db.commit()

        results = await execute_tool_calls(
            _ctx(db, {"punishments.view"}),
            [{"tool": "get_punishment_history", "player_uuid": player.uuid}],
        )
        rows = results[0].result
        assert len(rows) == 2
        assert rows[0]["type"] == "mute"  # most recent first
        assert rows[1]["type"] == "ban"


@pytest.mark.asyncio
async def test_get_punishment_history_requires_punishments_view_not_players_view(db_session):
    """punishments.view is a distinct permission from players.view in
    services/roles_service.py — a caller with only players.view must NOT
    be able to read punishment history through this tool."""
    async with db_session() as db:
        results = await execute_tool_calls(
            _ctx(db, {"players.view"}),  # NOT punishments.view
            [{"tool": "get_punishment_history", "player_uuid": "some-uuid"}],
        )
        assert "error" in results[0].result
        assert "punishments.view" in results[0].result


@pytest.mark.asyncio
async def test_get_punishment_history_empty_for_clean_player(db_session):
    async with db_session() as db:
        results = await execute_tool_calls(
            _ctx(db, {"punishments.view"}),
            [{"tool": "get_punishment_history", "player_uuid": "no-punishments-uuid"}],
        )
        assert "no punishment history" in results[0].result


# ---------------------------------------------------------------------------
# execute_tool_calls — get_anticheat_violations
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_anticheat_violations_returns_rows(db_session):
    async with db_session() as db:
        player = Player(uuid="55555555-5555-5555-5555-555555555555", username="Etho")
        db.add(player)
        db.add(AnticheatViolation(
            player_uuid=player.uuid, player_name="Etho", check_name="Killaura",
            verbose="suspicious hit pattern", vl=15,
        ))
        await db.commit()

        results = await execute_tool_calls(
            _ctx(db, {"players.view"}),
            [{"tool": "get_anticheat_violations", "player_uuid": player.uuid}],
        )
        rows = results[0].result
        assert len(rows) == 1
        assert rows[0]["check_name"] == "Killaura"
        assert rows[0]["vl"] == 15


@pytest.mark.asyncio
async def test_get_anticheat_violations_truncates_long_verbose_text(db_session):
    async with db_session() as db:
        player = Player(uuid="66666666-6666-6666-6666-666666666666", username="Iskall")
        db.add(player)
        db.add(AnticheatViolation(
            player_uuid=player.uuid, player_name="Iskall", check_name="Speed",
            verbose="x" * 500, vl=1,
        ))
        await db.commit()

        results = await execute_tool_calls(
            _ctx(db, {"players.view"}),
            [{"tool": "get_anticheat_violations", "player_uuid": player.uuid}],
        )
        assert len(results[0].result[0]["verbose"]) == 200


# ---------------------------------------------------------------------------
# execute_tool_calls — cross-cutting behavior
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unknown_tool_name_returns_error_not_exception(db_session):
    async with db_session() as db:
        results = await execute_tool_calls(
            _ctx(db, {"players.view"}, is_superuser=True), [{"tool": "delete_everything"}]
        )
        assert "unknown tool" in results[0].result


@pytest.mark.asyncio
async def test_multiple_tool_calls_in_one_request_all_execute(db_session):
    """One bad/unauthorized call among several must not prevent the others
    from executing — each result is independent."""
    async with db_session() as db:
        db.add(Player(uuid="77777777-7777-7777-7777-777777777777", username="Bdubs"))
        await db.commit()

        results = await execute_tool_calls(
            _ctx(db, {"players.view"}),  # no punishments.view
            [
                {"tool": "lookup_player", "username": "Bdubs"},
                {"tool": "get_punishment_history", "player_uuid": "77777777-7777-7777-7777-777777777777"},
            ],
        )
        assert len(results) == 2
        assert results[0].result["username"] == "Bdubs"  # succeeded
        assert "error" in results[1].result  # denied, but didn't block results[0]


def test_format_tool_results_block_delimits_output():
    results = [ToolCallResult(tool="lookup_player", args={"username": "Steve"}, result={"uuid": "abc"})]
    block = format_tool_results_block(results)
    assert block.startswith("<tool_results>")
    assert block.endswith("</tool_results>")
    assert "lookup_player" in block
    assert "abc" in block
