"""
MIRAI — Generative AI Assistant Package (M16)
Provides natural-language financial intelligence, multi-turn dialogue,
Ollama integration, and tool-driven factual explanations.
"""

from src.assistant.assistant_schemas import (
    MessageRole,
    ChatMessage,
    ToolCallRequest,
    ToolCallResult,
    AssistantResponse,
    ConversationState,
)
from src.assistant.financial_safety import FinancialSafetyGuard, STANDARD_DISCLAIMER
from src.assistant.ollama_client import OllamaClient, OllamaServiceUnavailableError
from src.assistant.tool_registry import get_tool_definitions, get_tool_by_name
from src.assistant.tool_executor import ToolExecutor
from src.assistant.context_builder import ContextBuilder, default_context_builder
from src.assistant.prompt_manager import PromptManager
from src.assistant.response_formatter import ResponseFormatter
from src.assistant.assistant_engine import AssistantEngine, default_assistant

__all__ = [
    "MessageRole",
    "ChatMessage",
    "ToolCallRequest",
    "ToolCallResult",
    "AssistantResponse",
    "ConversationState",
    "FinancialSafetyGuard",
    "STANDARD_DISCLAIMER",
    "OllamaClient",
    "OllamaServiceUnavailableError",
    "get_tool_definitions",
    "get_tool_by_name",
    "ToolExecutor",
    "ContextBuilder",
    "default_context_builder",
    "PromptManager",
    "ResponseFormatter",
    "AssistantEngine",
    "default_assistant",
]
