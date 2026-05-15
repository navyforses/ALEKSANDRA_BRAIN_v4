-- ─────────────────────────────────────────────────────────────────────────────
-- 007_runs_token_cost_precision.sql — Phase 2.5 sub-phase 2.5A
--
-- Bumps runs.token_cost precision from NUMERIC(10, 4) to NUMERIC(14, 8).
--
-- Why: at NUMERIC(10, 4) the smallest non-zero value is $0.0001. A single
-- Anthropic Haiku 4.5 call that consumes < ~60 tokens (0.80/M input +
-- 4.00/M output USD) computes a cost below $0.0001 and truncates to $0
-- on store. Phase 2's bulk Sonnet calls were $0.03+ each so the floor
-- never bit them, but Phase 2.5B will fire ~140 Haiku calls (70 papers ×
-- entity extraction + relevance scoring) — many small ones — and the
-- audit gap we just closed (commit 7db305e) would silently re-open as
-- under-reporting drift. NUMERIC(14, 8) supports $0.00000001 granularity,
-- which captures even a single-token Haiku call.
--
-- This is a column-type widening (10,4 -> 14,8). Postgres accepts it
-- without rewriting rows when the new type is wider; existing values are
-- preserved exactly. The append-only triggers (runs_no_update,
-- runs_no_delete) installed in migration 001 are NOT affected by
-- ALTER COLUMN ... TYPE — triggers fire on UPDATE/DELETE, not on DDL.
--
-- Re-runnable: the DO block checks the current numeric_precision /
-- numeric_scale on information_schema.columns and skips if already
-- ≥ (14, 8).
-- ─────────────────────────────────────────────────────────────────────────────

DO $$
DECLARE
    cur_prec integer;
    cur_scale integer;
BEGIN
    SELECT numeric_precision, numeric_scale
    INTO cur_prec, cur_scale
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name   = 'runs'
      AND column_name  = 'token_cost';

    IF cur_prec IS NULL THEN
        RAISE NOTICE '007: runs.token_cost column not found; skipping.';
        RETURN;
    END IF;

    IF cur_prec >= 14 AND cur_scale >= 8 THEN
        RAISE NOTICE '007: runs.token_cost already at NUMERIC(%, %) — no-op.',
            cur_prec, cur_scale;
        RETURN;
    END IF;

    RAISE NOTICE '007: widening runs.token_cost from NUMERIC(%, %) to NUMERIC(14, 8).',
        cur_prec, cur_scale;

    ALTER TABLE public.runs
        ALTER COLUMN token_cost TYPE NUMERIC(14, 8);
END
$$;
