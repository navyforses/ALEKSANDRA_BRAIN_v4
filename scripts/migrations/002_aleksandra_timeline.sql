-- Phase 0+ — aleksandra_timeline table
-- Single-patient timeline of clinical/treatment events.
-- Append-friendly (no triggers blocking UPDATE/DELETE because the family
-- legitimately needs to correct typos in entries). RLS still enforces
-- family-only access.

CREATE TABLE IF NOT EXISTS aleksandra_timeline (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_date    date NOT NULL,
  event_type    text NOT NULL,
  -- examples: birth, diagnosis, mri_scan, medication_start, medication_change,
  --           appointment, hospitalization, milestone, eap_application,
  --           trial_screening, lab_result, surgery, vaccination
  title         text NOT NULL,
  description   text,
  institution   text,
  location      text,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS aleksandra_timeline_event_date_idx
  ON aleksandra_timeline (event_date DESC);

CREATE INDEX IF NOT EXISTS aleksandra_timeline_event_type_idx
  ON aleksandra_timeline (event_type);

-- RLS
ALTER TABLE aleksandra_timeline ENABLE ROW LEVEL SECURITY;

-- Read: any authenticated family member; service-role bypasses RLS by default.
DROP POLICY IF EXISTS aleksandra_timeline_family_read ON aleksandra_timeline;
CREATE POLICY aleksandra_timeline_family_read
  ON aleksandra_timeline
  FOR SELECT
  TO authenticated
  USING (true);

-- Write: service-role only (n8n cron + admin scripts). The anon role cannot write.
DROP POLICY IF EXISTS aleksandra_timeline_service_write ON aleksandra_timeline;
CREATE POLICY aleksandra_timeline_service_write
  ON aleksandra_timeline
  FOR INSERT
  TO service_role
  WITH CHECK (true);

DROP POLICY IF EXISTS aleksandra_timeline_service_update ON aleksandra_timeline;
CREATE POLICY aleksandra_timeline_service_update
  ON aleksandra_timeline
  FOR UPDATE
  TO service_role
  USING (true) WITH CHECK (true);

-- updated_at trigger
CREATE OR REPLACE FUNCTION aleksandra_timeline_touch_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS aleksandra_timeline_set_updated_at ON aleksandra_timeline;
CREATE TRIGGER aleksandra_timeline_set_updated_at
  BEFORE UPDATE ON aleksandra_timeline
  FOR EACH ROW EXECUTE FUNCTION aleksandra_timeline_touch_updated_at();
