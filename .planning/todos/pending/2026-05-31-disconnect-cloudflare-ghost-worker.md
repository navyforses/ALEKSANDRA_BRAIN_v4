---
status: pending
created: 2026-05-31
resolves_phase: maintenance
source: CLAUDE.md MEMORY layer note ("ghost Cloudflare Worker `aleksandrabrane4` slated for disconnect")
owner: Shako (operator — requires Cloudflare dashboard access)
priority: P2 (CI noise; not blocking any phase, but every PR shows a red ❌)
estimated_window: 5 minutes (one Cloudflare dashboard click + verify next PR)
related_pr: navyforses/ALEKSANDRA_BRAIN_v4#3, #4 (both observed the failure)
---

# Disconnect ghost Cloudflare Worker `aleksandrabrane4`

## Context

When Phase 1 provisioned the Cloudflare side of the stack, **Workers KV** was the planned hot cache for n8n workflow state, URL dedup keys, and the Firecrawl spend ledger. A Worker service `aleksandrabrane4` was created in the Cloudflare account `414a50c18fa76da1f07ea9d3b62af7bc` and connected to this Git repository for auto-deploy on every push.

KV was deprecated on **2026-05-21**. Phase 1–3 absorbed all three KV roles into Supabase Postgres:
- URL dedup → `papers` UNIQUE constraints
- Workflow state → `runs` table
- Firecrawl budget cap → `runs.cost_usd` ledger + `scripts/cognition/budget.py`

The Worker was never given source code (no `wrangler.toml`, no `worker.js`, no `/cloudflare/` dir in the repo — verified 2026-05-31). On every push, Cloudflare Workers Builds:

1. Clones the repo.
2. Fails to auto-detect a Worker project.
3. Falls back to `pip install -r requirements.txt` — pulling CrewAI 1.14, Graphiti 0.29, Neo4j 6.2, Qdrant 1.18, fastembed 0.8, biopython, nibabel, pillow, lxml, psycopg2-binary, etc.
4. Build fails (Workers runtime cannot host this dependency tree).

Net effect: every PR carries a permanent ❌ from `Workers Builds: aleksandrabrane4`, and Cloudflare burns ~30 seconds of build time on each push for nothing.

## What to do

Open Cloudflare dashboard:

https://dash.cloudflare.com/414a50c18fa76da1f07ea9d3b62af7bc/workers/services/view/aleksandrabrane4/production/

Then **either**:

### Option A — Disconnect Git integration only (preserves the empty Worker)

1. **Settings** → **Builds** → **Disconnect repository**.
2. Confirm. No more builds triggered by repo pushes.

Use this if there's any chance you'll re-attach a different repo to this Worker later.

### Option B — Delete the Worker service entirely (recommended)

1. **Settings** → **Delete service**.
2. Type the service name to confirm.

The Worker is empty, has no traffic, has no KV/R2/D1 bindings worth preserving (the only related binding — KV — is already deprecated). Deletion is the clean end-state.

## Done criteria

- The next PR opened against `main` does NOT show a `Workers Builds: aleksandrabrane4` check (or it shows `skipped`).
- `mcp__github__pull_request_read` with `method=get_check_runs` on the next PR returns 4 checks instead of 5 (Vercel Preview Comments, Supabase Preview, viewer/ imaging boundary, gitleaks).
- Update CLAUDE.md MEMORY-layer note: change "ghost Cloudflare Worker `aleksandrabrane4` slated for disconnect" → "ghost Cloudflare Worker `aleksandrabrane4` deleted 2026-MM-DD".
- Move this file from `.planning/todos/pending/` to `.planning/todos/completed/`.

## Why this is not urgent

The failure is cosmetic — every CI failure on this worker has been a false signal for ~10 days and the team has correctly learned to ignore it. No phase blocks on it. But it adds friction for any new contributor (or future you) reviewing PR status, and it consumes a small amount of Cloudflare free-tier build minutes per push.

## What it costs to leave it

- Every PR shows ❌ next to the merge button — operator must visually parse 5 checks to confirm "only the ghost failed."
- Cloudflare free tier build minutes consumed (small).
- Future risk: if Cloudflare changes auto-detect heuristics, the build could start succeeding accidentally and deploy something unintended. Disconnect is the durable fix.
