"""Append-only audit trail of agent-loop activity.

Every chat turn appends records to `output/audit_trail.json` — one per tool call
(time, tool, short args, short result) plus one `run_end` record carrying the stop
reason. The file is a JSON array and is **never wiped**: existing records are read,
the new ones appended, and the whole array rewritten atomically (temp file +
rename) so a crash mid-write cannot corrupt or truncate the history.

Writing is best-effort: auditing must never take down a chat reply, so any failure
here is swallowed (the turn still succeeds).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"

# Keep stored args/results short — this is an activity log, not a data dump.
_MAX_FIELD = 300


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def short(value: object, limit: int = _MAX_FIELD) -> str:
    """A compact, single-line string form of any value, truncated."""
    try:
        text = value if isinstance(value, str) else json.dumps(value, default=str)
    except (TypeError, ValueError):
        text = str(value)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def append_events(events: list[dict]) -> None:
    """Append records to the trail, preserving everything already there."""
    if not events:
        return
    try:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        existing = _read_existing()
        existing.extend(events)
        _atomic_write(existing)
    except Exception:
        # Never let auditing break a chat turn.
        pass


def _read_existing() -> list[dict]:
    if not AUDIT_PATH.exists():
        return []
    try:
        data = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        # Corrupt/partial file: do not wipe it — set it aside and start fresh so
        # the prior bytes are still recoverable on disk.
        try:
            AUDIT_PATH.replace(AUDIT_PATH.with_suffix(".json.bak"))
        except OSError:
            pass
        return []


def _atomic_write(records: list[dict]) -> None:
    tmp = AUDIT_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(records, indent=2, default=str), encoding="utf-8")
    os.replace(tmp, AUDIT_PATH)
