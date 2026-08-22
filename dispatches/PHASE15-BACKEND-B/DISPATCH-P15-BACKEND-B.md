# DISPATCH: Phase 15 Backend B — Player Profile, Appeal Close, AI Review

**Type:** Sub-chat (write access)
**Scope:** `umbrella-core-CURRENT/` only
**Write PAT:** [WRITE_PAT — see head chat]
**Read-only PAT:** [READ_ONLY_PAT — see head chat]
**Repo:** https://github.com/sepisotoni/UmbrellaOS
**Tip at dispatch time:** 185fe32

---

## Context

Read before touching anything:
- `PHASE15-SPEC.md` — full phase spec, especially Feature 1 and Feature 3
- `umbrella-core-CURRENT/api/routers/players.py` — existing player routes
- `umbrella-core-CURRENT/api/routers/appeals.py` — existing appeal routes
- `umbrella-core-CURRENT/api/routers/ai_tasks.py` — existing AI review routes
- `umbrella-core-CURRENT/models/` — all existing models
- `umbrella-core-CURRENT/services/` — all existing services
- `umbrella-core-CURRENT/main.py` — mounted routers

**Important:** Backend A (running in parallel) is adding the `AnticheatViolation` model and table. Assume it exists — import from `models.anticheat_violation` and query `AnticheatViolation`. If it's not merged yet when you run, note it in the handback and stub the anticheat section with an empty list fallback.

Commit after every task. Push to main after each commit.
Do NOT touch `umbrella-dashboard-CURRENT/`.

---

## Task 1 — Full player profile endpoint

**File:** `umbrella-core-CURRENT/api/routers/players.py`

Add:
```
GET /api/v1/players/{uuid}/full-profile
```

This is a single aggregated endpoint — one call, all player data. Response shape (see PHASE15-SPEC.md Feature 1 for full schema):

```json
{
  "player": { "uuid", "username", "first_seen", "last_seen", "playtime", "current_server", "risk_score", "suspicion_score" },
  "verification": { "discord_id", "discord_username", "linked_at", "status" } | null,
  "punishment_history": [...],
  "anticheat_history": {
    "total_flags": int,
    "by_check": { "CheckName": { "count": int, "avg_vl": float, "max_vl": int } },
    "timeline": [{ "check_name", "vl", "verbose", "timestamp" }]
  },
  "appeal_history": [...],
  "alt_accounts": [...]
}
```

Implementation:
- Query player from DB — 404 if not found
- Query verification link for this player_uuid
- Query all punishments for this player_uuid ordered by created_at desc
- Query AnticheatViolation for this player_uuid (last 30 days), group by check_name for `by_check`, return last 50 as timeline
- Query appeals for this player_uuid
- Query alt detection results for this player_uuid
- Assemble and return — do NOT make separate HTTP calls, query DB directly
- Use `asyncio.gather()` for parallel DB queries where possible

---

## Task 2 — Update Appeal model with close fields

**File:** `umbrella-core-CURRENT/models/appeal.py` (or wherever Appeal is defined)

Add fields to the Appeal model:
```python
action_taken: str | None = None  # ACCEPT | REDUCE_SENTENCE | REJECT | ESCALATE | SCHEDULE_REVIEW
handled_by: str | None = None    # staff username
case_summary: str | None = None  # auto-generated on close
closed_at: datetime | None = None
ai_review_status: str | None = None  # PENDING | COMPLETED | FAILED
ai_review_result: dict | None = None  # JSON blob of AI output
```

Write an Alembic migration for these new columns. DO NOT run it — just write the file.

---

## Task 3 — Appeal close endpoint

**File:** `umbrella-core-CURRENT/api/routers/appeals.py`

Add:
```
POST /api/v1/appeals/{id}/close
```

Body:
```json
{
  "action": "ACCEPT | REDUCE_SENTENCE | REJECT | ESCALATE | SCHEDULE_REVIEW",
  "staff_note": "string | null",
  "new_expiry": "ISO8601 | null"
}
```

Implementation:
- Fetch appeal by id — 404 if not found
- Execute the action:
  - `ACCEPT` → find the linked punishment, set `active=False`, set `status="PARDONED"`
  - `REDUCE_SENTENCE` → update `punishment.expires_at = new_expiry` (required if action is REDUCE_SENTENCE)
  - `REJECT` → set appeal status to REJECTED
  - `ESCALATE` → set appeal status to ESCALATED
  - `SCHEDULE_REVIEW` → set appeal status to REVIEW_SCHEDULED
- Auto-generate case summary string:
```
Appeal #{id} — Closed [{date}]
Player: {username} | Punishment: {punishment_type} ({punishment_reason})
Action Taken: {action}
Handled by: {staff_username}
Notes: {staff_note or "None"}
```
- Save `action_taken`, `handled_by`, `case_summary`, `closed_at=now()` to appeal record
- Write to audit log
- Return updated appeal

---

## Task 4 — Update AI appeal review to use full context

**File:** `umbrella-core-CURRENT/api/routers/ai_tasks.py` or `services/ai/`

Update `POST /api/v1/ai/review/appeal/{id}` to pull rich context before calling AI:

1. Fetch the appeal + original punishment
2. Fetch player's full punishment history (count, types, dates)
3. Fetch player's AnticheatViolation records in ±72hr window around punishment created_at
4. Fetch player's previous appeals if any

Build a structured context string (NOT raw logs):
```
APPEAL REVIEW CONTEXT
=====================
Appeal: #{id} | Submitted: {date}
Player: {username} ({uuid})
Original Punishment: {type} | Reason: {reason} | Issued by: {staff} on {date}

Player History:
- Total punishments: {n} ({breakdown by type})
- Previous appeals: {n} ({outcomes})

GrimAC Context (±72hr around punishment):
- {check_name}: {count} flags, VL {min}-{max}, avg {avg}
[or "No GrimAC flags in this window"]

Appeal Statement:
{appeal_text}
```

Send to AI with system prompt:
```
You are UmbrellaOS Appeal Reviewer. Analyze this Minecraft server ban appeal objectively.
Return JSON only:
{
  "recommendation": "ACCEPT|REDUCE_SENTENCE|REJECT|ESCALATE|SCHEDULE_REVIEW",
  "confidence": 0.0-1.0,
  "reasoning": "2-3 sentences",
  "punishment_context": "first offence / repeat offender summary",
  "flag_summary": "GrimAC context or null",
  "risk_factors": ["list"],
  "mitigating_factors": ["list"]
}
```

Save result to `appeal.ai_review_result`, set `appeal.ai_review_status = "COMPLETED"`.
On AI failure: set `appeal.ai_review_status = "FAILED"`, return 503 with error — never fake a result.

---

## Task 5 — Update AI player review to use GrimAC history

**File:** same as Task 4

Update `POST /api/v1/ai/review/player/{uuid}` to use structured GrimAC context:

1. Fetch player record
2. Fetch AnticheatViolation records for this player (last 30 days)
3. Fetch punishment history

Build structured summary (target: under 500 tokens):
```
PLAYER REVIEW CONTEXT
=====================
Player: {username} ({uuid})
First seen: {date} | Last seen: {date}

GrimAC History (last 30 days):
- Total flags: {n}
- By check: {CheckName}: {count} flags, VL {min}-{max}, avg {avg}
- VL escalation: [timeline of when VL crossed thresholds]
- Notable flags: [up to 5 most significant verbose strings]

Punishment History:
- {n} total | {breakdown}
```

Send to AI with system prompt:
```
You are UmbrellaOS Player Risk Assessor for a Minecraft server.
Analyze this player's anticheat data and history objectively.
Return JSON only:
{
  "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
  "confidence": 0.0-1.0,
  "reasoning": "2-3 sentences",
  "recommendation": "MONITOR|WARN|TEMP_BAN|PERMANENT_BAN|FALSE_POSITIVE",
  "key_findings": ["list of specific concerning patterns"],
  "mitigating_factors": ["list"]
}
```

On AI failure: return 503 with error — never fake a result.

---

## Commit Instructions

- `core: add GET /api/v1/players/{uuid}/full-profile (P15 Task 1)`
- `core: add appeal close fields + migration (P15 Task 2)`
- `core: add POST /api/v1/appeals/{id}/close (P15 Task 3)`
- `core: update appeal AI review with full context (P15 Task 4)`
- `core: update player AI review with GrimAC history (P15 Task 5)`

When done write `dispatches/PHASE15-BACKEND-B/SUBCHAT-HANDBACK.md` with all commits, decisions, and any stubs made due to Backend A not being merged yet.
