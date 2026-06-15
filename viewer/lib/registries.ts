// Registry-awareness helpers for the clinical-trials surface.
//
// Three supported registries: ctgov (ClinicalTrials.gov), ctis (EU CTIS),
// isrctn (UK ISRCTN). Pure functions — no fabrication, no side effects.
//
// External URL patterns verified in docs/CLINICAL_TRIALS_SOURCES_RESEARCH.md:
//   ctgov  : https://clinicaltrials.gov/study/{registry_id}
//   isrctn : https://www.isrctn.com/{registry_id}
//   ctis   : https://euclinicaltrials.eu/ctis-public/view/{eu_ctr_id}

export type RegistryKey = "ctgov" | "ctis" | "isrctn";

// Shape that registryUrl / registryId need — a subset of TrialItem / TrialDetail.
export interface RegistryInfo {
  registry: string;       // 'ctgov' | 'ctis' | 'isrctn' | ''
  registryId: string;     // resolved per-registry id (nct_id for ctgov, etc.)
  euCtrId: string;        // CTIS ctNumber (e.g. '2025-520538-49-00'); empty for non-CTIS
  nctId: string;          // NCT number for ctgov rows; may be empty for others
}

/**
 * Human-readable display label for a registry key.
 * Falls back to the raw string for unknown values — never fabricates.
 */
export function registryLabel(registry: string): string {
  switch (registry) {
    case "ctgov":  return "ClinicalTrials.gov";
    case "ctis":   return "EU CTIS";
    case "isrctn": return "ISRCTN";
    default:       return registry || "ClinicalTrials.gov"; // safe default for legacy rows
  }
}

/**
 * Construct the verified external public-view URL for a trial.
 * Falls back to the CTIS public search page if the ctNumber is missing (never
 * returns a 404-guaranteed invented URL).
 */
export function registryUrl(trial: RegistryInfo): string {
  const reg = trial.registry || "ctgov";
  switch (reg) {
    case "ctgov":
      return `https://clinicaltrials.gov/study/${trial.registryId || trial.nctId}`;
    case "isrctn":
      return `https://www.isrctn.com/${trial.registryId}`;
    case "ctis": {
      // eu_ctr_id is the ctNumber (e.g. "2025-520538-49-00").
      // Public view URL verified in docs/CLINICAL_TRIALS_SOURCES_RESEARCH.md.
      const ctNumber = trial.euCtrId || trial.registryId;
      if (ctNumber) {
        return `https://euclinicaltrials.eu/ctis-public/view/${ctNumber}`;
      }
      // Fallback: CTIS public search page — better than a 404.
      return "https://euclinicaltrials.eu/ctis-public/search";
    }
    default:
      // Unknown registry — fall back to ctgov pattern.
      return `https://clinicaltrials.gov/study/${trial.nctId || trial.registryId}`;
  }
}

/**
 * The id string to display for this trial (visible in the UI chip).
 *   ctgov   → NCT id  (e.g. "NCT06123456")
 *   ctis    → ctNumber / eu_ctr_id  (e.g. "2025-520538-49-00")
 *   isrctn  → registry_id with ISRCTN prefix if not already present
 */
export function registryDisplayId(trial: RegistryInfo): string {
  const reg = trial.registry || "ctgov";
  switch (reg) {
    case "ctgov":
      return trial.nctId || trial.registryId || "";
    case "ctis":
      return trial.euCtrId || trial.registryId || "";
    case "isrctn": {
      const id = trial.registryId || "";
      // Registry stores bare number (e.g. "61218504") or full "ISRCTN61218504".
      if (id && !id.toUpperCase().startsWith("ISRCTN")) return `ISRCTN${id}`;
      return id;
    }
    default:
      return trial.registryId || trial.nctId || "";
  }
}
