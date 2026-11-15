import React from 'react';
import { useApp } from '../context/AppContext';
import { Star, Plus } from 'lucide-react';

export const WatchlistPage: React.FC = () => {
  const { availableSymbols, navigateToStock } = useApp();

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between pb-4 border-b border-[#1F2937] dark:border-[#1F2937] light:border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <Star className="w-5 h-5 text-amber-400" />
            <h1 className="text-xl font-bold font-mono tracking-tight text-slate-100 dark:text-slate-100 light:text-slate-900">
              Watchlists
            </h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">Track and organize your key stock picks with real-time indicators</p>
        </div>

        <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium shadow-md transition">
          <Plus className="w-4 h-4" />
          <span>New Watchlist</span>
        </button>
      </div>

      <div className="terminal-card overflow-hidden">
        <div className="p-4 border-b border-[#1F2937] flex items-center justify-between">
          <span className="font-semibold text-sm text-slate-200">Default Portfolio Watchlist</span>
          <span className="text-xs text-slate-400">{availableSymbols.length} instruments</span>
        </div>
        <div className="divide-y divide-[#1F2937]">
          {availableSymbols.map((sym) => (
            <div
              key={sym}
              onClick={() => navigateToStock(sym)}
              className="p-4 flex items-center justify-between hover:bg-slate-800/40 cursor-pointer transition"
            >
              <div className="flex items-center gap-3">
                <Star className="w-4 h-4 text-amber-400 fill-amber-400" />
                <div>
                  <div className="font-mono font-bold text-sm text-slate-100">{sym}</div>
                  <div className="text-xs text-slate-400">{sym} India Limited</div>
                </div>
              </div>
              <div className="text-right">
                <span className="text-xs text-blue-400 font-medium">View Stock Details →</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
