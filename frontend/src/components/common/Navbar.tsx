import React from 'react';
import { useApp } from '../../context/AppContext';
import { RefreshCw, Cpu, Server, Layers } from 'lucide-react';
import { StatusBadge } from './StatusBadge';

export const Navbar: React.FC = () => {
  const {
    selectedPipeline,
    setSelectedPipeline,
    backendStatus,
    ollamaStatus,
    lastUpdated,
    triggerRefresh,
  } = useApp();

  return (
    <header className="h-14 border-b border-[#1F2937] bg-[#111827]/80 backdrop-blur sticky top-0 z-40 px-6 flex items-center justify-between">
      {/* Brand & Platform Identity */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center font-black text-white shadow-lg shadow-blue-500/20 font-mono">
          M
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold tracking-wider text-slate-100 font-mono text-sm">MIRAI</span>
            <span className="text-[10px] bg-blue-950 text-blue-400 border border-blue-800 px-1.5 py-0.2 rounded font-mono">
              QUANT X
            </span>
          </div>
          <p className="text-[10px] text-slate-400 hidden sm:block">
            Adaptive AI Quantitative Trading & Microstructure Framework
          </p>
        </div>
      </div>

      {/* Center: Pipeline & Mode Indicators */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 bg-[#0B0F19] border border-[#1F2937] rounded-md px-2.5 py-1 text-xs">
          <Layers className="w-3.5 h-3.5 text-blue-400" />
          <span className="text-slate-400 text-[11px]">Pipeline:</span>
          <select
            value={selectedPipeline}
            onChange={(e) => setSelectedPipeline(e.target.value)}
            className="bg-transparent text-slate-200 font-mono text-xs focus:outline-none cursor-pointer"
          >
            <option value="pipeline_b_nifty" className="bg-slate-900">Pipeline B (NIFTY 50 Equities)</option>
            <option value="pipeline_a_fi2010" className="bg-slate-900">Pipeline A (FI-2010 Microstructure)</option>
          </select>
        </div>

        <div className="hidden lg:flex items-center gap-1.5 text-[11px] font-mono text-slate-400 bg-slate-900/50 px-2 py-1 rounded border border-slate-800">
          <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping" />
          <span>VIRTUAL SIMULATION ONLY</span>
        </div>
      </div>

      {/* Right Controls: Connectivity & Health Telemetry */}
      <div className="flex items-center gap-3">
        {/* Backend Connectivity */}
        <div className="hidden md:flex items-center gap-1.5 text-xs">
          <Server className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-400 text-[11px]">API:</span>
          <StatusBadge status={backendStatus} type="health" />
        </div>

        {/* Ollama Status */}
        <div className="hidden md:flex items-center gap-1.5 text-xs">
          <Cpu className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-400 text-[11px]">Ollama:</span>
          <StatusBadge status={ollamaStatus} type="health" />
        </div>

        {/* Freshness & Refresh */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-slate-500 font-mono hidden xl:block">
            {lastUpdated.toLocaleTimeString()}
          </span>
          <button
            onClick={triggerRefresh}
            title="Refresh Data"
            className="p-1.5 rounded bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </header>
  );
};
