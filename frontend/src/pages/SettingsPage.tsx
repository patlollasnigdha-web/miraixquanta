import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { Settings, Server, Layers, Save, Check } from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const { selectedPipeline, setSelectedPipeline, selectedSymbol, setSelectedSymbol, availableSymbols } = useApp();
  const [apiUrl, setApiUrl] = useState<string>(import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1');
  const [saved, setSaved] = useState<boolean>(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="terminal-card p-5">
        <div className="flex items-center gap-2 mb-2">
          <Settings className="w-5 h-5 text-blue-400" />
          <h2 className="text-sm font-mono font-bold uppercase tracking-wider text-slate-200">
            Platform Settings & Operational Environment
          </h2>
        </div>
        <p className="text-xs text-slate-400 mb-6">
          Configure API connectivity parameters, active execution pipeline, and default instrument universe.
        </p>

        <form onSubmit={handleSave} className="space-y-5">
          {/* API Base URL */}
          <div>
            <label className="block text-xs font-mono text-slate-300 font-semibold mb-1 flex items-center gap-1.5">
              <Server className="w-3.5 h-3.5 text-blue-400" /> Backend API Base URL
            </label>
            <input
              type="text"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              className="w-full bg-[#0B0F19] border border-slate-700 rounded p-2.5 text-xs text-slate-100 font-mono focus:border-blue-500 focus:outline-none"
            />
            <span className="text-[11px] text-slate-500 font-mono mt-1 block">
              Default: http://localhost:8000/api/v1 (FastAPI backend service)
            </span>
          </div>

          {/* Active Pipeline */}
          <div>
            <label className="block text-xs font-mono text-slate-300 font-semibold mb-1 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-indigo-400" /> Execution Pipeline
            </label>
            <select
              value={selectedPipeline}
              onChange={(e) => setSelectedPipeline(e.target.value)}
              className="w-full bg-[#0B0F19] border border-slate-700 rounded p-2.5 text-xs text-slate-100 font-mono focus:border-blue-500 focus:outline-none"
            >
              <option value="pipeline_b_nifty">Pipeline B — NIFTY 50 Indian Equities (Daily & Intraday)</option>
              <option value="pipeline_a_fi2010">Pipeline A — FI-2010 Limit Order Book Microstructure</option>
            </select>
            <span className="text-[11px] text-slate-500 font-mono mt-1 block">
              Controls dataset source, prediction horizons, and strategy rules.
            </span>
          </div>

          {/* Default Symbol */}
          <div>
            <label className="block text-xs font-mono text-slate-300 font-semibold mb-1">
              Default Navigation Symbol
            </label>
            <select
              value={selectedSymbol}
              onChange={(e) => setSelectedSymbol(e.target.value)}
              className="w-full bg-[#0B0F19] border border-slate-700 rounded p-2.5 text-xs text-slate-100 font-mono focus:border-blue-500 focus:outline-none"
            >
              {availableSymbols.map((sym) => (
                <option key={sym} value={sym}>
                  {sym}
                </option>
              ))}
            </select>
          </div>

          <div className="pt-2">
            <button
              type="submit"
              className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-mono font-semibold flex items-center gap-2 transition"
            >
              {saved ? <Check className="w-4 h-4 text-emerald-300" /> : <Save className="w-4 h-4" />}
              {saved ? 'Settings Saved' : 'Save Configurations'}
            </button>
          </div>
        </form>
      </div>

      {/* Architecture Spec Card */}
      <div className="terminal-card p-5 space-y-3 text-xs font-mono">
        <h3 className="text-slate-200 font-bold uppercase tracking-wider text-[11px]">
          MIRAI Quant System Specifications
        </h3>
        <div className="grid grid-cols-2 gap-3 text-slate-400">
          <div>Architecture: M01 - M18 Integrated</div>
          <div>Frontend: React 18 + Vite + Tailwind</div>
          <div>Backend: FastAPI + Uvicorn + Pydantic</div>
          <div>Inference: PyTorch + XGBoost + Scikit-Learn</div>
          <div>LLM Runtime: Ollama (Qwen 2.5 Coder 7B)</div>
          <div>Paper Database: SQLite 3 State Manager</div>
        </div>
      </div>
    </div>
  );
};
