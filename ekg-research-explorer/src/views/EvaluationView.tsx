import React from 'react';
import { GraduationCap, Calculator, ShieldCheck, ArrowRight, CheckCircle2, AlertOctagon } from 'lucide-react';

export const EvaluationView: React.FC = () => {
  return (
    <div>
      <div style={{ marginBottom: '32px' }}>
        <span className="badge badge-primary">Comprehensive Tutorial</span>
        <h1 style={{ marginTop: '8px' }}>Evaluation Framework, Metrics & Statistical Methodology</h1>
        <p style={{ fontSize: '16px', color: 'var(--text-secondary)', maxWidth: '900px' }}>
          Mathematical formulas, step-by-step worked numerical examples, bootstrap confidence interval procedures, and common interpretation pitfalls for every metric used in the paper.
        </p>
      </div>

      {/* Metric 1: Precision, Recall, F1 */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <h3 style={{ margin: '0 0 10px 0', fontSize: '18px', color: 'var(--text-primary)' }}>
          1. Direct Edge Precision, Recall, and F1 Score
        </h3>
        <p>
          Standard classification metrics applied to predicted directed prerequisite edges against human-annotated ground-truth edges:
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '14px', margin: '14px 0' }}>
          <div className="formula-card">
            {`Precision = TP / (TP + FP)`}
          </div>
          <div className="formula-card">
            {`Recall = TP / (TP + FN)`}
          </div>
          <div className="formula-card">
            {`F1 = 2 * (Precision * Recall) / (Precision + Recall)`}
          </div>
        </div>

        <div style={{ fontSize: '13.5px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          <strong>Worked Numerical Example:</strong> Suppose an algorithm predicts 10 prerequisite edges: 8 are verified true positives (TP), 2 are spurious hallucinations (FP), and it missed 4 true prerequisites (FN).
          <ul style={{ paddingLeft: '20px', marginTop: '6px' }}>
            <li><strong>Precision:</strong> 8 / (8 + 2) = 8 / 10 = <strong>0.800 (80%)</strong>. High precision ensures students are not taught invalid dependencies.</li>
            <li><strong>Recall:</strong> 8 / (8 + 4) = 8 / 12 = <strong>0.667 (66.7%)</strong>. Missing prerequisites creates gaps in intelligent tutoring diagnostic trees.</li>
            <li><strong>F1 Score:</strong> 2 &times; (0.800 &times; 0.667) / (0.800 + 0.667) = 1.067 / 1.467 = <strong>0.727</strong>.</li>
          </ul>
        </div>
      </div>

      {/* Metric 2: Transitive Closure F1 */}
      <div className="card" style={{ marginBottom: '24px', borderLeft: '4px solid #10b981' }}>
        <h3 style={{ margin: '0 0 10px 0', fontSize: '18px', color: 'var(--text-primary)' }}>
          2. Transitive Closure F1 (Reachability Evaluation)
        </h3>
        <p>
          In educational curricula, prerequisite dependencies are inherently <strong>transitive</strong>: if Concept A is required for B, and B is required for C, then A is an indirect prerequisite for C.
        </p>

        <div className="formula-card">
          {`G+ = (V, E+),  (u, w) in E+ <=> directed path u -> w exists in G`}
        </div>

        <div style={{ padding: '14px 18px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)', margin: '12px 0', fontSize: '13px', lineHeight: 1.6 }}>
          <strong>Why Closure F1 differs from Direct Edge F1:</strong> Human benchmark annotators often omit intermediate transitive hops (or conversely, skip direct links in favor of foundational primitives). Direct edge F1 penalizes any missing intermediate step as a False Negative. Transitive closure resolves this by computing the all-pairs reachability matrix via the Floyd-Warshall algorithm. This is why <code>kgx_v2_hybrid</code> jumps from an Edge F1 of <strong>0.413</strong> to a Closure F1 of <strong>0.786</strong>.
        </div>
      </div>

      {/* Metric 3: ROC-AUC & Bootstrap Confidence Intervals */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <h3 style={{ margin: '0 0 10px 0', fontSize: '18px', color: 'var(--text-primary)' }}>
          3. ROC-AUC and Non-Parametric Bootstrap 95% Confidence Intervals
        </h3>
        <p>
          <strong>Area Under the Receiver Operating Characteristic Curve (ROC-AUC)</strong> measures ranking discrimination: the probability that a randomly chosen ground-truth positive pair will receive a higher predicted score than a negative pair, across all possible thresholds.
        </p>

        <div className="formula-card">
          {`ROC-AUC = Integral_0^1 TPR(tau) d(FPR(tau)) = P(score(pos) > score(neg))`}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px', marginTop: '14px' }}>
          <div style={{ padding: '14px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)' }}>
            <strong style={{ fontSize: '13px', color: 'var(--primary)' }}>Chance-Level Baseline (AUC = 0.500):</strong>
            <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              An unweighted random coin flip yields an expected AUC of 0.500. A score of 0.503 indicates that the model has zero discriminatory capability.
            </p>
          </div>

          <div style={{ padding: '14px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)' }}>
            <strong style={{ fontSize: '13px', color: 'var(--primary)' }}>Bootstrap Confidence Intervals (B = 1,000):</strong>
            <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              We resample the N = 868 common covered pair set 1,000 times with replacement. For <code>kgx_v2</code>, the 95% CI is <strong>[0.49, 0.51]</strong>, proving statistical equivalence to chance.
            </p>
          </div>
        </div>
      </div>

      {/* Metric 4: Directional Accuracy & NDCG@10 */}
      <div className="grid-2">
        <div className="card">
          <div className="card-title">
            <CheckCircle2 size={16} style={{ color: 'var(--primary)' }} />
            <span>4. Directional Accuracy (Oriented Edges)</span>
          </div>
          <p style={{ fontSize: '13px' }}>
            Measures whether a proposed edge between two related concepts points in the correct pedagogical order:
          </p>
          <div className="formula-card" style={{ fontSize: '12px' }}>
            {`Directional Accuracy = Correctly Oriented Edges / Total Predicted Edges on GT Pairs`}
          </div>
          <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)' }}>
            <strong>Always report numerator and denominator together:</strong> <code>rule_v3</code> scored 7/7 (100% on a tiny sample), <code>kgx_v2</code> scored 4/8 (50.0% chance), and Reading Order scored 251/260 (96.5% robust).
          </div>
        </div>

        <div className="card">
          <div className="card-title">
            <CheckCircle2 size={16} style={{ color: 'var(--primary)' }} />
            <span>5. Ranking Quality: NDCG@10</span>
          </div>
          <p style={{ fontSize: '13px' }}>
            Evaluates ranked prerequisite candidate retrieval by applying logarithmic discounting to lower ranks:
          </p>
          <div className="formula-card" style={{ fontSize: '12px' }}>
            {`DCG@10 = sum_{i=1}^10 (2^{rel_i} - 1) / log_2(i + 1),  NDCG@10 = DCG@10 / IDCG@10`}
          </div>
          <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)' }}>
            Used in our feature ablation to test whether Saaty AHP (0.709) beats simple co-occurrence (0.723) or book position gap (0.891).
          </div>
        </div>
      </div>
    </div>
  );
};
