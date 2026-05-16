# Security Audit — Phase 3 Readiness Sprint

**Date:** 2026-05-16
**Author:** BRAIN_MANAGER (Phase 3 Readiness Sprint)
**Scope:** RLS posture on Supabase tables + secrets posture in the repo.

This is a read-only audit. No schema changes were made in this sprint per the
sprint's "no schema changes without explicit approval" rule.

## TL;DR

- `.env` is gitignored. No secrets committed in this sprint.
- Migration-defined tables (`runs`, `aleksandra_timeline`, `evidence_ledger`,
  `kv_state`, `paper_chunks`) have correctly scoped RLS policies that grant
  read access only to `authenticated` and write access only to `service_role`.
- **Pre-existing exposure:** The base medical tables defined in
  `scripts/schema.sql` (`papers`, `therapies`, `pathways`, `brain_regions`,
  `hypotheses`, `contacts`, `relationships`, `clinical_trials`,
  `ingestion_log`, `discovery_reports`) have RLS *enabled* but the policy
  `"Service role full access" FOR ALL USING (true)` is missing a `TO
  service_role` clause. Without an explicit role target, PostgreSQL applies
  the policy to PUBLIC, which includes the `anon` role. The viewer routes
  always use the service-role key, so the family-facing app is unaffected;
  however, anyone with the Supabase project's *anon* key could currently
  `SELECT *` from these tables via the REST API.
- Phase 2.5 verifier C.2 confirms that `/rest/v1/runs` correctly rejects anon
  access. C.2 does not test the older base-schema tables.

## Evidence Snapshot

### Secrets

- `.env` is matched by `.gitignore` (`git check-ignore .env` returned
  `.env`).
- No `*.env` file other than `.env.example` is tracked.
- `.env.example` was updated this sprint to include `CLOUDFLARE_R2_ENDPOINT`,
  matching what `scripts/ledger.py` expects.

### RLS — migration-defined tables (CORRECTLY SCOPED)

| Table | Migration | Read policy target | Write policy target |
| --- | --- | --- | --- |
| `runs` | `001_runs_append_only.sql` | `authenticated` | `service_role` |
| `aleksandra_timeline` | `002_aleksandra_timeline.sql` | `authenticated` | `service_role` (insert + update) |
| `evidence_ledger` | `003_evidence_ledger.sql` | `authenticated` | `service_role` |
| `kv_state` | `004_kv_state.sql` | `authenticated` | `service_role` |
| `paper_chunks` | `005_paper_chunks.sql` | `authenticated` | `service_role` |

These match the canonical Supabase RLS pattern. No action needed.

### RLS — base-schema tables (NOT CORRECTLY SCOPED)

In `scripts/schema.sql`:

```sql
CREATE POLICY "Service role full access" ON papers FOR ALL USING (true);
CREATE POLICY "Service role full access" ON therapies FOR ALL USING (true);
CREATE POLICY "Service role full access" ON pathways FOR ALL USING (true);
CREATE POLICY "Service role full access" ON brain_regions FOR ALL USING (true);
CREATE POLICY "Service role full access" ON hypotheses FOR ALL USING (true);
CREATE POLICY "Service role full access" ON contacts FOR ALL USING (true);
CREATE POLICY "Service role full access" ON relationships FOR ALL USING (true);
CREATE POLICY "Service role full access" ON clinical_trials FOR ALL USING (true);
CREATE POLICY "Service role full access" ON ingestion_log FOR ALL USING (true);
CREATE POLICY "Service role full access" ON discovery_reports FOR ALL USING (true);
```

The policy name is misleading: there is no `TO service_role` clause, so the
policy applies to PUBLIC. With RLS enabled and a PUBLIC permissive policy,
any client using the `anon` key can read these tables.

The viewer routes are unaffected because they use the service-role key
server-side. The risk is the *Supabase anon key*, which is intended for
direct browser/anon access.

### Severity Assessment

- **Family PHI:** None of these tables contain Aleksandra's MRI/DICOM data.
  Imaging data is client-side only and never leaves the browser. So this is
  not a HIPAA blast radius event for the protected MRI corpus.
- **Soft PHI:** `contacts` may contain clinician names and email addresses,
  and `aleksandra_timeline` rows (already correctly scoped) reference
  clinical visits. The `contacts` exposure under a leaked anon key is the
  most sensitive item here.
- **Confidentiality:** Internal `hypotheses`, `discovery_reports`, and
  `ingestion_log` were not designed for public read.
- **Likelihood:** Moderate. Exposure requires possession of the project's
  Supabase anon key, which is typically embedded in any deployed frontend.
  If the family viewer is ever publicly served, the anon key is recoverable
  from page source.

**Classified severity:** Medium (pre-existing, not introduced by this sprint).

## Recommendation

This sprint **does not** modify `scripts/schema.sql`. A targeted Phase 3
follow-up sprint should:

1. Write a migration `008_base_schema_rls_scope.sql` that drops the unscoped
   `"Service role full access"` policies and re-creates them as:

   ```sql
   DROP POLICY "Service role full access" ON papers;
   CREATE POLICY papers_service_all ON papers
     FOR ALL TO service_role USING (true) WITH CHECK (true);
   CREATE POLICY papers_family_read ON papers
     FOR SELECT TO authenticated USING (true);
   ```

   …and so on for each of the ten base tables.

2. Extend `verify_phase2_5` (or add `verify_phase3` C-class gates) to assert
   that anon `SELECT` on each base table returns HTTP 401/403, mirroring the
   existing C.2 check.

3. Rotate the Supabase anon key after the migration to invalidate any cached
   copies in deployed clients.

## Secret-Scan Posture

The repo's secret-scan path is not exercised in this sprint, but spot checks:

- No `sk-ant-` substrings outside `.env.example` placeholder.
- No Telegram bot tokens (`/bot[0-9]+:`) committed.
- No `*.pem`, `*.key`, or `*.p12` files committed.

A formal secret-scan run on the working tree should be part of the Phase 3
implementation entry checklist.

## Sign-off

Issued by BRAIN_MANAGER for the Phase 3 Readiness Sprint. No code or schema
changes follow from this audit; only documentation of the current posture
and the recommended remediation path.
