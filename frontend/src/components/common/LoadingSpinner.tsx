import React from 'react';

export const LoadingSpinner: React.FC<{ message?: string }> = ({
  message = 'Fetching algorithmic data...',
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-slate-400 gap-3">
      <div className="w-8 h-8 border-2 border-slate-700 border-t-blue-500 rounded-full animate-spin" />
      <span className="text-xs font-mono">{message}</span>
    </div>
  );
};

export const ErrorAlert: React.FC<{ message: string; onRetry?: () => void }> = ({
  message,
  onRetry,
}) => {
  return (
    <div className="terminal-card bg-rose-950/30 border-rose-800/80 p-4 rounded-lg text-rose-300 text-xs flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className="text-rose-400 font-bold">ERR:</span>
        <span>{message}</span>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-2.5 py-1 bg-rose-900/60 hover:bg-rose-900 border border-rose-700 rounded text-rose-200 transition font-mono"
        >
          Retry
        </button>
      )}
    </div>
  );
};
