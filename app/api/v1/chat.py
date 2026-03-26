"""Concierge chat API — conversational AI assistant with voice support."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, UploadFile, File
from pydantic import BaseModel
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_session
from app.models.chat import ChatMessage
from app.models.user import User
from app.models.tenant import Tenant
from app.models.brand import Brand

router = APIRouter(prefix="/chat", tags=["chat"])


async def _get_user_context(user: User, session: AsyncSession) -> dict:
    """Build context for the Concierge from user/tenant/brand data."""
    tenant = await session.get(Tenant, user.tenant_id)

    brands_result = await session.execute(
        select(Brand).where(Brand.tenant_id == user.tenant_id).limit(5)
    )
    brands = brands_result.scalars().all()
    brand_info = ", ".join(f"{b.name} ({b.industry})" for b in brands) if brands else "Aucune marque"
    brand_id = str(brands[0].id) if brands else None

    return {
        "user_id": str(user.id),
        "user_name": user.full_name,
        "user_role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "tenant_id": str(user.tenant_id),
        "tenant_name": tenant.name if tenant else "",
        "brand_info": brand_info,
        "brand_id": brand_id,
        "language": "francais",
    }


@router.get("/history")
async def get_chat_history(
    limit: int = 30,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get recent chat messages."""
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.tenant_id == user.tenant_id, ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    messages = list(reversed(result.scalars().all()))
    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "audio_url": m.audio_url,
            "action_type": m.action_type,
            "action_result": m.action_result,
            "action_buttons": m.action_buttons,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


@router.post("/send")
async def send_message(
    body: dict,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Send a text message to the Concierge."""
    user_message = body.get("message", "").strip()
    if not user_message:
        from app.core.exceptions import InvalidInputError
        raise InvalidInputError("Message vide")

    # Save user message
    user_msg = ChatMessage(
        tenant_id=user.tenant_id,
        user_id=user.id,
        role="user",
        content=user_message,
    )
    session.add(user_msg)
    await session.flush()

    # Get context
    ctx = await _get_user_context(user, session)

    # Get recent history
    history_stmt = (
        select(ChatMessage)
        .where(ChatMessage.tenant_id == user.tenant_id, ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(10)
    )
    history_result = await session.execute(history_stmt)
    history = [
        {"role": m.role, "content": m.content}
        for m in reversed(history_result.scalars().all())
    ]

    # Run Concierge
    from app.agents.concierge import ConciergeAgent
    concierge = ConciergeAgent()
    result = await concierge.run({
        **ctx,
        "user_message": user_message,
        "history": history,
    })

    output = result.output if result.success else {"message": "Desole, une erreur est survenue. Peux-tu reformuler ?"}

    # Save assistant response
    assistant_msg = ChatMessage(
        tenant_id=user.tenant_id,
        user_id=user.id,
        role="assistant",
        content=output.get("message", ""),
        action_type=output.get("action"),
        action_result=output.get("action_result"),
        action_buttons=output.get("buttons"),
    )
    session.add(assistant_msg)
    await session.commit()

    # Notify via WebSocket
    try:
        from app.core.websocket import notify
        await notify(
            tenant_id=str(user.tenant_id),
            event_type="chat_response",
            data={"message_id": str(assistant_msg.id)},
            user_id=str(user.id),
        )
    except Exception:
        pass

    return {
        "message": output.get("message", ""),
        "action": output.get("action"),
        "action_result": output.get("action_result"),
        "buttons": output.get("buttons", []),
        "needs_confirmation": output.get("needs_confirmation", False),
        "follow_up_question": output.get("follow_up_question"),
    }


@router.post("/send-voice")
async def send_voice_message(
    audio: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Send a voice message — transcribes then processes like text."""
    audio_data = await audio.read()

    if len(audio_data) > 10 * 1024 * 1024:  # 10MB max
        from app.core.exceptions import InvalidInputError
        raise InvalidInputError("Audio trop lourd (max 10 Mo)")

    # Transcribe
    from app.integrations.audio import get_audio_router
    audio_router = get_audio_router()

    try:
        transcription = await audio_router.speech_to_text(audio_data, language="fr")
    except Exception as e:
        return {"error": f"Transcription echouee: {str(e)[:100]}", "transcription": ""}

    if not transcription.strip():
        return {"error": "Aucune parole detectee", "transcription": ""}

    # Save user voice message
    user_msg = ChatMessage(
        tenant_id=user.tenant_id,
        user_id=user.id,
        role="user",
        content=transcription,
    )
    session.add(user_msg)
    await session.flush()

    # Process like text
    ctx = await _get_user_context(user, session)

    history_stmt = (
        select(ChatMessage)
        .where(ChatMessage.tenant_id == user.tenant_id, ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(10)
    )
    history_result = await session.execute(history_stmt)
    history = [
        {"role": m.role, "content": m.content}
        for m in reversed(history_result.scalars().all())
    ]

    from app.agents.concierge import ConciergeAgent
    concierge = ConciergeAgent()
    result = await concierge.run({
        **ctx,
        "user_message": transcription,
        "history": history,
    })

    output = result.output if result.success else {"message": "Desole, une erreur est survenue."}

    # Save assistant response
    assistant_msg = ChatMessage(
        tenant_id=user.tenant_id,
        user_id=user.id,
        role="assistant",
        content=output.get("message", ""),
        action_type=output.get("action"),
        action_result=output.get("action_result"),
        action_buttons=output.get("buttons"),
    )
    session.add(assistant_msg)
    await session.commit()

    return {
        "transcription": transcription,
        "message": output.get("message", ""),
        "action": output.get("action"),
        "action_result": output.get("action_result"),
        "buttons": output.get("buttons", []),
    }


class TTSRequest(BaseModel):
    text: str
    language: str = "fr"
    voice: str | None = None


@router.post("/tts")
async def text_to_speech(
    body: TTSRequest,
    user: User = Depends(get_current_user),
):
    """Convert text to speech audio."""
    text = body.text
    language = body.language
    voice = body.voice

    if not text:
        from app.core.exceptions import InvalidInputError
        raise InvalidInputError("Texte vide")

    from app.integrations.audio import get_audio_router
    audio_router = get_audio_router()

    try:
        audio_bytes = await audio_router.text_to_speech(text, language, voice)
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except Exception as e:
        return {"error": f"TTS echoue: {str(e)[:100]}"}


@router.post("/action")
async def execute_chat_action(
    body: dict,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Execute a button action from the chat (e.g. confirm, approve, etc.)."""
    action = body.get("action", "")
    params = body.get("params", {})

    ctx = await _get_user_context(user, session)

    from app.agents.concierge import ConciergeAgent
    concierge = ConciergeAgent()

    result = await concierge._execute_action(action, params, ctx)
    return {"action": action, "result": result}
