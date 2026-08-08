import json
import logging
import threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Protect file writes and in-memory dedup set if multiple threads/processes are ever used
_log_lock = threading.Lock()
_seen_skills: set[str] = set()


def log_unrecognized_skill(skill_text: str, source: str, job_id: str, batch_date: Optional[str] = None):
    """
    Logs an unrecognized skill to a JSONL file for offline LLM-assisted labeling.
    Dedup per process: same skill_text only written once.
    """
    if not skill_text or not skill_text.strip():
        return

    skill_text = skill_text.strip()

    with _log_lock:
        if skill_text in _seen_skills:
            return
        _seen_skills.add(skill_text)

    metadata_dir = Path("data/metadata")
    metadata_dir.mkdir(parents=True, exist_ok=True)

    log_file = metadata_dir / "unrecognized_skills.jsonl"

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_text": skill_text,
        "source": source,
        "job_id": job_id,
        "batch_date": batch_date
    }

    try:
        with _log_lock:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"Failed to log unrecognized skill '{skill_text}': {e}")


def log_unrecognized_role(title: str, source: str, job_id: str, batch_date: Optional[str] = None):
    """
    Logs a job title that could not be classified into any canonical role.
    Similar to log_unrecognized_skill but for role extraction gaps.
    """
    if not title or not title.strip():
        return

    title = title.strip()

    metadata_dir = Path("data/metadata")
    metadata_dir.mkdir(parents=True, exist_ok=True)

    log_file = metadata_dir / "unrecognized_roles.jsonl"

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_text": title,
        "source": source,
        "job_id": job_id,
        "batch_date": batch_date
    }

    try:
        with _log_lock:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"Failed to log unrecognized role '{title}': {e}")
