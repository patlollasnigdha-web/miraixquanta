import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import { DecisionResponse } from '../types/api';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSpinner, ErrorAlert } from '../components/common/LoadingSpinner';
import {
  BrainCircuit,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Play,
  Lock,
} from 'lucide-react';

export const DecisionExplorerPage: React.FC = () => {
  const { selectedSymbol, setSelectedSymbol, availableSymbols, selectedPipeline } = useApp();
  const [horizon, setHorizon] = useState<string>('1d');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [decision, setDecision] = useState<DecisionResponse | null>(null);

  const handleEvaluate = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.evaluateDecision(selectedSymbol, horizon, selectedPipeline);
      setDecision(res);
    } catch (err: any) {
      setError(err.message || 'Error evaluating investment decision');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Controls Box */}
      <div className="terminal-card p-5">
        <div className="flex items-center gap-3 mb-2">
          <BrainCircuit className="w-5 h-5 text-blue-400" />
          <h2 className="text-sm font-mono font-bold uppercase tracking-wider text-slate-200">
            M09 Authoritative Investment Decision Engine
          </h2>
        </div>
        <p className="text-xs text-slate-400 mb-5 leading-relaxed">
          Aggregates evidence across Predictive AI (M03), Stock Strength (M05), Sentiment & Fundamentals (M06),
          and Market Regime (M07), strictly validated through M11 Dynamic Risk Management.
        </p>

        <div className="flex flex-wrap items-center gap-4 bg-[#0B0F19] p-4 rounded-lg border border-slate-800">
          <div>
            <label className="block text-[11px] font-mono text-slate-400 mb-1">Target Instrument</label>
            <select
              value={selectedSymbol}
              onChange={(e) => setSelectedSymbol(e.target.value)}
              className="bg-slate-900 border border-slate-700 text-slate-100 rounded px-3 py-1.5 text-xs font-mono focus:border-blue-500 focus:outline-none cursor-pointer"
            >
              {availableSymbols.map((sym) => (
                <option key={sym} value={sym}>
                  {sym} (NSE)
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-mono text-slate-400 mb-1">Investment Horizon</label>
            <select
              value={horizon}
              onChange={(e) => setHorizon(e.target.value)}
              className="bg-slate-900 border border-slate-700 text-slate-100 rounded px-3 py-1.5 text-xs font-mono focus:border-blue-500 focus:outline-none cursor-pointer"
            >
              <option value="1d">1-Day Forward (Daily)</option>
              <option value="5d">5-Day Forward (Swing)</option>
              <option value="20d">20-Day Forward (Monthly)</option>
            </select>
          </div>

          <div className="self-end">
            <button
              onClick={handleEvaluate}
              disabled={loading}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900/50 text-white rounded text-xs font-mono font-semibold flex items-center gap-2 transition shadow-md shadow-blue-500/20"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              {loading ? 'Evaluating...' : 'Generate Decision'}
            </button>
          </div>
        </div>
      </div>

      {loading && <LoadingSpinner message={`Running M09 multi-pillar arbitration for ${selectedSymbol}...`} />}
      {error && <ErrorAlert message={error} onRetry={handleEvaluate} />}

      {/* Decision Output Card */}
      {decision && !loading && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {/* Main Verdict Spotlight Banner */}
          <div
            className={`terminal-card p-6 border-2 ${
              decision.verdict === 'YES'
                ? 'border-emerald-600/80 bg-emerald-950/20'
                : decision.verdict === 'NO'
                ? 'border-rose-600/80 bg-rose-950/20'
                : decision.verdict === 'WAIT'
                ? 'border-amber-600/80 bg-amber-950/20'
                : 'border-slate-700 bg-slate-900/40'
            }`}
          >
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4 mb-4">
              <div>
                <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">
                  Authoritative M09 Verdict
                </span>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-3xl font-black font-mono tracking-tight text-slate-100">
                    {decision.verdict}
                  </span>
                  <StatusBadge status={decision.display_label} type="generic" />
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-4 text-xs font-mono">
                <div className="bg-slate-900/80 border border-slate-800 px-3 py-1.5 rounded">
                  <span className="text-slate-400 block text-[10px]">Composite Score</span>
                  <span className="font-bold text-slate-100">
                    {decision.verdict === 'INSUFFICIENT_DATA' || decision.composite_score == null
                      ? 'N/A'
                      : `${decision.composite_score.toFixed(1)} / 100`}
                  </span>
                </div>
                <div className="bg-slate-900/80 border border-slate-800 px-3 py-1.5 rounded">
                  <span className="text-slate-400 block text-[10px]">Confidence</span>
                  <span className="font-bold text-slate-100">
                    {decision.verdict === 'INSUFFICIENT_DATA' || decision.confidence === 0
                      ? '0.0% (N/A)'
                      : `${(decision.confidence * 100).toFixed(1)}%`}
                  </span>
                </div>
                <div className="bg-slate-900/80 border border-slate-800 px-3 py-1.5 rounded flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-blue-400" />
                  <div>
                    <span className="text-slate-400 block text-[10px]">M11 Risk Shield</span>
                    <span
                      className={`font-bold ${
                        decision.verdict === 'INSUFFICIENT_DATA'
                          ? 'text-slate-400'
                          : decision.risk_status === 'RISK_APPROVED'
                          ? 'text-emerald-400'
                          : 'text-rose-400'
                      }`}
                    >
                      {decision.verdict === 'INSUFFICIENT_DATA' ? 'NOT EVALUATED (INSUFFICIENT DATA)' : decision.risk_status}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Execution Parameter Targets */}
            {decision.verdict === 'YES' && (decision.suggested_stop_loss || decision.suggested_take_profit) && (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 bg-[#0B0F19]/60 p-3 rounded border border-slate-800 mb-4 text-xs font-mono">
                {decision.entry_reference_price && (
                  <div>
                    <span className="text-slate-500 text-[10px] block">Reference Price:</span>
                    <span className="font-semibold text-slate-200">₹{decision.entry_reference_price.toFixed(2)}</span>
                  </div>
                )}
                {decision.suggested_stop_loss && (
                  <div>
                    <span className="text-rose-400/80 text-[10px] block">Stop Loss:</span>
                    <span className="font-semibold text-rose-300">₹{decision.suggested_stop_loss.toFixed(2)}</span>
                  </div>
                )}
                {decision.suggested_take_profit && (
                  <div>
                    <span className="text-emerald-400/80 text-[10px] block">Take Profit:</span>
                    <span className="font-semibold text-emerald-300">₹{decision.suggested_take_profit.toFixed(2)}</span>
                  </div>
                )}
              </div>
            )}

            {/* Narrative Explanation */}
            <div className="space-y-1">
              <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold">
                Decision Rationale
              </span>
              <p className="text-xs text-slate-200 leading-relaxed bg-slate-900/40 p-3 rounded border border-slate-800">
                {decision.explanation}
              </p>
            </div>
          </div>

          {/* Evidence Factors Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Positive Factors */}
            <div className="terminal-card p-4">
              <div className="flex items-center gap-2 text-emerald-400 mb-2">
                <CheckCircle2 className="w-4 h-4" />
                <h4 className="text-xs font-mono font-bold uppercase">
                  Supporting Factors ({decision.positive_factors?.length || 0})
                </h4>
              </div>
              <ul className="space-y-2 text-xs text-slate-300">
                {decision.positive_factors && decision.positive_factors.length > 0 ? (
                  decision.positive_factors.map((f, i) => (
                    <li key={i} className="flex items-start gap-1.5">
                      <span className="text-emerald-500">•</span>
                      <span>{f}</span>
                    </li>
                  ))
                ) : (
                  <li className="text-slate-500 italic">No strong positive factors identified.</li>
                )}
              </ul>
            </div>

            {/* Negative Factors */}
            <div className="terminal-card p-4">
              <div className="flex items-center gap-2 text-rose-400 mb-2">
                <XCircle className="w-4 h-4" />
                <h4 className="text-xs font-mono font-bold uppercase">
                  Negative Factors ({decision.negative_factors?.length || 0})
                </h4>
              </div>
              <ul className="space-y-2 text-xs text-slate-300">
                {decision.negative_factors && decision.negative_factors.length > 0 ? (
                  decision.negative_factors.map((f, i) => (
                    <li key={i} className="flex items-start gap-1.5">
                      <span className="text-rose-500">•</span>
                      <span>{f}</span>
                    </li>
                  ))
                ) : (
                  <li className="text-slate-500 italic">No critical negative factors detected.</li>
                )}
              </ul>
            </div>

            {/* Conflicting Signals */}
            <div className="terminal-card p-4">
              <div className="flex items-center gap-2 text-amber-400 mb-2">
                <AlertTriangle className="w-4 h-4" />
                <h4 className="text-xs font-mono font-bold uppercase">
                  Conflicting Signals ({decision.conflicting_signals?.length || 0})
                </h4>
              </div>
              <ul className="space-y-2 text-xs text-slate-300">
                {decision.conflicting_signals && decision.conflicting_signals.length > 0 ? (
                  decision.conflicting_signals.map((f, i) => (
                    <li key={i} className="flex items-start gap-1.5">
                      <span className="text-amber-500">•</span>
                      <span>{f}</span>
                    </li>
                  ))
                ) : (
                  <li className="text-slate-500 italic">No conflicting cross-pillar signals.</li>
                )}
              </ul>
            </div>
          </div>

          {/* Institutional Compliance Disclaimer */}
          <div className="p-4 rounded-lg bg-slate-900/40 border border-slate-800 text-[11px] text-slate-400 leading-relaxed font-mono flex items-start gap-2.5">
            <Lock className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-slate-300">FINANCIAL COMPLIANCE & SAFETY NOTICE:</span> This decision
              is computed algorithmically by MIRAI M09 Investment Decision Engine using point-in-time quantitative data.
              Trading financial markets carries significant risk of capital loss. Past algorithmic performance does not
              guarantee future results.
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
