import React, { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import { PaperAccountState, PaperPosition, PortfolioOptimiseResponse } from '../types/api';
import { StatCard } from '../components/common/StatCard';
import { LoadingSpinner, ErrorAlert } from '../components/common/LoadingSpinner';
import { Wallet, Coins, Briefcase, Sliders, Play } from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from 'recharts';

export const PortfolioPage: React.FC = () => {
  const { availableSymbols, refreshKey } = useApp();
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [account, setAccount] = useState<PaperAccountState | null>(null);
  const [positions, setPositions] = useState<PaperPosition[]>([]);

  // M10 Optimiser interactive form state
  const [optSymbols, setOptSymbols] = useState<string[]>(['TCS', 'INFY', 'RELIANCE', 'HDFCBANK']);
  const [optMethod, setOptMethod] = useState<string>('risk_budgeting');
  const [optTargetRisk, setOptTargetRisk] = useState<number>(0.15);
  const [optLoading, setOptLoading] = useState<boolean>(false);
  const [optResult, setOptResult] = useState<PortfolioOptimiseResponse | null>(null);

  useEffect(() => {
    let isMounted = true;
    const loadPortfolio = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.getPortfolio();
        if (!isMounted) return;
        setAccount(res.account);
        setPositions(res.positions || []);
      } catch (err: any) {
        if (isMounted) setError(err.message || 'Failed to fetch portfolio data');
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    loadPortfolio();
    return () => {
      isMounted = false;
    };
  }, [refreshKey]);

  const handleRunOptimizer = async () => {
    setOptLoading(true);
    try {
      const res = await api.optimisePortfolio(optSymbols, optMethod, optTargetRisk);
      setOptResult(res);
    } catch (err: any) {
      alert(`Optimization failed: ${err.message}`);
    } finally {
      setOptLoading(false);
    }
  };

  const toggleSymbolSelection = (sym: string) => {
    if (optSymbols.includes(sym)) {
      if (optSymbols.length > 2) setOptSymbols(optSymbols.filter((s) => s !== sym));
    } else {
      setOptSymbols([...optSymbols, sym]);
    }
  };

  if (loading) return <LoadingSpinner message="Retrieving portfolio state..." />;
  if (error) return <ErrorAlert message={error} />;

  const totalEquity = account?.total_equity || 1000000;
  const cash = account?.available_cash || 1000000;
  const invested = account?.invested_capital || 0;

  // Chart data from optimization
  const weightsChartData = optResult?.weights
    ? Object.entries(optResult.weights).map(([sym, w]) => ({
        symbol: sym,
        weightPct: Math.round(w * 1000) / 10,
      }))
    : [];

  return (
    <div className="space-y-6">
      {/* Portfolio Header Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          title="Virtual Portfolio Equity"
          value={`₹${totalEquity.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
          subtitle="Net Asset Value"
          icon={<Wallet className="w-4 h-4 text-blue-400" />}
        />
        <StatCard
          title="Available Cash"
          value={`₹${cash.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
          subtitle={`Reserve: ${((cash / totalEquity) * 100).toFixed(1)}%`}
          icon={<Coins className="w-4 h-4 text-emerald-400" />}
        />
        <StatCard
          title="Invested Capital"
          value={`₹${invested.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
          subtitle={`${positions.length} active holdings`}
          icon={<Briefcase className="w-4 h-4 text-amber-400" />}
        />
      </div>

      {/* Current Positions Table */}
      <div className="terminal-card p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold">
              Current Virtual Holdings ({positions.length})
            </h3>
            <p className="text-xs text-slate-400">Mark-to-market positions from active paper trading</p>
          </div>
          <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
            LIVE MTM
          </span>
        </div>

        {positions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono text-left">
              <thead className="bg-slate-900/80 text-slate-400 uppercase text-[10px] border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">Symbol</th>
                  <th className="py-2.5 px-3">Units</th>
                  <th className="py-2.5 px-3">Avg Entry</th>
                  <th className="py-2.5 px-3">Current Price</th>
                  <th className="py-2.5 px-3">Market Value</th>
                  <th className="py-2.5 px-3">Stop Loss</th>
                  <th className="py-2.5 px-3">Take Profit</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {positions.map((pos, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/30">
                    <td className="py-2.5 px-3 font-bold text-slate-100">{pos.symbol}</td>
                    <td className="py-2.5 px-3 text-slate-300">{pos.units}</td>
                    <td className="py-2.5 px-3 text-slate-300">₹{pos.average_entry_price?.toFixed(2)}</td>
                    <td className="py-2.5 px-3 text-slate-100 font-semibold">₹{pos.current_price?.toFixed(2)}</td>
                    <td className="py-2.5 px-3 text-slate-200">₹{pos.market_value?.toFixed(2)}</td>
                    <td className="py-2.5 px-3 text-rose-400">
                      {pos.stop_loss ? `₹${pos.stop_loss.toFixed(2)}` : '—'}
                    </td>
                    <td className="py-2.5 px-3 text-emerald-400">
                      {pos.take_profit ? `₹${pos.take_profit.toFixed(2)}` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-8 text-center text-xs text-slate-500 font-mono">
            No virtual positions currently open. Generate orders or run paper trading sessions.
          </div>
        )}
      </div>

      {/* M10 Portfolio Optimiser Engine Box */}
      <div className="terminal-card p-5">
        <div className="flex items-center gap-2 mb-2">
          <Sliders className="w-5 h-5 text-blue-400" />
          <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold">
            M10 Quantitative Portfolio Optimisation Engine
          </h3>
        </div>
        <p className="text-xs text-slate-400 mb-5">
          Solves mathematical asset allocation using Risk Budgeting, Minimum Variance, or Equal Weight.
        </p>

        {/* Optimiser Controls */}
        <div className="bg-[#0B0F19] p-4 rounded-lg border border-slate-800 space-y-4 mb-6">
          <div>
            <label className="block text-[11px] font-mono text-slate-400 mb-2">
              Select Candidate Asset Universe (Min 2):
            </label>
            <div className="flex flex-wrap gap-2">
              {availableSymbols.map((sym) => {
                const isSelected = optSymbols.includes(sym);
                return (
                  <button
                    key={sym}
                    onClick={() => toggleSymbolSelection(sym)}
                    className={`px-2.5 py-1 rounded text-xs font-mono transition ${
                      isSelected
                        ? 'bg-blue-600 text-white font-semibold'
                        : 'bg-slate-900 text-slate-400 border border-slate-800 hover:text-slate-200'
                    }`}
                  >
                    {sym}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-4 pt-2">
            <div>
              <label className="block text-[11px] font-mono text-slate-400 mb-1">Allocation Method</label>
              <select
                value={optMethod}
                onChange={(e) => setOptMethod(e.target.value)}
                className="bg-slate-900 border border-slate-700 text-slate-100 rounded px-3 py-1.5 text-xs font-mono focus:outline-none"
              >
                <option value="risk_budgeting">Risk Budgeting / Parity</option>
                <option value="min_variance">Minimum Variance</option>
                <option value="equal_weight">Equal Weight (Baseline)</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-mono text-slate-400 mb-1">Target Volatility</label>
              <select
                value={optTargetRisk}
                onChange={(e) => setOptTargetRisk(parseFloat(e.target.value))}
                className="bg-slate-900 border border-slate-700 text-slate-100 rounded px-3 py-1.5 text-xs font-mono focus:outline-none"
              >
                <option value="0.10">10% Target Annual Vol</option>
                <option value="0.15">15% Target Annual Vol</option>
                <option value="0.20">20% Target Annual Vol</option>
              </select>
            </div>

            <div className="self-end">
              <button
                onClick={handleRunOptimizer}
                disabled={optLoading}
                className="px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900 text-white rounded text-xs font-mono font-semibold flex items-center gap-2 transition"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                {optLoading ? 'Optimizing...' : 'Calculate Optimal Weights'}
              </button>
            </div>
          </div>
        </div>

        {/* Optimiser Result Output */}
        {optResult && (
          <div className="space-y-4 pt-4 border-t border-slate-800">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs">
              <div className="bg-slate-900/60 p-3 rounded border border-slate-800">
                <span className="text-[10px] text-slate-500 block">Expected Return</span>
                <span className="font-bold text-emerald-400">
                  {optResult.expected_annual_return_pct.toFixed(2)}% p.a.
                </span>
              </div>
              <div className="bg-slate-900/60 p-3 rounded border border-slate-800">
                <span className="text-[10px] text-slate-500 block">Annual Volatility</span>
                <span className="font-bold text-amber-400">
                  {optResult.annual_volatility_pct.toFixed(2)}%
                </span>
              </div>
              <div className="bg-slate-900/60 p-3 rounded border border-slate-800">
                <span className="text-[10px] text-slate-500 block">Sharpe Ratio</span>
                <span className="font-bold text-slate-100">{optResult.sharpe_ratio.toFixed(2)}</span>
              </div>
              <div className="bg-slate-900/60 p-3 rounded border border-slate-800">
                <span className="text-[10px] text-slate-500 block">Diversification Score</span>
                <span className="font-bold text-blue-400">
                  {optResult.diversification_score.toFixed(2)}
                </span>
              </div>
            </div>

            {/* Weights Chart */}
            <div className="h-56 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={weightsChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <XAxis dataKey="symbol" stroke="#64748B" fontSize={11} />
                  <YAxis stroke="#64748B" fontSize={11} unit="%" />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', fontSize: '11px' }}
                    formatter={(val: any) => [`${val}%`, 'Allocated Weight']}
                  />
                  <Bar dataKey="weightPct" fill="#3B82F6" radius={[4, 4, 0, 0]}>
                    {weightsChartData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill="#3B82F6" />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
