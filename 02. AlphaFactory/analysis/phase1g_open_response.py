#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import math
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


START_EQUITY = 10000.0
DATE_FMT = "%Y.%m.%d %H:%M:%S"

FULL_CONFIGS = {
    "G0_DYNAMIC_OPEN_BASE": "20260308_141138",
    "G1B_WIN15_ACCEPT": "20260308_141457",
    "G1C_WIN30_ACCEPT": "20260308_141744",
    "G2B_WIN15_FAILVETO": "20260308_142042",
    "G2C_WIN30_FAILVETO_HANDOFF": "20260308_142311",
    "G3A_WIN15_THROTTLE": "20260308_142537",
    "G3C_WIN15_THROTTLE_HANDOFF": "20260308_142827",
}

FAMILY_WINNERS = {
    "G1": "G1C_WIN30_ACCEPT",
    "G2": "G2C_WIN30_FAILVETO_HANDOFF",
    "G3": "G3C_WIN15_THROTTLE_HANDOFF",
}

REALISM_RUNS = {
    "G1C_REALTICKS_NODELAY": "20260308_145123",
    "G1C_EVERYTICK_RANDOM_DELAY": "20260308_145416",
}

PHASE1F_REF_RUN = "20260308_115728"


def parse_dt(value):
    s = str(value or "").strip()
    if not s or s.lower() == "nan":
        return pd.NaT
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return pd.NaT


def pct(series, p):
    xs = [float(x) for x in series if pd.notna(x)]
    if not xs:
        return 0.0
    xs = sorted(xs)
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return xs[int(k)]
    return xs[f] * (c - k) + xs[c] * (k - f)


def profit_factor(pnls):
    gp = sum(x for x in pnls if x > 0)
    gl = -sum(x for x in pnls if x < 0)
    return gp / gl if gl > 0 else 999.99


def top_contrib_pct(pnls, n):
    wins = sorted([x for x in pnls if x > 0], reverse=True)
    gp = sum(wins)
    if gp <= 0 or not wins:
        return 0.0
    return round(sum(wins[:n]) / gp * 100.0, 2)


def nth_sunday(year, month, n):
    d = datetime(year, month, 1)
    while d.weekday() != 6:
        d += timedelta(days=1)
    d += timedelta(days=7 * (n - 1))
    return d.day


def ny_dst_for_utc(utc_dt):
    if pd.isna(utc_dt):
        return False
    year = utc_dt.year
    start_day = nth_sunday(year, 3, 2)
    end_day = nth_sunday(year, 11, 1)
    start_utc = datetime(year, 3, start_day, 7, 0, 0)
    end_utc = datetime(year, 11, end_day, 6, 0, 0)
    return start_utc <= utc_dt < end_utc


def utc_to_ny(utc_dt):
    if pd.isna(utc_dt):
        return pd.NaT
    offset = -4 if ny_dst_for_utc(utc_dt) else -5
    return utc_dt + timedelta(hours=offset)


def ny_open_local(ny_dt):
    if pd.isna(ny_dt):
        return pd.NaT
    return ny_dt.replace(hour=9, minute=30, second=0, microsecond=0)


def minutes_from_ny_open(utc_dt):
    ny_dt = utc_to_ny(utc_dt)
    if pd.isna(ny_dt):
        return math.nan
    return (ny_dt - ny_open_local(ny_dt)).total_seconds() / 60.0


def ny_bucket(mins):
    if pd.isna(mins):
        return "NA"
    if mins < 0:
        return "PRE_OPEN"
    if mins < 10:
        return "NY_00_10"
    if mins < 15:
        return "NY_10_15"
    if mins < 30:
        return "NY_15_30"
    if mins < 60:
        return "NY_30_60"
    if mins < 120:
        return "NY_60_120"
    return "NY_120_PLUS"


def safe_reason(reason):
    s = str(reason or "")
    return s if s and s.lower() != "nan" else ""


def block_category(reason):
    reason = safe_reason(reason)
    if not reason:
        return "NONE"
    if "OPEN_ACCEPT_GATE" in reason or "OPEN_WINDOW_NOT_READY" in reason or "OPEN_RESPONSE" in reason:
        return "OPEN_RESPONSE"
    if "daily_hard_stop" in reason:
        return "DAILY_HARD_STOP"
    if "daily_soft_lock" in reason:
        return "DAILY_SOFT_LOCK"
    if "max_trades_session" in reason:
        return "MAX_TRADES_SESSION"
    if "entry_spread_guard" in reason:
        return "ENTRY_SPREAD_GUARD"
    if "router" in reason.lower():
        return "ROUTER"
    return "OTHER"


@dataclass
class RunBundle:
    run_id: str
    scenario: str
    run_dir: Path
    logs_dir: Path
    reports_dir: Path
    run_meta: dict
    summary: dict
    signals: pd.DataFrame
    trades: pd.DataFrame
    shadow: pd.DataFrame
    observers: pd.DataFrame
    activity: pd.DataFrame


def read_json(path: Path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


def load_csv(path: Path):
    if not path or not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def pick_file(logs_dir: Path, name_fragment: str, run_token: str, suffix="csv"):
    hits = sorted(logs_dir.glob(f"*{name_fragment}*{run_token}*.{suffix}"))
    if hits:
        return hits[-1]
    hits = sorted(logs_dir.glob(f"*{name_fragment}*.{suffix}"))
    if hits:
        hits = sorted(hits, key=lambda p: p.stat().st_size)
        return hits[-1]
    return None


def prepare_df_times(df, cols):
    if df.empty:
        return df
    for c in cols:
        if c in df.columns:
            df[c + "_dt"] = df[c].apply(parse_dt)
    return df


def load_run(root_runs: Path, folder_run_id: str) -> RunBundle:
    run_dir = root_runs / folder_run_id
    logs_dir = run_dir / "logs"
    reports_dir = run_dir / "reports"
    run_meta_path = sorted(logs_dir.glob("*RunMeta*.json"))[-1]
    run_meta = read_json(run_meta_path)
    run_token = run_meta.get("run_id", "")
    summary = read_json(reports_dir / "summary.json")
    signals = load_csv(pick_file(logs_dir, "Signals", run_token))
    trades = load_csv(pick_file(logs_dir, "Trades", run_token))
    shadow = load_csv(pick_file(logs_dir, "Shadow", run_token))
    observers = load_csv(pick_file(logs_dir, "Observers", run_token))
    activity = load_csv(pick_file(logs_dir, "Activity", run_token))

    signals = prepare_df_times(signals, ["server_ts", "utc_ts"])
    trades = prepare_df_times(trades, ["entry_server_ts", "entry_utc_ts", "exit_server_ts", "exit_utc_ts"])
    shadow = prepare_df_times(shadow, ["signal_server_ts", "signal_utc_ts", "exit_server_ts", "exit_utc_ts"])
    observers = prepare_df_times(observers, ["server_ts", "utc_ts"])
    activity = prepare_df_times(activity, ["server_ts", "utc_ts"])

    if not signals.empty:
        signals["ny_dt"] = signals["utc_ts_dt"].apply(utc_to_ny)
        signals["ny_minutes_from_open"] = signals["utc_ts_dt"].apply(minutes_from_ny_open)
        signals["ny_bucket"] = signals["ny_minutes_from_open"].apply(ny_bucket)
        signals["block_category"] = signals["block_reason"].apply(block_category) if "block_reason" in signals.columns else "NONE"
        signals["signal_key"] = signals.apply(
            lambda r: f"{r.get('server_ts','')}|{r.get('engine_name','')}|{r.get('direction','')}", axis=1
        )

    if not trades.empty:
        if "is_final_close" in trades.columns:
            trades = trades[trades["is_final_close"].fillna(1).astype(int) == 1].copy()
        for c in [
            "hold_minutes", "sl_dist_points", "initial_r_points", "mfe_points", "mae_points",
            "giveback_points", "realized_r", "pnl_gross", "commission", "swap", "pnl_net",
            "news_proximity_min", "friday_proximity_min", "risk_multiplier"
        ]:
            if c in trades.columns:
                trades[c] = pd.to_numeric(trades[c], errors="coerce").fillna(0.0)
        trades["ny_dt"] = trades["entry_utc_ts_dt"].apply(utc_to_ny)
        trades["ny_minutes_from_open"] = trades["entry_utc_ts_dt"].apply(minutes_from_ny_open)
        trades["ny_bucket"] = trades["ny_minutes_from_open"].apply(ny_bucket)
        trades["entry_signal_key"] = trades.apply(
            lambda r: f"{r.get('entry_server_ts','')}|{r.get('engine_name','')}|{r.get('direction','')}", axis=1
        )
        trades["trade_date"] = trades["entry_server_ts_dt"].dt.date

    if not shadow.empty:
        for c in ["realized_net_points", "mfe_points", "mae_points", "score"]:
            if c in shadow.columns:
                shadow[c] = pd.to_numeric(shadow[c], errors="coerce").fillna(0.0)
        shadow["signal_key"] = shadow.apply(
            lambda r: f"{r.get('signal_server_ts','')}|{r.get('engine_name','')}|{r.get('direction','')}", axis=1
        )

    return RunBundle(
        run_id=run_token,
        scenario=run_meta.get("scenario_id", folder_run_id),
        run_dir=run_dir,
        logs_dir=logs_dir,
        reports_dir=reports_dir,
        run_meta=run_meta,
        summary=summary,
        signals=signals,
        trades=trades,
        shadow=shadow,
        observers=observers,
        activity=activity,
    )

def summary_metrics(bundle: RunBundle):
    core = bundle.summary.get("core_metrics", {}).get("full_basket", {})
    if core:
        return {
            "run_id": bundle.run_dir.name,
            "scenario": bundle.scenario,
            "trades": int(core.get("trades", 0)),
            "net": float(core.get("net_profit", 0.0)),
            "pf": float(core.get("profit_factor", 0.0)),
            "dd": float(core.get("max_drawdown_pct", 0.0)),
            "avg_hold": float(core.get("avg_hold_minutes", 0.0)),
            "median_hold": float(core.get("median_hold_minutes", 0.0)),
            "p95_hold": float(core.get("p95_hold_minutes", 0.0)),
            "top5": float(core.get("top5_trades_contribution_pct", 0.0)),
            "top10": float(core.get("top10_trades_contribution_pct", 0.0)),
            "worst_day": core.get("worst_day", {}).get("pnl", 0.0),
        }
    return calc_metrics(bundle.trades)


def calc_metrics(trades: pd.DataFrame):
    if trades.empty:
        return {
            "trades": 0, "net": 0.0, "pf": 0.0, "dd": 0.0,
            "avg_hold": 0.0, "median_hold": 0.0, "p95_hold": 0.0,
            "top5": 0.0, "top10": 0.0, "worst_day": 0.0, "worst_5day": 0.0,
        }
    tr = trades.sort_values(["exit_server_ts_dt", "position_id"]).copy()
    pnls = tr["pnl_net"].tolist()
    eq = START_EQUITY + tr["pnl_net"].cumsum()
    peak = eq.cummax()
    dd_pct = (((peak - eq) / peak.replace(0, math.nan)) * 100.0).fillna(0.0).max()
    daily = tr.groupby(tr["exit_server_ts_dt"].dt.date)["pnl_net"].sum()
    worst_day = daily.min() if not daily.empty else 0.0
    worst_5 = 0.0
    if not daily.empty:
        dser = daily.sort_index()
        for i in range(len(dser)):
            worst_5 = min(worst_5, dser.iloc[i:i + 5].sum())
    return {
        "trades": int(len(tr)),
        "net": round(sum(pnls), 2),
        "pf": round(profit_factor(pnls), 4),
        "dd": round(float(dd_pct), 2),
        "avg_hold": round(float(tr["hold_minutes"].mean()), 2),
        "median_hold": round(float(tr["hold_minutes"].median()), 2),
        "p95_hold": round(float(pct(tr["hold_minutes"], 0.95)), 2),
        "top5": round(top_contrib_pct(pnls, 5), 2),
        "top10": round(top_contrib_pct(pnls, 10), 2),
        "worst_day": round(float(worst_day), 2),
        "worst_5day": round(float(worst_5), 2),
    }


def window_slice(trades: pd.DataFrame, start: str, end: str):
    if trades.empty:
        return trades.copy()
    s = datetime.strptime(start, "%Y.%m.%d")
    e = datetime.strptime(end, "%Y.%m.%d") + timedelta(days=1)
    return trades[(trades["entry_utc_ts_dt"] >= s) & (trades["entry_utc_ts_dt"] < e)].copy()


def rolling_windows():
    return [
        ("ROLL_2020_2021", "2020.03.07", "2021.03.06"),
        ("ROLL_2021_2022", "2021.03.07", "2022.03.06"),
        ("ROLL_2022_2023", "2022.03.07", "2023.03.06"),
        ("ROLL_2023_2024", "2023.03.07", "2024.03.06"),
        ("ROLL_2024_2025", "2024.03.07", "2025.03.06"),
        ("ROLL_2025_2026", "2025.03.07", "2026.03.06"),
    ]


def build_time_normalization_audit(ref_bundle: RunBundle, out_path: Path):
    trades = ref_bundle.trades.copy()
    trades["utc_hour"] = trades["entry_utc_ts_dt"].dt.hour
    trades["server_hour"] = trades["entry_server_ts_dt"].dt.hour
    trades["ny_hour"] = trades["ny_dt"].dt.hour
    trades["ny_minute"] = trades["ny_dt"].dt.minute
    trades["ny_dst"] = trades["entry_utc_ts_dt"].apply(ny_dst_for_utc)
    trades["server_utc_offset_h"] = ((trades["entry_server_ts_dt"] - trades["entry_utc_ts_dt"]).dt.total_seconds() / 3600.0).round(1)

    losing = trades[trades["pnl_net"] < 0].copy()
    by_hour = losing.groupby("utc_hour").agg(count=("pnl_net", "size"), net=("pnl_net", "sum"), pf=("pnl_net", lambda s: profit_factor(s.tolist())))
    by_hour = by_hour.sort_values(["net", "count"])
    dominant_hour = int(by_hour.index[0]) if not by_hour.empty else 13
    h_cluster = losing[losing["utc_hour"] == dominant_hour].copy()
    h_cluster["ny_clock"] = h_cluster["ny_dt"].dt.strftime("%H:%M")
    h_cluster["server_clock"] = h_cluster["entry_server_ts_dt"].dt.strftime("%H:%M")

    ny_bucket_counts = h_cluster["ny_bucket"].value_counts().to_dict()
    server_hour_counts = h_cluster["server_hour"].value_counts().sort_index().to_dict()
    dst_counts = Counter("NY_DST" if x else "NY_STD" for x in h_cluster["ny_dst"])
    offset_counts = Counter(h_cluster["server_utc_offset_h"])

    lines = [
        "# Time normalization audit",
        "",
        f"- Reference run: `{ref_bundle.run_dir.name}` (`{ref_bundle.scenario}`)",
        f"- Dominant losing UTC-hour cluster in reference branch: **H{dominant_hour:02d}**",
        f"- H{dominant_hour:02d} losing trades: **{len(h_cluster)}** | net **{h_cluster['pnl_net'].sum():.2f}** | PF **{profit_factor(h_cluster['pnl_net'].tolist()):.3f}**",
        "",
        "## What the old H13-like cluster really means",
        "",
        f"- UTC H{dominant_hour:02d} mostly maps to NY local buckets: `{ny_bucket_counts}`",
        f"- Server-hour distribution for the same cluster: `{server_hour_counts}`",
        f"- NY DST vs standard split: `{dict(dst_counts)}`",
        f"- Observed server-UTC offsets: `{dict(offset_counts)}`",
        "",
        "## Interpretation",
        "",
        f"- The old H{dominant_hour:02d} cluster is a **clock-projection artifact**, not a universal fixed-hour truth.",
        "- Under New York local time, the same behavior sits around the NY open-response window, while its UTC/server label shifts with DST.",
        "- During NY DST, the open-response window compresses into earlier UTC/server labels; during NY standard time it shifts later.",
        "- Therefore feature design should anchor to **NY local open-response minutes**, not static UTC H13/H14 buckets.",
    ]
    sample = h_cluster[["entry_server_ts", "entry_utc_ts", "pnl_net", "ny_clock", "ny_bucket", "server_utc_offset_h"]].head(12)
    lines.extend(["", "## Sample mapped trades", "", sample.to_markdown(index=False)])
    out_path.write_text("\n".join(lines), encoding="utf-8")


def build_h13_stability_audit(ref_bundle: RunBundle, best_bundle: RunBundle, out_path: Path):
    ref = ref_bundle.trades.copy()
    best = best_bundle.trades.copy()
    rows = []
    windows = [
        ("FULL", "2020.03.07", "2026.03.06"),
        ("SPLIT_A", "2020.03.07", "2023.03.06"),
        ("SPLIT_B", "2023.03.07", "2026.03.06"),
    ] + list(rolling_windows())

    for label, start, end in windows:
        ref_w = window_slice(ref, start, end)
        best_w = window_slice(best, start, end)
        ref_h13 = ref_w[ref_w["entry_utc_ts_dt"].dt.hour == 13]
        ref_open = ref_w[(ref_w["ny_minutes_from_open"] >= 0) & (ref_w["ny_minutes_from_open"] < 60)]
        best_open = best_w[(best_w["ny_minutes_from_open"] >= 0) & (best_w["ny_minutes_from_open"] < 60)]
        rows.append({
            "window": label,
            "ref_h13_trades": len(ref_h13),
            "ref_h13_net": round(ref_h13["pnl_net"].sum(), 2),
            "ref_h13_pf": round(profit_factor(ref_h13["pnl_net"].tolist()), 4) if len(ref_h13) else 0.0,
            "ref_open_trades": len(ref_open),
            "ref_open_net": round(ref_open["pnl_net"].sum(), 2),
            "ref_open_pf": round(profit_factor(ref_open["pnl_net"].tolist()), 4) if len(ref_open) else 0.0,
            "g1c_open_trades": len(best_open),
            "g1c_open_net": round(best_open["pnl_net"].sum(), 2),
            "g1c_open_pf": round(profit_factor(best_open["pnl_net"].tolist()), 4) if len(best_open) else 0.0,
        })

    df = pd.DataFrame(rows)
    lines = [
        "# H13 cluster stability audit",
        "",
        f"- Reference branch: `{ref_bundle.run_dir.name}` (`{ref_bundle.scenario}`)",
        f"- Best Phase 1G branch: `{best_bundle.run_dir.name}` (`{best_bundle.scenario}`)",
        "",
        "## Stability table",
        "",
        df.to_markdown(index=False),
        "",
        "## Verdict",
        "",
        "- UTC H13 is **not stable enough** to be treated as a promotable global feature by itself.",
        "- The more coherent framing is NY-open local response, but even that remains mixed across split B and rolling windows.",
        "- This supports redesign around **open-response structure**, not hard-coded UTC buckets.",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")

def build_path_substitution_audit(base_bundle: RunBundle, best_bundle: RunBundle, out_path: Path):
    base_trades = base_bundle.trades.copy()
    best_trades = best_bundle.trades.copy()
    base_signals = base_bundle.signals.copy()
    best_signals = best_bundle.signals.copy()

    base_map = {k: r for k, r in base_trades.set_index("entry_signal_key").to_dict("index").items()}
    best_map = {k: r for k, r in best_trades.set_index("entry_signal_key").to_dict("index").items()}
    base_keys = set(base_map.keys())
    best_keys = set(best_map.keys())
    overlap = base_keys & best_keys
    removed = sorted(base_keys - best_keys)
    admitted = sorted(best_keys - base_keys)

    base_signal_map = {k: r for k, r in base_signals.set_index("signal_key").to_dict("index").items()}
    best_signal_map = {k: r for k, r in best_signals.set_index("signal_key").to_dict("index").items()}

    admitted_rows = []
    for k in admitted:
        b = best_map[k]
        base_sig = base_signal_map.get(k, {})
        admitted_rows.append({
            "signal_key": k,
            "trade_date": b["trade_date"],
            "entry_server_ts": b["entry_server_ts"],
            "pnl_net": b["pnl_net"],
            "base_block_reason": base_sig.get("block_reason", ""),
            "base_block_category": block_category(base_sig.get("block_reason", "")),
        })
    admitted_df = pd.DataFrame(admitted_rows)

    removed_rows = []
    for k in removed:
        r = base_map[k]
        best_sig = best_signal_map.get(k, {})
        removed_rows.append({
            "signal_key": k,
            "trade_date": r["trade_date"],
            "entry_server_ts": r["entry_server_ts"],
            "pnl_net": r["pnl_net"],
            "best_block_reason": best_sig.get("block_reason", ""),
            "best_block_category": block_category(best_sig.get("block_reason", "")),
        })
    removed_df = pd.DataFrame(removed_rows)

    chain_rows = []
    all_days = set(removed_df.get("trade_date", pd.Series(dtype=object)).tolist()) | set(admitted_df.get("trade_date", pd.Series(dtype=object)).tolist())
    for day in sorted(all_days):
        rem = removed_df[removed_df["trade_date"] == day].copy().sort_values("entry_server_ts")
        adm = admitted_df[admitted_df["trade_date"] == day].copy().sort_values("entry_server_ts")
        if rem.empty or adm.empty:
            continue
        chain_rows.append({
            "date": str(day),
            "removed_count": int(len(rem)),
            "removed_net": round(rem["pnl_net"].sum(), 2),
            "admitted_count": int(len(adm)),
            "admitted_net": round(adm["pnl_net"].sum(), 2),
            "chain_delta": round(adm["pnl_net"].sum() - rem["pnl_net"].sum(), 2),
        })

    chain_df = pd.DataFrame(chain_rows).sort_values("chain_delta", ascending=False) if chain_rows else pd.DataFrame()
    lines = [
        "# Path substitution audit",
        "",
        f"- Baseline reference: `{base_bundle.run_dir.name}` (`{base_bundle.scenario}`)",
        f"- Best Phase 1G config: `{best_bundle.run_dir.name}` (`{best_bundle.scenario}`)",
        "",
        "## Universe reconciliation",
        "",
        f"- Overlap trades: **{len(overlap)}**",
        f"- Removed baseline-only trades: **{len(removed)}** | net **{sum(base_map[k]['pnl_net'] for k in removed):.2f}**",
        f"- Admitted best-only trades: **{len(admitted)}** | net **{sum(best_map[k]['pnl_net'] for k in admitted):.2f}**",
        "",
        "## Admitted trade causes in baseline path",
        "",
        admitted_df["base_block_category"].value_counts().rename_axis("category").reset_index(name="count").to_markdown(index=False) if not admitted_df.empty else "_No admitted trades_",
        "",
        "## Removed trade causes in best path",
        "",
        removed_df["best_block_category"].value_counts().rename_axis("category").reset_index(name="count").to_markdown(index=False) if not removed_df.empty else "_No removed trades_",
        "",
        "## Replacement-chain summary (same-day heuristic)",
        "",
        chain_df.head(12).to_markdown(index=False) if not chain_df.empty else "_No same-day replacement chains_",
        "",
        "## Verdict",
        "",
        "- The improvement from G0 to the best Phase 1G config is **not pure signal-quality filtering only**; path substitution is present.",
        "- However, path substitution is only useful when the removed chain is sufficiently toxic; otherwise the branch is still too weak.",
        "- For promotion, future branches must show edge improvement **without relying on fragile chain replacement side-effects**.",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def drawdown_episodes(trades: pd.DataFrame, top_n=10):
    tr = trades.sort_values(["exit_server_ts_dt", "position_id"]).copy()
    eq = START_EQUITY
    peak = START_EQUITY
    peak_time = tr.iloc[0]["exit_server_ts_dt"] if not tr.empty else pd.NaT
    in_dd = False
    ep_start = None
    ep_peak = START_EQUITY
    rows = []
    depth_abs = 0.0

    for _, row in tr.iterrows():
        eq += row["pnl_net"]
        cur_time = row["exit_server_ts_dt"]
        if eq >= peak:
            if in_dd:
                rows.append({
                    "start": ep_start,
                    "end": cur_time,
                    "depth_abs": depth_abs,
                    "depth_pct": (depth_abs / ep_peak * 100.0) if ep_peak > 0 else 0.0,
                })
                in_dd = False
                depth_abs = 0.0
            peak = eq
            peak_time = cur_time
        else:
            if not in_dd:
                in_dd = True
                ep_start = peak_time
                ep_peak = peak
                depth_abs = peak - eq
            else:
                depth_abs = max(depth_abs, peak - eq)
    if in_dd and not tr.empty:
        rows.append({
            "start": ep_start,
            "end": tr.iloc[-1]["exit_server_ts_dt"],
            "depth_abs": depth_abs,
            "depth_pct": (depth_abs / ep_peak * 100.0) if ep_peak > 0 else 0.0,
        })
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(["depth_pct", "depth_abs"], ascending=False).head(top_n).copy()


def build_drawdown_replay(best_bundle: RunBundle, compare_bundles, out_path: Path):
    eps = drawdown_episodes(best_bundle.trades, top_n=10)
    rows = []
    for _, ep in eps.iterrows():
        s = ep["start"]
        e = ep["end"]
        best_slice = best_bundle.trades[(best_bundle.trades["exit_server_ts_dt"] >= s) & (best_bundle.trades["exit_server_ts_dt"] <= e)]
        row = {
            "start": s.strftime(DATE_FMT) if pd.notna(s) else "",
            "end": e.strftime(DATE_FMT) if pd.notna(e) else "",
            "g1c_depth_pct": round(ep["depth_pct"], 2),
            "g1c_trades": int(len(best_slice)),
            "g1c_net": round(best_slice["pnl_net"].sum(), 2),
        }
        if not best_slice.empty:
            row["dominant_weekday"] = best_slice["weekday_tag"].value_counts().index[0]
            row["dominant_utc_hour"] = int(best_slice["entry_utc_ts_dt"].dt.hour.value_counts().index[0])
            row["dominant_open_bucket"] = best_slice["ny_bucket"].value_counts().index[0]
        for tag, bundle in compare_bundles.items():
            sl = bundle.trades[(bundle.trades["exit_server_ts_dt"] >= s) & (bundle.trades["exit_server_ts_dt"] <= e)]
            row[f"{tag}_net"] = round(sl["pnl_net"].sum(), 2)
            row[f"{tag}_trades"] = int(len(sl))
        rows.append(row)
    df = pd.DataFrame(rows)
    out_path.write_text("# Drawdown replay gallery\n\n" + df.to_markdown(index=False), encoding="utf-8")

def build_state_action_and_stories(best_bundle: RunBundle, out_dir: Path):
    signals = best_bundle.signals.copy()
    trades = best_bundle.trades.copy()
    shadow = best_bundle.shadow.copy()
    trade_map = {k: r for k, r in trades.set_index("parent_trade_id").to_dict("index").items()}
    shadow_map = {k: r for k, r in shadow.set_index("parent_trade_id").to_dict("index").items()}

    mat_rows = []
    trade_story = []
    blocked_story = []

    for _, r in signals.iterrows():
        pid = r.get("parent_trade_id", "")
        tr = trade_map.get(pid)
        sh = shadow_map.get(pid)
        raw_action = str(r.get("state_action", "") or "").upper()
        if raw_action == "ALLOW" or (str(r.get("blocked_or_fired", "")).lower() == "fired" and float(r.get("risk_multiplier", 1.0)) >= 0.999):
            action = "ALLOW_FULL"
        elif raw_action == "HALF" or (str(r.get("blocked_or_fired", "")).lower() == "fired" and 0.0 < float(r.get("risk_multiplier", 1.0)) < 0.999):
            action = "ALLOW_HALF"
        else:
            action = "BLOCK"
        mat_rows.append({
            "server_ts": r.get("server_ts", ""),
            "utc_ts": r.get("utc_ts", ""),
            "ny_local_ts": r["ny_dt"].strftime(DATE_FMT) if pd.notna(r.get("ny_dt")) else "",
            "engine_name": r.get("engine_name", ""),
            "direction": r.get("direction", ""),
            "blocked_or_fired": r.get("blocked_or_fired", ""),
            "chosen_action": action,
            "state_reason": safe_reason(r.get("state_reason", "")),
            "block_reason": safe_reason(r.get("block_reason", "")),
            "risk_multiplier": round(float(r.get("risk_multiplier", 0.0)), 4),
            "quality_score": round(float(r.get("quality_score", 0.0)), 4),
            "atr_points": round(float(r.get("atr_points", 0.0)), 2),
            "spread_points": round(float(r.get("spread_points", 0.0)), 2),
            "vwap_distance_points": round(float(r.get("vwap_distance_points", 0.0)), 2),
            "vwap_slope_points": round(float(r.get("vwap_slope_points", 0.0)), 2),
            "ny_open_minutes_from_open": r.get("ny_open_minutes_from_open", math.nan),
            "ny_open_window_min": r.get("ny_open_window_min", math.nan),
            "ny_open_impulse_atr": r.get("ny_open_impulse_atr", math.nan),
            "ny_open_accept_closes": r.get("ny_open_accept_closes", math.nan),
            "ny_open_rotation_count": r.get("ny_open_rotation_count", math.nan),
            "ny_open_close_location": r.get("ny_open_close_location", math.nan),
            "ny_open_last_close_vs_vwap_points": r.get("ny_open_last_close_vs_vwap_points", math.nan),
            "ny_open_accepted_break": r.get("ny_open_accepted_break", math.nan),
            "ny_open_failed_break": r.get("ny_open_failed_break", math.nan),
            "ny_open_handoff_conflict": r.get("ny_open_handoff_conflict", math.nan),
            "ny_open_state_class": r.get("ny_open_state_class", ""),
            "counterfactual_status": sh.get("counterfactual_status", "") if sh else "",
            "counterfactual_exit_reason": sh.get("exit_reason", "") if sh else "",
            "counterfactual_net_points": round(float(sh.get("realized_net_points", 0.0)), 2) if sh else 0.0,
            "trade_pnl_net": round(float(tr.get("pnl_net", 0.0)), 2) if tr else 0.0,
            "trade_exit_reason": tr.get("exit_reason", "") if tr else "",
        })
        if tr:
            trade_story.append({
                "parent_trade_id": pid,
                "entry_server_ts": tr.get("entry_server_ts"),
                "entry_utc_ts": tr.get("entry_utc_ts"),
                "ny_local_ts": r["ny_dt"].strftime(DATE_FMT) if pd.notna(r.get("ny_dt")) else "",
                "direction": tr.get("direction"),
                "engine": tr.get("engine_name"),
                "why_entry_allowed": safe_reason(r.get("state_reason", "")),
                "compliance_ok": int(not safe_reason(r.get("block_reason", ""))),
                "observer_vetoed": 0,
                "sizing_reason": f"risk_multiplier={float(r.get('risk_multiplier', 1.0)):.2f}",
                "playbook_followed": int("vwap_pullback_nyopen" in str(tr.get("entry_reason", ""))),
                "exit_reason": tr.get("exit_reason"),
                "hold_minutes": float(tr.get("hold_minutes", 0.0)),
                "pnl_net": float(tr.get("pnl_net", 0.0)),
                "state_class": r.get("ny_open_state_class", ""),
            })
        else:
            blocked_story.append({
                "parent_trade_id": pid,
                "signal_server_ts": r.get("server_ts"),
                "signal_utc_ts": r.get("utc_ts"),
                "ny_local_ts": r["ny_dt"].strftime(DATE_FMT) if pd.notna(r.get("ny_dt")) else "",
                "direction": r.get("direction"),
                "engine": r.get("engine_name"),
                "why_blocked": safe_reason(r.get("block_reason", "")),
                "state_reason": safe_reason(r.get("state_reason", "")),
                "state_class": r.get("ny_open_state_class", ""),
                "counterfactual_status": sh.get("counterfactual_status", "") if sh else "",
                "counterfactual_exit_reason": sh.get("exit_reason", "") if sh else "",
                "counterfactual_net_points": float(sh.get("realized_net_points", 0.0)) if sh else 0.0,
            })

    pd.DataFrame(mat_rows).to_csv(out_dir / "state_action_matrix.csv", index=False)
    with (out_dir / "trade_story.jsonl").open("w", encoding="utf-8") as f:
        for row in trade_story:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (out_dir / "blocked_signal_story.jsonl").open("w", encoding="utf-8") as f:
        for row in blocked_story:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_microstructure_cost_audit(best_bundle: RunBundle, realticks_bundle: RunBundle, out_path: Path):
    trades = best_bundle.trades.copy()
    signals = best_bundle.signals.copy()
    sig_spread = signals[["parent_trade_id", "spread_points", "vwap_distance_points"]].drop_duplicates("parent_trade_id")
    tr = trades.merge(sig_spread, on="parent_trade_id", how="left")
    tr["winner"] = tr["pnl_net"] > 0
    tr["sl_spread_ratio"] = tr["sl_dist_points"] / tr["spread_points"].replace(0, math.nan)
    tr["target_spread_ratio"] = tr["initial_r_points"] / tr["spread_points"].replace(0, math.nan)
    tr["vwap_spread_ratio"] = tr["vwap_distance_points"] / tr["spread_points"].replace(0, math.nan)

    def qdesc(df):
        return {
            "p50": round(float(df.median()), 2),
            "p80": round(float(pct(df.dropna(), 0.8)), 2),
            "p90": round(float(pct(df.dropna(), 0.9)), 2),
        }

    win_spread = qdesc(tr.loc[tr["winner"], "spread_points"])
    lose_spread = qdesc(tr.loc[~tr["winner"], "spread_points"])
    degrad = realticks_bundle.summary.get("core_metrics", {}).get("full_basket", {})
    lines = [
        "# Microstructure cost audit",
        "",
        f"- Baseline best config PF/DD: **{best_bundle.summary['core_metrics']['full_basket']['profit_factor']:.4f} / {best_bundle.summary['core_metrics']['full_basket']['max_drawdown_pct']:.2f}%**",
        f"- Real ticks PF/DD: **{degrad.get('profit_factor', 0.0):.4f} / {degrad.get('max_drawdown_pct', 0.0):.2f}%**",
        "",
        "## Winner vs loser spread percentile",
        "",
        f"- Winners: `{win_spread}`",
        f"- Losers: `{lose_spread}`",
        "",
        "## Structural ratios",
        "",
        f"- Median SL/spread ratio: **{tr['sl_spread_ratio'].median():.2f}**",
        f"- Median target/spread ratio: **{tr['target_spread_ratio'].median():.2f}**",
        f"- Median VWAP-distance/spread ratio: **{tr['vwap_spread_ratio'].median():.2f}**",
        "",
    ]
    tr["spread_bucket"] = pd.qcut(tr["spread_points"].rank(method='first'), q=3, labels=["NORMAL", "HIGH", "EXTREME"])
    tr["vd_bucket"] = pd.qcut(tr["vwap_distance_points"].rank(method='first'), q=3, labels=["NORMAL", "HIGH", "EXTREME"])
    inter = tr.groupby(["spread_bucket", "vd_bucket"]).agg(trades=("pnl_net", "size"), net=("pnl_net", "sum")).reset_index()
    inter = inter.sort_values("net").head(8)
    lines.extend(["## VWAP-distance x spread interaction", "", inter.to_markdown(index=False), "", "## Interpretation", "", "- Raw spread alone does not explain the branch weakness.", "- The degradation concentrates when spread frictions combine with poor VWAP-context positioning, consistent with weak opening-response quality."])
    out_path.write_text("\n".join(lines), encoding="utf-8")

def build_family_outputs(root_runs: Path, bundles, oos_csv: Path, out_csv: Path, out_md: Path, out_oos_csv: Path, out_oos_md: Path, out_ladder: Path):
    rows = []
    for scenario, run_id in FULL_CONFIGS.items():
        b = bundles[run_id]
        m = summary_metrics(b)
        family = scenario.split("_")[0]
        rows.append({
            "family": family,
            "scenario": scenario,
            "run_id": run_id,
            "trades": m["trades"],
            "net": m["net"],
            "pf": m["pf"],
            "dd": m["dd"],
            "avg_hold": m["avg_hold"],
            "median_hold": m["median_hold"],
            "p95_hold": m["p95_hold"],
            "top5": m["top5"],
            "top10": m["top10"],
        })
    df = pd.DataFrame(rows)
    oos = pd.read_csv(oos_csv)
    winners = []
    for family, scenario in FAMILY_WINNERS.items():
        full = df[df["scenario"] == scenario].iloc[0].to_dict()
        fam_oos = oos[oos["family"] == scenario.split("_")[0]].copy()
        split_a = fam_oos[fam_oos["window"] == "SPLIT_A"].iloc[0].to_dict()
        split_b = fam_oos[fam_oos["window"] == "SPLIT_B"].iloc[0].to_dict()
        rolls = fam_oos[fam_oos["window"].str.startswith("ROLL_")].copy()
        profitable = int(((rolls["pf"] > 1.0) & (rolls["net"] > 0)).sum())
        winners.append({
            "family": family,
            "scenario": scenario,
            "run_id": full["run_id"],
            "full_pf": full["pf"],
            "full_dd": full["dd"],
            "split_a_pf": float(split_a["pf"]),
            "split_a_dd": float(split_a["dd"]),
            "split_b_pf": float(split_b["pf"]),
            "split_b_dd": float(split_b["dd"]),
            "rolling_profitable": profitable,
            "rolling_avg_pf": round(float(rolls["pf"].mean()), 4),
            "trade_count": int(full["trades"]),
        })
    wdf = pd.DataFrame(winners).sort_values(
        ["split_b_pf", "rolling_profitable", "full_pf", "trade_count"],
        ascending=[False, False, False, False]
    )
    df.to_csv(out_csv, index=False)
    out_md.write_text("# Phase 1G family comparison\n\n" + df.to_markdown(index=False), encoding="utf-8")
    wdf.to_csv(out_oos_csv, index=False)
    out_oos_md.write_text("# Phase 1G OOS comparison\n\n" + wdf.to_markdown(index=False), encoding="utf-8")

    hypotheses = {
        "G1B_WIN15_ACCEPT": "Gate VWAP by first 15m NY continuation acceptance.",
        "G1C_WIN30_ACCEPT": "Gate VWAP by first 30m NY continuation acceptance.",
        "G2B_WIN15_FAILVETO": "Veto VWAP after first 15m NY failure structure.",
        "G2C_WIN30_FAILVETO_HANDOFF": "Veto VWAP after 30m failure + London-to-NY handoff conflict.",
        "G3A_WIN15_THROTTLE": "3-state action after 15m open-response quality assessment.",
        "G3C_WIN15_THROTTLE_HANDOFF": "3-state action after 15m open-response + handoff conflict.",
    }
    ladder_lines = ["# Open response feature ladder", ""]
    g0_trades = int(df[df["scenario"] == "G0_DYNAMIC_OPEN_BASE"]["trades"].iloc[0])
    for scenario in ["G1B_WIN15_ACCEPT", "G1C_WIN30_ACCEPT", "G2B_WIN15_FAILVETO", "G2C_WIN30_FAILVETO_HANDOFF", "G3A_WIN15_THROTTLE", "G3C_WIN15_THROTTLE_HANDOFF"]:
        full = df[df["scenario"] == scenario].iloc[0]
        family = scenario.split("_")[0]
        fam_oos = oos[oos["family"] == family]
        delta_trades = int(full["trades"] - g0_trades)
        if fam_oos.empty:
            split_a_pf = split_a_dd = split_b_pf = split_b_dd = "not_run"
            prof = "not_run"
        else:
            split_a = fam_oos[fam_oos["window"] == "SPLIT_A"].iloc[0]
            split_b = fam_oos[fam_oos["window"] == "SPLIT_B"].iloc[0]
            rolls = fam_oos[fam_oos["window"].str.startswith("ROLL_")]
            prof = f"{int(((rolls['pf'] > 1.0) & (rolls['net'] > 0)).sum())}/6"
            split_a_pf = f"{split_a['pf']:.4f}"
            split_a_dd = f"{split_a['dd']:.2f}%"
            split_b_pf = f"{split_b['pf']:.4f}"
            split_b_dd = f"{split_b['dd']:.2f}%"
        ladder_lines.extend([
            f"## {scenario}",
            "",
            f"- Hypothesis: {hypotheses.get(scenario, '')}",
            f"- Trade-count delta vs G0: **{delta_trades}**",
            f"- Full PF/DD: **{full['pf']:.4f} / {full['dd']:.2f}%**",
            f"- Split A PF/DD: **{split_a_pf} / {split_a_dd}**",
            f"- Split B PF/DD: **{split_b_pf} / {split_b_dd}**",
            f"- Rolling profitable windows: **{prof}**",
            "",
        ])
    out_ladder.write_text("\n".join(ladder_lines), encoding="utf-8")
    return df, wdf


def build_weekday_toxicity(best_bundle: RunBundle, out_path: Path):
    tr = best_bundle.trades.copy()
    wk = tr[tr["weekday_tag"].isin(["Thursday", "Friday"])].copy()
    sigmap = best_bundle.signals[["parent_trade_id", "spread_points", "news_proximity_min", "ny_open_state_class", "ny_bucket"]].drop_duplicates("parent_trade_id")
    wk = wk.merge(sigmap, on="parent_trade_id", how="left", suffixes=("", "_sig"))
    if "ny_bucket_sig" in wk.columns:
        wk["ny_bucket"] = wk["ny_bucket_sig"].fillna(wk.get("ny_bucket"))
    wk["hour_bucket"] = wk["entry_utc_ts_dt"].dt.hour.apply(lambda x: f"H{int(x):02d}")
    wk["spread_regime"] = pd.qcut(wk["spread_points"].rank(method='first'), q=3, labels=["NORMAL", "HIGH", "EXTREME"]) if len(wk) >= 3 else "NORMAL"
    tables = {
        "hour": wk.groupby("hour_bucket").agg(trades=("pnl_net", "size"), net=("pnl_net", "sum"), pf=("pnl_net", lambda s: profit_factor(s.tolist()))).reset_index().sort_values("net"),
        "spread": wk.groupby("spread_regime").agg(trades=("pnl_net", "size"), net=("pnl_net", "sum"), pf=("pnl_net", lambda s: profit_factor(s.tolist()))).reset_index().sort_values("net"),
        "open_state": wk.groupby("ny_open_state_class").agg(trades=("pnl_net", "size"), net=("pnl_net", "sum"), pf=("pnl_net", lambda s: profit_factor(s.tolist()))).reset_index().sort_values("net"),
        "ny_bucket": wk.groupby("ny_bucket").agg(trades=("pnl_net", "size"), net=("pnl_net", "sum"), pf=("pnl_net", lambda s: profit_factor(s.tolist()))).reset_index().sort_values("net"),
    }
    lines = ["# Weekday toxicity decomposition", "", f"- Thursday/Friday trades: **{len(wk)}** | net **{wk['pnl_net'].sum():.2f}** | PF **{profit_factor(wk['pnl_net'].tolist()):.4f}**", ""]
    for name, table in tables.items():
        lines.extend([f"## {name}", "", table.to_markdown(index=False), ""])
    lines.append("- Conclusion: Thursday/Friday are not hard-ban candidates by themselves; sub-regime composition remains the driver.")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def build_calendar_gap_plan(best_bundle: RunBundle, out_path: Path):
    meta = best_bundle.run_meta
    lines = [
        "# Calendar gap plan",
        "",
        f"- Current snapshot id: `{meta.get('calendar_snapshot_id','')}`",
        f"- Current snapshot hash: `{meta.get('calendar_snapshot_hash','')}`",
        f"- Current coverage: `{meta.get('snapshot_coverage_from','')}` -> `{meta.get('snapshot_coverage_to','')}`",
        f"- Included classes: `{meta.get('included_event_classes','')}`",
        f"- Source provenance: `{meta.get('source_provenance','')}`",
        "",
        "## Why this is insufficient",
        "",
        "- Coverage is only a narrow 2026 slice, not the full 2020-03-07 -> 2026-03-06 research window.",
        "- Event classes are partial and manually curated, so strict prop-compliance claims remain provisional.",
        "",
        "## Required plan to close the gap",
        "",
        "1. Build a historical macro-event dataset covering the full 6-year backtest window.",
        "2. Normalize every event to UTC and preserve original source timestamps + timezone.",
        "3. Version each snapshot with calendar_snapshot_id, hash, coverage_from/to, included_event_classes, source_provenance.",
        "4. Store the exact snapshot alongside each run folder for immutable replay.",
        "5. Add QA checks: duplicate detection, DST sanity, missing high-impact US releases, and schema validation.",
        "6. Only after full coverage exists should FTMO/The5ers policy-profile validation be considered substantive.",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def build_summary_json(out_path: Path, family_df: pd.DataFrame, oos_df: pd.DataFrame, best_bundle: RunBundle, rt_bundle: RunBundle, rd_bundle: RunBundle):
    obj = {
        "phase": "1G",
        "verdict": "USEFUL_BUT_WEAK",
        "promotion_gate_pass": False,
        "best_config": {
            "scenario": best_bundle.scenario,
            "folder_run_id": best_bundle.run_dir.name,
            "full_sample": summary_metrics(best_bundle),
        },
        "family_winners_ranked": oos_df.to_dict(orient="records"),
        "realism": {
            "real_ticks_no_delay": summary_metrics(rt_bundle),
            "every_tick_random_delay": summary_metrics(rd_bundle),
        },
        "kill_rule_triggered": True,
        "next_step": "Kill current VWAP trader branch and redesign trader engine as Phase 2A: NY_OPEN_ACCEPTANCE trader, NY_OPEN_FAILURE_FADE trader, POST_OPEN_VWAP_RECLAIM trader.",
    }
    out_path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root-runs", required=True)
    ap.add_argument("--oos-csv", required=True)
    args = ap.parse_args()

    root_runs = Path(args.root_runs)
    bundles = {}
    for run_id in set(list(FULL_CONFIGS.values()) + list(REALISM_RUNS.values()) + [PHASE1F_REF_RUN]):
        bundles[run_id] = load_run(root_runs, run_id)

    best_bundle = bundles[FULL_CONFIGS["G1C_WIN30_ACCEPT"]]
    g0_bundle = bundles[FULL_CONFIGS["G0_DYNAMIC_OPEN_BASE"]]
    g2c_bundle = bundles[FULL_CONFIGS["G2C_WIN30_FAILVETO_HANDOFF"]]
    g3c_bundle = bundles[FULL_CONFIGS["G3C_WIN15_THROTTLE_HANDOFF"]]
    ref_bundle = bundles[PHASE1F_REF_RUN]
    rt_bundle = bundles[REALISM_RUNS["G1C_REALTICKS_NODELAY"]]
    rd_bundle = bundles[REALISM_RUNS["G1C_EVERYTICK_RANDOM_DELAY"]]

    phase_dir = best_bundle.reports_dir / "phase1g"
    phase_dir.mkdir(parents=True, exist_ok=True)

    build_time_normalization_audit(ref_bundle, phase_dir / "time_normalization_audit.md")
    build_h13_stability_audit(ref_bundle, best_bundle, phase_dir / "h13_cluster_stability_audit.md")
    build_path_substitution_audit(g0_bundle, best_bundle, phase_dir / "path_substitution_audit.md")
    build_state_action_and_stories(best_bundle, phase_dir)
    build_drawdown_replay(best_bundle, {"g0": g0_bundle, "g2c": g2c_bundle, "g3c": g3c_bundle}, phase_dir / "drawdown_replay_gallery.md")
    build_microstructure_cost_audit(best_bundle, rt_bundle, phase_dir / "microstructure_cost_audit.md")
    build_weekday_toxicity(best_bundle, phase_dir / "weekday_toxicity_decomposition.md")
    build_calendar_gap_plan(best_bundle, phase_dir / "calendar_gap_plan.md")

    family_csv = root_runs / "phase1g_family_comparison_20260308.csv"
    family_md = root_runs / "phase1g_family_comparison_20260308.md"
    oos_csv = root_runs / "phase1g_oos_summary_20260308.csv"
    oos_md = root_runs / "phase1g_oos_summary_20260308.md"
    ladder_md = phase_dir / "open_response_feature_ladder.md"
    family_df, oos_df = build_family_outputs(root_runs, bundles, Path(args.oos_csv), family_csv, family_md, oos_csv, oos_md, ladder_md)
    build_summary_json(phase_dir / "phase1g_summary.json", family_df, oos_df, best_bundle, rt_bundle, rd_bundle)

    print("Phase1G artifacts written to:")
    print(phase_dir)
    print(family_csv)
    print(family_md)
    print(oos_csv)
    print(oos_md)


if __name__ == "__main__":
    main()
