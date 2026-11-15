import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import {
  LayoutDashboard,
  Compass,
  LineChart,
  Star,
  MessageSquareCode,
  Menu,
  X,
  PieChart,
  ShieldAlert,
  History,
  FileSpreadsheet,
  Activity,
  Settings,
  BrainCircuit,
  TrendingUp,
} from 'lucide-react';
import { PageId } from '../../context/AppContext';

export const MobileNav: React.FC = () => {
  const { activePage, setActivePage } = useApp();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const mainItems: { id: PageId; label: string; icon: React.FC<{ className?: string }> }[] = [
    { id: 'overview', label: 'Markets', icon: LayoutDashboard },
    { id: 'explorer', label: 'Explore', icon: Compass },
    { id: 'stock_detail', label: 'Stock', icon: LineChart },
    { id: 'watchlist', label: 'Watchlist', icon: Star },
    { id: 'assistant', label: 'Copilot', icon: MessageSquareCode },
  ];

  const drawerItems: { id: PageId; label: string; icon: React.FC<{ className?: string }> }[] = [
    { id: 'stocks', label: 'Stock Intelligence (M05)', icon: TrendingUp },
    { id: 'decision', label: 'Decision Explorer (M09)', icon: BrainCircuit },
    { id: 'portfolio', label: 'Portfolio (M10)', icon: PieChart },
    { id: 'papertrading', label: 'Paper Trading (M14)', icon: FileSpreadsheet },
    { id: 'backtest', label: 'Strategy & Backtest (M13)', icon: History },
    { id: 'risk', label: 'Risk Controls (M11)', icon: ShieldAlert },
    { id: 'monitoring', label: 'System Health (M18)', icon: Activity },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <>
      {/* Mobile Drawer Menu */}
      {drawerOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex flex-col justify-end bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="w-full bg-[#111827] dark:bg-[#111827] light:bg-white border-t border-[#1F2937] dark:border-[#1F2937] light:border-slate-200 rounded-t-2xl p-5 max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-[#1F2937] dark:border-[#1F2937] light:border-slate-200 mb-4">
              <span className="font-mono font-bold text-sm text-slate-100 dark:text-slate-100 light:text-slate-900">
                All MIRAI Modules
              </span>
              <button
                onClick={() => setDrawerOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-2">
              {drawerItems.map((item) => {
                const Icon = item.icon;
                const isActive = activePage === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      setActivePage(item.id);
                      setDrawerOpen(false);
                    }}
                    className={`flex items-center gap-2.5 p-3 rounded-xl text-left font-medium text-xs transition ${
                      isActive
                        ? 'bg-blue-600/15 text-blue-400 border border-blue-500/30'
                        : 'bg-slate-800/40 dark:bg-slate-800/40 light:bg-slate-50 text-slate-300 dark:text-slate-300 light:text-slate-700 hover:bg-slate-800 border border-transparent'
                    }`}
                  >
                    <Icon className="w-4 h-4 shrink-0 text-blue-400" />
                    <span className="truncate">{item.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
          <div className="flex-1" onClick={() => setDrawerOpen(false)} />
        </div>
      )}

      {/* Fixed Bottom Touch Navigation Bar */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 h-16 bg-[#111827]/95 dark:bg-[#111827]/95 light:bg-white/95 backdrop-blur-md border-t border-[#1F2937] dark:border-[#1F2937] light:border-slate-200 flex items-center justify-around px-2">
        {mainItems.map((item) => {
          const Icon = item.icon;
          const isActive = activePage === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActivePage(item.id)}
              className={`flex flex-col items-center justify-center flex-1 py-1 transition-all ${
                isActive
                  ? 'text-blue-400 font-semibold'
                  : 'text-slate-400 dark:text-slate-400 light:text-slate-500 hover:text-slate-200'
              }`}
            >
              <Icon className={`w-5 h-5 mb-0.5 ${isActive ? 'text-blue-400 scale-110' : ''}`} />
              <span className="text-[10px] tracking-tight">{item.label}</span>
            </button>
          );
        })}

        <button
          onClick={() => setDrawerOpen(true)}
          className={`flex flex-col items-center justify-center flex-1 py-1 text-slate-400 dark:text-slate-400 light:text-slate-500 hover:text-slate-200 transition-all ${
            drawerOpen ? 'text-blue-400' : ''
          }`}
        >
          <Menu className="w-5 h-5 mb-0.5" />
          <span className="text-[10px] tracking-tight">More</span>
        </button>
      </nav>
    </>
  );
};
