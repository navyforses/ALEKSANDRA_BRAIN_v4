-- 027_bilingual_therapy_mechanism.sql
-- Make therapies.mechanism_of_action bilingual JSONB {en, ka}, matching the
-- shape therapies.name / therapies.evidence_summary already use. It was TEXT
-- (English only), so /ka rendered the mechanism in English even in the Georgian
-- locale. After this, the ka slot (backfilled by the .py orchestrator) shows.
--
-- Idempotent-by-guard: the orchestrator skips this DDL when the column is
-- already jsonb. USING wraps each existing English string as {"en":<text>,
-- "ka":null}; NULL stays NULL. A plain-string scalar already stored in a jsonb
-- column (from a pre-migration writer) would also be handled by the backfill.

ALTER TABLE therapies
  ALTER COLUMN mechanism_of_action TYPE jsonb
  USING CASE
          WHEN mechanism_of_action IS NULL THEN NULL
          ELSE jsonb_build_object('en', mechanism_of_action, 'ka', NULL)
        END;
