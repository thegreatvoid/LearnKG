import React from 'react';
import { Scale, ShieldAlert, CheckCircle2, AlertTriangle, Layers, BookOpen } from 'lucide-react';

export const DiscussionView: React.FC = () => {
  return (
    <div>
      <div style={{ marginBottom: '32px' }}>
        <span className="badge badge-primary">Scientific Rigor & Honest Limitations</span>
        <h1 style={{ marginTop: '8px' }}>Scientific Interpretation & Threats to Validity</h1>
        <p style={{ fontSize: '16px', color: 'var(--text-secondary)', maxWidth: '900px' }}>
          Deconstruct each major research finding across three distinct layers (Beginner, Technical, and Scientific Limitation) and review the comprehensive threats to internal, construct, and external validity.
        </p>
      </div>

      {/* 3-Layer Explanations */}
      <h2 style={{ fontSize: '20px', marginBottom: '16px' }}>
        1. Three-Layer Interpretations of the Core Findings
      </h2>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', marginBottom: '36px' }}>
        {[
          {
            title: "Finding 1: The Local LLM Operates at Chance (AUC 0.503)",
            beginner: "When given textbook definition snippets, a 7B AI model is no better at telling which concept came first than flipping a coin.",
            technical: "On the N = 868 common covered AL-CPL pair set, kgx_v2 achieved an ROC-AUC of 0.503 [95% CI: 0.49, 0.51] and exactly 4/8 (50.0%) directional accuracy on positive pairs. The 95% confidence interval encompasses 0.500, confirming performance indistinguishable from an unweighted random classifier.",
            limitation: "This finding applies specifically to zero-shot inference using sentence definitions on a 7B parameter open-weight model. Larger models (70B+) or few-shot chain-of-thought prompting on full chapter text might exhibit stronger directional reasoning."
          },
          {
            title: "Finding 2: The Reading-Order Baseline is Dominant (AUC 0.868)",
            beginner: "Simply checking which concept appears earlier in the book works remarkably well, correctly pointing arrows in 96.5% of cases.",
            technical: "A zero-parameter deterministic rule (u precedes v) achieves an edge F1 of 0.736, an ROC-AUC of 0.868 [95% CI: 0.81, 0.91], and correctly orients 251 out of 260 ground truth positive prerequisites.",
            limitation: "The reading-order prior produces numerous false-positive edges between distant, unrelated concepts across chapters and lacks semantic relation types. It is an inductive regularizer, not a complete knowledge graph."
          },
          {
            title: "Finding 3: The Hybrid is Structurally Driven (Marginal LLM AUC +0.020)",
            beginner: "The hybrid pipeline looks great, but almost all of its success comes from the book order rule; the AI only helped clean up early false alarms.",
            technical: "Ablation reveals that reading order alone accounts for 0.868 of the hybrid's 0.888 AUC. The marginal contribution of Qwen-2.5-7B is +0.020 AUC. The LLM functions as an undirected semantic pruning filter that prunes early false positives, raising precision from 0.595 to 0.845.",
            limitation: "Circularity risk: curriculum benchmarks were created by inspecting textbook sequences, meaning the reading-order forward gate rides the same structural correlation embedded in the ground truth."
          },
          {
            title: "Finding 4: Multi-Criteria Saaty AHP Weighting is Redundant",
            beginner: "Complex mathematical formulas for combining features sound sophisticated, but simple word co-occurrence works just as well or better.",
            technical: "The 4-factor Saaty AHP formula (CR = 0.022) achieved an NDCG@10 of 0.709. Simple sentence co-occurrence alone achieved 0.723 (p = 0.68, not significant vs AHP), while raw co-occurrence count reached 0.742. Definition overlap (weighted at 52% in AHP) scored 0.589, near random noise.",
            limitation: "In domains with longer, highly technical definitions, Jaccard token overlap may carry more signal than in elementary Euclidean geometry."
          }
        ].map((item, idx) => (
          <div key={idx} className="card" style={{ padding: '22px' }}>
            <h3 style={{ margin: '0 0 14px 0', fontSize: '17px', color: 'var(--text-primary)' }}>{item.title}</h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ padding: '10px 14px', background: '#ecfdf5', borderRadius: 'var(--radius-md)', borderLeft: '3px solid #10b981' }}>
                <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: '#047857' }}>Layer 1: Plain-English Intuition</div>
                <div style={{ fontSize: '13.5px', color: '#065f46', marginTop: '2px' }}>{item.beginner}</div>
              </div>

              <div style={{ padding: '10px 14px', background: 'var(--primary-light)', borderRadius: 'var(--radius-md)', borderLeft: '3px solid var(--primary)' }}>
                <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--primary)' }}>Layer 2: Technical & Empirical Interpretation</div>
                <div style={{ fontSize: '13px', color: 'var(--text-primary)', marginTop: '2px', lineHeight: 1.5 }}>{item.technical}</div>
              </div>

              <div style={{ padding: '10px 14px', background: '#fffbeb', borderRadius: 'var(--radius-md)', borderLeft: '3px solid #f59e0b' }}>
                <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: '#b45309' }}>Layer 3: Scientific Caveat & Limitation</div>
                <div style={{ fontSize: '12.5px', color: '#92400e', marginTop: '2px', lineHeight: 1.5 }}>{item.limitation}</div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Threats to Validity */}
      <h2 style={{ fontSize: '20px', marginBottom: '16px' }}>
        2. Comprehensive Threats to Validity (Conference Quality Audit)
      </h2>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
        <div className="card" style={{ borderTop: '4px solid #ef4444' }}>
          <div className="card-title" style={{ color: '#dc2626' }}>
            <ShieldAlert size={16} />
            <span>Internal Validity Threats</span>
          </div>
          <ul style={{ paddingLeft: '18px', fontSize: '13px', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <li><strong>Candidate Filtering Bottleneck:</strong> Filtering candidates using co-occurrence windows discards 96.5% of valid ground truth pairs, choking end-to-end recall before classification even starts.</li>
            <li><strong>Fuzzy Concept Matching:</strong> The Levenshtein &ge; 0.85 threshold and manual synonym dictionary could introduce alignment noise or subjectivity.</li>
          </ul>
        </div>

        <div className="card" style={{ borderTop: '4px solid #f59e0b' }}>
          <div className="card-title" style={{ color: '#d97706' }}>
            <AlertTriangle size={16} />
            <span>Construct Validity Threats</span>
          </div>
          <ul style={{ paddingLeft: '18px', fontSize: '13px', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <li><strong>Curriculum Circularity:</strong> Benchmark authors designed AL-CPL by following curriculum standards; using reading order implicitly leaks that same curriculum sequence.</li>
            <li><strong>Reference-Free Non-Prerequisites:</strong> <em>Part-of</em>, <em>Application</em>, and <em>Similarity</em> lack human gold standards and were audited solely via structural consistency heuristics.</li>
          </ul>
        </div>

        <div className="card" style={{ borderTop: '4px solid #2563eb' }}>
          <div className="card-title" style={{ color: '#2563eb' }}>
            <Scale size={16} />
            <span>External Validity Threats</span>
          </div>
          <ul style={{ paddingLeft: '18px', fontSize: '13px', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <li><strong>Single Educational Domain:</strong> Geometry is uniquely axiomatic and deductive. Reading order may carry far less predictive power in non-linear subjects like History or Literature.</li>
            <li><strong>Single Model Family:</strong> Results are based on Ollama <code>Qwen-2.5-7B</code>. Larger models (70B+) or fine-tuned specialist models may possess stronger zero-shot directional reasoning.</li>
          </ul>
        </div>
      </div>
    </div>
  );
};
