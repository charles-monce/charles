"""Telegram notification system."""

import json
import logging
from datetime import date

import requests

from .config import config

logger = logging.getLogger(__name__)

# Daily notification counter (resets at midnight via date check)
_notification_state = {
    "date": None,
    "count": 0,
}

# Pending messages awaiting response (message_id -> message_summary)
_pending_messages: dict[int, str] = {}


def _reset_if_new_day():
    today = date.today().isoformat()
    if _notification_state["date"] != today:
        _notification_state["date"] = today
        _notification_state["count"] = 0


def notifications_today() -> int:
    _reset_if_new_day()
    return _notification_state["count"]


def can_notify() -> bool:
    _reset_if_new_day()
    return _notification_state["count"] < config.max_notifications_per_day


def _telegram_api(method: str, **kwargs) -> dict:
    if not config.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set")

    url = f"https://api.telegram.org/bot{config.telegram_bot_token}/{method}"
    response = requests.post(url, json=kwargs, timeout=10)

    if response.status_code != 200:
        logger.error(f"Telegram API error: {response.status_code} — {response.text}")
        raise RuntimeError(f"Telegram API error: {response.status_code}")

    return response.json()


def send_notification(summary: str, message_text: str) -> dict:
    """Send a Telegram notification with Yes/No/Prompt buttons.

    Returns the Telegram API response.
    """
    if not can_notify():
        return {"sent": False, "reason": f"Daily limit reached ({config.max_notifications_per_day})"}

    if not config.telegram_bot_token or not config.telegram_chat_id:
        return {"sent": False, "reason": "Telegram not configured"}

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "Yes", "callback_data": "response:yes"},
                {"text": "No", "callback_data": "response:no"},
                {"text": "Prompt required", "callback_data": "response:prompt"},
            ]
        ]
    }

    text = f"**Charles needs you**\n\n{summary}\n\n_Original:_ {message_text[:500]}"

    result = _telegram_api(
        "sendMessage",
        chat_id=config.telegram_chat_id,
        text=text,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

    _notification_state["count"] += 1

    # Track pending message
    msg_id = result.get("result", {}).get("message_id")
    if msg_id:
        _pending_messages[msg_id] = summary

    logger.info(
        f"Notification sent ({_notification_state['count']}/{config.max_notifications_per_day}): {summary}"
    )

    return {"sent": True, "notification_number": _notification_state["count"], "message_id": msg_id}


def handle_callback(callback_data: str, message_id: int) -> dict:
    """Handle a Telegram inline keyboard callback.

    Returns: {"action": str, "needs_text": bool}
    """
    action = callback_data.replace("response:", "")
    summary = _pending_messages.pop(message_id, "unknown message")

    if action == "yes":
        return {"action": "yes", "needs_text": False, "summary": summary}
    elif action == "no":
        return {"action": "no", "needs_text": False, "summary": summary}
    elif action == "prompt":
        # Ask user to type a response
        _telegram_api(
            "sendMessage",
            chat_id=config.telegram_chat_id,
            text=f"Type your response for: _{summary}_",
            parse_mode="Markdown",
            reply_markup={"force_reply": True},
        )
        return {"action": "prompt", "needs_text": True, "summary": summary}

    return {"action": "unknown", "needs_text": False, "summary": summary}


def answer_callback_query(callback_query_id: str, text: str):
    """Acknowledge a callback query (removes loading state on button)."""
    try:
        _telegram_api("answerCallbackQuery", callback_query_id=callback_query_id, text=text)
    except Exception as e:
        logger.warning(f"Failed to answer callback query: {e}")
