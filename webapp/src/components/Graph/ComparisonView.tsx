import type { ComparisonResult } from "../../types/api";
import GraphPanel from "./GraphPanel";

interface ComparisonViewProps {
  comparison: ComparisonResult;
  onSelectNode: (nodeId: string | null) => void;
}

/** Mode 3 (spec sections 15-18): two independently navigable localized
 * graphs side by side, each with its own GraphPanel/ReactFlowProvider so
 * pan/zoom/selection stay independent, plus a shared comparison summary
 * built generically from the KG (never hardcoded per concept pair). */
export default function ComparisonView({ comparison, onSelectNode }: ComparisonViewProps) {
  const { concept_a, concept_b, summary } = comparison;

  return (
    <div className="flex h-full flex-col">
      <div className="grid min-h-0 flex-1 grid-cols-1 divide-y md:grid-cols-2 md:divide-x md:divide-y-0" style={{ borderColor: "var(--color-border)" }}>
        <div className="relative min-h-[280px]">
          <SideLabel label={concept_a.concept.label} />
          <GraphPanel
            graph={concept_a.graph}
            onSelectNode={onSelectNode}
            focusId={concept_a.concept.id}
            showLegend={false}
            fitKey={`cmp-a-${concept_a.concept.id}`}
          />
        </div>
        <div className="relative min-h-[280px]">
          <SideLabel label={concept_b.concept.label} />
          <GraphPanel
            graph={concept_b.graph}
            onSelectNode={onSelectNode}
            focusId={concept_b.concept.id}
            showLegend={false}
            fitKey={`cmp-b-${concept_b.concept.id}`}
          />
        </div>
      </div>

      {summary.length > 0 && (
        <div className="border-t p-3" style={{ borderColor: "var(--color-border)" }}>
          <h4 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--color-text-muted)" }}>
            {concept_a.concept.label} vs {concept_b.concept.label}
          </h4>
          <ul className="flex flex-col gap-1 text-sm" style={{ color: "var(--color-text)" }}>
            {summary.map((line, i) => (
              <li key={i}>{line}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function SideLabel({ label }: { label: string }) {
  return (
    <div
      className="absolute left-3 top-3 z-10 rounded-full border px-2.5 py-1 text-xs font-semibold shadow-sm"
      style={{ background: "var(--color-surface)", borderColor: "var(--color-accent)", color: "var(--color-accent)" }}
    >
      {label}
    </div>
  );
}
