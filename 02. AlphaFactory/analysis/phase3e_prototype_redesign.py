#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import importlib.util
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(r"02. AlphaFactory/runs/XAU_Scalp_Portfolio")
OUT_DIR = ROOT / "phase3e_prototypes_20260308"
PHASE3B_SCRIPT = Path(r"02. AlphaFactory/analysis/phase3b_router_simulation.py")

LABEL_CONT = "CONTINUATION"
LABEL_REV = "REVERSAL"
LABEL_ABS = "ABSTAIN"

BEST_R_MIN = 0.15
GAP_R_MIN = 0.20


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


def load_base_frame(mod):
    features = mod.load_features()
    m1, m5, point = mod.load_mt5_rates()
    day_ctx = mod.build_daily_market_context(features, m1, m5, point)
    frame = features.merge(day_ctx, on="ny_date", how="inner").sort_values("ny_date").reset_index(drop=True)
    sim = mod.simulate_day_playbooks(frame, m5, point)
    sim["continuation_base_r"] = sim["ACCEPTANCE_realized_r"].astype(float)
    sim["reversal_base_r"] = sim["FAILURE_FADE_realized_r"].astype(float)
    sim["base_best_r"] = sim[["continuation_base_r", "reversal_base_r"]].max(axis=1)
    sim["base_gap_r"] = (sim["continuation_base_r"] - sim["reversal_base_r"]).abs()
    sim["base_best_action"] = np.where(
        sim["continuation_base_r"] > sim["reversal_base_r"],
        LABEL_CONT,
        np.where(sim["reversal_base_r"] > sim["continuation_base_r"], LABEL_REV, LABEL_ABS),
    )
    return sim


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
    }


def pf(vals) -> float:
    vals = [float(v) for v in vals]
    gp = sum(v for v in vals if v > 0)
    gl = -sum(v for v in vals if v < 0)
    return gp / gl if gl > 0 else 999.99


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


def subset_metrics(frame: pd.DataFrame, mask: pd.Series, r_col: str, roll_windows) -> dict:
    subset = frame.loc[mask].copy()
    vals = subset[r_col].astype(float).tolist()
    full = {
        "trades": int(len(subset)),
        "net_r": round(float(sum(vals)), 4),
        "pf": round(float(pf(vals)), 4),
        "dd": round(float(drawdown_pct(vals)), 2),
        "avg_r": round(float(pd.Series(vals).mean()), 4) if vals else 0.0,
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


def build_config_masks(frame: pd.DataFrame, thr: dict) -> dict:
    sp_low = frame["spread_pct_10"] <= thr["spread_low"]
    h0 = frame["handoff_conflict"] == 0
    h1 = frame["handoff_conflict"] == 1
    l_low = frame["london_pos_at_open"] <= thr["london_pos_mid"]
    l_high = frame["london_pos_at_open"] > thr["london_pos_mid"]
    vdist_hi = frame["vwap_dist_30_norm"] >= thr["vdist_mid"]
    rot_lo = frame["rotation_30"] <= thr["rot_mid"]
    rot_hi = frame["rotation_30"] >= thr["rot_mid"]
    mid_hi = frame["or_mid_status_30"].abs() >= thr["mid_abs_mid"]
    acc_hi = frame["accept_balance_30"] >= thr["accept_mid"]
    or10_lo = frame["or10_width_norm"] <= thr["or10_mid"]
    or10_hi = frame["or10_width_norm"] >= thr["or10_mid"]
    recl15 = frame["vwap_reclaim_15"] == 1

    return {
        "P3E_BASE_DIRECT": {
            "continuation_rule": "Không filter: continuation prototype luôn hợp lệ tại 10:05.",
            "reversal_rule": "Không filter: reversal prototype luôn hợp lệ tại 10:05.",
            "cont_mask": pd.Series(True, index=frame.index),
            "rev_mask": pd.Series(True, index=frame.index),
            "cont_reason_cols": [],
            "rev_reason_cols": [],
        },
        "P3E_BALANCED_VALUE_CONFLICT": {
            "continuation_rule": "Continuation chỉ hợp lệ khi NY mở ở nửa dưới London range và spread đầu mở thấp.",
            "reversal_rule": "Reversal chỉ hợp lệ khi có handoff conflict + acceptance balance cao + open ở nửa trên London range + spread thấp.",
            "cont_mask": l_low & sp_low,
            "rev_mask": h1 & acc_hi & l_high & sp_low,
            "cont_reason_cols": ["london_pos_at_open", "spread_pct_10"],
            "rev_reason_cols": ["handoff_conflict", "accept_balance_30", "london_pos_at_open", "spread_pct_10"],
        },
        "P3E_DENSER_HANDOFF_POLAR": {
            "continuation_rule": "Continuation khi London→NY handoff aligned và spread thấp.",
            "reversal_rule": "Reversal khi dislocation khỏi VWAP cao + handoff conflict + open ở nửa trên London range + spread thấp.",
            "cont_mask": h0 & sp_low,
            "rev_mask": vdist_hi & h1 & l_high & sp_low,
            "cont_reason_cols": ["handoff_conflict", "spread_pct_10"],
            "rev_reason_cols": ["vwap_dist_30_norm", "handoff_conflict", "london_pos_at_open", "spread_pct_10"],
        },
        "P3E_CLEAN_VDIST_POLAR": {
            "continuation_rule": "Continuation khi dislocation khỏi VWAP cao + handoff aligned + open ở nửa trên London range + spread thấp.",
            "reversal_rule": "Reversal khi dislocation khỏi VWAP cao + handoff conflict + open ở nửa trên London range + spread thấp.",
            "cont_mask": vdist_hi & h0 & l_high & sp_low,
            "rev_mask": vdist_hi & h1 & l_high & sp_low,
            "cont_reason_cols": ["vwap_dist_30_norm", "handoff_conflict", "london_pos_at_open", "spread_pct_10"],
            "rev_reason_cols": ["vwap_dist_30_norm", "handoff_conflict", "london_pos_at_open", "spread_pct_10"],
        },
        "P3E_PULLBACK_REJECTION": {
            "continuation_rule": "Continuation khi OR10 hẹp + open ở nửa dưới London range + có VWAP reclaim sớm + spread thấp.",
            "reversal_rule": "Reversal khi |OR-mid status| cao + rotation cao + acceptance balance cao + spread thấp.",
            "cont_mask": or10_lo & l_low & recl15 & sp_low,
            "rev_mask": mid_hi & rot_hi & acc_hi & sp_low,
            "cont_reason_cols": ["or10_width_norm", "london_pos_at_open", "vwap_reclaim_15", "spread_pct_10"],
            "rev_reason_cols": ["or_mid_status_30", "rotation_30", "accept_balance_30", "spread_pct_10"],
        },
        "P3E_ROTATION_POLAR": {
            "continuation_rule": "Continuation khi rotation thấp + handoff aligned + open ở nửa trên London range + spread thấp.",
            "reversal_rule": "Reversal khi handoff conflict + OR10 rộng + spread thấp.",
            "cont_mask": rot_lo & h0 & l_high & sp_low,
            "rev_mask": h1 & or10_hi & sp_low,
            "cont_reason_cols": ["rotation_30", "handoff_conflict", "london_pos_at_open", "spread_pct_10"],
            "rev_reason_cols": ["handoff_conflict", "or10_width_norm", "spread_pct_10"],
        },
    }


def analyze_config(name: str, frame: pd.DataFrame, spec: dict, mod) -> dict:
    cont_mask = spec["cont_mask"].astype(bool)
    rev_mask = spec["rev_mask"].astype(bool)
    cont_eff = frame["continuation_base_r"].where(cont_mask, 0.0)
    rev_eff = frame["reversal_base_r"].where(rev_mask, 0.0)
    best_r = np.maximum(cont_eff, rev_eff)
    second_r = np.minimum(cont_eff, rev_eff)
    gap_r = best_r - second_r
    winner = np.where(cont_eff > rev_eff, LABEL_CONT, np.where(rev_eff > cont_eff, LABEL_REV, LABEL_ABS))
    action_label = np.where((best_r <= BEST_R_MIN) | (gap_r <= GAP_R_MIN), LABEL_ABS, winner)

    cont_metrics = subset_metrics(frame, cont_mask, "continuation_base_r", mod.ROLL_WINDOWS)
    rev_metrics = subset_metrics(frame, rev_mask, "reversal_base_r", mod.ROLL_WINDOWS)

    acted_mask = action_label != LABEL_ABS
    abstain_mask = action_label == LABEL_ABS
    base_strong_mask = (frame["base_best_r"] > BEST_R_MIN) & (frame["base_gap_r"] > GAP_R_MIN)
    base_weak_mask = frame["base_best_r"] <= BEST_R_MIN
    base_small_gap_mask = frame["base_gap_r"] <= GAP_R_MIN

    gap_metrics = {
        "active_union_days": int((cont_mask | rev_mask).sum()),
        "both_active_days": int((cont_mask & rev_mask).sum()),
        "both_inactive_days": int((~cont_mask & ~rev_mask).sum()),
        "continuation_winner_days": int((action_label == LABEL_CONT).sum()),
        "reversal_winner_days": int((action_label == LABEL_REV).sum()),
        "abstain_days": int(abstain_mask.sum()),
        "mean_gap_acted": round(float(pd.Series(gap_r[acted_mask]).mean()), 4) if acted_mask.any() else 0.0,
        "median_gap_acted": round(float(pd.Series(gap_r[acted_mask]).median()), 4) if acted_mask.any() else 0.0,
        "acted_rate_pct": round(float(acted_mask.mean() * 100.0), 2),
    }

    abstain_metrics = {
        "abstain_days": int(abstain_mask.sum()),
        "base_weak_days": int((abstain_mask & base_weak_mask).sum()),
        "base_small_gap_days": int((abstain_mask & base_small_gap_mask).sum()),
        "blocked_meaningful_base_days": int((abstain_mask & base_strong_mask).sum()),
        "blocked_meaningful_base_best_r_sum": round(float(frame.loc[abstain_mask & base_strong_mask, "base_best_r"].sum()), 4),
        "blocked_meaningful_base_best_r_mean": round(float(frame.loc[abstain_mask & base_strong_mask, "base_best_r"].mean()), 4)
        if int((abstain_mask & base_strong_mask).sum())
        else 0.0,
    }

    return {
        "config": name,
        "continuation_rule": spec["continuation_rule"],
        "reversal_rule": spec["reversal_rule"],
        "cont_reason_cols": spec["cont_reason_cols"],
        "rev_reason_cols": spec["rev_reason_cols"],
        "cont_mask": cont_mask,
        "rev_mask": rev_mask,
        "cont_eff": cont_eff,
        "rev_eff": rev_eff,
        "winner": winner,
        "action_label": action_label,
        "gap_r": gap_r,
        "best_r": best_r,
        "cont_metrics": cont_metrics,
        "rev_metrics": rev_metrics,
        "gap_metrics": gap_metrics,
        "abstain_metrics": abstain_metrics,
    }


def rank_configs(results: list) -> pd.DataFrame:
    rows = []
    for r in results:
        rows.append({
            "config": r["config"],
            "cont_trades": r["cont_metrics"]["full"]["trades"],
            "rev_trades": r["rev_metrics"]["full"]["trades"],
            "active_union_days": r["gap_metrics"]["active_union_days"],
            "cont_pf": r["cont_metrics"]["full"]["pf"],
            "rev_pf": r["rev_metrics"]["full"]["pf"],
            "cont_splitB_pf": r["cont_metrics"]["splits"]["B"]["pf"],
            "rev_splitB_pf": r["rev_metrics"]["splits"]["B"]["pf"],
            "cont_roll": r["cont_metrics"]["full"]["rolling_profitable"],
            "rev_roll": r["rev_metrics"]["full"]["rolling_profitable"],
            "abstain_days": r["abstain_metrics"]["abstain_days"],
            "blocked_meaningful_base_days": r["abstain_metrics"]["blocked_meaningful_base_days"],
            "mean_gap_acted": r["gap_metrics"]["mean_gap_acted"],
            "score_min_splitB_pf": min(r["cont_metrics"]["splits"]["B"]["pf"], r["rev_metrics"]["splits"]["B"]["pf"]),
        })
    ranked = pd.DataFrame(rows).sort_values(
        ["score_min_splitB_pf", "active_union_days", "mean_gap_acted"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    return ranked


def build_family_table_md(ranked: pd.DataFrame) -> str:
    cols = [
        "config", "cont_trades", "rev_trades", "active_union_days",
        "cont_pf", "rev_pf", "cont_splitB_pf", "rev_splitB_pf",
        "cont_roll", "rev_roll", "abstain_days", "blocked_meaningful_base_days",
    ]
    return ranked[cols].to_markdown(index=False)


def rolling_lines(title: str, rolling_rows: list) -> list:
    lines = [f"### {title}", ""]
    lines.append(pd.DataFrame(rolling_rows).to_markdown(index=False))
    lines.append("")
    return lines


def build_winner_gap_audit(results: list, ranked: pd.DataFrame):
    lines = [
        "# Winner gap audit",
        "",
        "## Cảnh báo phương pháp",
        "- Raw winner-gap của baseline direct vốn đã lớn vì continuation/reversal là hai phía đối xứng 1R/1R.",
        "- Phase 3E vì thế không đọc winner-gap thuần túy như 'edge', mà đọc cùng với expectancy của từng action subset và ý nghĩa của ABSTAIN.",
        "",
        "## Config comparison",
        "",
        build_family_table_md(ranked),
        "",
    ]
    for r in results:
        gm = r["gap_metrics"]
        lines.extend([
            f"## {r['config']}",
            f"- Continuation winner days: **{gm['continuation_winner_days']}**",
            f"- Reversal winner days: **{gm['reversal_winner_days']}**",
            f"- Abstain days: **{gm['abstain_days']}**",
            f"- Mean / median gap on acted days: **{gm['mean_gap_acted']} / {gm['median_gap_acted']}R**",
            f"- Acted-rate: **{gm['acted_rate_pct']}%**",
            "",
        ])
    return "\n".join(lines)


def build_action_expectancy_md(results: list, ranked: pd.DataFrame) -> str:
    lines = ["# Prototype action expectancy", ""]
    lines.append("## Ranked configs")
    lines.append("")
    lines.append(build_family_table_md(ranked))
    lines.append("")
    for r in results:
        cm = r["cont_metrics"]
        rm = r["rev_metrics"]
        lines.extend([
            f"## {r['config']}",
            "",
            "### Continuation active subset",
            pd.DataFrame([{
                "trades": cm["full"]["trades"],
                "full_pf": cm["full"]["pf"],
                "full_dd": cm["full"]["dd"],
                "splitA_pf": cm["splits"]["A"]["pf"],
                "splitB_pf": cm["splits"]["B"]["pf"],
                "rolling_profitable": cm["full"]["rolling_profitable"],
                "rolling_avg_pf": cm["full"]["rolling_avg_pf"],
            }]).to_markdown(index=False),
            "",
            "### Reversal active subset",
            pd.DataFrame([{
                "trades": rm["full"]["trades"],
                "full_pf": rm["full"]["pf"],
                "full_dd": rm["full"]["dd"],
                "splitA_pf": rm["splits"]["A"]["pf"],
                "splitB_pf": rm["splits"]["B"]["pf"],
                "rolling_profitable": rm["full"]["rolling_profitable"],
                "rolling_avg_pf": rm["full"]["rolling_avg_pf"],
            }]).to_markdown(index=False),
            "",
        ])
    lines.extend([
        "## Winner-only caveat",
        "- Nếu chỉ đo expectancy trên các ngày mà action 'thắng' theo oracle, PF sẽ cơ học bị thổi phồng vì label đã yêu cầu best-action dương và gap đủ lớn.",
        "- Metric operational trong Phase 3E vì vậy là **active-subset expectancy**, không phải oracle winner-only expectancy.",
    ])
    return "\n".join(lines)


def build_abstain_report(results: list, ranked: pd.DataFrame) -> str:
    rows = []
    for r in results:
        am = r["abstain_metrics"]
        rows.append({
            "config": r["config"],
            "abstain_days": am["abstain_days"],
            "base_weak_days": am["base_weak_days"],
            "base_small_gap_days": am["base_small_gap_days"],
            "blocked_meaningful_base_days": am["blocked_meaningful_base_days"],
            "blocked_bestR_sum": am["blocked_meaningful_base_best_r_sum"],
            "blocked_bestR_mean": am["blocked_meaningful_base_best_r_mean"],
        })
    lines = [
        "# Abstain meaning report",
        "",
        "## Audit rule",
        "- ABSTAIN chỉ được xem là có ý nghĩa nếu đa số ngày bị flat là vì **cả hai action đều yếu** hoặc **winner-gap quá nhỏ**.",
        "- Nếu ABSTAIN chặn nhiều ngày mà baseline direct vẫn có winner-gap lớn và best-action dương, thì improvement đang đến từ sparsity hơn là do action rõ hơn.",
        "",
        pd.DataFrame(rows).to_markdown(index=False),
        "",
    ]
    best = ranked.iloc[0]["config"]
    best_row = next(r for r in results if r["config"] == best)
    am = best_row["abstain_metrics"]
    lines.extend([
        f"## Best-ranked config: {best}",
        f"- Abstain days: **{am['abstain_days']}**",
        f"- Base-weak days inside abstain: **{am['base_weak_days']}**",
        f"- Base-small-gap days inside abstain: **{am['base_small_gap_days']}**",
        f"- Blocked meaningful baseline days: **{am['blocked_meaningful_base_days']}**",
        f"- Sum blocked best-action R: **{am['blocked_meaningful_base_best_r_sum']}R**",
        "",
        "## Interpretation",
        "- Nếu `blocked_meaningful_base_days` quá lớn so với `base_weak_days + base_small_gap_days`, ABSTAIN đang là cơ chế cắt activity mạnh tay hơn là cơ chế đọc action rõ hơn.",
    ])
    return "\n".join(lines)


def build_fairness_md(best_result: dict, thresholds: dict) -> str:
    lines = [
        "# Prototype redesign fairness",
        "",
        "## Neutral framework giữ nguyên cho cả continuation và reversal",
        "- Decision time / evaluation point: **10:00 NY**",
        "- Entry reference: **10:05 NY onward** (cùng trade result base từ Phase 3B)",
        "- Stop family: **max(0.8 * ATR14 pre-open, 0.4 * pre-open range, point)**",
        "- Target family: **1R fixed**",
        "- Timeout: **12 bar M5**",
        "- Spread: **cùng spread charge của entry bar**",
        "- Same-bar collision rule: **SL-first**",
        "- Không trailing, không partial, không exit asymmetric",
        "",
        "## Threshold source",
        "- Tất cả threshold trong Phase 3E lấy từ **median/quantile của Split A**.",
        "- Không genetic search, không broad sweep, không threshold chasing theo full sample.",
        "",
        "## Best config rules",
        f"- Config: **{best_result['config']}**",
        f"- Continuation rule: {best_result['continuation_rule']}",
        f"- Reversal rule: {best_result['reversal_rule']}",
        "",
        "## Fairness verdict",
        "- Cải thiện nếu có đến từ **playbook-validity gating** trên cùng trade template, không đến từ exit bias.",
        "- Điểm cần cảnh báo: vì gating mạnh, improvement có thể đến từ sparsity/abstention hơn là từ action quality thực sự.",
    ]
    return "\n".join(lines)


def build_split_rolling_md(results: list, ranked: pd.DataFrame) -> str:
    lines = ["# Split and rolling prototype report", ""]
    for r in results:
        lines.extend([
            f"## {r['config']}",
            "",
            "### Continuation",
            pd.DataFrame([{
                "full_pf": r["cont_metrics"]["full"]["pf"],
                "full_dd": r["cont_metrics"]["full"]["dd"],
                "splitA_pf": r["cont_metrics"]["splits"]["A"]["pf"],
                "splitA_dd": r["cont_metrics"]["splits"]["A"]["dd"],
                "splitB_pf": r["cont_metrics"]["splits"]["B"]["pf"],
                "splitB_dd": r["cont_metrics"]["splits"]["B"]["dd"],
                "rolling_profitable": r["cont_metrics"]["full"]["rolling_profitable"],
                "rolling_avg_pf": r["cont_metrics"]["full"]["rolling_avg_pf"],
            }]).to_markdown(index=False),
            "",
        ])
        lines.extend(rolling_lines("Continuation rolling windows", r["cont_metrics"]["rolling"]))
        lines.extend([
            "### Reversal",
            pd.DataFrame([{
                "full_pf": r["rev_metrics"]["full"]["pf"],
                "full_dd": r["rev_metrics"]["full"]["dd"],
                "splitA_pf": r["rev_metrics"]["splits"]["A"]["pf"],
                "splitA_dd": r["rev_metrics"]["splits"]["A"]["dd"],
                "splitB_pf": r["rev_metrics"]["splits"]["B"]["pf"],
                "splitB_dd": r["rev_metrics"]["splits"]["B"]["dd"],
                "rolling_profitable": r["rev_metrics"]["full"]["rolling_profitable"],
                "rolling_avg_pf": r["rev_metrics"]["full"]["rolling_avg_pf"],
            }]).to_markdown(index=False),
            "",
        ])
        lines.extend(rolling_lines("Reversal rolling windows", r["rev_metrics"]["rolling"]))
    return "\n".join(lines)


def build_drawdown_replay(best_result: dict, frame: pd.DataFrame) -> str:
    cfg = best_result["config"]
    cont_mask = best_result["cont_mask"]
    rev_mask = best_result["rev_mask"]
    acted = frame.copy()
    acted["action"] = np.where(cont_mask, LABEL_CONT, np.where(rev_mask, LABEL_REV, LABEL_ABS))
    acted["strategy_r"] = np.where(cont_mask, acted["continuation_base_r"], np.where(rev_mask, acted["reversal_base_r"], 0.0))
    acted = acted[acted["action"] != LABEL_ABS].copy().sort_values("ny_date")
    if acted.empty:
        return "# Drawdown replay gallery\n\n_No active trades._"
    acted["day_loss_rank"] = acted["strategy_r"].rank(method="first")
    worst_days = acted.nsmallest(10, "strategy_r")[[
        "ny_date", "split", "action", "strategy_r", "continuation_base_r", "reversal_base_r",
        "handoff_conflict", "london_pos_at_open", "vwap_dist_30_norm", "spread_pct_10"
    ]]
    by_day = acted.groupby("ny_date")["strategy_r"].sum().sort_index()
    worst_5 = by_day.rolling(5).sum().sort_values().head(5)
    lines = [
        "# Drawdown replay gallery",
        "",
        f"## Best config: {cfg}",
        "",
        "### Worst single-day action outcomes",
        worst_days.to_markdown(index=False),
        "",
        "### Worst rolling 5-day stretches",
        pd.DataFrame([{"end_date": str(idx), "rolling5_r": round(float(val), 4)} for idx, val in worst_5.items()]).to_markdown(index=False),
    ]
    return "\n".join(lines)


def build_trade_stories(best_result: dict, frame: pd.DataFrame) -> tuple[list, list]:
    stories = []
    blocked = []
    cont_mask = best_result["cont_mask"]
    rev_mask = best_result["rev_mask"]
    cont_cols = best_result["cont_reason_cols"]
    rev_cols = best_result["rev_reason_cols"]
    for _, row in frame.iterrows():
        cont_valid = bool(cont_mask.loc[row.name])
        rev_valid = bool(rev_mask.loc[row.name])
        cont_r = float(row["continuation_base_r"]) if cont_valid else 0.0
        rev_r = float(row["reversal_base_r"]) if rev_valid else 0.0
        best_r = max(cont_r, rev_r)
        gap_r = abs(cont_r - rev_r)
        action = LABEL_ABS
        if best_r > BEST_R_MIN and gap_r > GAP_R_MIN:
            action = LABEL_CONT if cont_r > rev_r else LABEL_REV if rev_r > cont_r else LABEL_ABS
        rec = {
            "ny_date": str(row["ny_date"]),
            "split": row["split"],
            "config": best_result["config"],
            "continuation_valid": cont_valid,
            "reversal_valid": rev_valid,
            "continuation_r": round(cont_r, 5),
            "reversal_r": round(rev_r, 5),
            "winner_gap_r": round(gap_r, 5),
            "selected_action": action,
            "base_best_action": row["base_best_action"],
            "base_best_r": round(float(row["base_best_r"]), 5),
            "key_features": {
                "handoff_conflict": int(row["handoff_conflict"]),
                "london_pos_at_open": round(float(row["london_pos_at_open"]), 5),
                "vwap_dist_30_norm": round(float(row["vwap_dist_30_norm"]), 5),
                "rotation_30": int(row["rotation_30"]),
                "accept_balance_30": int(row["accept_balance_30"]),
                "spread_pct_10": round(float(row["spread_pct_10"]), 5),
                "or10_width_norm": round(float(row["or10_width_norm"]), 5),
            },
        }
        if action == LABEL_CONT:
            rec["story"] = {
                "why_allowed": best_result["continuation_rule"],
                "reason_features": {c: row[c] for c in cont_cols},
                "result_r": round(cont_r, 5),
            }
            stories.append(rec)
        elif action == LABEL_REV:
            rec["story"] = {
                "why_allowed": best_result["reversal_rule"],
                "reason_features": {c: row[c] for c in rev_cols},
                "result_r": round(rev_r, 5),
            }
            stories.append(rec)
        else:
            blocked.append({
                "ny_date": str(row["ny_date"]),
                "split": row["split"],
                "config": best_result["config"],
                "abstain_reason": "BOTH_ACTIONS_WEAK_OR_GAP_TOO_SMALL" if (best_r <= BEST_R_MIN or gap_r <= GAP_R_MIN) else "BOTH_PROTOTYPES_INACTIVE",
                "continuation_valid": cont_valid,
                "reversal_valid": rev_valid,
                "continuation_rule": best_result["continuation_rule"],
                "reversal_rule": best_result["reversal_rule"],
                "base_best_action": row["base_best_action"],
                "base_best_r": round(float(row["base_best_r"]), 5),
                "base_gap_r": round(float(row["base_gap_r"]), 5),
                "key_features": {
                    "handoff_conflict": int(row["handoff_conflict"]),
                    "london_pos_at_open": round(float(row["london_pos_at_open"]), 5),
                    "vwap_dist_30_norm": round(float(row["vwap_dist_30_norm"]), 5),
                    "rotation_30": int(row["rotation_30"]),
                    "accept_balance_30": int(row["accept_balance_30"]),
                    "spread_pct_10": round(float(row["spread_pct_10"]), 5),
                    "or10_width_norm": round(float(row["or10_width_norm"]), 5),
                },
            })
    return stories, blocked


def build_summary_json(best_result: dict, ranked: pd.DataFrame) -> dict:
    return {
        "generated_at": datetime.now().isoformat(),
        "best_config": best_result["config"],
        "ranking": ranked.to_dict(orient="records"),
        "best_continuation": best_result["cont_metrics"],
        "best_reversal": best_result["rev_metrics"],
        "best_gap": best_result["gap_metrics"],
        "best_abstain": best_result["abstain_metrics"],
    }


def main():
    mod = load_phase3b()
    frame = load_base_frame(mod)
    thresholds = split_a_thresholds(frame)
    config_specs = build_config_masks(frame, thresholds)

    results = [analyze_config(name, frame, spec, mod) for name, spec in config_specs.items()]
    ranked = rank_configs(results)
    best_cfg = str(ranked.iloc[0]["config"])
    best_result = next(r for r in results if r["config"] == best_cfg)

    write_text(OUT_DIR / "winner_gap_audit.md", build_winner_gap_audit(results, ranked))
    write_text(OUT_DIR / "prototype_action_expectancy.md", build_action_expectancy_md(results, ranked))
    write_text(OUT_DIR / "abstain_meaning_report.md", build_abstain_report(results, ranked))
    write_text(OUT_DIR / "prototype_redesign_fairness.md", build_fairness_md(best_result, thresholds))
    write_text(OUT_DIR / "split_rolling_prototype_report.md", build_split_rolling_md(results, ranked))
    write_text(OUT_DIR / "drawdown_replay_gallery.md", build_drawdown_replay(best_result, frame))

    stories, blocked = build_trade_stories(best_result, frame)
    write_jsonl(OUT_DIR / "trade_story.jsonl", stories)
    write_jsonl(OUT_DIR / "blocked_signal_story.jsonl", blocked)
    ranked.to_csv(OUT_DIR / "phase3e_family_comparison.csv", index=False)
    write_json(OUT_DIR / "phase3e_summary.json", build_summary_json(best_result, ranked))


if __name__ == "__main__":
    main()
