# DISPATCH: Phase 15 Frontend — Player Profile Page + Appeals Decision UI

**Type:** Sub-chat (write access)
**Scope:** `umbrella-dashboard-CURRENT/` only
**Write PAT:** [WRITE_PAT — see head chat]
**Read-only PAT:** [READ_ONLY_PAT — see head chat]
**Repo:** https://github.com/sepisotoni/UmbrellaOS
**Tip at dispatch time:** 185fe32

---

## Context

Read before touching anything:
- `PHASE15-SPEC.md` — full spec, especially Features 1, 2, 3
- `umbrella-dashboard-CURRENT/src/lib/api.ts` — API client
- `umbrella-dashboard-CURRENT/src/components/moderation/ModerationView.tsx` — existing moderation UI patterns
- `umbrella-dashboard-CURRENT/src/components/verification/VerificationView.tsx` — existing table patterns
- `umbrella-dashboard-CURRENT/src/services/dataAdapters.ts` — existing adapters

**Important:** Backend A and B are running in parallel. Assume these endpoints exist:
- `GET /api/v1/players/{uuid}/full-profile`
- `POST /api/v1/appeals/{id}/close` — body: `{ action, staff_note?, new_expiry? }`
- `POST /api/v1/ai/review/appeal/{id}` — updated with full context
- `POST /api/v1/ai/review/player/{uuid}` — updated with GrimAC history

If any endpoint 404s, show a graceful error state — never crash the UI.

Commit after every task. Push to main after each commit.
Do NOT touch `umbrella-core-CURRENT/`.

---

## Task 1 — Add full profile API call

**File:** `umbrella-dashboard-CURRENT/src/lib/api.ts`

Add:
```typescript
getPlayerFullProfile(uuid: string): Promise<PlayerFullProfile>
// GET /api/v1/players/{uuid}/full-profile

closeAppeal(id: string, action: string, staffNote?: string, newExpiry?: string): Promise<Appeal>
// POST /api/v1/appeals/{id}/close

reviewAppealAI(id: string): Promise<AIReviewResult>
// POST /api/v1/ai/review/appeal/{id}

reviewPlayerAI(uuid: string): Promise<PlayerAIReview>
// POST /api/v1/ai/review/player/{uuid}
```

Add corresponding TypeScript types to `src/types/dashboard.ts`:
```typescript
interface PlayerFullProfile {
  player: PlayerDetail
  verification: VerificationLink | null
  punishment_history: Punishment[]
  anticheat_history: {
    total_flags: number
    by_check: Record<string, { count: number; avg_vl: number; max_vl: number }>
    timeline: AnticheatFlag[]
  }
  appeal_history: Appeal[]
  alt_accounts: AltAccount[]
}

interface AIReviewResult {
  recommendation: 'ACCEPT' | 'REDUCE_SENTENCE' | 'REJECT' | 'ESCALATE' | 'SCHEDULE_REVIEW'
  confidence: number
  reasoning: string
  punishment_context: string
  flag_summary: string | null
  risk_factors: string[]
  mitigating_factors: string[]
}

interface PlayerAIReview {
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  confidence: number
  reasoning: string
  recommendation: 'MONITOR' | 'WARN' | 'TEMP_BAN' | 'PERMANENT_BAN' | 'FALSE_POSITIVE'
  key_findings: string[]
  mitigating_factors: string[]
}
```

---

## Task 2 — Player Profile page

**File:** `umbrella-dashboard-CURRENT/src/components/players/PlayerProfileView.tsx` (new file)

This is a full page component shown when a player row is clicked. It replaces the current player detail modal/sheet if one exists, or is a new route/modal.

Layout: tabbed card page with 5 tabs.

**Header (above tabs):**
- Player username (large, bold)
- UUID (small, muted, copyable)
- Status badge (Online/Offline based on last_seen)
- Risk score badge (colour coded: LOW=green, MEDIUM=yellow, HIGH=orange, CRITICAL=red)
- "AI Review" button — calls `reviewPlayerAI(uuid)`, shows result in a side panel (see Task 3)

**Tab 1 — Overview:**
- First seen, last seen, playtime
- Verification status (Discord username if linked, "Not verified" if not)
- Alt accounts count with link to Alts tab
- Active punishment count

**Tab 2 — Punishments:**
- Full punishment history table: type badge, reason, issued by, date, status, expires_at
- "Issue Punishment" button — opens existing punishment modal
- Revoke button per active punishment

**Tab 3 — Anticheat:**
- Summary cards row: total flags, unique checks triggered, most flagged check
- "By Check" breakdown: each check as a row with count, avg VL, max VL, progress bar
- Timeline table: check name, VL, verbose string, timestamp (last 50)
- Filter by check name (client-side)
- "View Evidence" deep link per flag: filters timeline to ±10 min window

**Tab 4 — Appeals:**
- Appeal history list: punishment linked, appeal text excerpt, submitted date, status badge, outcome
- "Submit Appeal" button (for staff submitting on player's behalf)

**Tab 5 — Alts:**
- Alt account cards: username, UUID, confidence score, cluster type
- "Mark False Positive" button per alt

Loading state: skeleton cards while fetching.
Error state: error card if profile fetch fails — show UUID and "Profile unavailable" message.

---

## Task 3 — Player AI Review result panel

**File:** `umbrella-dashboard-CURRENT/src/components/players/PlayerAIReviewPanel.tsx` (new file)

A side panel (Sheet component) that opens when "AI Review" is clicked on a player profile.

States:
1. **Loading** — "Analyzing player data..." spinner
2. **Error** — "AI review failed — [reason]" with a "Re-review" button
3. **Result** — show:
   - Risk level badge (prominent, colour coded)
   - Confidence percentage
   - Reasoning text
   - Recommendation badge
   - Key findings list (bullet points, red icons)
   - Mitigating factors list (bullet points, green icons)
   - "Re-review" button (always shown at bottom)

---

## Task 4 — Update Appeals view with AI decision UI

**File:** `umbrella-dashboard-CURRENT/src/components/moderation/AppealDetailPanel.tsx` (new file, or inline in AppealView if simpler)

When a staff member opens an appeal, show a panel with:

**Appeal info section:**
- Player name + UUID link to player profile
- Original punishment (type, reason, issued by, date)
- Appeal text (full)
- Submitted date
- Current status badge

**AI Review section:**
- If `ai_review_status === "COMPLETED"` — show result card:
  - Prominent recommendation badge: e.g. `✅ RECOMMEND: ACCEPT`
  - Confidence score
  - Reasoning
  - Punishment context ("First offence — no prior bans")
  - GrimAC context if present
  - Risk factors list (red)
  - Mitigating factors list (green)
- If `ai_review_status === "FAILED"` — show error card with "Re-review" button
- If `ai_review_status === null` — show "AI Review" button that calls `reviewAppealAI(id)`
- If loading — spinner with "Analyzing appeal..."

**Action buttons (always visible, like Claude web UI):**
Five buttons in a row, each triggers `closeAppeal()` with the relevant action:
- ✅ Accept Appeal
- ⏳ Reduce Sentence (opens date picker for new_expiry before calling)
- 📞 Schedule Review Call
- ⬆️ Escalate to Senior Staff
- ❌ Reject Appeal

On action taken:
- Optimistically update UI
- Show success toast: "Appeal #[id] — [action] by [staff username]"
- Refresh appeal list

**If appeal is already closed** — show the case summary prominently at the top:
```
✅ ACCEPTED — Appeal #A-0042
[case summary text]
Handled by: Notch | 22 Aug 2026
```
Action buttons are hidden for closed appeals.

---

## Task 5 — Wire View Evidence deep link

**File:** `umbrella-dashboard-CURRENT/src/components/moderation/ModerationView.tsx`

In the punishments table, if `issuer === "GrimAC AutoMod"` or `issuer === "GrimAC"`:
- Show "View Evidence" link next to the punishment row
- Link opens the player profile (Task 2) at the Anticheat tab, filtered to ±10 min around `punishment.created_at`
- Pass as props: `defaultTab="anticheat"`, `filterFrom={banTime - 10min}`, `filterTo={banTime + 10min}`

---

## Task 6 — Update Appeals list view

**File:** `umbrella-dashboard-CURRENT/src/components/moderation/AppealView.tsx` or wherever appeals are listed

Update the appeals list to:
- Show `action_taken` as the card header for closed appeals: `✅ ACCEPTED`, `❌ REJECTED` etc.
- Show `ai_review_status` badge: "AI Reviewed", "AI Failed", "Pending AI" 
- Clicking an appeal opens the AppealDetailPanel from Task 4
- Colour code status badges: OPEN=blue, ACCEPTED=green, REJECTED=red, ESCALATED=orange, REVIEW_SCHEDULED=purple

---

## Code Standards

- Dark navy/purple theme, match existing component patterns exactly
- All new API calls in `src/lib/api.ts`
- New types in `src/types/dashboard.ts`
- Data adapters in `src/services/dataAdapters.ts`
- Loading: skeleton or spinner matching existing patterns
- Error: red border card with message and retry button
- No new npm dependencies
- Read files lazily — only the section you need

---

## Commit Instructions

- `dashboard: add full profile API calls and types (P15 Task 1)`
- `dashboard: add player profile page with 5 tabs (P15 Task 2)`
- `dashboard: add player AI review panel (P15 Task 3)`
- `dashboard: add appeal detail panel with AI decision UI (P15 Task 4)`
- `dashboard: wire View Evidence deep link in punishments (P15 Task 5)`
- `dashboard: update appeals list with close state and AI status (P15 Task 6)`

When done write `dispatches/PHASE15-FRONTEND/SUBCHAT-HANDBACK.md` with all commits, decisions, and any endpoints that 404d.
