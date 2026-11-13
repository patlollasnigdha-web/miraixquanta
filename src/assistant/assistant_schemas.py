"""
MIRAI — Generative AI Assistant Schemas (M16)
Data structures for chat conversations, intent parsing, tool calls, and responses.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class MessageRole(str, Enum):
    """Chat participant roles."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ChatMessage:
    """Individual message in a multi-turn conversation."""
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "role": self.role.value if isinstance(self.role, MessageRole) else str(self.role),
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        return d


@dataclass
class ToolCallRequest:
    """Requested backend tool execution."""
    tool_name: str
    arguments: Dict[str, Any]
    call_id: str = field(default_factory=lambda: f"CALL_{uuid.uuid4().hex[:6].upper()}")


@dataclass
class ToolCallResult:
    """Result emitted by backend tool execution."""
    tool_name: str
    success: bool
    data: Any
    error: Optional[str] = None
    call_id: Optional[str] = None
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "call_id": self.call_id,
            "execution_time_ms": self.execution_time_ms,
        }


@dataclass
class AssistantResponse:
    """Structured assistant response container."""
    message: str
    conversation_id: str
    intent: Optional[str] = None
    tools_called: List[str] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    verdict: Optional[str] = None
    confidence: Optional[float] = None
    data_freshness_timestamp: Optional[str] = None
    disclaimer: str = (
        "Educational & Research Simulation Only: MIRAI quantitative analytics and predictions "
        "do not constitute financial advice. Past performance and simulated returns are not guaranteed."
    )
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "conversation_id": self.conversation_id,
            "intent": self.intent,
            "tools_called": self.tools_called,
            "tool_results": self.tool_results,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "data_freshness_timestamp": self.data_freshness_timestamp,
            "disclaimer": self.disclaimer,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ConversationState:
    """Multi-turn session state."""
    conversation_id: str
    messages: List[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def add_message(self, role: MessageRole, content: str, **kwargs) -> ChatMessage:
        msg = ChatMessage(role=role, content=content, **kwargs)
        self.messages.append(msg)
        self.updated_at = datetime.utcnow()
        return msg

    def clear(self) -> None:
        self.messages.clear()
        self.updated_at = datetime.utcnow()
