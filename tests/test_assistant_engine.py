"""
Tests for MIRAI Assistant Engine (M16)
Validates intent extraction, multi-turn dialogue, tool orchestration, and response generation.
"""

import pytest
from src.assistant.assistant_engine import AssistantEngine
from src.assistant.context_builder import ContextBuilder


def test_intent_and_tool_extraction():
    engine = AssistantEngine(use_ollama_for_synthesis=False)

    # 1. Investment Decision
    intent1, tools1 = engine.extract_intent_and_tools("Should I invest in TCS?")
    assert intent1 == "INVESTMENT_DECISION"
    assert len(tools1) == 1
    assert tools1[0].tool_name == "get_investment_decision"
    assert tools1[0].arguments["symbol"] == "TCS"

    # 2. Stock Strength
    intent2, tools2 = engine.extract_intent_and_tools("What is the strength of INFY?")
    assert intent2 == "STOCK_STRENGTH"
    assert len(tools2) == 1
    assert tools2[0].tool_name == "get_stock_strength"
    assert tools2[0].arguments["symbol"] == "INFY"

    # 3. Compare Stocks
    intent3, tools3 = engine.extract_intent_and_tools("Compare TCS and INFY.")
    assert intent3 == "COMPARE_STOCKS"
    assert len(tools3) == 1
    assert tools3[0].tool_name == "compare_stocks"
    assert "TCS" in tools3[0].arguments["symbols"]
    assert "INFY" in tools3[0].arguments["symbols"]

    # 4. Market Regime
    intent4, tools4 = engine.extract_intent_and_tools("What is the current market regime?")
    assert intent4 == "MARKET_REGIME"
    assert tools4[0].tool_name == "get_market_regime"


def test_ask_investment_decision_flow():
    engine = AssistantEngine(use_ollama_for_synthesis=False)
    resp = engine.ask("Should I invest in TCS?")

    assert resp.intent == "INVESTMENT_DECISION"
    assert "get_investment_decision" in resp.tools_called
    assert resp.verdict in ("YES", "NO", "WAIT", "INSUFFICIENT_DATA")
    assert resp.conversation_id is not None
    assert "### Investment Analysis: TCS" in resp.message
    assert "Authoritative Verdict:" in resp.message
    assert "Disclaimer:" in resp.message


def test_multi_turn_conversation_and_reset():
    ctx = ContextBuilder()
    engine = AssistantEngine(context_builder=ctx, use_ollama_for_synthesis=False)

    # Turn 1
    r1 = engine.ask("What is the strength of TCS?")
    cid = r1.conversation_id
    assert cid in ctx._conversations
    assert len(ctx._conversations[cid].messages) == 2  # user + assistant

    # Turn 2
    r2 = engine.ask("What is the market regime?", conversation_id=cid)
    assert r2.conversation_id == cid
    assert len(ctx._conversations[cid].messages) == 4

    # Reset
    success = ctx.reset_conversation(cid)
    assert success is True
    assert len(ctx._conversations[cid].messages) == 0
