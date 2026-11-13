/**
 * MIRAI — Centralized Frontend API Client (M16 & M17)
 * Handles authentication tokens, base URL configuration, request timeouts,
 * response interceptors, and compatibility methods.
 */

import axios, { AxiosInstance } from 'axios';

let configuredApiBase = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '');
if (configuredApiBase.endsWith('/api/v1')) {
  configuredApiBase = configuredApiBase.slice(0, -7);
} else if (configuredApiBase.endsWith('/v1')) {
  configuredApiBase = configuredApiBase.slice(0, -3);
}
configuredApiBase = configuredApiBase.replace(/\/+$/, '');
const baseURL = configuredApiBase ? (configuredApiBase.endsWith('/api') ? configuredApiBase : `${configuredApiBase}/api`) : '/api';

export const api: AxiosInstance & Record<string, any> = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
}) as any;

// Request interceptor: Attach JWT Bearer token
api.interceptors.request.use(config => {
  try {
    const token = localStorage.getItem('mirai_token') || sessionStorage.getItem('mirai_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  } catch {
    // Graceful storage access fallback
  }
  return config;
});

// Response interceptor: Handle 401 unauthorized session expiry
api.interceptors.response.use(
  response => response,
  error => {
    if (error?.response?.status === 401) {
      try {
        if (sessionStorage.getItem('mirai_token') || localStorage.getItem('mirai_token')) {
          sessionStorage.removeItem('mirai_token');
          localStorage.removeItem('mirai_token');
          if (typeof window !== 'undefined') {
            window.dispatchEvent(new Event('mirai:unauthorized'));
          }
        }
      } catch {
        // Safe storage access
      }
    }
    return Promise.reject(error);
  }
);

export type Instrument = {
  symbol: string;
  name: string;
  exchange: string;
  kind: string;
};

export async function loadHistory(symbol: string, period = '1y') {
  return (await api.get('/market/indicators', { params: { symbol, period } })).data;
}

export async function loadOverview(symbol: string, period = '1y') {
  return (await api.get('/market/overview', { params: { symbol, period } })).data;
}

// -------------------------------------------------------------
// BACKWARD-COMPATIBLE API HELPERS (FOR ADVANCED QUANT DASHBOARD)
// -------------------------------------------------------------
api.getHealth = async () => (await api.get('/v1/health')).data;
api.getSystemSummary = async () => (await api.get('/v1/monitoring/summary')).data;
api.getMetrics = async () => (await api.get('/v1/monitoring/metrics')).data;
api.getAlerts = async () => (await api.get('/v1/monitoring/alerts')).data;
api.getSymbols = async (pipeline = 'pipeline_b_nifty') =>
  (await api.get('/v1/market/symbols', { params: { pipeline } })).data;
api.getMarketData = async (symbol = 'TCS', pipeline = 'pipeline_b_nifty', horizon = '1d') =>
  (await api.get('/v1/market/data', { params: { symbol, pipeline, horizon } })).data;
api.getMarketRegime = async (pipeline = 'pipeline_b_nifty') =>
  (await api.get('/v1/market/regime', { params: { pipeline } })).data;
api.getStockStrength = async (pipeline = 'pipeline_b_nifty', top_n = 5) =>
  (await api.get('/v1/stocks/strength', { params: { pipeline, top_n } })).data;
api.getStockSentiment = async (symbol: string) =>
  (await api.get(`/v1/stocks/${symbol}/sentiment`)).data;
api.evaluateDecision = async (symbol: string, pipeline = 'pipeline_b_nifty') =>
  (await api.post('/v1/decisions/evaluate', { symbol, pipeline_id: pipeline })).data;
api.listStrategies = async () => (await api.get('/v1/strategies/list')).data;
api.evaluateStrategy = async (strategy_id: string, symbol: string) =>
  (await api.post('/v1/strategies/evaluate', { strategy_id, symbol })).data;
api.runBacktest = async (payload: any) =>
  (await api.post('/v1/backtest/run', payload)).data;
api.getPortfolio = async () => (await api.get('/portfolio')).data;
api.optimisePortfolio = async (payload: any) =>
  (await api.post('/v1/portfolio/optimise', payload)).data;
api.getRiskStatus = async () => (await api.get('/v1/risk/status')).data;
api.getPaperAccount = async () => (await api.get('/v1/paper-trading/account')).data;
api.getPaperPositions = async () => (await api.get('/v1/paper-trading/positions')).data;
api.getPaperOrders = async () => (await api.get('/v1/paper-trading/orders')).data;
api.listPaperSessions = async () => (await api.get('/v1/paper-trading/sessions')).data;
api.createPaperSession = async (payload: any) =>
  (await api.post('/v1/paper-trading/session/create', payload)).data;
api.startPaperSession = async () => (await api.post('/v1/paper-trading/session/start')).data;
api.pausePaperSession = async () => (await api.post('/v1/paper-trading/session/pause')).data;
api.resumePaperSession = async () => (await api.post('/v1/paper-trading/session/resume')).data;
api.stopPaperSession = async () => (await api.post('/v1/paper-trading/session/stop')).data;
api.closePaperSession = async () => (await api.post('/v1/paper-trading/session/close')).data;
api.askAssistant = async (query: string, symbol?: string) =>
  (await api.post('/v1/assistant/ask', { query, symbol })).data;
api.resetConversation = async () =>
  (await api.post('/v1/assistant/reset')).data;
