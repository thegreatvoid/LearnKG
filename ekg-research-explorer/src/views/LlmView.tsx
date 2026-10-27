import React from 'react';
import { Cpu, Terminal, ShieldAlert, CheckCircle2, AlertOctagon, HelpCircle } from 'lucide-react';

export const LlmView: React.FC = () => {
  return (
    <div>
      <div style={{ marginBottom: '32px' }}>
        <span className="badge badge-primary">Model Architecture & Prompting</span>
        <h1 style={{ marginTop: '8px' }}>Local LLM Methodology: Architecture, Prompting & Directional Failure</h1>
        <p style={{ fontSize: '16px', color: 'var(--text-secondary)', maxWidth: '900px' }}>
          A technical deep dive into our Ollama-based local inference setup using <code>Qwen-2.5-7B-Instruct</code>, the structured JSON schema validation mechanism, and the empirical root cause of chance-level prerequisite directionality.
        </p>
      </div>

      {/* Local Deployment Rationale */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <h3 style={{ margin: '0 0 10px 0', fontSize: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Cpu size={18} style={{ color: 'var(--primary)' }} />
          1. Why Local Open-Weight Models?
        </h3>
        <p>
          While cloud APIs (e.g., GPT-4o, Claude 3.5 Sonnet) offer immense parameter capacity, their adoption in real-world educational institutions faces three major roadblocks:
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '14px', marginTop: '12px' }}>
          <div style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'var(--bg-subtle)', border: '1px solid var(--border-color)' }}>
            <strong style={{ color: 'var(--primary)' }}>Student Data Privacy (FERPA / GDPR):</strong> School systems cannot transmit proprietary curricula or private student diagnostic profiles to external third-party API servers.
          </div>
          <div style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'var(--bg-subtle)', border: '1px solid var(--border-color)' }}>
            <strong style={{ color: 'var(--primary)' }}>Zero Inference Cost:</strong> Running Qwen-2.5-7B locally on commodity GPU or Apple Silicon hardware enables non-profit open curriculum indexing with zero ongoing API token fees.
          </div>
          <div style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'var(--bg-subtle)', border: '1px solid var(--border-color)' }}>
            <strong style={{ color: 'var(--primary)' }}>Complete Reproducibility:</strong> Open weights ensure experiments can be audited and reproduced indefinitely without risk of vendor model deprecation or silent prompt drift.
          </div>
        </div>
      </div>

      {/* Structured Output Prompting */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <h3 style={{ margin: '0 0 10px 0', fontSize: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Terminal size={18} style={{ color: 'var(--primary)' }} />
          2. Prompt Engineering & JSON Schema Enforcement
        </h3>
        <p>
          Unstructured natural language generation is notorious for hallucinating syntax errors. In <code>kgx_v2</code>, we enforced strict JSON schema formatting via Ollama's structured output mode:
        </p>

        <div style={{ backgroundColor: 'var(--bg-code)', padding: '16px 20px', borderRadius: 'var(--radius-md)', color: 'var(--text-code)', fontFamily: 'var(--font-mono)', fontSize: '12.5px', lineHeight: 1.5, overflowX: 'auto', marginBottom: '14px' }}>
          <pre>{`{
  "system": "You are a formal educational ontology specialist in Euclidean geometry.",
  "prompt": "Given concept A: '\${conceptA}' and concept B: '\${conceptB}', along with their textbook definitions, classify their relationship into EXACTLY one of: ['prerequisite', 'part_of', 'application', 'extension', 'similarity', 'none']. If a prerequisite exists, indicate whether A is a prerequisite for B, or B is for A.",
  "response_format": {
    "type": "json_object",
    "schema": {
      "relation_type": "string (enum)",
      "is_directed": "boolean",
      "direction": "string (A_to_B | B_to_A | symmetric | none)",
      "confidence": "number (0.0 to 1.0)",
      "evidence_sentence": "string"
    }
  }
}`}</pre>
        </div>

        <p style={{ fontSize: '13.5px' }}>
          Schema adherence reached over <strong>98.5%</strong> structural validity. However, <em>syntactic validity is not semantic correctness</em>. While the LLM generated perfectly valid JSON, its internal relationship classifications revealed profound directional failure.
        </p>
      </div>

      {/* The Expository Symmetry Failure Mode */}
      <div className="card" style={{ marginBottom: '24px', borderLeft: '4px solid #ef4444' }}>
        <h3 style={{ margin: '0 0 10px 0', fontSize: '18px', color: '#b91c1c', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldAlert size={18} />
          3. The Root Cause: Expository Textual Symmetry
        </h3>
        <p>
          On ground-truth positive pairs in the common covered set ($N=868$), the local 7B LLM achieved exactly <strong>4 out of 8</strong> correct directional classifications (<strong>50.0% accuracy</strong>). It is literally the equivalent of flipping a coin.
        </p>

        <div style={{ padding: '14px 18px', backgroundColor: '#fef2f2', borderRadius: 'var(--radius-md)', border: '1px solid #fecaca', margin: '14px 0' }}>
          <div style={{ fontWeight: 700, fontSize: '13px', color: '#991b1b', marginBottom: '4px' }}>
            Example: Why the 7B Parameter Model Cannot Orient "Angle" and "Ray"
          </div>
          <div style={{ fontStyle: 'italic', fontSize: '13px', color: '#7f1d1d' }}>
            "An angle is defined as a geometric figure formed by two rays sharing a common vertex."
          </div>
          <div style={{ fontSize: '12.5px', color: '#991b1b', marginTop: '8px', lineHeight: 1.5 }}>
            Both concepts co-occur in the same sentence. Grammatically, <em>"Angle"</em> is the grammatical subject and <em>"Ray"</em> is the predicate noun. To a student, <em>Ray</em> is the prerequisite because you must understand rays to construct an angle. But to a language model reading purely surface syntax, <em>Angle</em> is introduced first in the sentence, creating severe directional ambiguity!
          </div>
        </div>

        <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
          Introductory textbooks describe geometric relationships <strong>symmetrically</strong>. They do not write <em>"A student must master rays prior to studying angles."</em> Without temporal, historical, or curriculum position markers, a 7B language model reading sentence snippets alone is fundamentally blind to pedagogical dependency.
        </p>
      </div>

      {/* 5 Distinct Operations in Educational KG Construction */}
      <div className="card">
        <h3 style={{ margin: '0 0 10px 0', fontSize: '18px' }}>
          4. De-conflating the 5 Different Operations in KG Pipelines
        </h3>
        <p style={{ fontSize: '13.5px', color: 'var(--text-secondary)' }}>
          To prevent misleading research claims, the paper strictly separates these five distinct operations:
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px', marginTop: '14px' }}>
          {[
            { num: "Op 1", title: "Semantic Relatedness", desc: "Checking if concepts u and v interact in geometry. (LLMs perform well here: ~0.84 precision)." },
            { num: "Op 2", title: "Textual Grounding", desc: "Verifying if the textbook has a sentence connecting u and v. (Audited via BIGS)." },
            { num: "Op 3", title: "Relation Typing", desc: "Distinguishing Part-of vs Prerequisite vs Application vs Similarity." },
            { num: "Op 4", title: "Directional Orientation", desc: "Determining whether u ≺ v or v ≺ u. (LLM operates at 50% chance!)." },
            { num: "Op 5", title: "Structural Gating", desc: "Enforcing pos(u) < pos(v) using document hierarchy. (Solves directionality!)." }
          ].map((op, idx) => (
            <div key={idx} style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'var(--bg-subtle)', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--primary)' }}>{op.num}</div>
              <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)', margin: '3px 0' }}>{op.title}</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{op.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
