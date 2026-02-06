#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime

import requests

MEMORY_DIR = os.path.expanduser("~/.charles")
MEMORY_FILE = os.path.join(MEMORY_DIR, "memories.json")

API_URL = os.environ.get("CHARLES_API_URL", "https://charles.aws.monce.ai")

BEDROCK_REGION = "eu-west-3"
MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
BEDROCK_URL = f"https://bedrock-runtime.{BEDROCK_REGION}.amazonaws.com/model/{MODEL_ID}/invoke"


def load_memories():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE) as f:
            return json.load(f)
    return []


def save_memories(memories):
    os.makedirs(MEMORY_DIR, exist_ok=True)
    with open(MEMORY_FILE, "w") as f:
        json.dump(memories, f, indent=2)


def ask_haiku(text):
    """Local fallback: call Bedrock directly."""
    token = os.environ.get("AWS_BEARER_TOKEN_BEDROCK")
    if not token:
        print("Error: AWS_BEARER_TOKEN_BEDROCK not set")
        sys.exit(1)

    memories = load_memories()
    context = ""
    if memories:
        context = "Here's what you remember:\n"
        for m in memories[-20:]:
            context += f"- {m['text']} ({m['timestamp']})\n"
        context += "\n"

    prompt = f"{context}User says: {text}"

    response = requests.post(
        BEDROCK_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30,
    )

    if response.status_code != 200:
        print(f"Bedrock error: {response.status_code} — {response.text}")
        sys.exit(1)

    result = response.json()
    return result.get("content", [{}])[0].get("text", "")


def api_message(text):
    """Send message to Charles API."""
    response = requests.post(
        f"{API_URL}/message",
        json={"text": text},
        timeout=35,
    )
    response.raise_for_status()
    return response.json()


def api_forget(query):
    """Send forget request to Charles API."""
    response = requests.post(
        f"{API_URL}/forget",
        json={"query": query},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def forget(query):
    """Forget memories — try API first, fall back to local."""
    try:
        result = api_forget(query)
        forgotten = result["forgotten"]
    except Exception:
        # Local fallback
        memories = load_memories()
        remaining = [m for m in memories if query.lower() not in m["text"].lower()]
        forgotten = len(memories) - len(remaining)
        if forgotten > 0:
            save_memories(remaining)

    if forgotten == 0:
        print(f'Nothing to forget about "{query}"')
    else:
        print(f'Forgot {forgotten} memory{"s" if forgotten > 1 else ""} about "{query}"')


def main():
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else sys.stdin.read().strip()

    if not text:
        print("Usage: charles <text>")
        sys.exit(1)

    if text.startswith("forget "):
        forget(text[7:])
        return

    # Try API first, fall back to local
    try:
        result = api_message(text)
        reply = result.get("reply")
        if reply:
            print(reply)
        if result.get("notification_sent"):
            print("[notification sent to Charles Dana]")
    except Exception:
        # Local fallback: remember + ask Haiku directly
        memories = load_memories()
        memories.append({"text": text, "timestamp": datetime.now().isoformat()})
        save_memories(memories)
        reply = ask_haiku(text)
        print(reply)


if __name__ == "__main__":
    main()
