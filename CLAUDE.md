# Read this first — every session, no exceptions

You are joining an active multi-chat development project. Read this file
fully before touching any code.

## The one rule that matters most

**Pull before you read. Read before you write. Verify before you claim.**
Never trust a prior chat's "X is done" — run it yourself.

## First actions every session

1. `git pull` — always, before anything else
2. `git diff ORIG_HEAD -- CHAT-COORDINATION.md` — read only what changed
3. Read `.claude/skills/README.md` — find which skill files apply to your work
4. Read relevant skill files before writing any code

## Your chat ID

Every chat has an ID. Prefix every commit with it:
`[AUTH] fix(auth): use hmac.compare_digest`

Current IDs: `[HEAD]` `[PLUGIN]` `[DASH]` `[CURSOR]` `[BOT]`
See `CHAT-COORDINATION.md` for full registry and current assignments.

## Key files

| File | Purpose |
|---|---|
| `CHAT-COORDINATION.md` | Live multi-chat coordination — read diff on every pull |
| `.claude/skills/` | Short reference docs — read before working, update when you learn |
| `AUDIT-VERIFICATION-2026-08-29-MASTER-BUG-REPORT.md` | Bug tracker — mark fixes as you go |
| `SHARED-TEST-SANDBOX.md` | How to run tests in the shared codespace |

## Architecture in one paragraph

FastAPI core (Render) + React dashboard (Vercel) + discord.py bot (HeavenCloud
`e3f69e73`) + Java Paper 1.21.4 plugin (BisectHosting) + Supabase PostgreSQL.
Bot and plugin auth via PBKDF2 HMAC (WPA2-style) — never raw key comparison.
Dashboard auth via Discord OAuth session tokens. All settings changes go through
`SettingsService.update()`. All plugin-facing endpoints use `require_plugin_key()`.

## CI — watch it, fix it

5 checks run on every push: Backend CI, Bot CI, Plugin CI, Dashboard CI, Vercel.
If your commit breaks CI, fix it before moving on. Check GitHub Actions tab.

## Rules

- Read `.claude/skills/` before writing code in any subsystem
- Claim files in `CHAT-COORDINATION.md` before editing them
- Commit every logical group of fixes — don't batch everything at end
- Push after every commit — other chats need your changes
- Never commit `.venv/`, SSH keys, or secrets
- Fix CI red before starting new work
- Post cross-chat notices for bugs outside your subsystem — don't fix them yourself

## Who you're working with

Sepiso (owner) — casual typing, wants directness, runs multi-chat workflow.
One HEAD chat orchestrates, subsystem chats do the work.
