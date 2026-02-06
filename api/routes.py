"""API routes for Charles."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from . import memory, notifications
from .haiku import classify_message, chat_response

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Request/Response models ---

class MessageRequest(BaseModel):
    text: str
    source: Optional[str] = None

class ForgetRequest(BaseModel):
    query: str

class MessageResponse(BaseModel):
    remembered: bool
    reply: Optional[str] = None
    notification_sent: bool = False
    classification: Optional[dict] = None

class ForgetResponse(BaseModel):
    forgotten: int
    query: str


# --- Endpoints ---

@router.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "charles",
        "memories": memory.memory_count(),
        "responses": memory.response_count(),
        "notifications_today": notifications.notifications_today(),
        "max_notifications": notifications.config.max_notifications_per_day,
        "can_notify": notifications.can_notify(),
    }


@router.post("/message", response_model=MessageResponse)
async def receive_message(req: MessageRequest):
    """Receive a message, remember it, classify it, maybe notify."""
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty message")

    source = req.source

    # 1. Remember (with source tag)
    memory.add_memory(text, source=source)

    # Self-sent prompts from Claude Code: remember silently, no classification
    if source == "claude-code":
        return MessageResponse(
            remembered=True,
            reply=None,
            notification_sent=False,
            classification={"notify": False, "reason": "self-sent (claude-code)", "summary": ""},
        )

    # 2. Classify with Haiku
    notification_sent = False
    classification = None
    try:
        classification = classify_message(text)

        # 3. Maybe notify
        if classification.get("notify") and notifications.can_notify():
            notif_result = notifications.send_notification(
                summary=classification.get("summary", text[:100]),
                message_text=text,
            )
            notification_sent = notif_result.get("sent", False)

    except Exception as e:
        logger.error(f"Classification/notification error: {e}")
        classification = {"notify": False, "reason": f"Error: {e}", "summary": ""}

    # 4. Generate chat reply
    reply = None
    try:
        reply = chat_response(text)
    except Exception as e:
        logger.error(f"Chat response error: {e}")

    return MessageResponse(
        remembered=True,
        reply=reply,
        notification_sent=notification_sent,
        classification=classification,
    )


@router.post("/forget", response_model=ForgetResponse)
async def forget_memories(req: ForgetRequest):
    """Forget memories matching query."""
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Empty query")

    forgotten = memory.forget(query)
    return ForgetResponse(forgotten=forgotten, query=query)


@router.get("/memories")
async def get_memories(limit: int = 50, offset: int = 0):
    """Return memories, most recent first."""
    all_memories = memory.load_memories()
    total = len(all_memories)
    # Reverse for most recent first
    reversed_memories = list(reversed(all_memories))
    page = reversed_memories[offset:offset + limit]
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "memories": page,
    }


@router.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """Handle Telegram bot callbacks (button presses and text replies)."""
    body = await request.json()
    logger.info(f"Telegram webhook: {body}")

    # Handle callback query (button press)
    if "callback_query" in body:
        cq = body["callback_query"]
        callback_data = cq.get("data", "")
        message_id = cq.get("message", {}).get("message_id", 0)
        callback_query_id = cq.get("id", "")

        result = notifications.handle_callback(callback_data, message_id)

        # Store response
        action = result["action"]
        summary = result["summary"]

        if action == "yes":
            memory.save_response("Yes (acknowledged)", summary)
            notifications.answer_callback_query(callback_query_id, "Acknowledged")
        elif action == "no":
            memory.save_response("No (dismissed)", summary)
            notifications.answer_callback_query(callback_query_id, "Dismissed")
        elif action == "prompt":
            notifications.answer_callback_query(callback_query_id, "Type your response...")

        return {"ok": True}

    # Handle text message (reply to "Prompt required")
    if "message" in body:
        msg = body["message"]
        text = msg.get("text", "")
        reply_to = msg.get("reply_to_message", {})

        if text and reply_to:
            # This is a response to a prompt
            original_text = reply_to.get("text", "")
            # Extract summary from the original prompt message
            summary = original_text.replace("Type your response for: _", "").rstrip("_")
            memory.save_response(text, summary)
            logger.info(f"Charles Dana responded: {text} (re: {summary})")

        return {"ok": True}

    return {"ok": True}
