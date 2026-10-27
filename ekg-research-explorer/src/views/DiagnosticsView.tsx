import React from 'react';
import { AlertTriangle, AlertOctagon, CheckCircle2, ShieldAlert, FileText } from 'lucide-react';

export const DiagnosticsView: React.FC = () => {
  return (
    <div>
      <div style={{ marginBottom: '32px' }}>
        <span className="badge badge-danger">Failure Modes & Error Auditing</span>
        <h1 style={{ marginTop: '8px' }}>Diagnostics, Semantic Contradictions & Error Analysis</h1>
        <p style={{ fontSize: '16px', color: 'var(--text-secondary)', maxWidth: '900px' }}>
          Detailed audit of the 43 ontological contradictions identified in the unconstrained LLM graph, qualitative analysis of hyponymy/meronymy confusion, and lexico-syntactic failure modes.
        </p>
      </div>

      {/* The 43 Ontological Contradictions */}
      <div className="card" style={{ marginBottom: '28px', borderLeft: '4px solid #ef4444' }}>
        <h3 style={{ margin: '0 0 10px 0', fontSize: '18px', color: '#b91c1c', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertOctagon size={18} />
          1. Reference-Free Audit: 43 Semantic Contradictions in Unconstrained LLM Graph
        </h3>
        <p>
          Because external human gold standards do not exist for the non-prerequisite relations (<em>Part-of</em>, <em>Application</em>, <em>Extension</em>, <em>Similarity</em>), we implemented automated structural consistency diagnostics in <code>kg_eval/direction_check_report.json</code>.
        </p>
        <p>
          The automated audit detected <strong>43 formal ontological contradictions</strong> in the standalone <code>kgx_v2</code> graph. These contradictions fall into three primary categories:
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', margin: '16px 0' }}>
          <div style={{ padding: '14px', background: '#fef2f2', borderRadius: 'var(--radius-md)', border: '1px solid #fecaca' }}>
            <strong style={{ color: '#991b1b', fontSize: '13.5px' }}>Reciprocal Part-Of Cycles (18 Cases):</strong>
            <p style={{ fontSize: '12.5px', color: '#7f1d1d', margin: '4px 0 0 0' }}>
              The model extracted that Concept A is part of Concept B, AND simultaneously that Concept B is part of Concept A (e.g., <em>"Ray is part-of Angle"</em> and <em>"Angle is part-of Ray"</em>), violating the asymmetry axiom of meronymy.
            </p>
          </div>

          <div style={{ padding: '14px', background: '#fef2f2', borderRadius: 'var(--radius-md)', border: '1px solid #fecaca' }}>
            <strong style={{ color: '#991b1b', fontSize: '13.5px' }}>Hyponymy vs Meronymy Conflation (15 Cases):</strong>
            <p style={{ fontSize: '12.5px', color: '#7f1d1d', margin: '4px 0 0 0' }}>
              The model confused <em>"Is-A"</em> (taxonomic subtyping) with <em>"Part-Of"</em> (structural constituent), asserting that <em>"Right Triangle is part-of Triangle"</em> rather than an extension/subtype of Triangle.
            </p>
          </div>

          <div style={{ padding: '14px', background: '#fef2f2', borderRadius: 'var(--radius-md)', border: '1px solid #fecaca' }}>
            <strong style={{ color: '#991b1b', fontSize: '13.5px' }}>Reciprocal Prerequisite Deadlocks (10 Cases):</strong>
            <p style={{ fontSize: '12.5px', color: '#7f1d1d', margin: '4px 0 0 0' }}>
              Circular prerequisite dependencies (A &prec; B and B &prec; A), causing cycles that prevent the knowledge graph from functioning as a Directed Acyclic Graph (DAG).
            </p>
          </div>
        </div>

        <div style={{ padding: '12px 14px', background: '#ecfdf5', borderRadius: 'var(--radius-md)', border: '1px solid #10b981', fontSize: '13px', color: '#047857' }}>
          <strong>How the Hybrid Pipeline Resolved This:</strong> Enforcing the deterministic reading-order forward gate and strict DAG cycle elimination in <code>kgx_v2_hybrid</code> completely purged all 43 reciprocal contradictions, guaranteeing a cycle-free prerequisite DAG.
        </div>
      </div>

      {/* Concrete Qualitative Failure Examples */}
      <h3 style={{ fontSize: '18px', marginBottom: '14px' }}>
        2. Concrete Real-World Failure Cases from the Study
      </h3>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {[
          {
            title: "Case 1: The Expository Symmetry Inversion (Angle ≺ Ray)",
            type: "Directional Reversal",
            observed: "Model predicted Angle is a prerequisite of Ray (confidence = 0.78).",
            truth: "Ground truth: Ray is a prerequisite of Angle (Ray ≺ Angle).",
            cause: "The textbook definition stated 'An angle is formed by two rays'. The model keyed on 'angle' as the first word and reversed the directional dependency.",
            remedy: "Reading-order forward gating: since Ray appears in Section 1.2 and Angle in Section 1.3, pos(Ray) < pos(Angle) corrects the orientation."
          },
          {
            title: "Case 2: The Handcrafted Glossary Omission (Alternate Interior Angles)",
            type: "Concept Recall Bottleneck",
            observed: "rule_v3 completely missed 'alternate interior angles'.",
            truth: "The concept is taught extensively in Chapter 3 (Parallel Lines).",
            cause: "The human-curated 130-term glossary only included 'angle', failing to match the composite multi-word technical term.",
            remedy: "Local LLMs successfully extracted this concept (204 concepts discovered), expanding terminology coverage."
          },
          {
            title: "Case 3: Uninformative Lexical Overlap (Plane & Point)",
            type: "AHP Feature Dilution",
            observed: "Definition overlap scored Jaccard = 0.12 (near zero), despite Point and Plane being closely linked.",
            truth: "Point is a fundamental primitive necessary to define a Plane.",
            cause: "The textbook definition of Point ('A location in space...') and Plane ('A flat two-dimensional surface...') share zero non-stopword vocabulary.",
            remedy: "Ablation proved that Definition Overlap is uninformative; simple co-occurrence and positional gap dominate."
          }
        ].map((c, idx) => (
          <div key={idx} className="card" style={{ padding: '18px 22px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <h4 style={{ margin: 0, fontSize: '15px', color: 'var(--text-primary)' }}>{c.title}</h4>
              <span className="badge badge-warning">{c.type}</span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '12.5px', margin: '8px 0' }}>
              <div style={{ padding: '8px 10px', background: '#fef2f2', borderRadius: '4px', color: '#991b1b' }}>
                <strong>Observed Output:</strong> {c.observed}
              </div>
              <div style={{ padding: '8px 10px', background: '#ecfdf5', borderRadius: '4px', color: '#047857' }}>
                <strong>Benchmark Ground Truth:</strong> {c.truth}
              </div>
            </div>

            <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '6px' }}>
              <strong>Root Cause:</strong> {c.cause}
            </div>
            <div style={{ fontSize: '12.5px', color: 'var(--primary)', marginTop: '4px' }}>
              <strong>Architectural Fix:</strong> {c.remedy}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
