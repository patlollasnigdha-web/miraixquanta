import React, { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import { RiskStatusResponse } from '../types/api';
import { StatCard } from '../components/common/StatCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSpinner, ErrorAlert } from '../components/common/LoadingSpinner';
import { ShieldAlert, AlertTriangle, Lock, CheckCircle, ShieldCheck } from 'lucide-react';

export const RiskManagementPage: React.FC = () => {
  const { refreshKey } = useApp();
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [riskStatus, setRiskStatus] = useState<RiskStatusResponse | null>(null);

  useEffect(() => {
    let isMounted = true;
    const fetchRisk = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.getRiskStatus();
        if (!isMounted) return;
        setRiskStatus(res);
      } catch (err: any) {
        if (isMounted) setError(err.message || 'Failed to load risk management status');
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchRisk();
    return () => {
      isMounted = false;
    };
  }, [refreshKey]);

  if (loading) return <LoadingSpinner message="Checking M11 dynamic risk controls..." />;
  if (error) return <ErrorAlert message={error} />;

  const cbState = riskStatus?.circuit_breaker_state || 'NORMAL';

  return (
    <div className="space-y-6">
      {/* Top Banner: Circuit Breaker State */}
      <div className="terminal-card p-6 bg-gradient-to-r from-slate-900 to-[#111827]">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div
              className={`w-12 h-12 rounded-lg flex items-center justify-center font-bold text-xl border ${
                cbState === 'NORMAL'
                  ? 'bg-emerald-950/80 border-emerald-800 text-emerald-400'
                  : cbState === 'CAUTION'
                  ? 'bg-amber-950/80 border-amber-800 text-amber-400'
                  : 'bg-rose-950/80 border-rose-800 text-rose-400'
              }`}
            >
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h2 className="text-xl font-bold font-mono text-slate-100">Circuit Breaker: {cbState}</h2>
                <StatusBadge status={cbState} type="circuit" />
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {riskStatus?.status_message || 'Automated safety supervision actively enforced.'}
              </p>
            </div>
          </div>
          <div className="text-xs font-mono text-slate-500">
            Last Checked: {new Date(riskStatus?.timestamp || Date.now()).toLocaleTimeString()}
          </div>
        </div>
      </div>

      {/* Risk Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          title="Max Drawdown Limit"
          value={`${riskStatus?.max_drawdown_limit_pct.toFixed(1) || '15.0'}%`}
          subtitle="Peak-to-Trough Cap"
          icon={<AlertTriangle className="w-4 h-4 text-rose-400" />}
        />
        <StatCard
          title="Max Single Position"
          value={`${riskStatus?.max_position_size_pct.toFixed(1) || '20.0'}%`}
          subtitle="Single-Asset Exposure Ceiling"
          icon={<Lock className="w-4 h-4 text-blue-400" />}
        />
        <StatCard
          title="Mandatory Cash Reserve"
          value={`${riskStatus?.cash_reserve_required_pct.toFixed(1) || '5.0'}%`}
          subtitle="Liquidity Buffer Requirement"
          icon={<ShieldCheck className="w-4 h-4 text-emerald-400" />}
        />
      </div>

      {/* Dynamic Risk Enforcements */}
      <div className="terminal-card p-5">
        <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold mb-4">
          M11 Dynamic Risk Rules & State Specifications
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-[#0B0F19] p-4 rounded-lg border border-slate-800 space-y-2">
            <div className="flex items-center gap-2 text-emerald-400 text-xs font-mono font-bold">
              <CheckCircle className="w-4 h-4" />
              <span>NORMAL Operating State</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Standard quantitative limits applied. 100% position sizing permissible. Trailing stops ratcheted
              continuously on all open positions.
            </p>
          </div>

          <div className="bg-[#0B0F19] p-4 rounded-lg border border-slate-800 space-y-2">
            <div className="flex items-center gap-2 text-amber-400 text-xs font-mono font-bold">
              <AlertTriangle className="w-4 h-4" />
              <span>CAUTION Operating State</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Triggered upon 50% drawdown threshold or volatility shock. Position sizing automatically halved (50% scale
              down) to curtail capital erosion.
            </p>
          </div>

          <div className="bg-[#0B0F19] p-4 rounded-lg border border-slate-800 space-y-2">
            <div className="flex items-center gap-2 text-orange-400 text-xs font-mono font-bold">
              <Lock className="w-4 h-4" />
              <span>RESTRICTED Operating State</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              No new long positions permitted. System permits only risk-reducing exits, stop-loss triggers, and profit
              taking.
            </p>
          </div>

          <div className="bg-[#0B0F19] p-4 rounded-lg border border-slate-800 space-y-2">
            <div className="flex items-center gap-2 text-rose-400 text-xs font-mono font-bold">
              <ShieldAlert className="w-4 h-4" />
              <span>HALTED Emergency State</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Critical risk threshold breach. All algorithmic trade generation suspended immediately until manual
              acknowledgment and reset.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
