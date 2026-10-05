import { useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  type Node,
  type NodeMouseHandler,
  ReactFlowProvider,
} from "reactflow";
import "reactflow/dist/style.css";
import type { LocalizedGraph } from "../../types/api";
import ConceptNode from "./ConceptNode";
import { layoutGraph } from "./layout";
import Legend from "./Legend";

const nodeTypes = { concept: ConceptNode };

interface GraphPanelProps {
  graph: LocalizedGraph | null;
  onSelectNode: (nodeId: string | null) => void;
  focusId?: string | null;
  exploredIds?: Set<string>;
  showLegend?: boolean;
  fitKey?: string; // pass a value that changes only when the view should re-fit (e.g. per query, not per merge)
}

export default function GraphPanel({
  graph,
  onSelectNode,
  focusId,
  exploredIds,
  showLegend = true,
  fitKey,
}: GraphPanelProps) {
  const { nodes, edges } = useMemo(
    () => (graph ? layoutGraph(graph, { focusId, exploredIds }) : { nodes: [], edges: [] }),
    [graph, focusId, exploredIds],
  );

  return (
    <div className="relative h-full w-full">
      {!graph || graph.nodes.length === 0 ? (
        <EmptyState />
      ) : (
        <ReactFlowProvider>
          <ReactFlow
            key={fitKey ?? graph.nodes.map((n) => n.id).join(",")}
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.3 }}
            minZoom={0.2}
            maxZoom={2}
            onNodeClick={((_, node: Node) => onSelectNode(node.id)) as NodeMouseHandler}
            onPaneClick={() => onSelectNode(null)}
            proOptions={{ hideAttribution: true }}
          >
            <Background gap={20} color="var(--color-border)" />
            <Controls showInteractive={false} />
          </ReactFlow>
          {showLegend && <Legend />}
        </ReactFlowProvider>
      )}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex h-full w-full flex-col items-center justify-center gap-2 text-center px-8">
      <div
        className="h-12 w-12 rounded-full border-2 border-dashed"
        style={{ borderColor: "var(--color-border)" }}
      />
      <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>
        Ask a question to build a localized knowledge graph around the concept it touches.
      </p>
    </div>
  );
}
