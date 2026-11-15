import React from 'react';
import { useApp } from '../context/AppContext';
import { Compass, Search } from 'lucide-react';

export const CompanyExplorerPage: React.FC = () => {
  const { availableSymbols, navigateToStock, setSearchOpen } = useApp();

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[#1F2937] dark:border-[#1F2937] light:border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <Compass className="w-5 h-5 text-blue-400" />
            <h1 className="text-xl font-bold font-mono tracking-tight text-slate-100 dark:text-slate-100 light:text-slate-900">
              Company Explorer
            </h1>
          </div>
          <p className="text-xs text-slate-400 dark:text-slate-400 light:text-slate-500 mt-1">
            Explore verified equity instruments from the actual dataset universe
          </p>
        </div>

        <button
          onClick={() => setSearchOpen(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium text-xs shadow-md transition"
        >
          <Search className="w-4 h-4" />
          <span>Quick Search (Ctrl+K)</span>
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {availableSymbols.map((sym) => (
          <div
            key={sym}
            onClick={() => navigateToStock(sym)}
            className="terminal-card p-4 hover:border-blue-500/50 cursor-pointer transition-all hover:scale-[1.01] group"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="font-mono font-bold text-base text-slate-100 dark:text-slate-100 light:text-slate-900 group-hover:text-blue-400 transition-colors">
                {sym}
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 dark:bg-slate-800 light:bg-slate-100 text-slate-400 border border-slate-700 dark:border-slate-700 light:border-slate-200">
                NSE
              </span>
            </div>
            <p className="text-xs text-slate-400 dark:text-slate-400 light:text-slate-500 line-clamp-1 mb-3">
              {sym} India Limited
            </p>
            <div className="pt-2 border-t border-[#1F2937] dark:border-[#1F2937] light:border-slate-100 flex items-center justify-between text-xs text-blue-400 font-medium">
              <span>View Financial Details</span>
              <span>→</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
