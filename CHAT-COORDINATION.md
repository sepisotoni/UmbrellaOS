# UmbrellaOS — Multi-Chat Coordination File

---

## Chat ID Registry
| ID | Subsystem | Model |
|---|---|---|
| [HEAD] | Orchestration | Claude Sonnet 4.6 |
| [AUTH] | Auth & Permissions | Claude Sonnet 4.6 |
| [PLAYER] | Player / Moderation / Appeals | Claude Sonnet 4.6 |
| [BOT] | Bot Cogs & Core Client | Claude Sonnet 4.6 |
| [AI] | AI Subsystem | Claude Sonnet 4.6 |
| [CURSOR] | Settings / Knowledge / Webhooks | Claude Sonnet 4.6 |
| [PLUGIN] | Plugin & Server subsystem | TBD |
| [DASH] | Dashboard frontend | TBD |

---

## Protocol

**On first clone/startup:** read this entire file once.

**On every subsequent `git pull`:** only check what changed:
```bash
git diff ORIG_HEAD -- CHAT-COORDINATION.md
```
Only read new lines — don't re-read the whole file. Token efficient.

**Commits:** prefix every commit with your chat ID:
`[AUTH] fix(auth): use hmac.compare_digest`

**Before editing a file:** claim it in Files Being Edited below.
**When done:** remove your claim.

**Found a bug outside your subsystem?** Don't fix it — post a notice and leave it.

**Push often** — after every logical group of fixes, not all at once at the end.

---

## Addressing in Cross-Chat Notices
```
[BOT → PLAYER]        # direct to one chat
[BOT → ALL]           # broadcast to everyone
[AUTH → HEAD]         # escalate to orchestrator
[PLAYER → AUTH,BOT]   # multi-target
```
[HEAD] reads all notices and coordinates if needed.

---

## Cross-Chat Notices
<!-- Append only — never delete old notices -->

[HEAD → ALL] .venv was committed and removed (commit b2cd284). If tracked locally: git rm -r --cached umbrella-core-CURRENT/.venv/
[HEAD → ALL] SSH keypair removed (commit 76f9f50). Not registered anywhere, no revocation needed.
[HEAD → ALL] Master bug report: AUDIT-VERIFICATION-2026-08-29-MASTER-BUG-REPORT.md — mark fixes as you go.
[HEAD → ALL] capabilities/shared.py created at commit d5679d1 — pull past this before referencing it.
[HEAD → CURSOR] Previous Cursor session hit usage limit. New Claude chat taking [CURSOR] slot — pick up unfixed Settings/Knowledge/Webhooks/Bridge/Verification findings from master report.

---

## Files Currently Being Edited
<!-- [CHATID] path/to/file — remove when done -->
[PLAYER] umbrella-core-CURRENT/api/routers/appeals.py
[PLAYER] umbrella-core-CURRENT/tests/conftest.py
[PLAYER] umbrella-core-CURRENT/tests/test_appeals.py
[PLAYER] umbrella-core-CURRENT/tests/test_moderation_intelligence.py

---

## Completed Work
- [AUTH] auth.py, rate_limit.py, waf.py, verification.py, feature_flags.py — bugs #1 #6 #25 #27
- [AI] capabilities/shared.py created, investigation.py, knowledge.py, memory.py — bugs #60 #62 #63 #64 #72 #85
- [CURSOR] models/anticheat_violation.py, audit_log.py, memory.py, plugin_execution.py — indexes + FK fixes
- [HEAD] Removed .venv and SSH keypair
