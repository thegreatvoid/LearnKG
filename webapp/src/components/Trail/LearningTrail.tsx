import type { ConceptRef } from "../../types/api";

interface LearningTrailProps {
  trail: ConceptRef[];
  focusId: string | null;
  onFocus: (id: string) => void;
}

/** Ordered sequence of concepts queried this session (spec section 14). Clicking
 * an earlier concept focuses the cumulative graph on it without re-querying
 * or deleting anything already explored. */
export default function LearningTrail({ trail, focusId, onFocus }: LearningTrailProps) {
  if (trail.length === 0) return null;

  return (
    <div className="border-t p-3" style={{ borderColor: "var(--color-border)" }}>
      <h4
        className="mb-2 text-[11px] font-semibold uppercase tracking-wide"
        style={{ color: "var(--color-text-muted)" }}
      >
        Learning Trail
      </h4>
      <ol className="flex flex-col gap-1">
        {trail.map((c, i) => {
          const isFocus = c.id === focusId;
          return (
            <li key={c.id}>
              <button
                onClick={() => onFocus(c.id)}
                className="flex w-full items-center gap-2 rounded-md px-2 py-1 text-left text-xs hover:opacity-80"
                style={{
                  background: isFocus ? "var(--color-accent-soft)" : "transparent",
                  color: isFocus ? "var(--color-accent)" : "var(--color-text)",
                  fontWeight: isFocus ? 600 : 400,
                }}
              >
                <span style={{ color: "var(--color-text-muted)" }}>{String(i + 1).padStart(2, "0")}</span>
                {c.label}
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
