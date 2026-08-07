#!/usr/bin/env python3
"""Population and frozen matched-pair diagnostics for RSF Cell 16."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


SCHEMA = "rsf_cell16_forensic_metrics.v1"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def summarize(frame: pd.DataFrame, label: str) -> dict:
    wins = frame[frame.net_profit > 0]
    losses = frame[frame.net_profit <= 0]
    gross_win = float(wins.net_profit.sum())
    gross_loss = float(-losses.net_profit.sum())
    avg_win_r = float(wins.net_r.mean()) if len(wins) else 0.0
    avg_loss_r = float(losses.net_r.mean()) if len(losses) else 0.0
    payoff_r = avg_win_r / abs(avg_loss_r) if avg_loss_r else 0.0
    return {
        "bucket": label,
        "trades": int(len(frame)),
        "wins": int(len(wins)),
        "win_rate_pct": float(100 * len(wins) / len(frame)) if len(frame) else 0.0,
        "net_profit": float(frame.net_profit.sum()),
        "profit_factor": gross_win / gross_loss if gross_loss else 0.0,
        "mean_net_r": float(frame.net_r.mean()) if len(frame) else 0.0,
        "median_net_r": float(frame.net_r.median()) if len(frame) else 0.0,
        "avg_win_r": avg_win_r,
        "avg_loss_r": avg_loss_r,
        "payoff_r": payoff_r,
        "breakeven_win_rate_pct": 100 / (1 + payoff_r) if payoff_r else 100.0,
        "avg_initial_risk_account": float(frame.initial_risk_account.mean()) if len(frame) else 0.0,
        "median_holding_minutes": float(frame.holding_minutes.median()) if len(frame) else 0.0,
    }


def grouped(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    rows = [summarize(group, str(key)) for key, group in frame.groupby(column, dropna=False)]
    return pd.DataFrame(rows).sort_values("bucket")


def conservative_path_stats(trades: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame:
    bars = bars.set_index("time_utc").sort_index()
    rows = []
    for trade in trades.itertuples(index=False):
        entry_t = pd.Timestamp(trade.entry_time_utc)
        exit_t = pd.Timestamp(trade.exit_time_utc)
        risk = abs(float(trade.entry_price) - float(trade.initial_sl))
        first = entry_t.ceil("5min")
        last = (exit_t - pd.Timedelta(minutes=5)).floor("5min")
        path = bars.loc[first:last] if first <= last else bars.iloc[0:0]
        prices_high = [float(trade.entry_price), float(trade.exit_price)]
        prices_low = [float(trade.entry_price), float(trade.exit_price)]
        if not path.empty:
            prices_high.append(float(path.high.max()))
            prices_low.append(float(path.low.min()))
        if int(trade.direction) > 0:
            mfe = (max(prices_high) - float(trade.entry_price)) / risk if risk else 0.0
            mae = (float(trade.entry_price) - min(prices_low)) / risk if risk else 0.0
        else:
            mfe = (float(trade.entry_price) - min(prices_low)) / risk if risk else 0.0
            mae = (max(prices_high) - float(trade.entry_price)) / risk if risk else 0.0
        rows.append({
            "position_id": int(trade.position_id),
            "engine_name": trade.engine_name,
            "outcome": trade.outcome,
            "net_r": float(trade.net_r),
            "conservative_mfe_r": float(max(mfe, 0.0)),
            "conservative_mae_r": float(max(mae, 0.0)),
            "reached_0_25r": bool(mfe >= 0.25),
            "reached_0_50r": bool(mfe >= 0.50),
            "reached_1_00r": bool(mfe >= 1.00),
        })
    return pd.DataFrame(rows)


def matched_pair_table(cases: pd.DataFrame, replay: pd.DataFrame) -> pd.DataFrame:
    records = []
    for case in cases.itertuples(index=False):
        snapshot = replay[replay.decision_time_server == str(case.entry_time_server)]
        if len(snapshot) != 1:
            raise RuntimeError(f"{case.case_id}: expected one replay row, got {len(snapshot)}")
        s = snapshot.iloc[0]
        direction = int(case.direction)
        half_width = (float(s.mbb_upper) - float(s.mbb_lower)) / 2.0
        risk_price = abs(float(case.entry) - float(case.sl))
        aird_align = (direction > 0 and int(s.aird_regime) == 0) or (direction < 0 and int(s.aird_regime) == 1)
        vrc_align = np.sign(float(s.vrc_direction)) == direction
        tb_align = np.sign(float(s.tb_bias)) == direction
        qqe_strength = min(direction * float(s.qqe_primary), direction * float(s.qqe_secondary))
        signal = "+".join(
            label for key, label in [
                ("s1_long", "S1L"), ("s1_short", "S1S"),
                ("s2_long", "S2L"), ("s2_short", "S2S"),
                ("s3_long", "S3L"), ("s3_short", "S3S"),
            ] if int(s[key]) == 1
        )
        records.append({
            "case_id": case.case_id,
            "stratum": case.stratum,
            "position_id": int(case.position_id),
            "engine_name": case.engine_name,
            "direction": direction,
            "result": "WIN" if float(case.net_r) > 0 else "LOSS",
            "net_r": float(case.net_r),
            "aird_regime": int(s.aird_regime),
            "aird_confidence": float(s.aird_confidence),
            "aird_direction_aligned": bool(aird_align),
            "vrc_regime": int(s.vrc_regime),
            "vrc_direction": float(s.vrc_direction),
            "vrc_direction_aligned": bool(vrc_align),
            "vrc_vol_percentile": float(s.vrc_vol_percentile),
            "mbb_signal": signal,
            "mbb_squeeze": float(s.mbb_squeeze),
            "mbb_extension_halfwidth": direction * (float(case.entry) - float(s.mbb_basis)) / half_width if half_width else np.nan,
            "tb_bias": int(s.tb_bias),
            "tb_bias_aligned": bool(tb_align),
            "tb_atr": float(s.tb_atr),
            "stop_atr": risk_price / float(s.tb_atr) if float(s.tb_atr) else np.nan,
            "tb_cell_side": int(s.tb_cell_side),
            "tb_void_side": int(s.tb_void_side),
            "qqe_primary": float(s.qqe_primary),
            "qqe_secondary": float(s.qqe_secondary),
            "qqe_directional_strength": qqe_strength,
            "qqe_state": int(s.qqe_state),
        })
    return pd.DataFrame(records)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--truth", required=True, type=Path)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--replay", required=True, type=Path)
    parser.add_argument("--bars", required=True, type=Path)
    parser.add_argument("--runmeta", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    trades = pd.read_csv(args.truth)
    cases = pd.read_csv(args.cases)
    replay = pd.read_csv(args.replay)
    bars = pd.read_parquet(args.bars, columns=["time_utc", "high", "low"])
    bars["time_utc"] = pd.to_datetime(bars.time_utc, utc=True).dt.tz_localize(None)
    trades["entry_time_utc"] = pd.to_datetime(trades.entry_time_utc)
    trades["exit_time_utc"] = pd.to_datetime(trades.exit_time_utc)
    replay["decision_time_server"] = replay.decision_time_server.astype(str)
    numeric = [c for c in replay.columns if c not in {
        "decision_time_server", "decision_time_utc", "source_bar_time_server",
        "source_bar_time_utc", "engine_name", "source_hash", "hypothesis_id", "variant_tag",
    }]
    for column in numeric:
        replay[column] = pd.to_numeric(replay[column], errors="coerce")

    overall = summarize(trades, "ALL")
    tables = {
        "population_by_engine.csv": grouped(trades, "engine_name"),
        "population_by_year.csv": grouped(trades, "year"),
        "population_by_session.csv": grouped(trades, "session"),
        "population_by_direction.csv": grouped(trades, "direction"),
        "population_by_exit_reason.csv": grouped(trades, "exit_reason"),
    }
    risk_year = trades.groupby("year").agg(
        trades=("position_id", "count"),
        mean_initial_risk_account=("initial_risk_account", "mean"),
        median_initial_risk_account=("initial_risk_account", "median"),
        min_initial_risk_account=("initial_risk_account", "min"),
        max_initial_risk_account=("initial_risk_account", "max"),
        mean_net_r=("net_r", "mean"),
        net_profit=("net_profit", "sum"),
    ).reset_index()
    tables["risk_capacity_by_year.csv"] = risk_year

    path_stats = conservative_path_stats(trades, bars)
    tables["population_path_stats.csv"] = path_stats
    pair_table = matched_pair_table(cases, replay)
    tables["matched_pair_entry_states.csv"] = pair_table
    for name, table in tables.items():
        table.to_csv(args.output / name, index=False)

    losers = path_stats[path_stats.outcome == "LOSS"]
    runmeta = json.loads(args.runmeta.read_text(encoding="utf-8-sig"))
    qqe_counts = {str(int(k)): int(v) for k, v in replay.qqe_state.value_counts().sort_index().items()}
    paired = pair_table[pair_table.stratum.isin(["engine_median_loser", "matched_winner"])]
    metrics = {
        "schema_version": SCHEMA,
        "inputs": {
            "truth_sha256": sha256_file(args.truth),
            "cases_sha256": sha256_file(args.cases),
            "replay_sha256": sha256_file(args.replay),
            "bars_sha256": sha256_file(args.bars),
            "runmeta_sha256": sha256_file(args.runmeta),
        },
        "overall": overall,
        "runmeta_funnel": runmeta.get("funnel", {}),
        "path": {
            "losers": int(len(losers)),
            "losers_never_reached_0_25r": int((~losers.reached_0_25r).sum()),
            "losers_never_reached_0_25r_pct": float(100 * (~losers.reached_0_25r).mean()),
            "losers_reached_0_50r_then_lost": int(losers.reached_0_50r.sum()),
            "losers_reached_0_50r_then_lost_pct": float(100 * losers.reached_0_50r.mean()),
            "losers_reached_1_00r_then_lost": int(losers.reached_1_00r.sum()),
            "median_loser_mfe_r": float(losers.conservative_mfe_r.median()),
            "median_loser_mae_r": float(losers.conservative_mae_r.median()),
        },
        "frozen_window_diagnostics": {
            "snapshots": int(len(replay)),
            "aird_confidence_ge_0_45": int((replay.aird_confidence >= 0.45).sum()),
            "aird_confidence_ge_0_45_pct": float(100 * (replay.aird_confidence >= 0.45).mean()),
            "qqe_state_counts": qqe_counts,
            "qqe_state_is_neutral_pct": float(100 * (replay.qqe_state == 0).mean()),
        },
        "matched_pair_direction_alignment": {
            "pairs": 6,
            "loss_tb_aligned": int(paired[(paired.result == "LOSS") & paired.tb_bias_aligned].shape[0]),
            "win_tb_aligned": int(paired[(paired.result == "WIN") & paired.tb_bias_aligned].shape[0]),
            "loss_aird_aligned": int(paired[(paired.result == "LOSS") & paired.aird_direction_aligned].shape[0]),
            "win_aird_aligned": int(paired[(paired.result == "WIN") & paired.aird_direction_aligned].shape[0]),
            "loss_vrc_aligned": int(paired[(paired.result == "LOSS") & paired.vrc_direction_aligned].shape[0]),
            "win_vrc_aligned": int(paired[(paired.result == "WIN") & paired.vrc_direction_aligned].shape[0]),
        },
        "caveats": [
            "Path MFE/MAE uses only fully completed M5 bars before exit plus entry/exit prices; it is conservative and does not infer within-exit-bar extremes.",
            "Indicator distributions cover the 13 frozen capture windows, not all 670 entries. Population claims use the full lifecycle truth table only.",
            "Matched-pair comparisons are descriptive at n=6 pairs and cannot authorize a threshold or filter.",
        ],
    }
    metrics_path = args.output / "forensic_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"RSF_FORENSIC_METRICS_OK trades={len(trades)} cases={len(cases)} output={args.output}")


if __name__ == "__main__":
    main()
