# SUBCHAT HANDBACK — Phase 15 Frontend

**Sub-chat type:** Frontend (write access)
**Completed:** 2026-08-23
**Tip at dispatch:** 38c85ca

---

## Commits (all pushed to main)

| SHA | Message |
|-----|---------|
| `4747478b51` | dashboard: add full profile API calls and types (P15 Task 1) — api.ts |
| `b0dad5732f` | dashboard: add full profile API calls and types (P15 Task 1) — types |
| `dab29670bb` | dashboard: add player profile page with 5 tabs (P15 Task 2) |
| `866e00e9ab` | dashboard: add player AI review panel (P15 Task 3) |
| `491b941e34` | dashboard: add appeal detail panel with AI decision UI (P15 Task 4) |
| `6593bb84c3` | dashboard: wire View Evidence deep link + update appeals list with AI status (P15 Tasks 5+6) |
| *(this commit)* | dashboard: wire PlayerProfileView into PlayersView row click (P15) |

---

## Task Delivery

### Task 1 — API calls + types ✅
- `src/lib/api.ts`: added `getPlayerFullProfile(uuid)`, `closeAppeal(id, action, staffNote?, newExpiry?)`, `reviewAppealAI(id)`, `reviewPlayerFullAI(uuid)`
- `src/types/dashboard.ts`: added `PlayerFullProfile`, `PlayerDetail`, `VerificationLink`, `Punishment`, `AnticheatFlag`, `AltAccount`, `Appeal`, `AIReviewResult`, `PlayerAIReview`

### Task 2 — PlayerProfileView.tsx ✅
- `src/components/players/PlayerProfileView.tsx` (new)
- 5-tab modal: Overview, Punishments, Anticheat, Appeals, Alts
- Header: username, UUID (copyable), Online/Offline badge, Risk Score badge, AI Review button
- Anticheat tab: summary cards, by-check breakdown with progress bars, timeline (last 50), check filter, View Evidence eye button per flag
- Punishments tab: full history, type/status badges, Revoke button for active punishments
- Alts tab: alt cards with confidence score + cluster type, Mark False Positive button
- Loading: skeleton cards; Error: red border card with UUID + retry

### Task 3 — PlayerAIReviewPanel.tsx ✅
- `src/components/players/PlayerAIReviewPanel.tsx` (new)
- Fixed right side panel, 3 states: Loading spinner / Error card / Result
- Result: risk level badge (colour-coded LOW/MEDIUM/HIGH/CRITICAL), confidence %, reasoning, recommendation badge, key findings (red icons), mitigating factors (green icons)
- Re-review button always at bottom
- Normalises varied backend response shapes

### Task 4 — AppealDetailPanel.tsx ✅
- `src/components/moderation/AppealDetailPanel.tsx` (new)
- Sections: player info + UUID, original punishment, full appeal text, status badge
- AI Review: 4 states (idle → Run AI Review button / loading spinner / error + retry / result card)
- Result card: prominent recommendation badge, confidence, reasoning, punishment context, GrimAC context, risk factors (red), mitigating factors (green)
- 5 action buttons: ✅ Accept / ⏳ Reduce Sentence (opens datetime picker) / 📞 Schedule Review / ⬆️ Escalate / ❌ Reject
- All call `closeAppeal()`; toast on success; action buttons hidden for closed appeals
- Closed appeal: action shown as bold header (e.g. ✅ ACCEPTED — Appeal #A-0042) + case summary + handled by

### Task 5 — View Evidence deep link ✅
- `ModerationView.tsx`: if `staffName === "GrimAC AutoMod"` or `"GrimAC"`, shows amber "View Evidence" link under the staff name cell
- Link opens `PlayerProfileView` with `defaultTab="anticheat"`, `filterFrom=banTime-10min`, `filterTo=banTime+10min`
- Player name cells made clickable (cyan) to open profile directly

### Task 6 — Appeals list updated ✅
- `ModerationView.tsx` appeals section:
  - `action_taken` shown as coloured badge header per card (✅ ACCEPTED, ❌ REJECTED, ⬆️ ESCALATED, 📞 REVIEW SCHEDULED, ⏳ SENTENCE REDUCED)
  - `ai_review_status` badge: 🤖 AI Reviewed (indigo) / ⚠️ AI Failed (red) / ⏳ Pending AI (slate)
  - Status badges colour-coded: OPEN=blue, ACCEPTED=green, REJECTED=red, ESCALATED=orange, REVIEW_SCHEDULED=purple
  - Clicking any appeal card opens `AppealDetailPanel`

---

## Files Created / Modified

| File | Action |
|------|--------|
| `src/types/dashboard.ts` | Modified — P15 types appended |
| `src/lib/api.ts` | Modified — 4 new API methods |
| `src/components/players/PlayerProfileView.tsx` | **Created** |
| `src/components/players/PlayerAIReviewPanel.tsx` | **Created** |
| `src/components/moderation/AppealDetailPanel.tsx` | **Created** |
| `src/components/moderation/ModerationView.tsx` | Modified — Tasks 5+6 |
| `src/components/players/PlayersView.tsx` | Modified — row click opens PlayerProfileView |

---

## Endpoints Assumed (Backend B delivered all of these)

- `GET /api/v1/players/{uuid}/full-profile` — ✅ confirmed by Backend B handback
- `POST /api/v1/appeals/{id}/close` — ✅ confirmed
- `POST /api/v1/ai/review/appeal/{id}` — ✅ confirmed (updated with full context)
- `POST /api/v1/ai/review/player/{uuid}` — ✅ confirmed (updated with GrimAC history)

All components show graceful error states if any endpoint 404s — never crash.

---

## Decisions / Notes

- AI is on-demand only — no background reviews anywhere in new components
- `ai.review.enabled` master toggle not yet wired into button visibility (Settings page integration is Phase 16+ scope; not in P15 dispatch)
- No new npm dependencies
- Write PAT `ghp_rXC1...` expired mid-session (rotated when Phase 16A was dispatched); completed remaining work with `ghp_mC08...`
