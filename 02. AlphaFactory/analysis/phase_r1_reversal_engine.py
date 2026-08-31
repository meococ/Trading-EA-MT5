#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import importlib.util
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(r"02. AlphaFactory/runs/XAU_Scalp_Portfolio")
OUT_DIR = ROOT / "phaseR1_reversal_20260309"
PHASE3B_SCRIPT = Path(r"02. AlphaFactory/analysis/phase3b_router_simulation.py")

SYMBOL = "XAUUSD"


def load_phase3b():
    spec = importlib.util.spec_from_file_location("phase3b_router_simulation", PHASE3B_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def pf(vals) -> float:
    vals = [float(v) for v in vals]
    gp = sum(v for v in vals if v > 0)
    gl = -sum(v for v in vals if v < 0)
    return gp / gl if gl > 0 else 999.99


def top_contrib_pct(vals, n: int) -> float:
    wins = sorted([float(v) for v in vals if v > 0], reverse=True)
    gp = sum(wins)
    return round((sum(wins[:n]) * 100.0 / gp), 2) if gp > 0 else 0.0


def drawdown_pct(vals) -> float:
    equity = 100_000.0
    peak = equity
    max_dd = 0.0
    for v in vals:
        equity += equity * 0.0025 * float(v)
        peak = max(peak, equity)
        if peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak * 100.0)
    return max_dd


def load_base_frame(mod):
    features = mod.load_features()
    m1, m5, point = mod.load_mt5_rates()
    day_ctx = mod.build_daily_market_context(features, m1, m5, point)
    frame = features.merge(day_ctx, on="ny_date", how="inner").sort_values("ny_date").reset_index(drop=True)
    sim = mod.simulate_day_playbooks(frame, m5, point)
    sim["reversal_r"] = sim["FAILURE_FADE_realized_r"].astype(float)
    sim["reversal_hold"] = sim["FAILURE_FADE_hold_minutes"].astype(float)
    sim["reversal_exit_reason"] = sim["FAILURE_FADE_exit_reason"]
    sim["reversal_entry_ny"] = sim["FAILURE_FADE_entry_ny"]
    sim["reversal_exit_ny"] = sim["FAILURE_FADE_exit_ny"]
    return sim, m1, m5, point


def split_a_thresholds(frame: pd.DataFrame) -> dict:
    train = frame[frame["split"] == "A"].copy()
    return {
        "spread_low": float(train["spread_pct_10"].median()),
        "london_pos_mid": float(train["london_pos_at_open"].median()),
        "vdist_mid": float(train["vwap_dist_30_norm"].median()),
        "rot_mid": float(train["rotation_30"].median()),
        "mid_abs_mid": float(train["or_mid_status_30"].abs().median()),
        "accept_mid": float(train["accept_balance_30"].median()),
        "or10_mid": float(train["or10_width_norm"].median()),
        "sweep_hi": float(train["london_extreme_sweep_norm"].quantile(0.75)),
    }


def build_family_specs(frame: pd.DataFrame, thr: dict) -> dict:
    sp_low = frame["spread_pct_10"] <= thr["spread_low"]
    h1 = frame["handoff_conflict"] == 1
    l_high = frame["london_pos_at_open"] > thr["london_pos_mid"]
    vdist_hi = frame["vwap_dist_30_norm"] >= thr["vdist_mid"]
    rot_hi = frame["rotation_30"] >= thr["rot_mid"]
    mid_hi = frame["or_mid_status_30"].abs() >= thr["mid_abs_mid"]
    acc_hi = frame["accept_balance_30"] >= thr["accept_mid"]
    or10_hi = frame["or10_width_norm"] >= thr["or10_mid"]
    sweep_flag = frame["london_sweep_flag"] == 1
    sweep_hi = frame["london_extreme_sweep_norm"] >= thr["sweep_hi"]

    return {
        "R0_BASE_DIRECT": {
            "family": "BASELINE_COMPARISON",
            "hypothesis": "Baseline reversal prototype: trade opposite initial NY-open impulse every day at 10:05.",
            "mask": pd.Series(True, index=frame.index),
            "reason_cols": [],
        },
        "R1_CONFLICT_BASE": {
            "family": "FAILED_ACCEPTANCE_AFTER_OPEN",
            "hypothesis": "Nếu London→NY handoff mâu thuẫn và spread đầu mở không xấu, reversal có thể khai thác failed acceptance.",
            "mask": h1 & sp_low,
            "reason_cols": ["handoff_conflict", "spread_pct_10"],
        },
        "R2_FAILED_ACCEPTANCE": {
            "family": "FAILED_ACCEPTANCE_AFTER_OPEN",
            "hypothesis": "Handoff conflict + acceptance balance cao + open ở nửa trên London range cho reversal rõ nhất.",
            "mask": h1 & acc_hi & l_high & sp_low,
            "reason_cols": ["handoff_conflict", "accept_balance_30", "london_pos_at_open", "spread_pct_10"],
        },
        "R3_VALUE_CONFLICT_RETURN": {
            "family": "VALUE_CONFLICT_VWAP_RETURN",
            "hypothesis": "Khi dislocation khỏi VWAP đủ lớn đồng thời handoff conflict và open ở nửa trên London range, reversal về value có xác suất tốt hơn.",
            "mask": vdist_hi & h1 & l_high & sp_low,
            "reason_cols": ["vwap_dist_30_norm", "handoff_conflict", "london_pos_at_open", "spread_pct_10"],
        },
        "R4_OR_MID_REJECTION": {
            "family": "OR_MIDPOINT_REJECTION",
            "hypothesis": "OR-mid displacement lớn + rotation cao + acceptance balance cao thể hiện failed drive có thể đảo về value.",
            "mask": mid_hi & rot_hi & acc_hi & sp_low,
            "reason_cols": ["or_mid_status_30", "rotation_30", "accept_balance_30", "spread_pct_10"],
        },
        "R5_LONDON_SWEEP_REJECT": {
            "family": "LONDON_EXTREME_SWEEP_REJECTION",
            "hypothesis": "London extreme sweep lớn và có handoff conflict có thể tạo NY-open reversal nếu spread còn chấp nhận được.",
            "mask": sweep_flag & sweep_hi & h1 & sp_low,
            "reason_cols": ["london_sweep_flag", "london_extreme_sweep_norm", "handoff_conflict", "spread_pct_10"],
        },
        "R6_WIDE_OR_CONFLICT": {
            "family": "FAILED_ACCEPTANCE_AFTER_OPEN",
            "hypothesis": "OR10 rộng trong trạng thái handoff conflict có thể là failed drive đủ mạnh cho reversal, ưu tiên density hơn purity.",
            "mask": h1 & or10_hi & sp_low,
            "reason_cols": ["handoff_conflict", "or10_width_norm", "spread_pct_10"],
        },
    }


def subset_metrics(frame: pd.DataFrame, mask: pd.Series, r_col: str, hold_col: str, roll_windows) -> dict:
    subset = frame.loc[mask].copy()
    vals = subset[r_col].astype(float).tolist()
    holds = subset[hold_col].astype(float).tolist() if len(subset) else []
    by_day = subset.groupby("ny_date")[r_col].sum().sort_index() if len(subset) else pd.Series(dtype=float)
    by_month = subset.groupby(pd.to_datetime(subset["ny_date"]).dt.to_period("M"))[r_col].sum() if len(subset) else pd.Series(dtype=float)
    full = {
        "trades": int(len(subset)),
        "net_r": round(float(sum(vals)), 4),
        "pf": round(float(pf(vals)), 4),
        "dd": round(float(drawdown_pct(vals)), 2),
        "avg_hold": round(float(pd.Series(holds).mean()), 2) if holds else 0.0,
        "median_hold": round(float(pd.Series(holds).median()), 2) if holds else 0.0,
        "p95_hold": round(float(pd.Series(holds).quantile(0.95)), 2) if holds else 0.0,
        "top5": top_contrib_pct(vals, 5),
        "top10": top_contrib_pct(vals, 10),
        "worst_month": round(float(by_month.min()), 4) if len(by_month) else 0.0,
        "worst_5day": round(float(by_day.rolling(5).sum().min()), 4) if len(by_day) >= 5 else 0.0,
    }
    splits = {}
    for split_name, split_mask in {
        "A": mask & (frame["split"] == "A"),
        "B": mask & (frame["split"] == "B"),
    }.items():
        sub = frame.loc[split_mask].copy()
        v = sub[r_col].astype(float).tolist()
        splits[split_name] = {
            "trades": int(len(sub)),
            "net_r": round(float(sum(v)), 4),
            "pf": round(float(pf(v)), 4) if len(v) else 0.0,
            "dd": round(float(drawdown_pct(v)), 2),
        }
    rolling_rows = []
    profitable = 0
    for name, start_d, end_d in roll_windows:
        w = frame.loc[mask & (frame["ny_date"] >= start_d) & (frame["ny_date"] <= end_d)].copy()
        v = w[r_col].astype(float).tolist()
        row = {
            "window": name,
            "from": str(start_d),
            "to": str(end_d),
            "trades": int(len(w)),
            "net_r": round(float(sum(v)), 4),
            "pf": round(float(pf(v)), 4) if len(v) else 0.0,
            "dd": round(float(drawdown_pct(v)), 2),
        }
        if row["trades"] > 0 and row["pf"] > 1.0 and row["net_r"] > 0:
            profitable += 1
        rolling_rows.append(row)
    full["rolling_profitable"] = f"{profitable}/{len(roll_windows)}"
    full["rolling_avg_pf"] = round(float(pd.Series([r["pf"] for r in rolling_rows]).mean()), 4) if rolling_rows else 0.0
    return {"full": full, "splits": splits, "rolling": rolling_rows}


def rank_families(results: list) -> pd.DataFrame:
    rows = []
    for r in results:
        rows.append({
            "config": r["config"],
            "family": r["family"],
            "trades": r["metrics"]["full"]["trades"],
            "pf": r["metrics"]["full"]["pf"],
            "dd": r["metrics"]["full"]["dd"],
            "splitA_pf": r["metrics"]["splits"]["A"]["pf"],
            "splitB_pf": r["metrics"]["splits"]["B"]["pf"],
            "rolling": r["metrics"]["full"]["rolling_profitable"],
            "top5": r["metrics"]["full"]["top5"],
            "top10": r["metrics"]["full"]["top10"],
        })
    ranked = pd.DataFrame(rows).sort_values(
        ["splitB_pf", "trades", "top10", "pf"],
        ascending=[False, False, True, False],
    ).reset_index(drop=True)
    return ranked


def analyze_families(frame: pd.DataFrame, specs: dict, mod):
    results = []
    for cfg, spec in specs.items():
        mask = spec["mask"].astype(bool)
        metrics = subset_metrics(frame, mask, "reversal_r", "reversal_hold", mod.ROLL_WINDOWS)
        results.append({
            "config": cfg,
            "family": spec["family"],
            "hypothesis": spec["hypothesis"],
            "reason_cols": spec["reason_cols"],
            "mask": mask,
            "metrics": metrics,
        })
    return results


def build_family_comparison_md(ranked: pd.DataFrame, results: list) -> str:
    lines = [
        "# Reversal engine family comparison",
        "",
        "## Neutral execution framework",
        "- Decision time: **10:00 NY**",
        "- Entry semantics: **10:05 NY market entry**",
        "- Stop family: **max(0.8 * ATR14 pre-open, 0.4 * pre-open range, point)**",
        "- Target family: **1R fixed**",
        "- Timeout: **12 bar M5**",
        "- Spread charge: **entry-bar spread**",
        "- No trailing / no partial / no asymmetrical exit",
        "",
        ranked.to_markdown(index=False),
        "",
    ]
    for r in results:
        lines.extend([
            f"## {r['config']} — {r['family']}",
            f"- Hypothesis: {r['hypothesis']}",
            f"- Trades: **{r['metrics']['full']['trades']}**",
            f"- Full PF/DD: **{r['metrics']['full']['pf']} / {r['metrics']['full']['dd']}%**",
            f"- Split B PF/DD: **{r['metrics']['splits']['B']['pf']} / {r['metrics']['splits']['B']['dd']}%**",
            f"- Rolling: **{r['metrics']['full']['rolling_profitable']}**",
            "",
        ])
    return "\n".join(lines)


def build_sample_density_md(best: dict, frame: pd.DataFrame) -> str:
    mask = best["mask"]
    sub = frame.loc[mask].copy()
    year_counts = sub.groupby("year").size().rename("trades").reset_index()
    quarter_counts = sub.groupby(pd.to_datetime(sub["ny_date"]).dt.to_period("Q")).size().rename("trades").reset_index()
    split_counts = sub.groupby("split").size().rename("trades").reset_index()
    lines = [
        "# Sample density report",
        "",
        f"## Best family: {best['config']}",
        f"- Total trades: **{best['metrics']['full']['trades']}**",
        f"- Median trades/quarter: **{int(quarter_counts['trades'].median()) if len(quarter_counts) else 0}**",
        "",
        "### Trades by split",
        split_counts.to_markdown(index=False) if len(split_counts) else "_No trades_",
        "",
        "### Trades by year",
        year_counts.to_markdown(index=False) if len(year_counts) else "_No trades_",
        "",
        "### Rolling windows",
        pd.DataFrame(best["metrics"]["rolling"])[["window", "trades", "pf", "net_r"]].to_markdown(index=False),
    ]
    return "\n".join(lines)


def build_concentration_md(ranked: pd.DataFrame, results: list) -> str:
    rows = []
    for r in results:
        m = r["metrics"]["full"]
        rows.append({
            "config": r["config"],
            "trades": m["trades"],
            "pf": m["pf"],
            "top5": m["top5"],
            "top10": m["top10"],
            "worst_month": m["worst_month"],
            "worst_5day": m["worst_5day"],
        })
    lines = [
        "# Concentration audit",
        "",
        pd.DataFrame(rows).sort_values(["pf", "top10"], ascending=[False, True]).to_markdown(index=False),
        "",
        "## Read rule",
        "- Top5/Top10 càng thấp càng tốt.",
        "- Worst month và worst 5-day stretch cho biết engine có bị phụ thuộc vài episode hay không.",
    ]
    return "\n".join(lines)


def build_split_rolling_md(results: list) -> str:
    lines = ["# Split and rolling stability report", ""]
    for r in results:
        m = r["metrics"]
        lines.extend([
            f"## {r['config']} — {r['family']}",
            "",
            pd.DataFrame([{
                "full_pf": m["full"]["pf"],
                "full_dd": m["full"]["dd"],
                "splitA_trades": m["splits"]["A"]["trades"],
                "splitA_pf": m["splits"]["A"]["pf"],
                "splitA_dd": m["splits"]["A"]["dd"],
                "splitB_trades": m["splits"]["B"]["trades"],
                "splitB_pf": m["splits"]["B"]["pf"],
                "splitB_dd": m["splits"]["B"]["dd"],
                "rolling_profitable": m["full"]["rolling_profitable"],
                "rolling_avg_pf": m["full"]["rolling_avg_pf"],
            }]).to_markdown(index=False),
            "",
            pd.DataFrame(m["metrics"]["rolling"] if "metrics" in m else m["rolling"]).to_markdown(index=False) if False else pd.DataFrame(m["rolling"]).to_markdown(index=False),
            "",
        ])
    return "\n".join(lines)


def simulate_reversal_variant(day_row: pd.Series, m5_group: pd.DataFrame, m1_group: pd.DataFrame, point: float, variant: str, timeout_bars: int) -> float:
    direction = int(day_row["failure_dir"])
    if direction == 0 or m5_group.empty:
        return 0.0

    entry_min = 10 * 60 + 5
    m5_trade = m5_group[(m5_group["ny_min_of_day"] >= entry_min) & (m5_group["ny_min_of_day"] < 13 * 60 + 30)].reset_index(drop=True)
    if m5_trade.empty:
        return 0.0
    entry_bar = m5_trade.iloc[0]
    risk_dist = max(0.80 * float(day_row["atr14_pre_m5"]), 0.40 * float(day_row["preopen_range"]), point)
    spread_cost = float(entry_bar.get("spread", 0.0)) * point
    entry_price = float(entry_bar["open"])

    if variant in {"M1_ADVERSE", "M1_ADVERSE_SPREAD25"}:
        m1_window = m1_group[(m1_group["ny_min_of_day"] >= entry_min) & (m1_group["ny_min_of_day"] < entry_min + 5)].copy()
        if not m1_window.empty:
            if direction > 0:
                entry_price = float(m1_window["open"].max())
            else:
                entry_price = float(m1_window["open"].min())
    if variant == "M1_ADVERSE_SPREAD25":
        spread_cost *= 1.25

    stop = entry_price - direction * risk_dist
    target = entry_price + direction * risk_dist
    exit_price = float(m5_trade.iloc[min(len(m5_trade), timeout_bars) - 1]["close"])

    for _, bar in m5_trade.iloc[:timeout_bars].iterrows():
        hi = float(bar["high"])
        lo = float(bar["low"])
        if direction > 0:
            stop_hit = lo <= stop
            target_hit = hi >= target
        else:
            stop_hit = hi >= stop
            target_hit = lo <= target
        if stop_hit and target_hit:
            exit_price = stop
            break
        if stop_hit:
            exit_price = stop
            break
        if target_hit:
            exit_price = target
            break

    gross_r = direction * (exit_price - entry_price) / risk_dist
    return gross_r - (spread_cost / risk_dist)


def build_mini_realism(best: dict, frame: pd.DataFrame, m1: pd.DataFrame, m5: pd.DataFrame, point: float, mod) -> str:
    mask = best["mask"]
    subset = frame.loc[mask].copy()
    m1_groups = {d: g.reset_index(drop=True) for d, g in m1.groupby("ny_date")}
    m5_groups = {d: g.reset_index(drop=True) for d, g in m5.groupby("ny_date")}

    rows = []
    for variant in ["BASE", "M1_ADVERSE", "M1_ADVERSE_SPREAD25"]:
        vals = []
        for _, row in subset.iterrows():
            day = row["ny_date"]
            if variant == "BASE":
                vals.append(float(row["reversal_r"]))
            else:
                vals.append(simulate_reversal_variant(row, m5_groups.get(day, pd.DataFrame()), m1_groups.get(day, pd.DataFrame()), point, variant, mod.TIMEOUT_BARS))
        rows.append({
            "variant": variant,
            "trades": int(len(vals)),
            "net_r": round(float(sum(vals)), 4),
            "pf": round(float(pf(vals)), 4),
            "dd": round(float(drawdown_pct(vals)), 2),
        })

    lines = [
        "# Mini realism sanity",
        "",
        "## Cảnh báo",
        "- Đây là **offline sanity stress**, không phải MT5 Strategy Tester real-ticks validation.",
        "- `M1_ADVERSE` dùng fill bất lợi từ M1 trong 5 phút đầu sau 10:05.",
        "- `M1_ADVERSE_SPREAD25` cộng thêm stress spread +25%.",
        "",
        f"## Best family: {best['config']}",
        "",
        pd.DataFrame(rows).to_markdown(index=False),
    ]
    return "\n".join(lines), rows


def build_trade_stories(best: dict, frame: pd.DataFrame):
    mask = best["mask"]
    sub = frame.loc[mask].copy()
    reason_cols = best["reason_cols"]
    trade_rows = []
    blocked_rows = []
    for _, row in frame.iterrows():
        if bool(mask.loc[row.name]):
            trade_rows.append({
                "ny_date": str(row["ny_date"]),
                "symbol": SYMBOL,
                "config": best["config"],
                "family": best["family"],
                "split": row["split"],
                "hypothesis": best["hypothesis"],
                "why_allowed": {c: row[c] for c in reason_cols},
                "reversal_r": round(float(row["reversal_r"]), 5),
                "hold_minutes": round(float(row["reversal_hold"]), 2),
                "exit_reason": row["reversal_exit_reason"],
                "entry_ny": row["reversal_entry_ny"],
                "exit_ny": row["reversal_exit_ny"],
            })
        else:
            blocked_rows.append({
                "ny_date": str(row["ny_date"]),
                "symbol": SYMBOL,
                "config": best["config"],
                "family": best["family"],
                "split": row["split"],
                "blocked_reason": "FAMILY_CONDITION_NOT_MET",
                "reason_features": {c: row[c] for c in reason_cols},
                "base_reversal_r_if_forced": round(float(row["reversal_r"]), 5),
            })
    return trade_rows, blocked_rows


def build_summary_json(best: dict, ranked: pd.DataFrame, mini_rows: list) -> dict:
    return {
        "generated_at": datetime.now().isoformat(),
        "best_family": best["config"],
        "ranking": ranked.to_dict(orient="records"),
        "best_metrics": best["metrics"],
        "mini_realism": mini_rows,
    }


def main():
    mod = load_phase3b()
    frame, m1, m5, point = load_base_frame(mod)
    thr = split_a_thresholds(frame)
    specs = build_family_specs(frame, thr)
    results = analyze_families(frame, specs, mod)
    ranked = rank_families(results)

    # density-first strategic choice among families with splitB > 1
    promotable_pool = ranked[ranked["splitB_pf"] > 1.0].copy()
    if not promotable_pool.empty:
        promotable_pool = promotable_pool.sort_values(["trades", "splitB_pf", "top10"], ascending=[False, False, True])
        best_cfg = str(promotable_pool.iloc[0]["config"])
    else:
        best_cfg = str(ranked.iloc[0]["config"])
    best = next(r for r in results if r["config"] == best_cfg)

    write_text(OUT_DIR / "reversal_engine_family_comparison.md", build_family_comparison_md(ranked, results))
    write_text(OUT_DIR / "sample_density_report.md", build_sample_density_md(best, frame))
    write_text(OUT_DIR / "concentration_audit.md", build_concentration_md(ranked, results))
    write_text(OUT_DIR / "split_rolling_stability_report.md", build_split_rolling_md(results))
    mini_md, mini_rows = build_mini_realism(best, frame, m1, m5, point, mod)
    write_text(OUT_DIR / "mini_realism_sanity.md", mini_md)

    trades, blocked = build_trade_stories(best, frame)
    write_jsonl(OUT_DIR / "trade_story.jsonl", trades)
    write_jsonl(OUT_DIR / "blocked_signal_story.jsonl", blocked)
    ranked.to_csv(OUT_DIR / "phaseR1_family_comparison.csv", index=False)
    write_json(OUT_DIR / "phaseR1_summary.json", build_summary_json(best, ranked, mini_rows))


if __name__ == "__main__":
    main()
