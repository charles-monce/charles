"""Memory management for Charles."""

import json
import logging
import os
import tempfile
from datetime import datetime
from typing import Optional

from .config import config

logger = logging.getLogger(__name__)


def _memories_path() -> str:
    return os.path.join(config.data_dir, "memories.json")


def _responses_path() -> str:
    return os.path.join(config.data_dir, "charles-dana", "responses.json")


def _manifest_path() -> str:
    return os.path.join(config.data_dir, "charles-dana", "MANIFEST.md")


def _ensure_dirs():
    os.makedirs(os.path.join(config.data_dir, "charles-dana"), exist_ok=True)


def _safe_load_json(path: str) -> list:
    """Load a JSON list from path. Returns [] on missing file, corruption, or bad type."""
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        logger.warning(f"Expected list in {path}, got {type(data).__name__} — resetting")
        return []
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Corrupt JSON in {path}: {e} — backing up and resetting")
        _backup_corrupt(path)
        return []
    except Exception as e:
        logger.error(f"Failed to read {path}: {e}")
        return []


def _backup_corrupt(path: str):
    """Rename corrupt file so it's preserved but won't block the service."""
    backup = path + f".corrupt.{datetime.now().strftime('%Y%m%d%H%M%S')}"
    try:
        os.rename(path, backup)
        logger.info(f"Backed up corrupt file to {backup}")
    except OSError as e:
        logger.error(f"Could not back up {path}: {e}")


def _safe_write_json(path: str, data: list):
    """Atomic write: dump to temp file in same dir, then rename."""
    _ensure_dirs()
    dir_name = os.path.dirname(path)
    try:
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
    except Exception as e:
        logger.error(f"Failed to write {path}: {e}")
        # Clean up temp file if rename failed
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def load_memories() -> list:
    return _safe_load_json(_memories_path())


def save_memories(memories: list):
    _safe_write_json(_memories_path(), memories)


def add_memory(text: str, source: Optional[str] = None) -> dict:
    memories = load_memories()
    entry = {"text": text, "timestamp": datetime.now().isoformat()}
    if source:
        entry["source"] = source
    memories.append(entry)
    save_memories(memories)
    return entry


def forget(query: str) -> int:
    memories = load_memories()
    q = query.lower()
    remaining = [m for m in memories if q not in m.get("text", "").lower()]
    forgotten = len(memories) - len(remaining)
    if forgotten > 0:
        save_memories(remaining)
    return forgotten


def load_responses() -> list:
    return _safe_load_json(_responses_path())


def save_response(response: str, message_summary: str):
    responses = load_responses()
    responses.append({
        "response": response,
        "message_summary": message_summary,
        "timestamp": datetime.now().isoformat(),
    })
    _safe_write_json(_responses_path(), responses)


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
