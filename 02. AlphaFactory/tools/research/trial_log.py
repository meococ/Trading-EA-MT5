"""Canonical trial-log appender (numpy-safe, single serialization).

Every executed evaluation of a frozen config is one appended line; rows must
self-authenticate via hypothesis_id + prereg_sha256. One writer, one format —
never hand-append with ad-hoc json.dumps.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REQUIRED = ("hypothesis_id", "prereg_sha256")


def numpy_safe(obj):
    """json.dumps default= converter for numpy scalars/arrays."""
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"not JSON serializable: {type(obj).__name__}")


def append_trial(path: Path, record: dict) -> None:
    missing = [k for k in REQUIRED if not record.get(k)]
    if missing:
        raise ValueError(f"trial record missing required fields: {missing}")
    record.setdefault("ts_utc", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    line = json.dumps(record, ensure_ascii=True, separators=(",", ":"),
                      default=numpy_safe)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(line + "\n")
