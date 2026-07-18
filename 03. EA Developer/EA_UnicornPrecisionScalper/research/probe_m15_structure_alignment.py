#!/usr/bin/env python3
"""Measure closed-bar M15 swing-structure alignment without trade outcomes."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def confirmed_pivots(
    bars: list[dict[str, object]], field: str, strength: int, *, find_highs: bool
) -> list[tuple[int, float]]:
    if strength < 1:
        raise ValueError("pivot strength must be at least 1")
    pivots: list[tuple[int, float]] = []
    for index in range(strength, len(bars) - strength):
        value = float(bars[index][field])
        neighbours = (
            float(bars[offset][field])
            for offset in range(index - strength, index + strength + 1)
            if offset != index
        )
        if all(value > other for other in neighbours) if find_highs else all(
            value < other for other in neighbours
        ):
            pivots.append((index, value))
    return pivots


def structure_state(bars: list[dict[str, object]], strength: int = 2) -> int:
    """Return 1 for HH+HL, -1 for LH+LL, otherwise 0.

    Bars must be completed and sorted oldest to newest. A pivot is confirmed only
    when ``strength`` newer completed bars exist, so the result does not repaint at
    the supplied information cutoff.
    """

    highs = confirmed_pivots(bars, "h", strength, find_highs=True)
    lows = confirmed_pivots(bars, "l", strength, find_highs=False)
    if len(highs) < 2 or len(lows) < 2:
        return 0
    older_high, newer_high = highs[-2][1], highs[-1][1]
    older_low, newer_low = lows[-2][1], lows[-1][1]
    if newer_high > older_high and newer_low > older_low:
        return 1
    if newer_high < older_high and newer_low < older_low:
        return -1
    return 0


def load_rows(paths: Iterable[Path]) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    rows: list[dict[str, object]] = []
    inputs: list[dict[str, str]] = []
    event_ids: set[str] = set()
    for path in sorted(paths):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("authority") != "PRE_OUTCOME_LABEL_CONTEXT_ONLY":
            raise ValueError(f"unexpected authority in {path}")
        if payload.get("outcomes_included") is not False:
            raise ValueError(f"outcome-bearing context rejected: {path}")
        batch_rows = payload.get("rows")
        if not isinstance(batch_rows, list) or payload.get("row_count") != len(batch_rows):
            raise ValueError(f"row-count mismatch in {path}")
        for row in batch_rows:
            detector = row.get("detector", {})
            event_id = str(detector.get("event_id", ""))
            if not event_id or event_id in event_ids:
                raise ValueError(f"missing or duplicate event id: {event_id}")
            event_ids.add(event_id)
            cutoff = parse_utc(str(row["information_cutoff_utc"]))
            m15 = row.get("completed_bar_context", {}).get("m15")
            if not isinstance(m15, list) or not m15:
                raise ValueError(f"missing M15 context for {event_id}")
            stamps = [parse_utc(str(bar["t"])) for bar in m15]
            if stamps != sorted(stamps):
                raise ValueError(f"M15 context not chronological for {event_id}")
            if any(stamp + timedelta(minutes=15) > cutoff for stamp in stamps):
                raise ValueError(f"future/incomplete M15 bar for {event_id}")
            rows.append(row)
        inputs.append({"path": str(path.resolve()), "sha256": sha256_file(path)})
    return rows, inputs


def analyze(rows: list[dict[str, object]], strength: int) -> dict[str, object]:
    states: Counter[str] = Counter()
    directions: Counter[str] = Counter()
    aligned = 0
    for row in rows:
        detector = row["detector"]
        direction_name = str(detector["direction"])
        direction = 1 if direction_name == "long" else -1 if direction_name == "short" else 0
        if direction == 0:
            raise ValueError(f"unexpected detector direction: {direction_name}")
        state = structure_state(row["completed_bar_context"]["m15"], strength)
        state_name = {1: "bull", -1: "bear", 0: "neutral"}[state]
        states[state_name] += 1
        directions[direction_name] += 1
        if state == direction:
            aligned += 1
    total = len(rows)
    return {
        "rows": total,
        "pivot_strength": strength,
        "definition": "two latest confirmed M15 swing highs and lows form HH+HL or LH+LL",
        "state_counts": dict(sorted(states.items())),
        "direction_counts": dict(sorted(directions.items())),
        "aligned_rows": aligned,
        "aligned_fraction": aligned / total if total else 0.0,
        "outcomes_read": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pivot-strength", type=int, default=2)
    args = parser.parse_args()

    paths = list(args.context_dir.glob("label_context_batch_*.json"))
    if not paths:
        raise ValueError(f"no label context batches found in {args.context_dir}")
    rows, inputs = load_rows(paths)
    result = {
        "schema_version": "unicorn_m15_structure_probe.v1",
        "authority": "PRE_OUTCOME_FIDELITY_PROBE_ONLY",
        "inputs": inputs,
        "result": analyze(rows, args.pivot_strength),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
