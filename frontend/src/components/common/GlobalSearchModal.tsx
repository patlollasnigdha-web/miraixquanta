import React, { useState, useEffect, useRef } from 'react';
import { useApp, CompanyMetadata } from '../../context/AppContext';
import { Search, X, TrendingUp, TrendingDown, Clock, ArrowRight } from 'lucide-react';

export const GlobalSearchModal: React.FC = () => {
  const {
    searchOpen,
    setSearchOpen,
    availableSymbols,
    companiesInventory,
    navigateToStock,
    recentlyViewed,
  } = useApp();

  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (searchOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [searchOpen]);

  if (!searchOpen) return null;

  // Filter candidates
  const cleanQ = query.trim().toUpperCase();
  const baseList: CompanyMetadata[] = companiesInventory.length > 0 
    ? companiesInventory 
    : availableSymbols.map((sym) => ({
        symbol: sym,
        name: `${sym} India Limited`,
        exchange: 'NSE',
        sector: 'Equities',
      }));

  const filtered = baseList.filter((c) => {
    if (!cleanQ) return true;
    return (
      c.symbol.toUpperCase().includes(cleanQ) ||
      (c.name && c.name.toUpperCase().includes(cleanQ)) ||
      (c.sector && c.sector.toUpperCase().includes(cleanQ))
    );
  }).slice(0, 8);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setSearchOpen(false);
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, filtered.length));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filtered.length) % Math.max(1, filtered.length));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filtered[selectedIndex]) {
        navigateToStock(filtered[selectedIndex].symbol);
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-16 sm:pt-24 px-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div
        className="w-full max-w-2xl bg-[#111827] dark:bg-[#111827] light:bg-white border border-[#1F2937] dark:border-[#1F2937] light:border-slate-200 rounded-2xl shadow-2xl overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="flex items-center px-4 py-3.5 border-b border-[#1F2937] dark:border-[#1F2937] light:border-slate-200">
          <Search className="w-5 h-5 text-blue-400 shrink-0 mr-3" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Search companies by ticker or name (e.g. TCS, RELIANCE, INFY)..."
            className="w-full bg-transparent text-slate-100 dark:text-slate-100 light:text-slate-900 placeholder-slate-500 text-sm focus:outline-none"
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              className="p-1 rounded text-slate-400 hover:text-slate-200 mr-2"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          <kbd className="hidden sm:inline-flex items-center px-2 py-0.5 text-[10px] font-mono text-slate-400 bg-slate-800 dark:bg-slate-800 light:bg-slate-100 rounded border border-slate-700 dark:border-slate-700 light:border-slate-300">
            ESC
          </kbd>
        </div>

        {/* Recently Viewed (if no query) */}
        {!query && recentlyViewed.length > 0 && (
          <div className="px-4 py-2.5 bg-slate-900/50 dark:bg-slate-900/50 light:bg-slate-50 border-b border-[#1F2937] dark:border-[#1F2937] light:border-slate-200 flex items-center gap-2 overflow-x-auto text-xs">
            <span className="flex items-center gap-1 text-[11px] text-slate-400 shrink-0 font-medium">
              <Clock className="w-3 h-3 text-slate-500" /> Recent:
            </span>
            {recentlyViewed.map((sym) => (
              <button
                key={sym}
                onClick={() => navigateToStock(sym)}
                className="px-2.5 py-1 rounded-md bg-slate-800 dark:bg-slate-800 light:bg-white text-slate-300 dark:text-slate-300 light:text-slate-700 hover:text-blue-400 border border-slate-700 dark:border-slate-700 light:border-slate-200 font-mono text-[11px] font-semibold transition"
              >
                {sym}
              </button>
            ))}
          </div>
        )}

        {/* Search Results List */}
        <div className="max-h-80 overflow-y-auto divide-y divide-[#1F2937] dark:divide-[#1F2937] light:divide-slate-100">
          {filtered.length === 0 ? (
            <div className="p-8 text-center text-slate-500 text-sm">
              No matching equities found in dataset for "{query}".
            </div>
          ) : (
            filtered.map((item, idx) => {
              const isSelected = idx === selectedIndex;
              const price = item.latest_price;
              const chg = item.change_pct;
              const isPos = chg !== undefined && chg >= 0;

              return (
                <div
                  key={item.symbol}
                  onClick={() => navigateToStock(item.symbol)}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`px-4 py-3 flex items-center justify-between cursor-pointer transition-colors ${
                    isSelected
                      ? 'bg-blue-600/15 text-blue-400'
                      : 'hover:bg-slate-800/40 dark:hover:bg-slate-800/40 light:hover:bg-slate-100'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-slate-800 dark:bg-slate-800 light:bg-slate-100 border border-slate-700 dark:border-slate-700 light:border-slate-200 flex items-center justify-center font-mono font-bold text-xs text-blue-400">
                      {item.symbol.slice(0, 3)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-sm text-slate-100 dark:text-slate-100 light:text-slate-900">
                          {item.symbol}
                        </span>
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 dark:bg-slate-800 light:bg-slate-100 text-slate-400 border border-slate-700 dark:border-slate-700 light:border-slate-200">
                          {item.exchange || 'NSE'}
                        </span>
                        {item.sector && (
                          <span className="text-[10px] text-slate-500 font-medium hidden sm:inline">
                            • {item.sector}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-400 line-clamp-1 max-w-sm">
                        {item.name || `${item.symbol} Limited`}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    {price !== undefined && (
                      <div className="text-right">
                        <div className="font-mono font-semibold text-sm text-slate-100 dark:text-slate-100 light:text-slate-900">
                          ₹{price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </div>
                        {chg !== undefined && (
                          <div
                            className={`flex items-center justify-end text-[11px] font-mono font-medium ${
                              isPos ? 'text-emerald-400' : 'text-rose-400'
                            }`}
                          >
                            {isPos ? (
                              <TrendingUp className="w-3 h-3 mr-0.5" />
                            ) : (
                              <TrendingDown className="w-3 h-3 mr-0.5" />
                            )}
                            {isPos ? '+' : ''}
                            {chg.toFixed(2)}%
                          </div>
                        )}
                      </div>
                    )}
                    <ArrowRight className={`w-4 h-4 ${isSelected ? 'text-blue-400' : 'text-slate-600'}`} />
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="px-4 py-2.5 bg-slate-900/70 dark:bg-slate-900/70 light:bg-slate-50 border-t border-[#1F2937] dark:border-[#1F2937] light:border-slate-200 flex items-center justify-between text-[11px] text-slate-500 font-mono">
          <div className="flex items-center gap-3">
            <span>↑↓ Navigate</span>
            <span>↵ Select</span>
            <span>ESC Close</span>
          </div>
          <span className="text-slate-400 font-medium">MIRAI Data Verified</span>
        </div>
      </div>
      <div className="fixed inset-0 -z-10" onClick={() => setSearchOpen(false)} />
    </div>
  );
};
