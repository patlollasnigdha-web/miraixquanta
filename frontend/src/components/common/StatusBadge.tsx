import React from 'react';

interface StatusBadgeProps {
  status: string;
  type?: 'verdict' | 'circuit' | 'health' | 'session' | 'sentiment' | 'generic';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, type = 'generic' }) => {
  const s = status.toUpperCase();

  let colorClass = 'bg-slate-800 text-slate-300 border-slate-700';

  if (type === 'verdict') {
    switch (s) {
      case 'YES':
        colorClass = 'bg-emerald-950/80 text-emerald-400 border-emerald-700/60 font-semibold';
        break;
      case 'NO':
        colorClass = 'bg-rose-950/80 text-rose-400 border-rose-700/60 font-semibold';
        break;
      case 'WAIT':
        colorClass = 'bg-amber-950/80 text-amber-400 border-amber-700/60 font-semibold';
        break;
      case 'INSUFFICIENT_DATA':
        colorClass = 'bg-slate-900 text-slate-400 border-slate-700';
        break;
    }
  } else if (type === 'circuit') {
    switch (s) {
      case 'NORMAL':
        colorClass = 'bg-emerald-950/60 text-emerald-400 border-emerald-800';
        break;
      case 'CAUTION':
        colorClass = 'bg-amber-950/60 text-amber-400 border-amber-800';
        break;
      case 'RESTRICTED':
        colorClass = 'bg-orange-950/60 text-orange-400 border-orange-800';
        break;
      case 'HALTED':
        colorClass = 'bg-rose-950/80 text-rose-400 border-rose-800 font-bold';
        break;
    }
  } else if (type === 'health') {
    switch (s) {
      case 'HEALTHY':
      case 'ONLINE':
        colorClass = 'bg-emerald-950/60 text-emerald-400 border-emerald-800';
        break;
      case 'DEGRADED':
        colorClass = 'bg-amber-950/60 text-amber-400 border-amber-800';
        break;
      case 'UNHEALTHY':
      case 'OFFLINE':
        colorClass = 'bg-rose-950/60 text-rose-400 border-rose-800';
        break;
    }
  } else if (type === 'session') {
    switch (s) {
      case 'RUNNING':
        colorClass = 'bg-emerald-950/60 text-emerald-400 border-emerald-800 animate-pulse';
        break;
      case 'PAUSED':
        colorClass = 'bg-amber-950/60 text-amber-400 border-amber-800';
        break;
      case 'STOPPED':
      case 'CLOSED':
        colorClass = 'bg-slate-900 text-slate-400 border-slate-700';
        break;
      case 'IDLE':
        colorClass = 'bg-blue-950/60 text-blue-400 border-blue-800';
        break;
    }
  } else if (type === 'sentiment') {
    if (s.includes('POSITIVE') || s.includes('BULLISH')) {
      colorClass = 'bg-emerald-950/60 text-emerald-400 border-emerald-800';
    } else if (s.includes('NEGATIVE') || s.includes('BEARISH')) {
      colorClass = 'bg-rose-950/60 text-rose-400 border-rose-800';
    } else {
      colorClass = 'bg-slate-900 text-slate-400 border-slate-700';
    }
  }

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-mono border ${colorClass}`}
    >
      {status}
    </span>
  );
};
