# PHASE 15 SPEC — Player Profiles, Anticheat AI Review, Appeals Decision UI

**Status:** Planned — not yet dispatched
**Depends on:** Phase 14 frontend fixes complete, Phase 14 backend fixes complete

---

## Overview

Three interconnected features that form a unified moderation intelligence system:
1. Full player profile page
2. GrimAC violation storage + AI cheat review
3. Appeals AI analysis + decision UI with case summaries

---

## Feature 1 — Full Player Profile

### Backend

**New endpoint:** `GET /api/v1/players/{uuid}/full-profile`

Single aggregated response — dashboard makes one call, not 6. Returns:
```json
{
  "player": { "uuid", "username", "first_seen", "last_seen", "playtime", "current_server", "risk_score", "suspicion_score" },
  "verification": { "discord_id", "discord_username", "linked_at", "status" },
  "punishment_history": [ { "id", "type", "reason", "staff_name", "created_at", "expires_at", "status", "appeal_id" } ],
  "anticheat_history": { "total_flags", "by_check": { "Reach": { "count": 23, "avg_vl": 4.2, "max_vl": 18 } }, "timeline": [ { "check_name", "vl", "verbose", "timestamp" } ] },
  "appeal_history": [ { "id", "punishment_id", "status", "created_at", "action_taken", "handled_by", "ai_recommendation" } ],
  "alt_accounts": [ { "uuid", "username", "confidence", "cluster_type" } ]
}
```

### Dashboard

Player detail view redesigned as a tabbed profile page:
- **Overview tab** — basic info, risk score, verification status, alt count
- **Punishments tab** — full punishment history table, issue new punishment button
- **Anticheat tab** — GrimAC flag history grouped by check, VL timeline chart, "AI Review" button
- **Appeals tab** — appeal history with outcomes, "Submit Appeal" button (for staff creating one on player's behalf)
- **Alts tab** — linked alt accounts with confidence scores, false-positive button

---

## Feature 2 — GrimAC Violation Storage + AI Cheat Review

### Backend — Dedicated violation table

**New migration:** `AnticheatViolation` table:
```sql
id, player_uuid, player_name, server_id, check_name, verbose, vl, timestamp
```

Update `anticheat_service.handle_cheat_flag()` to write to this table instead of shoehorning into `AITask` rows.

Update plugin to send `server_id` in the flag payload (`POST /api/v1/anticheat/flag` body gains `server_id` field).

Update `GET /api/v1/anticheat/violations` to query the new table — `server_id` filter becomes functional.

### Backend — AI cheat review

Update `POST /api/v1/ai/review/player/{uuid}` to:
1. Pull player's `AnticheatViolation` history (last 30 days)
2. Build structured summary before sending to AI — NOT raw logs:
   - Flag counts grouped by check name
   - VL progression timeline (when did VL escalate, how fast)
   - Notable verbose strings (actual cheat detail from GrimAC)
   - Context: total playtime, first seen, punishment history count
3. Send structured summary as AI context (target: under 500 tokens of input)
4. Return: `{ risk_assessment, recommendation, confidence, flag_summary, reasoning }`

### Log filtering rules (before any AI call)
- Strip: chat messages, heartbeat lines, tick noise, repetitive identical lines (collapse to "N similar lines omitted")
- Keep: errors, warnings, stack traces, GrimAC flags, connection events, plugin errors, authentication events
- Cap: last 200 relevant lines max, or last 24 hours whichever is smaller
- Pre-summarise: if same check fires >10 times, collapse to "Reach: 23 flags (VL 2-18, avg 4.2)"

---

## Feature 3 — Appeals AI Analysis + Decision UI

### Backend

Update appeal AI review (`POST /api/v1/ai/review/appeal/{id}`) to pull full context before AI call:
- The appeal text itself
- Original punishment (type, reason, issuing staff)
- Player's **full punishment history** (is this first offence or 5th ban?)
- Player's **GrimAC flags** around the time of the ban (±72hr window) — was it cheat-related?
- Player's **previous appeals** if any (have they appealed, been accepted, then reoffended?)

AI output schema:
```json
{
  "recommendation": "ACCEPT | REDUCE_SENTENCE | REJECT | ESCALATE | SCHEDULE_REVIEW",
  "confidence": 0.0-1.0,
  "reasoning": "2-3 sentence explanation",
  "flag_summary": "GrimAC context if relevant",
  "punishment_context": "First offence / repeat offender summary",
  "risk_factors": ["list of things that went against the player"],
  "mitigating_factors": ["list of things that went for the player"]
}
```

New field on `Appeal` model: `action_taken` (what staff actually did), `handled_by` (staff username), `case_summary` (auto-generated on close), `closed_at`.

New endpoint: `POST /api/v1/appeals/{id}/close`
Body: `{ action: "ACCEPT | REDUCE_SENTENCE | REJECT | ESCALATE | SCHEDULE_REVIEW", staff_note?: string, new_expiry?: ISO8601 }`

On close:
- Executes the action (revokes punishment if ACCEPT, updates expiry if REDUCE_SENTENCE, etc.)
- Auto-generates case summary and saves to appeal record
- Notifies player via Discord bot if linked
- Writes to audit log

### Dashboard — Decision UI

After AI review completes, show a result card:

**Header (prominent):** AI recommendation badge — e.g. `✅ RECOMMEND: ACCEPT`

**Body:**
- Confidence score (e.g. "87% confidence")
- Reasoning (2-3 sentences from AI)
- Punishment context ("First offence — no prior bans")
- GrimAC context if relevant ("No cheat flags in 72hr window around ban")
- Risk factors list
- Mitigating factors list

**Action buttons (like Claude web UI — tap one to execute):**
- ✅ Accept Appeal
- ⏳ Reduce Sentence (opens date picker for new expiry)
- 📞 Schedule Review Call (flags for manual staff interview)
- ⬆️ Escalate to Senior Staff
- ❌ Reject Appeal

On action taken — auto-generates and saves case summary, shows confirmation.

**Closed appeal card header format:**
```
✅ ACCEPTED — Appeal #A-0042
```
Action is the header. Summary below. Outcome visible immediately when scanning appeal list.

**Case summary format (saved to DB, shown in player profile):**
```
Appeal #A-0042 — Closed [2026-08-22]
Player: Steve | Punishment: 30-day ban (Hacking)
AI Analysis: No GrimAC flags in 72hr window. First offence. Genuine remorse.
AI Recommendation: Accept (87% confidence)
Action Taken: Accept Appeal
Handled by: Notch
```

---

## Phase Sequencing

This is one phase (Phase 15) with three tracks that can be partially parallelised:

1. **Backend Track A** — AnticheatViolation migration + updated flag storage + plugin server_id field
2. **Backend Track B** — Full player profile endpoint + updated AI review functions + appeal close endpoint  
3. **Frontend Track** — Player profile page redesign + appeals decision UI (depends on A+B)
4. **Test** — End-to-end: flag a player in-game → see in dashboard → AI review → appeal → decision

---

## Notes

- Discord bot needs to be deployed before appeal notifications work (Phase 16 dependency)
- The log filtering rules apply to ALL AI calls that read server logs, not just cheat review
- `server_id` in anticheat flags requires a plugin update — coordinate with plugin phase
- Appeal `SCHEDULE_REVIEW_CALL` action just sets a flag on the appeal — the actual scheduling is out of scope for now

---

## Additional Note — Configurable Verification Messages

The messages the Discord bot sends during the verification flow (DM prompts, success messages, error messages) and the in-game messages the Minecraft plugin sends (e.g. "Check your DMs for a verification code") must be configurable from the dashboard — not hardcoded in the bot or plugin.

These should be stored in the core settings table (already exists) and editable from the Settings page in the dashboard. The bot and plugin read them via `GET /api/v1/plugin/config` and `GET /api/v1/settings/{key}` respectively on startup and on reconnect.

Keys to make configurable (at minimum):
- `verification.dm_prompt` — the DM message asking the player to send their code
- `verification.success_message` — sent in DM on successful link
- `verification.error_already_linked` — if Discord already linked to another account
- `verification.error_invalid_code` — if code is wrong/expired
- `verification.ingame_prompt` — message shown in-game telling player to check their DMs
- `verification.ingame_success` — message shown in-game on successful verification
- `verification.nickname_format` — format for the Discord nickname set on verify (e.g. `{minecraft_username}` or `{minecraft_username} | {server}`)

Dashboard Settings page should have a "Verification Messages" section where staff can edit these without touching code or redeploying.

---

## Important Constraint — AI is On-Demand Only

The AI must NEVER run automatically in the background. No scheduled AI scans, no auto-flagging, no autonomous decisions.

AI only activates when a staff member explicitly clicks:
- "AI Review" on a player profile
- "AI Review" on an appeal
- "AI Crash Analysis" on a server
- The copilot send button

This applies to all phases. The AI is a staff tool, not an autonomous system.
