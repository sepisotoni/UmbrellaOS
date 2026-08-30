# UmbrellaOS — Multi-Chat Coordination File

> Every chat (Claude, Cursor, Gemini, etc.) MUST read this file immediately after every `git pull`.
> If you find something another chat should know, append it to Cross-Chat Notices below.
> Claim files you are actively editing to avoid merge conflicts.
> Use your chat ID prefix on every git commit: e.g. `[AUTH] fix: ...`

---

## Chat ID Registry
| ID | Subsystem | Model |
|---|---|---|
| [HEAD] | Orchestration / this chat | Claude Sonnet 4.6 |
| [AUTH] | Auth & Permissions | Claude Sonnet 4.6 |
| [PLAYER] | Player / Moderation / Appeals | Claude Sonnet 4.6 |
| [BOT] | Bot Cogs & Core Client | Claude Sonnet 4.6 |
| [AI] | AI Subsystem | Claude Sonnet 4.6 |
| [CURSOR] | Settings / Knowledge / Webhooks | Grok 4.6 Medium |
| [PLUGIN] | Plugin & Server subsystem | TBD |
| [DASH] | Dashboard frontend | TBD |

---

## Protocol
1. `git pull` → read this file → then start work
2. Before editing a file, add it to **Files Being Edited** below
3. When done with a file, remove it from that section
4. Commit format: `[CHATID] scope(area): description` e.g. `[AUTH] fix(auth): use hmac.compare_digest`
5. Push after every logical group of fixes — don't batch everything into one push at the end
6. If you find a bug outside your subsystem, add it to **Cross-Chat Notices** — don't fix it yourself

---

## Cross-Chat Notices
<!-- Append here when you find something another chat owns. Format: [FROM → TO] description -->

[HEAD → ALL] .venv was committed and has been removed (commit b2cd284). If your local clone has umbrella-core-CURRENT/.venv/ tracked, run: git rm -r --cached umbrella-core-CURRENT/.venv/
[HEAD → ALL] SSH keypair id_ed25520 / id_ed25520.pub was committed and removed (commit 76f9f50). Key is not registered anywhere so no revocation needed.
[HEAD → ALL] Master bug report lives at AUDIT-VERIFICATION-2026-08-29-MASTER-BUG-REPORT.md — mark your fixes in that file as you go.
[HEAD → ALL] capabilities/shared.py did not exist until commit d5679d1 — if you reference it, make sure you have pulled past that commit.

---

## Files Currently Being Edited
<!-- Claim files here before editing. Remove when done. -->
<!-- Format: [CHATID] path/to/file.py -->

---

## Recently Completed Work (summary)
- [AUTH] auth.py, rate_limit.py, waf.py, verification.py, feature_flags.py — bugs #1 #6 #25 #27 fixed
- [AI] capabilities/shared.py created, investigation.py, knowledge.py, memory.py fixed — bugs #60 #62 #63 #64 #72 #85 fixed
- [CURSOR] models/anticheat_violation.py, audit_log.py, memory.py, plugin_execution.py — indexes + FK fixes
- [HEAD] Removed .venv and SSH keypair from repo
