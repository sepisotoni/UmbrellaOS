# UmbrellaOS — Head Chat Handoff, 2026-08-18

Read `CLAUDE.md` first, then this doc.

---

## 1. Repo access

Repo: `https://github.com/sepisotoni/UmbrellaOS`

**Read-write PAT:**
[REDACTED — head chat write PAT, rotate on session start]

**Read-only PAT (sub-chats only):**
[REDACTED — read-only PAT for sub-chats]

Current tip: `ee5fe57` (Phase 13 Step 3: GrimAC bridge)

**Codespace:** use secondary account (Sepisoton1) — primary has billing
block ~1 week. Codespace `stunning-adventure-6v9694r9rjv4fr4vq` on
sepisotoni/UmbrellaOS, Java 17 already default. Only use for mvn
test/verification — flag before pushing from inside it.

---

## 2. What happened this session

### Committed
- Doc fixes: stale "no git repo" claims, phase status table, Phase 8
  flagged disputed, Phase 13 added, README.md + CLAUDE.md added at root
- archive branch: fixed missing /api/v1 prefix on all plugin endpoint paths
- review-6: 5 surfaces confirmed working (tempban, chat bridge,
  plugin-key writes, webhook CRUD, automation cron firing)
- Phase 13 Steps 1-3: all committed to main (see section 3)
- Bugfix sweep: scoped at dispatches/BUGFIX-SWEEP-2026-08-17.md, not started
- codespaces/bug-sweep-report.md and related: pushed directly by
  Sepiso/other sessions — read these, not fully digested yet

---

## 3. Most important open item: Phase 13 Step 3 build failure

GrimBridge.java is on main but mvn build fails — grimac:2.3.73 is not
published to any Maven repo (not repo.grim.ac, not Maven Central, not
PaperMC proxy).

Fix: Sepiso downloads Grim-2.3.73.jar from
https://github.com/GrimAnticheat/Grim/releases/tag/v2.3.73
then installs it locally:

  mvn install:install-file \
    -Dfile=/path/to/Grim-2.3.73.jar \
    -DgroupId=ac.grim.grimac \
    -DartifactId=grimac \
    -Dversion=2.3.73 \
    -Dpackaging=jar

Then mvn test should pass (11 new GrimBridgeTest tests).

**Also unresolved: Minecraft version.** Sepiso says server runs "26.2"
which is not a standard MC version. Clarify before deploying:
- Paper API dep in pom.xml is pinned to a specific MC version
- GrimAC 2.3.73 has its own supported MC version range
- Live end-to-end test (real GrimAC flag reaching core) still needed

---

## 4. Open decisions

- BanEnforcer fail-open vs fail-closed: currently banned players can
  join if core is unreachable. One-line flip to fail-closed. Ask Sepiso.
- anticheat.enabled toggle: GrimBridge ignores it currently. Easy to add.
- mute punishment type: dead vocabulary, no route writes it. Add route
  or drop from constraint.

---

## 5. Sepiso's working style

Casual abbreviated typing. Multi-chat courier workflow — you hold write
access, sub-chats get read-only. Uses Sepisoton1 codespaces while
primary billing is blocked. Will push directly to main sometimes
(merge cleanly, happened twice this session). Wants directness.

Dispatch naming: P13-S1/S2/S3 (done), BUGFIX-01 (not started).

---

## 6. Phase status

| Phase | Status |
|---|---|
| 0-10 | Done |
| 11 | Not started (clustering/HA, highest complexity) |
| 12 | Not started (installer/i18n/CI-CD) |
| 13 | Partial — code committed, build unverified, live test not done |
| Bugfix sweep | Scoped, not started |

Recommended order: bugfix sweep -> verify Phase 13 build -> Phase 11 -> Phase 12.

---

## 7. Leak investigation — resolved

Devin only had access to the old Windsurf-built version, not this
codebase. No credential rotation needed.
