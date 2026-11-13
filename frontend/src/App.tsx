import React, { useState } from 'react';
import { AppProvider } from './context/AppContext';
import { Navbar } from './components/common/Navbar';
import { Sidebar, PageId } from './components/common/Sidebar';
import { OverviewPage } from './pages/OverviewPage';
import { StockIntelligencePage } from './pages/StockIntelligencePage';
import { DecisionExplorerPage } from './pages/DecisionExplorerPage';
import { AssistantPage } from './pages/AssistantPage';
import { PortfolioPage } from './pages/PortfolioPage';
import { RiskManagementPage } from './pages/RiskManagementPage';
import { StrategyBacktestPage } from './pages/StrategyBacktestPage';
import { PaperTradingPage } from './pages/PaperTradingPage';
import { SystemMonitoringPage } from './pages/SystemMonitoringPage';
import { SettingsPage } from './pages/SettingsPage';

export const AppContent: React.FC = () => {
  const [activePage, setActivePage] = useState<PageId>('overview');

  return (
    <div className="min-h-screen bg-[#0B0F19] text-slate-100 flex flex-col font-sans">
      <Navbar />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar activePage={activePage} setActivePage={setActivePage} />
        <main className="flex-1 overflow-y-auto p-6 bg-[#0B0F19]">
          <div className="max-w-7xl mx-auto">
            {activePage === 'overview' && <OverviewPage onNavigate={(p) => setActivePage(p as PageId)} />}
            {activePage === 'stocks' && <StockIntelligencePage />}
            {activePage === 'decision' && <DecisionExplorerPage />}
            {activePage === 'assistant' && <AssistantPage />}
            {activePage === 'portfolio' && <PortfolioPage />}
            {activePage === 'risk' && <RiskManagementPage />}
            {activePage === 'backtest' && <StrategyBacktestPage />}
            {activePage === 'papertrading' && <PaperTradingPage />}
            {activePage === 'monitoring' && <SystemMonitoringPage />}
            {activePage === 'settings' && <SettingsPage />}
          </div>
        </main>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
};

export default App;
