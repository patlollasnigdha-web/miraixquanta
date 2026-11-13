# MIRAI — Interactive Quantitative Trading Dashboard (M17)

MIRAI is an AI-driven adaptive quantitative trading and intelligent execution framework for dynamic financial markets. This frontend terminal provides a responsive, dark-themed institutional interface for visualizing and controlling the end-to-end quantitative trading system.

---

## Features

- **Executive Overview Dashboard:** Live virtual account equity, buying power, capital allocation, active market regime, M09 decision highlights, and operational alerts.
- **Stock Intelligence Explorer:** M05 Stock Strength Score (0–100), multi-pillar factor contributions (momentum, relative strength, volume confirmation, trend quality, volatility-adjusted return, liquidity), point-in-time financial news sentiment, and side-by-side stock comparisons.
- **Decision Explorer:** Direct interface to the authoritative M09 Investment Decision Engine. Inspect algorithmic verdicts (`YES`, `NO`, `WAIT`, `INSUFFICIENT_DATA`), composite scores, model confidence, execution parameters, positive/negative factor evidence, and narrative rationale.
- **AI Quantitative Copilot:** Institutional natural-language chat connected to the local Ollama LLM runtime (`qwen2.5-coder:7b`) with 14 bound backend quantitative tools, automatic multi-turn context memory, and strict regulatory financial safety guards.
- **Portfolio & Risk Controls:** Real-time virtual holdings ledger, M10 mathematical portfolio optimizer (Risk Budgeting, Minimum Variance, Equal Weight), and M11 dynamic circuit breaker state monitoring (`NORMAL`, `CAUTION`, `RESTRICTED`, `HALTED`).
- **Strategy Analysis & Backtesting:** Quantitative strategy catalog (Adaptive Momentum, Mean Reversion, Breakout), bar-by-bar chronological historical simulation, transaction cost & slippage modeling, and equity growth trajectory visualization.
- **Paper Trading Control Station:** Virtual trading session lifecycle manager (Create, Start, Pause, Resume, Stop, Close) with explicit confirmation modals before state-changing transitions, and chronological virtual order ledger.
- **System Monitoring & Diagnostics:** Real-time health probing across database, Ollama, model binaries, and system hardware telemetry (CPU, RAM, disk usage).

---

## Technology Stack

- **Framework:** React 18 with TypeScript
- **Bundler:** Vite 6
- **Styling:** Tailwind CSS with custom dark terminal theme
- **Visualizations:** Recharts
- **Icons:** Lucide React
- **Testing:** Vitest with React Testing Library and JSDOM

---

## Setup & Running

### Prerequisites
- Node.js >= 18 (Tested on Node.js v25)
- Running MIRAI FastAPI Backend on `http://localhost:8000`

### 1. Install Dependencies
```bash
npm install
```

### 2. Configure Environment
Copy `.env.example` to `.env`:
```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_DEFAULT_PIPELINE=pipeline_b_nifty
```

### 3. Launch Development Server
```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

### 4. Build for Production
```bash
npm run build
```

### 5. Run Frontend Test Suite
```bash
npm run test
```
