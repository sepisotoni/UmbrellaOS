# UmbrellaOS Claude Skills

Skill files are short focused docs that any chat can read on demand instead of being fed a giant prompt upfront. Chats should read relevant skills before starting work and update them when they learn something new.

## Available Skills
| File | When to read |
|---|---|
| architecture.md | Before touching any cross-subsystem code |
| auth-protocol.md | Before touching any auth/plugin key code |
| database.md | Before writing migrations or DB queries |
| ci.md | Before pushing — check what CI expects |
| plugin-api.md | Before adding plugin-facing endpoints |
| coordination.md | First thing every chat reads on startup |

## Rules
- Read before you work, not after
- Update when you discover something new
- Keep each file SHORT — these are quick references not novels
- If a skill is wrong, fix it immediately
