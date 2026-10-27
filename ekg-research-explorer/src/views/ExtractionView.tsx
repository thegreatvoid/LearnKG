import React from 'react';
import { Filter, Layers, AlertTriangle, ShieldCheck, ArrowRight, CheckCircle2 } from 'lucide-react';

export const ExtractionView: React.FC = () => {
  return (
    <div>
      <div style={{ marginBottom: '32px' }}>
        <span className="badge badge-primary">Extraction Pipeline Analysis</span>
        <h1 style={{ marginTop: '8px' }}>Concept Extraction, Matching & The Candidate Bottleneck</h1>
        <p style={{ fontSize: '16px', color: 'var(--text-secondary)', maxWidth: '900px' }}>
          Comparing symbolic glossary extraction with zero-shot LLM noun-phrase discovery, analyzing definition validity rates, and proving why candidate-pair generation is the true statistical bottleneck of knowledge graph construction.
        </p>
      </div>

      {/* Concept Extraction Comparison Table */}
      <div className="card" style={{ marginBottom: '28px' }}>
        <h3 style={{ margin: '0 0 10px 0', fontSize: '18px' }}>
          1. Concept Extraction & Definition Validity Audit
        </h3>
        <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
          A knowledge graph is structurally bounded by its nodes. If a concept is missed during initial extraction, all relations involving that concept are permanently lost.
        </p>

        <div className="table-wrapper" style={{ margin: '14px 0' }}>
          <table>
            <thead>
              <tr>
                <th>Extraction Pipeline</th>
                <th>Extracted Concepts</th>
                <th>Valid Definitions</th>
                <th>Definition Validity Rate</th>
                <th>AL-CPL Matches</th>
                <th>Benchmark Coverage</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style={{ fontWeight: 600 }}>rule_v3 (Handcrafted Glossary)</td>
                <td>130 concepts</td>
                <td>67 definitions</td>
                <td><strong>51.5%</strong></td>
                <td>65 / 89</td>
                <td><span className="badge badge-primary">73.0%</span></td>
              </tr>
              <tr>
                <td style={{ fontWeight: 600 }}>kgx_v2 (Local Qwen-2.5-7B)</td>
                <td>204 concepts</td>
                <td>70 definitions</td>
                <td><strong>34.3%</strong></td>
                <td>65 / 89</td>
                <td><span className="badge badge-primary">73.0%</span></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="callout" style={{ margin: 0 }}>
          <strong>Key Discovery:</strong> The local LLM extracted <strong>57% more concepts</strong> (204 vs 130), capturing multi-word technical phrases like <em>"included angle"</em> and <em>"alternate interior angles"</em>. However, its definition validity rate dropped from 51.5% to 34.3% due to extracting sentence fragments. Most importantly, <strong>both systems plateaued at exactly 65/89 benchmark matches</strong>, confirming that the remaining 24 concepts simply do not exist in the source textbook.
        </div>
      </div>

      {/* The Candidate Generation Bottleneck */}
      <div className="card" style={{ marginBottom: '28px', borderLeft: '4px solid #ef4444' }}>
        <h3 style={{ margin: '0 0 10px 0', fontSize: '18px', color: '#b91c1c', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertTriangle size={18} />
          2. The Candidate Generation Bottleneck: Where Recall Actually Dies
        </h3>
        <p>
          Researchers often observe low end-to-end prerequisite recall (e.g., 0.015 for <code>kgx_v2</code> and 0.027 for <code>rule_v3</code>) and immediately blame the classifier. However, our stage attrition audit revealed that <strong>candidate pair filtering discards over 96% of ground-truth prerequisite pairs before the classifier is ever executed</strong>!
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px', margin: '16px 0' }}>
          <div style={{ padding: '16px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>rule_v3 Candidate Recall</div>
            <div style={{ fontSize: '26px', fontWeight: 800, color: '#ef4444', margin: '4px 0' }}>3.1%</div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Filters candidate pairs using sentence co-occurrence windows, immediately discarding 96.9% of true prerequisites.
            </div>
          </div>

          <div style={{ padding: '16px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>kgx_v2 Candidate Recall</div>
            <div style={{ fontSize: '26px', fontWeight: 800, color: '#ef4444', margin: '4px 0' }}>3.5%</div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Proposes candidates within section boundaries, discarding 96.5% of cross-chapter prerequisite dependencies.
            </div>
          </div>

          <div style={{ padding: '16px', background: '#ecfdf5', borderRadius: 'var(--radius-md)', border: '1px solid #10b981' }}>
            <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: '#047857' }}>Hybrid / Reading Order Recall</div>
            <div style={{ fontSize: '26px', fontWeight: 800, color: '#047857', margin: '4px 0' }}>32.3% / 100%</div>
            <div style={{ fontSize: '12px', color: '#065f46' }}>
              Reading order pairs concepts globally based on appearance sequence, preserving cross-chapter prerequisite candidates.
            </div>
          </div>
        </div>

        <p style={{ fontSize: '13.5px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          <strong>Mathematical Consequence:</strong> If a candidate generator only proposes 3.5% of valid ground-truth pairs, the downstream classifier has a theoretical maximum recall of 0.035—even if it operates with 100% precision. Candidate generation is the true architectural bottleneck in automated knowledge graph construction.
        </p>
      </div>

      {/* Step-by-Step Geometry Walkthrough */}
      <div className="card">
        <h3 style={{ margin: '0 0 10px 0', fontSize: '18px' }}>
          3. Step-by-Step Candidate Journey: From Raw Text to Verified Graph Edge
        </h3>
        <p style={{ fontSize: '13.5px', color: 'var(--text-secondary)' }}>
          Tracing how a candidate pair (<em>Ray</em>, <em>Angle</em>) progresses through the hybrid pipeline:
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '14px' }}>
          {[
            { step: "Step 1: Text Tokenization", desc: "Chapter 1, Section 1.2 introduces 'Ray' (pos = 142); Section 1.3 introduces 'Angle' (pos = 284)." },
            { step: "Step 2: Candidate Generation", desc: "Both concepts co-occur in Section 1.3 definition: candidate pair (Ray, Angle) is generated." },
            { step: "Step 3: Neural Scoring", desc: "Qwen-2.5-7B classifies the pair as related (confidence = 0.82), but predicts direction symmetrically." },
            { step: "Step 4: Structural Gating", desc: "Forward gate checks pos(Ray) = 142 < pos(Angle) = 284. The gate validates orientation: Ray ≺ Angle." },
            { step: "Step 5: Topological Verification", desc: "Cycle check verifies DAG property. Transitive edge is verified against AL-CPL ground truth (True Positive!)." }
          ].map((item, idx) => (
            <div key={idx} style={{ padding: '12px 16px', borderRadius: 'var(--radius-md)', background: 'var(--bg-subtle)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '14px' }}>
              <div style={{ width: '24px', height: '24px', borderRadius: '50%', background: 'var(--primary)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px', fontWeight: 700, flexShrink: 0 }}>
                {idx + 1}
              </div>
              <div>
                <strong style={{ fontSize: '13px', color: 'var(--text-primary)' }}>{item.step}:</strong>{' '}
                <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{item.desc}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
