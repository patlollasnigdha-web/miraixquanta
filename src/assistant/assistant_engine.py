"""
MIRAI — Generative AI Assistant Engine (M16)
Central coordinator for natural-language query parsing, intent recognition,
tool calling, Ollama chat generation, safety enforcement, and response formatting.
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from src.utils.logger import get_logger
from src.assistant.assistant_schemas import (
    AssistantResponse,
    ChatMessage,
    MessageRole,
    ToolCallRequest,
    ToolCallResult,
)
from src.assistant.ollama_client import OllamaClient, OllamaServiceUnavailableError
from src.assistant.tool_executor import ToolExecutor
from src.assistant.tool_registry import get_tool_definitions
from src.assistant.context_builder import ContextBuilder, default_context_builder
from src.assistant.prompt_manager import PromptManager
from src.assistant.response_formatter import ResponseFormatter
from src.assistant.financial_safety import FinancialSafetyGuard

logger = get_logger("AssistantEngine")


class AssistantEngine:
    """
    High-level conversational intelligence interface for MIRAI.
    Translates user questions into backend tool calls and formats evidence-based answers.
    """

    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        tool_executor: Optional[ToolExecutor] = None,
        context_builder: Optional[ContextBuilder] = None,
        use_ollama_for_synthesis: bool = True,
    ):
        self.ollama = ollama_client or OllamaClient()
        self.tool_executor = tool_executor or ToolExecutor()
        self.context_builder = context_builder or default_context_builder
        self.use_ollama = use_ollama_for_synthesis

    def extract_intent_and_tools(self, query: str) -> Tuple[str, List[ToolCallRequest]]:
        """
        Rule-based and heuristic intent recognition.
        Identifies tickers and required MIRAI backend tools without hallucinating inputs.
        """
        q = query.strip()
        q_lower = q.lower()
        tool_requests: List[ToolCallRequest] = []
        intent = "GENERAL_QUERY"

        # 1. Extract stock symbols (standard Indian equity names or capitalized words)
        symbols = self._extract_symbols(q)
        target_symbol = symbols[0] if symbols else None

        # 2. Rule-based Intent Matching

        # Case A: "Should I invest in X?" / "Buy X?"
        if any(p in q_lower for p in ["should i invest", "can i buy", "invest in", "buy or sell", "recommend"]):
            intent = "INVESTMENT_DECISION"
            sym = target_symbol or "TCS"
            tool_requests.append(ToolCallRequest(tool_name="get_investment_decision", arguments={"symbol": sym}))
            return intent, tool_requests

        # Case B: Compare stocks
        if "compare" in q_lower or (len(symbols) >= 2 and any(w in q_lower for w in ["vs", "better", "difference"])):
            intent = "COMPARE_STOCKS"
            comp_symbols = symbols if len(symbols) >= 2 else ["TCS", "INFY"]
            tool_requests.append(ToolCallRequest(tool_name="compare_stocks", arguments={"symbols": comp_symbols}))
            return intent, tool_requests

        # Case C: Stock Strength
        if any(w in q_lower for w in ["strength", "score", "strongest", "momentum"]):
            intent = "STOCK_STRENGTH"
            sym = target_symbol or "TCS"
            tool_requests.append(ToolCallRequest(tool_name="get_stock_strength", arguments={"symbol": sym}))
            return intent, tool_requests

        # Case D: Market Regime
        if any(w in q_lower for w in ["regime", "market condition", "volatility regime", "macro"]):
            intent = "MARKET_REGIME"
            tool_requests.append(ToolCallRequest(tool_name="get_market_regime", arguments={"pipeline": "pipeline_b_nifty"}))
            return intent, tool_requests

        # Case E: Paper Trading / Account / Portfolio / Orders
        if any(w in q_lower for w in ["paper", "account", "portfolio", "positions", "my orders", "rejected"]):
            if "rejected" in q_lower or "order" in q_lower:
                intent = "PAPER_ORDERS"
                tool_requests.append(ToolCallRequest(tool_name="get_paper_orders", arguments={"limit": 10}))
            else:
                intent = "PAPER_ACCOUNT"
                tool_requests.append(ToolCallRequest(tool_name="get_paper_account", arguments={}))
                tool_requests.append(ToolCallRequest(tool_name="get_portfolio_summary", arguments={}))
            return intent, tool_requests

        # Case F: Risk
        if any(w in q_lower for w in ["risk", "drawdown", "circuit breaker", "exposure"]):
            intent = "RISK_STATUS"
            tool_requests.append(ToolCallRequest(tool_name="get_risk_status", arguments={}))
            return intent, tool_requests

        # Case G: Sentiment
        if "sentiment" in q_lower or "news" in q_lower:
            intent = "SENTIMENT_ANALYSIS"
            sym = target_symbol or "TCS"
            tool_requests.append(ToolCallRequest(tool_name="get_sentiment", arguments={"symbol": sym}))
            return intent, tool_requests

        # Case H: Fundamentals
        if any(w in q_lower for w in ["fundamental", "p/e", "valuation", "earnings"]):
            intent = "FUNDAMENTAL_ANALYSIS"
            sym = target_symbol or "TCS"
            tool_requests.append(ToolCallRequest(tool_name="get_fundamentals", arguments={"symbol": sym}))
            return intent, tool_requests

        # Case I: Backtest
        if "backtest" in q_lower or "performance" in q_lower:
            intent = "BACKTEST_RESULTS"
            tool_requests.append(ToolCallRequest(tool_name="get_backtest_results", arguments={"backtest_id": "LATEST"}))
            return intent, tool_requests

        # Default fallback: if a symbol is mentioned, default to stock strength
        if target_symbol:
            intent = "STOCK_STRENGTH"
            tool_requests.append(ToolCallRequest(tool_name="get_stock_strength", arguments={"symbol": target_symbol}))
            return intent, tool_requests

        return intent, tool_requests

    def _extract_symbols(self, text: str) -> List[str]:
        """Identifies known or capitalized ticker symbols."""
        known_stocks = [
            "TCS", "INFY", "RELIANCE", "HDFCBANK", "ICICIBANK", "SBIN",
            "BHARTIARTL", "ITC", "KOTAKBANK", "LT", "HINDUNILVR", "TATAMOTORS"
        ]
        found = []
        tokens = re.findall(r"\b[A-Za-z0-9_]+\b", text)
        for t in tokens:
            t_up = t.upper()
            if t_up in known_stocks and t_up not in found:
                found.append(t_up)
        if found:
            return found

        stop_words = {
            "SHOULD", "INVEST", "WILL", "WHAT", "WHEN", "WHERE", "WHICH", "COULD",
            "WOULD", "IS", "ARE", "AM", "WAS", "WERE", "DOES", "DO", "DID", "THE",
            "AND", "FOR", "BUY", "SELL", "HOLD", "STOCK", "STOCKS", "PRICE", "MARKET",
            "TRADE", "TRADING", "EXPLAIN", "SHOW", "GIVE", "VIEW", "REPORT", "ANALYSIS",
            "CAN", "HOW", "WHY"
        }
        raw_caps = re.findall(r"\b[A-Z]{2,10}\b", text)
        for w in raw_caps:
            if w not in stop_words and w not in found:
                found.append(w)
        return found

    def ask(self, query: str, conversation_id: Optional[str] = None) -> AssistantResponse:
        """
        Executes complete multi-turn conversational processing pipeline:
        1. Context retrieval & Intent recognition
        2. Backend tool execution
        3. Response generation (Ollama LLM or Deterministic Formatter fallback)
        4. Financial safety validation & Disclaimer attachment
        5. Memory update
        """
        conv = self.context_builder.get_or_create_conversation(conversation_id)
        cid = conv.conversation_id

        # 1. Record user turn
        self.context_builder.add_message(cid, role=MessageRole.USER, content=query)

        # 2. Extract Intent and Tools
        intent, tool_requests = self.extract_intent_and_tools(query)

        # 3. Execute Tools
        tool_results: List[Dict[str, Any]] = []
        tools_called_names: List[str] = []

        verdict_val = None
        conf_val = None
        as_of_val = None

        for req in tool_requests:
            res = self.tool_executor.execute_tool(req)
            tools_called_names.append(req.tool_name)
            tool_results.append(res.to_dict())

            # Capture decision metadata if present
            if req.tool_name == "get_investment_decision" and res.success and isinstance(res.data, dict):
                verdict_val = res.data.get("verdict")
                conf_val = res.data.get("confidence")
                as_of_val = res.data.get("timestamp")
            elif req.tool_name == "get_stock_strength" and res.success and isinstance(res.data, dict):
                conf_val = res.data.get("confidence")
                as_of_val = res.data.get("as_of_date")

        # 4. Generate Response Text
        # For critical investment decisions or stock comparisons, use deterministic formatter
        # to ensure 100% adherence to M09 verdict and M11 risk rules
        response_text = ""
        if intent == "INVESTMENT_DECISION" and tool_results:
            first_data = tool_results[0].get("data")
            response_text = ResponseFormatter.format_investment_decision(first_data) if first_data else f"Unable to evaluate investment decision: {tool_results[0].get('error', 'Execution failed.')}"
        elif intent == "COMPARE_STOCKS" and tool_results:
            first_data = tool_results[0].get("data")
            response_text = ResponseFormatter.format_stock_comparison(first_data) if first_data else f"Unable to compare stocks: {tool_results[0].get('error', 'Execution failed.')}"
        elif intent == "STOCK_STRENGTH" and tool_results:
            first_data = tool_results[0].get("data")
            response_text = ResponseFormatter.format_stock_strength(first_data) if first_data else f"Unable to evaluate stock strength: {tool_results[0].get('error', 'Execution failed.')}"
        elif intent == "MARKET_REGIME" and tool_results:
            first_data = tool_results[0].get("data")
            response_text = ResponseFormatter.format_market_regime(first_data) if first_data else f"Unable to detect market regime: {tool_results[0].get('error', 'Execution failed.')}"
        elif tool_results:
            response_text = ResponseFormatter.format_generic_tool_results(tool_results)
        else:
            # General conversation without tools: attempt Ollama if enabled
            if self.use_ollama:
                try:
                    llm_msgs = self.context_builder.build_llm_messages(
                        conversation_id=cid,
                        system_prompt=PromptManager.get_system_prompt(),
                        current_query=query,
                        tool_results=tool_results,
                    )
                    ollama_res = self.ollama.chat(messages=llm_msgs)
                    response_text = ollama_res.get("message", {}).get("content", "")
                except OllamaServiceUnavailableError as e:
                    logger.warning("Ollama unavailable for general query: %s", e)
                    response_text = (
                        "I am operating in deterministic mode because the local Ollama runtime "
                        "is currently unavailable. However, all quantitative trading engines, stock strength, "
                        "risk management, and paper trading tools remain fully operational."
                    )
            else:
                response_text = (
                    "I am the MIRAI Quantitative Assistant. Ask me about stock strength, "
                    "market regimes, portfolio risk, paper trading, or investment decisions."
                )

        # 5. Financial Safety Guardrails
        response_text = FinancialSafetyGuard.sanitize_guarantee_claims(response_text)
        response_text = FinancialSafetyGuard.attach_disclaimer(response_text)

        # 6. Record assistant turn
        self.context_builder.add_message(cid, role=MessageRole.ASSISTANT, content=response_text)

        return AssistantResponse(
            message=response_text,
            conversation_id=cid,
            intent=intent,
            tools_called=tools_called_names,
            tool_results=tool_results,
            verdict=verdict_val,
            confidence=conf_val,
            data_freshness_timestamp=as_of_val,
        )


# Global shared instance
default_assistant = AssistantEngine()
