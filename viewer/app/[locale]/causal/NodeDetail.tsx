"use client";

// viewer/app/[locale]/causal/NodeDetail.tsx — Phase 7.6 Client Component.
//
// Side panel rendered next to the vis-network graph. Shows the selected
// node, its incoming + outgoing edges with mechanism + citation, and a
// link out to each PMID. Pure-client because it reads selection state.

import { useMemo } from "react";
import { useTranslations } from "next-intl";

import type {
  CausalGraphResponse,
  CausalEdge,
} from "@/lib/api/causal";

interface Props {
  graph: CausalGraphResponse;
  selectedId: number | null;
  locale: "en" | "ka";
}

function pmidUrl(citation: string): string | null {
  const m = citation.match(/PMID:(\d+)/i);
  if (m) return `https://pubmed.ncbi.nlm.nih.gov/${m[1]}/`;
  return null;
}

interface EdgeRowProps {
  edge: CausalEdge;
  otherName: string;
  direction: "in" | "out";
  label: string;
}

function EdgeRow({ edge, otherName, direction, label }: EdgeRowProps) {
  const link = pmidUrl(edge.citation);
  return (
    <li className="rounded-md border border-stone-200 bg-stone-50 p-3 text-xs leading-5 text-stone-700">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-md bg-white px-2 py-0.5 font-mono text-[10px] uppercase text-stone-600 ring-1 ring-stone-200">
          {edge.edge_type}
        </span>
        <span className="font-medium">
          {direction === "in" ? `${otherName} → ${label}` : `${label} → ${otherName}`}
        </span>
      </div>
      {edge.mechanism ? (
        <p className="mt-1 text-stone-600">{edge.mechanism}</p>
      ) : null}
      {link ? (
        <a
          href={link}
          target="_blank"
          rel="noreferrer"
          className="mt-1 inline-block font-mono text-[10px] text-cyan-700 hover:underline"
        >
          {edge.citation}
        </a>
      ) : (
        <p className="mt-1 font-mono text-[10px] text-stone-400">
          {edge.citation}
        </p>
      )}
    </li>
  );
}

export default function NodeDetail({ graph, selectedId, locale }: Props) {
  const t = useTranslations("Causal");

  const node = useMemo(
    () => graph.nodes.find((n) => n.id === selectedId) ?? null,
    [graph, selectedId],
  );

  const incoming = useMemo(
    () =>
      selectedId == null
        ? []
        : graph.edges.filter((e) => e.target === selectedId),
    [graph, selectedId],
  );
  const outgoing = useMemo(
    () =>
      selectedId == null
        ? []
        : graph.edges.filter((e) => e.source === selectedId),
    [graph, selectedId],
  );

  function nodeName(id: number): string {
    return graph.nodes.find((n) => n.id === id)?.name ?? `#${id}`;
  }

  if (!node) {
    return (
      <aside className="rounded-md border border-stone-200 bg-white p-4 text-sm text-stone-500">
        {t("noSelection")}
      </aside>
    );
  }

  return (
    <aside className="flex flex-col gap-3 rounded-md border border-stone-200 bg-white p-4">
      <header>
        <p className="font-mono text-[10px] uppercase text-stone-500">
          {t("selectedNode")} · {locale.toUpperCase()}
        </p>
        <h2 className="mt-1 text-lg font-semibold text-stone-900">
          {node.name}
        </h2>
        {node.dimension_ref ? (
          <p className="mt-1 font-mono text-[10px] text-stone-500">
            dim_ref: {node.dimension_ref}
          </p>
        ) : null}
      </header>

      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-stone-700">
          {t("parents")} ({incoming.length})
        </h3>
        <ul className="mt-2 flex flex-col gap-2">
          {incoming.length === 0 ? (
            <li className="text-xs text-stone-400">{t("noParents")}</li>
          ) : (
            incoming.map((e, idx) => (
              <EdgeRow
                key={`in-${idx}`}
                edge={e}
                otherName={nodeName(e.source)}
                direction="in"
                label={node.name}
              />
            ))
          )}
        </ul>
      </div>

      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-stone-700">
          {t("children")} ({outgoing.length})
        </h3>
        <ul className="mt-2 flex flex-col gap-2">
          {outgoing.length === 0 ? (
            <li className="text-xs text-stone-400">{t("noChildren")}</li>
          ) : (
            outgoing.map((e, idx) => (
              <EdgeRow
                key={`out-${idx}`}
                edge={e}
                otherName={nodeName(e.target)}
                direction="out"
                label={node.name}
              />
            ))
          )}
        </ul>
      </div>
    </aside>
  );
}
