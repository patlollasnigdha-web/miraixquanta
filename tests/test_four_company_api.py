"""
Integration test suite for MIRAI Four-Company Prediction Engine.
Validates:
1. Four CSV datasets integration (MRF, TCS, JIO, RELIANCE).
2. Elimination of NIFTY 50 from instruments and predictions.
3. Quantitative indicator calculation and P&L decision engine.
4. API response structure and status codes.
"""

import pytest
import requests
from src.prediction.four_company_engine import four_company_engine, COMPANY_REGISTRY


def test_four_datasets_loaded():
    for sym in ["MRF", "TCS", "JIO", "RELIANCE"]:
        df = four_company_engine.load_dataset(sym)
        assert len(df) == 61, f"Expected 61 sessions for {sym}, got {len(df)}"
        for col in ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]:
            assert col in df.columns, f"Missing column {col} in {sym}"


def test_decision_engine_calculations():
    for sym in ["MRF", "TCS", "JIO", "RELIANCE"]:
        res = four_company_engine.predict_and_decide(sym, horizon=5)
        assert res["verdict"] in ["BUY", "SELL", "HOLD"]
        assert "expected_net_return_pct" in res
        assert "forecast_price" in res
        assert "indicators" in res
        assert "rsi" in res["indicators"]
        assert "ema20" in res["indicators"]
        assert "roc_10d" in res["indicators"]
        assert "atr_14d" in res["indicators"]
        assert "rel_vol" in res["indicators"]
        assert "obv" in res["indicators"]
        assert "momentum_10d" in res["indicators"]
        assert res["estimated_transaction_cost_pct"] == 0.20


def test_nifty_eliminated_from_instruments():
    from src.api.services.market_data_service import INSTRUMENTS
    assert "^NSEI" not in INSTRUMENTS
    assert "^NSEBANK" not in INSTRUMENTS
    assert "^BSESN" not in INSTRUMENTS
    for sym in ["MRF", "TCS", "JIO", "RELIANCE"]:
        assert sym in INSTRUMENTS


def test_api_instruments_endpoint():
    res = requests.get("http://127.0.0.1:8000/api/market/instruments")
    assert res.status_code == 200
    data = res.json()
    symbols = [x["symbol"] for x in data]
    assert len(symbols) == 4
    assert set(symbols) == {"MRF", "TCS", "JIO", "RELIANCE"}
    assert "^NSEI" not in symbols


def test_api_four_companies_prediction():
    res = requests.get("http://127.0.0.1:8000/api/predictions/companies?include_ollama=false")
    assert res.status_code == 200
    data = res.json()
    assert "NONE" in data["benchmark_index"]
    assert len(data["companies"]) == 4
    for c in data["companies"]:
        assert c["verdict"] in ["BUY", "SELL", "HOLD"]
        assert c["current_price"] > 0
        assert c["forecast_price"] > 0


def test_api_single_company_mrf():
    res = requests.get("http://127.0.0.1:8000/api/predictions/companies/MRF")
    assert res.status_code == 200
    data = res.json()
    assert data["symbol"] == "MRF"
    assert data["verdict"] == "BUY"
    assert data["current_price"] == 128600.0


def test_api_evaluate_endpoint():
    res = requests.post("http://127.0.0.1:8000/api/predictions/evaluate", json={"symbol": "TCS", "horizon": 5})
    assert res.status_code == 200
    data = res.json()
    assert data["symbol"] == "TCS"
    assert data["verdict"] == "HOLD"
