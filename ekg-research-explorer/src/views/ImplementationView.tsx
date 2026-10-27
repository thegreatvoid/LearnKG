import React from 'react';
import { REPOSITORY_FILE_MAP } from '../data/researchData';
import { FolderGit2, Terminal, FileCode, ShieldCheck, CheckCircle2 } from 'lucide-react';

export const ImplementationView: React.FC = () => {
  return (
    <div>
      <div style={{ marginBottom: '32px' }}>
        <span className="badge badge-primary">Open Science & Traceability</span>
        <h1 style={{ marginTop: '8px' }}>Repository Implementation Map & Reproducibility</h1>
        <p style={{ fontSize: '16px', color: 'var(--text-secondary)', maxWidth: '900px' }}>
          File-by-file technical mapping of all Python extraction scripts, evaluation frameworks, frozen dataset manifests, and exact CLI commands to audit our experimental findings.
        </p>
      </div>

      {/* Reproduction Commands */}
      <div className="card" style={{ marginBottom: '28px' }}>
        <h3 style={{ margin: '0 0 10px 0', fontSize: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Terminal size={18} style={{ color: 'var(--primary)' }} />
          1. Exact Reproduction Commands (No New Model Runs Required)
        </h3>
        <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
          To verify all benchmark numbers, bootstrap confidence intervals, and ablation NDCG scores published in the paper, execute the following commands using our frozen evaluation manifests:
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '14px' }}>
          <div>
            <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px' }}>
              A. Audit Prerequisite Benchmark Metrics (Edge F1, Closure F1, ROC-AUC, Directional Accuracy):
            </div>
            <div style={{ backgroundColor: 'var(--bg-code)', padding: '12px 16px', borderRadius: 'var(--radius-md)', color: 'var(--text-code)', fontFamily: 'var(--font-mono)', fontSize: '12.5px', overflowX: 'auto' }}>
              <code>python3 eval/evaluate_prereq_benchmarks.py --benchmark al_cpl --pairs data_output/ck12_geometry_kgx_v2_hybrid/pair_scores.csv --bootstrap 1000</code>
            </div>
          </div>

          <div>
            <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px' }}>
              B. Audit Edge-Weighting Ablation (AHP Composite vs Co-occurrence vs Book Gap):
            </div>
            <div style={{ backgroundColor: 'var(--bg-code)', padding: '12px 16px', borderRadius: 'var(--radius-md)', color: 'var(--text-code)', fontFamily: 'var(--font-mono)', fontSize: '12.5px', overflowX: 'auto' }}>
              <code>python3 eval/evaluate_prereq_benchmarks.py --mode ablation --config ahp_vs_cooc --queries data_input/benchmarks/al_cpl/geometry.pairs</code>
            </div>
          </div>

          <div>
            <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px' }}>
              C. Audit Automated Structural Consistency Diagnostics (43 Contradictions):
            </div>
            <div style={{ backgroundColor: 'var(--bg-code)', padding: '12px 16px', borderRadius: 'var(--radius-md)', color: 'var(--text-code)', fontFamily: 'var(--font-mono)', fontSize: '12.5px', overflowX: 'auto' }}>
              <code>python3 scripts/reconcile.py --check-contradictions --graph data_output/ck12_geometry/relations.csv</code>
            </div>
          </div>
        </div>
      </div>

      {/* File-by-File Implementation Table */}
      <h3 style={{ fontSize: '18px', marginBottom: '14px' }}>
        2. Technical Source Code & Artifact Inventory Map
      </h3>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>File Path</th>
              <th>Pipeline Stage</th>
              <th>Technical Purpose</th>
              <th>Inputs & Outputs</th>
              <th>Known Limitation</th>
            </tr>
          </thead>
          <tbody>
            {REPOSITORY_FILE_MAP.map((item, idx) => (
              <tr key={idx}>
                <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--primary)', fontSize: '12.5px' }}>
                  {item.path}
                </td>
                <td><span className="badge badge-primary">{item.stage}</span></td>
                <td style={{ fontSize: '13px' }}>{item.purpose}</td>
                <td style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  <div><strong>In:</strong> {item.inputs}</div>
                  <div><strong>Out:</strong> {item.outputs}</div>
                </td>
                <td style={{ fontSize: '12px', color: '#b91c1c' }}>{item.limitations}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
