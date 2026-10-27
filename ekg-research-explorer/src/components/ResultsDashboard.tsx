import React, { useState } from 'react';
import { BENCHMARK_RESULTS, MetricResult } from '../data/researchData';
import { BarChart3, ShieldCheck, AlertTriangle, Info } from 'lucide-react';

export const ResultsDashboard: React.FC = () => {
  const [selectedMetric, setSelectedMetric] = useState<'rocAuc' | 'closureF1' | 'edgeF1' | 'dirAccPct' | 'ndcg10'>('rocAuc');

  const metricMeta = {
    rocAuc: {
      name: "ROC-AUC",
      desc: "Ranking discrimination between ground-truth positive and negative prerequisite pairs (Threshold-independent).",
      max: 1.0,
      chance: 0.5
    },
    closureF1: {
      name: "Transitive Closure F1",
      desc: "Prerequisite path reachability evaluated after Floyd-Warshall transitive closure expansion.",
      max: 1.0,
      chance: null
    },
    edgeF1: {
      name: "Direct Edge F1",
      desc: "Exact recovery of direct human-annotated prerequisite edges without transitive expansion.",
      max: 1.0,
      chance: null
    },
    dirAccPct: {
      name: "Directional Accuracy (%)",
      desc: "Proportion of positive prerequisite pairs where the edge arrow was oriented correctly.",
      max: 100,
      chance: 50
    },
    ndcg10: {
      name: "NDCG@10",
      desc: "Normalized Discounted Cumulative Gain evaluating top-10 ranked prerequisite retrieval quality.",
      max: 1.0,
      chance: null
    }
  };

  const currentMeta = metricMeta[selectedMetric];

  return (
    <div className="card" style={{ padding: '24px', marginBottom: '32px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
        <div>
          <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <BarChart3 size={18} style={{ color: 'var(--primary)' }} />
            <span>Interactive Prerequisite Benchmark Dashboard</span>
            <span className="badge badge-success">Common Set N=868</span>
          </h3>
          <p style={{ margin: '4px 0 0 0', fontSize: '13.5px' }}>
            Comparative evaluation on identical AL-CPL common covered pairs (260 positive, 608 negative). Select a metric to inspect comparative bar charts and 95% bootstrap confidence intervals.
          </p>
        </div>

        {/* Metric Selector Buttons */}
        <div style={{ display: 'flex', gap: '6px', background: 'var(--bg-subtle)', padding: '4px', borderRadius: 'var(--radius-md)', flexWrap: 'wrap' }}>
          {(Object.keys(metricMeta) as Array<keyof typeof metricMeta>).map(key => (
            <button
              key={key}
              onClick={() => setSelectedMetric(key)}
              style={{
                padding: '6px 12px',
                fontSize: '12px',
                fontWeight: 600,
                borderRadius: 'var(--radius-sm)',
                border: 'none',
                cursor: 'pointer',
                background: selectedMetric === key ? 'var(--primary)' : 'none',
                color: selectedMetric === key ? '#fff' : 'var(--text-secondary)'
              }}
            >
              {metricMeta[key].name}
            </button>
          ))}
        </div>
      </div>

      <div className="callout" style={{ margin: '0 0 20px 0', fontSize: '13px' }}>
        <strong>{currentMeta.name}:</strong> {currentMeta.desc}
      </div>

      {/* Visual Chart */}
      <div style={{ padding: '20px', backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-lg)', marginBottom: '24px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {BENCHMARK_RESULTS.map((item, idx) => {
            const rawVal = item[selectedMetric];
            const numVal = typeof rawVal === 'number' ? rawVal : (rawVal === "Not reported" || rawVal === "N/A" ? 0 : parseFloat(String(rawVal)));
            const pct = (numVal / currentMeta.max) * 100;
            const isChance = currentMeta.chance !== null && numVal <= currentMeta.chance + 0.02 && numVal >= currentMeta.chance - 0.02;

            let barColor = '#2563eb';
            if (item.category === 'Baseline') barColor = '#64748b';
            if (item.method.includes('hybrid')) barColor = '#10b981';
            if (item.method.includes('Reading-Order')) barColor = '#8b5cf6';
            if (isChance) barColor = '#ef4444';

            return (
              <div key={idx}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', fontWeight: 600, marginBottom: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span>{item.method}</span>
                    <span className="badge badge-primary" style={{ fontSize: '10px' }}>{item.category}</span>
                    {item.method.includes('kgx_v2_hybrid') && (
                      <span className="badge badge-warning" style={{ fontSize: '10px' }}>Uses Reading Order</span>
                    )}
                  </div>
                  <div style={{ fontFamily: 'var(--font-mono)' }}>
                    {typeof rawVal === 'number' ? (selectedMetric === 'dirAccPct' ? `${rawVal.toFixed(1)}%` : rawVal.toFixed(3)) : rawVal}
                    {selectedMetric === 'rocAuc' && item.rocAucCI && (
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginLeft: '6px' }}>{item.rocAucCI}</span>
                    )}
                    {selectedMetric === 'closureF1' && item.closureF1CI && (
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginLeft: '6px' }}>{item.closureF1CI}</span>
                    )}
                  </div>
                </div>

                <div style={{ height: '18px', width: '100%', backgroundColor: 'var(--bg-subtle)', borderRadius: 'var(--radius-full)', overflow: 'hidden', position: 'relative' }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${pct}%`,
                      backgroundColor: barColor,
                      borderRadius: 'var(--radius-full)',
                      transition: 'width 0.4s ease'
                    }}
                  />
                  {currentMeta.chance !== null && (
                    <div
                      title="Theoretical Chance Line (50%)"
                      style={{
                        position: 'absolute',
                        top: 0,
                        bottom: 0,
                        left: `${(currentMeta.chance / currentMeta.max) * 100}%`,
                        width: '2px',
                        backgroundColor: '#ef4444',
                        zIndex: 2
                      }}
                    />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Comprehensive Benchmark Table */}
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Methodology</th>
              <th>Category</th>
              <th>Precision</th>
              <th>Recall</th>
              <th>Edge F1</th>
              <th>Closure F1 (95% CI)</th>
              <th>ROC-AUC (95% CI)</th>
              <th>Dir. Accuracy</th>
              <th>NDCG@10</th>
            </tr>
          </thead>
          <tbody>
            {BENCHMARK_RESULTS.map((row, idx) => (
              <tr key={idx}>
                <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{row.method}</td>
                <td><span className="badge badge-primary">{row.category}</span></td>
                <td>{typeof row.precision === 'number' ? row.precision.toFixed(3) : row.precision}</td>
                <td>{typeof row.recall === 'number' ? row.recall.toFixed(3) : row.recall}</td>
                <td style={{ fontWeight: 600 }}>{typeof row.edgeF1 === 'number' ? row.edgeF1.toFixed(3) : row.edgeF1}</td>
                <td>
                  <strong>{typeof row.closureF1 === 'number' ? row.closureF1.toFixed(3) : row.closureF1}</strong>
                  {row.closureF1CI && <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{row.closureF1CI}</div>}
                </td>
                <td>
                  <strong style={{ color: typeof row.rocAuc === 'number' && row.rocAuc < 0.55 ? '#ef4444' : 'inherit' }}>
                    {typeof row.rocAuc === 'number' ? row.rocAuc.toFixed(3) : row.rocAuc}
                  </strong>
                  {row.rocAucCI && <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{row.rocAucCI}</div>}
                </td>
                <td>
                  <span className={`badge ${row.dirAccPct >= 90 ? 'badge-success' : row.dirAccPct === 50 ? 'badge-danger' : 'badge-primary'}`}>
                    {row.dirAcc} ({row.dirAccPct.toFixed(1)}%)
                  </span>
                </td>
                <td>{typeof row.ndcg10 === 'number' ? row.ndcg10.toFixed(3) : row.ndcg10}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
