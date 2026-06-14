-- 026_bilingual_ai_analysis.sql
-- Make the two family-facing AI analysis prose columns bilingual JSONB {en, ka},
-- mirroring the shape papers.title / papers.abstract already use (migration 017).
--
-- Before: ai_summary / ai_aleksandra_implications are TEXT (English only), so the
-- /ka/research surface shows English analysis text even in the Georgian locale.
-- After:  both are JSONB {en, ka}. The viewer's flatten(value, locale) already
-- renders {en, ka} and falls back across locales, so the Georgian site shows the
-- ka slot once it is backfilled (scripts/migrations/026_bilingual_ai_analysis.py).
--
-- Idempotent-by-guard: the orchestrator skips this DDL when the columns are
-- already jsonb (information_schema check), so re-running is safe. The USING
-- clause wraps each existing English string as {"en": <text>, "ka": null};
-- NULL stays NULL (papers with no analysis yet). ai_key_findings (text[]) is
-- intentionally left as-is — it is a structured list, lower priority, and can
-- stay English for now.

ALTER TABLE papers
  ALTER COLUMN ai_summary TYPE jsonb
  USING CASE
          WHEN ai_summary IS NULL THEN NULL
          ELSE jsonb_build_object('en', ai_summary, 'ka', NULL)
        END;

ALTER TABLE papers
  ALTER COLUMN ai_aleksandra_implications TYPE jsonb
  USING CASE
          WHEN ai_aleksandra_implications IS NULL THEN NULL
          ELSE jsonb_build_object('en', ai_aleksandra_implications, 'ka', NULL)
        END;
