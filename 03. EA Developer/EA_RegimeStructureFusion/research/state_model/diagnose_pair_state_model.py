from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import analyze_state_model012 as model_lib


def pf(values: np.ndarray) -> float:
    wins = float(values[values > 0].sum())
    losses = float(-values[values < 0].sum())
    return wins / losses if losses > 0 else (999.0 if wins > 0 else 0.0)


def summarize(frame: pd.DataFrame, keys: list[str]) -> list[dict]:
    rows: list[dict] = []
    grouped = frame.groupby(keys, dropna=False, sort=True)
    for key, part in grouped:
        key = key if isinstance(key, tuple) else (key,)
        row = {name: value.item() if hasattr(value, "item") else value for name, value in zip(keys, key)}
        gross = part["directional_gross_r"].to_numpy()
        net = part["net_r"].to_numpy()
        row.update(
            trades=int(len(part)),
            gross_pf=pf(gross),
            net_pf=pf(net),
            gross_r=float(gross.sum()),
            cost_r=float(part["cost_r"].sum()),
            net_r=float(net.sum()),
            win_rate=float((net > 0).mean()),
        )
        rows.append(row)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--census", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--hypothesis-id", required=True)
    ap.add_argument("--point", required=True, type=float)
    ap.add_argument("--horizon", type=int, default=12)
    ap.add_argument("--target-cadence", type=float, default=3.5)
    ap.add_argument("--bar-minutes", type=int, default=5)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    model_lib.POINT = args.point

    df = pd.read_csv(args.census)
    if (df["hypothesis_id"] != args.hypothesis_id).any():
        raise SystemExit("Hypothesis identity mismatch")
    times = pd.to_datetime(df["source_bar_time_utc"], format="%Y.%m.%d %H:%M:%S", utc=True)
    x, _ = model_lib.build_features(df)
    atr = df["tb_atr"].to_numpy()
    entry = df["open"].shift(-1).to_numpy()
    exit_price = df["close"].shift(-args.horizon).to_numpy()
    gross_target = (exit_price - entry) / atr
    base_spread_r = df["spread_points"].to_numpy() * args.point / atr
    cost_r = base_spread_r * (1.5 + 0.15 * (1.0 + df["vrc_vol_percentile"].to_numpy() / 100.0))
    exit_times = times.shift(-args.horizon)
    elapsed_minutes = (exit_times - times.shift(-1)).dt.total_seconds().to_numpy() / 60.0
    valid = (
        x.notna().all(axis=1).to_numpy()
        & (atr > args.point)
        & np.isfinite(gross_target)
        & np.isfinite(cost_r)
        & (elapsed_minutes >= 0)
        & (elapsed_minutes <= args.horizon * args.bar_minutes + 2 * args.bar_minutes)
    )

    trades: list[pd.DataFrame] = []
    for test_year in model_lib.TEST_YEARS:
        start = pd.Timestamp(f"{test_year}-01-01", tz="UTC")
        end = pd.Timestamp(f"{test_year + 1}-01-01", tz="UTC")
        train_mask = (times < start) & (exit_times < start)
        test_mask = (times >= start) & (times < end)
        train_idx = np.flatnonzero(train_mask.to_numpy() & valid)
        test_idx = np.flatnonzero(test_mask.to_numpy() & valid)
        model = model_lib.make_model("RIDGE")
        model.fit(x.iloc[train_idx], gross_target[train_idx])
        train_score = model.predict(x.iloc[train_idx])
        test_score = model.predict(x.iloc[test_idx])
        threshold = model_lib.choose_threshold(
            train_score,
            np.ones(len(train_idx), dtype=bool),
            args.horizon,
            model_lib.elapsed_weeks(times.iloc[train_idx].reset_index(drop=True)),
            args.target_cadence,
        )
        chosen_local = model_lib.select_nonoverlapping(
            test_score, np.ones(len(test_idx), dtype=bool), threshold, args.horizon
        )
        chosen = test_idx[chosen_local]
        direction = np.sign(test_score[chosen_local])
        part = pd.DataFrame(
            {
                "source_bar_time_utc": times.iloc[chosen].astype(str).to_numpy(),
                "test_year": test_year,
                "hour_utc": times.iloc[chosen].dt.hour.to_numpy(),
                "weekday_utc": times.iloc[chosen].dt.dayofweek.to_numpy(),
                "direction": direction.astype(int),
                "score": test_score[chosen_local],
                "directional_gross_r": direction * gross_target[chosen],
                "observed_spread_r": base_spread_r[chosen],
                "cost_r": cost_r[chosen],
                "net_r": direction * gross_target[chosen] - cost_r[chosen],
                "aird_regime": df["aird_regime"].to_numpy()[chosen],
                "vrc_regime": df["vrc_regime"].to_numpy()[chosen],
                "mbb_squeeze": df["mbb_squeeze"].to_numpy()[chosen],
                "tb_bias": df["tb_bias"].to_numpy()[chosen],
                "qqe_state": df["qqe_state"].to_numpy()[chosen],
            }
        )
        trades.append(part)

    out = pd.concat(trades, ignore_index=True)
    out.to_csv(args.out_dir / "best_cell_trade_diagnostics.csv", index=False)
    result = {
        "schema_version": "rsf_pair_state_failure_diagnostic.v1",
        "hypothesis_id": args.hypothesis_id,
        "model_family": "RIDGE",
        "horizon_bars": args.horizon,
        "target_cadence": args.target_cadence,
        "overall": summarize(out.assign(all="ALL"), ["all"])[0],
        "by_year": summarize(out, ["test_year"]),
        "by_direction": summarize(out, ["direction"]),
        "by_hour_utc": summarize(out, ["hour_utc"]),
        "by_weekday_utc": summarize(out, ["weekday_utc"]),
        "by_aird_regime": summarize(out, ["aird_regime"]),
        "by_vrc_regime": summarize(out, ["vrc_regime"]),
    }
    (args.out_dir / "best_cell_failure_diagnostic.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["overall"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
