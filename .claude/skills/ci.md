# CI / GitHub Actions

## Workflows
- Backend CI: pytest on every push to main — needs Postgres + Redis
- Plugin CI: mvn test — needs Java 21, Paper API, GrimAPI from repo.grim.ac
- Dashboard CI: tsc --noEmit build check
- Bot CI: pytest on umbrella-discord-CURRENT/ changes — uses fake token/key env vars
- Vercel: auto-deploys on push (two projects: umbrella-dashboard, umbrella-os)

## Before pushing
- Backend: make sure tests pass locally in shared sandbox (see SHARED-TEST-SANDBOX.md)
- Plugin: `mvn compile` must succeed with Java 21
- Dashboard: `tsc --noEmit` must pass (0 errors)

## Known CI gotchas
- Redis must be running for rate_limit_service tests — CI uses Docker service now
- cyclonedx-python-lib must be in requirements.txt for test_dependency_scanning
- GrimAPI is fetched from repo.grim.ac/snapshots — if that's down, plugin CI fails
- Plugin pom.xml targets Java 21 — don't use Java 25 syntax

## If CI is red
Fix it before moving on. The test suite is the source of truth.
