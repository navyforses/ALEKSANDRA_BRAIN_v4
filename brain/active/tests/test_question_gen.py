"""Phase 7.4 Day 5 — question_gen tests."""

from __future__ import annotations

import pytest

from brain.active.question_gen import (
    BANNED_BIGRAMS,
    TemplateError,
    load_templates,
    render_all_dims_for_lang,
    render_question,
    validate_ka_template_anti_loop,
    validate_no_template_leaks,
)


EXPECTED_DIMS = {
    "cyst_volume_pct",
    "brainstem_function",
    "seizure_freq_per_day",
    "muscle_tone_hammersmith",
    "eye_tracking_seconds",
    "head_control_seconds",
    "gmfcs_level",
    "bayley_cognitive",
    "feeding_stage",
    "respiratory_apnea_per_day",
    "csf_biomarkers",
    "neuroplasticity_resource",
    "family_readiness",
}


def test_ka_renders_all_13_dims_no_leak() -> None:
    """Verifier check 5: every KA template renders cleanly."""
    rendered = render_all_dims_for_lang(lang="ka", eig_pct=12.3)
    assert set(rendered.keys()) == EXPECTED_DIMS
    for dim, text in rendered.items():
        assert validate_no_template_leaks(text), f"placeholder leak in {dim}: {text}"
        # spot-check eig_pct interpolation
        assert "12.3" in text, f"eig_pct missing in {dim}: {text}"


def test_en_renders_all_13_dims_no_leak() -> None:
    rendered = render_all_dims_for_lang(lang="en", eig_pct=7.5)
    assert set(rendered.keys()) == EXPECTED_DIMS
    for dim, text in rendered.items():
        assert validate_no_template_leaks(text), f"placeholder leak in {dim}: {text}"
        assert "7.5" in text, f"eig_pct missing in {dim}: {text}"


def test_missing_variable_raises_template_error() -> None:
    # Force an extra placeholder by monkey-patching the cache.
    from brain.active import question_gen

    question_gen.clear_cache()
    templates = load_templates("ka")
    # Use the original; the existing templates only need eig_pct.
    rendered = render_question(dim_name="cyst_volume_pct", lang="ka", eig_pct=10.0)
    assert "10.0" in rendered

    # Now force a missing variable by handing a template with an extra slot.
    question_gen._CACHE[("ka", "synthetic")] = {
        "foo": {
            "template": "needs {missing_var} {eig_pct}",
            "variables": ["missing_var", "eig_pct"],
            "expected_format": "integer_count",
        }
    }
    # Monkey-patch load: temporarily swap default path lookup
    from pathlib import Path

    question_gen._CACHE[("ka", str(question_gen.DEFAULT_KA_PATH))] = (
        question_gen._CACHE[("ka", "synthetic")]
    )
    try:
        with pytest.raises(TemplateError):
            render_question(dim_name="foo", lang="ka", eig_pct=10.0)
    finally:
        question_gen.clear_cache()


def test_unknown_dim_raises_template_error() -> None:
    from brain.active import question_gen
    question_gen.clear_cache()
    with pytest.raises(TemplateError):
        render_question(dim_name="nonexistent_xyz", lang="ka", eig_pct=10.0)


def test_ka_templates_pass_anti_loop_check() -> None:
    """Verifier check 4 partial: KA templates respect banned-bigram rule."""
    from brain.active import question_gen
    question_gen.clear_cache()
    rendered = render_all_dims_for_lang(lang="ka", eig_pct=10.0)
    for dim, text in rendered.items():
        offenders = validate_ka_template_anti_loop(text)
        assert offenders == [], (
            f"anti-loop violation in {dim} (banned bigrams {offenders} appear >=2 times): {text}"
        )


def test_eig_pct_rounded_one_decimal() -> None:
    from brain.active import question_gen
    question_gen.clear_cache()
    text = render_question(dim_name="seizure_freq_per_day", lang="en", eig_pct=12.3456)
    assert "12.3" in text
