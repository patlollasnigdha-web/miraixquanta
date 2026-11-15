/**
 * MIRAI — Frontend Integration Tests (M16 & M17)
 * Verifies all teammate pages, routing, authentication, market data display,
 * portfolio tracking, and AI assistant chat interaction.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from '../context/AuthContext';
import { LoginPage, SignupPage, WatchlistPage } from '../pages/AuthPages';
import { Dashboard, Markets, Regimes, Strategies, Backtest, Assistant } from '../pages/Pages';
import Portfolio from '../pages/PortfolioPage';
import { api } from '../services/api';

vi.mock('../services/api', async () => {
  const actual = await vi.importActual<any>('../services/api');
  return {
    ...actual,
    api: {
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn(),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    },
    loadHistory: vi.fn(),
    loadOverview: vi.fn(),
  };
});

describe('MIRAI Frontend-Backend Integration Pages', () => {
  beforeEach(async () => {
    vi.clearAllMocks();

    // Default mock responses matching real backend schemas
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === '/market/instruments') {
        return {
          data: [
            { symbol: '^NSEI', name: 'NIFTY 50', exchange: 'NSE', kind: 'index' },
            { symbol: 'RELIANCE', name: 'Reliance Industries Ltd.', exchange: 'NSE', kind: 'equity' },
            { symbol: 'TCS', name: 'Tata Consultancy Services', exchange: 'NSE', kind: 'equity' },
          ],
        };
      }
      if (url === '/portfolio') {
        return {
          data: {
            available: true,
            price_available: true,
            total_value: 145880.0,
            total_invested: 135000.0,
            profit_loss: 10880.0,
            return_pct: 0.0805,
            stocks_held: 1,
            positions: [{ symbol: 'RELIANCE', allocation: 1.0 }],
            holdings: [
              {
                id: 1,
                name: 'Reliance Industries Ltd.',
                symbol: 'RELIANCE',
                quantity: 100,
                purchase_price: 1350.0,
                current_price: 1458.8,
                investment: 135000.0,
                current_value: 145880.0,
                profit_loss: 10880.0,
                return_pct: 0.0805,
                price_available: true,
                price_source: 'historical · NIFTY 50 dataset',
              },
            ],
          },
        };
      }
      if (url === '/portfolio/performance') {
        return {
          data: {
            available: true,
            data: [{ date: '2026-01-14', value: 145880.0 }],
          },
        };
      }
      if (url === '/portfolio/risk') {
        return {
          data: {
            available: true,
            risk: {
              annualized_volatility: 0.198,
              sharpe: 0.586,
              max_drawdown: -0.121,
              var_95: -0.015,
            },
            beta: 1.04,
          },
        };
      }
      if (url === '/watchlist') {
        return {
          data: [
            {
              id: 101,
              symbol: 'TCS',
              name: 'Tata Consultancy Services',
              exchange: 'NSE',
              price: 3820.0,
              change: 0.012,
              source: 'historical · NIFTY 50 dataset',
              simulated: false,
            },
          ],
        };
      }
      if (url === '/strategies') {
        return {
          data: {
            data: [
              {
                id: 'ma_crossover',
                name: 'Moving Average Crossover',
                risk: 'Moderate',
                description: '10/30 SMA crossover with next-session execution.',
                metrics: {
                  cagr: 0.175,
                  sharpe: 1.45,
                  sortino: 1.82,
                  max_drawdown: -0.11,
                  win_rate: 0.58,
                  total_trades: 24,
                },
              },
            ],
          },
        };
      }
      return { data: {} };
    });

    const { loadOverview, loadHistory } = vi.mocked(await import('../services/api'));
    loadOverview.mockResolvedValue({
      symbol: '^NSEI',
      instrument: 'NIFTY 50',
      price: 24350.5,
      change: 0.0065,
      rsi: 54.2,
      adx: 24.1,
      volatility: 0.155,
      regime: {
        regime: 'Bullish trending',
        confidence: 0.78,
        explanation: 'Strong directional trend with positive 20-session slope.',
        supporting_indicators: { adx_14: 24.1, rsi_14: 54.2 },
      },
      active_signal: {
        strategy: 'Moving Average Crossover',
        signal: 'BUY',
        position: 'LONG',
      },
      risk: {
        max_drawdown: -0.085,
        var_95: -0.012,
        cvar_95: -0.018,
        cagr: 0.142,
        sharpe: 1.25,
      },
      source: 'historical · NIFTY 50 dataset',
      simulated: false,
    });

    loadHistory.mockResolvedValue({
      data: [
        {
          date: '2026-01-14',
          close: 24350.5,
          sma_20: 24100.0,
          rsi: 54.2,
          macd: 45.2,
          macd_signal: 38.1,
          adx: 24.1,
          volatility: 0.155,
        },
      ],
    });
  });

  // 1. Login Page
  it('renders Login page and triggers authentication submission', async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: {
        access_token: 'mock_jwt_token',
        user: { id: 1, full_name: 'Test Trader', email: 'trader@mirai.org', username: 'trader' },
      },
    });

    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(screen.getByText('Welcome back')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('you@example.com')).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText('you@example.com'), {
      target: { value: 'trader@mirai.org' },
    });
    fireEvent.change(screen.getByPlaceholderText('Enter your password'), {
      target: { value: 'Password123' },
    });

    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/auth/login', {
        email: 'trader@mirai.org',
        password: 'Password123',
        remember_me: true,
      });
    });
  });

  // 2. Signup Page
  it('renders Signup page with input validations', async () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <SignupPage />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(screen.getByText('Create your account')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Choose a username')).toBeInTheDocument();
  });

  // 3. Dashboard Page
  it('renders Dashboard with market KPIs, regime, and real prices', async () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <Dashboard />
        </AuthProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Market dashboard')).toBeInTheDocument();
      expect(screen.getAllByText('Bullish trending').length).toBeGreaterThan(0);
      expect(screen.getByText(/24,350/)).toBeInTheDocument();
    });
  });

  // 4. Markets Page
  it('renders Markets page with technical indicators and instrument selector', async () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <Markets />
        </AuthProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Market intelligence')).toBeInTheDocument();
      expect(screen.getByText('Indicator monitor')).toBeInTheDocument();
    });
  });

  // 5. Regimes Page
  it('renders Regimes page with quantitative explanation', async () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <Regimes />
        </AuthProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Market regimes')).toBeInTheDocument();
      expect(screen.getByText('CURRENT CLASSIFICATION')).toBeInTheDocument();
    });
  });

  // 6. Strategies Page
  it('renders Strategy discovery table with metrics', async () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <Strategies />
        </AuthProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Strategy discovery')).toBeInTheDocument();
      expect(screen.getByText('Moving Average Crossover')).toBeInTheDocument();
      expect(screen.getByText('1.45')).toBeInTheDocument();
    });
  });

  // 7. Backtest Lab Page
  it('renders Backtesting lab with configurable inputs', async () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <Backtest />
        </AuthProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Backtesting lab')).toBeInTheDocument();
      expect(screen.getByText('Strategy')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /run backtest/i })).toBeInTheDocument();
    });
  });

  // 8. Portfolio Page
  it('renders Portfolio holdings, allocation, and risk estimates', async () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <Portfolio />
        </AuthProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('My portfolio')).toBeInTheDocument();
      expect(screen.getByText('Reliance Industries Ltd.')).toBeInTheDocument();
      expect(screen.getAllByText(/1,45,880/).length).toBeGreaterThan(0);
    });
  });

  // 9. Watchlist Page
  it('renders Watchlist instruments and allows tracking', async () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <WatchlistPage />
        </AuthProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Watchlist')).toBeInTheDocument();
      expect(screen.getAllByText('Tata Consultancy Services').length).toBeGreaterThan(0);
      expect(screen.getAllByText(/3,820/).length).toBeGreaterThan(0);
    });
  });

  // 10. AI Assistant Chat
  it('renders AI Assistant chat and sends question to backend', async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: {
        answer: 'The current regime is Bullish trending with positive momentum.',
        provider: 'ollama',
      },
    });

    render(
      <MemoryRouter>
        <AuthProvider>
          <Assistant />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(screen.getByText('MIRAI Intelligence')).toBeInTheDocument();
    const input = screen.getByPlaceholderText('Ask a research question…');
    fireEvent.change(input, { target: { value: 'Explain current market regime' } });

    const sendBtn = screen.getByRole('button', { name: '' });
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/ai/chat', {
        question: 'Explain current market regime',
        symbol: '^NSEI',
      });
    });
  });
});
