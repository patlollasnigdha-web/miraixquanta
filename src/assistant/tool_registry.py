"""
MIRAI — Assistant Tool Registry (M16)
Defines metadata, parameter schemas, and whitelists for controlled MIRAI backend tool calling.
"""

from typing import Any, Dict, List, Optional

TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "get_stock_strength",
        "description": "Retrieves the Stock Strength Score (0-100), factor contributions, and status for an Indian equity symbol.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ticker symbol, e.g. TCS, INFY, RELIANCE"}
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "get_market_regime",
        "description": "Identifies the current macroeconomic and volatility market regime (e.g. BULLISH_TRENDING, HIGH_VOLATILITY).",
        "parameters": {
            "type": "object",
            "properties": {
                "pipeline": {"type": "string", "description": "pipeline_b_nifty (default) or pipeline_a_fi2010", "default": "pipeline_b_nifty"}
            }
        }
    },
    {
        "name": "get_prediction",
        "description": "Retrieves AI/ML price directional predictions (M03) for a stock across model architectures.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ticker symbol, e.g. TCS, INFY"},
                "horizon": {"type": "string", "description": "Prediction horizon, e.g. '1d', '5d'", "default": "1d"}
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "get_sentiment",
        "description": "Retrieves financial news sentiment analysis (M06) and sentiment polarity score for a symbol.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ticker symbol, e.g. TCS, INFY, RELIANCE"}
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "get_fundamentals",
        "description": "Retrieves fundamental score, valuation ratios (P/E, P/B, ROE), and classification for a symbol.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ticker symbol, e.g. TCS, INFY"}
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "get_strategy_signal",
        "description": "Evaluates candidate adaptive trading strategies (M08) and returns actionable signals with price targets.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ticker symbol, e.g. TCS, INFY"}
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "get_investment_decision",
        "description": "The authoritative investment decision engine (M09 + M11). Returns YES/NO/WAIT verdict, risk approval, and multi-pillar evidence.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ticker symbol, e.g. TCS, INFY"},
                "horizon": {"type": "string", "description": "Investment horizon, e.g. '1d'", "default": "1d"}
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "get_portfolio_summary",
        "description": "Retrieves the current paper trading portfolio holdings, market value, cost basis, and unrealized P&L.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "get_risk_status",
        "description": "Retrieves the M11 dynamic risk engine status, circuit-breaker state (NORMAL, CAUTION, RESTRICTED, HALTED), and exposure limits.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "get_paper_account",
        "description": "Retrieves virtual paper account capital, available cash, reserved cash, buying power, and realized P&L.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "get_paper_positions",
        "description": "Lists all open active virtual positions in the paper trading portfolio.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "get_paper_orders",
        "description": "Lists recent submitted, filled, cancelled, or rejected paper trading orders.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Maximum orders to return", "default": 20}
            }
        }
    },
    {
        "name": "get_backtest_results",
        "description": "Retrieves performance metrics, return curves, and trade statistics from historical backtesting runs.",
        "parameters": {
            "type": "object",
            "properties": {
                "backtest_id": {"type": "string", "description": "Unique backtest run identifier"}
            }
        }
    },
    {
        "name": "compare_stocks",
        "description": "Compares Stock Strength Scores, fundamental scores, and returns across multiple stock symbols.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of symbols to compare, e.g. ['INFY', 'TCS']"
                }
            },
            "required": ["symbols"]
        }
    }
]


def get_tool_definitions() -> List[Dict[str, Any]]:
    """Returns list of allowed tool schemas."""
    return list(TOOL_DEFINITIONS)


def get_tool_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Finds tool definition by name."""
    for tool in TOOL_DEFINITIONS:
        if tool["name"] == name:
            return tool
    return None
