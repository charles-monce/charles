"""Bedrock Haiku caller for classification and chat."""

import json
import logging
import time

import requests

from .config import config
from .memory import get_recent_memories, get_recent_responses, load_manifest

logger = logging.getLogger(__name__)

BEDROCK_URL = (
    f"https://bedrock-runtime.{config.aws_region}.amazonaws.com"
    f"/model/{config.bedrock_model}/invoke"
)


def _call_haiku(prompt: str, max_tokens: int = 1024) -> str:
    if not config.aws_bearer_token:
        raise RuntimeError("AWS_BEARER_TOKEN_BEDROCK not set")

    response = requests.post(
        BEDROCK_URL,
        headers={
            "Authorization": f"Bearer {config.aws_bearer_token}",
            "Content-Type": "application/json",
        },
        json={
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30,
    )

    if response.status_code != 200:
        logger.error(f"Bedrock error: {response.status_code} — {response.text}")
        raise RuntimeError(f"Bedrock API error: {response.status_code}")

    result = response.json()
    return result.get("content", [{}])[0].get("text", "")


def classify_message(message: str) -> dict:
    """Classify whether a message should trigger a notification.

    Returns: {"notify": bool, "reason": str, "summary": str}
    """
    manifest = load_manifest()
    recent_memories = get_recent_memories(20)
    recent_responses = get_recent_responses(10)

    memories_text = ""
    if recent_memories:
        memories_text = "Recent memories (last 20):\n"
        for m in recent_memories:
            memories_text += f"- {m['text']} ({m['timestamp']})\n"

    responses_text = ""
    if recent_responses:
        responses_text = "What Charles Dana has said before:\n"
        for r in recent_responses:
            responses_text += f"- {r['response']} (re: {r['message_summary']}, {r['timestamp']})\n"

    prompt = f"""You are the gatekeeper for Charles Dana's attention.
You receive messages sent to "charles" — a public endpoint that anyone can call.

Charles Dana's rules:
{manifest}

{responses_text}

{memories_text}

Current message: "{message}"

Decide: should Charles Dana be notified on his phone?

NOTIFY only if:
- Someone specifically needs Charles Dana (the person)
- Production issue or system alert
- A decision only Charles Dana can make
- Time-sensitive request

DO NOT notify for:
- Casual messages, greetings, spam
- Things charles (the bot) can handle alone
- Repeated/duplicate requests
- Anything that doesn't require human attention

Respond ONLY as JSON (no other text):
{{"notify": true/false, "reason": "brief explanation", "summary": "1-line notification text"}}"""

    start = time.time()
    raw = _call_haiku(prompt, max_tokens=256)
    latency_ms = int((time.time() - start) * 1000)
    logger.info(f"Haiku classification took {latency_ms}ms")

    # Parse JSON from response (handle potential markdown wrapping)
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse Haiku response as JSON: {raw}")
        result = {"notify": False, "reason": "Failed to parse classification", "summary": ""}

    result["latency_ms"] = latency_ms
    return result


def chat_response(message: str) -> str:
    """Generate a chat response using Haiku with memory context."""
    recent_memories = get_recent_memories(20)

    context = ""
    if recent_memories:
        context = "Here's what you remember:\n"
        for m in recent_memories[-20:]:
            context += f"- {m['text']} ({m['timestamp']})\n"
        context += "\n"

    prompt = f"{context}User says: {message}"
    return _call_haiku(prompt)
