"""Phase 7.4 Day 3 — Candidate observation catalog.

Hand-authored list of candidate observations per dimension, with bilingual
descriptions, expected response format, and the wife-time cost. Used by
the Day 4 ranker to weight EIG by clinical/family cost.

Hard rule:
    * wife_time_minutes in (0, 15] — cap from spec §1 Day 4 "≤ 5 min/observation"
      relaxed to 15 min to accommodate PT-administered Bayley-III.
    * Every entry has non-empty `description_en` and `description_ka`.
    * Citation field reuses Phase 7.0 dimensions.toml PMIDs only.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


ExpectedFormat = Literal[
    "integer_seconds",
    "integer_count",
    "float_value",
    "categorical_choice",
    "boolean",
    "scale_0_5",
]


class CandidateObservation(BaseModel):
    """One row of the candidate-observation catalog."""

    model_config = ConfigDict(extra="forbid")

    dim_name: str = Field(..., min_length=1)
    observation_type: str = Field(..., min_length=1)
    description_en: str = Field(..., min_length=1)
    description_ka: str = Field(..., min_length=1)
    expected_format: ExpectedFormat
    wife_time_minutes: float = Field(..., gt=0.0, le=15.0)
    cost_usd: float = Field(default=0.0, ge=0.0)
    citation: Optional[str] = None


# ---------------------------------------------------------------------------
# CANDIDATE_CATALOG — 13 hand-authored entries
# ---------------------------------------------------------------------------
CANDIDATE_CATALOG: list[CandidateObservation] = [
    CandidateObservation(
        dim_name="cyst_volume_pct",
        observation_type="mri_volumetric_report",
        description_en="Forward the latest BMC MRI volumetric report PDF (cyst-volume estimate).",
        description_ka="ბოლო BMC MRI მოცულობითი ანგარიში გადააგზავნე (ცისტის მოცულობის შეფასება).",
        expected_format="float_value",
        wife_time_minutes=5.0,
        citation="PMID:39799120",
    ),
    CandidateObservation(
        dim_name="brainstem_function",
        observation_type="neuro_exam",
        description_en="Record neurologist's brainstem-function rating from last clinic visit (impaired/partial/intact).",
        description_ka="ნევროლოგის შეფასება ღეროს ფუნქციაზე ბოლო ვიზიტიდან (დაზიანებული, ნაწილობრივი, შენარჩუნებული).",
        expected_format="categorical_choice",
        wife_time_minutes=3.0,
        citation="PMID:26981220",
    ),
    CandidateObservation(
        dim_name="seizure_freq_per_day",
        observation_type="parent_log_count",
        description_en="Count visible seizure episodes over the past 24 hours.",
        description_ka="ბოლო 24 საათში დაფიქსირებული გულყრის ეპიზოდების რაოდენობა დათვალე.",
        expected_format="integer_count",
        wife_time_minutes=2.0,
        citation="PMID:27595841",
    ),
    CandidateObservation(
        dim_name="muscle_tone_hammersmith",
        observation_type="pt_hammersmith_score",
        description_en="Ask the PT for this week's Hammersmith infant neurologic exam (HINE) total score.",
        description_ka="ფიზიოთერაპევტს სთხოვე ამ კვირის HINE შეფასების ჯამური ქულა.",
        expected_format="integer_count",
        wife_time_minutes=10.0,
        cost_usd=0.0,
        citation="PMID:31426574",
    ),
    CandidateObservation(
        dim_name="eye_tracking_seconds",
        observation_type="five_min_red_ball_video",
        description_en="Five-minute video with a red ball at 30 cm; note longest fixation in seconds.",
        description_ka="ხუთწუთიანი ვიდეო წითელი ბურთით 30 სმ-ზე; ყველაზე ხანგრძლივი ფიქსაცია წამებში ჩაიწერე.",
        expected_format="integer_seconds",
        wife_time_minutes=5.0,
        citation="PMID:40151356",
    ),
    CandidateObservation(
        dim_name="head_control_seconds",
        observation_type="tummy_time_timer",
        description_en="One-minute tummy-time; time vertical head-hold in seconds.",
        description_ka="ერთწუთიანი მუცელზე წოლა; ვერტიკალური თავის დაჭერა წამებში დაითვალე.",
        expected_format="integer_seconds",
        wife_time_minutes=2.0,
        citation="PMID:31426574",
    ),
    CandidateObservation(
        dim_name="gmfcs_level",
        observation_type="pt_gmfcs_assessment",
        description_en="Confirm the current GMFCS level (I-V) recorded by the PT at last assessment.",
        description_ka="დაადასტურე ფიზიოთერაპევტის ბოლო GMFCS დონე (I-V).",
        expected_format="scale_0_5",
        wife_time_minutes=3.0,
        citation="PMID:9183258",
    ),
    CandidateObservation(
        dim_name="bayley_cognitive",
        observation_type="bayley_iii_snapshot",
        description_en="PT-administered Bayley-III cognitive subtest snapshot (numeric composite).",
        description_ka="ფიზიოთერაპევტის ჩატარებული Bayley-III კოგნიტური ქვეტესტი (ციფრული ჯამი).",
        expected_format="integer_count",
        wife_time_minutes=15.0,
        cost_usd=200.0,
        citation="PMID:24743133",
    ),
    CandidateObservation(
        dim_name="feeding_stage",
        observation_type="weekly_feeding_log",
        description_en="Current feeding stage this week: NG-tube / partial-oral / full-oral-puree / full-oral-solid.",
        description_ka="ამ კვირის კვების ეტაპი: ნაზონდი, ნაწილობრივ პერორალური, სრულად პერორალური პიურე, სრულად პერორალური მყარი.",
        expected_format="categorical_choice",
        wife_time_minutes=3.0,
        citation="PMID:39761677",
    ),
    CandidateObservation(
        dim_name="respiratory_apnea_per_day",
        observation_type="monitor_apnea_count",
        description_en="Was any apnea event detected by the home monitor in the past 24 hours? Yes/no.",
        description_ka="დაფიქსირდა თუ არა აპნოეს ეპიზოდი სახლის მონიტორზე ბოლო 24 საათში? კი/არა.",
        expected_format="boolean",
        wife_time_minutes=1.0,
        citation="PMID:26981220",
    ),
    CandidateObservation(
        dim_name="csf_biomarkers",
        observation_type="csf_panel_draw",
        description_en="Most recent CSF biomarker panel value (NSE / S100B / GFAP / Tau, pick one).",
        description_ka="ბოლო ცერებროსპინალური სითხის ბიომარკერის მნიშვნელობა (NSE, S100B, GFAP ან Tau).",
        expected_format="float_value",
        wife_time_minutes=5.0,
        cost_usd=0.0,
        citation="PMID:32610169",
    ),
    CandidateObservation(
        dim_name="neuroplasticity_resource",
        observation_type="calendar_age_in_days",
        description_en="Confirm Aleksandra's age in days as of today (for plasticity-window calibration).",
        description_ka="დაადასტურე ალექსანდრას ასაკი დღეებში დღევანდელი თარიღით.",
        expected_format="integer_count",
        wife_time_minutes=1.0,
        citation="PMID:19489084",
    ),
    CandidateObservation(
        dim_name="family_readiness",
        observation_type="weekly_self_report",
        description_en="On a 0-5 scale, how stable did the family feel this week? (0 overwhelmed, 5 thriving)",
        description_ka="0-დან 5-მდე როგორ გრძნობდა თავს ოჯახი ამ კვირას? (0 გადატვირთული, 5 აყვავებული).",
        expected_format="scale_0_5",
        wife_time_minutes=2.0,
        citation="PMID:40776994",
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_catalog_for_dimension(dim_name: str) -> list[CandidateObservation]:
    """Return every candidate observation registered for `dim_name`."""
    return [c for c in CANDIDATE_CATALOG if c.dim_name == dim_name]


def all_dim_names() -> list[str]:
    """Return the de-duplicated list of dim_names present in the catalog."""
    return sorted({c.dim_name for c in CANDIDATE_CATALOG})


def total_entries() -> int:
    return len(CANDIDATE_CATALOG)


__all__ = [
    "ExpectedFormat",
    "CandidateObservation",
    "CANDIDATE_CATALOG",
    "get_catalog_for_dimension",
    "all_dim_names",
    "total_entries",
]
