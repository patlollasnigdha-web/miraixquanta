import React from 'react';
import {
  LayoutDashboard,
  Compass,
  LineChart,
  Star,
  TrendingUp,
  BrainCircuit,
  MessageSquareCode,
  PieChart,
  ShieldAlert,
  History,
  FileSpreadsheet,
  Activity,
  Settings,
} from 'lucide-react';
import { PageId, useApp } from '../../context/AppContext';

export type { PageId };

interface SidebarProps {
  activePage: PageId;
  setActivePage: (page: PageId) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activePage, setActivePage }) => {
  const { selectedSymbol } = useApp();

  const sections = [
    {
      title: 'Market & Equities',
      items: [
        { id: 'overview', label: 'Overview', icon: LayoutDashboard },
        { id: 'explorer', label: 'Company Explorer', icon: Compass, badge: 'All' },
        { id: 'stock_detail', label: 'Stock Details', icon: LineChart, subtitle: selectedSymbol },
        { id: 'watchlist', label: 'Watchlists', icon: Star },
      ],
    },
    {
      title: 'Quantitative Intelligence',
      items: [
        { id: 'stocks', label: 'Stock Intelligence', icon: TrendingUp },
        { id: 'decision', label: 'Decision Explorer', icon: BrainCircuit, highlight: true },
        { id: 'assistant', label: 'AI Assistant', icon: MessageSquareCode, badge: 'Copilot' },
      ],
    },
    {
      title: 'Execution & Simulation',
      items: [
        { id: 'portfolio', label: 'Portfolio', icon: PieChart },
        { id: 'papertrading', label: 'Paper Trading', icon: FileSpreadsheet },
        { id: 'backtest', label: 'Strategy & Backtest', icon: History },
        { id: 'risk', label: 'Risk Controls', icon: ShieldAlert },
      ],
    },
    {
      title: 'System & Admin',
      items: [
        { id: 'monitoring', label: 'System Health', icon: Activity },
        { id: 'settings', label: 'Settings', icon: Settings },
      ],
    },
  ];

  return (
    <aside className="hidden md:flex w-64 border-r border-[#1F2937] dark:border-[#1F2937] light:border-slate-200 bg-[#111827] dark:bg-[#111827] light:bg-white flex-col justify-between shrink-0 h-[calc(100vh-3.5rem)] sticky top-14 overflow-y-auto transition-colors">
      <div className="py-4 px-3 space-y-4">
        {sections.map((section) => (
          <div key={section.title} className="space-y-1">
            <div className="px-3 pb-1.5 text-[10px] font-mono uppercase tracking-wider text-slate-500 font-bold">
              {section.title}
            </div>
            {section.items.map((item: any) => {
              const Icon = item.icon;
              const isActive = activePage === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActivePage(item.id as PageId)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-blue-600/15 text-blue-400 border border-blue-500/30 font-semibold'
                      : 'text-slate-400 dark:text-slate-400 light:text-slate-600 hover:text-slate-200 dark:hover:text-slate-200 light:hover:text-slate-900 hover:bg-slate-800/60 dark:hover:bg-slate-800/60 light:hover:bg-slate-100 border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-blue-400' : 'text-slate-400'}`} />
                    <span className="truncate">{item.label}</span>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0 ml-2">
                    {item.subtitle && (
                      <span className="text-[10px] font-mono font-bold text-slate-400 dark:text-slate-400 light:text-slate-600 bg-slate-800 dark:bg-slate-800 light:bg-slate-100 px-1.5 py-0.5 rounded border border-slate-700 dark:border-slate-700 light:border-slate-200">
                        {item.subtitle}
                      </span>
                    )}
                    {item.badge && (
                      <span className="text-[9px] font-mono uppercase tracking-wider bg-blue-950 dark:bg-blue-950 light:bg-blue-50 text-blue-400 border border-blue-800/60 dark:border-blue-800/60 light:border-blue-200 px-1.5 py-0.5 rounded">
                        {item.badge}
                      </span>
                    )}
                    {item.highlight && (
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        ))}
      </div>

      {/* Bottom Terminal Footnote */}
      <div className="p-3.5 border-t border-[#1F2937] dark:border-[#1F2937] light:border-slate-200 text-[11px] font-mono text-slate-400 dark:text-slate-400 light:text-slate-500 bg-slate-900/40 dark:bg-slate-900/40 light:bg-slate-50/50">
        <div className="flex items-center justify-between">
          <span>Engine Build</span>
          <span className="text-slate-300 dark:text-slate-300 light:text-slate-700 font-semibold">v1.2.0-PRO</span>
        </div>
        <div className="text-[10px] text-slate-500 mt-1 flex items-center justify-between">
          <span>MIRAI Stock Website</span>
          <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" title="Ready" />
        </div>
      </div>
    </aside>
  );
};
