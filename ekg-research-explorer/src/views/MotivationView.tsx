import React from 'react';
import { Lightbulb, BookOpen, AlertTriangle, ArrowRight, ShieldCheck, CheckCircle2 } from 'lucide-react';

export const MotivationView: React.FC = () => {
  return (
    <div>
      <div style={{ marginBottom: '32px' }}>
        <span className="badge badge-primary">Foundational Principles</span>
        <h1 style={{ marginTop: '8px' }}>Problem Statement, Motivation & First Principles</h1>
        <p style={{ fontSize: '16px', color: 'var(--text-secondary)', maxWidth: '900px' }}>
          Understanding why automatic Educational Knowledge Graph construction is challenging, why local privacy-preserving LLMs are appealing yet prone to directional failure, and why document reading order acts as a dominant structural regularizer.
        </p>
      </div>

      {/* What is an EKG? */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <h3 style={{ margin: '0 0 10px 0', fontSize: '18px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Lightbulb size={18} style={{ color: 'var(--primary)' }} />
          1. What is an Educational Knowledge Graph (EKG)?
        </h3>
        <p>
          Unlike general-purpose knowledge graphs (such as DBpedia or Wikidata) that model static factual assertions (e.g., <em>"Paris is the capital of France"</em>), an <strong>Educational Knowledge Graph (EKG)</strong> models cognitive concepts and pedagogical progression. 
        </p>
        <p>
          Nodes in an EKG represent <strong>learning concepts</strong> (e.g., <em>Acute Angle</em>, <em>Pythagorean Theorem</em>, <em>Triangle Congruence</em>), while directed edges encode <strong>pedagogical dependencies</strong>—most importantly, the <em>Prerequisite</em> relation.
        </p>

        <div className="callout" style={{ margin: '14px 0 0 0' }}>
          <strong>Why EKGs matter for real-world learning:</strong> When a high school student struggles to solve a problem involving the <em>Pythagorean Theorem</em>, the underlying learning gap is rarely the algebraic formula itself. It is frequently an unmastered prerequisite: <em>Right Triangles</em>, <em>Square Roots</em>, or <em>Perpendicular Lines</em>. An EKG allows intelligent tutoring systems to traverse backwards along directed dependency edges to diagnose and remediate foundational learning deficits.
        </div>
      </div>

      {/* Accessible Step-by-Step Geometry Example */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <h3 style={{ margin: '0 0 10px 0', fontSize: '18px', color: 'var(--text-primary)' }}>
          2. The Euclidean Axiomatic Ladder: An Intuitive Geometry Walkthrough
        </h3>
        <p>
          To understand why prerequisite extraction is challenging, consider how Euclidean geometry builds from zero-dimensional primitives up to rigorous deductive proofs:
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px', margin: '20px 0' }}>
          {[
            { step: "Tier 1: Primitives", title: "Point, Line, Plane", desc: "Undefined primitives. A line is defined as an infinite collinear set of points." },
            { step: "Tier 2: Linear Subsets", title: "Segment, Ray", desc: "A ray is a half-line with an endpoint; a segment has two endpoints." },
            { step: "Tier 3: Angular Figures", title: "Angle, Right Angle", desc: "Two rays meeting at a common vertex form an angle." },
            { step: "Tier 4: Polygons", title: "Triangle, Polygon", desc: "Three coplanar line segments connecting end-to-end form a triangle." },
            { step: "Tier 5: Theorems & Proofs", title: "Pythagorean Theorem", desc: "Requires right angles, right triangles, and area multiplication to prove." }
          ].map((tier, idx) => (
            <div key={idx} style={{ padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-subtle)' }}>
              <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--primary)' }}>{tier.step}</div>
              <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)', margin: '4px 0' }}>{tier.title}</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{tier.desc}</div>
            </div>
          ))}
        </div>

        <p style={{ fontSize: '14px' }}>
          Notice that you <strong>cannot</strong> understand what a <em>Triangle</em> is without first knowing what a <em>Line Segment</em> and an <em>Angle</em> are. This dependency is strictly directed and irreversible.
        </p>
      </div>

      {/* Why Automatic Extraction is Hard: Rules vs LLMs */}
      <div className="grid-2" style={{ marginBottom: '24px' }}>
        <div className="card">
          <div className="card-title">
            <AlertTriangle size={16} style={{ color: '#ef4444' }} />
            <span>Why Symbolic Rules Collapse</span>
          </div>
          <p style={{ fontSize: '13.5px' }}>
            Rule-based information extraction relies on lexico-syntactic patterns (Hearst patterns like <em>"X is required for Y"</em> or <em>"X is a prerequisite of Y"</em>).
          </p>
          <ul style={{ paddingLeft: '18px', fontSize: '13px', color: 'var(--text-secondary)' }}>
            <li>Textbook authors rarely write pedagogical warnings explicitly. They simply introduce the concept and proceed.</li>
            <li>In CK-12 Basic Geometry, pattern matching found only 7 prerequisite edges out of 260 ground-truth pairs, resulting in catastrophic recall (0.027).</li>
          </ul>
        </div>

        <div className="card">
          <div className="card-title">
            <AlertTriangle size={16} style={{ color: '#f59e0b' }} />
            <span>Why Local LLMs Operate at Chance</span>
          </div>
          <p style={{ fontSize: '13.5px' }}>
            When a local open-weight LLM (Qwen-2.5-7B) reads textbook definitions, it encounters <strong>expository symmetry</strong>:
          </p>
          <div style={{ fontStyle: 'italic', fontSize: '12.5px', background: 'var(--bg-subtle)', padding: '8px 10px', borderRadius: '4px', margin: '8px 0' }}>
            "Two rays sharing an initial endpoint form an angle."
          </div>
          <ul style={{ paddingLeft: '18px', fontSize: '13px', color: 'var(--text-secondary)' }}>
            <li>The sentence describes an equivalence or joint presence, lacking any asymmetric directional marker.</li>
            <li>Without external curriculum context, the model guesses edge direction at 50% accuracy (ROC-AUC 0.503).</li>
          </ul>
        </div>
      </div>

      {/* The Structural Prior Insight */}
      <div className="card" style={{ marginBottom: '24px', borderLeft: '4px solid #10b981' }}>
        <h3 style={{ margin: '0 0 10px 0', fontSize: '18px', color: 'var(--text-primary)' }}>
          3. The Structural Prior: Why Linear Reading Order is Dominant
        </h3>
        <p>
          Curriculum authors do not introduce advanced concepts at random. They deliberately organize textbook chapters in pedagogical sequence:
        </p>
        <div className="formula-card">
          {`pos(u) < pos(v) => u appears earlier in the curriculum than v`}
        </div>
        <p>
          In our evaluation against the AL-CPL ground truth, this zero-parameter reading-order baseline achieved:
        </p>
        <ul style={{ paddingLeft: '20px', fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '14px' }}>
          <li><strong>ROC-AUC: 0.868 [95% CI: 0.81, 0.91]</strong> (compared to 0.503 for the standalone LLM).</li>
          <li><strong>Directional Accuracy: 251 / 260 (96.5%)</strong>.</li>
        </ul>
        <p>
          This establishes that the pedagogical ordering embedded in textbook layout provides an overwhelming signal that easily outperforms unconstrained neural classification.
        </p>
      </div>

      {/* What the Research Establishes vs What it Does NOT Claim */}
      <div className="grid-2">
        <div className="card" style={{ borderTop: '4px solid #10b981' }}>
          <div className="card-title" style={{ color: '#059669' }}>
            <CheckCircle2 size={16} />
            <span>What This Research Formally Establishes</span>
          </div>
          <ul style={{ paddingLeft: '18px', fontSize: '13px', color: 'var(--text-secondary)' }}>
            <li>Local 7B LLMs cannot infer prerequisite directionality from textbook snippets alone (50% chance).</li>
            <li>Linear reading order is a massive structural prior that must be controlled for in all EKG benchmarks.</li>
            <li>In the hybrid pipeline, 97.7% of the AUC gain comes from structural gating, not LLM reasoning.</li>
            <li>The LLM's true contribution in the hybrid is precision pruning (+0.020 AUC gain).</li>
            <li>Multi-criteria Saaty AHP weighting is redundant when co-occurrence is available (p = 0.68).</li>
          </ul>
        </div>

        <div className="card" style={{ borderTop: '4px solid #ef4444' }}>
          <div className="card-title" style={{ color: '#dc2626' }}>
            <AlertTriangle size={16} />
            <span>What This Research Does NOT Claim</span>
          </div>
          <ul style={{ paddingLeft: '18px', fontSize: '13px', color: 'var(--text-secondary)' }}>
            <li>We do NOT claim LLMs are universally incapable of education tasks (larger 70B+ models might improve).</li>
            <li>We do NOT claim reading order alone is a complete knowledge graph (it has no semantic labels).</li>
            <li>We do NOT claim geometry findings generalize automatically to non-deductive fields like History.</li>
            <li>We do NOT claim to have introduced a new foundational machine learning architecture.</li>
          </ul>
        </div>
      </div>
    </div>
  );
};
