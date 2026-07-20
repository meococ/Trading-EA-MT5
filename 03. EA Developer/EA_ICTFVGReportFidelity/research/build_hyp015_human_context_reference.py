#!/usr/bin/env python3
"""Build the HYP-015 decision-time context reference without outcome access."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


HYPOTHESIS_ID = "HYP-ICT-FVG-HUMAN-CONTEXT-ENGINE-EURUSD-M5-015"
SCHEMA_VERSION = "human-context-reference.v1"
WORKSPACE = Path(__file__).resolve().parents[3]
POSITIONS = (
    WORKSPACE
    / "02. AlphaFactory/runtime/ictfvg_hyp012_context_forensics"
    / "positions_with_context.csv"
)
M5_DATA = (
    WORKSPACE
    / "02. AlphaFactory/runtime/ictfvg_hyp011_forensics"
    / "EURUSD_M5_2018_2026.parquet"
)
CASEBOOK_MANIFEST = (
    WORKSPACE
    / "02. AlphaFactory/runtime/ictfvg_hyp014_casebook/charts_h1_anatomy"
    / "cases_manifest.json"
)
OUTPUT_DIR = (
    WORKSPACE
    / "02. AlphaFactory/runtime/ictfvg_hyp015_human_context"
)
OUTPUT_CSV = OUTPUT_DIR / "human_context_reference.csv"
RESULT_JSON = OUTPUT_DIR / "human_context_reference_result.json"

POSITIONS_SHA256 = "1661ECE481CC1D52BE7751F445602ECE79AC1CA1F6F92AA6C2BF28594645B5B6"
M5_SHA256 = "AAF14451A0AA3671C5037A19ECB30E3A1A27B115A0F16CACBBB4D4209F921C73"
CASEBOOK_MANIFEST_SHA256 = (
    "0FF240AE20073999C0C02BE5CF8AFD48CBF41D2A3A124F03A3F59CF6055FB602"
)

HUMAN_RANGE_BARS = 20
HUMAN_PIVOT_STRENGTH = 2
HUMAN_PIVOT_LOOKBACK = 120
HUMAN_ATR_PERIOD = 14
TARGET_RR = 2.0
PIP_SIZE = 0.0001
POINT_SIZE = 0.00001

# pd.read_csv(usecols=...) is the enforcement boundary: the builder never loads
# exit, PnL, R-result, MFE/MAE, hold time or any other outcome field.
ALLOWED_POSITION_COLUMNS = (
    "position_id",
    "direction",
    "entry_time_server",
    "entry_time_utc",
    "entry",
    "risk_pts",
    "sweep_high",
    "sweep_low",
    "sweep_close",
    "confirmation_open",
    "confirmation_high",
    "confirmation_low",
    "confirmation_close",
)
FORBIDDEN_OUTCOME_COLUMNS = frozenset(
    {
        "exit_time_server",
        "exit_time_utc",
        "exit",
        "gross_before_commission",
        "commission",
        "net",
        "r_gross",
        "r_net",
        "hold_minutes",
        "hold_hours",
        "mfe",
        "mae",
    }
)

# Frozen chart-manifest parity anchors. Only identity and the context metric are
# carried here; no label, exit or trade result is loaded by this builder.
CASEBOOK_H1_RANGE_POSITION = {
    2034: 0.1699438202247147,
    3572: 0.5285524568393194,
    1936: 0.07089947089948925,
    2308: 0.6538461538461792,
    3812: 1.0311041990668703,
    2110: 0.6310904872389868,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def require_hash(path: Path, expected: str) -> None:
    actual = sha256(path)
    if actual != expected:
        raise SystemExit(f"hash mismatch: {path} expected={expected} actual={actual}")


def aggregate_ohlc(bars: pd.DataFrame, bucket: pd.Series) -> pd.DataFrame:
    frame = bars.assign(_bucket=bucket).groupby("_bucket", sort=True).agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
    )
    frame.index.name = "bucket_start"
    return frame


def prepare_frames(bars: pd.DataFrame) -> dict[str, pd.DataFrame]:
    server = pd.DatetimeIndex(bars["time_server"])
    h1_bucket = server.floor("1h")
    h4_bucket = server.floor("4h")
    day_bucket = server.normalize()
    week_bucket = day_bucket - pd.to_timedelta(server.weekday, unit="D")
    return {
        "H1": aggregate_ohlc(bars, pd.Series(h1_bucket, index=bars.index)),
        "H4": aggregate_ohlc(bars, pd.Series(h4_bucket, index=bars.index)),
        "D1": aggregate_ohlc(bars, pd.Series(day_bucket, index=bars.index)),
        "W1": aggregate_ohlc(bars, pd.Series(week_bucket, index=bars.index)),
    }


def completed(frame: pd.DataFrame, decision: pd.Timestamp, duration: pd.Timedelta) -> pd.DataFrame:
    cutoff = decision - duration
    return frame.loc[frame.index <= cutoff]


def atr(rates: pd.DataFrame, period: int) -> float:
    if len(rates) < period + 1:
        return float("nan")
    newest = rates.tail(period + 1).iloc[::-1].reset_index(drop=True)
    values = []
    for index in range(period):
        current = newest.iloc[index]
        previous_close = float(newest.iloc[index + 1]["close"])
        values.append(
            max(
                float(current["high"] - current["low"]),
                abs(float(current["high"]) - previous_close),
                abs(float(current["low"]) - previous_close),
            )
        )
    return float(np.mean(values))


def pivot_structure(rates: pd.DataFrame) -> tuple[int, float, float] | None:
    newest = rates.tail(
        HUMAN_PIVOT_LOOKBACK + 2 * HUMAN_PIVOT_STRENGTH + 2
    ).iloc[::-1].reset_index(drop=True)
    highs: list[float] = []
    lows: list[float] = []
    strength = HUMAN_PIVOT_STRENGTH
    for center in range(strength, len(newest) - strength):
        high = float(newest.iloc[center]["high"])
        low = float(newest.iloc[center]["low"])
        is_high = all(
            high > float(newest.iloc[center - distance]["high"])
            and high >= float(newest.iloc[center + distance]["high"])
            for distance in range(1, strength + 1)
        )
        is_low = all(
            low < float(newest.iloc[center - distance]["low"])
            and low <= float(newest.iloc[center + distance]["low"])
            for distance in range(1, strength + 1)
        )
        if is_high and len(highs) < 2:
            highs.append(high)
        if is_low and len(lows) < 2:
            lows.append(low)
        if len(highs) == 2 and len(lows) == 2:
            break
    if len(highs) < 2 or len(lows) < 2:
        return None
    structure = 0
    if highs[0] > highs[1] and lows[0] > lows[1]:
        structure = 1
    elif highs[0] < highs[1] and lows[0] < lows[1]:
        structure = -1
    return structure, highs[0], lows[0]


def partial_bar(
    bars_server: pd.DataFrame, decision: pd.Timestamp, duration: pd.Timedelta
) -> tuple[float, float, float, float] | None:
    bucket = decision.floor(duration)
    if bucket == decision:
        return 0.0, 0.0, 0.0, 0.0
    last_closed_open = decision - pd.Timedelta(minutes=5)
    available = bars_server.loc[bucket:last_closed_open]
    if available.empty:
        return None
    return (
        float(available["open"].iloc[0]),
        float(available["high"].max()),
        float(available["low"].min()),
        float(available["close"].iloc[-1]),
    )


def asia_range(
    bars_utc: pd.DataFrame, entry_utc: pd.Timestamp
) -> tuple[float, float] | None:
    start = entry_utc.normalize()
    end = start + pd.Timedelta(hours=7) - pd.Timedelta(minutes=5)
    asia = bars_utc.loc[start:end]
    if asia.empty:
        return None
    return float(asia["low"].min()), float(asia["high"].max())


def directional_run(
    bars_server: pd.DataFrame, decision: pd.Timestamp, direction: int
) -> int:
    closed = bars_server.loc[: decision - pd.Timedelta(minutes=5)].tail(32)
    run = 0
    for row in closed.iloc[::-1].itertuples(index=False):
        directional = row.close > row.open if direction > 0 else row.close < row.open
        if not directional:
            break
        run += 1
    return run


def add_pool(
    pools: list[tuple[str, float]], name: str, value: float | None
) -> None:
    if value is not None and np.isfinite(value) and value > 0.0:
        pools.append((name, float(value)))


def swept(direction: int, high: float, low: float, close: float, pool: float) -> bool:
    if direction > 0:
        return low < pool < close
    return close < pool < high


def build_row(
    position: pd.Series,
    bars_server: pd.DataFrame,
    bars_utc: pd.DataFrame,
    frames: dict[str, pd.DataFrame],
) -> dict[str, object]:
    decision = pd.Timestamp(position["entry_time_server"])
    entry_utc = pd.Timestamp(position["entry_time_utc"])
    direction = int(position["direction"])
    entry = float(position["entry"])
    risk = float(position["risk_pts"]) * POINT_SIZE
    h1 = completed(frames["H1"], decision, pd.Timedelta(hours=1))
    h4 = completed(frames["H4"], decision, pd.Timedelta(hours=4))
    current_day = decision.normalize()
    current_week = current_day - pd.Timedelta(days=decision.weekday())
    d1 = frames["D1"].loc[frames["D1"].index < current_day]
    w1 = frames["W1"].loc[frames["W1"].index < current_week]
    complete = (
        len(h1) >= HUMAN_PIVOT_LOOKBACK
        and len(h4) >= HUMAN_PIVOT_LOOKBACK
        and not d1.empty
        and not w1.empty
    )
    h1_structure = pivot_structure(h1) if complete else None
    h4_structure = pivot_structure(h4) if complete else None
    asia = asia_range(bars_utc, entry_utc) if complete else None
    partial_h1 = (
        partial_bar(bars_server, decision, pd.Timedelta(hours=1)) if complete else None
    )
    partial_h4 = (
        partial_bar(bars_server, decision, pd.Timedelta(hours=4)) if complete else None
    )
    complete = complete and all(
        value is not None for value in (h1_structure, h4_structure, asia, partial_h1, partial_h4)
    )
    if not complete:
        return {
            "position_id": int(position["position_id"]),
            "entry_time_utc": entry_utc.isoformat(),
            "direction": direction,
            "entry": entry,
            "valid": 0,
            "context_state": "INCOMPLETE",
        }

    h1_recent = h1.tail(HUMAN_RANGE_BARS)
    h4_recent = h4.tail(HUMAN_RANGE_BARS)
    h1_low, h1_high = float(h1_recent["low"].min()), float(h1_recent["high"].max())
    h4_low, h4_high = float(h4_recent["low"].min()), float(h4_recent["high"].max())
    h1_atr = atr(h1, HUMAN_ATR_PERIOD)
    h4_atr = atr(h4, HUMAN_ATR_PERIOD)
    closed_m5 = bars_server.loc[: decision - pd.Timedelta(minutes=5)]
    m5_atr = atr(closed_m5, HUMAN_ATR_PERIOD)
    h1_struct, h1_pivot_high, h1_pivot_low = h1_structure
    h4_struct, h4_pivot_high, h4_pivot_low = h4_structure
    previous_day = d1.iloc[-1]
    previous_week = w1.iloc[-1]
    asia_low, asia_high = asia
    pools: list[tuple[str, float]] = []
    for name, value in (
        ("PDH", previous_day["high"]),
        ("PDL", previous_day["low"]),
        ("PWH", previous_week["high"]),
        ("PWL", previous_week["low"]),
        ("ASIA_HIGH", asia_high),
        ("ASIA_LOW", asia_low),
        ("H1_PIVOT_HIGH", h1_pivot_high),
        ("H1_PIVOT_LOW", h1_pivot_low),
        ("H4_PIVOT_HIGH", h4_pivot_high),
        ("H4_PIVOT_LOW", h4_pivot_low),
    ):
        add_pool(pools, name, float(value))
    directional_pools = [
        (name, price, direction * (price - entry))
        for name, price in pools
        if direction * (price - entry) > POINT_SIZE
    ]
    nearest = min(directional_pools, key=lambda item: item[2]) if directional_pools else None
    nearest_distance = float(nearest[2]) if nearest else 0.0
    room_r = nearest_distance / risk if risk > POINT_SIZE else 0.0
    swept_count = sum(
        swept(
            direction,
            float(position["sweep_high"]),
            float(position["sweep_low"]),
            float(position["sweep_close"]),
            price,
        )
        for _, price in pools
    )
    h1_extension = (
        max(0.0, entry - h1_high) if direction > 0 else max(0.0, h1_low - entry)
    ) / h1_atr
    h4_extension = (
        max(0.0, entry - h4_high) if direction > 0 else max(0.0, h4_low - entry)
    ) / h4_atr
    if not directional_pools:
        state = "NO_DIRECTIONAL_TARGET"
    elif h1_extension > 0.0 or h4_extension > 0.0:
        state = "DIRECTIONAL_EXHAUSTION"
    elif h1_struct * direction < 0 and h4_struct * direction < 0:
        state = "STRUCTURE_CONFLICT"
    elif room_r < TARGET_RR:
        state = "INSUFFICIENT_ROOM"
    elif swept_count > 0:
        state = "EXTERNAL_SWEEP_WITH_ROOM"
    else:
        state = "INTERNAL_SWEEP_WITH_ROOM"
    confirmation_body = abs(
        float(position["confirmation_close"]) - float(position["confirmation_open"])
    )
    partial_h1_body = abs(partial_h1[3] - partial_h1[0]) / h1_atr
    partial_h4_body = abs(partial_h4[3] - partial_h4[0]) / h4_atr
    return {
        "position_id": int(position["position_id"]),
        "entry_time_utc": entry_utc.isoformat(),
        "direction": direction,
        "entry": entry,
        "valid": 1,
        "context_state": state,
        "h1_range_low": h1_low,
        "h1_range_high": h1_high,
        "h1_range_location": (entry - h1_low) / (h1_high - h1_low),
        "h4_range_low": h4_low,
        "h4_range_high": h4_high,
        "h4_range_location": (entry - h4_low) / (h4_high - h4_low),
        "h1_structure": h1_struct,
        "h4_structure": h4_struct,
        "h1_aligned": int(h1_struct * direction > 0),
        "h4_aligned": int(h4_struct * direction > 0),
        "h1_pivot_high": h1_pivot_high,
        "h1_pivot_low": h1_pivot_low,
        "h4_pivot_high": h4_pivot_high,
        "h4_pivot_low": h4_pivot_low,
        "previous_day_high": float(previous_day["high"]),
        "previous_day_low": float(previous_day["low"]),
        "previous_week_high": float(previous_week["high"]),
        "previous_week_low": float(previous_week["low"]),
        "asia_high": asia_high,
        "asia_low": asia_low,
        "nearest_pool_type": nearest[0] if nearest else "NONE",
        "nearest_pool_price": nearest[1] if nearest else 0.0,
        "nearest_pool_pips": nearest_distance / PIP_SIZE,
        "directional_pool_count": len(directional_pools),
        "room_r": room_r,
        "room_to_target": int(room_r >= TARGET_RR and nearest is not None),
        "external_sweep": int(swept_count > 0),
        "external_swept_count": swept_count,
        "partial_h1_body_atr": partial_h1_body,
        "partial_h4_body_atr": partial_h4_body,
        "confirmation_body_atr": confirmation_body / m5_atr,
        "directional_run_bars": directional_run(bars_server, decision, direction),
        "h1_extension_atr": h1_extension,
        "h4_extension_atr": h4_extension,
        "spread_to_risk": float("nan"),
    }


def main() -> int:
    require_hash(POSITIONS, POSITIONS_SHA256)
    require_hash(M5_DATA, M5_SHA256)
    require_hash(CASEBOOK_MANIFEST, CASEBOOK_MANIFEST_SHA256)
    if set(ALLOWED_POSITION_COLUMNS) & FORBIDDEN_OUTCOME_COLUMNS:
        raise SystemExit("allowed position schema contains an outcome field")
    positions = pd.read_csv(
        POSITIONS,
        usecols=list(ALLOWED_POSITION_COLUMNS),
        parse_dates=["entry_time_server", "entry_time_utc"],
    )
    required_reference_rows = 3385
    if len(positions) != required_reference_rows:
        raise SystemExit(
            f"row contract failed: expected={required_reference_rows} actual={len(positions)}"
        )
    bars = pd.read_parquet(
        M5_DATA,
        columns=["time_server", "time_utc", "open", "high", "low", "close"],
    ).sort_values("time_server", kind="stable").reset_index(drop=True)
    frames = prepare_frames(bars)
    bars_server = bars.set_index("time_server", drop=False)
    bars_utc = bars.sort_values("time_utc", kind="stable").set_index(
        "time_utc", drop=False
    )
    output = pd.DataFrame(
        [
            build_row(row, bars_server, bars_utc, frames)
            for _, row in positions.iterrows()
        ]
    ).sort_values("position_id", kind="stable").reset_index(drop=True)
    if output["position_id"].duplicated().any():
        raise SystemExit("duplicate position_id in reference output")
    parity = []
    for position_id, expected in CASEBOOK_H1_RANGE_POSITION.items():
        selected = output.loc[output["position_id"] == position_id]
        if len(selected) != 1:
            raise SystemExit(f"casebook position missing: {position_id}")
        actual = float(selected.iloc[0]["h1_range_location"])
        parity.append(
            {
                "position_id": position_id,
                "expected_range_position_20": expected,
                "actual_h1_range_location": actual,
                "absolute_error": abs(actual - expected),
            }
        )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output.to_csv(OUTPUT_CSV, index=False, lineterminator="\n", float_format="%.12g")
    complete_fraction = float(output["valid"].mean())
    maximum_error = max(item["absolute_error"] for item in parity)
    result = {
        "schema_version": SCHEMA_VERSION,
        "hypothesis_id": HYPOTHESIS_ID,
        "outcome_blind": True,
        "required_reference_rows": required_reference_rows,
        "input": {
            "positions_sha256": POSITIONS_SHA256,
            "m5_sha256": M5_SHA256,
            "casebook_manifest_sha256": CASEBOOK_MANIFEST_SHA256,
        },
        "rows": int(len(output)),
        "unique_position_ids": int(output["position_id"].nunique()),
        "complete_rows": int(output["valid"].sum()),
        "complete_fraction": complete_fraction,
        "maximum_six_case_h1_range_location_error": maximum_error,
        "casebook_parity": parity,
        "gates": {
            "row_count": len(output) == required_reference_rows,
            "no_duplicates": not output["position_id"].duplicated().any(),
            "complete_fraction_gte_0_99": complete_fraction >= 0.99,
            "six_case_h1_parity_lte_1e_9": maximum_error <= 1e-9,
        },
    }
    result["gates"]["all_passed"] = all(result["gates"].values())
    result["output_csv_sha256"] = sha256(OUTPUT_CSV)
    RESULT_JSON.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["gates"]["all_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
