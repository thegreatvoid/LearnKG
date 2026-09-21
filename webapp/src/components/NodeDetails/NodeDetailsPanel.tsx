import type { QueryResponse } from "../../types/api";
import { CONFIDENCE_COLOR, NODE_TYPE_COLOR_VAR, NODE_TYPE_LABEL } from "../../utils/nodeStyles";

interface NodeDetailsPanelProps {
  response: QueryResponse;
  nodeId: string;
  onClose: () => void;
  onExplain: (label: string) => void;
}

export default function NodeDetailsPanel({ response, nodeId, onClose, onExplain }: NodeDetailsPanelProps) {
  const node = response.localized_graph.nodes.find((n) => n.id === nodeId);
  if (!node) return null;

  const gap = response.knowledge_gaps.find((g) => g.concept.id === nodeId);
  const relationships = response.localized_graph.edges.filter(
    (e) => e.source === nodeId || e.target === nodeId,
  );

  return (
    <div
      className="absolute right-3 top-3 z-10 w-72 rounded-xl border p-4 shadow-lg"
      style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <div
            className="text-[11px] font-medium uppercase tracking-wide"
            style={{ color: NODE_TYPE_COLOR_VAR[node.type] }}
          >
            {gap ? "Potential Knowledge Gap" : NODE_TYPE_LABEL[node.type]}
          </div>
          <h3 className="mt-0.5 text-base font-semibold">{node.label}</h3>
        </div>
        <button
          onClick={onClose}
          className="rounded-md p-1 text-sm leading-none hover:opacity-70"
          style={{ color: "var(--color-text-muted)" }}
          aria-label="Close"
        >
          ✕
        </button>
      </div>

      {node.description && (
        <p className="mt-3 text-sm leading-relaxed" style={{ color: "var(--color-text-muted)" }}>
          {node.description}
        </p>
      )}

      {gap && (
        <div className="mt-3 rounded-lg p-2.5 text-sm" style={{ background: "var(--color-accent-soft)" }}>
          <p className="font-medium">Why this may be needed</p>
          <p className="mt-1" style={{ color: "var(--color-text-muted)" }}>
            {gap.reason}
          </p>
          <p className="mt-2 flex items-center gap-1.5 text-xs">
            Confidence:
            <span className="font-semibold" style={{ color: CONFIDENCE_COLOR[gap.confidence] }}>
              {gap.confidence}
            </span>
          </p>
          <button
            onClick={() => onExplain(node.label)}
            className="mt-2 rounded-md border px-2.5 py-1 text-xs font-medium hover:opacity-80"
            style={{ borderColor: "var(--color-accent)", color: "var(--color-accent)" }}
          >
            Learn this concept
          </button>
        </div>
      )}

      {relationships.length > 0 && (
        <div className="mt-3">
          <p className="text-xs font-medium" style={{ color: "var(--color-text-muted)" }}>
            Relationships
          </p>
          <ul className="mt-1 space-y-1 text-sm">
            {relationships.map((r, i) => {
              const otherId = r.source === nodeId ? r.target : r.source;
              const other = response.localized_graph.nodes.find((n) => n.id === otherId);
              const arrow = r.source === nodeId ? "→" : "←";
              return (
                <li key={i} style={{ color: "var(--color-text-muted)" }}>
                  <span className="font-medium" style={{ color: "var(--color-text)" }}>
                    {r.type}
                  </span>{" "}
                  {arrow} {other?.label ?? otherId}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {!gap && node.type !== "central" && (
        <button
          onClick={() => onExplain(node.label)}
          className="mt-3 rounded-md border px-2.5 py-1 text-xs font-medium hover:opacity-80"
          style={{ borderColor: "var(--color-border)", color: "var(--color-text)" }}
        >
          Explain this concept
        </button>
      )}
    </div>
  );
}
