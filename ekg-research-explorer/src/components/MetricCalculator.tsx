import React, { useState } from 'react';
import { Calculator, HelpCircle, CheckCircle, AlertTriangle, ArrowRight } from 'lucide-react';

export const MetricCalculator: React.FC = () => {
  const [tp, setTp] = useState(8);
  const [fp, setFp] = useState(2);
  const [fn, setFn] = useState(4);
  const [closureDemoStep, setClosureDemoStep] = useState<number>(1);

  // Compute metrics
  const precision = (tp + fp) > 0 ? tp / (tp + fp) : 0;
  const recall = (tp + fn) > 0 ? tp / (tp + fn) : 0;
  const f1 = (precision + recall) > 0 ? (2 * precision * recall) / (precision + recall) : 0;

  return (
    <div className="card" style={{ padding: '24px', marginBottom: '32px' }}>
      <div style={{ marginBottom: '20px' }}>
        <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Calculator size={18} style={{ color: 'var(--primary)' }} />
          <span>Interactive Metric & Transitive Closure Calculator</span>
          <span className="badge badge-primary">Hands-on Tool</span>
        </h3>
        <p style={{ margin: '4px 0 0 0', fontSize: '13.5px' }}>
          Adjust True Positives (TP), False Positives (FP), and False Negatives (FN) to observe real-time precision/recall trade-offs and explore how transitive closure evaluation bridges missing intermediate links.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px' }}>
        {/* Sliders & Inputs */}
        <div style={{ backgroundColor: 'var(--bg-subtle)', padding: '20px', borderRadius: 'var(--radius-lg)', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <h4 style={{ fontSize: '14px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            1. Configure Edge Prediction Counts
          </h4>

          {/* TP */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', fontWeight: 600, marginBottom: '6px' }}>
              <span style={{ color: '#10b981' }}>True Positives (TP): Correct Prerequisites</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>{tp}</span>
            </div>
            <input
              type="range"
              min="0"
              max="50"
              value={tp}
              onChange={e => setTp(Number(e.target.value))}
              style={{ width: '100%', accentColor: '#10b981' }}
            />
          </div>

          {/* FP */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', fontWeight: 600, marginBottom: '6px' }}>
              <span style={{ color: '#ef4444' }}>False Positives (FP): Spurious Predictions</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>{fp}</span>
            </div>
            <input
              type="range"
              min="0"
              max="50"
              value={fp}
              onChange={e => setFp(Number(e.target.value))}
              style={{ width: '100%', accentColor: '#ef4444' }}
            />
          </div>

          {/* FN */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', fontWeight: 600, marginBottom: '6px' }}>
              <span style={{ color: '#f59e0b' }}>False Negatives (FN): Missed Ground Truth</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>{fn}</span>
            </div>
            <input
              type="range"
              min="0"
              max="50"
              value={fn}
              onChange={e => setFn(Number(e.target.value))}
              style={{ width: '100%', accentColor: '#f59e0b' }}
            />
          </div>

          <div style={{ fontSize: '11.5px', color: 'var(--text-dim)', borderTop: '1px solid var(--border-color)', paddingTop: '10px' }}>
            Total Ground Truth Edges: <strong>{tp + fn}</strong> | Total Predicted Edges: <strong>{tp + fp}</strong>
          </div>
        </div>

        {/* Live Mathematical Breakdown */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <h4 style={{ fontSize: '14px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            2. Live Derived Evaluation Metrics
          </h4>

          {/* Precision Card */}
          <div style={{ padding: '14px 18px', backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)' }}>Precision: TP / (TP + FP)</div>
              <div style={{ fontSize: '12px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                {tp} / ({tp} + {fp}) = {tp} / {tp + fp}
              </div>
            </div>
            <div style={{ fontSize: '24px', fontWeight: 800, color: '#2563eb' }}>
              {(precision * 100).toFixed(1)}%
            </div>
          </div>

          {/* Recall Card */}
          <div style={{ padding: '14px 18px', backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)' }}>Recall: TP / (TP + FN)</div>
              <div style={{ fontSize: '12px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                {tp} / ({tp} + {fn}) = {tp} / {tp + fn}
              </div>
            </div>
            <div style={{ fontSize: '24px', fontWeight: 800, color: '#10b981' }}>
              {(recall * 100).toFixed(1)}%
            </div>
          </div>

          {/* F1 Card */}
          <div style={{ padding: '14px 18px', backgroundColor: 'var(--primary-light)', border: '1px solid var(--border-active)', borderRadius: 'var(--radius-md)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--primary)' }}>F1 Score: Harmonic Mean</div>
              <div style={{ fontSize: '11.5px', color: 'var(--text-secondary)' }}>
                2 × (P × R) / (P + R)
              </div>
            </div>
            <div style={{ fontSize: '28px', fontWeight: 800, color: 'var(--primary)' }}>
              {f1.toFixed(3)}
            </div>
          </div>
        </div>
      </div>

      {/* Interactive Transitive Closure Demonstration */}
      <div style={{ marginTop: '24px', borderTop: '1px solid var(--border-color)', paddingTop: '20px' }}>
        <h4 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '8px' }}>
          Interactive Demonstration: Direct Edge F1 vs Transitive Closure F1
        </h4>
        <p style={{ fontSize: '13.5px', color: 'var(--text-secondary)', marginBottom: '14px' }}>
          Consider a 3-concept curriculum: <strong>Angle ≺ Triangle</strong> and <strong>Triangle ≺ Trigonometry</strong>. Ground truth includes the indirect prerequisite <strong>Angle ≺ Trigonometry</strong>.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
          <div style={{ padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-surface)' }}>
            <div style={{ fontWeight: 700, fontSize: '13px', color: '#ef4444', marginBottom: '6px' }}>
              Direct Edge Evaluation (Edge F1 = 0.667)
            </div>
            <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              If your model only extracts <code>Angle → Triangle</code> and <code>Triangle → Trigonometry</code>, direct edge evaluation treats <code>Angle → Trigonometry</code> as a <strong>False Negative</strong>! Edge recall is penalized even though the learning path is completely traversable.
            </div>
          </div>

          <div style={{ padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid #10b981', backgroundColor: '#ecfdf5' }}>
            <div style={{ fontWeight: 700, fontSize: '13px', color: '#047857', marginBottom: '6px' }}>
              Transitive Closure Evaluation (Closure F1 = 1.000)
            </div>
            <div style={{ fontSize: '12.5px', color: '#065f46', lineHeight: 1.5 }}>
              Transitive closure (G+) computes reachability: since Angle reaches Trigonometry via Triangle, the indirect prerequisite is satisfied. This is why our hybrid pipeline achieves <strong>Closure F1 = 0.786</strong> despite an <strong>Edge F1 of 0.413</strong>.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
