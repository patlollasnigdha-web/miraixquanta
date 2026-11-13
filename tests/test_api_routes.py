"""
Tests for MIRAI FastAPI Core REST Routes (M15)
Validates market data, stock intelligence, predictions, strategies, decisions,
portfolio, risk, execution simulation, backtesting, and paper trading endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_market_data_route(client):
    res = client.get("/api/v1/market/TCS")
    assert res.status_code == 200
    data = res.json()
    assert data["symbol"] == "TCS"
    assert "latest_bar" in data
    assert "bars_count" in data


def test_stock_strength_route(client):
    res = client.get("/api/v1/stock/TCS/strength")
    assert res.status_code == 200
    data = res.json()
    assert data["symbol"] == "TCS"
    assert "stock_strength_score" in data
    assert 0.0 <= data["stock_strength_score"] <= 100.0
    assert "factor_contributions" in data


def test_stock_sentiment_route(client):
    res = client.get("/api/v1/stock/TCS/sentiment")
    assert res.status_code == 200
    data = res.json()
    assert data["symbol"] == "TCS"
    assert "sentiment_score" in data
    assert "sentiment_label" in data


def test_predictions_route(client):
    payload = {
        "symbol": "TCS",
        "pipeline": "pipeline_b_nifty",
        "horizon": "1d",
        "model_name": "random_forest",
    }
    res = client.post("/api/v1/predictions", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["symbol"] == "TCS"
    assert data["predicted_direction"] in ("UPWARD", "DOWNWARD", "STATIONARY")
    assert 0.0 <= data["confidence"] <= 1.0


def test_strategies_list_and_evaluate_routes(client):
    # List
    res_list = client.get("/api/v1/strategies")
    assert res_list.status_code == 200
    strats = res_list.json()
    assert len(strats) >= 3

    # Evaluate
    payload = {
        "strategy_id": "MOMENTUM_STRATEGY",
        "symbol": "TCS",
        "pipeline": "pipeline_b_nifty",
    }
    res_eval = client.post("/api/v1/strategies/evaluate", json=payload)
    assert res_eval.status_code == 200
    eval_data = res_eval.json()
    assert eval_data["symbol"] == "TCS"
    assert eval_data["signal"] in ("BUY", "SELL", "HOLD", "NO_SIGNAL")


def test_decisions_evaluate_route(client):
    payload = {
        "symbol": "TCS",
        "pipeline_id": "pipeline_b_nifty",
        "investment_horizon": "1d",
    }
    res = client.post("/api/v1/decisions/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["symbol"] == "TCS"
    assert data["verdict"] in ("YES", "NO", "WAIT", "INSUFFICIENT_DATA")
    assert data["risk_status"] in ("RISK_APPROVED", "RISK_BLOCKED", "RISK_PENDING")
    assert "explanation" in data


def test_portfolio_and_optimisation_routes(client):
    # GET portfolio
    res_port = client.get("/api/v1/portfolio")
    assert res_port.status_code == 200
    assert "positions" in res_port.json()

    # POST optimise
    payload = {
        "symbols": ["TCS", "INFY", "RELIANCE"],
        "method": "risk_budgeting",
        "target_risk_pct": 0.15,
    }
    res_opt = client.post("/api/v1/portfolio/optimise", json=payload)
    assert res_opt.status_code == 200
    opt_data = res_opt.json()
    assert "weights" in opt_data
    assert "sharpe_ratio" in opt_data


def test_risk_status_route(client):
    res = client.get("/api/v1/risk/status")
    assert res.status_code == 200
    data = res.json()
    assert "circuit_breaker_state" in data
    assert data["circuit_breaker_state"] in ("NORMAL", "CAUTION", "RESTRICTED", "HALTED")


def test_execution_simulate_route(client):
    payload = {
        "symbol": "TCS",
        "side": "BUY",
        "quantity": 25,
        "order_type": "MARKET",
    }
    res = client.post("/api/v1/execution/simulate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["symbol"] == "TCS"
    assert data["filled_quantity"] == 25
    assert data["status"] == "FILLED"
    assert data["average_price"] > 0.0


def test_backtest_run_route(client):
    payload = {
        "strategy_id": "MOMENTUM_STRATEGY",
        "symbols": ["TCS"],
        "initial_capital": 500_000.0,
    }
    res = client.post("/api/v1/backtesting/run", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert "backtest_id" in data
    assert "metrics" in data


def test_paper_trading_session_endpoints(client):
    # 1. Create Session
    create_payload = {
        "session_name": "APITestSession",
        "initial_capital": 500_000.0,
        "symbols": ["TCS"],
        "mode": "HISTORICAL_REPLAY",
    }
    res_create = client.post("/api/v1/paper-trading/sessions", json=create_payload)
    assert res_create.status_code == 201
    sess = res_create.json()
    sess_id = sess["session_id"]
    assert sess["status"] == "CREATED"

    # 2. Start
    res_start = client.post(f"/api/v1/paper-trading/sessions/{sess_id}/start")
    assert res_start.status_code == 200
    assert res_start.json()["status"] == "RUNNING"

    # 3. Pause
    res_pause = client.post(f"/api/v1/paper-trading/sessions/{sess_id}/pause")
    assert res_pause.status_code == 200
    assert res_pause.json()["status"] == "PAUSED"

    # 4. Resume
    res_resume = client.post(f"/api/v1/paper-trading/sessions/{sess_id}/resume")
    assert res_resume.status_code == 200
    assert res_resume.json()["status"] == "RUNNING"

    # 5. Stop
    res_stop = client.post(f"/api/v1/paper-trading/sessions/{sess_id}/stop")
    assert res_stop.status_code == 200
    assert res_stop.json()["status"] == "STOPPED"

    # 6. Close
    res_close = client.post(f"/api/v1/paper-trading/sessions/{sess_id}/close")
    assert res_close.status_code == 200
    assert res_close.json()["status"] == "CLOSED"

    # 7. Check account, positions, orders query
    assert client.get("/api/v1/paper-trading/account").status_code == 200
    assert client.get("/api/v1/paper-trading/positions").status_code == 200
    assert client.get("/api/v1/paper-trading/orders").status_code == 200
