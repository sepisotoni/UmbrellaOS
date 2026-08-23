# DISPATCH: Dashboard Deployment to Vercel

**Type:** Sub-chat (write access + Vercel)
**Scope:** Deploy `umbrella-dashboard-CURRENT/` to Vercel
**Write PAT:** [WRITE_PAT — see head chat]
**Repo:** https://github.com/sepisotoni/UmbrellaOS
**Tip:** 7a8110b
**Vercel token:** [VERCEL_TOKEN — see head chat]
**Vercel team ID:** team_jxYs3eCsymnBsVpR7sBO1ueu

---

## Context

The dashboard is a **React + Vite SPA** at `umbrella-dashboard-CURRENT/`. It needs to be deployed to Vercel as a static site. Use the Vercel MCP tools — do NOT use the codespace for this.

Build command: `npm run build`
Output directory: `dist`
Root directory: `umbrella-dashboard-CURRENT`
Framework: Vite

---

## Task 1 — Check what env vars the dashboard needs

Read `umbrella-dashboard-CURRENT/src/lib/api.ts` — find how `UMBRELLA_CORE_URL` or any other env vars are referenced (look for `import.meta.env` calls). List every env var the dashboard reads.

---

## Task 2 — Create Vercel project linked to repo

Use `create_git_project` to link `sepisotoni/UmbrellaOS` to Vercel:
- Project name: `umbrella-dashboard`
- Root directory: `umbrella-dashboard-CURRENT`
- Team ID: `team_jxYs3eCsymnBsVpR7sBO1ueu`

---

## Task 3 — Set environment variables

After project is created, set whatever env vars Task 1 found. At minimum:
- `VITE_UMBRELLA_CORE_URL` = `https://umbrellaos-core.onrender.com`

Use `update_environment_variables` on the new project.

---

## Task 4 — Trigger deployment and verify

Check deployment status. Once live, report the production URL.

---

## Handback

Write `dispatches/PHASE16-DASHBOARD-DEPLOY/SUBCHAT-HANDBACK.md` with:
- Production URL
- Env vars set
- Any build errors encountered
- Anything the head chat needs to do manually
