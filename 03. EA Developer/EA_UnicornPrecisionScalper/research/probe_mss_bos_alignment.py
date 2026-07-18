#!/usr/bin/env python3
"""Probe closed-bar sweep-to-MSS/BOS sequencing without reading outcomes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from probe_m15_structure_alignment import (
    confirmed_pivots,
    load_rows,
    structure_state,
)


def mss_bos_close(
    m5: list[dict[str, object]],
    *,
    direction: int,
    sweep_age_bars: int,
    strength: int = 2,
) -> tuple[bool, float | None, int | None]:
    """Return whether a post-sweep close breaks the last pre-sweep swing.

    Context bars are oldest to newest. The detector's sweep age is measured from
    the three-bar FVG left candle, so its MQL series index is ``age + 2``.
    """

    if direction not in {-1, 1}:
        raise ValueError("direction must be -1 or 1")
    if sweep_age_bars < 0:
        raise ValueError("sweep age cannot be negative")
    sweep_index = len(m5) - 1 - (sweep_age_bars + 2)
    if sweep_index <= 2 * strength or sweep_index >= len(m5) - 1:
        return False, None, None

    if direction > 0:
        pivots = confirmed_pivots(
            m5[: sweep_index + 1], "h", strength, find_highs=True
        )
    else:
        pivots = confirmed_pivots(
            m5[: sweep_index + 1], "l", strength, find_highs=False
        )
    if not pivots:
        return False, None, None
    level = pivots[-1][1]
    for index in range(sweep_index + 1, len(m5)):
        close = float(m5[index]["c"])
        if (direction > 0 and close > level) or (direction < 0 and close < level):
            return True, level, index
    return False, level, None


def analyze(rows: list[dict[str, object]], strength: int) -> dict[str, object]:
    mss_rows = 0
    m15_rows = 0
    combined_rows = 0
    by_direction = {
        "long": {"rows": 0, "mss": 0, "m15": 0, "combined": 0},
        "short": {"rows": 0, "mss": 0, "m15": 0, "combined": 0},
    }
    for row in rows:
        detector = row["detector"]
        name = str(detector["direction"])
        direction = 1 if name == "long" else -1 if name == "short" else 0
        if direction == 0:
            raise ValueError(f"unexpected direction: {name}")
        has_mss, _, _ = mss_bos_close(
            row["completed_bar_context"]["m5"],
            direction=direction,
            sweep_age_bars=int(detector["sweep_age_bars"]),
            strength=strength,
        )
        m15_aligned = (
            structure_state(row["completed_bar_context"]["m15"], strength)
            == direction
        )
        by_direction[name]["rows"] += 1
        if has_mss:
            mss_rows += 1
            by_direction[name]["mss"] += 1
        if m15_aligned:
            m15_rows += 1
            by_direction[name]["m15"] += 1
        if has_mss and m15_aligned:
            combined_rows += 1
            by_direction[name]["combined"] += 1
    total = len(rows)
    return {
        "rows": total,
        "pivot_strength": strength,
        "definition": "after the sweep, a completed M5 bar closes through the latest confirmed pre-sweep opposing swing",
        "mss_rows": mss_rows,
        "mss_fraction": mss_rows / total if total else 0.0,
        "m15_aligned_rows": m15_rows,
        "m15_plus_mss_rows": combined_rows,
        "m15_plus_mss_fraction": combined_rows / total if total else 0.0,
        "by_direction": by_direction,
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
    payload = {
        "schema_version": "unicorn_mss_bos_probe.v1",
        "authority": "PRE_OUTCOME_FIDELITY_PROBE_ONLY",
        "inputs": inputs,
        "result": analyze(rows, args.pivot_strength),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
