import React from 'react';
import { PipelineFlowchart } from '../components/PipelineFlowchart';
import { GitMerge, Cpu, Compass, BookOpen, AlertCircle } from 'lucide-react';

export const PipelinesView: React.FC = () => {
  return (
    <div>
      <div style={{ marginBottom: '32px' }}>
        <span className="badge badge-primary">End-to-End Architectures</span>
        <h1 style={{ marginTop: '8px' }}>Pipeline Architecture & Stage Walkthrough</h1>
        <p style={{ fontSize: '16px', color: 'var(--text-secondary)', maxWidth: '900px' }}>
          Compare the three primary knowledge graph construction pipelines: the symbolic rule pipeline (<code>rule_v3</code>), the unconstrained local LLM pipeline (<code>kgx_v2</code>), and the neuro-symbolic hybrid pipeline (<code>kgx_v2_hybrid</code>).
        </p>
      </div>

      {/* Interactive Flowchart */}
      <PipelineFlowchart />

      {/* Detailed 3-Pipeline Comparison Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', marginTop: '20px' }}>
        {/* Pipeline 1: rule_v3 */}
        <div className="card" style={{ borderLeft: '4px solid #64748b' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="badge badge-primary">Pipeline 1</span>
              <h3 style={{ margin: 0, fontSize: '18px' }}>rule_v3: Symbolic Information Extraction</h3>
            </div>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)' }}>Precision: 0.875 | Recall: 0.027</span>
          </div>

          <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
            <strong>Mechanism:</strong> Handcrafted 130-word geometry glossary + regex matching for definition sentences. Generates candidate pairs based on sentence-level co-occurrence. Scores edges using the Analytic Hierarchy Process composite formula: <code>W = 0.52S + 0.24C + 0.09P + 0.15E</code>. Applies lexico-syntactic Hearst patterns (<em>"is required for"</em>) for prerequisite assignment.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', fontSize: '13px', marginTop: '8px' }}>
            <div style={{ padding: '10px 12px', background: '#ecfdf5', borderRadius: 'var(--radius-sm)', border: '1px solid #10b981' }}>
              <strong style={{ color: '#047857' }}>Main Advantage:</strong> 100% directional accuracy on matched edges (7/7 correct) due to strict explicit connective syntax. Highly predictable and explainable.
            </div>
            <div style={{ padding: '10px 12px', background: '#fef2f2', borderRadius: 'var(--radius-sm)', border: '1px solid #ef4444' }}>
              <strong style={{ color: '#b91c1c' }}>Main Limitation:</strong> Catastrophic recall collapse (0.027). Authors rarely write explicit pedagogical warnings in textbooks.
            </div>
          </div>
        </div>

        {/* Pipeline 2: kgx_v2 */}
        <div className="card" style={{ borderLeft: '4px solid #2563eb' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="badge badge-primary">Pipeline 2</span>
              <h3 style={{ margin: 0, fontSize: '18px' }}>kgx_v2: Unconstrained Local LLM Extraction</h3>
            </div>
            <span style={{ fontSize: '12px', fontWeight: 600, color: '#ef4444' }}>ROC-AUC: 0.503 (Chance Level)</span>
          </div>

          <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
            <strong>Mechanism:</strong> Uses Ollama running <code>Qwen-2.5-7B-Instruct</code> locally. First extracts concept candidates and definitions using structured JSON prompts. Then prompts the model to classify section-level candidate pairs into 5 relation types and indicate directionality.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', fontSize: '13px', marginTop: '8px' }}>
            <div style={{ padding: '10px 12px', background: '#ecfdf5', borderRadius: 'var(--radius-sm)', border: '1px solid #10b981' }}>
              <strong style={{ color: '#047857' }}>Main Advantage:</strong> Expands concept discovery beyond static glossaries (204 concepts vs 130), capturing multi-word technical noun phrases.
            </div>
            <div style={{ padding: '10px 12px', background: '#fef2f2', borderRadius: 'var(--radius-sm)', border: '1px solid #ef4444' }}>
              <strong style={{ color: '#b91c1c' }}>Main Limitation:</strong> Operates at chance (AUC 0.503, Dir Acc 50.0%) when inferring directionality from definition snippets due to expository textual symmetry.
            </div>
          </div>
        </div>

        {/* Pipeline 3: kgx_v2_hybrid */}
        <div className="card" style={{ borderLeft: '4px solid #10b981' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="badge badge-primary">Pipeline 3</span>
              <h3 style={{ margin: 0, fontSize: '18px' }}>kgx_v2_hybrid: Neuro-Symbolic Structurally Gated Fusion</h3>
            </div>
            <span style={{ fontSize: '12px', fontWeight: 700, color: '#10b981' }}>Closure F1: 0.786 | ROC-AUC: 0.888</span>
          </div>

          <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
            <strong>Mechanism:</strong> Takes candidate relations from the local LLM and passes them through a deterministic <strong>Reading-Order Forward Gate</strong>: requires <code>pos(u) &lt; pos(v)</code> for any prerequisite edge <code>u &rarr; v</code>. Inverts reversed predictions and enforces DAG acyclicity constraints.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', fontSize: '13px', marginTop: '8px' }}>
            <div style={{ padding: '10px 12px', background: '#ecfdf5', borderRadius: 'var(--radius-sm)', border: '1px solid #10b981' }}>
              <strong style={{ color: '#047857' }}>Main Advantage:</strong> Dominant topological performance (Closure F1 = 0.786, Directional Accuracy = 98.6%, Precision = 0.845).
            </div>
            <div style={{ padding: '10px 12px', background: '#fffbeb', borderRadius: 'var(--radius-sm)', border: '1px solid #f59e0b' }}>
              <strong style={{ color: '#b45309' }}>De-confounded Truth:</strong> Performance derives from the structural prior (+0.368 AUC), not neural reasoning. The LLM acts strictly as a semantic pruning filter (+0.020 AUC gain).
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
