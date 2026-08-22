# DISPATCH: Phase 14 — Dashboard Quality & Fit Audit

**Type:** Sub-chat (read-only — no commits, no code changes)
**Read-only PAT:** [READ_ONLY_PAT — see head chat]
**Repo:** https://github.com/sepisotoni/UmbrellaOS
**Tip at dispatch time:** 914fba0

---

## Your job

Read the dashboard and the backend. Produce a single document called `PHASE14-QUALITY-AUDIT.md`.

Do NOT write code. Do NOT commit anything. Output the completed doc as a file artifact.

---

## What to read first

**Dashboard (React SPA — Vite/TypeScript):**
The dashboard is in the zip uploaded by the head chat — it is NOT yet in the repo. You will be given access to it as a zip. Read every file:
- `src/lib/api.ts` — every API call the dashboard makes
- `src/context/DashboardContext.tsx` — all data fetching logic
- `src/services/dataAdapters.ts` — how backend data is transformed
- `src/types/dashboard.ts` — all TypeScript types
- `src/components/*/` — every view component
- `BACKEND_REQUIREMENTS.md` — what Gemini says the backend needs
- `docs/AI_DIAGNOSTICS_CAPABILITIES.md` — the AI multi-provider spec
- `docs/BACKEND_PLUGIN_ARCHITECTURE.md` — plugin architecture spec

**Backend (umbrella-core — FastAPI/Python):**
- `umbrella-core-CURRENT/api/routers/` — every router file
- `umbrella-core-CURRENT/main.py` — what's mounted and at what prefix
- `umbrella-core-CURRENT/capabilities/` — if it exists, what capabilities are registered
- `umbrella-core-CURRENT/services/` — to understand what business logic exists

---

## What to produce

### Section 1 — Page-by-page fit assessment

For each of the 17 dashboard views, answer:
- **What it does** (1-2 sentences)
- **Backend fit** — does the backend actually support this? What's there, what's missing?
- **Verdict** — one of:
  - ✅ Good fit — backend supports it, page makes sense
  - ⚠️ Partial fit — some backend support, gaps noted
  - ❌ Poor fit — backend doesn't support this, needs significant backend work
  - 🔄 Redesign candidate — page exists but could be done better given what the backend actually does

Pages to assess:
1. Overview
2. Players
3. Topology (nodes/infrastructure)
4. Console (WebSocket terminal)
5. Moderation (punishments, appeals, GrimAC violations)
6. AI Intelligence (multi-provider copilot, crash triage, model router)
7. Discord (chat bridge, embed builder, slash commands, webhooks)
8. Plugins (plugin heartbeats, upload, enable/disable)
9. Snapshots (server checkpoints, rollback)
10. Staff (Discord members, roles, permissions)
11. Audit/Logs (structured log viewer)
12. Verification (Discord↔MC link management)
13. Translation (UI locale/string management)
14. Automation (cron jobs, scheduled tasks)
15. API Hub (webhooks, API keys)
16. Settings (backend config, feature flags, AI keys)
17. Login

---

### Section 2 — What's genuinely bloat or wrong-fit

Be honest. If something doesn't make sense for a Minecraft network admin dashboard, or requires so much backend work it's not worth it at this stage, call it out. Include:
- Feature/page name
- Why it's wrong-fit or bloat
- Recommendation: cut it, simplify it, or defer it

Don't be aggressive — the dashboard is good. But if something is fundamentally misaligned with what this project actually is, flag it.

---

### Section 3 — Useful features not in the dashboard that could be added

Given what the backend CAN already do (from reading the routers), are there useful things the backend supports that the dashboard doesn't expose at all? List them with:
- Feature name
- Which backend endpoint supports it
- Why it's useful for a Minecraft network

---

### Section 4 — AI capabilities reality check

The `docs/AI_DIAGNOSTICS_CAPABILITIES.md` describes a sophisticated 6-provider failover system. Compare this against what actually exists in:
- `umbrella-core-CURRENT/api/routers/ai_tasks.py`
- `umbrella-core-CURRENT/api/routers/ai_config.py`
- Any other AI-related files in core

Answer:
- What AI capabilities does the backend actually have right now?
- What does the dashboard's AI view assume exists that doesn't?
- What's the gap between the spec doc and reality?
- What's realistic to build vs what's aspirational?

---

### Section 5 — Discord features reality check

The Discord view has: chat bridge, embed builder, slash command management, webhook config, bot status.

The bot (`umbrella-discord`) has 11 cogs. Cross-reference:
- Which Discord features in the dashboard map to real bot cogs?
- Which assume bot capabilities that don't exist yet?
- What does the bot do that the dashboard doesn't expose?

---

### Section 6 — Schema mismatches

Where the dashboard's TypeScript types or API calls don't match what the backend actually returns. Be specific:
- Dashboard expects field X, backend returns field Y
- Dashboard calls endpoint A with method B, backend has it at method C
- Dashboard type has field that doesn't exist in backend schema

---

### Section 7 — Priority ranking

Given all of the above, rank the work needed in order of impact:
1. Things to fix before first real use (blockers)
2. Things that would make it significantly better (high value)
3. Things that are nice-to-have (low priority)
4. Things to cut or defer

---

## Output format

Single markdown file `PHASE14-QUALITY-AUDIT.md`. Be specific and direct. No filler. If you don't know something because a file wasn't readable, say so explicitly rather than guessing.
