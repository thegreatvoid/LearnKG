import type { ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import type { QueryResponse } from "../../types/api";
import { CONFIDENCE_COLOR } from "../../utils/nodeStyles";

interface StructuredAnswerProps {
  response: QueryResponse;
}

export default function StructuredAnswer({ response }: StructuredAnswerProps) {
  return (
    <div className="flex flex-col gap-3">
      <div className="prose-sm text-sm leading-relaxed [&_p]:m-0">
        <ReactMarkdown>{response.answer}</ReactMarkdown>
      </div>

      {response.key_concept && (
        <Section title="Key Concept">
          <span
            className="inline-block rounded-full px-2.5 py-1 text-xs font-semibold"
            style={{ background: "var(--color-accent-soft)", color: "var(--color-accent)" }}
          >
            {response.key_concept.label}
          </span>
        </Section>
      )}

      {response.prerequisites.length > 0 && (
        <Section title="Prerequisites">
          <TagList labels={response.prerequisites.map((c) => c.label)} />
        </Section>
      )}

      {response.knowledge_gaps.length > 0 && (
        <Section title="Possible Knowledge Gaps">
          <ul className="flex flex-col gap-0.5">
            {response.knowledge_gaps.map((g) => (
              <li key={g.concept.id} className="text-xs">
                {g.concept.label} —{" "}
                <span className="font-semibold" style={{ color: CONFIDENCE_COLOR[g.confidence] }}>
                  {g.confidence} confidence
                </span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {response.related_concepts.length > 0 && (
        <Section title="Related Concepts">
          <TagList labels={response.related_concepts.map((c) => c.label)} />
        </Section>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--color-text-muted)" }}>
        {title}
      </p>
      <div className="mt-1">{children}</div>
    </div>
  );
}

function TagList({ labels }: { labels: string[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {labels.map((l) => (
        <span
          key={l}
          className="rounded-full border px-2 py-0.5 text-xs"
          style={{ borderColor: "var(--color-border)" }}
        >
          {l}
        </span>
      ))}
    </div>
  );
}
