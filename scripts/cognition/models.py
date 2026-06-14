"""
models.py — task→tier→model registry + pricing (multi-provider routing).

Single source of truth for "which model runs which kind of work". Call sites
ask for a TASK (e.g. ``task="extraction"``); the router resolves it to a tier
and then to a concrete model slug. Changing the lineup happens here only.

Three tiers
-----------
- worker  : high-volume, structured, repetitive work — cheap model.
- thinker : low-volume, high-value reasoning — Anthropic's strongest model.
- writer  : prose / translation where tone + language matter — Gemini.

Provider routing
----------------
Default provider is OpenRouter (one OpenAI-compatible gateway, one key
``OPENROUTER_API_KEY``). Setting ``MODEL_PROVIDER=anthropic`` is the rollback
path: every tier resolves to a native Anthropic model id instead, and
``scripts.cognition.llm`` sends it straight to the Anthropic SDK. This lets a
single env var revert the whole system to the pre-refactor behaviour without a
code change.

Model slugs are env-overridable (``WORKER_MODEL`` / ``THINKER_MODEL`` /
``WRITER_MODEL``) so an incorrect OpenRouter slug can be corrected from Railway
without a deploy. Pricing for an unknown/overridden slug falls back to the
conservative Opus rate so spend is never under-reported.
"""

from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Tier → model slug. OpenRouter convention is "provider/model".
# Env-overridable so a wrong slug is fixable from Railway without a deploy.
# ---------------------------------------------------------------------------
TIER_MODEL: dict[str, str] = {
    "worker": os.environ.get("WORKER_MODEL", "deepseek/deepseek-v4-flash"),
    "thinker_light": os.environ.get("THINKER_LIGHT_MODEL", "deepseek/deepseek-v4-pro"),
    "thinker": os.environ.get("THINKER_MODEL", "anthropic/claude-opus-4-8"),
    "writer": os.environ.get("WRITER_MODEL", "google/gemini-3.5-flash"),
}

# Rollback lineup: MODEL_PROVIDER=anthropic resolves tiers to native ids that
# scripts.cognition.llm routes to the Anthropic SDK directly.
TIER_MODEL_ANTHROPIC: dict[str, str] = {
    "worker": "claude-haiku-4-5-20251001",
    "thinker_light": "claude-sonnet-4-5",
    "thinker": "claude-opus-4-8",
    "writer": "claude-sonnet-4-5",
}

# ---------------------------------------------------------------------------
# Task → tier. Unknown tasks fall back to the (cheap) worker tier so a typo
# never silently bills Opus rates.
# ---------------------------------------------------------------------------
TASK_TIER: dict[str, str] = {
    # 🔧 worker — repetitive / structured
    "extraction": "worker",
    "edge_classify": "worker",
    "relevance": "worker",
    "intake_parse": "worker",
    "self_review": "worker",
    # 🧠 thinker — reasoning
    "got": "thinker",
    "repurpose": "thinker",
    "evidence_hard": "thinker",
    # Evidence Refinery Stage 2 (REASON): per-paper deep analysis. thinker tier,
    # complexity-gated — short abstracts run on thinker_light (DeepSeek V4 Pro),
    # long/complex ones escalate to Opus. See scripts.analysis.analyze_paper.
    "analyze_paper": "thinker",
    # ✍️ writer — prose / translation
    "translate": "writer",
    "weekly_brief": "writer",
    "family_msg": "writer",
    "summarize": "writer",
}

DEFAULT_TIER = "worker"

# Thinker gating: a thinker-tier call whose caller-supplied `complexity` proxy
# (currently the user-prompt length in characters) is BELOW this threshold is
# downgraded to the `thinker_light` model (DeepSeek V4 Pro). This is the "Opus
# only for hard cases" policy — short/simple reasoning runs on V4 Pro,
# long/complex reasoning escalates to Opus 4.8. Tune from Railway without a deploy.
THINKER_COMPLEXITY_MIN = int(os.environ.get("THINKER_COMPLEXITY_MIN", "1200"))

# ---------------------------------------------------------------------------
# Pricing — $/1M tokens (input, output). Verified 2026-06 (OpenRouter +
# Anthropic published rates). Resolved by exact match first, then by prefix so
# date-suffixed ids (e.g. claude-opus-4-8) match a shorter family key.
# ---------------------------------------------------------------------------
PRICING_USD_PER_M: dict[str, tuple[float, float]] = {
    # OpenRouter slugs
    "deepseek/deepseek-v4-flash": (0.10, 0.20),
    # V4 Pro: conservative standard estimate. OpenRouter listed an effective
    # promo rate ~$0.44/$0.87 (ended 2026-05-31); we over-report rather than
    # under-report spend. Verify + tighten if needed — env-overridable.
    "deepseek/deepseek-v4-pro": (1.74, 3.48),
    "deepseek/deepseek-chat": (0.27, 1.10),
    "google/gemini-3.5-flash": (1.50, 9.00),
    "google/gemini-2.5-flash": (0.30, 2.50),
    "google/gemini-2.5-pro": (1.25, 10.00),
    "anthropic/claude-opus-4-8": (15.00, 75.00),
    "anthropic/claude-opus-4": (15.00, 75.00),
    "anthropic/claude-sonnet-4": (3.00, 15.00),
    # Native Anthropic ids (legacy / rollback path)
    "claude-opus-4": (15.00, 75.00),
    "claude-sonnet-4": (3.00, 15.00),
    "claude-haiku-4": (0.80, 4.00),
}
# Conservative fallback for unknown/overridden slugs — never under-report spend.
FALLBACK_PRICE: tuple[float, float] = (15.00, 75.00)


def provider() -> str:
    """Active provider: 'openrouter' (default) or 'anthropic' (rollback)."""
    return (
        os.environ.get("MODEL_PROVIDER", "openrouter").strip().lower() or "openrouter"
    )


def tier_for(task: str) -> str:
    """Map a task name to a tier. Unknown task → cheap worker tier."""
    return TASK_TIER.get(task, DEFAULT_TIER)


def model_for(task: str, *, complexity: int | None = None) -> str:
    """Resolve a task to a concrete model slug, honouring MODEL_PROVIDER.

    When ``complexity`` is supplied for a thinker-tier task and falls below
    ``THINKER_COMPLEXITY_MIN``, the call is downgraded to ``thinker_light``
    (DeepSeek V4 Pro) — strong reasoning at a fraction of Opus cost. The hardest
    cases (complexity above the gate, or no ``complexity`` hint) get the full
    ``thinker`` model (Opus 4.8) — quality-safe default.
    """
    tier = tier_for(task)
    table = TIER_MODEL_ANTHROPIC if provider() == "anthropic" else TIER_MODEL
    if (
        tier == "thinker"
        and complexity is not None
        and complexity < THINKER_COMPLEXITY_MIN
    ):
        return table["thinker_light"]
    return table[tier]


def price_for(model: str) -> tuple[float, float]:
    """Return ($/1M input, $/1M output) for a model slug. Exact then prefix."""
    if model in PRICING_USD_PER_M:
        return PRICING_USD_PER_M[model]
    for prefix, rate in PRICING_USD_PER_M.items():
        if model.startswith(prefix):
            return rate
    return FALLBACK_PRICE


def is_openrouter_model(model: str) -> bool:
    """OpenRouter slugs are 'provider/model'; native Anthropic ids are 'claude-*'."""
    return "/" in model


# Models that reject the `temperature` request param (newer reasoning models such
# as Opus 4.8). Sending `temperature` to these returns HTTP 400
# invalid_request_error ("`temperature` is deprecated for this model"), so
# scripts.cognition.llm omits the param for them and lets the model use its default.
TEMPERATURE_UNSUPPORTED: tuple[str, ...] = (
    "claude-opus-4-8",
    "anthropic/claude-opus-4-8",
)


def supports_temperature(model: str) -> bool:
    """False for models that reject the `temperature` request param (e.g. Opus 4.8)."""
    return not any(model.startswith(p) for p in TEMPERATURE_UNSUPPORTED)


def crew_llm(tier: str) -> str:
    """LiteLLM model string for CrewAI agents.

    CrewAI resolves models through LiteLLM, which needs an explicit
    ``openrouter/`` provider prefix to reach the gateway (and ``OPENROUTER_API_KEY``
    in env). Under MODEL_PROVIDER=anthropic this returns the native Claude id,
    which LiteLLM routes to Anthropic directly (rollback).
    """
    if provider() == "anthropic":
        return TIER_MODEL_ANTHROPIC[tier]
    return f"openrouter/{TIER_MODEL[tier]}"


__all__ = [
    "TIER_MODEL",
    "TIER_MODEL_ANTHROPIC",
    "TASK_TIER",
    "PRICING_USD_PER_M",
    "FALLBACK_PRICE",
    "provider",
    "tier_for",
    "model_for",
    "price_for",
    "is_openrouter_model",
    "supports_temperature",
    "TEMPERATURE_UNSUPPORTED",
    "crew_llm",
    "THINKER_COMPLEXITY_MIN",
]
