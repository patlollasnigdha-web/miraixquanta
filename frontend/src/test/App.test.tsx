import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { App } from '../App';
import { api } from '../services/api';

// Mock all API service methods for deterministic testing
vi.mock('../services/api', () => ({
  api: {
    getHealth: vi.fn(),
    getSystemSummary: vi.fn(),
    getMetrics: vi.fn(),
    getAlerts: vi.fn(),
    getSymbols: vi.fn(),
    getMarketData: vi.fn(),
    getMarketRegime: vi.fn(),
    getStockStrength: vi.fn(),
    getStockSentiment: vi.fn(),
    evaluateDecision: vi.fn(),
    listStrategies: vi.fn(),
    evaluateStrategy: vi.fn(),
    runBacktest: vi.fn(),
    getPortfolio: vi.fn(),
    optimisePortfolio: vi.fn(),
    getRiskStatus: vi.fn(),
    getPaperAccount: vi.fn(),
    getPaperPositions: vi.fn(),
    getPaperOrders: vi.fn(),
    listPaperSessions: vi.fn(),
    createPaperSession: vi.fn(),
    startPaperSession: vi.fn(),
    pausePaperSession: vi.fn(),
    resumePaperSession: vi.fn(),
    stopPaperSession: vi.fn(),
    closePaperSession: vi.fn(),
    askAssistant: vi.fn(),
    resetConversation: vi.fn(),
  },
}));

describe('MIRAI Interactive Dashboard (M17)', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock implementations
    vi.mocked(api.getHealth).mockResolvedValue({
      overall_status: 'HEALTHY',
      version: '1.0.0',
      timestamp: new Date().toISOString(),
      components: {
        database: { status: 'HEALTHY', message: 'SQLite operational' },
        ollama_service: { status: 'HEALTHY', message: 'Ollama connected' },
        model_files: { status: 'HEALTHY', message: 'Models loaded' },
      },
    });

    vi.mocked(api.getSymbols).mockResolvedValue({
      pipeline: 'pipeline_b_nifty',
      symbols: ['TCS', 'INFY', 'RELIANCE', 'HDFCBANK'],
      count: 4,
    });

    vi.mocked(api.getMarketRegime).mockResolvedValue({
      pipeline: 'pipeline_b_nifty',
      detected_regime: 'BULLISH_TRENDING',
      regime_confidence: 0.88,
      regime_probabilities: { BULLISH_TRENDING: 0.88, SIDEWAYS_RANGE_BOUND: 0.12 },
      as_of_date: '2026-11-13',
    });

    vi.mocked(api.getPortfolio).mockResolvedValue({
      account: {
        account_id: 'PAPER_1',
        initial_capital: 1000000,
        available_cash: 850000,
        reserved_cash: 0,
        invested_capital: 150000,
        total_equity: 1025000,
        circuit_breaker_state: 'NORMAL',
      },
      positions: [
        {
          symbol: 'TCS',
          units: 40,
          average_entry_price: 3750,
          current_price: 3820,
          market_value: 152800,
          stop_loss: 3650,
          take_profit: 4000,
        },
      ],
      positions_count: 1,
    });

    vi.mocked(api.evaluateDecision).mockResolvedValue({
      symbol: 'TCS',
      verdict: 'YES',
      display_label: 'Strong Buy',
      composite_score: 82.5,
      confidence: 0.85,
      action_type: 'ENTER_LONG',
      risk_status: 'RISK_APPROVED',
      entry_reference_price: 3820,
      suggested_stop_loss: 3650,
      suggested_take_profit: 4100,
      explanation: 'Robust multi-pillar alignment across momentum and fundamentals.',
      positive_factors: ['Strong momentum expansion', 'Favorable PEG ratio'],
      negative_factors: [],
      conflicting_signals: [],
      warnings: [],
      timestamp: '2026-11-13T10:00:00Z',
    });

    vi.mocked(api.getAlerts).mockResolvedValue({
      alerts: [
        {
          alert_id: 'alt_1',
          severity: 'INFO',
          component: 'SystemMonitor',
          message: 'System nominal',
          acknowledged: false,
          timestamp: new Date().toISOString(),
        },
      ],
      count: 1,
    });

    vi.mocked(api.getStockStrength).mockResolvedValue({
      symbol: 'TCS',
      stock_strength_score: 84.2,
      status: 'Strong',
      factor_scores: {
        momentum: 88.0,
        relative_strength: 82.0,
        volume_confirmation: 80.0,
        trend_quality: 85.0,
        volatility_adjusted_return: 83.0,
        liquidity: 90.0,
      },
      factor_contributions: {
        momentum: 22.0,
        relative_strength: 20.5,
        volume_confirmation: 16.0,
        trend_quality: 17.0,
        volatility_adjusted_return: 12.5,
        liquidity: 9.0,
      },
      confidence: 0.86,
      as_of_date: '2026-11-13',
    });

    vi.mocked(api.getStockSentiment).mockResolvedValue({
      symbol: 'TCS',
      sentiment_score: 0.45,
      sentiment_label: 'BULLISH',
      sentiment_confidence: 0.82,
      news_count: 12,
      fundamental_score: 81.0,
      fundamental_classification: 'Strong Valuation',
      recent_headlines: ['TCS secures major multi-year digital transformation deal.'],
      as_of_date: '2026-11-13',
    });

    vi.mocked(api.getRiskStatus).mockResolvedValue({
      circuit_breaker_state: 'NORMAL',
      max_drawdown_limit_pct: 15.0,
      max_position_size_pct: 20.0,
      cash_reserve_required_pct: 5.0,
      status_message: 'M11 Dynamic Risk Management Active.',
      timestamp: new Date().toISOString(),
    });

    vi.mocked(api.listStrategies).mockResolvedValue([
      {
        name: 'Adaptive Momentum Strategy',
        strategy_id: 'MOMENTUM_STRATEGY',
        description: 'Trend expansion with EMA and ATR',
        supported_pipelines: ['pipeline_b_nifty'],
      },
    ]);

    vi.mocked(api.runBacktest).mockResolvedValue({
      backtest_id: 'BT_TEST_1',
      status: 'COMPLETED',
      metrics: {
        cagr: 0.185,
        total_return: 0.24,
        sharpe_ratio: 1.62,
        max_drawdown: 0.075,
        win_rate: 0.61,
        total_trades: 38,
      },
      timestamp: new Date().toISOString(),
    });

    vi.mocked(api.getPaperAccount).mockResolvedValue({
      account_id: 'DEFAULT_ACC',
      initial_capital: 1000000,
      available_cash: 850000,
      reserved_cash: 0,
      invested_capital: 150000,
      total_equity: 1025000,
    });

    vi.mocked(api.getPaperPositions).mockResolvedValue({
      positions: [
        {
          symbol: 'TCS',
          units: 40,
          average_entry_price: 3750,
          current_price: 3820,
          market_value: 152800,
        },
      ],
      count: 1,
    });

    vi.mocked(api.getPaperOrders).mockResolvedValue({
      orders: [
        {
          order_id: 'ORD_101',
          symbol: 'TCS',
          side: 'BUY',
          order_type: 'MARKET',
          quantity: 40,
          execution_price: 3750,
          status: 'FILLED',
        },
      ],
      count: 1,
    });

    vi.mocked(api.listPaperSessions).mockResolvedValue([
      {
        session_id: 'SESS_1',
        session_name: 'TestLiveSim',
        status: 'RUNNING',
        mode: 'HISTORICAL_REPLAY',
        initial_capital: 1000000,
        symbols: ['TCS'],
        start_time: '2026-11-13T09:15:00Z',
        end_time: null,
      },
    ]);

    vi.mocked(api.getSystemSummary).mockResolvedValue({
      cpu_percent: 22.5,
      memory_used_mb: 4096,
      memory_total_mb: 16384,
      memory_percent: 25.0,
      disk_used_gb: 120,
      disk_total_gb: 512,
      disk_percent: 23.4,
      timestamp: new Date().toISOString(),
    });

    vi.mocked(api.getMetrics).mockResolvedValue({
      timestamp: new Date().toISOString(),
      counters: { api_requests_total: 124 },
      gauges: { app_status: 1.0 },
      latencies: {
        api_request_duration_ms: { count: 124, mean: 4.8, p50: 3.9, p95: 11.2, p99: 18.0 },
      },
      error_rates: { general_error_rate: 0.0 },
    });
  });

  // 1. Application Startup & Brand Identity
  it('renders application startup header with MIRAI branding and status pills', async () => {
    render(<App />);
    expect(screen.getByText('MIRAI')).toBeInTheDocument();
    expect(screen.getByText('QUANT X')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText('BULLISH_TRENDING')).toBeInTheDocument();
    });
  });

  // 2. Sidebar Navigation
  it('navigates across sidebar modules cleanly', async () => {
    render(<App />);
    const decisionNav = screen.getByRole('button', { name: /decision explorer/i });
    fireEvent.click(decisionNav);

    await waitFor(() => {
      expect(screen.getByText(/M09 Authoritative Investment Decision Engine/i)).toBeInTheDocument();
    });

    const assistantNav = screen.getByRole('button', { name: /ai assistant/i });
    fireEvent.click(assistantNav);

    await waitFor(() => {
      expect(screen.getByText(/MIRAI Quantitative Copilot/i)).toBeInTheDocument();
    });
  });

  // 3. Overview Page Rendering
  it('renders overview KPIs with actual backend account data', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText('BULLISH_TRENDING')).toBeInTheDocument();
      expect(screen.getByText('₹10,25,000')).toBeInTheDocument();
      expect(screen.getByText('₹8,50,000')).toBeInTheDocument();
    });
  });

  // 4. Stock Intelligence Rendering
  it('renders stock intelligence factor breakdowns and score', async () => {
    render(<App />);
    const stocksNav = screen.getByRole('button', { name: /stock intelligence/i });
    fireEvent.click(stocksNav);

    await waitFor(() => {
      expect(screen.getByText('84.2 / 100')).toBeInTheDocument();
      expect(screen.getByText(/M05 Multi-Pillar Factor Breakdown/i)).toBeInTheDocument();
      expect(screen.getAllByText(/BULLISH/i).length).toBeGreaterThan(0);
    });
  });

  // 5. Decision Verdict Rendering
  it('renders authoritative M09 decision verdict and explanation', async () => {
    render(<App />);
    const decisionNav = screen.getByRole('button', { name: /decision explorer/i });
    fireEvent.click(decisionNav);

    const evaluateBtn = await screen.findByRole('button', { name: /generate decision/i });
    fireEvent.click(evaluateBtn);

    await waitFor(() => {
      expect(screen.getByText('YES')).toBeInTheDocument();
      expect(screen.getByText(/Strong Buy/i)).toBeInTheDocument();
      expect(screen.getByText(/Strong momentum expansion/i)).toBeInTheDocument();
      expect(screen.getByText(/RISK_APPROVED/i)).toBeInTheDocument();
    });
  });

  // 6. Chatbot Interaction
  it('sends query and renders assistant response with disclaimers', async () => {
    vi.mocked(api.askAssistant).mockResolvedValue({
      message: 'TCS indicates strong momentum expansion with an approved YES verdict.',
      conversation_id: 'conv_test_1',
      intent: 'INVESTMENT_DECISION',
      tools_called: ['get_investment_decision'],
      verdict: 'YES',
      disclaimer: 'Trading financial markets involves substantial risk of loss.',
      timestamp: new Date().toISOString(),
    });

    render(<App />);
    const assistantNav = screen.getByRole('button', { name: /ai assistant/i });
    fireEvent.click(assistantNav);

    const input = await screen.findByPlaceholderText(/ask about stock strength/i);
    fireEvent.change(input, { target: { value: 'Should I invest in TCS?' } });

    const sendBtn = screen.getByRole('button', { name: /send/i });
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(screen.getByText(/TCS indicates strong momentum expansion/i)).toBeInTheDocument();
      expect(screen.getByText('get_investment_decision')).toBeInTheDocument();
    });
  });

  // 7. Portfolio & Optimisation Data Display
  it('displays portfolio holdings and allows running M10 optimisation', async () => {
    vi.mocked(api.optimisePortfolio).mockResolvedValue({
      method: 'risk_budgeting',
      weights: { TCS: 0.35, INFY: 0.25, RELIANCE: 0.40 },
      expected_annual_return_pct: 14.8,
      annual_volatility_pct: 12.2,
      sharpe_ratio: 1.21,
      diversification_score: 0.82,
      timestamp: new Date().toISOString(),
    });

    render(<App />);
    const portfolioNav = screen.getByRole('button', { name: /^portfolio$/i });
    fireEvent.click(portfolioNav);

    await waitFor(() => {
      expect(screen.getByText('₹10,25,000')).toBeInTheDocument();
    });

    const optBtn = screen.getByRole('button', { name: /calculate optimal weights/i });
    fireEvent.click(optBtn);

    await waitFor(() => {
      expect(screen.getByText('14.80% p.a.')).toBeInTheDocument();
      expect(screen.getByText('1.21')).toBeInTheDocument();
    });
  });

  // 8. Risk Management Controls Display
  it('displays dynamic risk limits and circuit breaker state', async () => {
    render(<App />);
    const riskNav = screen.getByRole('button', { name: /risk controls/i });
    fireEvent.click(riskNav);

    await waitFor(() => {
      expect(screen.getByText('Circuit Breaker: NORMAL')).toBeInTheDocument();
      expect(screen.getByText('15.0%')).toBeInTheDocument();
      expect(screen.getByText('20.0%')).toBeInTheDocument();
    });
  });

  // 9. Backtesting Configuration and Execution
  it('configures and executes historical backtesting simulation', async () => {
    render(<App />);
    const backtestNav = screen.getByRole('button', { name: /strategy & backtest/i });
    fireEvent.click(backtestNav);

    const runBtn = await screen.findByRole('button', { name: /run backtest/i });
    fireEvent.click(runBtn);

    await waitFor(() => {
      expect(screen.getByText('24.00%')).toBeInTheDocument();
      expect(screen.getByText('1.62')).toBeInTheDocument();
      expect(screen.getByText('61.0%')).toBeInTheDocument();
    });
  });

  // 10. Paper Trading Session Controls & State Confirmation Modal
  it('opens confirmation modal before executing state changes', async () => {
    render(<App />);
    const paperNav = screen.getByRole('button', { name: /paper trading/i });
    fireEvent.click(paperNav);

    await waitFor(() => {
      expect(screen.getByText('TestLiveSim')).toBeInTheDocument();
    });

    const pauseBtn = screen.getByRole('button', { name: /pause/i });
    fireEvent.click(pauseBtn);

    // Confirmation modal should appear
    await waitFor(() => {
      expect(screen.getByText(/Confirm Session Action: PAUSE/i)).toBeInTheDocument();
    });

    const confirmBtn = screen.getByRole('button', { name: /yes, pause/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(api.pausePaperSession).toHaveBeenCalledWith('SESS_1');
    });
  });

  // 11. System Monitoring Telemetry
  it('displays hardware and operational telemetry', async () => {
    render(<App />);
    const monNav = screen.getByRole('button', { name: /system health/i });
    fireEvent.click(monNav);

    await waitFor(() => {
      expect(screen.getByText('124')).toBeInTheDocument();
      expect(screen.getByText('4.8 ms')).toBeInTheDocument();
      expect(screen.getByText('22.5%')).toBeInTheDocument();
    });
  });
});
