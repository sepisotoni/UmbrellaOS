# UmbrellaOS

A custom Minecraft server administration platform, built for Sepiso
Toni's community server. Backend (`umbrella-core`), Discord bot
(`umbrella-discord`), dashboard (`umbrella-dashboard`), and a
from-scratch Paper/Java plugin (not yet started).

This project is developed across many separate chat sessions. If
you're a person: start with `MASTER-PROJECT-STATUS-AND-HANDOFF.md`.
If you're an AI assistant picking this project up: **read `CLAUDE.md`
first, it's the actual entry point for you.**

## Where things are

| Doc | What it's for |
|---|---|
| `CLAUDE.md` | Start here if you're an AI session. Points everywhere else. |
| `MASTER-PROJECT-STATUS-AND-HANDOFF.md` | "Where we are" — full narrative status, current phase, what to do next. |
| `PROJECT-PRINCIPLES-AND-WORKING-RULES.md` | "How we work" — the non-negotiable rules (verify independently, don't trust self-reports, scope discipline). Read before touching anything. |
| `PHASE-STATUS-CORRECTED.md` | The actual, sourced phase-by-phase status, with confidence markers. More reliable than any summary table. |
| `phase10/UMBRELLAOS_MASTER_ROADMAP_v3_CONSOLIDATED.md` | "What's planned" — full 13-phase roadmap and definition-of-done per phase. |
| `CRITICAL-FINDINGS-2026-08-17.md` | Open, unresolved, high-priority bugs. Read before starting new feature work. |
| `dispatches/` | Every prior scoped sub-chat dispatch and its handback. |
| `cross-chat-findings/` | Independent review docs, including live-Postgres functional testing. |
| `historical-reference/` | Narrative record of complications and false starts. Context only — never a starting point to build from. |

## Repo / access

Real git history exists from **2026-08-15 onward** (see D4 in the
working-rules doc) — nothing before that is in `git log`, only in the
handoff docs. Only the head chat session holds write access; sub-chats
get read-only (D5).
