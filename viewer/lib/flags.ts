// viewer/lib/flags.ts - Phase 7.7 feature flags
//
// GO state defaults (all true). NO-GO rollback procedure per spec
// §5.2: flip the relevant flag to `false` and redeploy. Backend APIs
// stay live; only the visible UI surfaces gate.
//
// Each flag's comment notes (a) the phase that owns the surface and
// (b) the NO-GO action a Shako-led rollback would take.

export const FEATURE_FLAGS = {
  // /[locale]/twin - Phase 7.6 Twin Status route.
  // NO-GO action: flip to false to hide the page; the wife sees the
  // pre-v7.0 Status Cockpit only.
  TWIN_VIEW_ENABLED: true,

  // /[locale]/causal - Phase 7.6 SCM/causal-graph viewer.
  // NO-GO action: flip to false to hide the page; backend CRUD still
  // works for Shako via direct API.
  CAUSAL_VIEW_ENABLED: true,

  // /[locale]/simulate - Phase 7.6 Simulation Studio.
  // NO-GO action: flip to false; doctor cannot run scenarios from UI,
  // but Phase 7.3 sim/api.py remains callable from CLI.
  SIM_VIEW_ENABLED: true,

  // /[locale]/drift - Phase 7.6 posterior-drift view.
  // NO-GO action: flip to false; PNG renders remain in
  // brain/belief/snapshots/ for offline inspection.
  DRIFT_VIEW_ENABLED: true,

  // StatusCockpit Twin Status widget - Phase 7.6 refactor.
  // NO-GO action: flip to false; Status Cockpit reverts to v6.1 layout.
  STATUS_COCKPIT_TWIN_WIDGET: true,

  // Phase 7.4 Telegram active-question outbound.
  // NO-GO action: flip to false to FREEZE outbound questions; in-app
  // responses still parse to keep the audit chain warm.
  ACTIVE_QUESTION_OUTBOUND: true,

  // Phase 7.2 SCM CRUD editor in the UI.
  // NO-GO action: flip to false; SCM definition stays read-only.
  SCM_EDITOR_ENABLED: true,

  // Phase 7.5 escape-hatch / constitutional override panel.
  // NO-GO action: keep true even on rollback - the audit panel is
  // independently valuable. Disable ONLY if the panel itself ships
  // a regression.
  CONSTITUTIONAL_OVERRIDE_PANEL: true,
} as const;

export type FeatureFlag = keyof typeof FEATURE_FLAGS;

export function isEnabled(flag: FeatureFlag): boolean {
  return FEATURE_FLAGS[flag];
}
