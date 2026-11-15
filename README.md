# MIRAI — AI-Driven Adaptive Quantitative Trading and Intelligent Execution Framework

> **ASTRAQUANT X** | Academic Engineering & Quantitative Trading Framework for Dynamic Financial Markets

MIRAI is an end-to-end institutional algorithmic trading framework combining machine learning predictions, market microstructure analysis, multi-factor stock strength intelligence, point-in-time financial sentiment, market regime detection, adaptive strategy switching, evidence-based investment decisions, portfolio optimisation, dynamic risk controls, intelligent order execution, historical backtesting, virtual paper trading, an Ollama LLM copilot, and an interactive dark-themed dashboard.

##live deployed webiste

open=> https://miraixquanta-sn7k.vercel.app
---

## Architecture Overview (Modules M01–M18)

1. **M01 — Data Integration & Access:** Point-in-time data loaders for Pipeline A (FI-2010 limit order book tick events) and Pipeline B (NIFTY 50 Indian equities daily and intraday candles).
2. **M02 — Feature Engineering & Store:** Microstructure order-flow imbalance (OFI), volume-synchronized probability of toxicity (VPIN), price impact, multi-timeframe technical indicators, and persistent feature caching.
3. **M03/M04 — Predictive AI Engine & Model Registry:** PyTorch sequence models (LSTM, Microstructure Transformer) and tree ensembles (Random Forest, XGBoost) with metadata versioning, line-of-sight tracking, and fallback baseline guards.
4. **M05 — Stock Strength Intelligence:** 6-pillar composite strength scoring (0–100) assessing momentum, relative strength, volume confirmation, trend quality, volatility-adjusted return, and liquidity.
5. **M06 — Financial Sentiment & Fundamental Intelligence:** Point-in-time news NLP evaluation and officially disclosed financial ratios.
6. **M07 — Market Regime Detection:** Rule-based and unsupervised Gaussian Mixture Model (GMM) clustering classifying market dynamics into 6 regimes (e.g. `BULLISH_TRENDING`, `HIGH_VOLATILITY`, `STRESS_ABNORMAL`).
7. **M08 — Adaptive Trading Strategy Engine:** Strategy switching (Momentum, Mean Reversion, Breakout) governed by current regime alignment.
8. **M09 — Authoritative Investment Decision Engine:** Synthesizes multi-pillar evidence into transparent, explainable decisions (`YES`, `NO`, `WAIT`, `INSUFFICIENT_DATA`).
9. **M10 — Portfolio Optimisation:** Minimum Variance, Equal Weight, and Risk Budgeting asset allocation engines.
10. **M11 — Dynamic Risk Management:** Portfolio drawdown monitoring, exposure limits, dynamic trailing stops, and automated 4-state circuit breakers (`NORMAL`, `CAUTION`, `RESTRICTED`, `HALTED`).
11. **M12 — Intelligent Execution Engine:** Microstructure simulation with TWAP, VWAP, adaptive execution, realistic non-linear slippage, and Indian NSE statutory fee calculations.
12. **M13 — Historical Backtesting Engine:** Strictly non-lookahead bar-by-bar chronological execution simulator with performance attribution (CAGR, Sharpe, Sortino, Max Drawdown).
13. **M14 — Integrated Paper Trading Engine:** Multi-session SQLite-backed state machine for virtual forward simulation without brokerage connections.
14. **M15 — FastAPI Backend:** Asynchronous REST API exposing 20+ endpoints with OpenAPI documentation.
15. **M16 — Ollama Generative AI Assistant:** Local LLM runtime copilot (`qwen2.5-coder:7b`) with 14 bound quantitative tools and financial safety guards.
16. **M17 — Interactive Dashboard:** Modern React 18, TypeScript, Vite, and Tailwind CSS financial terminal.
17. **M18 — System Monitoring & Observability:** Real-time health probing, metrics aggregation, threshold alerting, and host hardware telemetry.

---

## Quick Start Guide

### 1. Backend Environment Setup (Python 3.10+)

```bash
# Activate virtual environment
.\.venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Launch FastAPI backend service
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be live at `http://localhost:8000/docs`.

### 2. Ollama Local LLM Runtime (Optional for M16 Copilot)

```bash
# Ensure Ollama is running locally
ollama serve

# Verify model presence
ollama list
# Recommended: qwen2.5-coder:7b
```

### 3. Frontend Interactive Dashboard (Node.js 18+)

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) to access the MIRAI terminal.

---

## Verification & Testing

### Run Backend Tests (208 Tests)
```bash
python -m pytest tests/ -v
```

### Run Frontend Tests (11 Tests)
```bash
cd frontend
npm run test
```

### Build Frontend for Production
```bash
cd frontend
npm run build
```

---

## Regulatory and Safety Disclaimers

MIRAI is an academic research and algorithmic simulation platform.
- **Virtual Simulation Only:** Real-money brokerage or exchange execution is explicitly disabled.
- **Risk Notice:** Past model performance and backtesting results do not guarantee future performance.
