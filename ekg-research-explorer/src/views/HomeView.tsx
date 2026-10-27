import React from 'react';
import { PROJECT_META } from '../data/researchData';
import { ArrowRight, ShieldCheck, Sparkles, BookOpen, AlertCircle, Database, GitMerge, BarChart3, Scale } from 'lucide-react';

interface HomeViewProps {
  onNavigate: (sectionId: string) => void;
}

export const HomeView: React.FC<HomeViewProps> = ({ onNavigate }) => {
  return (
    <div>
      {/* Hero Section */}
      <div style={{ marginBottom: '40px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
          <span className="badge badge-primary">Research Documentation Hub</span>
          <span className="badge badge-success">
            <ShieldCheck size={12} /> 100% Empirically Verified
          </span>
          <span className="badge badge-warning">Double-Blind Submission Ready</span>
        </div>

        <h1 style={{ fontSize: '32px', lineHeight: 1.25, maxWidth: '1000px', marginBottom: '16px' }}>
          {PROJECT_META.title}
        </h1>

        <p style={{ fontSize: '16px', color: 'var(--text-secondary)', maxWidth: '900px', lineHeight: 1.65 }}>
          A comprehensive interactive technical guide to our empirical study comparing <strong>Symbolic Rules</strong>, <strong>Local Large Language Models (Qwen-2.5-7B)</strong>, and <strong>Structural Reading-Order Priors</strong> on the AL-CPL Geometry benchmark.
        </p>

        {/* Quick Action Buttons */}
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginTop: '20px' }}>
          <button
            onClick={() => onNavigate('results')}
            style={{
              padding: '10px 20px',
              backgroundColor: 'var(--primary)',
              color: '#fff',
              border: 'none',
              borderRadius: 'var(--radius-md)',
              fontWeight: 600,
              fontSize: '14px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            <BarChart3 size={16} />
            Explore Benchmark Results
          </button>

          <button
            onClick={() => onNavigate('graph-explorer')}
            style={{
              padding: '10px 20px',
              backgroundColor: 'var(--bg-surface)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-md)',
              fontWeight: 600,
              fontSize: '14px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            <GitMerge size={16} />
            Interactive Knowledge Graph
          </button>

          <button
            onClick={() => onNavigate('faq')}
            style={{
              padding: '10px 20px',
              backgroundColor: 'var(--bg-surface)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-md)',
              fontWeight: 600,
              fontSize: '14px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            <BookOpen size={16} />
            Oral Presentation Defense FAQ
          </button>
        </div>
      </div>

      {/* Abstract Callout */}
      <div className="card" style={{ marginBottom: '32px', backgroundColor: 'var(--bg-surface)', borderLeft: '4px solid var(--primary)' }}>
        <h3 style={{ margin: '0 0 10px 0', fontSize: '16px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <BookOpen size={18} style={{ color: 'var(--primary)' }} />
          Official Manuscript Abstract
        </h3>
        <p style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.7, margin: 0 }}>
          {PROJECT_META.abstract}
        </p>
      </div>

      {/* Clickable Visual Research Flow Blueprint */}
      <div className="card" style={{ marginBottom: '36px', padding: '24px' }}>
        <h3 style={{ margin: '0 0 6px 0', fontSize: '17px' }}>
          Visual Research Architecture Blueprint
        </h3>
        <p style={{ fontSize: '13.5px', color: 'var(--text-muted)', margin: '0 0 18px 0' }}>
          Click any phase of the pipeline to jump directly into its mathematical principles, implementation details, and empirical diagnostics:
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
          {[
            { step: "1. Corpus & Data", label: "CK-12 Geometry", sub: "12 Ch, 59 Sec, 6,104 Sentences", target: "dataset", icon: <Database size={18} /> },
            { step: "2. Pipelines", label: "Rule vs LLM", sub: "130 Terms (Rule) vs 204 (7B LLM)", target: "pipelines", icon: <GitMerge size={18} /> },
            { step: "3. Structural Priors", label: "Reading Order Gating", sub: "pos(u) < pos(v) Forward Gate", target: "priors", icon: <Sparkles size={18} /> },
            { step: "4. Benchmark", label: "AL-CPL Ground Truth", sub: "Common Set N=868 Pairs", target: "evaluation", icon: <ShieldCheck size={18} /> },
            { step: "5. Results & Ablations", label: "De-confounded Metrics", sub: "AUC 0.503 vs 0.868 vs 0.888", target: "results", icon: <BarChart3 size={18} /> },
            { step: "6. Scientific Audit", label: "Validity & Defense", sub: "Circularity & Threat Analysis", target: "discussion", icon: <Scale size={18} /> }
          ].map((node, i) => (
            <div
              key={i}
              onClick={() => onNavigate(node.target)}
              style={{
                padding: '16px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-color)',
                backgroundColor: 'var(--bg-subtle)',
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                transition: 'all 0.15s ease'
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = 'var(--primary)';
                e.currentTarget.style.backgroundColor = 'var(--primary-light)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = 'var(--border-color)';
                e.currentTarget.style.backgroundColor = 'var(--bg-subtle)';
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>{node.step}</span>
                <span style={{ color: 'var(--primary)' }}>{node.icon}</span>
              </div>
              <div style={{ fontWeight: 700, fontSize: '14px', color: 'var(--text-primary)' }}>{node.label}</div>
              <div style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>{node.sub}</div>
            </div>
          ))}
        </div>
      </div>

      {/* 5 Core Verified Research Findings */}
      <h2 style={{ fontSize: '22px', marginBottom: '16px' }}>5 Core Empirical Discoveries</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '18px', marginBottom: '36px' }}>
        {PROJECT_META.keyFindings.map((finding, idx) => (
          <div key={idx} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <span className="badge badge-primary">Finding #{idx + 1}</span>
              <span style={{ fontSize: '12px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--primary)' }}>
                {finding.stat}
              </span>
            </div>
            <h4 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
              {finding.title}
            </h4>
            <p style={{ fontSize: '13.5px', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.6 }}>
              {finding.detail}
            </p>
          </div>
        ))}
      </div>

      {/* Dataset & Benchmark Quick Summary Cards */}
      <div className="grid-2">
        <div className="card">
          <div className="card-title">
            <Database size={16} style={{ color: 'var(--primary)' }} />
            <span>Corpus: CK-12 Basic Geometry</span>
          </div>
          <p style={{ fontSize: '13.5px', margin: '4px 0 12px 0' }}>
            Open educational resource licensed under Creative Commons (CC BY-NC 3.0), structured into formal introductory chapters.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px', fontSize: '12.5px' }}>
            <div style={{ padding: '8px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-sm)' }}>
              <strong>12</strong> Chapters (59 Sections)
            </div>
            <div style={{ padding: '8px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-sm)' }}>
              <strong>6,104</strong> Sentences Indexed
            </div>
            <div style={{ padding: '8px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-sm)' }}>
              <strong>126,450</strong> Word Tokens
            </div>
            <div style={{ padding: '8px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-sm)' }}>
              <strong>Axiomatic</strong> Domain Progression
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-title">
            <ShieldCheck size={16} style={{ color: '#10b981' }} />
            <span>Benchmark: AL-CPL Geometry</span>
          </div>
          <p style={{ fontSize: '13.5px', margin: '4px 0 12px 0' }}>
            Authoritative concept prerequisite learning benchmark created by Liang et al. (AAAI 2015, EMNLP 2018).
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px', fontSize: '12.5px' }}>
            <div style={{ padding: '8px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-sm)' }}>
              <strong>89</strong> Ground Truth Concepts
            </div>
            <div style={{ padding: '8px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-sm)' }}>
              <strong>98</strong> Directed Prerequisites
            </div>
            <div style={{ padding: '8px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-sm)' }}>
              <strong>65 / 89 (73%)</strong> Covered by Textbook
            </div>
            <div style={{ padding: '8px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-sm)' }}>
              <strong>N = 868</strong> Evaluated Pair Set
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
