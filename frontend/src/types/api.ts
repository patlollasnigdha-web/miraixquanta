// MIRAI Frontend — TypeScript API Schemas

export interface SystemHealthReport {
  overall_status: 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY';
  version: string;
  timestamp: string;
  components: {
    [key: string]: {
      status: 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY';
      message?: string;
      details?: Record<string, any>;
    };
  };
}

export interface MarketDataResponse {
  symbol: string;
  bars_count: number;
  latest_bar: Record<string, number | string>;
  source_timestamp: string;
  pipeline: string;
}

export interface MarketRegimeResponse {
  pipeline: string;
  detected_regime: string;
  regime_confidence: number;
  regime_probabilities: Record<string, number>;
  quantitative_evidence?: Record<string, number>;
  as_of_date: string;
}

export interface StockStrengthResponse {
  symbol: string;
  stock_strength_score: number;
  status: string;
  factor_scores: Record<string, number>;
  factor_contributions: Record<string, number>;
  confidence: number;
  as_of_date: string;
}

export interface StockSentimentResponse {
  symbol: string;
  sentiment_score: number;
  sentiment_label: string;
  sentiment_confidence: number;
  news_count: number;
  fundamental_score: number | null;
  fundamental_classification: string | null;
  recent_headlines: string[];
  as_of_date: string;
}

export interface DecisionResponse {
  symbol: string;
  verdict: 'YES' | 'NO' | 'WAIT' | 'INSUFFICIENT_DATA';
  display_label: string;
  composite_score: number | null;
  confidence: number;
  action_type: string;
  risk_status: string;
  entry_reference_price: number | null;
  suggested_stop_loss: number | null;
  suggested_take_profit: number | null;
  explanation: string;
  positive_factors: string[];
  negative_factors: string[];
  conflicting_signals: string[];
  warnings: string[];
  timestamp: string;
}

export interface PortfolioOptimiseResponse {
  method: string;
  weights: Record<string, number>;
  expected_annual_return_pct: number;
  annual_volatility_pct: number;
  sharpe_ratio: number;
  diversification_score: number;
  timestamp: string;
}

export interface RiskStatusResponse {
  circuit_breaker_state: 'NORMAL' | 'CAUTION' | 'RESTRICTED' | 'HALTED';
  max_drawdown_limit_pct: number;
  max_position_size_pct: number;
  cash_reserve_required_pct: number;
  status_message: string;
  timestamp: string;
}

export interface StrategyInfo {
  name: string;
  strategy_id: string;
  description: string;
  supported_pipelines: string[];
}

export interface StrategySignalResponse {
  symbol: string;
  strategy_name: string;
  signal: string;
  signal_strength: number;
  suggested_stop_loss: number | null;
  suggested_take_profit: number | null;
  timestamp: string;
}

export interface BacktestRunResponse {
  backtest_id: string;
  status: string;
  metrics: {
    cagr?: number;
    annualized_return?: number;
    total_return?: number;
    sharpe_ratio?: number;
    sortino_ratio?: number;
    max_drawdown?: number;
    win_rate?: number;
    profit_factor?: number;
    total_trades?: number;
    trades_count?: number;
    transaction_costs?: number;
    [key: string]: any;
  };
  timestamp: string;
}

export interface PaperAccountState {
  account_id: string;
  initial_capital: number;
  available_cash: number;
  reserved_cash: number;
  invested_capital: number;
  total_equity: number;
  circuit_breaker_state?: string;
  message?: string;
}

export interface PaperPosition {
  symbol: string;
  units: number;
  average_entry_price: number;
  current_price: number;
  market_value: number;
  stop_loss?: number;
  take_profit?: number;
}

export interface PaperOrder {
  order_id: string;
  session_id?: string;
  symbol: string;
  side: string;
  order_type: string;
  quantity: number;
  limit_price?: number;
  execution_price?: number;
  status: string;
  rejection_reason?: string;
  created_at?: string;
}

export interface PaperSession {
  session_id: string;
  session_name: string;
  status: 'IDLE' | 'RUNNING' | 'PAUSED' | 'STOPPED' | 'CLOSED';
  mode: string;
  initial_capital: number;
  symbols: string[];
  start_time: string | null;
  end_time: string | null;
}

export interface AssistantChatResponse {
  message: string;
  conversation_id: string;
  intent?: string;
  tools_called: string[];
  verdict?: string;
  confidence?: number;
  disclaimer: string;
  timestamp: string;
}

export interface MonitoringMetrics {
  timestamp: string;
  counters: Record<string, number>;
  gauges: Record<string, number>;
  latencies: Record<string, { count: number; mean: number; p50: number; p95: number; p99: number }>;
  error_rates: Record<string, number>;
}

export interface MonitoringAlert {
  alert_id: string;
  severity: 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
  component: string;
  message: string;
  acknowledged: boolean;
  timestamp: string;
}

export interface SystemResourceUsage {
  cpu_percent: number;
  memory_used_mb: number;
  memory_total_mb: number;
  memory_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  disk_percent: number;
  timestamp: string;
}
