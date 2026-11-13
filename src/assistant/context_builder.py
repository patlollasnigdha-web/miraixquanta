"""
MIRAI — Conversation Context Builder (M16)
Manages multi-turn conversation memory, context trimming, and tool evidence injection.
Prevents stale conversation context from overriding newer market data.
"""

from datetime import datetime
import threading
from typing import Any, Dict, List, Optional
import uuid

from src.assistant.assistant_schemas import ChatMessage, ConversationState, MessageRole


class ContextBuilder:
    """
    In-memory multi-turn session storage and context assembly.
    """

    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self._lock = threading.Lock()
        self._conversations: Dict[str, ConversationState] = {}

    def get_or_create_conversation(self, conversation_id: Optional[str] = None) -> ConversationState:
        """Retrieves existing conversation or initializes a new conversation state."""
        with self._lock:
            cid = conversation_id or f"CONV_{uuid.uuid4().hex[:8].upper()}"
            if cid not in self._conversations:
                self._conversations[cid] = ConversationState(conversation_id=cid)
            return self._conversations[cid]

    def add_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        **kwargs,
    ) -> ChatMessage:
        """Appends a message to conversation and enforces max_turns sliding window."""
        conv = self.get_or_create_conversation(conversation_id)
        with self._lock:
            msg = conv.add_message(role=role, content=content, **kwargs)
            # Enforce max turns (pairs of user-assistant)
            if len(conv.messages) > self.max_turns * 2:
                # Keep first system message if any, trim oldest user/assistant
                conv.messages = conv.messages[-self.max_turns * 2 :]
            return msg

    def reset_conversation(self, conversation_id: str) -> bool:
        """Clears memory for a specific conversation session."""
        with self._lock:
            if conversation_id in self._conversations:
                self._conversations[conversation_id].clear()
                return True
        return False

    def build_llm_messages(
        self,
        conversation_id: str,
        system_prompt: str,
        current_query: str,
        tool_results: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, str]]:
        """
        Constructs the messages payload for Ollama /api/chat.
        Includes system prompt, recent dialogue history, tool execution results, and user query.
        """
        conv = self.get_or_create_conversation(conversation_id)
        llm_messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

        with self._lock:
            for m in conv.messages:
                role_str = m.role.value if isinstance(m.role, MessageRole) else str(m.role)
                if role_str in ("user", "assistant"):
                    llm_messages.append({"role": role_str, "content": m.content})

        # Append fresh tool evidence if retrieved
        if tool_results:
            tool_summary_lines = ["\n[CURRENT FACTUAL BACKEND DATA]"]
            for tr in tool_results:
                tool_summary_lines.append(f"Tool: {tr.get('tool_name')}")
                tool_summary_lines.append(f"Output: {tr.get('data')}")
            tool_summary_lines.append("[END BACKEND DATA]\n")
            llm_messages.append({"role": "system", "content": "\n".join(tool_summary_lines)})

        llm_messages.append({"role": "user", "content": current_query})
        return llm_messages


# Global shared instance
default_context_builder = ContextBuilder()
