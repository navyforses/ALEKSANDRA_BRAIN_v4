# tests/test_imperative_verb_lint_georgian.py
"""I18N-10 — imperative-verb lint must be bilingual-clean across 30 sample digests.

Three test groups:
  A. 30-sample lint-clean sweep over tests/fixtures/phase6/bilingual_samples.json
     (25 'clean' samples assert zero violations under per-locale scoping;
     5 'positive-catch' samples assert at least one violation under their
     banned-language scope).
  B. 8 positive-catch tests, one per new D-05 lexicon entry; each plants the
     banned form in a minimal Georgian sentence and asserts `check(text,
     locales=('ka',)).passed is False`.
  C. 1 English-regression test ensuring Phase 3 CGM-04 still catches
     should/consider/try.

Owner: plan 06-11 (Phase 6 — Bilingual System i18n).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.communicator.banned_phrases import check

FIXTURE_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "phase6" / "bilingual_samples.json"
)
with open(FIXTURE_PATH, encoding="utf-8") as f:
    SAMPLES = json.load(f)
assert len(SAMPLES) == 30, f"expected 30 bilingual samples, got {len(SAMPLES)}"

# Partition the 30 fixtures by their `banned` flag.
CLEAN_SAMPLES = [s for s in SAMPLES if not s.get("banned", False)]
POSITIVE_SAMPLES = [s for s in SAMPLES if s.get("banned", False)]
assert len(CLEAN_SAMPLES) == 25, f"expected 25 clean samples, got {len(CLEAN_SAMPLES)}"
assert (
    len(POSITIVE_SAMPLES) == 5
), f"expected 5 positive-catch samples, got {len(POSITIVE_SAMPLES)}"


# ---------------------------------------------------------------------------
# Group A — 30-sample sweep
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("sample", CLEAN_SAMPLES, ids=lambda s: s["id"])
def test_clean_sample_lint_clean_en(sample):
    """Each clean English sample must produce zero violations under locales=('en',)."""
    r = check(sample["en"], locales=("en",))
    assert r.passed, f"{sample['id']} en unexpectedly flagged: {r.violations}"


@pytest.mark.parametrize("sample", CLEAN_SAMPLES, ids=lambda s: s["id"])
def test_clean_sample_lint_clean_ka(sample):
    """Each clean Georgian sample must produce zero violations under locales=('ka',)."""
    r = check(sample["ka"], locales=("ka",))
    assert r.passed, f"{sample['id']} ka unexpectedly flagged: {r.violations}"


@pytest.mark.parametrize("sample", POSITIVE_SAMPLES, ids=lambda s: s["id"])
def test_positive_sample_caught_ka(sample):
    """Each positive-catch Georgian sample must trigger at least one violation.

    The Georgian half of every banned sample contains a D-05 lexicon entry,
    so this assertion is the primary contract Plan 06-11 establishes.
    """
    r = check(sample["ka"], locales=("ka",))
    assert not r.passed, (
        f"{sample['id']} ka expected violation (triggered_phrase="
        f"{sample.get('triggered_phrase')!r}), got passed=True"
    )


# Note: the English half of the 5 positive-catch samples is NOT asserted
# here. Plan 06-11 explicitly freezes `_PATTERNS_EN` (Task 1 action (c) — "DO
# NOT modify _PATTERNS_EN or _PATTERNS_FR. Phase 6 only extends the Georgian
# lexicon."). The fixture's English paraphrases ("Please consider …",
# "The family must try …", "Please request …") use bare verbs that the
# existing Phase 3 CGM-04 English lexicon does not cover by design (it scopes
# to subject+modal phrasings like "you should", "we recommend"). Extending
# `_PATTERNS_EN` to bare verbs is a Phase-3-side concern; tracked separately.
# The English regression contract Plan 06-11 owns is asserted by
# test_english_regression_phase3_cgm04 below.


# ---------------------------------------------------------------------------
# Group B — D-05 lexicon entry positive-catch tests
# ---------------------------------------------------------------------------
POSITIVE_KA_CASES = [
    ("ka-should", "მართებთ რომ მიიღოს თერაპია"),
    ("ka-must-bare", "აუცილებლად დაიწყოს მკურნალობა"),
    ("ka-must-pred", "აუცილებელია მკურნალობის გაგრძელება"),
    ("ka-consider", "განიხილეთ ეს ვარიანტი"),
    ("ka-consider2", "გაითვალისწინეთ ეს რეკომენდაცია"),
    ("ka-try", "სცადეთ ეს მიდგომა"),
    ("ka-askfor", "მოითხოვეთ კონსულტაცია"),
    ("ka-request", "ითხოვეთ მეორე აზრი"),
]


@pytest.mark.parametrize(
    "label,text", POSITIVE_KA_CASES, ids=[p[0] for p in POSITIVE_KA_CASES]
)
def test_d05_lexicon_catches_planted_violation(label, text):
    """Each of the 8 D-05 entries must catch a planted Georgian violation."""
    r = check(text, locales=("ka",))
    assert not r.passed, f"{label}: expected violation in {text!r}, got passed=True"


# ---------------------------------------------------------------------------
# Group C — English Phase 3 CGM-04 regression
# ---------------------------------------------------------------------------
def test_english_regression_phase3_cgm04():
    """Phase 3 CGM-04 English lint must still catch should/consider/try."""
    r = check("you should consider trying that approach", locales=("en",))
    assert (
        not r.passed
    ), "Phase 3 CGM-04 English lint must still catch should/consider/try"


# ---------------------------------------------------------------------------
# Group D — Per-locale scoping invariant (RESEARCH.md Open Question #3)
# ---------------------------------------------------------------------------
def test_locale_scoping_excludes_unrequested_locales():
    """A Georgian-only banned form scanned under locales=('en',) must pass."""
    r = check("მართებთ რომ მიიღოს თერაპია", locales=("en",))
    assert r.passed, (
        f"Per-locale scoping leaked: Georgian-only text under locales=('en',) "
        f"raised violations {r.violations!r}"
    )
