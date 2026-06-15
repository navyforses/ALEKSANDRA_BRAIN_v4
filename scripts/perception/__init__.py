"""scripts.perception — PERCEPTION-layer pluggable trial sources (Phase E).

Houses the pluggable multi-registry fetchers under ``sources/`` (ctis, isrctn, …)
that mirror ``scripts/fetch_ctgov.py``: each queries a clinical-trial registry for
Aleksandra's conditions, normalizes every trial into the SAME ``payload_metadata``
shape + vocabulary fetch_ctgov writes, uploads the full raw registry record to R2,
and inserts one ``evidence_ledger`` row per trial via ``scripts.ledger``.

See docs/CLINICAL_TRIALS_SOURCES_RESEARCH.md for the verified endpoints, field
mappings, status/age normalization, and honest gaps.
"""
