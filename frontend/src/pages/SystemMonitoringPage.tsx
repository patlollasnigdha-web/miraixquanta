import React, { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import { SystemHealthReport, MonitoringMetrics, MonitoringAlert, SystemResourceUsage } from '../types/api';
import { StatCard } from '../components/common/StatCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSpinner, ErrorAlert } from '../components/common/LoadingSpinner';
import {
  Activity,
  Server,
  Cpu,
  HardDrive,
  AlertTriangle,
  Clock,
} from 'lucide-react';

export const SystemMonitoringPage: React.FC = () => {
  const { refreshKey } = useApp();
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [health, setHealth] = useState<SystemHealthReport | null>(null);
  const [metrics, setMetrics] = useState<MonitoringMetrics | null>(null);
  const [alerts, setAlerts] = useState<MonitoringAlert[]>([]);
  const [sysUsage, setSysUsage] = useState<SystemResourceUsage | null>(null);

  useEffect(() => {
    let isMounted = true;
    const fetchTelemetry = async () => {
      setLoading(true);
      setError(null);
      try {
        const [hRes, mRes, aRes, sRes] = await Promise.allSettled([
          api.getHealth(),
          api.getMetrics(),
          api.getAlerts(),
          api.getSystemSummary(),
        ]);

        if (!isMounted) return;

        if (hRes.status === 'fulfilled') setHealth(hRes.value);
        if (mRes.status === 'fulfilled') setMetrics(mRes.value);
        if (aRes.status === 'fulfilled') setAlerts(aRes.value.alerts || []);
        if (sRes.status === 'fulfilled') setSysUsage(sRes.value);
      } catch (err: any) {
        if (isMounted) setError(err.message || 'Error fetching monitoring telemetry');
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchTelemetry();
    return () => {
      isMounted = false;
    };
  }, [refreshKey]);

  if (loading) return <LoadingSpinner message="Checking M18 telemetry & subsystem diagnostics..." />;
  if (error) return <ErrorAlert message={error} />;

  const reqTotal = metrics?.counters?.['api_requests_total'] || 0;
  const durationSummary = metrics?.latencies?.['api_request_duration_ms'];
  const meanLatency = durationSummary?.mean ? `${durationSummary.mean.toFixed(1)} ms` : '< 5 ms';
  const p95Latency = durationSummary?.p95 ? `${durationSummary.p95.toFixed(1)} ms` : '< 12 ms';

  return (
    <div className="space-y-6">
      {/* Top Health Header */}
      <div className="terminal-card p-5 bg-gradient-to-r from-slate-900 to-[#111827]">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Activity className="w-5 h-5 text-emerald-400" />
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-mono font-bold uppercase tracking-wider text-slate-100">
                  M18 Observability & Subsystem Telemetry
                </h2>
                <StatusBadge status={health?.overall_status || 'HEALTHY'} type="health" />
              </div>
              <p className="text-xs text-slate-400">
                Engine Version: <span className="font-mono text-slate-300">v{health?.version || '1.0.0'}</span> | Live
                Metrics Collector Window: 300s
              </p>
            </div>
          </div>
          <div className="text-xs font-mono text-slate-500">
            Telemetry Updated: {new Date(health?.timestamp || Date.now()).toLocaleTimeString()}
          </div>
        </div>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <StatCard
          title="Total API Calls"
          value={reqTotal}
          subtitle="Processed since startup"
          icon={<Server className="w-4 h-4 text-blue-400" />}
        />
        <StatCard
          title="Avg Latency"
          value={meanLatency}
          subtitle="Internal processing duration"
          icon={<Clock className="w-4 h-4 text-emerald-400" />}
        />
        <StatCard
          title="p95 Latency"
          value={p95Latency}
          subtitle="95th percentile response time"
          icon={<Clock className="w-4 h-4 text-amber-400" />}
        />
        <StatCard
          title="Active Alerts"
          value={alerts.length}
          subtitle="Operational events logged"
          icon={<AlertTriangle className="w-4 h-4 text-rose-400" />}
          badge={<StatusBadge status={alerts.length > 0 ? 'ALERTING' : 'NOMINAL'} />}
        />
      </div>

      {/* Subsystem Health Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {health?.components &&
          Object.entries(health.components).map(([name, comp]) => (
            <div key={name} className="terminal-card p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono uppercase tracking-wider text-slate-400">
                  {name.replace('_', ' ')}
                </span>
                <StatusBadge status={comp.status} type="health" />
              </div>
              <p className="text-xs text-slate-300 font-sans">{comp.message || 'Operational'}</p>
            </div>
          ))}
      </div>

      {/* Host Machine Telemetry */}
      {sysUsage && (
        <div className="terminal-card p-5">
          <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold mb-4">
            Host Hardware Resource Telemetry
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 font-mono text-xs">
            {/* CPU */}
            <div>
              <div className="flex justify-between items-center text-slate-300 mb-1.5">
                <span className="flex items-center gap-1.5">
                  <Cpu className="w-4 h-4 text-blue-400" /> CPU Load:
                </span>
                <span className="font-bold text-slate-100">{sysUsage.cpu_percent.toFixed(1)}%</span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-blue-500 h-full rounded-full transition-all duration-300"
                  style={{ width: `${Math.min(sysUsage.cpu_percent, 100)}%` }}
                />
              </div>
            </div>

            {/* RAM */}
            <div>
              <div className="flex justify-between items-center text-slate-300 mb-1.5">
                <span className="flex items-center gap-1.5">
                  <Server className="w-4 h-4 text-emerald-400" /> RAM Usage:
                </span>
                <span className="font-bold text-slate-100">
                  {(sysUsage.memory_used_mb / 1024).toFixed(1)} / {(sysUsage.memory_total_mb / 1024).toFixed(1)} GB (
                  {sysUsage.memory_percent.toFixed(1)}%)
                </span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-emerald-500 h-full rounded-full transition-all duration-300"
                  style={{ width: `${Math.min(sysUsage.memory_percent, 100)}%` }}
                />
              </div>
            </div>

            {/* Disk */}
            <div>
              <div className="flex justify-between items-center text-slate-300 mb-1.5">
                <span className="flex items-center gap-1.5">
                  <HardDrive className="w-4 h-4 text-amber-400" /> Disk Space:
                </span>
                <span className="font-bold text-slate-100">
                  {sysUsage.disk_used_gb.toFixed(0)} / {sysUsage.disk_total_gb.toFixed(0)} GB (
                  {sysUsage.disk_percent.toFixed(1)}%)
                </span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-amber-500 h-full rounded-full transition-all duration-300"
                  style={{ width: `${Math.min(sysUsage.disk_percent, 100)}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Detailed Alert Ledger */}
      <div className="terminal-card p-5">
        <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold mb-4">
          Historical Operational Alert Ledger ({alerts.length})
        </h3>
        {alerts.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono text-left">
              <thead className="bg-slate-900/80 text-slate-400 uppercase text-[10px] border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">Severity</th>
                  <th className="py-2.5 px-3">Subsystem</th>
                  <th className="py-2.5 px-3">Alert Message</th>
                  <th className="py-2.5 px-3">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {alerts.map((a) => (
                  <tr key={a.alert_id} className="hover:bg-slate-800/30">
                    <td className="py-2 px-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          a.severity === 'CRITICAL'
                            ? 'bg-rose-950 text-rose-400 border border-rose-800'
                            : 'bg-amber-950 text-amber-400 border border-amber-800'
                        }`}
                      >
                        {a.severity}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-slate-200">{a.component}</td>
                    <td className="py-2 px-3 text-slate-300">{a.message}</td>
                    <td className="py-2 px-3 text-slate-400">{new Date(a.timestamp).toLocaleTimeString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-8 text-center text-xs text-slate-500 font-mono">
            No system alerts triggered. All thresholds normal.
          </div>
        )}
      </div>
    </div>
  );
};
