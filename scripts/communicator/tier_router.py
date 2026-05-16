"""
tier_router.py — Phase 3 CGM-03 deterministic alert tier router.

Classifies a communicator Event into T0..T4 by rule, in this priority order:

  T0  Blocked       — any of: PHI leak, banned-phrase fail, source round-trip
                      fail, duplicate within dedupe window.
  T1  Urgent        — event.kind ∈ T1_KINDS AND confidence ≥ T1_CONFIDENCE
                      AND today's delivered-T1 count < T1_DAILY_CAP.
                      Otherwise demote to T2 with reason='t1_cap_reached'.
  T2  Action 7d     — event.kind == 'action_within_7d' AND confidence ≥ T2_CONFIDENCE,
                      OR demoted from T1.
                      Quiet-hours rule: T2 events generated 22:00–08:00 local
                      time defer their delivery to the next 08:00 batch.
  T3  Important     — event.kind == 'significant_update', OR confidence in
                      [T3_CONFIDENCE, T1_CONFIDENCE) for non-T1 kinds.
  T4  Weekly        — everything else with confidence > 0.

If the rules return AMBIGUOUS (no rule fired strongly), an optional LLM
fallback can be invoked. It's off by default — CGM-03 fixture is designed
so deterministic rules cover every case.

The router enforces the T1 daily cap by reading `alerts_log`:

    SELECT count(*) FROM alerts_log
    WHERE tier = 'T1' AND delivered_at >= today_start_utc

If count ≥ T1_DAILY_CAP, the proposed T1 demotes to T2.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone

import psycopg2


# ---------------------------------------------------------------------------
# Tunables (project-locked defaults)
# ---------------------------------------------------------------------------
T1_KINDS = frozenset(
    {
        "trial_deadline_24h",
        "researcher_reply",
        "med_safety_alert",
        "bmc_urgent",
    }
)
T1_CONFIDENCE = 0.85
T2_CONFIDENCE = 0.70
T3_CONFIDENCE = 0.50
T1_DAILY_CAP = 1
QUIET_START = time(22, 0)
QUIET_END = time(8, 0)
DEDUPE_WINDOW_HOURS = 24


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------
@dataclass
class Event:
    kind: str
    confidence: float
    phi_blocked: bool = False
    banned_blocked: bool = False
    source_round_trip_passed: bool = True
    is_duplicate: bool = False
    payload: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TierDecision:
    tier: str  # 'T0' | 'T1' | 'T2' | 'T3' | 'T4'
    confidence: float
    reason: str
    deferred_until: datetime | None = None  # set when quiet hours apply
    blocked_reason: str | None = None  # set when tier='T0'


# ---------------------------------------------------------------------------
# T1 cap query
# ---------------------------------------------------------------------------
def count_delivered_t1_today(now: datetime | None = None) -> int:
    """Read alerts_log for today's delivered T1 count (UTC day).

    Returns 0 if Supabase is unreachable — fail-open is intentional here:
    a connectivity blip should not silently block urgent alerts. The
    real safety net is the upstream evidence + confidence gate.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    try:
        conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT count(*) FROM alerts_log
                    WHERE tier = 'T1' AND delivered_at >= %s
                    """,
                    (today_start,),
                )
                row = cur.fetchone()
                return int(row[0]) if row else 0
        finally:
            conn.close()
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Quiet hours
# ---------------------------------------------------------------------------
def is_quiet_hour(ts: datetime) -> bool:
    """Quiet hours in local time = 22:00..08:00 next day.

    The router runs in UTC; for the v1 product we treat the server clock as
    the family's local clock (Boston/Durham/Tbilisi swings are tracked
    operationally, not in code). When the family relocates, replace this
    with a tz-aware lookup against contacts.preferred_tz.
    """
    h = ts.hour
    return h >= QUIET_START.hour or h < QUIET_END.hour


def defer_to_next_morning(ts: datetime) -> datetime:
    """Return next 08:00 (same tz as ts) so T2 deliveries batch cleanly."""
    base = ts.replace(hour=QUIET_END.hour, minute=0, second=0, microsecond=0)
    if ts.hour >= QUIET_END.hour:
        base = base + timedelta(days=1)
    return base


# ---------------------------------------------------------------------------
# classify()
# ---------------------------------------------------------------------------
def classify(
    event: Event,
    *,
    t1_count_today: int | None = None,
) -> TierDecision:
    """Deterministic tier decision for a single Event.

    `t1_count_today` lets tests pass in a known T1 count to avoid hitting
    the DB. Production callers leave it None and the router reads
    alerts_log directly.
    """
    # --- Hard blocks (T0) ----------------------------------------------------
    if event.phi_blocked:
        return TierDecision(
            tier="T0",
            confidence=event.confidence,
            reason="phi_blocked",
            blocked_reason="PHI redactor blocked the draft",
        )
    if event.banned_blocked:
        return TierDecision(
            tier="T0",
            confidence=event.confidence,
            reason="banned_blocked",
            blocked_reason="Clinical-command language detected",
        )
    if not event.source_round_trip_passed:
        return TierDecision(
            tier="T0",
            confidence=event.confidence,
            reason="source_round_trip_failed",
            blocked_reason="Citation does not round-trip to its source",
        )
    if event.is_duplicate:
        return TierDecision(
            tier="T0",
            confidence=event.confidence,
            reason="duplicate_within_dedupe_window",
            blocked_reason=f"Duplicate within {DEDUPE_WINDOW_HOURS}h dedupe window",
        )

    # No useful signal at all → T4 (weekly appendix or skip)
    if event.confidence <= 0.0:
        return TierDecision(
            tier="T4", confidence=event.confidence, reason="zero_confidence"
        )

    # --- T1 candidate --------------------------------------------------------
    if event.kind in T1_KINDS and event.confidence >= T1_CONFIDENCE:
        n_today = (
            t1_count_today if t1_count_today is not None else count_delivered_t1_today()
        )
        if n_today < T1_DAILY_CAP:
            return TierDecision(
                tier="T1",
                confidence=event.confidence,
                reason=f"t1_kind+conf>={T1_CONFIDENCE}+cap_open({n_today}/{T1_DAILY_CAP})",
            )
        # Cap reached → demote to T2
        decision = TierDecision(
            tier="T2",
            confidence=event.confidence,
            reason=f"t1_cap_reached({n_today}/{T1_DAILY_CAP})",
        )
        _apply_quiet_hours(decision, event)
        return decision

    # --- T2 — action needed within 7 days -----------------------------------
    if event.kind == "action_within_7d" and event.confidence >= T2_CONFIDENCE:
        decision = TierDecision(
            tier="T2",
            confidence=event.confidence,
            reason=f"action_within_7d+conf>={T2_CONFIDENCE}",
        )
        _apply_quiet_hours(decision, event)
        return decision

    # --- T3 — significant_update or medium confidence non-T1 kind -----------
    if event.kind == "significant_update":
        return TierDecision(
            tier="T3", confidence=event.confidence, reason="significant_update_kind"
        )
    if event.kind not in T1_KINDS and T3_CONFIDENCE <= event.confidence < T1_CONFIDENCE:
        return TierDecision(
            tier="T3",
            confidence=event.confidence,
            reason=f"non_t1_kind+conf>={T3_CONFIDENCE}",
        )

    # --- T4 — weekly appendix ------------------------------------------------
    return TierDecision(
        tier="T4", confidence=event.confidence, reason="falls_through_to_weekly"
    )


def _apply_quiet_hours(decision: TierDecision, event: Event) -> None:
    """Mutate `decision` to defer delivery if event timestamp is in quiet hours."""
    if decision.tier in {"T2", "T3"} and is_quiet_hour(event.timestamp):
        decision.deferred_until = defer_to_next_morning(event.timestamp)
        decision.reason = f"{decision.reason}+quiet_hours_defer"


__all__ = [
    "Event",
    "TierDecision",
    "classify",
    "count_delivered_t1_today",
    "is_quiet_hour",
    "defer_to_next_morning",
    "T1_KINDS",
    "T1_CONFIDENCE",
    "T2_CONFIDENCE",
    "T3_CONFIDENCE",
    "T1_DAILY_CAP",
]
