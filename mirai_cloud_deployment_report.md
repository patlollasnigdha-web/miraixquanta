# MIRAI — Cloud Backend Deployment Report (Checkpoint 5)

**Status:** PREPARED & VALIDATED FOR CLOUD DEPLOYMENT  
**Date:** 2026-11-14  
**Project Backend Root:** `C:\Users\srisa\OneDrive\Desktop\astraq`  
**Target Hosting Providers:** Render (Recommended Blueprint) / Railway / Container Registry (Docker)  
**Backend Framework:** FastAPI / Python 3.11+ / Uvicorn  
**Health Check Endpoints:** `GET /api/health` and `GET /api/v1/health` (HTTP 200 OK)  

---

## 1. Hosting Architecture & Provider Selection

| Factor | Render (Recommended) | Railway | Custom Docker / VPS |
|:---|:---|:---|:---|
| **Python / Uvicorn Support** | Native Python 3.11 runtime or Docker | Native Railpack or Dockerfile | Full container control |
| **Persistent Storage** | Supported (Persistent Disk mounted to `/app/data`) | Supported (Railway Volume mounted to `/app/data`) | Docker Volume / Host Mount |
| **Dataset & Model Size** | 9.2 MB NIFTY CSVs + 309 MB Models fully supported | Fully supported | Fully supported |
| **CORS & SSL** | Automatic HTTPS with custom domain / subdomains | Automatic HTTPS | Requires reverse proxy (Caddy/Nginx) |
| **Deployment Mechanism** | `render.yaml` Blueprint or Git Push | `Procfile` / Git Push | `docker run` / Docker Compose |

**Selected Primary Provider:** **Render** via [render.yaml](file:///c:/Users/srisa/OneDrive/Desktop/astraq/render.yaml) or **Railway** via [Procfile](file:///c:/Users/srisa/OneDrive/Desktop/astraq/Procfile). Both allow mounting a persistent disk volume to `/app/data` to preserve the SQLite database (`data/mirai.db`) across restarts and zero-downtime redeploys.

---

## 2. Production Configuration Files Created & Verified

### A. Production Dependencies ([requirements.txt](file:///c:/Users/srisa/OneDrive/Desktop/astraq/requirements.txt))
Verified and pinned all core ML, scientific, API, and cryptographic libraries:
```text
numpy, pandas, scipy, scikit-learn, matplotlib, seaborn, plotly, jupyter, openpyxl,
xgboost, joblib, tqdm, pyyaml, pytest, pytest-cov, pyarrow, streamlit, statsmodels,
fastapi, uvicorn[standard], pydantic, bcrypt, sqlalchemy, python-multipart, httpx, psutil
```

### B. Production Containerization ([Dockerfile](file:///c:/Users/srisa/OneDrive/Desktop/astraq/Dockerfile))
- **Base Image:** `python:3.11-slim`
- **System Dependencies:** `build-essential`, `curl`
- **Asset Bundling:** Bundles `src/`, `configs/`, `models/`, `NIFTY-50-Stock-Market-Data-main/`, `nifty50-historical-data-main/`, and `BenchmarkDatasets/`.
- **Dynamic Port:** Dynamically binds to cloud-assigned `$PORT` (defaults to 8000).
- **Health Check:** Native Docker `HEALTHCHECK` probing `http://localhost:${PORT:-8000}/api/health` every 30s.
- **Entrypoint:** `uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}`

### C. PaaS Startup Configuration ([Procfile](file:///c:/Users/srisa/OneDrive/Desktop/astraq/Procfile))
```text
web: uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
```

### D. Render Infrastructure-as-Code Blueprint ([render.yaml](file:///c:/Users/srisa/OneDrive/Desktop/astraq/render.yaml))
- Automates backend web service provisioning.
- Declares persistent disk `mirai-data` (1 GB) mounted at `/app/data`.
- Automatically injects secure random `MIRAI_SECRET_KEY`.
- Preconfigures CORS origins for the Vercel production frontend domain.

### E. Environment Variable Template ([.env.example](file:///c:/Users/srisa/OneDrive/Desktop/astraq/.env.example))
```env
MIRAI_API_HOST=0.0.0.0
MIRAI_API_PORT=8000
MIRAI_SECRET_KEY=replace-with-a-secure-random-32-byte-hex-string-for-production
MIRAI_TOKEN_TTL_SECONDS=86400
MIRAI_CORS_ORIGINS=https://mirai-jgw59fhk8-poojasrikandhula-6164s-projects.vercel.app,http://localhost:3000
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:7b
DATABASE_URL=sqlite:///data/mirai.db
```

### F. Repository Exclusion Cleanliness ([.gitignore](file:///c:/Users/srisa/OneDrive/Desktop/astraq/.gitignore))
- Preserves and tracks real stock datasets (`!NIFTY-50-Stock-Market-Data-main/`) and trained model binaries (`!models/`).
- Safely excludes `.env`, secrets, `.venv/`, `node_modules/`, `data/*.db` (auto-created on deployment), and build caches.

---

## 3. Persistent Storage, Database & Dataset Integrity

1. **Database Persistence:**
   - Database: SQLite initialized at `data/mirai.db`.
   - Auto-Migration: Handled by `init_db()` in [src/api/auth_database.py](file:///c:/Users/srisa/OneDrive/Desktop/astraq/src/api/auth_database.py) upon container startup.
   - Schema Tables: `users`, `portfolio_holdings`, `watchlist_items`, `revoked_tokens`, `password_reset_tokens`, `backtest_runs`.
   - Production Mounting: Mounted to persistent disk volume `/app/data`, preventing data loss across redeployments.

2. **Dataset Inventory (Real Data Only):**
   - **Constituent Datasets:** 11 multi-year constituent CSVs (`2016.csv` through `2026.csv`, 9.2 MB total) containing all 50 NIFTY 50 equities.
   - **Index Benchmark Datasets:** Official historical index datasets for `^NSEI`, `^NSEBANK`, and `^BSESN` in `nifty50-historical-data-main/`.
   - **Pipeline Separation:**
     - **Pipeline A (FI-2010):** High-frequency limit order book tick events in `BenchmarkDatasets/` for microstructure modeling.
     - **Pipeline B (NIFTY 50):** Daily OHLCV equities in `NIFTY-50-Stock-Market-Data-main/` for stock strength, regime detection, portfolio tracking, and backtesting.
     - Separation strictly preserved in `src/data_engineering/data_access.py`.

3. **Machine Learning Model Binaries:**
   - `models/auction_balanced_rf.joblib` (83.4 MB)
   - `models/auction_baseline_rf.joblib` (80.8 MB)
   - `models/non_auction_balanced_rf.joblib` (73.9 MB)
   - `models/non_auction_baseline_rf.joblib` (71.3 MB)
   - `models/registry.json`: Line-of-sight tracking and model metadata.

---

## 4. Ollama LLM Copilot Safe Production Behavior

Per production requirement 6:
1. **No Automatic Large Downloads:** The cloud deployment will not block or attempt to pull multi-gigabyte models into ephemeral storage.
2. **Availability Check:** `OllamaClient.is_available()` validates connectivity to `OLLAMA_HOST` (defaulting to `http://localhost:11434` or cloud tunnel) with a 2-second timeout.
3. **Graceful Quantitative Fallback:** When Ollama is unreachable or offline, [src/api/routes/compat_router.py](file:///c:/Users/srisa/OneDrive/Desktop/astraq/src/api/routes/compat_router.py) automatically catches the offline state and returns a comprehensive, data-grounded quantitative analysis using real calculated metrics (current price, GMM regime classification, 14-period RSI, 14-period ADX, annualized volatility, and user portfolio valuation).
4. **Zero Impact on Other Modules:** Market data, auth, stock screener, regimes, backtesting, and portfolio management operate normally regardless of Ollama status.

---

## 5. Security Validation

- **Authentication:** Bcrypt password hashing with 12 salt rounds (plain-text passwords never stored).
- **Session Tokens:** Cryptographically signed HS256 JWT tokens with configurable TTL (`MIRAI_TOKEN_TTL_SECONDS`).
- **CORS Configuration:** Explicitly permits the teammate's deployed Vercel domain (`https://mirai-jgw59fhk8-poojasrikandhula-6164s-projects.vercel.app`) as well as preview deployments matching `https://.*\.vercel\.app`.
- **Zero Exposed Secrets:** No credentials or API keys committed to Git or logged to stdout.

---

## 6. One-Click Cloud Deployment Instructions for User

Because cloud deployment requires your personal account authorization on your preferred host, perform the following single-step deployment:

### Option A: Render (Fastest & Simplest)
1. Sign in to [dashboard.render.com](https://dashboard.render.com).
2. Click **New +** &rarr; **Blueprint**.
3. Connect your GitHub repository (`astraq`). Render will automatically detect [render.yaml](file:///c:/Users/srisa/OneDrive/Desktop/astraq/render.yaml).
4. Click **Apply**.
5. Once deployed, copy your public backend URL: `https://mirai-backend-xxxx.onrender.com`.

### Option B: Railway
1. Sign in to [railway.app](https://railway.app).
2. Click **New Project** &rarr; **Deploy from GitHub Repo**.
3. Select `astraq`. Railway will automatically build using the [Dockerfile](file:///c:/Users/srisa/OneDrive/Desktop/astraq/Dockerfile) or [Procfile](file:///c:/Users/srisa/OneDrive/Desktop/astraq/Procfile).
4. In **Settings** &rarr; **Networking**, click **Generate Domain**.
5. Copy your public backend URL: `https://astraq-production.up.railway.app`.
