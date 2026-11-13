import React, { ReactNode } from 'react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  badge?: ReactNode;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  trendValue,
  badge,
}) => {
  return (
    <div className="terminal-card p-4 transition-all duration-150 hover:border-slate-700">
      <div className="flex items-center justify-between text-slate-400 mb-2">
        <span className="text-xs uppercase tracking-wider font-mono font-medium">{title}</span>
        {icon && <div className="text-slate-400">{icon}</div>}
      </div>
      <div className="flex items-baseline justify-between">
        <div className="text-2xl font-bold font-mono text-slate-100 tracking-tight">{value}</div>
        {badge}
      </div>
      {(subtitle || trendValue) && (
        <div className="mt-2 flex items-center gap-2 text-xs">
          {trendValue && (
            <span
              className={`font-mono font-semibold ${
                trend === 'up'
                  ? 'text-emerald-400'
                  : trend === 'down'
                  ? 'text-rose-400'
                  : 'text-slate-400'
              }`}
            >
              {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '•'} {trendValue}
            </span>
          )}
          {subtitle && <span className="text-slate-400 truncate">{subtitle}</span>}
        </div>
      )}
    </div>
  );
};
