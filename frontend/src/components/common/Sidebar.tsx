import React from 'react';
import {
  LayoutDashboard,
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

export type PageId =
  | 'overview'
  | 'stocks'
  | 'decision'
  | 'assistant'
  | 'portfolio'
  | 'risk'
  | 'backtest'
  | 'papertrading'
  | 'monitoring'
  | 'settings';

interface SidebarProps {
  activePage: PageId;
  setActivePage: (page: PageId) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activePage, setActivePage }) => {
  const navItems = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'stocks', label: 'Stock Intelligence', icon: TrendingUp },
    { id: 'decision', label: 'Decision Explorer', icon: BrainCircuit, highlight: true },
    { id: 'assistant', label: 'AI Assistant', icon: MessageSquareCode },
    { id: 'portfolio', label: 'Portfolio', icon: PieChart },
    { id: 'risk', label: 'Risk Controls', icon: ShieldAlert },
    { id: 'backtest', label: 'Strategy & Backtest', icon: History },
    { id: 'papertrading', label: 'Paper Trading', icon: FileSpreadsheet },
    { id: 'monitoring', label: 'System Health', icon: Activity },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="w-60 border-r border-[#1F2937] bg-[#111827] flex flex-col justify-between shrink-0 h-[calc(100vh-3.5rem)] sticky top-14">
      <div className="py-4 px-3 space-y-1">
        <div className="px-3 pb-2 text-[10px] font-mono uppercase tracking-wider text-slate-500 font-semibold">
          Terminal Modules
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activePage === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActivePage(item.id as PageId)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-all ${
                isActive
                  ? 'bg-blue-600/15 text-blue-400 border border-blue-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-blue-400' : 'text-slate-400'}`} />
              <span>{item.label}</span>
              {item.highlight && (
                <span className="ml-auto w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
              )}
            </button>
          );
        })}
      </div>

      {/* Bottom Terminal Footnote */}
      <div className="p-4 border-t border-[#1F2937] text-[11px] font-mono text-slate-400">
        <div className="flex items-center justify-between">
          <span>Engine Build</span>
          <span className="text-slate-300">v1.0.0</span>
        </div>
        <div className="text-[10px] text-slate-500 mt-1">
          MIRAI Quant Framework
        </div>
      </div>
    </aside>
  );
};
