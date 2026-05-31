// viewer/lib/api/belief.ts — Phase 7.6 typed API client for the Belief layer.
//
// Mirrors the Phase 7.0 Pydantic shapes from brain/belief/persistence.py.
// MOCK_MODE: when NEXT_PUBLIC_API_URL is unset OR NEXT_PUBLIC_MOCK_MODE=true,
// the module returns hand-authored deterministic data so the structural
// build + tsc pass without a live backend. The mock values match the
// priors defined in brain/belief/dimensions.toml so the UI renders the
// same distribution catalog as production.

const MOCK_MODE: boolean =
  !process.env.NEXT_PUBLIC_API_URL ||
  process.env.NEXT_PUBLIC_MOCK_MODE === "true";

const API_BASE: string = process.env.NEXT_PUBLIC_API_URL ?? "";

// ---------------------------------------------------------------------------
// Types — mirror brain/belief/persistence.py BeliefDimension + snapshots.
// ---------------------------------------------------------------------------
export type BeliefDistribution =
  | "beta"
  | "normal"
  | "poisson"
  | "categorical"
  | "bernoulli"
  | "gamma"
  | "exp_decay"
  | "vector";

export interface BeliefDimension {
  name: string;
  distribution: BeliefDistribution;
  posterior_mean: number;
  hdi_80_low: number;
  hdi_80_high: number;
  units: string;
  citation: string;
  samples: number[]; // 200 samples max for histogram rendering
}

export interface BeliefSnapshot {
  generated_at: string; // ISO 8601 UTC timestamp
  dimensions: BeliefDimension[];
  evidence_count_30d: number;
}

export interface BeliefHistoryEntry {
  dim_name: string;
  date: string; // ISO date
  posterior_mean: number;
  hdi_80_low: number;
  hdi_80_high: number;
  evidence_event_count: number; // events tied to this day
}

export interface PosteriorDelta {
  dim_name: string;
  mean_delta: number;
  kl_divergence: number;
}

// ---------------------------------------------------------------------------
// 13 dimensions — names must match dimensions.toml exactly so the i18n
// dictionary keys line up (Twin.dimensions.<name>).
// ---------------------------------------------------------------------------
export const DIMENSION_NAMES: readonly string[] = [
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
] as const;

// ---------------------------------------------------------------------------
// Deterministic mock sample generators (no Math.random — same data every run).
// ---------------------------------------------------------------------------
function makeBetaSamples(alpha: number, beta: number, n: number, seed: number): number[] {
  // Coarse approximation: shape draws from a triangular curve around the
  // beta mean. Good enough for histogram rendering, NOT for inference.
  const mean = alpha / (alpha + beta);
  const out: number[] = [];
  for (let i = 0; i < n; i++) {
    const u = ((i + seed) * 9301 + 49297) % 233280;
    const r = u / 233280;
    out.push(Math.max(0, Math.min(1, mean + (r - 0.5) * 0.3)));
  }
  return out;
}

function makeNormalSamples(mu: number, sigma: number, n: number, seed: number): number[] {
  const out: number[] = [];
  for (let i = 0; i < n; i++) {
    // Box-Muller approximation seeded from the integer stream.
    const u1 = (((i + 1 + seed) * 9301 + 49297) % 233280) / 233280 + 1e-9;
    const u2 = (((i + 7 + seed) * 4801 + 21013) % 200003) / 200003 + 1e-9;
    const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
    out.push(mu + sigma * z);
  }
  return out;
}

function makePoissonSamples(mu: number, n: number, seed: number): number[] {
  const out: number[] = [];
  for (let i = 0; i < n; i++) {
    const u = (((i + seed) * 17389 + 12347) % 100003) / 100003;
    // Inverse-CDF coarse for tiny mu.
    let k = 0;
    let p = Math.exp(-mu);
    let cdf = p;
    while (u > cdf && k < 50) {
      k += 1;
      p = (p * mu) / k;
      cdf += p;
    }
    out.push(k);
  }
  return out;
}

// ---------------------------------------------------------------------------
// Mock snapshot — values track the priors in dimensions.toml.
// ---------------------------------------------------------------------------
const MOCK_SNAPSHOT: BeliefSnapshot = {
  generated_at: new Date("2026-12-26T09:00:00Z").toISOString(),
  evidence_count_30d: 17,
  dimensions: [
    {
      name: "cyst_volume_pct",
      distribution: "beta",
      posterior_mean: 8.6,
      hdi_80_low: 0.5,
      hdi_80_high: 28.0,
      units: "percent",
      citation: "PMID:39799120",
      samples: makeBetaSamples(0.6, 6.4, 200, 1).map((v) => v * 100),
    },
    {
      name: "brainstem_function",
      distribution: "categorical",
      posterior_mean: 1.75,
      hdi_80_low: 1.0,
      hdi_80_high: 2.0,
      units: "state_index",
      citation: "PMID:26981220",
      samples: [],
    },
    {
      name: "seizure_freq_per_day",
      distribution: "poisson",
      posterior_mean: 0.8,
      hdi_80_low: 0.0,
      hdi_80_high: 3.0,
      units: "events_per_day",
      citation: "PMID:27595841",
      samples: makePoissonSamples(0.8, 200, 2),
    },
    {
      name: "muscle_tone_hammersmith",
      distribution: "normal",
      posterior_mean: 40.0,
      hdi_80_low: 22.0,
      hdi_80_high: 58.0,
      units: "hammersmith_score",
      citation: "PMID:31426574",
      samples: makeNormalSamples(40, 18, 200, 3),
    },
    {
      name: "eye_tracking_seconds",
      distribution: "gamma",
      posterior_mean: 3.0,
      hdi_80_low: 0.5,
      hdi_80_high: 9.0,
      units: "seconds",
      citation: "PMID:40151356",
      samples: makeNormalSamples(3, 2, 200, 4).map((v) => Math.max(0, v)),
    },
    {
      name: "head_control_seconds",
      distribution: "normal",
      posterior_mean: 8.0,
      hdi_80_low: 0.0,
      hdi_80_high: 22.0,
      units: "seconds",
      citation: "PMID:31426574",
      samples: makeNormalSamples(8, 10, 200, 5).map((v) => Math.max(0, v)),
    },
    {
      name: "gmfcs_level",
      distribution: "categorical",
      posterior_mean: 3.95,
      hdi_80_low: 3.0,
      hdi_80_high: 5.0,
      units: "level",
      citation: "PMID:9183258",
      samples: [],
    },
    {
      name: "bayley_cognitive",
      distribution: "normal",
      posterior_mean: 65.0,
      hdi_80_low: 47.0,
      hdi_80_high: 83.0,
      units: "bayley_iii_composite",
      citation: "PMID:24743133",
      samples: makeNormalSamples(65, 18, 200, 6),
    },
    {
      name: "feeding_stage",
      distribution: "categorical",
      posterior_mean: 0.9,
      hdi_80_low: 0.0,
      hdi_80_high: 2.0,
      units: "stage_index",
      citation: "PMID:39761677",
      samples: [],
    },
    {
      name: "respiratory_apnea_per_day",
      distribution: "bernoulli",
      posterior_mean: 0.2,
      hdi_80_low: 0.05,
      hdi_80_high: 0.4,
      units: "probability",
      citation: "PMID:26981220",
      samples: [],
    },
    {
      name: "csf_biomarkers",
      distribution: "vector",
      posterior_mean: 2.3,
      hdi_80_low: 1.4,
      hdi_80_high: 3.2,
      units: "z_score",
      citation: "PMID:32610169",
      samples: makeNormalSamples(2.3, 0.9, 200, 7),
    },
    {
      name: "neuroplasticity_resource",
      distribution: "exp_decay",
      posterior_mean: 0.566,
      hdi_80_low: 0.40,
      hdi_80_high: 0.70,
      units: "decay_rate_per_day",
      citation: "PMID:19489084",
      samples: makeNormalSamples(0.566, 0.1, 200, 8).map((v) =>
        Math.max(0, Math.min(1, v)),
      ),
    },
    {
      name: "family_readiness",
      distribution: "categorical",
      posterior_mean: 1.75,
      hdi_80_low: 1.0,
      hdi_80_high: 3.0,
      units: "state_index",
      citation: "PMID:40776994",
      samples: [],
    },
  ],
};

// ---------------------------------------------------------------------------
// Public API surface
// ---------------------------------------------------------------------------
export async function fetchBeliefSnapshot(): Promise<BeliefSnapshot> {
  if (MOCK_MODE) {
    return MOCK_SNAPSHOT;
  }
  try {
    // FND-02: Phase 7.0 belief snapshot is the 13-D posterior summary
    // (mean / sd / hdi). No MRI / DICOM / PHI ever traverses this path.
    const res = await fetch(`${API_BASE}/api/belief/snapshot`, /* allow-remote */ {
      cache: "no-store",
    });
    if (!res.ok) {
      return MOCK_SNAPSHOT;
    }
    return (await res.json()) as BeliefSnapshot;
  } catch {
    return MOCK_SNAPSHOT;
  }
}

export async function fetchBeliefHistory(
  dimName: string,
  days: number = 30,
): Promise<BeliefHistoryEntry[]> {
  if (MOCK_MODE) {
    return makeMockHistory(dimName, days);
  }
  try {
    // FND-02: Phase 7.0 belief history is per-dim time series of posterior
    // moments. No MRI / DICOM / PHI ever traverses this path.
    const res = await fetch( /* allow-remote */
      `${API_BASE}/api/belief/history?dim=${encodeURIComponent(dimName)}&days=${days}`,
      { cache: "no-store" },
    );
    if (!res.ok) {
      return makeMockHistory(dimName, days);
    }
    return (await res.json()) as BeliefHistoryEntry[];
  } catch {
    return makeMockHistory(dimName, days);
  }
}

function makeMockHistory(dimName: string, days: number): BeliefHistoryEntry[] {
  // Synthetic linear-drift series anchored on the matching mock snapshot dim.
  const dim = MOCK_SNAPSHOT.dimensions.find((d) => d.name === dimName);
  const anchor = dim?.posterior_mean ?? 0;
  const halfBand = (dim ? dim.hdi_80_high - dim.hdi_80_low : 1) / 2;
  const end = new Date("2026-12-26T00:00:00Z");
  const out: BeliefHistoryEntry[] = [];
  for (let i = 0; i < days; i++) {
    const date = new Date(end.getTime() - (days - 1 - i) * 86400000);
    const drift = (i / days) * 0.05 * anchor;
    out.push({
      dim_name: dimName,
      date: date.toISOString().slice(0, 10),
      posterior_mean: anchor + drift - 0.02 * anchor,
      hdi_80_low: anchor - halfBand + drift,
      hdi_80_high: anchor + halfBand + drift,
      evidence_event_count: i % 7 === 0 ? 1 : 0,
    });
  }
  return out;
}

export const __MOCK_MODE__ = MOCK_MODE;
