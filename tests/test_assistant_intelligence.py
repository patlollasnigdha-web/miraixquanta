"""
MIRAI — AI Assistant Response Intelligence & Final Verdict Verification Tests
Validates:
1. Strict final verdicts (YES — BUY, NO — DON'T BUY, WAIT, YES — CONTINUE HOLDING, INSUFFICIENT DATA)
2. Plain-English structure: ### FINAL VERDICT, ### WHY?, ### PRICE PREDICTION, ### PROFIT OR LOSS, ### RISK LEVEL, ### WHAT SHOULD I DO?
3. Elimination of fake confidence (Confidence: Not calibrated)
4. Strict four-company boundaries (MRF, TCS, JIO, RELIANCE) and rejection of external indices/stocks
"""

import pytest
from src.prediction.four_company_engine import four_company_engine


@pytest.mark.anyio
async def test_assistant_buy_mrf():
    res = await four_company_engine.generate_analyst_response("Should I buy MRF?", "MRF")
    assert "YES — BUY" in res["verdict"]
    answer = res["answer"]
    assert "### FINAL VERDICT\nYES — BUY" in answer
    assert "### WHY?" in answer
    assert "### PRICE PREDICTION" in answer
    assert "### PROFIT OR LOSS" in answer
    assert "### RISK LEVEL" in answer
    assert "### WHAT SHOULD I DO?" in answer
    assert "Not calibrated." in answer
    assert "128,600.00" in answer
    assert "+2.78%" in answer


@pytest.mark.anyio
async def test_assistant_no_buy_tcs():
    res = await four_company_engine.generate_analyst_response("If I buy TCS today, what could happen after five trading sessions?", "TCS")
    assert "NO — DON'T BUY" in res["verdict"]
    answer = res["answer"]
    assert "### FINAL VERDICT\nNO — DON'T BUY" in answer
    assert "-0.58%" in answer
    assert "loss" in answer.lower()


@pytest.mark.anyio
async def test_assistant_reliance_profit():
    res = await four_company_engine.generate_analyst_response("Will Reliance give me a profit or loss?", "RELIANCE")
    assert "YES — BUY" in res["verdict"]
    answer = res["answer"]
    assert "### FINAL VERDICT\nYES — BUY" in answer
    assert "net profit" in answer.lower()
    assert "+4.92%" in answer


@pytest.mark.anyio
async def test_assistant_hold_jio():
    res = await four_company_engine.generate_analyst_response("Should I hold Jio Platforms?", "JIO")
    assert "YES — CONTINUE HOLDING" in res["verdict"]
    answer = res["answer"]
    assert "### FINAL VERDICT\nYES — CONTINUE HOLDING" in answer
    assert "+4.66%" in answer


@pytest.mark.anyio
async def test_assistant_why_not_buy():
    res = await four_company_engine.generate_analyst_response("Explain why you are recommending not to buy.", "TCS")
    assert "NO — DON'T BUY" in res["verdict"]
    answer = res["answer"]
    assert "### FINAL VERDICT\nNO — DON'T BUY" in answer


@pytest.mark.anyio
async def test_assistant_unsupported_asset_rejected():
    res = await four_company_engine.generate_analyst_response("Should I buy NIFTY 50 or Infosys?", "RELIANCE")
    assert res["verdict"] == "INSUFFICIENT DATA"
    answer = res["answer"]
    assert "### FINAL VERDICT\nINSUFFICIENT DATA" in answer
    assert "strictly focused on institutional research for four companies" in answer
