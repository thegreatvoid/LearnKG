import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { Sidebar, NAVIGATION_GROUPS } from './components/Sidebar';
import { GlobalSearchModal } from './components/GlobalSearchModal';
import { InteractiveGraphExplorer } from './components/InteractiveGraphExplorer';
import { MetricCalculator } from './components/MetricCalculator';
import { ResultsDashboard } from './components/ResultsDashboard';
import { AblationExplorer } from './components/AblationExplorer';
import { SearchableGlossary } from './components/SearchableGlossary';
import { PresentationCards } from './components/PresentationCards';

// Views
import { HomeView } from './views/HomeView';
import { MotivationView } from './views/MotivationView';
import { RqsView } from './views/RqsView';
import { DatasetView } from './views/DatasetView';
import { PipelinesView } from './views/PipelinesView';
import { LlmView } from './views/LlmView';
import { PriorsView } from './views/PriorsView';
import { FundamentalsView } from './views/FundamentalsView';
import { ExtractionView } from './views/ExtractionView';
import { EvaluationView } from './views/EvaluationView';
import { DiagnosticsView } from './views/DiagnosticsView';
import { DiscussionView } from './views/DiscussionView';
import { RelatedWorkView } from './views/RelatedWorkView';
import { ImplementationView } from './views/ImplementationView';

export function App() {
  const [activeSection, setActiveSection] = useState<string>('home');
  const [theme, setTheme] = useState<'light' | 'dark'>('dark');
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  // Handle URL hash routing
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '');
      if (hash) {
        setActiveSection(hash);
      }
    };
    handleHashChange();
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const handleSelectSection = (id: string) => {
    setActiveSection(id);
    window.location.hash = id;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Find active label for breadcrumb
  let activeLabel = "Research Home";
  NAVIGATION_GROUPS.forEach(g => {
    g.sections.forEach(s => {
      if (s.id === activeSection) activeLabel = s.label;
    });
  });

  const renderActiveView = () => {
    switch (activeSection) {
      case 'home':
        return <HomeView onNavigate={handleSelectSection} />;
      case 'motivation':
        return <MotivationView />;
      case 'rqs':
        return <RqsView />;
      case 'dataset':
        return <DatasetView />;
      case 'pipelines':
        return <PipelinesView />;
      case 'llm':
        return <LlmView />;
      case 'priors':
        return <PriorsView />;
      case 'fundamentals':
        return <FundamentalsView />;
      case 'graph-explorer':
        return (
          <div>
            <div style={{ marginBottom: '28px' }}>
              <span className="badge badge-primary">Interactive Topology</span>
              <h1 style={{ marginTop: '8px' }}>Interactive Educational Knowledge Graph Explorer</h1>
              <p style={{ fontSize: '16px', color: 'var(--text-secondary)' }}>
                Filter by relation type, click any concept node to inspect definitions and prerequisite ancestor/descendant pathways, and zoom into chapter tiers.
              </p>
            </div>
            <InteractiveGraphExplorer />
          </div>
        );
      case 'extraction':
        return <ExtractionView />;
      case 'evaluation':
        return <EvaluationView />;
      case 'calculator':
        return (
          <div>
            <div style={{ marginBottom: '28px' }}>
              <span className="badge badge-primary">Hands-on Sandbox</span>
              <h1 style={{ marginTop: '8px' }}>Evaluation Metric & Transitive Closure Calculator</h1>
              <p style={{ fontSize: '16px', color: 'var(--text-secondary)' }}>
                Interactively simulate classification performance and observe how transitive closure alters precision, recall, and F1 reachability.
              </p>
            </div>
            <MetricCalculator />
          </div>
        );
      case 'results':
        return (
          <div>
            <div style={{ marginBottom: '28px' }}>
              <span className="badge badge-primary">Empirical Results</span>
              <h1 style={{ marginTop: '8px' }}>Benchmark Results Dashboard & Model Comparisons</h1>
              <p style={{ fontSize: '16px', color: 'var(--text-secondary)' }}>
                Controlled comparative evaluation on the AL-CPL common covered pair set (N=868), with 95% bootstrap confidence intervals and directional accuracy audits.
              </p>
            </div>
            <ResultsDashboard />
          </div>
        );
      case 'ablations':
        return (
          <div>
            <div style={{ marginBottom: '28px' }}>
              <span className="badge badge-primary">Component Ablation</span>
              <h1 style={{ marginTop: '8px' }}>Edge-Weighting & Feature Ablation Explorer</h1>
              <p style={{ fontSize: '16px', color: 'var(--text-secondary)' }}>
                Ablating individual components of the Analytic Hierarchy Process against sentence co-occurrence and document position gap with permutation test p-values.
              </p>
            </div>
            <AblationExplorer />
          </div>
        );
      case 'diagnostics':
        return <DiagnosticsView />;
      case 'discussion':
        return <DiscussionView />;
      case 'related-work':
        return <RelatedWorkView />;
      case 'implementation':
        return <ImplementationView />;
      case 'glossary':
        return (
          <div>
            <div style={{ marginBottom: '28px' }}>
              <span className="badge badge-primary">Technical Reference</span>
              <h1 style={{ marginTop: '8px' }}>Searchable Educational Knowledge Graph Glossary</h1>
              <p style={{ fontSize: '16px', color: 'var(--text-secondary)' }}>
                42 rigorous definitions with formal mathematical formulas, plain-English analogies, concrete geometry examples, and repository cross-references.
              </p>
            </div>
            <SearchableGlossary />
          </div>
        );
      case 'faq':
        return (
          <div>
            <div style={{ marginBottom: '28px' }}>
              <span className="badge badge-primary">Oral Defense & Conference Preparation</span>
              <h1 style={{ marginTop: '8px' }}>Oral Presentation FAQ & Defense Flashcards</h1>
              <p style={{ fontSize: '16px', color: 'var(--text-secondary)' }}>
                20 curated questions commonly asked by professors, conference reviewers, and examination committees. Toggle between the 30-second elevator pitch and the rigorous technical defense.
              </p>
            </div>
            <PresentationCards />
          </div>
        );
      default:
        return <HomeView onNavigate={handleSelectSection} />;
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <Sidebar
        currentSection={activeSection}
        onSelectSection={handleSelectSection}
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
      />

      {/* Main Content Area */}
      <div className="main-wrapper">
        <Navbar
          currentSection={activeLabel}
          theme={theme}
          onToggleTheme={() => setTheme(t => t === 'light' ? 'dark' : 'light')}
          onOpenSearch={() => setIsSearchOpen(true)}
          onToggleSidebar={() => setIsSidebarOpen(true)}
        />

        <main className="page-container">
          {renderActiveView()}
        </main>
      </div>

      {/* Cmd+K Global Search Modal */}
      <GlobalSearchModal
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        onNavigate={handleSelectSection}
      />
    </div>
  );
}

export default App;
