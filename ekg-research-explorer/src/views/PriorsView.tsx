import React from 'react';
import { Compass, Sparkles, Scale, AlertTriangle, ShieldCheck, CheckCircle2 } from 'lucide-react';

export const PriorsView: React.FC = () => {
  return (
    <div>
      <div style={{ marginBottom: '32px' }}>
        <span className="badge badge-primary">Inductive Biases & Regularization</span>
        <h1 style={{ marginTop: '8px' }}>Structural Priors, Reading-Order Gating & The Circularity Disclosure</h1>
        <p style={{ fontSize: '16px', color: 'var(--text-secondary)', maxWidth: '900px' }}>
          De-mystifying how document structure provides an immense pedagogical inductive bias, de-confounding the hybrid pipeline's performance, and rigorously analyzing circularity in educational benchmark evaluation.
        </p>
      </div>

      {/* What is a Structural Prior? */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <h3 style={{ margin: '0 0 10px 0', fontSize: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Compass size={18} style={{ color: 'var(--primary)' }} />
          1. What is an Educational Structural Prior?
        </h3>
        <p>
          In natural language processing, a <strong>structural prior</strong> is an inductive bias derived from external document organization—such as section hierarchies, chapter progressions, and linear reading sequence—rather than from text content alone.
        </p>
        <div className="callout" style={{ margin: '12px 0' }}>
          <strong>The Intuition:</strong> An author writing an introductory geometry textbook does not introduce the <em>Pythagorean Theorem</em> in Chapter 1 and then define a <em>Right Angle</em> in Chapter 8. The author intentionally arranges concepts in linear chronological sequence so that prerequisites precede their applications. Therefore, the physical appearance index <code>pos(c)</code> provides an immense inductive signal regarding prerequisite dependency.
        </div>
      </div>

      {/* 5 Distinct Ways Structure Can Be Used */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <h3 style={{ margin: '0 0 10px 0', fontSize: '18px' }}>
          2. Architectural Modalities: 5 Ways to Incorporate Document Structure
        </h3>
        <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
          Researchers frequently confuse different ways of utilizing structural information. In this paper, we classify and evaluate these distinct modalities:
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '14px', marginTop: '14px' }}>
          <div style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'var(--bg-subtle)', border: '1px solid var(--border-color)' }}>
            <div style={{ fontWeight: 700, fontSize: '13.5px', color: 'var(--primary)' }}>A. Standalone Baseline Heuristic</div>
            <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Assigning a directed prerequisite edge <code>u &rarr; v</code> iff <code>pos(u) &lt; pos(v)</code>. (Zero parameters, ROC-AUC: 0.868).
            </div>
          </div>

          <div style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'var(--bg-subtle)', border: '1px solid var(--border-color)' }}>
            <div style={{ fontWeight: 700, fontSize: '13.5px', color: 'var(--primary)' }}>B. Continuous Ranking Feature</div>
            <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Computing positional gap <code>&Delta;pos = pos(v) - pos(u)</code> and using it as a ranking feature (NDCG@10 = 0.891).
            </div>
          </div>

          <div style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'var(--bg-subtle)', border: '1px solid var(--border-color)' }}>
            <div style={{ fontWeight: 700, fontSize: '13.5px', color: 'var(--primary)' }}>C. Multi-Criteria Composite (AHP)</div>
            <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Weighting chapter proximity (P, 9%) and section co-location (E, 15%) alongside textual overlap (AHP NDCG@10 = 0.709).
            </div>
          </div>

          <div style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'var(--bg-subtle)', border: '1px solid var(--border-color)' }}>
            <div style={{ fontWeight: 700, fontSize: '13.5px', color: '#10b981' }}>D. Deterministic Forward Gate (Hybrid)</div>
            <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Filtering neural candidates: a predicted prerequisite is only accepted if <code>pos(u) &lt; pos(v)</code> (Closure F1 = 0.786).
            </div>
          </div>
        </div>
      </div>

      {/* De-confounding the Hybrid */}
      <div className="card" style={{ marginBottom: '24px', borderLeft: '4px solid #10b981' }}>
        <h3 style={{ margin: '0 0 10px 0', fontSize: '18px', color: 'var(--text-primary)' }}>
          3. De-confounding the Hybrid: What Does the LLM Actually Contribute?
        </h3>
        <p>
          A superficial analysis of our results table might suggest that <code>kgx_v2_hybrid</code> represents an emergence of neuro-symbolic reasoning (ROC-AUC = 0.888). However, rigorous ablation deconstructs this claim:
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', margin: '16px 0' }}>
          <div style={{ padding: '16px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>Baseline: Pure Reading Order Alone</div>
            <div style={{ fontSize: '24px', fontWeight: 800, color: '#64748b', margin: '4px 0' }}>ROC-AUC: 0.868</div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Directional Accuracy: <strong>96.5%</strong> (251/260 ground truth positive pairs correctly oriented).
            </div>
          </div>

          <div style={{ padding: '16px', background: 'var(--primary-light)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-active)' }}>
            <div style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--primary)' }}>Neuro-Symbolic Hybrid (LLM + Gate)</div>
            <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--primary)', margin: '4px 0' }}>ROC-AUC: 0.888</div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Directional Accuracy: <strong>98.6%</strong> (71/72 positive pairs). Marginal AUC gain = <strong>+0.020</strong>.
            </div>
          </div>
        </div>

        <p style={{ fontSize: '14px', lineHeight: 1.6 }}>
          <strong>The Scientific Reality:</strong> The structural reading-order prior provides <strong>+0.368 AUC</strong> over the raw LLM (0.503 &rarr; 0.868). Adding the local LLM provides a modest <strong>+0.020 AUC gain</strong> (0.868 &rarr; 0.888). Rather than performing directional reasoning, the LLM functions as an <strong>undirected semantic filter</strong> that prunes spurious early concept pairings, boosting edge precision from 0.595 to 0.845.
        </p>
      </div>

      {/* The Circularity Disclosure */}
      <div className="card" style={{ borderLeft: '4px solid #f59e0b' }}>
        <h3 style={{ margin: '0 0 10px 0', fontSize: '18px', color: '#b45309', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertTriangle size={18} />
          4. The Circularity Risk & Scientific Disclosure
        </h3>
        <p>
          As an honest scientific study, we must disclose the circularity inherent in using textbook reading order to evaluate prerequisite benchmarks:
        </p>

        <div style={{ padding: '14px 18px', backgroundColor: '#fffbeb', borderRadius: 'var(--radius-md)', border: '1px solid #fde68a', margin: '12px 0', fontSize: '13.5px', color: '#92400e', lineHeight: 1.6 }}>
          <strong>Why is there circularity?</strong> The AL-CPL benchmark was authored by education researchers who designed the prerequisite ground truth by examining curriculum standards and standard textbook sequences. When our hybrid pipeline uses textbook reading order as a forward gate, it leverages the <em>exact same pedagogical sequencing</em> that educators used to create the benchmark!
        </div>

        <p style={{ fontSize: '13.5px', color: 'var(--text-secondary)' }}>
          While this alignment reflects real-world educational engineering, researchers must not mistake this for independent machine reasoning. When evaluating knowledge graphs on linear textbooks, high scores may simply demonstrate that textbook authors follow curriculum guidelines, not that the AI algorithm has discovered novel cognitive relationships.
        </p>
      </div>
    </div>
  );
};
