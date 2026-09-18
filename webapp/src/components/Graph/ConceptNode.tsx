import { Handle, Position, type NodeProps } from "reactflow";
import type { GraphNode } from "../../types/api";
import { NODE_TYPE_COLOR_VAR } from "../../utils/nodeStyles";

interface ConceptNodeData {
  node: GraphNode;
}

export default function ConceptNode({ data, selected }: NodeProps<ConceptNodeData>) {
  const { node } = data;
  const isCentral = node.type === "central";
  const color = NODE_TYPE_COLOR_VAR[node.type];
  const isGap = node.type === "knowledge_gap";

  return (
    <div
      className="rounded-full border-2 px-4 py-2.5 text-center shadow-sm transition-shadow"
      style={{
        borderColor: color,
        background: isCentral ? color : "var(--color-surface)",
        color: isCentral ? "#fff" : "var(--color-text)",
        borderStyle: isGap ? "dashed" : "solid",
        minWidth: isCentral ? 170 : 150,
        boxShadow: selected ? `0 0 0 3px ${color}55` : undefined,
        fontWeight: isCentral ? 600 : 500,
        fontSize: isCentral ? 14 : 13,
      }}
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      {isGap && <span className="mr-1">⚠</span>}
      {node.label}
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </div>
  );
}
