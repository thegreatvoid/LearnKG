import { NODE_TYPE_COLOR_VAR, NODE_TYPE_LABEL } from "../../utils/nodeStyles";
import type { GraphNodeType } from "../../types/api";

const ORDER: GraphNodeType[] = ["central", "prerequisite", "related", "knowledge_gap"];

export default function Legend() {
  return (
    <div
      className="absolute bottom-3 left-3 z-10 rounded-lg border px-3 py-2 text-xs shadow-sm"
      style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
    >
      <div className="flex flex-col gap-1.5">
        {ORDER.map((type) => (
          <div key={type} className="flex items-center gap-2">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full border"
              style={{
                borderColor: NODE_TYPE_COLOR_VAR[type],
                background: type === "central" ? NODE_TYPE_COLOR_VAR[type] : "transparent",
                borderStyle: type === "knowledge_gap" ? "dashed" : "solid",
              }}
            />
            <span style={{ color: "var(--color-text-muted)" }}>{NODE_TYPE_LABEL[type]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
