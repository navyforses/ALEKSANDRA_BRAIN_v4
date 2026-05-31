"use client";

// viewer/app/[locale]/simulate/SimulateStudio.tsx — Phase 7.6 Client wrapper.
//
// Tiny stateful wrapper that holds the active ScenarioComparison so the
// builder + result viewer can both react to "Run Simulation". Default
// initialComparison is fetched server-side in simulate/page.tsx.

import { useState } from "react";

import {
  compareScenarios,
  saveScenario,
  type Scenario,
  type ScenarioComparison,
} from "@/lib/api/sim";
import ScenarioBuilder from "./ScenarioBuilder";
import ResultViewer from "./ResultViewer";

interface Props {
  initialComparison: ScenarioComparison | null;
  locale: "en" | "ka";
}

export default function SimulateStudio({ initialComparison, locale }: Props) {
  const [comparison, setComparison] = useState<ScenarioComparison | null>(
    initialComparison,
  );
  const [busy, setBusy] = useState(false);

  async function handleSubmit(scenario: Scenario) {
    setBusy(true);
    try {
      const { scenario_id } = await saveScenario(scenario);
      const next = await compareScenarios(scenario_id, "scn_b_control");
      setComparison(next);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
      <ScenarioBuilder onSubmit={handleSubmit} busy={busy} />
      <ResultViewer comparison={comparison} locale={locale} />
    </div>
  );
}
