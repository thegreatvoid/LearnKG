import React, { useState } from 'react';
import { PRESENTATION_FAQS, FAQItem } from '../data/researchData';
import { MessageSquare, ShieldAlert, Zap, BookOpen, ChevronDown, ChevronUp, Filter } from 'lucide-react';

export const PresentationCards: React.FC = () => {
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [expandedFaqId, setExpandedFaqId] = useState<string | null>('faq-1');

  const categories = ['All', 'Motivation', 'Baselines', 'LLM Performance', 'Hybrid & Circularity', 'Evaluation', 'Defense'];

  const filteredFaqs = PRESENTATION_FAQS.filter(
    faq => selectedCategory === 'All' || faq.category === selectedCategory
  );

  return (
    <div className="card" style={{ padding: '24px', marginBottom: '32px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
        <div>
          <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <MessageSquare size={18} style={{ color: 'var(--primary)' }} />
            <span>Oral Presentation Defense & Reviewer FAQ</span>
            <span className="badge badge-primary">20 Questions</span>
          </h3>
          <p style={{ margin: '4px 0 0 0', fontSize: '13.5px' }}>
            Curated questions commonly asked by professors, conference reviewers, and examination committees. Toggle between the 30-second elevator pitch and the rigorous technical defense.
          </p>
        </div>

        {/* Category Filter Pills */}
        <div style={{ display: 'flex', gap: '6px', background: 'var(--bg-subtle)', padding: '4px', borderRadius: 'var(--radius-md)', flexWrap: 'wrap' }}>
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              style={{
                padding: '5px 10px',
                fontSize: '11.5px',
                fontWeight: 600,
                borderRadius: 'var(--radius-sm)',
                border: 'none',
                cursor: 'pointer',
                background: selectedCategory === cat ? 'var(--primary)' : 'none',
                color: selectedCategory === cat ? '#fff' : 'var(--text-secondary)'
              }}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {filteredFaqs.map(faq => {
          const isExpanded = expandedFaqId === faq.id;

          return (
            <div
              key={faq.id}
              style={{
                border: '1px solid',
                borderColor: isExpanded ? 'var(--primary)' : 'var(--border-color)',
                borderRadius: 'var(--radius-lg)',
                backgroundColor: 'var(--bg-surface)',
                overflow: 'hidden',
                transition: 'all 0.2s ease'
              }}
            >
              {/* Question Header */}
              <div
                onClick={() => setExpandedFaqId(isExpanded ? null : faq.id)}
                style={{
                  padding: '16px 20px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  cursor: 'pointer',
                  backgroundColor: isExpanded ? 'var(--primary-light)' : 'transparent'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <span className="badge badge-primary" style={{ fontSize: '10.5px' }}>{faq.category}</span>
                  <span style={{ fontWeight: 700, fontSize: '15px', color: 'var(--text-primary)' }}>
                    {faq.question}
                  </span>
                </div>
                <div style={{ color: 'var(--text-dim)' }}>
                  {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                </div>
              </div>

              {/* Collapsible Content */}
              {isExpanded && (
                <div style={{ padding: '20px', borderTop: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {/* Quick 30s Answer */}
                  <div>
                    <div style={{ fontSize: '11px', fontWeight: 800, textTransform: 'uppercase', color: 'var(--primary)', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                      <Zap size={14} /> Quick Elevator Pitch (30 Seconds)
                    </div>
                    <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.5, backgroundColor: 'var(--bg-subtle)', padding: '12px 14px', borderRadius: 'var(--radius-md)' }}>
                      "{faq.quickAnswer}"
                    </div>
                  </div>

                  {/* Deep Technical Defense */}
                  <div>
                    <div style={{ fontSize: '11px', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                      <BookOpen size={14} /> Comprehensive Technical Defense
                    </div>
                    <div style={{ fontSize: '13.5px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                      {faq.deepAnswer}
                    </div>
                  </div>

                  {/* Supporting metric badge and pitfall warning */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '12px', borderTop: '1px solid var(--border-color)', paddingTop: '12px' }}>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      <strong>Key Evidence Coordinate:</strong> <code style={{ color: 'var(--primary)' }}>{faq.keyMetric}</code>
                    </div>

                    <div style={{ fontSize: '12px', color: '#b91c1c', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <ShieldAlert size={14} style={{ flexShrink: 0 }} />
                      <span><strong>Pitfall to Avoid:</strong> {faq.pitfallToAvoid}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
