import { Handle, Position, type NodeProps } from "reactflow";
import type { GraphNode } from "../../types/api";
import { NODE_TYPE_COLOR_VAR } from "../../utils/nodeStyles";

interface ConceptNodeData {
  node: GraphNode;
  dimmed?: boolean;
  isFocus?: boolean;
}

export default function ConceptNode({ data, selected }: NodeProps<ConceptNodeData>) {
  const { node, dimmed, isFocus } = data;
  const isCentral = node.type === "central";
  const isParent = node.type === "parent";
  const color = NODE_TYPE_COLOR_VAR[node.type];
  const isGap = node.type === "knowledge_gap";

  return (
    <div
      className="border-2 px-4 py-2.5 text-center shadow-sm transition-all"
      style={{
        borderColor: color,
        background: isCentral ? color : "var(--color-surface)",
        color: isCentral ? "#fff" : "var(--color-text)",
        borderStyle: isGap ? "dashed" : "solid",
        borderRadius: isParent ? 8 : 999, // squares for hierarchy/parent nodes, pills for everything else
        minWidth: isCentral ? 170 : 150,
        boxShadow: isFocus
          ? `0 0 0 3px ${color}aa`
          : selected
            ? `0 0 0 3px ${color}55`
            : undefined,
        fontWeight: isCentral ? 600 : 500,
        fontSize: isCentral ? 14 : 13,
        opacity: dimmed ? 0.35 : 1,
      }}
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      {isGap && <span className="mr-1">⚠</span>}
      {node.label}
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </div>
  );
}
