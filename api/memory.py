"""Memory management for Charles."""

import json
import os
from datetime import datetime
from typing import Optional

from .config import config


def _memories_path() -> str:
    return os.path.join(config.data_dir, "memories.json")


def _responses_path() -> str:
    return os.path.join(config.data_dir, "charles-dana", "responses.json")


def _manifest_path() -> str:
    return os.path.join(config.data_dir, "charles-dana", "MANIFEST.md")


def _ensure_dirs():
    os.makedirs(os.path.join(config.data_dir, "charles-dana"), exist_ok=True)


def load_memories() -> list:
    path = _memories_path()
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []


def save_memories(memories: list):
    _ensure_dirs()
    with open(_memories_path(), "w") as f:
        json.dump(memories, f, indent=2)


def add_memory(text: str) -> dict:
    memories = load_memories()
    entry = {"text": text, "timestamp": datetime.now().isoformat()}
    memories.append(entry)
    save_memories(memories)
    return entry


def forget(query: str) -> int:
    memories = load_memories()
    remaining = [m for m in memories if query.lower() not in m["text"].lower()]
    forgotten = len(memories) - len(remaining)
    if forgotten > 0:
        save_memories(remaining)
    return forgotten


def load_responses() -> list:
    path = _responses_path()
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []


def save_response(response: str, message_summary: str):
    _ensure_dirs()
    responses = load_responses()
    responses.append({
        "response": response,
        "message_summary": message_summary,
        "timestamp": datetime.now().isoformat(),
    })
    with open(_responses_path(), "w") as f:
        json.dump(responses, f, indent=2)


def load_manifest() -> str:
    path = _manifest_path()
    if os.path.exists(path):
        with open(path) as f:
            return f.read()
    return "No rules defined yet."


def get_recent_memories(n: int = 20) -> list:
    return load_memories()[-n:]


def get_recent_responses(n: int = 10) -> list:
    return load_responses()[-n:]


def memory_count() -> int:
    return len(load_memories())


def response_count() -> int:
    return len(load_responses())
