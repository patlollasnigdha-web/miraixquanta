import React from 'react';
import { useApp } from '../context/AppContext';
import { LineChart } from 'lucide-react';

export const StockDetailPage: React.FC = () => {
  const { selectedSymbol, setActivePage } = useApp();

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between pb-4 border-b border-[#1F2937] dark:border-[#1F2937] light:border-slate-200">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center font-mono font-bold text-blue-400">
            {selectedSymbol.slice(0, 3)}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold font-mono tracking-tight text-slate-100 dark:text-slate-100 light:text-slate-900">
                {selectedSymbol}
              </h1>
              <span className="text-xs px-2 py-0.5 rounded bg-slate-800 dark:bg-slate-800 light:bg-slate-100 text-slate-400 border border-slate-700">
                NSE
              </span>
            </div>
            <p className="text-xs text-slate-400">{selectedSymbol} India Limited</p>
          </div>
        </div>

        <button
          onClick={() => setActivePage('explorer')}
          className="px-3 py-1.5 rounded-lg border border-slate-700 hover:bg-slate-800 text-xs text-slate-300 transition"
        >
          ← Back to Explorer
        </button>
      </div>

      <div className="terminal-card p-8 text-center text-slate-400">
        <LineChart className="w-12 h-12 text-blue-400 mx-auto mb-3" />
        <p className="font-medium text-slate-200">Interactive Financial Chart</p>
        <p className="text-xs text-slate-500 mt-1">Lightweight Charts candlestick engine initializing for {selectedSymbol}...</p>
      </div>
    </div>
  );
};
