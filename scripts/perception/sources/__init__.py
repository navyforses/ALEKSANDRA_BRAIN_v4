"""scripts.perception.sources — one pluggable fetcher module per clinical-trial registry.

Each module exposes ``run(...) -> dict[str, int]`` mirroring ``fetch_ctgov.run``:

    from scripts.perception.sources import ctis, isrctn
    ctis.run()      # POST search + GET retrieve, normalize, R2 + ledger
    isrctn.run()    # GET XML query, normalize, R2 + ledger

The contract every fetcher honours (matches fetch_ctgov exactly):

  1. derive a stable ``source_id`` (registry-native id);
  2. ``known_sources([...], source_type)`` batch dedup (fail-open like ctgov);
  3. produce a thin ``payload_metadata`` dict in the SAME shape fetch_ctgov writes
     (status terms in ctgov vocab, ages as "N Years"/"N Months" strings where
     derivable, interventions list, locations_sample "Facility, Country" /
     "(Country)", min_age/max_age, title, official_title, registry, registry_id,
     secondary_ids, …);
  4. ``upload_artifact(source_type, source_id, raw_bytes, ext)`` — raw JSON / XML;
  5. ``insert_ledger_row(source_id, source_type, retrieval_method, content_hash,
     raw_artifact_url, query, payload_metadata)``.

No new ledger.py code is needed — the existing helpers already take ``source_type``.

Shared facet set (same conditions fetch_ctgov queries — Aleksandra's diagnosis):
Hypoxic Ischemic Encephalopathy / Neonatal Encephalopathy / Infantile Spasms /
Cerebral Palsy / encephalopathy.
"""

# The condition facets every registry source queries. Kept here (not per-module)
# so all sources cover the same diagnosis surface as fetch_ctgov's QUERY_SETS.
CONDITION_FACETS: tuple[str, ...] = (
    "Hypoxic Ischemic Encephalopathy",
    "Neonatal Encephalopathy",
    "Infantile Spasms",
    "Cerebral Palsy",
    "encephalopathy",
)

# Descriptive User-Agent — same as fetch_ctgov so we play nice with public APIs.
USER_AGENT = "aleksandra_brain/1.0 (+https://github.com/navyforses/ALEKSANDRA_BRAIN_v4)"

__all__ = ["CONDITION_FACETS", "USER_AGENT"]
