"""
services/ai/copilot_tools.py — Tool-calling for the AI copilot.

[HEAD → CURSOR, 2026-09-01] The copilot had zero tools wired to actual DB
endpoints — every provider call was a single-shot text completion, so the
model could only ask clarifying questions instead of fetching data
(confirmed live: "show me PlayerX's punishments" got a request for more
detail rather than an actual answer).

Design: none of the three providers' generate() wrap a native function-
calling API in this codebase (services/ai/base.py's HTTPProvider is a
plain single-turn request/response) — adding real tool-calling per-provider
(each with its own different function-call schema: Gemini's functionCall,
Anthropic's tool_use blocks, OpenRouter's OpenAI-compatible tools param)
would be a much larger, more invasive change to orchestrator.py and every
provider file, for a task that's currently only used by one low-stakes,
read-only endpoint. Instead: a text-based two-pass protocol that works
identically across every provider without touching any of them.

Pass 1: ask the model to decide, in a fenced ```json block, which of a
small fixed toolset (if any) would help answer the question, with a plain-
text early exit if no tool applies (most questions — "what's the ban
policy for X" — don't need one).
Pass 2 (only if tools were requested): execute each requested tool as a
direct, permission-scoped DB query — NOT a capability invocation, since
none of the read-only lookups this needs (player lookup, punishment
history, anticheat violations) exist as capabilities yet (confirmed via
grep before writing this — the closest matches, player_risk.score and
anticheat.violations.purge_old, do something else entirely) — then feed
the results back to the model for a final natural-language answer.

Every tool result is capped and summarized before going back into the
prompt (see _MAX_ROWS) so a "show me everything" question can't balloon
into a multi-thousand-row prompt. Tool execution respects the caller's
CallContext: a caller without players.view sees an explicit permission-
denied result for that tool, not a silent empty list or a bypass.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.player import Player, Punishment
from models.anticheat_violation import AnticheatViolation
from registry.context import CallContext

_MAX_ROWS = 20  # cap on rows returned per tool call, keeps the pass-2 prompt bounded

# Permission required to use each tool — checked against the caller's
# CallContext before the query runs, not just documented in a docstring.
# Matches the real permission keys in services/roles_service.py: players.view
# for player-record reads, punishments.view for punishment reads (a distinct
# permission — checked before assuming players.view covered it). Anticheat
# violations have no dedicated read permission of their own yet, so they
# fall under players.view same as the player record itself.
_TOOL_PERMISSIONS = {
    "lookup_player": "players.view",
    "get_punishment_history": "punishments.view",
    "get_anticheat_violations": "players.view",
}

_TOOLS_MANIFEST = """Available tools (respond with a JSON array in a ```json fenced block to call one or more; respond with plain text and no JSON block if no tool is needed):

- {"tool": "lookup_player", "username": "<name>"} — find a player's UUID, risk score, suspicion score, first/last seen, playtime.
- {"tool": "get_punishment_history", "player_uuid": "<uuid>"} — list a player's bans/mutes/kicks/warnings, most recent first.
- {"tool": "get_anticheat_violations", "player_uuid": "<uuid>"} — list a player's recent GrimAC/anticheat flags, most recent first.

If you need a player's UUID for get_punishment_history or get_anticheat_violations and only have a username, call lookup_player first — you can request multiple tools in the same JSON array and their results will all be given back to you together."""

# [CURSOR, 2026-09-02] Human-readable version of the same three tools for the
# /commands intercept in ai_copilot.py — kept as a plain list literal (not
# parsed out of _TOOLS_MANIFEST) so a change to one doesn't have to be
# re-derived from awkward string parsing of the other; small enough that
# keeping both in sync by eye is easy, and this is checked by
# test_copilot_tools.py::test_available_tools_list_matches_manifest_count.
AVAILABLE_TOOLS_DESCRIPTION = [
    ("lookup_player", "Look up a player by username — UUID, risk score, suspicion score, playtime, first/last seen."),
    ("get_punishment_history", "List a player's bans/mutes/kicks/warnings, most recent first."),
    ("get_anticheat_violations", "List a player's recent GrimAC/anticheat flags, most recent first."),
]


@dataclass
class ToolCallResult:
    tool: str
    args: dict[str, Any]
    result: Any  # JSON-serializable — a dict, list, or error string


def build_tool_selection_prompt(user_question_block: str) -> str:
    """The pass-1 prompt: the model's own question context plus the tool manifest."""
    return f"{user_question_block}\n\n{_TOOLS_MANIFEST}"


def parse_requested_tools(model_text: str) -> list[dict[str, Any]] | None:
    """Extracts a ```json [...] fenced block from the model's pass-1 response.

    Returns None if no fenced JSON array is present (the model answered
    directly, no tools needed — the common case). Malformed JSON inside a
    fenced block is also treated as "no tools" rather than raising, since a
    parse failure here shouldn't crash the whole request — pass 1's own
    text is still a usable answer on its own if pass 2 never runs.
    """
    match = re.search(r"```json\s*(\[.*?\])\s*```", model_text, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list):
        return None
    return [item for item in parsed if isinstance(item, dict) and "tool" in item]


async def execute_tool_calls(
    ctx: CallContext, requested: list[dict[str, Any]]
) -> list[ToolCallResult]:
    """Runs each requested tool as a direct, permission-scoped query.

    Uses ctx.db for every query — matches the established pattern every
    capability handler in this codebase already follows (CallContext is the
    single source of truth for "which session is this call using," per its
    own docstring: "capability handler's own queries share this session/
    transaction"). Does not take a separate db parameter.

    Unknown tool names and permission failures both produce a
    ToolCallResult with an error string in `result` rather than raising —
    the model gets to see "you don't have permission for X" or "unknown
    tool Y" as part of its context for the final answer, same as it would
    see any other tool failure, rather than the whole request 500ing over
    one bad or unauthorized tool call among several.
    """
    db = ctx.db
    results: list[ToolCallResult] = []
    for call in requested:
        tool = call.get("tool")
        required_perm = _TOOL_PERMISSIONS.get(tool)
        if required_perm is None:
            results.append(ToolCallResult(tool=str(tool), args=call, result=f"error: unknown tool {tool!r}"))
            continue
        if not ctx.has_permission(required_perm):
            results.append(ToolCallResult(
                tool=tool, args=call,
                result=f"error: caller lacks required permission {required_perm!r} for this tool",
            ))
            continue

        try:
            if tool == "lookup_player":
                result = await _lookup_player(db, call.get("username", ""))
            elif tool == "get_punishment_history":
                result = await _get_punishment_history(db, call.get("player_uuid", ""))
            elif tool == "get_anticheat_violations":
                result = await _get_anticheat_violations(db, call.get("player_uuid", ""))
            else:
                result = f"error: unknown tool {tool!r}"
        except Exception as exc:
            # A tool failing (bad uuid format, DB hiccup) shouldn't crash the
            # whole copilot request — surface it as data for pass 2 instead.
            result = f"error: tool execution failed: {exc}"

        results.append(ToolCallResult(tool=tool, args=call, result=result))
    return results


def format_tool_results_block(results: list[ToolCallResult]) -> str:
    """Renders tool results as a delimited block for the pass-2 prompt —
    same untrusted-input-delimiting pattern as the rest of this file
    (AUDIT-VERIFICATION-2026-08-29 #8): tool output can contain player-
    submitted strings (usernames, punishment reasons), so it's wrapped and
    labeled data, not concatenated as plain text."""
    lines = ["<tool_results>"]
    for r in results:
        lines.append(f"  {r.tool}({json.dumps(r.args)}):")
        lines.append(f"    {json.dumps(r.result, default=str)}")
    lines.append("</tool_results>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Individual tool implementations — direct DB queries, not capability calls
# (see module docstring for why: no matching read-only capability exists yet)
# ---------------------------------------------------------------------------

async def _lookup_player(db: AsyncSession, username: str) -> dict[str, Any] | str:
    if not username:
        return "error: username is required"
    result = await db.execute(select(Player).where(Player.username.ilike(username)))
    player = result.scalar_one_or_none()
    if player is None:
        return f"no player found with username {username!r}"
    return {
        "uuid": player.uuid,
        "username": player.username,
        "risk_score": player.risk_score,
        "suspicion_score": player.suspicion_score,
        "playtime_minutes": player.playtime,
        "first_seen": player.first_seen.isoformat() if player.first_seen else None,
        "last_seen": player.last_seen.isoformat() if player.last_seen else None,
    }


async def _get_punishment_history(db: AsyncSession, player_uuid: str) -> list[dict[str, Any]] | str:
    if not player_uuid:
        return "error: player_uuid is required"
    result = await db.execute(
        select(Punishment)
        .where(Punishment.player_uuid == player_uuid)
        .order_by(Punishment.created_at.desc())
        .limit(_MAX_ROWS)
    )
    rows = result.scalars().all()
    if not rows:
        return f"no punishment history for player {player_uuid}"
    return [
        {
            "type": p.type,
            "reason": p.reason,
            "staff_id": p.staff_id,
            "status": p.status,
            "active": p.active,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "expires_at": p.expires_at.isoformat() if p.expires_at else None,
        }
        for p in rows
    ]


async def _get_anticheat_violations(db: AsyncSession, player_uuid: str) -> list[dict[str, Any]] | str:
    if not player_uuid:
        return "error: player_uuid is required"
    result = await db.execute(
        select(AnticheatViolation)
        .where(AnticheatViolation.player_uuid == player_uuid)
        .order_by(AnticheatViolation.timestamp.desc())
        .limit(_MAX_ROWS)
    )
    rows = result.scalars().all()
    if not rows:
        return f"no anticheat violations for player {player_uuid}"
    return [
        {
            "check_name": v.check_name,
            "vl": v.vl,
            "verbose": v.verbose[:200] if v.verbose else "",  # cap: verbose can be long free text
            "timestamp": v.timestamp.isoformat() if v.timestamp else None,
        }
        for v in rows
    ]
