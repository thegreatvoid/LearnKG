import type { ReactNode } from "react";
import type { QueryResponse } from "../../types/api";
import { CONFIDENCE_COLOR } from "../../utils/nodeStyles";

interface InsightsPanelProps {
  response: QueryResponse | null;
  onSelectConcept: (label: string) => void;
}

export default function InsightsPanel({ response, onSelectConcept }: InsightsPanelProps) {
  if (!response) {
    return (
      <div className="p-4 text-sm" style={{ color: "var(--color-text-muted)" }}>
        Insights for your question will appear here.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 overflow-y-auto p-4">
      <Card title="Key Concept">
        {response.key_concept ? (
          <Pill label={response.key_concept.label} onClick={() => onSelectConcept(response.key_concept!.label)} />
        ) : (
          <Empty />
        )}
      </Card>

      <Card title="Prerequisites">
        {response.prerequisites.length ? (
          <div className="flex flex-wrap gap-1.5">
            {response.prerequisites.map((c) => (
              <Pill key={c.id} label={c.label} onClick={() => onSelectConcept(c.label)} />
            ))}
          </div>
        ) : (
          <Empty />
        )}
      </Card>

      <Card title="Possible Knowledge Gaps">
        {response.knowledge_gaps.length ? (
          <ul className="flex flex-col gap-2">
            {response.knowledge_gaps.map((g) => (
              <li key={g.concept.id}>
                <button
                  onClick={() => onSelectConcept(g.concept.label)}
                  className="flex w-full items-center justify-between rounded-md border px-2.5 py-1.5 text-left text-sm hover:opacity-80"
                  style={{ borderColor: "var(--color-border)" }}
                >
                  <span>⚠ {g.concept.label}</span>
                  <span className="text-xs font-semibold" style={{ color: CONFIDENCE_COLOR[g.confidence] }}>
                    {g.confidence}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <Empty text="No gaps detected for this question." />
        )}
      </Card>

      <Card title="Related Concepts">
        {response.related_concepts.length ? (
          <div className="flex flex-wrap gap-1.5">
            {response.related_concepts.map((c) => (
              <Pill key={c.id} label={c.label} onClick={() => onSelectConcept(c.label)} />
            ))}
          </div>
        ) : (
          <Empty />
        )}
      </Card>
    </div>
  );
}

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-xl border p-3" style={{ borderColor: "var(--color-border)" }}>
      <h4 className="mb-2 text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--color-text-muted)" }}>
        {title}
      </h4>
      {children}
    </div>
  );
}

function Pill({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="rounded-full border px-2.5 py-1 text-xs font-medium hover:opacity-80"
      style={{ borderColor: "var(--color-border)", background: "var(--color-accent-soft)" }}
    >
      {label}
    </button>
  );
}

function Empty({ text = "—" }: { text?: string }) {
  return (
    <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>
      {text}
    </p>
  );
}
