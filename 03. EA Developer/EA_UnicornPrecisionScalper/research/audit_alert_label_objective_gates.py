#!/usr/bin/env python3
"""Exploratory no-outcome precheck for objective Unicorn label components."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


LABEL_FIELDS = (
    "label_true_sweep_liquidity",
    "label_true_displacement",
    "label_true_mss_bos_close",
    "label_valid_breaker",
    "label_fvg_fresh_unfilled",
    "label_micro_confirm_present",
    "label_core_setup_accept",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def pivots(bars: list[dict[str, object]], field: str, high: bool) -> list[int]:
    result: list[int] = []
    for index in range(2, len(bars) - 2):
        value = float(bars[index][field])
        neighbors = [
            float(bars[index - 2][field]),
            float(bars[index - 1][field]),
            float(bars[index + 1][field]),
            float(bars[index + 2][field]),
        ]
        if (high and value > max(neighbors)) or (not high and value < min(neighbors)):
            result.append(index)
    return result


def latest_confirmed_pivot(
    bars: list[dict[str, object]], sweep_index: int, high: bool
) -> tuple[int, float] | None:
    field = "h" if high else "l"
    eligible = [index for index in pivots(bars, field, high) if index + 2 < sweep_index]
    if not eligible:
        return None
    index = eligible[-1]
    return index, float(bars[index][field])


def label_displacement(detector: dict[str, object], bars: list[dict[str, object]]) -> tuple[str, dict[str, object]]:
    displacement = bars[-2]
    candle_range = float(displacement["h"]) - float(displacement["l"])
    if candle_range <= 0.0:
        return "ambiguous", {"reason": "zero_range_displacement"}
    close_location = (float(displacement["c"]) - float(displacement["l"])) / candle_range
    direction = detector["direction"]
    outer_quartile = close_location >= 0.75 if direction == "long" else close_location <= 0.25
    body_gate = float(detector["displacement_atr"]) >= 1.50
    return (
        "yes" if body_gate and outer_quartile else "no",
        {
            "bar_time": displacement["t"],
            "body_atr": detector["displacement_atr"],
            "close_location": round(close_location, 6),
            "body_gate": body_gate,
            "outer_quartile": outer_quartile,
        },
    )


def label_sweep_and_mss(
    detector: dict[str, object], bars: list[dict[str, object]]
) -> tuple[str, str, dict[str, object]]:
    age = int(detector["sweep_age_bars"])
    sweep_index = len(bars) - 3 - age
    if sweep_index < 12 or sweep_index >= len(bars) - 2:
        return "ambiguous", "ambiguous", {"reason": "sweep_index_out_of_context"}
    direction = detector["direction"]
    sweep_bar = bars[sweep_index]
    liquidity = latest_confirmed_pivot(bars, sweep_index, high=direction == "short")
    if liquidity is None:
        return "ambiguous", "ambiguous", {"reason": "no_confirmed_pre_sweep_pivot"}
    liquidity_index, liquidity_level = liquidity
    tolerance = 0.011
    if direction == "long":
        swept = float(sweep_bar["l"]) < liquidity_level
        reclaimed = float(sweep_bar["c"]) > liquidity_level
        extreme_matches = abs(float(sweep_bar["l"]) - float(detector["sweep_extreme"])) <= tolerance
        opposing = latest_confirmed_pivot(bars, sweep_index, high=True)
        broke = False if opposing is None else any(
            float(bar["c"]) > opposing[1] for bar in bars[sweep_index + 1 :]
        )
    else:
        swept = float(sweep_bar["h"]) > liquidity_level
        reclaimed = float(sweep_bar["c"]) < liquidity_level
        extreme_matches = abs(float(sweep_bar["h"]) - float(detector["sweep_extreme"])) <= tolerance
        opposing = latest_confirmed_pivot(bars, sweep_index, high=False)
        broke = False if opposing is None else any(
            float(bar["c"]) < opposing[1] for bar in bars[sweep_index + 1 :]
        )
    sweep_label = "yes" if swept and reclaimed and extreme_matches else "no"
    mss_label = "ambiguous" if opposing is None else ("yes" if broke else "no")
    return sweep_label, mss_label, {
        "sweep_bar_time": sweep_bar["t"],
        "sweep_index": sweep_index,
        "liquidity_pivot_time": bars[liquidity_index]["t"],
        "liquidity_level": liquidity_level,
        "swept": swept,
        "reclaimed": reclaimed,
        "extreme_matches": extreme_matches,
        "mss_anchor_time": None if opposing is None else bars[opposing[0]]["t"],
        "mss_anchor_level": None if opposing is None else opposing[1],
        "mss_close_break": broke,
    }


def label_fvg(detector: dict[str, object], bars: list[dict[str, object]]) -> tuple[str, dict[str, object]]:
    left, _, right = bars[-3:]
    tolerance = 0.011
    if detector["direction"] == "long":
        low, high = float(left["h"]), float(right["l"])
        exists = high > low
    else:
        low, high = float(right["h"]), float(left["l"])
        exists = high > low
    bounds_match = (
        abs(low - float(detector["fvg_low"])) <= tolerance
        and abs(high - float(detector["fvg_high"])) <= tolerance
    )
    return (
        "yes" if exists and bounds_match else "no",
        {
            "formation_bar_time": right["t"],
            "exists": exists,
            "bounds_match": bounds_match,
            "derived_low": low,
            "derived_high": high,
            "post_formation_completed_bars": 0,
        },
    )


def breaker_precheck(detector: dict[str, object], bars: list[dict[str, object]]) -> tuple[str, dict[str, object]]:
    left_index = len(bars) - 3
    start = max(0, left_index - 6)
    low = float(detector["fvg_low"])
    high = float(detector["fvg_high"])
    width = high - low
    candidates: list[dict[str, object]] = []
    for index in range(start, left_index + 1):
        bar = bars[index]
        opposite = (
            float(bar["c"]) < float(bar["o"])
            if detector["direction"] == "long"
            else float(bar["c"]) > float(bar["o"])
        )
        if not opposite or width <= 0.0:
            continue
        body_low = min(float(bar["o"]), float(bar["c"]))
        body_high = max(float(bar["o"]), float(bar["c"]))
        overlap = max(0.0, min(high, body_high) - max(low, body_low)) / width
        invalidated = any(
            (
                float(later["c"]) > float(bar["h"])
                if detector["direction"] == "long"
                else float(later["c"]) < float(bar["l"])
            )
            for later in bars[index + 1 :]
        )
        if overlap >= 0.10:
            candidates.append(
                {
                    "bar_time": bar["t"],
                    "body_overlap_ratio": round(overlap, 6),
                    "invalidation_close_visible": invalidated,
                }
            )
    geometry_present = any(item["invalidation_close_visible"] for item in candidates)
    # The memo never freezes which failed order block is the breaker. Geometry
    # can reject an impossible row, but it cannot promote a proxy to a true label.
    label = "ambiguous" if geometry_present else "no"
    return label, {
        "geometry_candidate_count": len(candidates),
        "failed_block_geometry_visible": geometry_present,
        "candidates": candidates,
        "taxonomy_authority": "insufficient_for_yes_label",
    }


def review(row: dict[str, object]) -> dict[str, object]:
    detector = row["detector"]
    bars = row["completed_bar_context"]["m5"]
    displacement, displacement_evidence = label_displacement(detector, bars)
    sweep, mss, structure_evidence = label_sweep_and_mss(detector, bars)
    fvg, fvg_evidence = label_fvg(detector, bars)
    breaker, breaker_evidence = breaker_precheck(detector, bars)
    micro = "no"  # the logged FVG forms on the decision bar; no later closed bar exists
    components = [sweep, displacement, mss, breaker, fvg]
    if "no" in components:
        core = "no"
    elif "ambiguous" in components:
        core = "ambiguous"
    else:
        core = "yes"
    objective_ex_breaker = "yes" if all(
        value == "yes" for value in [sweep, displacement, mss, fvg]
    ) else "no"
    reason_order = [
        (sweep, "SWEEP_FALSE_OR_AMBIGUOUS"),
        (displacement, "DISPLACEMENT_WEAK"),
        (mss, "NO_MSS_CLOSE_OR_AMBIGUOUS"),
        (breaker, "BREAKER_INVALID_OR_AMBIGUOUS"),
        (fvg, "FVG_INVALID"),
    ]
    reason = next((code for value, code in reason_order if value != "yes"), "")
    return {
        "event_id": detector["event_id"],
        "decision_time_utc": detector["decision_time_utc"],
        "direction": detector["direction"],
        "label_true_sweep_liquidity": sweep,
        "label_true_displacement": displacement,
        "label_true_mss_bos_close": mss,
        "label_valid_breaker": breaker,
        "label_fvg_fresh_unfilled": fvg,
        "label_micro_confirm_present": micro,
        "label_core_setup_accept": core,
        "objective_core_ex_breaker": objective_ex_breaker,
        "entry_readiness": "reject" if core == "no" else "ambiguous",
        "primary_reject_reason": reason,
        "reviewer_id": "CODEX_OBJECTIVE_PRECHECK_V1",
        "reviewer_type": "AI_EXPLORATORY",
        "outcome_seen": False,
        "evidence": {
            "displacement": displacement_evidence,
            "structure": structure_evidence,
            "fvg": fvg_evidence,
            "breaker": breaker_evidence,
            "micro": {"post_formation_completed_bars": 0},
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context-dir", type=Path, required=True)
    parser.add_argument("--rubric", type=Path, required=True)
    parser.add_argument("--overlay", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()

    source_paths = sorted(args.context_dir.glob("label_context_batch_*.json"))
    rows: list[dict[str, object]] = []
    for path in source_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("outcomes_included") is not False:
            raise ValueError(f"context is not outcome-free: {path}")
        rows.extend(payload["rows"])
    if len(rows) != 200:
        raise ValueError(f"expected 200 context rows; found {len(rows)}")
    labels = [review(row) for row in rows]

    args.overlay.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "event_id",
        "decision_time_utc",
        "direction",
        *LABEL_FIELDS,
        "objective_core_ex_breaker",
        "entry_readiness",
        "primary_reject_reason",
        "reviewer_id",
        "reviewer_type",
        "outcome_seen",
    ]
    with args.overlay.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(labels)

    distributions = {
        field: dict(Counter(str(row[field]) for row in labels)) for field in LABEL_FIELDS
    }
    summary = {
        "schema_version": "unicorn_alert_objective_label_precheck.v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "authority": "AI_EXPLORATORY_PRE_OUTCOME_ONLY",
        "outcomes_seen": False,
        "human_label_gate_satisfied": False,
        "review_rows": len(labels),
        "rubric_sha256": sha256_file(args.rubric),
        "context_manifest_sha256": sha256_file(args.context_dir / "manifest.json"),
        "overlay_sha256": sha256_file(args.overlay),
        "distributions": distributions,
        "objective_core_ex_breaker_yes": sum(
            row["objective_core_ex_breaker"] == "yes" for row in labels
        ),
        "accepted_density": 0.0,
        "accepted_density_is_authoritative": False,
        "blocking_reason": (
            "breaker taxonomy lacks enough frozen authority for a yes label; "
            "independent human labels and kappa remain mandatory"
        ),
        "micro_confirmation_design_finding": (
            "all logged FVGs form on the decision bar, so the collector cannot "
            "contain a post-formation micro-confirmation at that same decision"
        ),
        "labels": labels,
    }
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "labels"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

