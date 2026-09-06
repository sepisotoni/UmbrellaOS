# UmbrellaOS

A Minecraft server management platform — FastAPI backend, React dashboard,
Discord bot, and Paper plugin working together.

## Stack

| Component | Tech | Hosted |
|---|---|---|
| Core API | FastAPI + PostgreSQL | Render |
| Dashboard | React + Vite + Tailwind | Vercel |
| Discord Bot | discord.py | HeavenCloud |
| Minecraft Plugin | Java + Paper 1.21.4 | BisectHosting |
| Database | Supabase PostgreSQL | Supabase |

## Live URLs

- Dashboard: https://umbrella-os-phi.vercel.app
- Core API: https://umbrellaos-core.onrender.com

## Branches

| Branch | Purpose |
|---|---|
| `main` | Production code only |
| `docs` | Historical docs, audit reports, handoffs |
| `archive` | Important things that shouldn't be on main |

## CI Status

5 checks run on every push to main:
- **Backend CI** — pytest (FastAPI core)
- **Bot CI** — pytest (discord.py bot)
- **Plugin CI** — mvn test (Java plugin)
- **Dashboard CI** — tsc build check
- **Vercel** — auto-deploy (dashboard + core)

## Multi-Chat Coordination

Active development uses multiple parallel Claude chats, each owning a subsystem.
Coordination happens via [`CHAT-COORDINATION.md`](./CHAT-COORDINATION.md).

| Chat ID | Subsystem |
|---|---|
| `[HEAD]` | Orchestration |
| `[PLUGIN]` | Plugin & Server subsystem |
| `[DASH]` | Dashboard frontend |
| `[CURSOR]` | Settings / Knowledge / Webhooks / Bridge |
| `[BOT]` | Discord bot cogs |

Each chat prefixes commits with its ID: `[DASH] fix(staff): role badge colors`

## Skill Files

Short reference docs for each subsystem at [`.claude/skills/`](./.claude/skills/).
Chats read these instead of being fed large prompts. Updated as the project evolves.

## Quick Start (for new chats)

```bash
git clone https://ghp_...@github.com/sepisotoni/UmbrellaOS.git
cat CLAUDE.md                          # read this first
git diff ORIG_HEAD -- CHAT-COORDINATION.md  # read coordination diff
cat .claude/skills/README.md           # find relevant skill files
```
