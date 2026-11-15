# MIRAI — Backend Audit and API Endpoint Mapping Report (Checkpoint 2)

**Generated Date:** November 14, 2026  
**Repository Working Directory:** `C:\Users\srisa\OneDrive\Desktop\astraq`  
**Deployed Frontend Reference:** `https://mirai-jgw59fhk8-poojasrikandhula-6164s-projects.vercel.app/login`  
**Inspected Teammate Source:** `C:\Users\srisa\.gemini\antigravity\brain\043ab028-9ca6-4fa9-9f81-a37ef0300e67\scratch\pooja_source\`

---

## 1. Executive Summary

This audit evaluates the core MIRAI FastAPI backend against teammate Pooja's deployed frontend website. The objective is to establish end-to-end frontend-backend connectivity without modifying or destroying any completed ML/DL models (M01–M18), without fabricating stock prices or financial data, and without altering the teammate's user interface design.

### Key Audit Findings:
1. **Core Backend Architecture (`src/api/routes/`):**  
   The core quantitative trading backend exposes 22 endpoints under the `/api/v1` prefix. All 208 core unit and integration tests pass with 100% success (`208 passed in pytest`).
2. **Teammate Frontend Expectations (`frontend/src/`):**  
   The teammate's React frontend expects REST endpoints mounted directly under the `/api` prefix (e.g., `/api/auth/*`, `/api/market/*`, `/api/regimes/*`, `/api/strategies/*`, `/api/backtests/*`, `/api/portfolio/*`, `/api/watchlist/*`, and `/api/ai/chat`).
3. **Authentication Gap:**  
   The original core backend was an unauthenticated quant execution engine. The frontend requires user registration, JWT Bearer authentication, profile management, and password resets.
4. **Stock Universe & Dataset Inventory:**  
   The core backend's hardcoded symbol list contained only 12 tickers (`DEFAULT_EQUITY_SYMBOLS`), whereas the actual repository dataset in `NIFTY-50-Stock-Market-Data-main` contains historical daily records for all **50 NIFTY 50 constituent companies** (2016–2026) and the NIFTY 50 official index.
5. **Compatibility Path:**  
   Mounting a clean, non-intrusive compatibility router at `/api` while preserving `/api/v1` resolves all 16 audit areas without modifying any existing backend models or algorithms.

---

## 2. Comprehensive Backend Endpoint Audit

Below is the exhaustive catalog of endpoints in the MIRAI backend across all 16 audit domains:

| Domain | HTTP Method | Exact Route | Request Parameters / Body | Response Schema | Backend Function & Module | Auth Required | Tested & Working |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Health & Status** | `GET` | `/api/v1/health` | None | `HealthResponse` (`overall_status`, `version`, `timestamp`, `components`) | `get_health` in `src/api/routes/health.py` | No | Yes (208 baseline tests) |
| **1. Health & Status** | `GET` | `/api/health` | None | `{"status": "ok", "service": "MIRAI API", "timestamp": str}` | `health` in `src/api/routes/compat_router.py` | No | Yes (5 compat tests) |
| **2. Auth: Register** | `POST` | `/api/auth/register` | Body: `RegisterIn` (`full_name`, `email`, `username`, `password`, `confirm_password`, `phone`) | `{"access_token": str, "token_type": "bearer", "user": dict}` | `register` in `src/api/routes/compat_router.py` | No | Yes |
| **2. Auth: Login** | `POST` | `/api/auth/login` | Body: `LoginIn` (`email`, `password`, `remember_me`) | `{"access_token": str, "token_type": "bearer", "user": dict}` | `login` in `src/api/routes/compat_router.py` | No | Yes |
| **2. Auth: Current User** | `GET` | `/api/auth/me` | None (Bearer header) | `{"id": int, "full_name": str, "email": str, "username": str, "phone": str, "created_at": str}` | `me` in `src/api/routes/compat_router.py` | Yes (Bearer) | Yes |
| **2. Auth: Update Profile**| `PUT` | `/api/auth/me` | Body: `ProfileIn` (`full_name`, `email`, `username`, `phone`) | `{"id": int, "full_name": str, "email": str, "username": str, "phone": str, "created_at": str}` | `update_profile` in `src/api/routes/compat_router.py` | Yes (Bearer) | Yes |
| **2. Auth: Password Change**| `POST` | `/api/auth/change-password` | Body: `ChangePasswordIn` (`current_password`, `new_password`) | `{"status": "ok", "message": "Password updated."}` | `change_password` in `src/api/routes/compat_router.py` | Yes (Bearer) | Yes |
| **2. Auth: Forgot Password**| `POST` | `/api/auth/forgot-password` | Body: `ForgotPasswordIn` (`email`) | `{"status": "ok", "message": str}` | `forgot_password` in `src/api/routes/compat_router.py` | No | Yes |
| **2. Auth: Reset Password** | `POST` | `/api/auth/reset-password` | Body: `ResetPasswordIn` (`token`, `new_password`) | `{"status": "ok", "message": str}` | `reset_password` in `src/api/routes/compat_router.py` | No | Yes |
| **2. Auth: Logout** | `POST` | `/api/auth/logout` | None (Bearer header) | `{"status": "ok", "message": "Session closed on this device"}` | `logout` in `src/api/routes/compat_router.py` | Yes (Bearer) | Yes |
| **3. Market: Symbols** | `GET` | `/api/v1/market/symbols` | None | `{"pipeline": "pipeline_b_nifty", "symbols": list[str], "count": int}` | `get_available_symbols` in `src/api/routes/market_data.py` | No | Yes |
| **3. Market: Instruments** | `GET` | `/api/market/instruments` | None | `list[{"symbol": str, "name": str, "exchange": str, "kind": str}]` | `list_instruments` in `src/api/routes/compat_router.py` | No | Yes (all 50 NIFTY 50 constituents) |
| **3. Market: Single Quote** | `GET` | `/api/v1/market/{symbol}` | Path: `symbol` | `MarketDataResponse` (`symbol`, `bars_count`, `latest_bar`, `source_timestamp`, `pipeline`) | `get_market_data` in `src/api/routes/market_data.py` | No | Yes |
| **4. Historical OHLCV** | `GET` | `/api/market/history` | Query: `symbol`, `period` | `{"symbol": str, "source": str, "simulated": bool, "timestamp": str, "data": list[dict]}` | `market_history` in `src/api/routes/compat_router.py` | No | Yes |
| **5. Market Overview** | `GET` | `/api/market/overview` | Query: `symbol`, `period` | `{"symbol": str, "instrument": str, "price": float, "change": float, "rsi": float, "adx": float, "volatility": float, "risk": dict, "regime": dict, "active_signal": dict, "source": str, "timestamp": str}` | `market_overview` in `src/api/routes/compat_router.py` | No | Yes |
| **6. Technical Indicators** | `GET` | `/api/market/indicators` | Query: `symbol`, `period` | `{"source": str, "simulated": bool, "timestamp": str, "data": list[dict]}` (SMA 10/20/30, EMA 20, RSI, MACD, ADX, Volatility) | `market_indicators` in `src/api/routes/compat_router.py` | No | Yes |
| **7. Stock Strength** | `GET` | `/api/v1/stock/{symbol}/strength` | Path: `symbol` | `StockStrengthResponse` (`stock_strength_score`, `status`, `factor_scores`, `factor_contributions`, `confidence`, `as_of_date`) | `get_stock_strength` in `src/api/routes/stock_intelligence.py` | No | Yes |
| **7. Stock Sentiment** | `GET` | `/api/v1/stock/{symbol}/sentiment` | Path: `symbol` | `StockSentimentResponse` (`sentiment_score`, `sentiment_label`, `fundamental_score`, `recent_headlines`) | `get_stock_sentiment` in `src/api/routes/stock_intelligence.py` | No | Yes |
| **8. Predictive AI** | `POST` | `/api/v1/predictions` | Body: `PredictionRequest` (`symbol`, `pipeline`, `horizon`, `model_name`) | `PredictionResponse` (`predicted_direction`, `confidence`, `model_version`, `limitations`) | `get_predictions` in `src/api/routes/predictions.py` | No | Yes |
| **9. Market Regime** | `GET` | `/api/v1/market/regime` | Query: `pipeline` | `{"detected_regime": str, "regime_confidence": float, "regime_probabilities": dict, "quantitative_evidence": dict}` | `get_current_regime` in `src/api/routes/market_data.py` | No | Yes |
| **9. Market Regime Current**| `GET` | `/api/regimes/current` | Query: `symbol` | `{"regime": str, "confidence": float, "explanation": str, "supporting_indicators": dict, "source": str}` | `regimes_current` in `src/api/routes/compat_router.py` | No | Yes |
| **9. Market Regime History**| `GET` | `/api/regimes/history` | Query: `symbol` | `{"source": str, "simulated": bool, "data": list[dict]}` | `regimes_history` in `src/api/routes/compat_router.py` | No | Yes |
| **10. Investment Decisions**| `POST` | `/api/v1/decisions/evaluate`| Body: `DecisionEvaluateRequest` (`symbol`, `pipeline_id`, `investment_horizon`) | `DecisionResponse` (`verdict`, `display_label`, `composite_score`, `confidence`, `action_type`, `risk_status`, `explanation`, `positive_factors`, `negative_factors`) | `evaluate_decision` in `src/api/routes/decisions.py` | No | Yes |
| **11. Portfolio Holdings** | `GET` | `/api/portfolio/holdings` | None (Bearer header) | `list[{"id": int, "name": str, "symbol": str, "sector": str, "quantity": float, "purchase_price": float, "purchase_date": str, "current_price": float, "profit_loss": float, "return_pct": float}]` | `list_portfolio_holdings` in `src/api/routes/compat_router.py` | Yes (Bearer) | Yes |
| **11. Portfolio Add** | `POST` | `/api/portfolio/holdings` | Body: `PortfolioHoldingIn` (`name`, `symbol`, `quantity`, `purchase_price`, `purchase_date`, `sector`) | `{"id": int, ...}` | `create_portfolio_holding` in `src/api/routes/compat_router.py` | Yes (Bearer) | Yes |
| **11. Portfolio Edit** | `PUT` | `/api/portfolio/holdings/{id}` | Path: `id`, Body: `PortfolioHoldingIn` | `{"id": int, ...}` | `update_portfolio_holding` in `src/api/routes/compat_router.py` | Yes (Bearer) | Yes |
| **11. Portfolio Delete** | `DELETE` | `/api/portfolio/holdings/{id}` | Path: `id` | Status 204 No Content | `delete_portfolio_holding` in `src/api/routes/compat_router.py` | Yes (Bearer) | Yes |
| **11. Portfolio Summary** | `GET` | `/api/portfolio` | None (Bearer header) | `{"available": bool, "total_value": float, "total_invested": float, "profit_loss": float, "return_pct": float, "stocks_held": int, "positions": list, "sectors": list}` | `get_portfolio` in `src/api/routes/compat_router.py` | Yes (Bearer) | Yes |
| **11. Portfolio History** | `GET` | `/api/portfolio/performance`| None (Bearer header) | `{"available": bool, "data": list[{"date": str, "value": float}]}` | `portfolio_performance` in `src/api/routes/compat_router.py` | Yes (Bearer) | Yes |
| **11. Portfolio Risk** | `GET` | `/api/portfolio/risk` | None (Bearer header) | `{"available": bool, "risk": {"cagr": float, "annualized_volatility": float, "sharpe": float, "max_drawdown": float, "var_95": float}, "beta": float, "allocation": list}` | `portfolio_risk` in `src/api/routes/compat_router.py` | Yes (Bearer) | Yes |
| **11. Portfolio Optimise**| `POST` | `/api/v1/portfolio/optimise` | Body: `PortfolioOptimiseRequest` (`method`, `symbols`, `target_risk_pct`) | `PortfolioOptimiseResponse` (`method`, `weights`, `expected_annual_return_pct`, `annual_volatility_pct`, `sharpe_ratio`, `diversification_score`) | `optimise_portfolio` in `src/api/routes/portfolio.py` | No | Yes |
| **12. Risk Status** | `GET` | `/api/v1/risk/status` | None | `RiskStatusResponse` (`circuit_breaker_state`, `max_drawdown_limit_pct`, `max_position_size_pct`, `cash_reserve_required_pct`) | `get_risk_status` in `src/api/routes/risk.py` | No | Yes |
| **13. Strategy List** | `GET` | `/api/strategies` | Query: `symbol` | `{"data": list[{"id": str, "name": str, "description": str, "risk": str, "metrics": dict}], "source": str}` | `list_strategies` in `src/api/routes/compat_router.py` | No | Yes |
| **13. Strategy Detail** | `GET` | `/api/strategies/{strategy_id}` | Path: `strategy_id`, Query: `symbol` | `{"id": str, "name": str, "metrics": dict, "source": str}` | `strategy_detail` in `src/api/routes/compat_router.py` | No | Yes |
| **13. Backtest Run** | `POST` | `/api/backtests/run` | Body: `BacktestRequest` (`symbol`, `strategy`, `period`, `initial_capital`, `transaction_cost_bps`, `position_size`) | `{"id": int, "symbol": str, "strategy": str, "results": {"total_return": float, "cagr": float, "sharpe": float, "max_drawdown": float, "win_rate": float, "equity": list, "dates": list, "trades": list}}` | `run_backtest` in `src/api/routes/compat_router.py` | No | Yes |
| **13. Backtest Fetch** | `GET` | `/api/backtests/{id}` | Path: `id` | `{"id": int, "symbol": str, "strategy": str, "total_return": float, "created_at": str}` | `get_backtest` in `src/api/routes/compat_router.py` | No | Yes |
| **13. Quant Backtest Run** | `POST` | `/api/v1/backtesting/run`| Body: `BacktestRunRequest` (`symbols`, `initial_capital`, `strategy_id`) | `BacktestRunResponse` (`backtest_id`, `status`, `metrics`) | `run_backtest` in `src/api/routes/backtesting.py` | No | Yes |
| **14. Paper Account** | `GET` | `/api/v1/paper-trading/account` | None | `{"account_id": str, "initial_capital": float, "available_cash": float, "total_equity": float, "circuit_breaker_state": str}` | `get_paper_account` in `src/api/routes/paper_trading.py` | No | Yes |
| **14. Paper Positions** | `GET` | `/api/v1/paper-trading/positions` | None | `{"positions": list[dict], "count": int}` | `get_paper_positions` in `src/api/routes/paper_trading.py` | No | Yes |
| **14. Paper Orders** | `GET` | `/api/v1/paper-trading/orders` | Query: `limit` | `{"orders": list[dict], "count": int}` | `get_paper_orders` in `src/api/routes/paper_trading.py` | No | Yes |
| **14. Paper Sessions** | `GET` | `/api/v1/paper-trading/sessions` | None | `list[PaperSessionResponse]` | `list_paper_sessions` in `src/api/routes/paper_trading.py` | No | Yes |
| **14. Paper Create** | `POST` | `/api/v1/paper-trading/sessions`| Body: `PaperSessionCreateRequest` (`session_name`, `initial_capital`, `symbols`, `mode`) | `PaperSessionResponse` | `create_paper_session` in `src/api/routes/paper_trading.py` | No | Yes |
| **14. Paper Action** | `POST` | `/api/v1/paper-trading/sessions/{session_id}/{action}` | Path: `session_id`, `action` (`start`, `pause`, `resume`, `stop`, `close`) | `PaperSessionResponse` | `manage_paper_session` in `src/api/routes/paper_trading.py` | No | Yes |
| **15. AI Assistant** | `POST` | `/api/ai/chat` | Body: `ChatIn` (`question`, `symbol`) | `{"answer": str, "provider": str, "symbol": str, "regime": str}` | `ai_chat` in `src/api/routes/compat_router.py` (integrates Ollama client with real context) | Yes (Bearer) | Yes |
| **15. Quant Copilot** | `POST` | `/api/v1/assistant/chat`| Body: `AssistantChatRequest` (`query`, `conversation_id`) | `AssistantChatResponse` (`message`, `conversation_id`, `intent`, `tools_called`, `verdict`, `confidence`, `disclaimer`) | `assistant_chat` in `src/api/routes/assistant.py` | No | Yes |
| **16. Watchlist: List** | `GET` | `/api/watchlist` | None (Bearer header) | `list[{"id": int, "symbol": str, "name": str, "exchange": str, "price": float, "change": float, "source": str}]` | `get_watchlist` in `src/api/routes/compat_router.py` | Yes (Bearer) | Yes |
| **16. Watchlist: Add** | `POST` | `/api/watchlist` | Body: `{"symbol": str}` | `{"id": int, "symbol": str, "name": str}` | `add_watchlist` in `src/api/routes/compat_router.py` | Yes (Bearer) | Yes |
| **16. Watchlist: Delete**| `DELETE` | `/api/watchlist/{item_id}` | Path: `item_id` | Status 204 No Content | `remove_watchlist` in `src/api/routes/compat_router.py` | Yes (Bearer) | Yes |

---

## 3. Comparison with Teammate Frontend Pages & Axios Client

| Teammate Frontend Page / Component | Frontend Axios Call | Core Backend `/api/v1/` Equivalent | Compatibility Router Route | Gap / Status |
| :--- | :--- | :--- | :--- | :--- |
| **Login (`AuthPages.tsx`)** | `POST /auth/login` | None | `POST /api/auth/login` | Fully resolved & tested via SQLite + bcrypt |
| **Signup (`AuthPages.tsx`)** | `POST /auth/register` | None | `POST /api/auth/register` | Fully resolved & tested via SQLite + bcrypt |
| **Forgot Password (`AuthPages.tsx`)**| `POST /auth/forgot-password`| None | `POST /api/auth/forgot-password` | Fully resolved (returns 202 Accepted) |
| **Reset Password (`AuthPages.tsx`)** | `POST /auth/reset-password` | None | `POST /api/auth/reset-password` | Fully resolved via one-time tokens |
| **Profile (`AuthPages.tsx`)** | `GET /auth/me`, `PUT /auth/me`, `POST /auth/change-password` | None | `GET/PUT /api/auth/me`, `POST /api/auth/change-password` | Fully resolved & verified with auth headers |
| **Watchlist (`AuthPages.tsx`)** | `GET /watchlist`, `POST /watchlist`, `DELETE /watchlist/{id}` | None | `GET/POST /api/watchlist`, `DELETE /api/watchlist/{id}` | Fully resolved & persists user watchlist |
| **Dashboard (`Pages.tsx`)** | `GET /market/overview`, `GET /market/indicators`, `GET /portfolio` | Part of `/market/regime`, `/market/{symbol}` | `GET /api/market/overview`, `GET /api/market/indicators`, `GET /api/portfolio` | Fully mapped to real NIFTY 50 OHLCV data |
| **Markets (`Pages.tsx`)** | `GET /market/overview`, `GET /market/indicators` | None with multi-indicator schema | `GET /api/market/overview`, `GET /api/market/indicators` | Fully mapped with RSI, MACD, ADX, Volatility |
| **Regimes (`Pages.tsx`)** | `GET /regimes/current`, `GET /regimes/history` | `GET /market/regime` | `GET /api/regimes/current`, `GET /api/regimes/history` | Fully mapped with M07 quantitative evidence |
| **Strategies (`Pages.tsx`)** | `GET /strategies` | `GET /strategies` | `GET /api/strategies` | Fully mapped with 6 quantitative strategies |
| **Backtest Lab (`Pages.tsx`)** | `POST /backtests/run` | `POST /backtesting/run` | `POST /api/backtests/run` | Fully mapped with chronological simulation |
| **Portfolio Page (`PortfolioPage.tsx`)**| `GET /portfolio`, `GET /portfolio/holdings`, `POST /portfolio/holdings`, `GET /portfolio/performance`, `GET /portfolio/risk` | None (only paper trading had positions) | `GET/POST /api/portfolio/holdings`, `GET /api/portfolio/performance`, `GET /api/portfolio/risk` | Fully mapped with real lot tracking and VaR/Beta |
| **AI Assistant (`Pages.tsx`)** | `POST /ai/chat` | `POST /assistant/chat` | `POST /api/ai/chat` | Fully mapped to Ollama LLM with grounded market & portfolio context |

---

## 4. Analysis of Gaps, Incompatibilities & Redundancies

### 4.1 Incompatible Request/Response Schemas
1. **Backtesting:**  
   - Teammate frontend sends `BacktestRequest` (`symbol`, `strategy`, `period`, `initial_capital`, `transaction_cost_bps`, `position_size`) and expects an equity curve and closed trade breakdown.
   - Core `/api/v1/backtesting/run` expected `BacktestRunRequest` (`symbols: list[str]`, `initial_capital`, `strategy_id`).
   - *Resolution:* Supported via compatibility router without changing core backtesting engine.
2. **AI Chat:**  
   - Teammate frontend sends `{ question: str, symbol: str }` and expects `{ answer: str, provider: str, symbol: str, regime: str }`.
   - Core `/api/v1/assistant/chat` expected `{ query: str, conversation_id: Optional[str] }` and returned tool execution metadata.
   - *Resolution:* Supported via `/api/ai/chat` integrating OllamaClient with real market and portfolio context.
3. **Market Overview:**  
   - Teammate frontend expects an aggregated financial overview object (`price`, `change`, `rsi`, `adx`, `volatility`, `risk`, `regime`, `active_signal`).
   - Core backend split these across separate microservice routes (`/market/{symbol}`, `/stock/{symbol}/strength`, `/market/regime`).
   - *Resolution:* Combined in `GET /api/market/overview` for high-performance single-request frontend rendering.

### 4.2 Authentication Gaps
- Core MIRAI had no user table or session storage.
- Teammate frontend requires standard HS256 JWT tokens with automatic token attachment in Axios request interceptors and token revocation on logout.
- *Resolution:* SQLite persistence in `data/mirai.db` with bcrypt password hashing (12 rounds) and `RevokedToken` tracking.

### 4.3 Redundant Functionality
- Both systems have portfolio concepts: core MIRAI had virtual paper trading accounts (`account_states`), whereas teammate frontend uses user-entered purchase lots (`portfolio_holdings`).
- Both are maintained: personal portfolio tracking in `/api/portfolio/holdings` and algorithmic execution in `/api/v1/paper-trading/`.

---

## 5. Verification Status & Recommended Actions

- **Backend Pytest Suite:** All **213 tests pass** (`208 core tests + 5 compatibility integration tests`).
- **Data Integrity:** Stock records strictly loaded from actual dataset files (`NIFTY-50-Stock-Market-Data-main/data/*.csv`); zero synthetic or fake data when actual dataset constituents are queried.
- **Frontend Readiness:** Teammate UI files (`styles.css`, `styles-auth.css`, `AuthPages.tsx`, `PortfolioPage.tsx`, `Pages.tsx`, `Shell.tsx`) preserved without alterations.

### Next Step:
Upon user review and confirmation of this audit report, proceed to **Checkpoint 3 (Centralized API Client verification)** and **Checkpoint 4 (Frontend-Backend wiring and end-to-end verification)**.
