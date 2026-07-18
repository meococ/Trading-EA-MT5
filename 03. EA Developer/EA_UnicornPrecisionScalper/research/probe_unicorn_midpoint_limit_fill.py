#!/usr/bin/env python3
"""Frozen no-PnL FVG-midpoint limit fill probe for HYP-UPS-XAU-M5-007."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5
import numpy as np

import probe_unicorn_event_anchored_closedbar as parent


HYPOTHESIS_ID = "HYP-UPS-XAU-M5-007"
EXPIRY_BARS = 3
MIN_FILL_RATE = 0.825


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def limit_fill_within(
    rates: np.ndarray,
    decision_index: int,
    direction: int,
    limit_price: float,
    sweep_extreme: float,
    expiry_bars: int = EXPIRY_BARS,
) -> dict[str, object]:
    """Evaluate resting-limit touch only; never calculate trade outcome/PnL."""
    for offset in range(1, expiry_bars + 1):
        index = decision_index + offset
        if index >= len(rates):
            return {"status": "insufficient_horizon", "offset": None}
        row = rates[index]
        if direction > 0:
            if float(row["low"]) <= limit_price:
                return {"status": "filled", "offset": offset, "bar_index": index}
            if float(row["close"]) <= sweep_extreme:
                return {"status": "invalidated", "offset": offset, "bar_index": index}
        else:
            if float(row["high"]) >= limit_price:
                return {"status": "filled", "offset": offset, "bar_index": index}
            if float(row["close"]) >= sweep_extreme:
                return {"status": "invalidated", "offset": offset, "bar_index": index}
    return {"status": "expired", "offset": None}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--terminal", type=Path, required=True)
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if not mt5.initialize(path=str(args.terminal), timeout=60_000, portable=True):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        terminal = mt5.terminal_info()
        if terminal is None or not terminal.connected:
            raise RuntimeError("MT5 terminal is not connected")
        data_path = Path(terminal.data_path).resolve()
        if data_path.drive.upper() != "D:":
            raise RuntimeError(f"portable MT5 data path must be on D:, got {data_path}")

        m5 = mt5.copy_rates_range(args.symbol, mt5.TIMEFRAME_M5, parent.WARMUP_FROM, parent.WINDOW_TO)
        h4 = mt5.copy_rates_range(
            args.symbol, mt5.TIMEFRAME_H4, parent.WARMUP_FROM - parent.timedelta(days=180), parent.WINDOW_TO
        )
        d1 = mt5.copy_rates_range(
            args.symbol, mt5.TIMEFRAME_D1, parent.WARMUP_FROM - parent.timedelta(days=3650), parent.WINDOW_TO
        )
        if m5 is None or h4 is None or d1 is None:
            raise RuntimeError(f"MT5 rates unavailable: {mt5.last_error()}")

        candidates, _ = parent.detect(m5, h4, d1)
        decision_index = {int(row["time"]) + 5 * 60: index for index, row in enumerate(m5)}
        rows: list[dict[str, object]] = []
        for candidate in candidates:
            decision = datetime.fromisoformat(str(candidate["decision_time_utc"]).replace("Z", "+00:00"))
            index = decision_index.get(int(decision.timestamp()))
            if index is None or index < 2:
                raise RuntimeError(f"candidate decision bar missing: {candidate['decision_time_utc']}")
            direction = 1 if candidate["direction"] == "long" else -1
            if direction > 0:
                fvg_low = float(m5[index - 2]["high"])
                fvg_high = float(m5[index]["low"])
            else:
                fvg_low = float(m5[index]["high"])
                fvg_high = float(m5[index - 2]["low"])
            if fvg_high <= fvg_low:
                raise RuntimeError(f"invalid FVG geometry at {candidate['decision_time_utc']}")
            limit_price = (fvg_low + fvg_high) / 2.0
            result = limit_fill_within(
                m5,
                index,
                direction,
                limit_price,
                float(candidate["sweep_extreme"]),
            )
            fill_time = None
            if result["status"] == "filled":
                fill_index = int(result["bar_index"])
                fill_time = datetime.fromtimestamp(
                    int(m5[fill_index]["time"]) + 5 * 60, tz=timezone.utc
                ).isoformat().replace("+00:00", "Z")
            rows.append(
                {
                    "decision_time_utc": candidate["decision_time_utc"],
                    "direction": candidate["direction"],
                    "sweep_age_bars": candidate["sweep_age_bars"],
                    "limit_price": round(limit_price, 6),
                    "status": result["status"],
                    "fill_offset_bars": result["offset"],
                    "fill_time_utc": fill_time,
                }
            )

        fills = [row for row in rows if row["status"] == "filled"]
        status_counts = Counter(str(row["status"]) for row in rows)
        direction_counts = Counter(str(row["direction"]) for row in fills)
        month_counts = Counter(str(row["fill_time_utc"])[:7] for row in fills)
        elapsed_weeks = (parent.WINDOW_TO - parent.WINDOW_FROM).total_seconds() / (7 * 24 * 60 * 60)
        fill_rate = len(fills) / len(rows) if rows else 0.0
        cadence = len(fills) / elapsed_weeks
        criteria = {
            "parent_candidates_eq_251": len(rows) == 251,
            "filled_cadence_ge_2_0": cadence >= 2.0,
            "filled_cadence_le_5_0": cadence <= 5.0,
            "fill_rate_ge_0_825": fill_rate >= MIN_FILL_RATE,
            "active_fill_months_ge_20": len(month_counts) >= 20,
            "long_fills_ge_30": direction_counts["long"] >= 30,
            "short_fills_ge_30": direction_counts["short"] >= 30,
        }
        verdict = "PASS" if all(criteria.values()) else "FAIL"
        payload = {
            "schema_version": "unicorn_midpoint_limit_fill_probe.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "purpose": "resting-limit fill feasibility only; no strategy outcome or PnL",
            "probe_script_sha256": sha256_file(Path(__file__)),
            "parent_probe_script_sha256": sha256_file(Path(parent.__file__)),
            "terminal": {
                "company": terminal.company,
                "build": terminal.build,
                "connected": bool(terminal.connected),
                "portable": True,
                "data_path": str(data_path),
            },
            "contract": {
                "limit": "FVG arithmetic midpoint",
                "expiry_bars": EXPIRY_BARS,
                "market_fallback": False,
                "outcomes_evaluated": False,
                "raw_bars_persisted_to_workspace": False,
            },
            "result": {
                "parent_candidates": len(rows),
                "filled_candidates": len(fills),
                "fill_rate": fill_rate,
                "filled_candidates_per_elapsed_week": cadence,
                "status_counts": dict(sorted(status_counts.items())),
                "direction_counts": dict(sorted(direction_counts.items())),
                "active_fill_months": len(month_counts),
                "monthly_fill_counts": dict(sorted(month_counts.items())),
                "criteria": criteria,
                "verdict": verdict,
            },
            "rows": rows,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(payload["result"], ensure_ascii=False))
        print(f"PROBE_ARTIFACT={args.output.resolve()}")
        return 0 if verdict == "PASS" else 2
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())

