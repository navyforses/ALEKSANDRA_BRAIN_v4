// viewer/lib/api/sim.ts — Phase 7.6 typed API client for the Simulation layer.
//
// Mirrors brain/sim/* Pydantic shapes (Phase 7.3). MOCK_MODE returns
// deterministic Vigabatrin-vs-control comparison using the reference SCM
// pattern so the Simulation Studio renders without the live worker.

const MOCK_MODE: boolean =
  !process.env.NEXT_PUBLIC_API_URL ||
  process.env.NEXT_PUBLIC_MOCK_MODE === "true";

const API_BASE: string = process.env.NEXT_PUBLIC_API_URL ?? "";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export type InterventionType = "treatment" | "control" | "lifestyle";

export interface Intervention {
  node_name: string;
  intervention_type: InterventionType;
  value: number | string;
}

export interface Scenario {
  name: string;
  scm_id: string;
  interventions: Intervention[];
  n_samples: number;
  horizon_days: number;
  notes?: string;
}

export interface ScenarioRecord {
  scenario_id: string;
  scenario_hash: string;
  name: string;
  scm_id: string;
  created_at: string;
  n_samples: number;
  horizon_days: number;
}

export interface OutcomeSummary {
  outcome_name: string;
  mean: number;
  hdi_80_low: number;
  hdi_80_high: number;
  samples: number[]; // truncated to 200 for histogram render
}

export interface ScenarioSummary {
  scenario_id: string;
  scenario_name: string;
  outcomes: OutcomeSummary[];
}

export type ComparisonVerdict = "A_better" | "B_better" | "tie" | "ambiguous";

export interface OutcomeDelta {
  outcome_name: string;
  p_a_greater_b: number;
  mean_delta: number;
  verdict: ComparisonVerdict;
}

export interface ScenarioComparison {
  scenario_a: ScenarioSummary;
  scenario_b: ScenarioSummary;
  outcome_deltas: OutcomeDelta[];
}

// ---------------------------------------------------------------------------
// Deterministic mock generators
// ---------------------------------------------------------------------------
function seededNormal(mu: number, sigma: number, n: number, seed: number): number[] {
  const out: number[] = [];
  for (let i = 0; i < n; i++) {
    const u1 = (((i + 1 + seed) * 9301 + 49297) % 233280) / 233280 + 1e-9;
    const u2 = (((i + 7 + seed) * 4801 + 21013) % 200003) / 200003 + 1e-9;
    const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
    out.push(mu + sigma * z);
  }
  return out;
}

// Reference comparison: A = Vigabatrin intervention (mean 0.25 seizures/day),
// B = control (mean 0.8 seizures/day). Lower is better -> B "wins" on raw
// magnitude but A is the desired intervention; the verdict logic reflects
// "A_better" since A drives outcome DOWN, matching the clinical sign.
const MOCK_COMPARISON: ScenarioComparison = {
  scenario_a: {
    scenario_id: "scn_a_vigabatrin",
    scenario_name: "Vigabatrin 50 mg/kg/day",
    outcomes: [
      {
        outcome_name: "seizure_freq_per_day",
        mean: 0.25,
        hdi_80_low: 0.0,
        hdi_80_high: 0.9,
        samples: seededNormal(0.25, 0.3, 200, 11).map((v) =>
          Math.max(0, v),
        ),
      },
    ],
  },
  scenario_b: {
    scenario_id: "scn_b_control",
    scenario_name: "No intervention",
    outcomes: [
      {
        outcome_name: "seizure_freq_per_day",
        mean: 0.8,
        hdi_80_low: 0.1,
        hdi_80_high: 2.6,
        samples: seededNormal(0.8, 0.7, 200, 12).map((v) =>
          Math.max(0, v),
        ),
      },
    ],
  },
  outcome_deltas: [
    {
      outcome_name: "seizure_freq_per_day",
      p_a_greater_b: 0.18, // P(A > B); since lower is better, low value -> A wins
      mean_delta: 0.25 - 0.8, // negative -> A reduces outcome
      verdict: "A_better",
    },
  ],
};

const MOCK_SCENARIO_LIST: ScenarioRecord[] = [
  {
    scenario_id: "scn_a_vigabatrin",
    scenario_hash: "h_a_vig",
    name: "Vigabatrin 50 mg/kg/day",
    scm_id: "reference_vigabatrin_seizure",
    created_at: "2026-12-20T10:00:00Z",
    n_samples: 1000,
    horizon_days: 90,
  },
  {
    scenario_id: "scn_b_control",
    scenario_hash: "h_b_ctrl",
    name: "No intervention",
    scm_id: "reference_vigabatrin_seizure",
    created_at: "2026-12-20T10:05:00Z",
    n_samples: 1000,
    horizon_days: 90,
  },
];

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------
export async function saveScenario(
  scenario: Scenario,
): Promise<{ scenario_id: string; scenario_hash: string }> {
  if (MOCK_MODE) {
    const id = `scn_mock_${Math.abs(hashString(scenario.name)).toString(16)}`;
    return { scenario_id: id, scenario_hash: id };
  }
  try {
    const res = await fetch(`${API_BASE}/api/sim/scenario`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(scenario),
    });
    if (!res.ok) {
      throw new Error(`save scenario HTTP ${res.status}`);
    }
    return (await res.json()) as { scenario_id: string; scenario_hash: string };
  } catch {
    const id = `scn_mock_${Math.abs(hashString(scenario.name)).toString(16)}`;
    return { scenario_id: id, scenario_hash: id };
  }
}

export async function listScenarios(): Promise<ScenarioRecord[]> {
  if (MOCK_MODE) {
    return MOCK_SCENARIO_LIST;
  }
  try {
    const res = await fetch(`${API_BASE}/api/sim/scenarios`, {
      cache: "no-store",
    });
    if (!res.ok) {
      return MOCK_SCENARIO_LIST;
    }
    return (await res.json()) as ScenarioRecord[];
  } catch {
    return MOCK_SCENARIO_LIST;
  }
}

export async function compareScenarios(
  scenarioA: string,
  scenarioB: string,
): Promise<ScenarioComparison> {
  if (MOCK_MODE) {
    return MOCK_COMPARISON;
  }
  try {
    const res = await fetch(
      `${API_BASE}/api/sim/compare?a=${encodeURIComponent(scenarioA)}&b=${encodeURIComponent(scenarioB)}`,
      { cache: "no-store" },
    );
    if (!res.ok) {
      return MOCK_COMPARISON;
    }
    return (await res.json()) as ScenarioComparison;
  } catch {
    return MOCK_COMPARISON;
  }
}

function hashString(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = (h << 5) - h + s.charCodeAt(i);
    h |= 0;
  }
  return h;
}

export const __MOCK_MODE__ = MOCK_MODE;
export const __MOCK_COMPARISON__ = MOCK_COMPARISON;
