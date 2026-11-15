"""
MIRAI — Generative AI Assistant Endpoints (M15)
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from src.api.dependencies import get_assistant_engine
from src.assistant.assistant_engine import AssistantEngine
from src.api.api_schemas import AssistantChatRequest, AssistantChatResponse, APIResponse
from src.prediction.four_company_engine import four_company_engine

router = APIRouter(prefix="/assistant", tags=["Assistant"])


@router.post("/chat", response_model=AssistantChatResponse)
async def assistant_chat(
    req: AssistantChatRequest,
    assistant: AssistantEngine = Depends(get_assistant_engine),
):
    """
    Conversational natural-language interface for MIRAI.
    Translates user questions into factual backend tool executions and answers.
    """
    res = await four_company_engine.generate_analyst_response(
        query=req.query,
        default_symbol="RELIANCE",
    )
    return AssistantChatResponse(
        message=res["answer"],
        conversation_id=req.conversation_id or "default-session",
        intent="FINANCIAL_ANALYST_VERDICT",
        tools_called=["four_company_engine"],
        verdict=res.get("verdict", "INSUFFICIENT DATA"),
        confidence=None,
        disclaimer="MIRAI Quantitative Framework · Research and decision support only · No trade execution.",
        timestamp=datetime.now().isoformat(),
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
