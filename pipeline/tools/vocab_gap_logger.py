import json
import logging
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Protect file writes if multiple threads/processes are ever used
_log_lock = threading.Lock()

def log_unrecognized_skill(skill_text: str, source: str, job_id: str, batch_date: Optional[str] = None):
    """
    Logs an unrecognized skill to a JSONL file for offline LLM-assisted labeling.
    """
    if not skill_text or not skill_text.strip():
        return

    skill_text = skill_text.strip()
    
    metadata_dir = Path("data/metadata")
    metadata_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = metadata_dir / "unrecognized_skills.jsonl"
    
    record = {
        "timestamp": datetime.utcnow().isoformat(),
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
