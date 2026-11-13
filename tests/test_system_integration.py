"""
Tests for MIRAI System-Wide End-to-End Integration (M15, M16, M18)
Validates complete operational flow across FastAPI, Ollama Assistant,
Decision Engine, Risk Management, Paper Trading, and Monitoring.
"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_complete_system_integration_flow(client):
    # 1. Health check
    h_res = client.get("/api/v1/health")
    assert h_res.status_code == 200
    assert h_res.json()["overall_status"] in ("HEALTHY", "DEGRADED")

    # 2. Stock Strength Intelligence
    str_res = client.get("/api/v1/stock/TCS/strength")
    assert str_res.status_code == 200
    assert str_res.json()["stock_strength_score"] > 0.0

    # 3. Authoritative Decision Evaluation
    dec_res = client.post("/api/v1/decisions/evaluate", json={"symbol": "TCS", "investment_horizon": "1d"})
    assert dec_res.status_code == 200
    dec_data = dec_res.json()
    assert dec_data["verdict"] in ("YES", "NO", "WAIT", "INSUFFICIENT_DATA")
    assert dec_data["risk_status"] in ("RISK_APPROVED", "RISK_BLOCKED", "RISK_PENDING")

    # 4. Create and start Paper Trading Session
    create_res = client.post("/api/v1/paper-trading/sessions", json={"session_name": "SystemIntegrationSession"})
    assert create_res.status_code == 201
    sess_id = create_res.json()["session_id"]

    start_res = client.post(f"/api/v1/paper-trading/sessions/{sess_id}/start")
    assert start_res.status_code == 200
    assert start_res.json()["status"] == "RUNNING"

    # 5. Assistant Query: "Should I invest in TCS?"
    chat_res = client.post("/api/v1/assistant/chat", json={"query": "Should I invest in TCS?"})
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert chat_data["intent"] == "INVESTMENT_DECISION"
    assert "get_investment_decision" in chat_data["tools_called"]
    assert chat_data["verdict"] == dec_data["verdict"]
    assert "Disclaimer:" in chat_data["disclaimer"] or "Disclaimer:" in chat_data["message"]

    # 6. Observability Metrics
    met_res = client.get("/api/v1/monitoring/metrics")
    assert met_res.status_code == 200
    met_data = met_res.json()
    assert met_data["counters"].get("api_requests_total", 0) > 0

    # 7. Stop and Close Session
    stop_res = client.post(f"/api/v1/paper-trading/sessions/{sess_id}/stop")
    assert stop_res.status_code == 200
    assert stop_res.json()["status"] == "STOPPED"

    close_res = client.post(f"/api/v1/paper-trading/sessions/{sess_id}/close")
    assert close_res.status_code == 200
    assert close_res.json()["status"] == "CLOSED"
