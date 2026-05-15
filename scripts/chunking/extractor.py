"""
extractor.py — Phase 2 sub-phase 2A.

Format-aware text extraction from R2 raw_artifact payloads. Every
evidence_ledger row points at one R2 artifact whose format depends on
source_type:

    source_type | format         | extractor
    ------------|----------------|------------------------------------
    pubmed      | XML (PubMed)   | extract_pubmed_xml
    ctgov       | JSON           | extract_ctgov_json
    biorxiv     | JSON (feedparser entry) | extract_rss_entry
    medrxiv     | JSON (feedparser entry) | extract_rss_entry
    crawl4ai    | Markdown       | extract_markdown

The dispatcher `extract_text(source_type, payload_bytes)` returns one
plain-text string per ledger row, ready for the chunker. Empty-string
return == "no usable text" (caller skips the row).
"""

from __future__ import annotations

import json
import re
from xml.etree import ElementTree as ET


# ---------------------------------------------------------------------------
# PubMed XML
# ---------------------------------------------------------------------------
def extract_pubmed_xml(xml_bytes: bytes) -> str:
    """
    Pull title + abstract from a PubMed E-utilities efetch XML payload.

    Body / full-text is NOT in the abstract XML — for PMC fulltext we'd need
    a separate efetch against db=pmc, which we don't do in Phase 1. So this
    extractor returns 'title\\n\\nabstract' (typically 1–3 paragraphs).
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return ""

    article = root.find(".//PubmedArticle/MedlineCitation/Article")
    if article is None:
        return ""

    parts: list[str] = []

    title = article.findtext("ArticleTitle")
    if title:
        parts.append(title.strip())

    abstract_pieces: list[str] = []
    for ab in article.findall(".//Abstract/AbstractText"):
        label = ab.get("Label")
        text = (ab.text or "").strip()
        if not text:
            continue
        if label:
            abstract_pieces.append(f"{label}: {text}")
        else:
            abstract_pieces.append(text)
    if abstract_pieces:
        parts.append("\n\n".join(abstract_pieces))

    return "\n\n".join(parts).strip()


# ---------------------------------------------------------------------------
# ClinicalTrials.gov JSON
# ---------------------------------------------------------------------------
def extract_ctgov_json(json_bytes: bytes) -> str:
    """
    Build a structured-text representation of a CT.gov v2 study so that
    the chunker can split it the same way it splits a paper. We
    intentionally concat field name + content (e.g. "Eligibility: ...")
    because that surface form helps both the embedder and downstream
    Graphiti reasoning.
    """
    try:
        study = json.loads(json_bytes)
    except json.JSONDecodeError:
        return ""

    proto = study.get("protocolSection") or {}
    ident = proto.get("identificationModule") or {}
    desc = proto.get("descriptionModule") or {}
    status = proto.get("statusModule") or {}
    design = proto.get("designModule") or {}
    arms = proto.get("armsInterventionsModule") or {}
    elig = proto.get("eligibilityModule") or {}
    cond = proto.get("conditionsModule") or {}

    parts: list[str] = []

    title = ident.get("officialTitle") or ident.get("briefTitle")
    if title:
        parts.append(title)

    brief = desc.get("briefSummary")
    if brief:
        parts.append(f"Brief Summary: {brief.strip()}")

    detailed = desc.get("detailedDescription")
    if detailed:
        parts.append(f"Detailed Description: {detailed.strip()}")

    conditions = cond.get("conditions") or []
    if conditions:
        parts.append("Conditions: " + "; ".join(conditions))

    interventions = [
        f"{i.get('type', '').strip()}: {i.get('name', '').strip()}"
        for i in (arms.get("interventions") or [])
        if i.get("name")
    ]
    if interventions:
        parts.append("Interventions: " + " | ".join(interventions))

    elig_criteria = elig.get("eligibilityCriteria")
    if elig_criteria:
        parts.append(f"Eligibility Criteria: {elig_criteria.strip()}")

    age_range = []
    if elig.get("minimumAge"):
        age_range.append(f"min={elig['minimumAge']}")
    if elig.get("maximumAge"):
        age_range.append(f"max={elig['maximumAge']}")
    if age_range:
        parts.append("Age: " + " ".join(age_range))

    overall = status.get("overallStatus")
    if overall:
        parts.append(f"Overall Status: {overall}")

    phases = design.get("phases") or []
    if phases:
        parts.append("Phases: " + ", ".join(phases))

    return "\n\n".join(p for p in parts if p).strip()


# ---------------------------------------------------------------------------
# bioRxiv / medRxiv RSS entries (JSON-serialised feedparser entries)
# ---------------------------------------------------------------------------
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _strip_html(s: str) -> str:
    return _WS_RE.sub(" ", _HTML_TAG_RE.sub(" ", s)).strip()


def extract_rss_entry(json_bytes: bytes) -> str:
    """
    Pull title + abstract excerpt from a feedparser entry JSON-serialised
    by fetch_preprints. Most preprint RSS entries carry the abstract in
    the `summary` field as HTML.
    """
    try:
        entry = json.loads(json_bytes)
    except json.JSONDecodeError:
        return ""

    parts: list[str] = []

    title = entry.get("title")
    if title:
        parts.append(title.strip())

    summary = entry.get("summary") or entry.get("description") or ""
    if summary:
        text = _strip_html(summary)
        if text:
            parts.append(text)

    return "\n\n".join(parts).strip()


# ---------------------------------------------------------------------------
# Crawl4AI markdown
# ---------------------------------------------------------------------------
def extract_markdown(md_bytes: bytes) -> str:
    """Pass-through for Crawl4AI markdown (already plain text)."""
    try:
        text = md_bytes.decode("utf-8", errors="ignore")
    except Exception:
        return ""
    # Collapse extreme whitespace runs that crawl4ai sometimes emits.
    text = re.sub(r"\n{4,}", "\n\n\n", text).strip()
    return text


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------
EXTRACTORS = {
    "pubmed": extract_pubmed_xml,
    "ctgov": extract_ctgov_json,
    "biorxiv": extract_rss_entry,
    "medrxiv": extract_rss_entry,
    "crawl4ai": extract_markdown,
    "firecrawl": extract_markdown,  # firecrawl falls back to markdown too
}


def extract_text(source_type: str, payload_bytes: bytes) -> str:
    """Dispatch to the right extractor. Returns empty string on unknown type."""
    fn = EXTRACTORS.get(source_type)
    if fn is None:
        return ""
    return fn(payload_bytes)
