import React, { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import { PaperAccountState, PaperPosition, PaperOrder, PaperSession } from '../types/api';
import { StatCard } from '../components/common/StatCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { ConfirmModal } from '../components/common/ConfirmModal';
import { LoadingSpinner, ErrorAlert } from '../components/common/LoadingSpinner';
import {
  Wallet,
  Play,
  Pause,
  Square,
  PlusCircle,
  FileSpreadsheet,
  AlertTriangle,
} from 'lucide-react';

export const PaperTradingPage: React.FC = () => {
  const { refreshKey, triggerRefresh } = useApp();
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [account, setAccount] = useState<PaperAccountState | null>(null);
  const [positions, setPositions] = useState<PaperPosition[]>([]);
  const [orders, setOrders] = useState<PaperOrder[]>([]);
  const [sessions, setSessions] = useState<PaperSession[]>([]);

  // State-changing action modal state
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const [pendingAction, setPendingAction] = useState<{
    type: 'START' | 'PAUSE' | 'RESUME' | 'STOP' | 'CLOSE';
    sessionId: string;
    sessionName: string;
  } | null>(null);

  // New session modal / form
  const [newSessionName, setNewSessionName] = useState<string>('LiveSimSession');
  const [newSessionCapital, setNewSessionCapital] = useState<number>(1000000);
  const [creatingSession, setCreatingSession] = useState<boolean>(false);

  const loadPaperTradingData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [accRes, posRes, ordRes, sessRes] = await Promise.all([
        api.getPaperAccount(),
        api.getPaperPositions(),
        api.getPaperOrders(30),
        api.listPaperSessions(),
      ]);
      setAccount(accRes);
      setPositions(posRes.positions || []);
      setOrders(ordRes.orders || []);
      setSessions(sessRes || []);
    } catch (err: any) {
      setError(err.message || 'Error fetching paper trading data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPaperTradingData();
  }, [refreshKey]);

  const handleActionClick = (
    type: 'START' | 'PAUSE' | 'RESUME' | 'STOP' | 'CLOSE',
    sessionId: string,
    sessionName: string
  ) => {
    setPendingAction({ type, sessionId, sessionName });
    setModalOpen(true);
  };

  const handleExecuteAction = async () => {
    if (!pendingAction) return;
    const { type, sessionId } = pendingAction;
    setModalOpen(false);
    try {
      if (type === 'START') await api.startPaperSession(sessionId);
      else if (type === 'PAUSE') await api.pausePaperSession(sessionId);
      else if (type === 'RESUME') await api.resumePaperSession(sessionId);
      else if (type === 'STOP') await api.stopPaperSession(sessionId);
      else if (type === 'CLOSE') await api.closePaperSession(sessionId);

      triggerRefresh();
      await loadPaperTradingData();
    } catch (err: any) {
      alert(`Action error: ${err.message}`);
    } finally {
      setPendingAction(null);
    }
  };

  const handleCreateSession = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreatingSession(true);
    try {
      await api.createPaperSession(newSessionName, newSessionCapital);
      triggerRefresh();
      await loadPaperTradingData();
    } catch (err: any) {
      alert(`Session creation error: ${err.message}`);
    } finally {
      setCreatingSession(false);
    }
  };

  if (loading) return <LoadingSpinner message="Retrieving paper trading ledger..." />;
  if (error) return <ErrorAlert message={error} onRetry={loadPaperTradingData} />;

  const totalEquity = account?.total_equity || 1000000;
  const cash = account?.available_cash || 1000000;
  const invested = account?.invested_capital || 0;

  return (
    <div className="space-y-6">
      {/* Top Warning Banner */}
      <div className="p-3 bg-amber-950/40 border border-amber-800/80 rounded-lg flex items-center justify-between text-xs text-amber-300 font-mono">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-400" />
          <span className="font-bold">SIMULATION MODE:</span>
          <span>Zero real-world brokerage or exchange accounts are connected. All orders and capital are purely virtual.</span>
        </div>
        <span className="bg-amber-900/60 px-2 py-0.5 rounded text-[10px] border border-amber-700">M14 ACTIVE</span>
      </div>

      {/* Account KPI Header */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          title="Virtual Account Equity"
          value={`₹${totalEquity.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
          subtitle="Real-time mark to market"
          icon={<Wallet className="w-4 h-4 text-blue-400" />}
        />
        <StatCard
          title="Available Cash"
          value={`₹${cash.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
          subtitle="Virtual Buying Power"
          icon={<Wallet className="w-4 h-4 text-emerald-400" />}
        />
        <StatCard
          title="Invested Capital"
          value={`₹${invested.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
          subtitle={`${positions.length} open positions`}
          icon={<Wallet className="w-4 h-4 text-amber-400" />}
        />
      </div>

      {/* Session Management Section */}
      <div className="terminal-card p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
          <div>
            <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold">
              M14 Registered Trading Sessions ({sessions.length})
            </h3>
            <p className="text-xs text-slate-400">Lifecycle execution controls with strict confirmation verification</p>
          </div>

          {/* Quick Create Session Form */}
          <form onSubmit={handleCreateSession} className="flex items-center gap-2">
            <input
              type="text"
              value={newSessionName}
              onChange={(e) => setNewSessionName(e.target.value)}
              placeholder="Session Name"
              className="bg-[#0B0F19] border border-slate-700 rounded px-2.5 py-1 text-xs font-mono text-slate-100 focus:outline-none"
            />
            <input
              type="number"
              value={newSessionCapital}
              onChange={(e) => setNewSessionCapital(Number(e.target.value))}
              placeholder="Capital"
              className="w-24 bg-[#0B0F19] border border-slate-700 rounded px-2.5 py-1 text-xs font-mono text-slate-100 focus:outline-none hidden sm:block"
            />
            <button
              type="submit"
              disabled={creatingSession}
              className="px-3 py-1 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900 text-white rounded text-xs font-mono font-semibold flex items-center gap-1.5 transition"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              <span>New Session</span>
            </button>
          </form>
        </div>

        {sessions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono text-left">
              <thead className="bg-slate-900/80 text-slate-400 uppercase text-[10px] border-b border-slate-800">
                <tr>
                  <th className="py-2 px-3">Session Name</th>
                  <th className="py-2 px-3">Session ID</th>
                  <th className="py-2 px-3">Status</th>
                  <th className="py-2 px-3">Initial Capital</th>
                  <th className="py-2 px-3">Execution Controls</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {sessions.map((sess) => (
                  <tr key={sess.session_id} className="hover:bg-slate-800/30">
                    <td className="py-2 px-3 font-bold text-slate-100">{sess.session_name}</td>
                    <td className="py-2 px-3 text-slate-400 text-[11px]">{sess.session_id}</td>
                    <td className="py-2 px-3">
                      <StatusBadge status={sess.status} type="session" />
                    </td>
                    <td className="py-2 px-3 text-slate-300">₹{sess.initial_capital.toLocaleString('en-IN')}</td>
                    <td className="py-2 px-3">
                      <div className="flex items-center gap-1.5">
                        {sess.status === 'IDLE' && (
                          <button
                            onClick={() => handleActionClick('START', sess.session_id, sess.session_name)}
                            className="px-2 py-0.5 rounded bg-emerald-600/20 hover:bg-emerald-600/40 text-emerald-300 border border-emerald-600/40 text-[10px] flex items-center gap-1"
                          >
                            <Play className="w-3 h-3" /> Start
                          </button>
                        )}
                        {sess.status === 'RUNNING' && (
                          <button
                            onClick={() => handleActionClick('PAUSE', sess.session_id, sess.session_name)}
                            className="px-2 py-0.5 rounded bg-amber-600/20 hover:bg-amber-600/40 text-amber-300 border border-amber-600/40 text-[10px] flex items-center gap-1"
                          >
                            <Pause className="w-3 h-3" /> Pause
                          </button>
                        )}
                        {sess.status === 'PAUSED' && (
                          <button
                            onClick={() => handleActionClick('RESUME', sess.session_id, sess.session_name)}
                            className="px-2 py-0.5 rounded bg-emerald-600/20 hover:bg-emerald-600/40 text-emerald-300 border border-emerald-600/40 text-[10px] flex items-center gap-1"
                          >
                            <Play className="w-3 h-3" /> Resume
                          </button>
                        )}
                        {(sess.status === 'RUNNING' || sess.status === 'PAUSED') && (
                          <button
                            onClick={() => handleActionClick('STOP', sess.session_id, sess.session_name)}
                            className="px-2 py-0.5 rounded bg-rose-600/20 hover:bg-rose-600/40 text-rose-300 border border-rose-600/40 text-[10px] flex items-center gap-1"
                          >
                            <Square className="w-3 h-3" /> Stop
                          </button>
                        )}
                        {sess.status !== 'CLOSED' && (
                          <button
                            onClick={() => handleActionClick('CLOSE', sess.session_id, sess.session_name)}
                            className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 text-[10px]"
                          >
                            Close
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-6 text-center text-xs text-slate-500 font-mono">
            No active paper trading sessions recorded. Create one above to begin simulated execution.
          </div>
        )}
      </div>

      {/* Orders Ledger */}
      <div className="terminal-card p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <FileSpreadsheet className="w-4 h-4 text-blue-400" />
            <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-bold">
              Recent Virtual Order Executions ({orders.length})
            </h3>
          </div>
          <span className="text-[10px] text-slate-400 font-mono">Chronological Ledger</span>
        </div>

        {orders.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono text-left">
              <thead className="bg-slate-900/80 text-slate-400 uppercase text-[10px] border-b border-slate-800">
                <tr>
                  <th className="py-2 px-3">Order ID</th>
                  <th className="py-2 px-3">Symbol</th>
                  <th className="py-2 px-3">Side</th>
                  <th className="py-2 px-3">Quantity</th>
                  <th className="py-2 px-3">Price</th>
                  <th className="py-2 px-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {orders.map((ord, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/30">
                    <td className="py-2 px-3 text-slate-400">{ord.order_id}</td>
                    <td className="py-2 px-3 font-bold text-slate-100">{ord.symbol}</td>
                    <td
                      className={`py-2 px-3 font-semibold ${
                        ord.side === 'BUY' ? 'text-emerald-400' : 'text-rose-400'
                      }`}
                    >
                      {ord.side}
                    </td>
                    <td className="py-2 px-3 text-slate-300">{ord.quantity}</td>
                    <td className="py-2 px-3 text-slate-100">
                      ₹{ord.execution_price || ord.limit_price || 0}
                    </td>
                    <td className="py-2 px-3">
                      <StatusBadge status={ord.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-6 text-center text-xs text-slate-500 font-mono">
            No virtual orders placed yet in this session.
          </div>
        )}
      </div>

      {/* Confirmation Modal */}
      <ConfirmModal
        isOpen={modalOpen}
        title={`Confirm Session Action: ${pendingAction?.type}`}
        message={`Are you sure you want to ${pendingAction?.type} paper trading session "${pendingAction?.sessionName}"? This state transition will alter simulated order routing.`}
        confirmLabel={`Yes, ${pendingAction?.type}`}
        isDestructive={pendingAction?.type === 'STOP' || pendingAction?.type === 'CLOSE'}
        onConfirm={handleExecuteAction}
        onCancel={() => setModalOpen(false)}
      />
    </div>
  );
};
