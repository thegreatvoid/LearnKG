import React, { useState } from 'react';
import { GLOSSARY_ENTRIES, GlossaryEntry } from '../data/researchData';
import { BookA, Search, Filter, Code } from 'lucide-react';

export const SearchableGlossary: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');

  const categories = ['All', 'Foundations', 'Extraction', 'Graph Theory', 'Evaluation', 'Priors & Ablation'];

  const filteredEntries = GLOSSARY_ENTRIES.filter(entry => {
    const matchesCat = selectedCategory === 'All' || entry.category === selectedCategory;
    const q = searchQuery.toLowerCase().trim();
    const matchesQuery =
      q.length === 0 ||
      entry.term.toLowerCase().includes(q) ||
      entry.plainDef.toLowerCase().includes(q) ||
      entry.technicalDef.toLowerCase().includes(q) ||
      entry.example.toLowerCase().includes(q);
    return matchesCat && matchesQuery;
  });

  return (
    <div className="card" style={{ padding: '24px', marginBottom: '32px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
        <div>
          <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <BookA size={18} style={{ color: 'var(--primary)' }} />
            <span>Searchable Research Glossary & Formal Definitions</span>
            <span className="badge badge-primary">{GLOSSARY_ENTRIES.length} Terms</span>
          </h3>
          <p style={{ margin: '4px 0 0 0', fontSize: '13.5px' }}>
            Comprehensive mathematical definitions, plain-English analogies, formal equations, and repository cross-references for every core concept in the study.
          </p>
        </div>

        {/* Search input */}
        <div style={{ position: 'relative', width: '280px' }}>
          <Search size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search glossary terms..."
            style={{
              width: '100%',
              padding: '8px 12px 8px 36px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-surface)',
              color: 'var(--text-primary)',
              fontSize: '13px',
              outline: 'none'
            }}
          />
        </div>
      </div>

      {/* Category Pills */}
      <div style={{ display: 'flex', gap: '6px', marginBottom: '20px', flexWrap: 'wrap' }}>
        {categories.map(cat => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            style={{
              padding: '5px 12px',
              fontSize: '12px',
              fontWeight: 600,
              borderRadius: 'var(--radius-full)',
              border: '1px solid',
              borderColor: selectedCategory === cat ? 'var(--primary)' : 'var(--border-color)',
              backgroundColor: selectedCategory === cat ? 'var(--primary-light)' : 'var(--bg-surface)',
              color: selectedCategory === cat ? 'var(--primary)' : 'var(--text-secondary)',
              cursor: 'pointer'
            }}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Entries Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
        {filteredEntries.map((item, idx) => (
          <div
            key={idx}
            style={{
              padding: '18px 20px',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-surface)',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <h4 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                {item.term}
              </h4>
              <span className="badge badge-primary" style={{ fontSize: '10.5px' }}>
                {item.category}
              </span>
            </div>

            <div>
              <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                Plain-English Definition
              </div>
              <div style={{ fontSize: '13.5px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                {item.plainDef}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--primary)' }}>
                Formal Mathematical Definition
              </div>
              <div style={{ fontSize: '12.5px', color: 'var(--text-primary)', marginTop: '2px', backgroundColor: 'var(--bg-subtle)', padding: '8px 10px', borderRadius: 'var(--radius-sm)', fontFamily: 'var(--font-mono)' }}>
                {item.technicalDef}
              </div>
            </div>

            {item.formula && (
              <div className="formula-card" style={{ margin: '4px 0', padding: '8px 12px', fontSize: '12.5px' }}>
                {item.formula}
              </div>
            )}

            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              <strong>Concrete Example:</strong> <em>{item.example}</em>
            </div>

            <div style={{ fontSize: '11px', color: 'var(--text-dim)', borderTop: '1px solid var(--border-color)', paddingTop: '6px' }}>
              Appears in manuscript: {item.appearsIn}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
