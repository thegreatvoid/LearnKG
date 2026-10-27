import React from 'react';
import {
  Home,
  Lightbulb,
  HelpCircle,
  Database,
  GitMerge,
  Cpu,
  Compass,
  Network,
  Share2,
  Filter,
  GraduationCap,
  Calculator,
  BarChart3,
  Sliders,
  AlertTriangle,
  Scale,
  BookOpen,
  FolderGit2,
  BookA,
  MessageSquare
} from 'lucide-react';

export interface NavSection {
  id: string;
  label: string;
  icon: React.ReactNode;
  badge?: string;
}

interface NavGroup {
  title: string;
  sections: NavSection[];
}

interface SidebarProps {
  currentSection: string;
  onSelectSection: (id: string) => void;
  isOpen: boolean;
  onClose: () => void;
}

export const NAVIGATION_GROUPS: NavGroup[] = [
  {
    title: "1. Research Overview",
    sections: [
      { id: 'home', label: 'Research Home', icon: <Home size={16} /> },
      { id: 'motivation', label: 'Problem & Motivation', icon: <Lightbulb size={16} /> },
      { id: 'rqs', label: 'Research Questions (RQs)', icon: <HelpCircle size={16} />, badge: '5 RQs' }
    ]
  },
  {
    title: "2. Corpus & Pipelines",
    sections: [
      { id: 'dataset', label: 'Dataset & Benchmark', icon: <Database size={16} /> },
      { id: 'pipelines', label: 'Pipeline Architecture', icon: <GitMerge size={16} /> },
      { id: 'llm', label: 'Local LLM Methodology', icon: <Cpu size={16} /> },
      { id: 'priors', label: 'Structural Priors & Hybrid', icon: <Compass size={16} /> }
    ]
  },
  {
    title: "3. EKG & Graph Theory",
    sections: [
      { id: 'fundamentals', label: 'EKG & 5 Relation Types', icon: <Network size={16} /> },
      { id: 'graph-explorer', label: 'Interactive Graph Explorer', icon: <Share2 size={16} />, badge: 'Live' },
      { id: 'extraction', label: 'Extraction & Bottlenecks', icon: <Filter size={16} /> }
    ]
  },
  {
    title: "4. Empirical Evaluation",
    sections: [
      { id: 'evaluation', label: 'Evaluation Tutorial', icon: <GraduationCap size={16} /> },
      { id: 'calculator', label: 'Metric Calculator', icon: <Calculator size={16} />, badge: 'Tool' }
    ]
  },
  {
    title: "5. Experimental Results",
    sections: [
      { id: 'results', label: 'Benchmark Results Dashboard', icon: <BarChart3 size={16} /> },
      { id: 'ablations', label: 'Ablation Study Explorer', icon: <Sliders size={16} /> },
      { id: 'diagnostics', label: 'Diagnostics & Error Analysis', icon: <AlertTriangle size={16} /> }
    ]
  },
  {
    title: "6. Scientific Discussion",
    sections: [
      { id: 'discussion', label: 'Interpretation & Validity', icon: <Scale size={16} /> },
      { id: 'related-work', label: 'Related Work & Positioning', icon: <BookOpen size={16} /> },
      { id: 'implementation', label: 'Code Map & Reproducibility', icon: <FolderGit2 size={16} /> }
    ]
  },
  {
    title: "7. Reference & Defense",
    sections: [
      { id: 'glossary', label: 'Searchable Glossary (42 Terms)', icon: <BookA size={16} /> },
      { id: 'faq', label: 'Oral Presentation FAQ (20 Qs)', icon: <MessageSquare size={16} />, badge: 'Defense' }
    ]
  }
];

export const Sidebar: React.FC<SidebarProps> = ({
  currentSection,
  onSelectSection,
  isOpen,
  onClose
}) => {
  return (
    <>
      {isOpen && (
        <div 
          className="sidebar-backdrop"
          onClick={onClose}
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            zIndex: 35
          }}
        />
      )}

      <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <div className="sidebar-logo">KG</div>
          <div>
            <div className="sidebar-title">LearnKG Explorer</div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Research Hub & Documentation</div>
          </div>
          <span className="sidebar-badge" style={{ marginLeft: 'auto' }}>v2.0</span>
        </div>

        <nav className="sidebar-nav">
          {NAVIGATION_GROUPS.map((group, groupIndex) => (
            <div key={groupIndex} className="nav-group">
              <div className="nav-group-title">{group.title}</div>
              <ul className="nav-items">
                {group.sections.map((section) => {
                  const isActive = currentSection === section.id;
                  return (
                    <li key={section.id}>
                      <button
                        className={`nav-link ${isActive ? 'active' : ''}`}
                        onClick={() => {
                          onSelectSection(section.id);
                          onClose();
                        }}
                        style={{ width: '100%', textAlign: 'left', background: 'none' }}
                      >
                        <span className="icon">{section.icon}</span>
                        <span style={{ flex: 1 }}>{section.label}</span>
                        {section.badge && (
                          <span 
                            className="badge badge-primary" 
                            style={{ fontSize: '10px', padding: '1px 6px' }}
                          >
                            {section.badge}
                          </span>
                        )}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>
      </aside>
    </>
  );
};
