// Phase 7.6 — type shim for react-plotly.js.
//
// Upstream `@types/react-plotly.js` is provided as an external @types
// package; rather than adding a devDependency in this structural sprint,
// we ship a permissive local declaration that lets dynamic-imported
// usage type-check. The runtime contract is unchanged; only the
// compile-time surface relaxes to `any`.
//
// Tighten in a follow-up by installing @types/react-plotly.js and
// removing this shim.

declare module "react-plotly.js" {
  import type { ComponentType } from "react";

  // Minimum surface used in Phase 7.6 components: data, layout, config,
  // style, onClick, className, divId.
  type PlotProps = {
    data?: unknown[];
    layout?: Record<string, unknown>;
    config?: Record<string, unknown>;
    style?: React.CSSProperties;
    className?: string;
    onClick?: (event: unknown) => void;
    onInitialized?: (figure: unknown, graphDiv: HTMLElement) => void;
    onUpdate?: (figure: unknown, graphDiv: HTMLElement) => void;
    onPurge?: (figure: unknown, graphDiv: HTMLElement) => void;
    divId?: string;
    revision?: number;
    useResizeHandler?: boolean;
  };

  const Plot: ComponentType<PlotProps>;
  export default Plot;
}
