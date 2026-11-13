"""
Tests for MIRAI Assistant Tool Registry and Tool Executor (M16)
Validates controlled tool execution, parameter schemas, and unauthorized invocation rejection.
"""

import pytest
from src.assistant.tool_registry import get_tool_definitions, get_tool_by_name
from src.assistant.tool_executor import ToolExecutor
from src.assistant.assistant_schemas import ToolCallRequest


def test_tool_registry_definitions():
    tools = get_tool_definitions()
    assert len(tools) >= 14
    tool_names = [t["name"] for t in tools]
    assert "get_stock_strength" in tool_names
    assert "get_market_regime" in tool_names
    assert "get_investment_decision" in tool_names
    assert "get_risk_status" in tool_names
    assert "compare_stocks" in tool_names


def test_tool_executor_stock_strength():
    executor = ToolExecutor()
    req = ToolCallRequest(tool_name="get_stock_strength", arguments={"symbol": "TCS"})
    res = executor.execute_tool(req)
    assert res.success is True
    assert res.data["symbol"] == "TCS"
    assert "stock_strength_score" in res.data
    assert "factor_scores" in res.data


def test_tool_executor_market_regime():
    executor = ToolExecutor()
    req = ToolCallRequest(tool_name="get_market_regime", arguments={"pipeline": "pipeline_b_nifty"})
    res = executor.execute_tool(req)
    assert res.success is True
    assert "current_regime" in res.data


def test_tool_executor_investment_decision():
    executor = ToolExecutor()
    req = ToolCallRequest(tool_name="get_investment_decision", arguments={"symbol": "TCS", "horizon": "1d"})
    res = executor.execute_tool(req)
    assert res.success is True
    assert res.data["symbol"] == "TCS"
    assert res.data["verdict"] in ("YES", "NO", "WAIT", "INSUFFICIENT_DATA")
    assert res.data["risk_status"] in ("RISK_APPROVED", "RISK_BLOCKED", "RISK_PENDING")


def test_tool_executor_compare_stocks():
    executor = ToolExecutor()
    req = ToolCallRequest(tool_name="compare_stocks", arguments={"symbols": ["TCS", "INFY"]})
    res = executor.execute_tool(req)
    assert res.success is True
    assert len(res.data["comparison"]) == 2


def test_tool_executor_unauthorized_tool_rejection():
    executor = ToolExecutor()
    req = ToolCallRequest(tool_name="execute_arbitrary_shell_command", arguments={"cmd": "ls"})
    res = executor.execute_tool(req)
    assert res.success is False
    assert "not in the authorized MIRAI tool registry" in res.error
