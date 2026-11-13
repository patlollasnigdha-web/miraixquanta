import React, { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import { StockStrengthResponse, StockSentimentResponse } from '../types/api';
import { StatCard } from '../components/common/StatCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSpinner, ErrorAlert } from '../components/common/LoadingSpinner';
import {
  TrendingUp,
  BarChart2,
  Newspaper,
  Layers,
  ArrowRightLeft,
  CheckCircle2,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from 'recharts';

export const StockIntelligencePage: React.FC = () => {
  const { selectedSymbol, setSelectedSymbol, availableSymbols, refreshKey } = useApp();
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [strength, setStrength] = useState<StockStrengthResponse | null>(null);
  const [sentiment, setSentiment] = useState<StockSentimentResponse | null>(null);

  // Comparison feature state
  const [compareSymbol, setCompareSymbol] = useState<string>('INFY');
  const [compareStrength, setCompareStrength] = useState<StockStrengthResponse | null>(null);
  const [showComparison, setShowComparison] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;
    const fetchStockIntelligence = async () => {
      setLoading(true);
      setError(null);
      try {
        const [strRes, sentRes] = await Promise.all([
          api.getStockStrength(selectedSymbol),
          api.getStockSentiment(selectedSymbol),
        ]);
        if (!isMounted) return;
        setStrength(strRes);
        setSentiment(sentRes);
      } catch (err: any) {
        if (isMounted) setError(err.message || 'Failed to fetch stock intelligence');
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchStockIntelligence();
    return () => {
      isMounted = false;
    };
  }, [selectedSymbol, refreshKey]);

  const handleRunComparison = async () => {
    try {
      const res = await api.getStockStrength(compareSymbol);
      setCompareStrength(res);
      setShowComparison(true);
    } catch (err: any) {
      alert(`Could not fetch comparison for ${compareSymbol}: ${err.message}`);
    }
  };

  if (loading) return <LoadingSpinner message={`Evaluating quantitative intelligence for ${selectedSymbol}...`} />;
  if (error) return <ErrorAlert message={error} onRetry={() => setSelectedSymbol(selectedSymbol)} />;

  // Transform factor scores for bar chart
  const factorData = strength?.factor_scores
    ? Object.entries(strength.factor_scores).map(([name, score]) => ({
        name: name.replace('_', ' ').replace('score', '').trim().toUpperCase(),
        score: Math.round(score * 10) / 10,
        contribution: strength.factor_contributions?.[name] || 0,
      }))
    : [];

  return (
    <div className="space-y-6">
      {/* Top Search & Instrument Header */}
      <div className="terminal-card p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-lg bg-blue-950/80 border border-blue-800 flex items-center justify-center font-bold text-lg font-mono text-blue-400">
            {selectedSymbol.slice(0, 3)}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold font-mono text-slate-100">{selectedSymbol}</h2>
              <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                NSE:EQ
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Evaluated as of: <span className="font-mono text-slate-300">{strength?.as_of_date || 'Latest'}</span>
            </p>
          </div>
        </div>

        {/* Symbol Selector */}
        <div className="flex items-center gap-3">
          <label className="text-xs text-slate-400 font-mono">Select Symbol:</label>
          <select
            value={selectedSymbol}
            onChange={(e) => setSelectedSymbol(e.target.value)}
            className="bg-[#0B0F19] border border-slate-700 text-slate-100 rounded px-3 py-1.5 text-xs font-mono focus:border-blue-500 focus:outline-none cursor-pointer"
          >
            {availableSymbols.map((sym) => (
              <option key={sym} value={sym}>
                {sym}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Stock Strength Score"
          value={`${strength?.stock_strength_score.toFixed(1) || 50.0} / 100`}
          subtitle={`Status: ${strength?.status || 'Neutral'}`}
          icon={<TrendingUp className="w-4 h-4 text-blue-400" />}
          badge={<StatusBadge status={strength?.status || 'Neutral'} type="generic" />}
        />
        <StatCard
          title="Model Confidence"
          value={`${((strength?.confidence || 0.8) * 100).toFixed(1)}%`}
          subtitle="Multi-Factor Agreement"
          icon={<CheckCircle2 className="w-4 h-4 text-emerald-400" />}
        />
        <StatCard
          title="News Sentiment"
          value={sentiment?.sentiment_label || 'NEUTRAL'}
          subtitle={`Score: ${sentiment?.sentiment_score.toFixed(2) || '0.00'} (${sentiment?.news_count || 0} items)`}
          icon={<Newspaper className="w-4 h-4 text-cyan-400" />}
          badge={<StatusBadge status={sentiment?.sentiment_label || 'NEUTRAL'} type="sentiment" />}
        />
        <StatCard
          title="Fundamentals"
          value={`${sentiment?.fundamental_score?.toFixed(1) || 'N/A'} / 100`}
          subtitle={sentiment?.fundamental_classification || 'Point-in-Time Disclosures'}
          icon={<Layers className="w-4 h-4 text-indigo-400" />}
        />
      </div>

      {/* Factor Contribution Breakdown Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="terminal-card p-5 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold">
                M05 Multi-Pillar Factor Breakdown
              </h3>
              <p className="text-xs text-slate-400">
                Pillar scores normalized from 0 to 100 with weighted risk-adjusted contributions
              </p>
            </div>
            <BarChart2 className="w-4 h-4 text-slate-500" />
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={factorData} layout="vertical" margin={{ top: 5, right: 20, left: 40, bottom: 5 }}>
                <XAxis type="number" domain={[0, 100]} stroke="#64748B" fontSize={11} />
                <YAxis dataKey="name" type="category" stroke="#64748B" fontSize={10} width={90} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', fontSize: '11px' }}
                  formatter={(val: any) => [`${val} / 100`, 'Factor Score']}
                />
                <Bar dataKey="score" radius={[0, 4, 4, 0]}>
                  {factorData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.score >= 60 ? '#10B981' : entry.score <= 40 ? '#EF4444' : '#3B82F6'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Sentiment Headlines & Insights */}
        <div className="terminal-card p-5 flex flex-col justify-between">
          <div>
            <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold mb-1">
              M06 Financial News & Fundamentals
            </h3>
            <p className="text-xs text-slate-400 mb-3">Extracted Point-in-Time Headlines</p>
            <div className="space-y-2">
              {sentiment?.recent_headlines && sentiment.recent_headlines.length > 0 ? (
                sentiment.recent_headlines.map((headline, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 rounded bg-slate-900/60 border border-slate-800 text-xs text-slate-300 leading-snug"
                  >
                    • {headline}
                  </div>
                ))
              ) : (
                <div className="p-4 text-center text-xs text-slate-500 font-mono">
                  No direct headlines available for this instrument. Neutral baseline applied.
                </div>
              )}
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] font-mono text-slate-400">
            Coverage Status:{' '}
            <span className="text-emerald-400 font-semibold">POINT-IN-TIME VERIFIED</span>
          </div>
        </div>
      </div>

      {/* Stock Comparison Tool */}
      <div className="terminal-card p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
          <div className="flex items-center gap-2">
            <ArrowRightLeft className="w-4 h-4 text-blue-400" />
            <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold">
              Comparative Intelligence Analysis
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 font-mono">Compare {selectedSymbol} with:</span>
            <select
              value={compareSymbol}
              onChange={(e) => setCompareSymbol(e.target.value)}
              className="bg-[#0B0F19] border border-slate-700 text-slate-100 rounded px-2.5 py-1 text-xs font-mono focus:outline-none"
            >
              {availableSymbols
                .filter((s) => s !== selectedSymbol)
                .map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
            </select>
            <button
              onClick={handleRunComparison}
              className="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-mono font-medium transition"
            >
              Compare
            </button>
          </div>
        </div>

        {showComparison && compareStrength && (
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono text-left">
              <thead className="bg-slate-900/80 text-slate-400 uppercase text-[10px] border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">Metric / Pillar</th>
                  <th className="py-2.5 px-3 text-blue-400">{selectedSymbol}</th>
                  <th className="py-2.5 px-3 text-emerald-400">{compareSymbol}</th>
                  <th className="py-2.5 px-3">Relative Leader</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                <tr>
                  <td className="py-2.5 px-3 text-slate-300 font-medium">Stock Strength Score</td>
                  <td className="py-2.5 px-3 font-bold text-slate-100">
                    {strength?.stock_strength_score.toFixed(1)} / 100
                  </td>
                  <td className="py-2.5 px-3 font-bold text-slate-100">
                    {compareStrength.stock_strength_score.toFixed(1)} / 100
                  </td>
                  <td className="py-2.5 px-3 font-semibold text-emerald-400">
                    {(strength?.stock_strength_score || 0) >= compareStrength.stock_strength_score
                      ? selectedSymbol
                      : compareSymbol}
                  </td>
                </tr>
                <tr>
                  <td className="py-2.5 px-3 text-slate-300">Status Classification</td>
                  <td className="py-2.5 px-3">
                    <StatusBadge status={strength?.status || 'Neutral'} />
                  </td>
                  <td className="py-2.5 px-3">
                    <StatusBadge status={compareStrength.status} />
                  </td>
                  <td className="py-2.5 px-3 text-slate-400">—</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-3 text-slate-300">Evaluation Confidence</td>
                  <td className="py-2.5 px-3">{((strength?.confidence || 0.8) * 100).toFixed(1)}%</td>
                  <td className="py-2.5 px-3">{(compareStrength.confidence * 100).toFixed(1)}%</td>
                  <td className="py-2.5 px-3 text-slate-400">
                    {(strength?.confidence || 0.8) >= compareStrength.confidence
                      ? selectedSymbol
                      : compareSymbol}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
