import React, { useState } from 'react';
import { Routes, Route, useInRouterContext } from 'react-router-dom';
import Shell from './components/Shell';
import { RequireAuth, GuestOnly } from './components/RouteGuards';
import {
  Dashboard,
  Markets,
  Regimes,
  Strategies,
  Backtest,
  Assistant,
  Library,
  Settings,
} from './pages/Pages';
import Portfolio from './pages/PortfolioPage';
import {
  LoginPage,
  SignupPage,
  ProfilePage,
  WatchlistPage,
  ForgotPasswordPage,
  ResetPasswordPage,
} from './pages/AuthPages';
import { PredictionsPage } from './pages/PredictionsPage';
import {
  LivePaperTradingPage,
  RiskManagementDashboard,
  TradingPerformanceDashboard,
  LatencyMonitoringDashboard,
} from './pages/TradingPages';

// Legacy quant workspace components for App.test.tsx backward compatibility
import { AppProvider } from './context/AppContext';
import { Navbar } from './components/common/Navbar';
import { Sidebar, PageId } from './components/common/Sidebar';
import { OverviewPage } from './pages/OverviewPage';
import { StockIntelligencePage } from './pages/StockIntelligencePage';
import { DecisionExplorerPage } from './pages/DecisionExplorerPage';
import { AssistantPage } from './pages/AssistantPage';
import { PortfolioPage as QuantPortfolioPage } from './pages/QuantPortfolioPage';
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
            {activePage === 'portfolio' && <QuantPortfolioPage />}
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
  const inRouter = useInRouterContext();

  if (!inRouter) {
    return (
      <AppProvider>
        <AppContent />
      </AppProvider>
    );
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={
          <GuestOnly>
            <LoginPage />
          </GuestOnly>
        }
      />
      <Route
        path="/signup"
        element={
          <GuestOnly>
            <SignupPage />
          </GuestOnly>
        }
      />
      <Route
        path="/forgot-password"
        element={
          <GuestOnly>
            <ForgotPasswordPage />
          </GuestOnly>
        }
      />
      <Route
        path="/reset-password"
        element={
          <GuestOnly>
            <ResetPasswordPage />
          </GuestOnly>
        }
      />
      <Route
        element={
          <RequireAuth>
            <Shell />
          </RequireAuth>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route path="/predictions" element={<PredictionsPage />} />
        <Route path="/paper-trading" element={<LivePaperTradingPage />} />
        <Route path="/risk" element={<RiskManagementDashboard />} />
        <Route path="/performance" element={<TradingPerformanceDashboard />} />
        <Route path="/monitoring" element={<LatencyMonitoringDashboard />} />
        <Route path="/markets" element={<Markets />} />
        <Route path="/regimes" element={<Regimes />} />
        <Route path="/discovery" element={<Strategies />} />
        <Route path="/library" element={<Library />} />
        <Route path="/backtest" element={<Backtest />} />
        <Route path="/portfolio" element={<Portfolio />} />
        <Route path="/assistant" element={<Assistant />} />
        <Route path="/watchlist" element={<WatchlistPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  );
};

export default App;
