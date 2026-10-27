import React, { useState, useMemo } from 'react';
import { SAMPLE_GRAPH_NODES, SAMPLE_GRAPH_EDGES, ConceptNode, RelationEdge } from '../data/researchData';
import { ZoomIn, ZoomOut, RotateCcw, Filter, Info, ArrowRight, ShieldCheck, AlertCircle } from 'lucide-react';

export const InteractiveGraphExplorer: React.FC = () => {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>("triangle");
  const [filterPrereq, setFilterPrereq] = useState(true);
  const [filterPartOf, setFilterPartOf] = useState(true);
  const [filterApp, setFilterApp] = useState(true);
  const [filterExt, setFilterExt] = useState(true);
  const [filterSim, setFilterSim] = useState(true);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [highlightMode, setHighlightMode] = useState<'all' | 'ancestors' | 'descendants'>('all');

  // Filter edges based on toggles
  const visibleEdges = useMemo(() => {
    return SAMPLE_GRAPH_EDGES.filter(edge => {
      if (edge.type === 'prerequisite' && !filterPrereq) return false;
      if (edge.type === 'part_of' && !filterPartOf) return false;
      if (edge.type === 'application' && !filterApp) return false;
      if (edge.type === 'extension' && !filterExt) return false;
      if (edge.type === 'similarity' && !filterSim) return false;
      return true;
    });
  }, [filterPrereq, filterPartOf, filterApp, filterExt, filterSim]);

  // Selected node details
  const selectedNode = useMemo(() => {
    return SAMPLE_GRAPH_NODES.find(n => n.id === selectedNodeId) || null;
  }, [selectedNodeId]);

  // Ancestors and Descendants
  const { ancestors, descendants, incomingEdges, outgoingEdges } = useMemo(() => {
    if (!selectedNodeId) return { ancestors: new Set<string>(), descendants: new Set<string>(), incomingEdges: [], outgoingEdges: [] };

    const inEdges = visibleEdges.filter(e => e.target === selectedNodeId);
    const outEdges = visibleEdges.filter(e => e.source === selectedNodeId);

    // Compute ancestors (DFS on incoming prerequisite/part-of edges)
    const anc = new Set<string>();
    const dfsAnc = (curr: string) => {
      visibleEdges.forEach(e => {
        if (e.target === curr && (e.type === 'prerequisite' || e.type === 'part_of')) {
          if (!anc.has(e.source)) {
            anc.add(e.source);
            dfsAnc(e.source);
          }
        }
      });
    };
    dfsAnc(selectedNodeId);

    // Compute descendants (DFS on outgoing prerequisite/part-of edges)
    const desc = new Set<string>();
    const dfsDesc = (curr: string) => {
      visibleEdges.forEach(e => {
        if (e.source === curr && (e.type === 'prerequisite' || e.type === 'part_of')) {
          if (!desc.has(e.target)) {
            desc.add(e.target);
            dfsDesc(e.target);
          }
        }
      });
    };
    dfsDesc(selectedNodeId);

    return { ancestors: anc, descendants: desc, incomingEdges: inEdges, outgoingEdges: outEdges };
  }, [selectedNodeId, visibleEdges]);

  // Layout node coordinates (2D topological circular/layered layout)
  const nodePositions = useMemo(() => {
    const posMap: Record<string, { x: number; y: number }> = {};
    const width = 850;
    const height = 550;

    // Arrange nodes by Chapter tiers horizontally
    const chapterGroups: Record<number, ConceptNode[]> = {};
    SAMPLE_GRAPH_NODES.forEach(n => {
      if (!chapterGroups[n.chapter]) chapterGroups[n.chapter] = [];
      chapterGroups[n.chapter].push(n);
    });

    const chapters = Object.keys(chapterGroups).map(Number).sort((a, b) => a - b);
    const xStep = (width - 160) / (chapters.length - 1 || 1);

    chapters.forEach((chap, cIdx) => {
      const nodesInChap = chapterGroups[chap];
      const yStep = (height - 120) / (nodesInChap.length + 1 || 1);
      nodesInChap.forEach((node, nIdx) => {
        posMap[node.id] = {
          x: 80 + cIdx * xStep,
          y: 60 + (nIdx + 1) * yStep
        };
      });
    });

    return posMap;
  }, []);

  const getEdgeStyle = (type: RelationEdge['type']) => {
    switch (type) {
      case 'prerequisite':
        return { stroke: '#2563eb', strokeWidth: 2, strokeDasharray: 'none', marker: 'url(#arrow-prereq)' };
      case 'part_of':
        return { stroke: '#10b981', strokeWidth: 2, strokeDasharray: '4 4', marker: 'url(#arrow-partof)' };
      case 'application':
        return { stroke: '#8b5cf6', strokeWidth: 2, strokeDasharray: '6 3', marker: 'url(#arrow-app)' };
      case 'extension':
        return { stroke: '#f59e0b', strokeWidth: 1.8, strokeDasharray: '2 3', marker: 'url(#arrow-ext)' };
      case 'similarity':
        return { stroke: '#64748b', strokeWidth: 1.5, strokeDasharray: 'none', marker: 'none' };
    }
  };

  return (
    <div className="card" style={{ padding: '24px', marginBottom: '32px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
        <div>
          <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>Interactive Educational Knowledge Graph</span>
            <span className="badge badge-primary">24 Nodes | 5 Relation Types</span>
          </h3>
          <p style={{ margin: '4px 0 0 0', fontSize: '13.5px' }}>
            Click any concept node to inspect its formal definition, textbook chapter, and prerequisite dependency pathways.
          </p>
        </div>

        {/* Filter controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px', cursor: 'pointer', color: '#2563eb', fontWeight: 600 }}>
            <input type="checkbox" checked={filterPrereq} onChange={e => setFilterPrereq(e.target.checked)} />
            Prerequisite (u ≺ v)
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px', cursor: 'pointer', color: '#10b981', fontWeight: 600 }}>
            <input type="checkbox" checked={filterPartOf} onChange={e => setFilterPartOf(e.target.checked)} />
            Part-of (u ⊂ v)
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px', cursor: 'pointer', color: '#8b5cf6', fontWeight: 600 }}>
            <input type="checkbox" checked={filterApp} onChange={e => setFilterApp(e.target.checked)} />
            Application (u → v)
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px', cursor: 'pointer', color: '#f59e0b', fontWeight: 600 }}>
            <input type="checkbox" checked={filterExt} onChange={e => setFilterExt(e.target.checked)} />
            Extension (u ⇒ v)
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px', cursor: 'pointer', color: '#64748b', fontWeight: 600 }}>
            <input type="checkbox" checked={filterSim} onChange={e => setFilterSim(e.target.checked)} />
            Similarity (u ≈ v)
          </label>
        </div>
      </div>

      {/* Main graph canvas & side panel */}
      <div style={{ display: 'grid', gridTemplateColumns: selectedNode ? '1fr 340px' : '1fr', gap: '20px' }}>
        <div style={{ position: 'relative', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-lg)', backgroundColor: 'var(--bg-subtle)', overflow: 'hidden' }}>
          {/* Zoom controls */}
          <div style={{ position: 'absolute', top: '12px', right: '12px', display: 'flex', gap: '6px', zIndex: 10 }}>
            <button className="btn-icon" onClick={() => setZoomLevel(z => Math.min(1.6, z + 0.15))} title="Zoom In">
              <ZoomIn size={15} />
            </button>
            <button className="btn-icon" onClick={() => setZoomLevel(z => Math.max(0.7, z - 0.15))} title="Zoom Out">
              <ZoomOut size={15} />
            </button>
            <button className="btn-icon" onClick={() => setZoomLevel(1)} title="Reset Zoom">
              <RotateCcw size={15} />
            </button>
          </div>

          {/* Chapter Guide Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 24px', backgroundColor: 'var(--bg-surface)', borderBottom: '1px solid var(--border-color)', fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            <span>← Ch 1: Basics</span>
            <span>Ch 3: Lines</span>
            <span>Ch 4: Triangles</span>
            <span>Ch 6: Polygons</span>
            <span>Ch 8: Trig</span>
            <span>Ch 10: Circles →</span>
          </div>

          <svg
            viewBox="0 0 880 580"
            style={{
              width: '100%',
              height: '520px',
              transform: `scale(${zoomLevel})`,
              transformOrigin: 'center center',
              transition: 'transform 0.2s ease'
            }}
          >
            <defs>
              <marker id="arrow-prereq" viewBox="0 0 10 10" refX="21" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1.5 L 9 5 L 0 8.5 z" fill="#2563eb" />
              </marker>
              <marker id="arrow-partof" viewBox="0 0 10 10" refX="21" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1.5 L 9 5 L 0 8.5 z" fill="#10b981" />
              </marker>
              <marker id="arrow-app" viewBox="0 0 10 10" refX="21" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1.5 L 9 5 L 0 8.5 z" fill="#8b5cf6" />
              </marker>
              <marker id="arrow-ext" viewBox="0 0 10 10" refX="21" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1.5 L 9 5 L 0 8.5 z" fill="#f59e0b" />
              </marker>
            </defs>

            {/* Edges */}
            {visibleEdges.map((edge, idx) => {
              const srcPos = nodePositions[edge.source];
              const tgtPos = nodePositions[edge.target];
              if (!srcPos || !tgtPos) return null;

              const isEdgeHighlighted =
                selectedNodeId === edge.source ||
                selectedNodeId === edge.target ||
                (ancestors.has(edge.source) && (ancestors.has(edge.target) || edge.target === selectedNodeId)) ||
                (descendants.has(edge.target) && (descendants.has(edge.source) || edge.source === selectedNodeId));

              const style = getEdgeStyle(edge.type);
              const opacity = selectedNodeId ? (isEdgeHighlighted ? 1 : 0.15) : 0.7;

              return (
                <line
                  key={idx}
                  x1={srcPos.x}
                  y1={srcPos.y}
                  x2={tgtPos.x}
                  y2={tgtPos.y}
                  stroke={style.stroke}
                  strokeWidth={isEdgeHighlighted ? style.strokeWidth + 1 : style.strokeWidth}
                  strokeDasharray={style.strokeDasharray}
                  markerEnd={edge.isDirected ? style.marker : undefined}
                  opacity={opacity}
                  style={{ transition: 'opacity 0.2s ease, stroke-width 0.2s ease' }}
                />
              );
            })}

            {/* Nodes */}
            {SAMPLE_GRAPH_NODES.map((node) => {
              const pos = nodePositions[node.id];
              if (!pos) return null;

              const isSelected = selectedNodeId === node.id;
              const isAncestor = ancestors.has(node.id);
              const isDescendant = descendants.has(node.id);

              let fillColor = 'var(--bg-surface)';
              let strokeColor = 'var(--border-color)';
              let textColor = 'var(--text-primary)';

              if (isSelected) {
                fillColor = '#2563eb';
                strokeColor = '#1d4ed8';
                textColor = '#ffffff';
              } else if (isAncestor) {
                fillColor = 'var(--primary-light)';
                strokeColor = '#2563eb';
              } else if (isDescendant) {
                fillColor = '#dcfce7';
                strokeColor = '#10b981';
              }

              return (
                <g
                  key={node.id}
                  transform={`translate(${pos.x}, ${pos.y})`}
                  onClick={() => setSelectedNodeId(node.id)}
                  style={{ cursor: 'pointer' }}
                >
                  <circle
                    r={isSelected ? 16 : 13}
                    fill={fillColor}
                    stroke={strokeColor}
                    strokeWidth={isSelected ? 3 : 2}
                    style={{ transition: 'all 0.2s ease' }}
                  />
                  <text
                    y={25}
                    textAnchor="middle"
                    fontSize={isSelected ? "11.5px" : "10px"}
                    fontWeight={isSelected ? 700 : 500}
                    fill="var(--text-primary)"
                    style={{ pointerEvents: 'none' }}
                  >
                    {node.name}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* Selected Node Inspector Drawer */}
        {selectedNode && (
          <div style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-lg)', padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <h4 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
                  {selectedNode.name}
                </h4>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                  Chapter {selectedNode.chapter} (Sec {selectedNode.section}) • {selectedNode.chapterName}
                </div>
              </div>
              {selectedNode.matchedALCPL ? (
                <span className="badge badge-success" title="Matched to AL-CPL Geometry benchmark">
                  <ShieldCheck size={12} /> AL-CPL Ground Truth
                </span>
              ) : (
                <span className="badge badge-warning" title="Concept present in CK-12 but unmapped in AL-CPL">
                  Textbook Only
                </span>
              )}
            </div>

            <div>
              <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '4px' }}>
                Verbatim Textbook Definition
              </div>
              <div style={{ fontSize: '13px', fontStyle: 'italic', color: 'var(--text-secondary)', backgroundColor: 'var(--bg-subtle)', padding: '10px 12px', borderRadius: 'var(--radius-md)', borderLeft: '3px solid var(--primary)' }}>
                "{selectedNode.definition}"
              </div>
            </div>

            {/* Prerequisite Ancestor Paths */}
            <div>
              <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--primary)', marginBottom: '6px' }}>
                Prerequisite Ancestors ({ancestors.size})
              </div>
              {ancestors.size === 0 ? (
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Foundational primitive (No prior prerequisites).</div>
              ) : (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                  {Array.from(ancestors).map(ancId => {
                    const node = SAMPLE_GRAPH_NODES.find(n => n.id === ancId);
                    return (
                      <span
                        key={ancId}
                        onClick={() => setSelectedNodeId(ancId)}
                        style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '4px', backgroundColor: 'var(--primary-light)', color: '#2563eb', cursor: 'pointer', fontWeight: 600 }}
                      >
                        {node?.name || ancId}
                      </span>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Dependent Concepts */}
            <div>
              <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: '#10b981', marginBottom: '6px' }}>
                Direct Dependents ({outgoingEdges.length})
              </div>
              {outgoingEdges.length === 0 ? (
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Terminal leaf concept.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '140px', overflowY: 'auto' }}>
                  {outgoingEdges.map((e, idx) => {
                    const tgt = SAMPLE_GRAPH_NODES.find(n => n.id === e.target);
                    return (
                      <div
                        key={idx}
                        onClick={() => setSelectedNodeId(e.target)}
                        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '12px', padding: '6px 8px', borderRadius: '4px', backgroundColor: 'var(--bg-subtle)', cursor: 'pointer' }}
                      >
                        <span style={{ fontWeight: 600 }}>{tgt?.name}</span>
                        <span className="badge badge-primary" style={{ fontSize: '9px', textTransform: 'capitalize' }}>
                          {e.type.replace('_', ' ')}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
