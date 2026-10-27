import React from 'react';
import { ABLATION_RESULTS } from '../data/researchData';
import { Sliders, CheckCircle2, XCircle, AlertTriangle, HelpCircle } from 'lucide-react';

export const AblationExplorer: React.FC = () => {
  return (
    <div className="card" style={{ padding: '24px', marginBottom: '32px' }}>
      <div style={{ marginBottom: '20px' }}>
        <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sliders size={18} style={{ color: 'var(--primary)' }} />
          <span>Edge Weighting & Feature Ablation Explorer</span>
          <span className="badge badge-primary">NDCG@10 Query Ranking</span>
        </h3>
        <p style={{ margin: '4px 0 0 0', fontSize: '13.5px' }}>
          Ablation of individual scoring features against the Saaty Analytic Hierarchy Process (AHP) composite formula (CR = 0.022). Paired permutation significance tests (B = 10,000 resamples).
        </p>
      </div>

      {/* Feature Component Matrix */}
      <h4 style={{ fontSize: '14px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '10px' }}>
        1. Feature Component Inclusion Matrix
      </h4>
      <div className="table-wrapper" style={{ margin: '0 0 24px 0' }}>
        <table>
          <thead>
            <tr>
              <th>Scoring Configuration</th>
              <th style={{ textAlign: 'center' }}>Definition Overlap (S, 52%)</th>
              <th style={{ textAlign: 'center' }}>Sentence Co-occ (C, 24%)</th>
              <th style={{ textAlign: 'center' }}>Section Position (E, 15%)</th>
              <th style={{ textAlign: 'center' }}>Chapter Proximity (P, 9%)</th>
              <th style={{ textAlign: 'center' }}>Book Position Gap</th>
              <th>NDCG@10</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style={{ fontWeight: 600 }}>Book Position Gap</td>
              <td style={{ textAlign: 'center', color: 'var(--text-dim)' }}>—</td>
              <td style={{ textAlign: 'center', color: 'var(--text-dim)' }}>—</td>
              <td style={{ textAlign: 'center', color: 'var(--text-dim)' }}>—</td>
              <td style={{ textAlign: 'center', color: 'var(--text-dim)' }}>—</td>
              <td style={{ textAlign: 'center', color: '#10b981' }}><CheckCircle2 size={16} /></td>
              <td style={{ fontWeight: 800, color: '#10b981' }}>0.891</td>
            </tr>
            <tr>
              <td style={{ fontWeight: 600 }}>Raw Co-occurrence Count</td>
              <td style={{ textAlign: 'center', color: 'var(--text-dim)' }}>—</td>
              <td style={{ textAlign: 'center', color: '#2563eb' }}>Raw Count</td>
              <td style={{ textAlign: 'center', color: 'var(--text-dim)' }}>—</td>
              <td style={{ textAlign: 'center', color: 'var(--text-dim)' }}>—</td>
              <td style={{ textAlign: 'center', color: 'var(--text-dim)' }}>—</td>
              <td style={{ fontWeight: 700 }}>0.742</td>
            </tr>
            <tr>
              <td style={{ fontWeight: 600 }}>Sentence Co-occurrence (C)</td>
              <td style={{ textAlign: 'center', color: 'var(--text-dim)' }}>—</td>
              <td style={{ textAlign: 'center', color: '#2563eb' }}><CheckCircle2 size={16} /></td>
              <td style={{ textAlign: 'center', color: 'var(--text-dim)' }}>—</td>
              <td style={{ textAlign: 'center', color: 'var(--text-dim)' }}>—</td>
              <td style={{ textAlign: 'center', color: 'var(--text-dim)' }}>—</td>
              <td style={{ fontWeight: 700 }}>0.723</td>
            </tr>
            <tr style={{ backgroundColor: 'var(--primary-light)' }}>
              <td style={{ fontWeight: 700, color: 'var(--primary)' }}>Saaty AHP Composite (Ref)</td>
              <td style={{ textAlign: 'center', color: '#2563eb', fontWeight: 700 }}>52%</td>
              <td style={{ textAlign: 'center', color: '#2563eb', fontWeight: 700 }}>24%</td>
              <td style={{ textAlign: 'center', color: '#2563eb', fontWeight: 700 }}>15%</td>
              <td style={{ textAlign: 'center', color: '#2563eb', fontWeight: 700 }}>9%</td>
              <td style={{ textAlign: 'center', color: 'var(--text-dim)' }}>—</td>
              <td style={{ fontWeight: 800, color: 'var(--primary)' }}>0.709</td>
            </tr>
            <tr>
              <td style={{ fontWeight: 600 }}>Section Co-location (E)</td>
              <td style={{ textAlign: 'center', color: 'var(--text-dim)' }}>—</td>
              <td style={{ textAlign: 'center', color: 'var(--text-dim)' }}>—</td>
              <td style={{ textAlign: 'center', color: '#2563eb' }}><CheckCircle2 size={16} /></td>
              <td style={{ textAlign: 'center', color: 'var(--text-dim)' }}>—</td>
              <td style={{ textAlign: 'center', color: 'var(--text-dim)' }}>—</td>
              <td>0.684</td>
            </tr>
            <tr>
              <td style={{ fontWeight: 600 }}>Chapter Proximity (P)</td>
              <td style={{ textAlign: 'center', color: 'var(--text-dim)' }}>—</td>
              <td style={{ textAlign: 'center', color: 'var(--text-dim)' }}>—</td>
              <td style={{ textAlign: 'center', color: 'var(--text-dim)' }}>—</td>
              <td style={{ textAlign: 'center', color: '#2563eb' }}><CheckCircle2 size={16} /></td>
              <td style={{ textAlign: 'center', color: 'var(--text-dim)' }}>—</td>
              <td>0.605</td>
            </tr>
            <tr>
              <td style={{ fontWeight: 600, color: '#ef4444' }}>Definition Overlap (S)</td>
              <td style={{ textAlign: 'center', color: '#ef4444' }}><CheckCircle2 size={16} /></td>
              <td style={{ textAlign: 'center', color: 'var(--text-dim)' }}>—</td>
              <td style={{ textAlign: 'center', color: 'var(--text-dim)' }}>—</td>
              <td style={{ textAlign: 'center', color: 'var(--text-dim)' }}>—</td>
              <td style={{ textAlign: 'center', color: 'var(--text-dim)' }}>—</td>
              <td style={{ fontWeight: 700, color: '#ef4444' }}>0.589</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Visual Bar Comparison */}
      <h4 style={{ fontSize: '14px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '10px' }}>
        2. Ranking Quality (NDCG@10) vs Statistical Significance
      </h4>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginBottom: '24px' }}>
        {ABLATION_RESULTS.map((item, idx) => {
          const pct = (item.ndcg10 / 1.0) * 100;
          const isDominant = item.name.includes("Book");
          const isAHP = item.name.includes("AHP");
          const isFlaw = item.name.includes("Definition");

          let barColor = '#2563eb';
          if (isDominant) barColor = '#10b981';
          if (isAHP) barColor = '#6366f1';
          if (isFlaw) barColor = '#ef4444';

          return (
            <div key={idx} style={{ padding: '12px 16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-surface)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px', marginBottom: '8px' }}>
                <div>
                  <span style={{ fontWeight: 700, fontSize: '14px', color: 'var(--text-primary)' }}>{item.name}</span>
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginLeft: '8px', fontFamily: 'var(--font-mono)' }}>{item.formulaOrFeature}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className={`badge ${item.pValueVsAHP.includes('p < 0.0001') ? 'badge-success' : item.pValueVsAHP.includes('Not Significant') ? 'badge-primary' : item.pValueVsAHP.includes('Reference') ? 'badge-primary' : 'badge-danger'}`} style={{ fontSize: '11px' }}>
                    {item.pValueVsAHP}
                  </span>
                  <span style={{ fontSize: '16px', fontWeight: 800, fontFamily: 'var(--font-mono)' }}>
                    {item.ndcg10.toFixed(3)}
                  </span>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{item.ci}</span>
                </div>
              </div>

              <div style={{ height: '12px', width: '100%', backgroundColor: 'var(--bg-subtle)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${pct}%`, backgroundColor: barColor, borderRadius: 'var(--radius-full)', transition: 'width 0.4s ease' }} />
              </div>

              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '6px' }}>
                <strong>Key Takeaway:</strong> {item.interpretation}
              </div>
            </div>
          );
        })}
      </div>

      <div className="callout warning" style={{ margin: 0 }}>
        <div className="callout-title">
          <AlertTriangle size={16} />
          <span>Scientific Discovery: The Illusion of Multi-Criteria Complexity</span>
        </div>
        The Saaty AHP formula assigned its heaviest weight (52%) to definition lexical overlap (S). However, because mathematical definitions in introductory textbooks share general vocabulary (e.g. 'points', 'set', 'space', 'figure'), Jaccard overlap provides virtually zero discriminative signal (NDCG@10 = 0.589, near random noise 0.582). Meanwhile, simple sentence co-occurrence (0.723) carries the entire statistical signal and matches the full AHP composite (p = 0.68, not significant).
      </div>
    </div>
  );
};
