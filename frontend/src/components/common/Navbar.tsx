import React from 'react';
import { useApp } from '../../context/AppContext';
import {
  RefreshCw,
  Cpu,
  Server,
  Layers,
  Search,
  Sun,
  Moon,
  User,
  Star,
} from 'lucide-react';
import { StatusBadge } from './StatusBadge';

export const Navbar: React.FC = () => {
  const {
    selectedPipeline,
    setSelectedPipeline,
    backendStatus,
    ollamaStatus,
    lastUpdated,
    triggerRefresh,
    theme,
    toggleTheme,
    setSearchOpen,
    setActivePage,
  } = useApp();

  return (
    <header className="h-14 border-b border-[#1F2937] dark:border-[#1F2937] light:border-slate-200 bg-[#111827]/90 dark:bg-[#111827]/90 light:bg-white/90 backdrop-blur sticky top-0 z-40 px-4 sm:px-6 flex items-center justify-between transition-colors">
      {/* Brand & Platform Identity */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setActivePage('overview')}
          className="flex items-center gap-2.5 text-left focus:outline-none group"
        >
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-blue-600 via-indigo-600 to-cyan-500 flex items-center justify-center font-black text-white shadow-lg shadow-blue-500/20 font-mono text-sm tracking-wider group-hover:scale-105 transition-transform">
            M
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-bold tracking-wider text-slate-100 dark:text-slate-100 light:text-slate-900 font-mono text-sm">
                MIRAI
              </span>
              <span className="text-[10px] bg-blue-950/80 dark:bg-blue-950/80 light:bg-blue-50 text-blue-400 dark:text-blue-400 light:text-blue-600 border border-blue-800 dark:border-blue-800 light:border-blue-200 px-1.5 py-0.2 rounded font-mono font-semibold">
                QUANT X
              </span>
            </div>
            <p className="text-[10px] text-slate-400 dark:text-slate-400 light:text-slate-500 hidden xl:block font-medium">
              Institutional AI Quantitative Trading & Stock Platform
            </p>
          </div>
        </button>
      </div>

      {/* Center: Global Search Trigger & Pipeline */}
      <div className="flex items-center gap-2 sm:gap-3 flex-1 max-w-xl mx-2 sm:mx-6">
        {/* Global Stock Search Pill */}
        <button
          onClick={() => setSearchOpen(true)}
          className="flex-1 flex items-center justify-between px-3 py-1.5 rounded-lg bg-[#0B0F19] dark:bg-[#0B0F19] light:bg-slate-100 border border-[#1F2937] dark:border-[#1F2937] light:border-slate-200 text-slate-400 hover:text-slate-200 dark:hover:text-slate-200 light:hover:text-slate-800 hover:border-slate-700 transition text-xs font-sans group shadow-inner"
        >
          <div className="flex items-center gap-2">
            <Search className="w-3.5 h-3.5 text-blue-400 group-hover:scale-110 transition-transform" />
            <span className="hidden sm:inline">Search stocks, symbols (e.g. TCS, RELIANCE)...</span>
            <span className="sm:hidden">Search stocks...</span>
          </div>
          <kbd className="hidden md:inline-flex items-center px-1.5 py-0.5 text-[10px] font-mono text-slate-500 bg-slate-800 dark:bg-slate-800 light:bg-white rounded border border-slate-700 dark:border-slate-700 light:border-slate-300">
            Ctrl+K
          </kbd>
        </button>

        {/* Pipeline Selector */}
        <div className="hidden lg:flex items-center gap-1.5 bg-[#0B0F19] dark:bg-[#0B0F19] light:bg-slate-100 border border-[#1F2937] dark:border-[#1F2937] light:border-slate-200 rounded-lg px-2.5 py-1 text-xs shrink-0">
          <Layers className="w-3.5 h-3.5 text-blue-400" />
          <select
            value={selectedPipeline}
            onChange={(e) => setSelectedPipeline(e.target.value)}
            className="bg-transparent text-slate-200 dark:text-slate-200 light:text-slate-800 font-mono text-xs focus:outline-none cursor-pointer"
          >
            <option value="pipeline_b_nifty" className="bg-slate-900 text-slate-100">Pipeline B (NIFTY 50)</option>
            <option value="pipeline_a_fi2010" className="bg-slate-900 text-slate-100">Pipeline A (FI-2010 LOB)</option>
          </select>
        </div>
      </div>

      {/* Right Controls: Theme, Connectivity, Watchlist, Profile */}
      <div className="flex items-center gap-2 sm:gap-3 shrink-0">
        {/* Watchlist Quick Button */}
        <button
          onClick={() => setActivePage('watchlist')}
          title="Open Watchlists"
          className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800/60 dark:bg-slate-800/60 light:bg-slate-100 hover:bg-slate-700 dark:hover:bg-slate-700 light:hover:bg-slate-200 text-slate-300 dark:text-slate-300 light:text-slate-700 border border-slate-700/60 dark:border-slate-700/60 light:border-slate-200 transition text-xs font-medium"
        >
          <Star className="w-3.5 h-3.5 text-amber-400" />
          <span className="hidden md:inline">Watchlist</span>
        </button>

        {/* Backend Connectivity */}
        <div className="hidden lg:flex items-center gap-1.5 text-xs">
          <Server className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-400 text-[11px] hidden xl:inline">API:</span>
          <StatusBadge status={backendStatus} type="health" />
        </div>

        {/* Ollama Status */}
        <div className="hidden xl:flex items-center gap-1.5 text-xs">
          <Cpu className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-400 text-[11px]">Ollama:</span>
          <StatusBadge status={ollamaStatus} type="health" />
        </div>

        {/* Theme Toggle (Dark / Light) */}
        <button
          onClick={toggleTheme}
          title={theme === 'dark' ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
          className="p-1.5 rounded-lg bg-slate-800/80 dark:bg-slate-800/80 light:bg-slate-100 hover:bg-slate-700 dark:hover:bg-slate-700 light:hover:bg-slate-200 text-slate-300 dark:text-slate-300 light:text-slate-700 border border-slate-700 dark:border-slate-700 light:border-slate-300 transition"
        >
          {theme === 'dark' ? (
            <Sun className="w-4 h-4 text-amber-400" />
          ) : (
            <Moon className="w-4 h-4 text-indigo-500" />
          )}
        </button>

        {/* User Account / Profile Button */}
        <button
          onClick={() => setActivePage('profile')}
          title="User Account"
          className="p-1.5 rounded-lg bg-slate-800/80 dark:bg-slate-800/80 light:bg-slate-100 hover:bg-slate-700 dark:hover:bg-slate-700 light:hover:bg-slate-200 text-slate-300 dark:text-slate-300 light:text-slate-700 border border-slate-700 dark:border-slate-700 light:border-slate-300 transition flex items-center gap-1.5"
        >
          <User className="w-4 h-4 text-blue-400" />
          <span className="hidden md:inline text-xs font-medium">Account</span>
        </button>

        {/* Data Refresh */}
        <button
          onClick={triggerRefresh}
          title={`Refresh Data (Last: ${lastUpdated.toLocaleTimeString()})`}
          className="p-1.5 rounded-lg bg-slate-800/80 dark:bg-slate-800/80 light:bg-slate-100 hover:bg-slate-700 dark:hover:bg-slate-700 light:hover:bg-slate-200 text-slate-300 dark:text-slate-300 light:text-slate-700 border border-slate-700 dark:border-slate-700 light:border-slate-300 transition"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
