"""
MIRAI — Integration Tests for Frontend Compatibility API (M16)
Tests /api/* endpoints including authentication, market data, backtesting,
watchlists, portfolio tracking, and AI chat fallback.
"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_compat_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "MIRAI API"
    assert "timestamp" in data


def test_compat_auth_lifecycle():
    import uuid
    uid = uuid.uuid4().hex[:8]
    username = f"trader_{uid}"
    email = f"{username}@miraiquant.org"
    reg_payload = {
        "full_name": "Test Trader",
        "email": email,
        "username": username,
        "password": "SecurePassword123",
        "confirm_password": "SecurePassword123",
        "phone": "+919876543210",
    }
    res_reg = client.post("/api/auth/register", json=reg_payload)
    assert res_reg.status_code in (201, 409)

    # 2. Login
    login_payload = {
        "email": email,
        "password": "SecurePassword123",
        "remember_me": True,
    }
    res_login = client.post("/api/auth/login", json=login_payload)
    assert res_login.status_code == 200
    login_data = res_login.json()
    assert "access_token" in login_data
    token = login_data["access_token"]
    assert login_data["user"]["email"] == email

    headers = {"Authorization": f"Bearer {token}"}

    # 3. GET /api/auth/me
    res_me = client.get("/api/auth/me", headers=headers)
    assert res_me.status_code == 200
    assert res_me.json()["username"] == username

    # 4. PUT /api/auth/me
    res_update = client.put(
        "/api/auth/me",
        headers=headers,
        json={
            "full_name": "Updated Trader",
            "email": email,
            "username": username,
            "phone": "+919999999999",
        },
    )
    assert res_update.status_code == 200
    assert res_update.json()["full_name"] == "Updated Trader"

    # 5. POST /api/auth/change-password
    res_pw = client.post(
        "/api/auth/change-password",
        headers=headers,
        json={
            "current_password": "SecurePassword123",
            "new_password": "NewSecurePassword456",
        },
    )
    assert res_pw.status_code == 200
    assert res_pw.json()["status"] == "ok"


def test_compat_market_instruments_and_history():
    # 1. Instruments
    res_inst = client.get("/api/market/instruments")
    assert res_inst.status_code == 200
    instruments = res_inst.json()
    assert len(instruments) >= 50
    symbols = {i["symbol"] for i in instruments}
    assert "^NSEI" in symbols
    assert "RELIANCE" in symbols or "RELIANCE.NS" in symbols

    # 2. History
    res_hist = client.get("/api/market/history?symbol=RELIANCE&period=1y")
    assert res_hist.status_code == 200
    hist = res_hist.json()
    assert hist["symbol"] == "RELIANCE"
    assert len(hist["data"]) > 0
    assert "close" in hist["data"][-1]

    # 3. Overview
    res_ov = client.get("/api/market/overview?symbol=TCS&period=1y")
    assert res_ov.status_code == 200
    ov = res_ov.json()
    assert ov["symbol"] == "TCS"
    assert "price" in ov
    assert "regime" in ov
    assert "active_signal" in ov


def test_compat_strategies_and_backtest():
    res_strat = client.get("/api/strategies?symbol=^NSEI")
    assert res_strat.status_code == 200
    strats = res_strat.json()["data"]
    assert len(strats) >= 6
    assert any(s["id"] == "ma_crossover" for s in strats)

    # Run backtest
    bt_req = {
        "symbol": "^NSEI",
        "strategy": "ma_crossover",
        "period": "1y",
        "initial_capital": 100000,
        "transaction_cost_bps": 5,
        "position_size": 1.0,
    }
    res_bt = client.post("/api/backtests/run", json=bt_req)
    assert res_bt.status_code == 200
    bt_res = res_bt.json()
    assert "id" in bt_res
    assert "results" in bt_res
    assert "equity" in bt_res["results"]


def test_compat_portfolio_and_watchlist():
    import uuid
    uid = uuid.uuid4().hex[:8]
    username = f"port_{uid}"
    email = f"{username}@miraiquant.org"
    client.post(
        "/api/auth/register",
        json={
            "full_name": "Portfolio Trader",
            "email": email,
            "username": username,
            "password": "Password123",
            "confirm_password": "Password123",
        },
    )
    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": "Password123"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Watchlist
    add_w = client.post("/api/watchlist", headers=headers, json={"symbol": "INFY"})
    assert add_w.status_code in (201, 409)
    get_w = client.get("/api/watchlist", headers=headers)
    assert get_w.status_code == 200

    # Add Portfolio Holding
    hold_payload = {
        "name": "Infosys Ltd.",
        "symbol": "INFY",
        "quantity": 10,
        "purchase_price": 1450.0,
        "purchase_date": "2026-01-15",
        "sector": "Information Technology",
    }
    add_h = client.post("/api/portfolio/holdings", headers=headers, json=hold_payload)
    assert add_h.status_code == 201

    get_port = client.get("/api/portfolio", headers=headers)
    assert get_port.status_code == 200
    port_data = get_port.json()
    assert port_data["available"] is True
    assert port_data["stocks_held"] >= 1

    # AI Chat
    chat_req = {
        "question": "What is the current market regime and how does it affect my portfolio?",
        "symbol": "INFY",
    }
    res_chat = client.post("/api/ai/chat", headers=headers, json=chat_req)
    assert res_chat.status_code == 200
    assert "answer" in res_chat.json()
