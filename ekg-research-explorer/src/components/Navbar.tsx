import React from 'react';
import { Search, Moon, Sun, Menu, BookOpen, ExternalLink, ShieldCheck } from 'lucide-react';
import { PROJECT_META } from '../data/researchData';

interface NavbarProps {
  currentSection: string;
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
  onOpenSearch: () => void;
  onToggleSidebar: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentSection,
  theme,
  onToggleTheme,
  onOpenSearch,
  onToggleSidebar
}) => {
  return (
    <header className="navbar">
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <button
          className="btn-icon mobile-menu-btn"
          onClick={onToggleSidebar}
          aria-label="Toggle Navigation Menu"
          style={{ display: 'none' }}
        >
          <Menu size={18} />
        </button>

        <div className="breadcrumb">
          <span>LearnKG</span>
          <span>/</span>
          <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
            {currentSection}
          </span>
        </div>
      </div>

      <button className="nav-search-btn" onClick={onOpenSearch}>
        <Search size={15} />
        <span>Search metrics, glossary, algorithms...</span>
        <span className="kbd-shortcut">⌘K</span>
      </button>

      <div className="navbar-actions">
        <div 
          className="badge badge-success"
          title="All experimental metrics are 100% verified from frozen repository JSON outputs"
          style={{ cursor: 'help' }}
        >
          <ShieldCheck size={13} />
          <span>Verified Artifacts</span>
        </div>

        <button
          className="btn-icon"
          onClick={onToggleTheme}
          title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} Mode`}
        >
          {theme === 'light' ? <Moon size={17} /> : <Sun size={17} />}
        </button>
      </div>
    </header>
  );
};
