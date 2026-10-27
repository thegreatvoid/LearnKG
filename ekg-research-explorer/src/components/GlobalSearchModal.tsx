import React, { useState, useEffect, useRef } from 'react';
import { Search, X, BookA, HelpCircle, GitMerge, FileText, ArrowRight } from 'lucide-react';
import { GLOSSARY_ENTRIES, PRESENTATION_FAQS, RESEARCH_QUESTIONS } from '../data/researchData';
import { NAVIGATION_GROUPS } from './Sidebar';

interface SearchResult {
  title: string;
  category: string;
  snippet: string;
  sectionId: string;
  icon: React.ReactNode;
}

interface GlobalSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (sectionId: string) => void;
}

export const GlobalSearchModal: React.FC<GlobalSearchModalProps> = ({
  isOpen,
  onClose,
  onNavigate
}) => {
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery('');
    }
  }, [isOpen]);

  // Handle Cmd+K / Ctrl+K and Esc
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (isOpen) onClose();
        else onClose(); // parent toggles
      }
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // Build searchable index
  const results: SearchResult[] = [];
  const q = query.toLowerCase().trim();

  if (q.length > 0) {
    // 1. Navigation sections
    NAVIGATION_GROUPS.forEach(g => {
      g.sections.forEach(s => {
        if (s.label.toLowerCase().includes(q) || g.title.toLowerCase().includes(q)) {
          results.push({
            title: s.label,
            category: "Page Section",
            snippet: `Navigate directly to ${s.label} in ${g.title}`,
            sectionId: s.id,
            icon: <FileText size={15} />
          });
        }
      });
    });

    // 2. Glossary terms
    GLOSSARY_ENTRIES.forEach(entry => {
      if (
        entry.term.toLowerCase().includes(q) ||
        entry.plainDef.toLowerCase().includes(q) ||
        entry.technicalDef.toLowerCase().includes(q)
      ) {
        results.push({
          title: entry.term,
          category: `Glossary (${entry.category})`,
          snippet: entry.plainDef,
          sectionId: 'glossary',
          icon: <BookA size={15} />
        });
      }
    });

    // 3. FAQs
    PRESENTATION_FAQS.forEach(faq => {
      if (
        faq.question.toLowerCase().includes(q) ||
        faq.quickAnswer.toLowerCase().includes(q) ||
        faq.deepAnswer.toLowerCase().includes(q)
      ) {
        results.push({
          title: faq.question,
          category: `Defense FAQ (${faq.category})`,
          snippet: faq.quickAnswer,
          sectionId: 'faq',
          icon: <HelpCircle size={15} />
        });
      }
    });

    // 4. Research Questions
    RESEARCH_QUESTIONS.forEach(rq => {
      if (
        rq.id.toLowerCase().includes(q) ||
        rq.title.toLowerCase().includes(q) ||
        rq.question.toLowerCase().includes(q)
      ) {
        results.push({
          title: `${rq.id}: ${rq.title}`,
          category: "Research Question",
          snippet: rq.question,
          sectionId: 'rqs',
          icon: <GitMerge size={15} />
        });
      }
    });
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid var(--border-color)', gap: '12px' }}>
          <Search size={18} style={{ color: 'var(--text-muted)' }} />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search concepts, RQs, metrics, algorithms, FAQs..."
            style={{
              flex: 1,
              background: 'none',
              border: 'none',
              outline: 'none',
              fontSize: '15px',
              color: 'var(--text-primary)',
              fontFamily: 'inherit'
            }}
          />
          <button className="btn-icon" onClick={onClose} style={{ width: '28px', height: '28px' }}>
            <X size={15} />
          </button>
        </div>

        <div style={{ maxHeight: '420px', overflowY: 'auto', padding: '10px 12px' }}>
          {query.trim().length === 0 ? (
            <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13.5px' }}>
              <div>Type any term, metric (e.g. <code>ROC-AUC</code>, <code>AHP</code>, <code>Reading Order</code>, <code>Closure F1</code>) or question to search across the entire research documentation.</div>
            </div>
          ) : results.length === 0 ? (
            <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13.5px' }}>
              No direct matches found for "{query}". Try searching for broader terms like <code>baseline</code>, <code>hybrid</code>, or <code>bottleneck</code>.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {results.slice(0, 8).map((res, i) => (
                <div
                  key={i}
                  onClick={() => {
                    onNavigate(res.sectionId);
                    onClose();
                  }}
                  style={{
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    border: '1px solid transparent',
                    transition: 'all 0.15s ease'
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.backgroundColor = 'var(--bg-subtle)';
                    e.currentTarget.style.borderColor = 'var(--border-color)';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.backgroundColor = 'transparent';
                    e.currentTarget.style.borderColor = 'transparent';
                  }}
                >
                  <div style={{ color: 'var(--primary)', flexShrink: 0 }}>{res.icon}</div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontWeight: 600, fontSize: '13.5px', color: 'var(--text-primary)' }}>
                        {res.title}
                      </span>
                      <span className="badge badge-primary" style={{ fontSize: '10px' }}>
                        {res.category}
                      </span>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {res.snippet}
                    </div>
                  </div>
                  <ArrowRight size={14} style={{ color: 'var(--text-dim)' }} />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
