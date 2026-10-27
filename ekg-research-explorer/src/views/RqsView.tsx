import React from 'react';
import { RESEARCH_QUESTIONS } from '../data/researchData';
import { HelpCircle, ArrowRight, ShieldCheck, AlertCircle, FileText, CheckCircle2 } from 'lucide-react';

export const RqsView: React.FC = () => {
  return (
    <div>
      <div style={{ marginBottom: '32px' }}>
        <span className="badge badge-primary">Scientific Methodology</span>
        <h1 style={{ marginTop: '8px' }}>Research Questions, Hypotheses & Evidence</h1>
        <p style={{ fontSize: '16px', color: 'var(--text-secondary)', maxWidth: '900px' }}>
          Our empirical comparative evaluation is structured around five core research questions designed to deconstruct the contributions of symbolic rules, local LLM classifiers, and structural reading-order priors.
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
        {RESEARCH_QUESTIONS.map((rq, idx) => (
          <div key={rq.id} className="card" style={{ padding: '26px', borderLeft: '4px solid var(--primary)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', flexWrap: 'wrap', gap: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="badge badge-primary" style={{ fontSize: '12px' }}>{rq.id}</span>
                <span style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 600 }}>{rq.pipelineOrBaseline}</span>
              </div>
              <span className="badge badge-success">
                <ShieldCheck size={12} /> Verified from Artifacts
              </span>
            </div>

            <h3 style={{ fontSize: '19px', fontWeight: 800, color: 'var(--text-primary)', margin: '0 0 10px 0' }}>
              {rq.title}
            </h3>

            <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--primary)', backgroundColor: 'var(--primary-light)', padding: '12px 16px', borderRadius: 'var(--radius-md)', marginBottom: '16px', lineHeight: 1.5 }}>
              "{rq.question}"
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', marginBottom: '16px' }}>
              <div>
                <h5 style={{ fontSize: '11.5px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '4px' }}>
                  Scientific Motivation
                </h5>
                <p style={{ fontSize: '13.5px', color: 'var(--text-secondary)', margin: 0 }}>
                  {rq.motivation}
                </p>
              </div>

              <div>
                <h5 style={{ fontSize: '11.5px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '4px' }}>
                  Evaluation Method & Benchmark
                </h5>
                <p style={{ fontSize: '13.5px', color: 'var(--text-secondary)', margin: 0 }}>
                  {rq.evalMethod}
                </p>
              </div>
            </div>

            {/* Evidence & Findings Box */}
            <div style={{ backgroundColor: 'var(--bg-subtle)', padding: '14px 18px', borderRadius: 'var(--radius-md)', marginBottom: '16px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-primary)', marginBottom: '4px' }}>
                Observed Empirical Evidence
              </div>
              <div style={{ fontSize: '13.5px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                {rq.reportedEvidence}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', marginBottom: '14px' }}>
              <div>
                <h5 style={{ fontSize: '11.5px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--primary)', marginBottom: '4px' }}>
                  Interpretation of Results
                </h5>
                <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0 }}>
                  {rq.interpretation}
                </p>
              </div>

              <div>
                <h5 style={{ fontSize: '11.5px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--danger)', marginBottom: '4px' }}>
                  Documented Limitations
                </h5>
                <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0 }}>
                  {rq.limitations}
                </p>
              </div>
            </div>

            {/* Justified Conclusion */}
            <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '12px', display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
              <CheckCircle2 size={16} style={{ color: '#10b981', flexShrink: 0, marginTop: '2px' }} />
              <div style={{ fontSize: '13.5px', color: 'var(--text-primary)' }}>
                <strong>Justified Conclusion:</strong> {rq.justifiedConclusion}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
