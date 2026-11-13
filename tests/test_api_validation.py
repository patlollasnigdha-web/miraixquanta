"""
Tests for MIRAI FastAPI Input Validation & Error Handlers (M15)
"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_missing_required_fields_returns_422(client):
    # Missing 'symbol'
    res = client.post("/api/v1/predictions", json={"horizon": "1d"})
    assert res.status_code == 422
    assert "error_type" in res.json() or "detail" in res.json()


def test_invalid_session_transition_returns_400(client):
    # 1. Create a session
    res_create = client.post("/api/v1/paper-trading/sessions", json={"session_name": "ValidationTest"})
    sess_id = res_create.json()["session_id"]

    # 2. Transition CREATED -> PAUSED (Illegal! Must be CREATED -> RUNNING or CLOSED)
    res_pause = client.post(f"/api/v1/paper-trading/sessions/{sess_id}/pause")
    assert res_pause.status_code == 400
    err = res_pause.json()
    assert err["error_type"] == "InvalidSessionStateError"
    assert "Cannot transition" in err["message"]


def test_nonexistent_session_id_returns_404(client):
    res = client.post("/api/v1/paper-trading/sessions/NONEXISTENT_SESSION_999/start")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_invalid_order_side_in_execution_simulate(client):
    payload = {
        "symbol": "TCS",
        "side": "INVALID_SIDE",
        "quantity": 10,
    }
    res = client.post("/api/v1/execution/simulate", json=payload)
    # Catches invalid enum / value error
    assert res.status_code in (400, 422)
