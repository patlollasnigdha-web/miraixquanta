// MIRAI Centralized API Client

import {
  SystemHealthReport,
  MarketDataResponse,
  MarketRegimeResponse,
  StockStrengthResponse,
  StockSentimentResponse,
  DecisionResponse,
  PortfolioOptimiseResponse,
  RiskStatusResponse,
  StrategyInfo,
  StrategySignalResponse,
  BacktestRunResponse,
  PaperAccountState,
  PaperPosition,
  PaperOrder,
  PaperSession,
  AssistantChatResponse,
  MonitoringMetrics,
  MonitoringAlert,
  SystemResourceUsage,
} from '../types/api';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), 20000); // 20s timeout

  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    });

    clearTimeout(id);

    if (!res.ok) {
      let detail = `HTTP ${res.status}: ${res.statusText}`;
      try {
        const errJson = await res.json();
        detail = errJson.detail || errJson.message || detail;
      } catch {
        // use default statusText
      }
      throw new Error(detail);
    }

    return await res.json();
  } catch (error: any) {
    clearTimeout(id);
    if (error.name === 'AbortError') {
      throw new Error('Request timed out while connecting to MIRAI backend.');
    }
    throw error;
  }
}

export const api = {
  // Health & System
  getHealth: () => request<SystemHealthReport>('/health'),
  getSystemSummary: () => request<SystemResourceUsage>('/monitoring/system'),
  getMetrics: () => request<MonitoringMetrics>('/monitoring/metrics'),
  getAlerts: () => request<{ alerts: MonitoringAlert[]; count: number }>('/monitoring/alerts'),

  // Market & Regime
  getSymbols: () => request<{ pipeline: string; symbols: string[]; count: number }>('/market/symbols'),
  getMarketData: (symbol: string) => request<MarketDataResponse>(`/market/${symbol}`),
  getMarketRegime: (pipeline: string = 'pipeline_b_nifty') =>
    request<MarketRegimeResponse>(`/market/regime?pipeline=${pipeline}`),

  // Stock Intelligence
  getStockStrength: (symbol: string) => request<StockStrengthResponse>(`/stock/${symbol}/strength`),
  getStockSentiment: (symbol: string) => request<StockSentimentResponse>(`/stock/${symbol}/sentiment`),

  // Investment Decisions
  evaluateDecision: (symbol: string, investmentHorizon: string = '1d', pipelineId: string = 'pipeline_b_nifty') =>
    request<DecisionResponse>('/decisions/evaluate', {
      method: 'POST',
      body: JSON.stringify({
        symbol,
        investment_horizon: investmentHorizon,
        pipeline_id: pipelineId,
      }),
    }),

  // Strategies & Backtesting
  listStrategies: () => request<StrategyInfo[]>('/strategies'),
  evaluateStrategy: (strategyId: string, symbol: string, pipeline: string = 'pipeline_b_nifty') =>
    request<StrategySignalResponse>('/strategies/evaluate', {
      method: 'POST',
      body: JSON.stringify({ strategy_id: strategyId, symbol, pipeline }),
    }),
  runBacktest: (strategyId: string, symbols: string[], initialCapital: number = 1000000) =>
    request<BacktestRunResponse>('/backtesting/run', {
      method: 'POST',
      body: JSON.stringify({ strategy_id: strategyId, symbols, initial_capital: initialCapital }),
    }),

  // Portfolio & Risk
  getPortfolio: () =>
    request<{ account: PaperAccountState; positions: PaperPosition[]; positions_count: number }>('/portfolio'),
  optimisePortfolio: (symbols: string[], method: string = 'risk_budgeting', targetRiskPct: number = 0.15) =>
    request<PortfolioOptimiseResponse>('/portfolio/optimise', {
      method: 'POST',
      body: JSON.stringify({ symbols, method, target_risk_pct: targetRiskPct }),
    }),
  getRiskStatus: () => request<RiskStatusResponse>('/risk/status'),

  // Paper Trading
  getPaperAccount: () => request<PaperAccountState>('/paper-trading/account'),
  getPaperPositions: () => request<{ positions: PaperPosition[]; count: number }>('/paper-trading/positions'),
  getPaperOrders: (limit: number = 50) => request<{ orders: PaperOrder[]; count: number }>(`/paper-trading/orders?limit=${limit}`),
  listPaperSessions: () => request<PaperSession[]>('/paper-trading/sessions'),
  createPaperSession: (sessionName: string, initialCapital: number = 1000000, symbols: string[] = ['TCS']) =>
    request<PaperSession>('/paper-trading/sessions', {
      method: 'POST',
      body: JSON.stringify({
        session_name: sessionName,
        initial_capital: initialCapital,
        symbols,
        mode: 'HISTORICAL_REPLAY',
      }),
    }),
  startPaperSession: (sessionId: string) =>
    request<PaperSession>(`/paper-trading/sessions/${sessionId}/start`, { method: 'POST' }),
  pausePaperSession: (sessionId: string) =>
    request<PaperSession>(`/paper-trading/sessions/${sessionId}/pause`, { method: 'POST' }),
  resumePaperSession: (sessionId: string) =>
    request<PaperSession>(`/paper-trading/sessions/${sessionId}/resume`, { method: 'POST' }),
  stopPaperSession: (sessionId: string) =>
    request<PaperSession>(`/paper-trading/sessions/${sessionId}/stop`, { method: 'POST' }),
  closePaperSession: (sessionId: string) =>
    request<PaperSession>(`/paper-trading/sessions/${sessionId}/close`, { method: 'POST' }),

  // AI Assistant
  askAssistant: (query: string, conversationId?: string) =>
    request<AssistantChatResponse>('/assistant/chat', {
      method: 'POST',
      body: JSON.stringify({ query, conversation_id: conversationId }),
    }),
  resetConversation: (conversationId: string) =>
    request<{ message: string; conversation_id: string }>(`/assistant/conversations/${conversationId}/reset`, {
      method: 'POST',
    }),
};
