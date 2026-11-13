"""
MIRAI — Generative AI Assistant Endpoints (M15)
"""

from fastapi import APIRouter, Depends
from src.api.dependencies import get_assistant_engine
from src.assistant.assistant_engine import AssistantEngine
from src.api.api_schemas import AssistantChatRequest, AssistantChatResponse, APIResponse

router = APIRouter(prefix="/assistant", tags=["Assistant"])


@router.post("/chat", response_model=AssistantChatResponse)
def assistant_chat(
    req: AssistantChatRequest,
    assistant: AssistantEngine = Depends(get_assistant_engine),
):
    """
    Conversational natural-language interface for MIRAI.
    Translates user questions into factual backend tool executions and answers.
    """
    res = assistant.ask(query=req.query, conversation_id=req.conversation_id)
    return AssistantChatResponse(
        message=res.message,
        conversation_id=res.conversation_id,
        intent=res.intent,
        tools_called=res.tools_called,
        verdict=res.verdict,
        confidence=res.confidence,
        disclaimer=res.disclaimer,
        timestamp=res.timestamp,
    )


@router.post("/conversations/{conversation_id}/reset", response_model=APIResponse)
def reset_conversation(
    conversation_id: str,
    assistant: AssistantEngine = Depends(get_assistant_engine),
):
    """Resets memory context for an active conversation session."""
    success = assistant.context_builder.reset_conversation(conversation_id)
    return APIResponse(
        success=success,
        message=f"Conversation '{conversation_id}' context has been reset." if success else f"Conversation '{conversation_id}' not found.",
    )
