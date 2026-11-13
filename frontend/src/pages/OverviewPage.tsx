import React, { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import {
  MarketRegimeResponse,
  PaperAccountState,
  PaperPosition,
  DecisionResponse,
  MonitoringAlert,
} from '../types/api';
import { StatCard } from '../components/common/StatCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSpinner, ErrorAlert } from '../components/common/LoadingSpinner';
import {
  Wallet,
  Coins,
  TrendingUp,
  ShieldCheck,
  Compass,
  Briefcase,
  AlertOctagon,
  ArrowRight,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

export const OverviewPage: React.FC<{ onNavigate: (page: string) => void }> = ({ onNavigate }) => {
  const { selectedPipeline, refreshKey } = useApp();
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [regime, setRegime] = useState<MarketRegimeResponse | null>(null);
  const [account, setAccount] = useState<PaperAccountState | null>(null);
  const [positions, setPositions] = useState<PaperPosition[]>([]);
  const [recentDecision, setRecentDecision] = useState<DecisionResponse | null>(null);
  const [alerts, setAlerts] = useState<MonitoringAlert[]>([]);

  useEffect(() => {
    let isMounted = true;
    const fetchOverviewData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [regimeRes, portRes, decRes, alertsRes] = await Promise.allSettled([
          api.getMarketRegime(selectedPipeline),
          api.getPortfolio(),
          api.evaluateDecision('TCS', '1d', selectedPipeline),
          api.getAlerts(),
        ]);

        if (!isMounted) return;

        if (regimeRes.status === 'fulfilled') setRegime(regimeRes.value);
        if (portRes.status === 'fulfilled') {
          setAccount(portRes.value.account);
          setPositions(portRes.value.positions || []);
        }
        if (decRes.status === 'fulfilled') setRecentDecision(decRes.value);
        if (alertsRes.status === 'fulfilled') setAlerts(alertsRes.value.alerts.slice(0, 5));
      } catch (err: any) {
        if (isMounted) setError(err.message || 'Failed to load overview data');
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchOverviewData();
    return () => {
      isMounted = false;
    };
  }, [selectedPipeline, refreshKey]);

  if (loading) return <LoadingSpinner message="Loading algorithmic terminal overview..." />;
  if (error) return <ErrorAlert message={error} />;

  const totalEquity = account?.total_equity || 1000000;
  const cash = account?.available_cash || 1000000;
  const invested = account?.invested_capital || 0;
  const initialCap = account?.initial_capital || 1000000;
  const totalReturnPct = ((totalEquity - initialCap) / initialCap) * 100;

  // Mocked equity curve trajectory for demonstration derived from account equity
  const equityHistory = [
    { date: 'Day -6', equity: initialCap * 0.992 },
    { date: 'Day -5', equity: initialCap * 0.998 },
    { date: 'Day -4', equity: initialCap * 1.005 },
    { date: 'Day -3', equity: initialCap * 1.002 },
    { date: 'Day -2', equity: initialCap * 1.011 },
    { date: 'Day -1', equity: initialCap * 1.008 },
    { date: 'Live', equity: totalEquity },
  ];

  // Allocation data
  const allocationData = [
    { name: 'Cash', value: Math.max(cash, 1000), color: '#3B82F6' },
    { name: 'Equities', value: Math.max(invested, 0), color: '#10B981' },
  ];

  return (
    <div className="space-y-6">
      {/* Top Banner: Market Regime & System Posture */}
      <div className="terminal-card bg-gradient-to-r from-blue-950/40 via-slate-900 to-slate-900 border-blue-900/40 p-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Compass className="w-5 h-5 text-blue-400" />
              <h2 className="text-sm font-mono font-bold uppercase tracking-wider text-slate-200">
                Active Market Regime Intelligence
              </h2>
            </div>
            <p className="text-xl font-bold text-slate-100 font-mono">
              {regime?.detected_regime || 'SIDEWAYS_RANGE_BOUND'}
            </p>
            <p className="text-xs text-slate-400">
              Confidence:{' '}
              <span className="font-mono text-emerald-400 font-semibold">
                {((regime?.regime_confidence || 0.8) * 100).toFixed(1)}%
              </span>{' '}
              | Pipeline:{' '}
              <span className="font-mono text-slate-300">
                {selectedPipeline === 'pipeline_b_nifty' ? 'NIFTY 50 Equities' : 'FI-2010 Microstructure'}
              </span>
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => onNavigate('decision')}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-mono font-semibold flex items-center gap-2 transition"
            >
              Evaluate Stock <ArrowRight className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => onNavigate('assistant')}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-xs font-mono transition"
            >
              Consult AI
            </button>
          </div>
        </div>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Virtual Equity"
          value={`₹${totalEquity.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
          subtitle="Total Account Value"
          icon={<Wallet className="w-4 h-4" />}
          trend={totalReturnPct >= 0 ? 'up' : 'down'}
          trendValue={`${totalReturnPct >= 0 ? '+' : ''}${totalReturnPct.toFixed(2)}%`}
        />
        <StatCard
          title="Available Cash"
          value={`₹${cash.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
          subtitle="Free Margin"
          icon={<Coins className="w-4 h-4" />}
        />
        <StatCard
          title="Active Positions"
          value={positions.length}
          subtitle={`₹${invested.toLocaleString('en-IN', { maximumFractionDigits: 0 })} deployed`}
          icon={<Briefcase className="w-4 h-4" />}
        />
        <StatCard
          title="Risk Status"
          value={account?.circuit_breaker_state || 'NORMAL'}
          subtitle="Dynamic Risk Shield"
          icon={<ShieldCheck className="w-4 h-4" />}
          badge={<StatusBadge status={account?.circuit_breaker_state || 'NORMAL'} type="circuit" />}
        />
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Equity Curve (2 cols) */}
        <div className="terminal-card p-5 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold">
                Portfolio Equity Trajectory
              </h3>
              <p className="text-xs text-slate-400">Chronological virtual portfolio progression</p>
            </div>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
              SIMULATED
            </span>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={equityHistory} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#3B82F6" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" stroke="#64748B" fontSize={11} tickLine={false} />
                <YAxis
                  stroke="#64748B"
                  fontSize={11}
                  domain={['dataMin - 10000', 'dataMax + 10000']}
                  tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
                />
                <Tooltip
                  contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', fontSize: '12px' }}
                  formatter={(val: any) => [`₹${Number(val).toLocaleString('en-IN')}`, 'Portfolio Equity']}
                />
                <Area type="monotone" dataKey="equity" stroke="#3B82F6" strokeWidth={2} fill="url(#equityGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Capital Allocation Pie (1 col) */}
        <div className="terminal-card p-5 flex flex-col justify-between">
          <div>
            <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold">
              Capital Allocation
            </h3>
            <p className="text-xs text-slate-400 mb-4">Holdings vs Liquid Reserves</p>
            <div className="h-44 w-full flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={allocationData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={70}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {allocationData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', fontSize: '11px' }}
                    formatter={(val: any) => `₹${Number(val).toLocaleString('en-IN')}`}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="space-y-2 font-mono text-xs pt-3 border-t border-slate-800">
            <div className="flex justify-between items-center">
              <span className="flex items-center gap-1.5 text-slate-400">
                <span className="w-2.5 h-2.5 rounded-sm bg-blue-500" /> Cash:
              </span>
              <span className="font-semibold text-slate-200">
                {((cash / totalEquity) * 100).toFixed(1)}%
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="flex items-center gap-1.5 text-slate-400">
                <span className="w-2.5 h-2.5 rounded-sm bg-emerald-500" /> Invested:
              </span>
              <span className="font-semibold text-slate-200">
                {((invested / totalEquity) * 100).toFixed(1)}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Lower Row: Authoritative M09 Decision Spotlight & Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Decision Spotlight */}
        <div className="terminal-card p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-emerald-400" />
              <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold">
                M09 Decision Intelligence: {recentDecision?.symbol || 'TCS'}
              </h3>
            </div>
            {recentDecision && <StatusBadge status={recentDecision.verdict} type="verdict" />}
          </div>
          {recentDecision ? (
            <div className="space-y-3">
              <div className="bg-slate-900/60 p-3 rounded border border-slate-800 text-xs">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-slate-400">Display Label:</span>
                  <span className="font-mono font-semibold text-slate-200">{recentDecision.display_label}</span>
                </div>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-slate-400">Composite Score:</span>
                  <span className="font-mono font-semibold text-emerald-400">
                    {recentDecision.composite_score.toFixed(1)} / 100
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">M11 Risk Status:</span>
                  <span className="font-mono text-slate-300">{recentDecision.risk_status}</span>
                </div>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed italic border-l-2 border-blue-500 pl-3">
                "{recentDecision.explanation || 'No rationale generated.'}"
              </p>
              <button
                onClick={() => onNavigate('decision')}
                className="text-xs text-blue-400 hover:text-blue-300 font-mono flex items-center gap-1 transition"
              >
                Open Full Decision Explorer →
              </button>
            </div>
          ) : (
            <p className="text-xs text-slate-500 font-mono">No decision recorded yet.</p>
          )}
        </div>

        {/* Operational Alerts */}
        <div className="terminal-card p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <AlertOctagon className="w-4 h-4 text-amber-400" />
              <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold">
                M18 Operational Alerts ({alerts.length})
              </h3>
            </div>
            <button
              onClick={() => onNavigate('monitoring')}
              className="text-xs text-slate-400 hover:text-slate-200 font-mono"
            >
              View All
            </button>
          </div>
          {alerts.length > 0 ? (
            <div className="space-y-2">
              {alerts.map((alt) => (
                <div
                  key={alt.alert_id}
                  className="bg-slate-900/40 border border-slate-800 p-2.5 rounded text-xs flex items-start justify-between gap-2"
                >
                  <div>
                    <div className="flex items-center gap-2 mb-0.5">
                      <span
                        className={`font-mono text-[10px] px-1.5 py-0.2 rounded font-semibold ${
                          alt.severity === 'CRITICAL'
                            ? 'bg-rose-950 text-rose-400 border border-rose-800'
                            : 'bg-amber-950 text-amber-400 border border-amber-800'
                        }`}
                      >
                        {alt.severity}
                      </span>
                      <span className="font-mono text-slate-300 text-[11px]">{alt.component}</span>
                    </div>
                    <p className="text-slate-400 text-[11px]">{alt.message}</p>
                  </div>
                  <span className="text-[10px] text-slate-500 font-mono shrink-0">
                    {new Date(alt.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-6 text-center text-xs text-slate-500 font-mono">
              ✓ No active operational alerts. All systems operating within normal parameters.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
