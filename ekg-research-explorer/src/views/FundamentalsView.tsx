import React from 'react';
import { RELATION_ONTOLOGY } from '../data/researchData';
import { Network, GitBranch, ArrowRight, ShieldCheck, AlertCircle, HelpCircle } from 'lucide-react';

export const FundamentalsView: React.FC = () => {
  return (
    <div>
      <div style={{ marginBottom: '32px' }}>
        <span className="badge badge-primary">Graph Theory & Ontologies</span>
        <h1 style={{ marginTop: '8px' }}>Educational Knowledge Graphs & The 5-Relation Ontology</h1>
        <p style={{ fontSize: '16px', color: 'var(--text-secondary)', maxWidth: '900px' }}>
          Formal definitions of graph topology, directed acyclic graphs, reachability, and an in-depth breakdown of the five educational relationship types defined in our schema.
        </p>
      </div>

      {/* Graph Theory Fundamentals */}
      <div className="card" style={{ marginBottom: '28px' }}>
        <h3 style={{ margin: '0 0 10px 0', fontSize: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Network size={18} style={{ color: 'var(--primary)' }} />
          1. Graph Theoretical Foundations
        </h3>
        <p>
          Formally, our Educational Knowledge Graph is modeled as a typed, directed multigraph:
        </p>
        <div className="formula-card">
          G = (V, E, R, W)
        </div>
        <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
          Where <strong>V</strong> is the set of extracted geometry concepts, <strong>R</strong> is the 5-relation ontology, <strong>E &sube; V &times; R &times; V</strong> is the set of typed relation edges, and <strong>W: E &rarr; [0, 1]</strong> assigns confidence weights.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px', marginTop: '16px' }}>
          <div style={{ padding: '12px 14px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)' }}>
            <strong style={{ fontSize: '13px', color: 'var(--text-primary)' }}>Directed Acyclic Graph (DAG):</strong>
            <p style={{ fontSize: '12px', margin: '4px 0 0 0', color: 'var(--text-muted)' }}>
              Prerequisite subgraphs must contain no directed cycles. If concept A requires B, and B requires A, learning deadlocks occur.
            </p>
          </div>

          <div style={{ padding: '12px 14px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)' }}>
            <strong style={{ fontSize: '13px', color: 'var(--text-primary)' }}>Transitive Reachability:</strong>
            <p style={{ fontSize: '12px', margin: '4px 0 0 0', color: 'var(--text-muted)' }}>
              If u &prec; v and v &prec; w, then u is an indirect prerequisite of w. Computed via Floyd-Warshall transitive closure (G+).
            </p>
          </div>

          <div style={{ padding: '12px 14px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)' }}>
            <strong style={{ fontSize: '13px', color: 'var(--text-primary)' }}>Asymmetry & Irreflexivity:</strong>
            <p style={{ fontSize: '12px', margin: '4px 0 0 0', color: 'var(--text-muted)' }}>
              A concept cannot be a prerequisite of itself (irreflexive: u &not;&prec; u), and dependencies cannot run both ways (asymmetric).
            </p>
          </div>
        </div>
      </div>

      {/* The 5 Educational Relation Types */}
      <h2 style={{ fontSize: '20px', marginBottom: '16px' }}>
        2. Comprehensive Specification of the 5 Relation Types
      </h2>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {RELATION_ONTOLOGY.map((rel, idx) => {
          let badgeColor = 'badge-primary';
          let borderCol = '#2563eb';
          if (rel.type === 'part_of') { badgeColor = 'badge-success'; borderCol = '#10b981'; }
          if (rel.type === 'application') { badgeColor = 'badge-primary'; borderCol = '#8b5cf6'; }
          if (rel.type === 'extension') { badgeColor = 'badge-warning'; borderCol = '#f59e0b'; }
          if (rel.type === 'similarity') { badgeColor = 'badge-primary'; borderCol = '#64748b'; }

          return (
            <div key={rel.type} className="card" style={{ borderLeft: `4px solid ${borderCol}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', flexWrap: 'wrap', gap: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span className={`badge ${badgeColor}`} style={{ fontSize: '12px' }}>
                    Type #{idx + 1}: {rel.name}
                  </span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 700 }}>
                    {rel.symbol} ({rel.directed ? 'Directed' : 'Undirected / Symmetric'})
                  </span>
                </div>
                <span className="badge badge-primary" style={{ fontSize: '11px' }}>
                  {rel.evalStatus}
                </span>
              </div>

              <div style={{ fontSize: '14.5px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
                {rel.plainMeaning}
              </div>

              <div style={{ fontSize: '13px', color: 'var(--text-secondary)', backgroundColor: 'var(--bg-subtle)', padding: '10px 14px', borderRadius: 'var(--radius-md)', marginBottom: '14px', fontFamily: 'var(--font-mono)' }}>
                <strong>Formal Axiom:</strong> {rel.formalDef}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px', fontSize: '12.5px' }}>
                <div style={{ padding: '10px 12px', background: '#ecfdf5', borderRadius: 'var(--radius-sm)', border: '1px solid #10b981' }}>
                  <strong style={{ color: '#047857' }}>Valid Example:</strong>
                  <div style={{ color: '#065f46', marginTop: '2px' }}>{rel.example}</div>
                </div>

                <div style={{ padding: '10px 12px', background: '#fef2f2', borderRadius: 'var(--radius-sm)', border: '1px solid #ef4444' }}>
                  <strong style={{ color: '#b91c1c' }}>Counterexample:</strong>
                  <div style={{ color: '#7f1d1d', marginTop: '2px' }}>{rel.counterexample}</div>
                </div>
              </div>

              <div style={{ fontSize: '12px', color: '#b45309', borderTop: '1px solid var(--border-color)', paddingTop: '10px', marginTop: '12px' }}>
                <strong>Common Extraction Error:</strong> {rel.commonErrors}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
