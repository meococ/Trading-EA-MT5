#!/usr/bin/env python3
"""Build a fixed six-case post-run chart list for HYP-014 forensic review."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


WORKSPACE = Path(__file__).resolve().parents[3]
POSITIONS = (
    WORKSPACE
    / "02. AlphaFactory/runtime/ictfvg_hyp012_context_forensics/positions_with_context.csv"
)
PREDICTIONS = (
    WORKSPACE
    / "02. AlphaFactory/runtime/ictfvg_hyp014_probability_probe/rolling_oos_predictions.csv"
)
OUTPUT_DIR = WORKSPACE / "02. AlphaFactory/runtime/ictfvg_hyp014_casebook"
POINT = 0.00001


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    positions = pd.read_csv(POSITIONS)
    predictions = pd.read_csv(PREDICTIONS)
    accepted = predictions[predictions["accepted"] == 1].copy()
    winners = accepted[accepted["r_x1_0"] > 0].nlargest(3, "score")
    losers = accepted[accepted["r_x1_0"] <= 0].nlargest(3, "score")
    selected = pd.concat([winners, losers], ignore_index=True)
    selected["case_id"] = ["PRW01", "PRW02", "PRW03", "PRL01", "PRL02", "PRL03"]
    selected["reason"] = [
        "accepted_high_score_winner",
        "accepted_high_score_winner",
        "accepted_high_score_winner",
        "accepted_high_score_loser",
        "accepted_high_score_loser",
        "accepted_high_score_loser",
    ]
    merged = selected.merge(positions, on="position_id", validate="one_to_one", suffixes=("_prediction", ""))

    rows: list[dict[str, object]] = []
    for record in merged.to_dict(orient="records"):
        direction = int(record["direction"])
        risk_price = float(record["risk_pts"]) * POINT
        server_to_utc = pd.Timestamp(record["entry_time_server"]) - pd.Timestamp(record["entry_time_utc"])
        sweep_time_utc = pd.Timestamp(record["sweep_time_server"]) - server_to_utc
        confirmation_time_utc = pd.Timestamp(record["confirmation_time_server"]) - server_to_utc
        rows.append(
            {
                "case_id": record["case_id"],
                "position_id": int(record["position_id"]),
                "entry_time_utc": record["entry_time_utc"],
                "exit_time_utc": record["exit_time_utc"],
                "direction": direction,
                "entry": float(record["entry"]),
                "sl": float(record["entry"] - direction * risk_price),
                "tp": float(record["entry"] + direction * 2.0 * risk_price),
                "exit": float(record["exit"]),
                "reason": record["reason"],
                "sweep_time_utc": sweep_time_utc,
                "pivot": float(record["pivot"]),
                "sweep_open": float(record["sweep_open"]),
                "sweep_high": float(record["sweep_high"]),
                "sweep_low": float(record["sweep_low"]),
                "sweep_close": float(record["sweep_close"]),
                "sweep_depth_pips": float(record["sweep_depth_pips"]),
                "sweep_reclaim_pips": float(record["sweep_reclaim_pips"]),
                "confirmation_time_utc": confirmation_time_utc,
                "confirmation_open": float(record["confirmation_open"]),
                "confirmation_high": float(record["confirmation_high"]),
                "confirmation_low": float(record["confirmation_low"]),
                "confirmation_close": float(record["confirmation_close"]),
                "confirmation_body_vs_prior20": float(record["confirmation_body_vs_prior20"]),
                "confirmation_directional_close_location": float(
                    record["confirmation_directional_close_location"]
                ),
                "bars_after_sweep": int(record["bars_after_sweep"]),
                "label": (
                    f"pid={int(record['position_id'])}; score={record['score']:.3f}; "
                    f"costR={record['r_x1_0']:.3f}; confirm="
                    f"{record['confirmation_body_vs_prior20']:.2f}x"
                ),
            }
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cases_path = OUTPUT_DIR / "cases.csv"
    pd.DataFrame(rows).to_csv(cases_path, index=False, lineterminator="\n")
    receipt = {
        "schema_version": "hyp014.casebook_selection.v1",
        "hypothesis_id": "HYP-ICT-FVG-PROB-RANK-EURUSD-M5-014",
        "purpose": "post-run visual forensics only; no rule or threshold authority",
        "selection": "top three accepted x1-cost winners and top three accepted x1-cost non-winners by frozen model score",
        "positions_sha256": sha256(POSITIONS),
        "predictions_sha256": sha256(PREDICTIONS),
        "cases_path": str(cases_path),
        "cases_sha256": sha256(cases_path),
        "position_ids": [int(value) for value in selected["position_id"]],
    }
    (OUTPUT_DIR / "selection_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"HYP014_CASEBOOK PASS cases={len(rows)} ids={receipt['position_ids']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

