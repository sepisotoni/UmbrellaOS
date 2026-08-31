# UmbrellaOS

A Minecraft server management platform — FastAPI backend, React dashboard, Discord bot, and Paper plugin working together.

## Stack

| Component | Tech | Hosted |
|---|---|---|
| Core API | FastAPI + PostgreSQL | Render |
| Dashboard | React + Vite + Tailwind | Vercel |
| Discord Bot | discord.py | HeavenCloud |
| Minecraft Plugin | Java + Paper 1.21.4 | BisectHosting |
| Database | Supabase (PostgreSQL) | Supabase |

## Branches

| Branch | Purpose |
|---|---|
| `main` | Production code only |
| `docs` | Historical docs, dispatches, audit reports, handoffs |
| `archive` | Important things that shouldn't be on main |

## Active Coordination

Multi-chat development is coordinated via [`CHAT-COORDINATION.md`](./CHAT-COORDINATION.md).
Each chat has an ID (`[HEAD]`, `[AUTH]`, `[PLAYER]` etc.) and prefixes all commits with it.
Chats post cross-chat notices and file claims in the coordination file.

## Key Files

- `CHAT-COORDINATION.md` — active multi-chat coordination
- `CLAUDE.md` — working rules and principles
- `PROJECT-PRINCIPLES-AND-WORKING-RULES.md` — architecture principles
- `UMBRELLA-PLUGIN-ARCHITECTURE.md` — plugin integration reference
- `SHARED-TEST-SANDBOX.md` — shared pytest environment setup
- `umbrella-core-CURRENT/docs/` — ADRs and design docs

## Commit Convention

```
[CHATID] scope(area): description
[AUTH] fix(auth): use hmac.compare_digest instead of ==
[HEAD] chore: remove stale dispatch docs
```
