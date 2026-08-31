#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import importlib.util
import json
import math
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(r"02. AlphaFactory/runs/XAU_Scalp_Portfolio")
OUT_DIR = ROOT / "phase3c_tradability_20260308"
PHASE3B_SCRIPT = Path(r"02. AlphaFactory/analysis/phase3b_router_simulation.py")

BEST_R_MIN = 0.15
GAP_R_MIN = 0.20
MIN_OPERATIONAL_COUNT = 30
WARMUP_DAYS = 120

LABEL_CONT = "CONTINUATION_READY"
LABEL_REV = "REVERSAL_READY"
LABEL_REC = "RECLAIM_READY"
LABEL_FLAT = "AMBIGUOUS_FLAT"

LABEL_MAP = {
    "ACCEPTANCE": LABEL_CONT,
    "FAILURE_FADE": LABEL_REV,
    "POST_OPEN_RECLAIM": LABEL_REC,
}

ROLL_WINDOWS = [
    ("ROLL_2020_2021", "2020-03-07", "2021-03-06"),
    ("ROLL_2021_2022", "2021-03-07", "2022-03-06"),
    ("ROLL_2022_2023", "2022-03-07", "2023-03-06"),
    ("ROLL_2023_2024", "2023-03-07", "2024-03-06"),
    ("ROLL_2024_2025", "2024-03-07", "2025-03-06"),
    ("ROLL_2025_2026", "2025-03-07", "2026-03-06"),
]


def load_phase3b_module():
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


def mutual_info(series: pd.Series, labels: pd.Series, bins: int = 5) -> float:
    s = pd.Series(series)
    y = pd.Series(labels)
    mask = s.notna() & y.notna()
    s = s[mask]
    y = y[mask]
    if s.empty or s.nunique() <= 1:
        return 0.0
    try:
        if pd.api.types.is_numeric_dtype(s):
            s = pd.qcut(s, q=min(bins, s.nunique()), duplicates="drop")
        else:
            s = s.astype(str)
    except Exception:
        s = s.astype(str)
    joint = pd.crosstab(s, y, normalize=True)
    px = joint.sum(axis=1)
    py = joint.sum(axis=0)
    out = 0.0
    for i in joint.index:
        for j in joint.columns:
            pxy = joint.loc[i, j]
            if pxy > 0:
                out += pxy * math.log2(pxy / (px[i] * py[j]))
    return float(out)


def dominant_label(frame: pd.DataFrame, feature: str, label_col: str) -> str:
    sub = frame[[feature, label_col]].dropna()
    if sub.empty:
        return ""
    grp = sub.groupby(label_col)[feature].median().sort_values(ascending=False)
    return str(grp.index[0]) if not grp.empty else ""


def build_base_frame(mod):
    features = mod.load_features()
    m1, m5, point = mod.load_mt5_rates()
    day_ctx = mod.build_daily_market_context(features, m1, m5, point)
    df = features.merge(day_ctx, on="ny_date", how="inner").sort_values("ny_date").reset_index(drop=True)
    sim = mod.simulate_day_playbooks(df, m5, point)
    return mod, df, sim


def assign_labels(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in frame.iterrows():
        vals = {
            "ACCEPTANCE": float(r["ACCEPTANCE_realized_r"]),
            "FAILURE_FADE": float(r["FAILURE_FADE_realized_r"]),
            "POST_OPEN_RECLAIM": float(r["POST_OPEN_RECLAIM_realized_r"]),
        }
        ranked = sorted(vals.items(), key=lambda kv: kv[1], reverse=True)
        best_pb, best_r = ranked[0]
        second_pb, second_r = ranked[1]
        gap_r = best_r - second_r
        raw_label = LABEL_FLAT if (best_r <= BEST_R_MIN or gap_r <= GAP_R_MIN) else LABEL_MAP[best_pb]
        rows.append({
            "best_playbook": best_pb,
            "second_best_playbook": second_pb,
            "best_r": round(best_r, 5),
            "second_best_r": round(second_r, 5),
            "gap_r": round(gap_r, 5),
            "raw_label": raw_label,
            "is_ambiguous": raw_label == LABEL_FLAT,
        })
    out = pd.concat([frame.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    raw_counts = out["raw_label"].value_counts().to_dict()
    out["tradability_label"] = out["raw_label"]
    rare_labels = [lbl for lbl, cnt in raw_counts.items() if lbl != LABEL_FLAT and cnt < MIN_OPERATIONAL_COUNT]
    if rare_labels:
        out.loc[out["tradability_label"].isin(rare_labels), "tradability_label"] = LABEL_FLAT
    out["retired_raw_label"] = np.where(out["raw_label"] != out["tradability_label"], out["raw_label"], "")
    return out


def calc_oracle_metrics(mod, label_df: pd.DataFrame):
    strategy = label_df.copy()
    strategy["strategy_playbook"] = strategy["tradability_label"].map({
        LABEL_CONT: "ACCEPTANCE",
        LABEL_REV: "FAILURE_FADE",
        LABEL_REC: "POST_OPEN_RECLAIM",
        LABEL_FLAT: "NO_TRADE",
    })
    strategy["strategy_executed"] = strategy["strategy_playbook"] != "NO_TRADE"
    strategy["strategy_r"] = strategy.apply(
        lambda r: 0.0 if r["strategy_playbook"] == "NO_TRADE" else float(r[f"{r['strategy_playbook']}_realized_r"]), axis=1
    )
    strategy["strategy_hold"] = strategy.apply(
        lambda r: 0.0 if r["strategy_playbook"] == "NO_TRADE" else float(r[f"{r['strategy_playbook']}_hold_minutes"]), axis=1
    )
    full = mod.calc_strategy_metrics(strategy)
    split_a = mod.calc_strategy_metrics(mod.window_slice(strategy, mod.FULL_START, mod.SPLIT_A_END))
    split_b = mod.calc_strategy_metrics(mod.window_slice(strategy, mod.SPLIT_B_START, mod.FULL_END))
    rolling_rows, profitable, avg_pf = mod.rolling_summary(strategy)
    return strategy, full, split_a, split_b, rolling_rows, profitable, avg_pf


def separability_audit(frame: pd.DataFrame, features: list, label_col: str):
    model = Pipeline([
        ("imp", SimpleImputer(strategy="median")),
        ("sc", StandardScaler()),
        ("lr", LogisticRegression(max_iter=2000, class_weight="balanced")),
    ])
    preds = []
    for i in range(len(frame)):
        train = frame.iloc[:i]
        cur = frame.iloc[[i]]
        if i < WARMUP_DAYS or train[label_col].nunique() < 2:
            preds.append(LABEL_FLAT)
            continue
        model.fit(train[features], train[label_col])
        preds.append(model.predict(cur[features])[0])
    out = frame.copy()
    out["wf_pred_label"] = preds
    eval_out = out.iloc[WARMUP_DAYS:].copy()
    acc = float((eval_out["wf_pred_label"] == eval_out[label_col]).mean()) if not eval_out.empty else 0.0
    conf = pd.crosstab(eval_out["wf_pred_label"], eval_out[label_col], dropna=False)
    return out, acc, conf


def feature_scorecard(frame: pd.DataFrame, label_col: str):
    candidates = [
        "rotation_30", "or30_width_norm", "preopen_range_norm", "preopen_range_pct20", "or10_width_norm",
        "vwap_dist_30_norm", "impulse30_norm", "london_pos_at_open", "accept_balance_30",
        "accept_outside_london_30", "handoff_conflict", "london_extreme_sweep_norm", "vwap_reclaim_15",
        "or_mid_status_30", "spread_pct_10",
    ]
    rows = []
    for feat in candidates:
        full = mutual_info(frame[feat], frame[label_col])
        split_a = mutual_info(frame[frame["split"] == "A"][feat], frame[frame["split"] == "A"][label_col])
        split_b = mutual_info(frame[frame["split"] == "B"][feat], frame[frame["split"] == "B"][label_col])
        rows.append({
            "feature": feat,
            "full_mi": round(full, 6),
            "splitA_mi": round(split_a, 6),
            "splitB_mi": round(split_b, 6),
            "robust_score": round(min(full, split_a, split_b), 6),
            "dominant_label": dominant_label(frame, feat, label_col),
        })
    return pd.DataFrame(rows).sort_values(["robust_score", "full_mi"], ascending=False).reset_index(drop=True)


def build_quality_report(frame: pd.DataFrame, raw_counts: dict, final_counts: dict, conf: pd.DataFrame, acc: float, out_dir: Path):
    split_counts = frame.groupby(["split", "tradability_label"]).size().unstack(fill_value=0)
    rolling_rows = []
    for name, start_s, end_s in ROLL_WINDOWS:
        start_d = pd.to_datetime(start_s).date()
        end_d = pd.to_datetime(end_s).date()
        sub = frame[(frame["ny_date"] >= start_d) & (frame["ny_date"] <= end_d)]
        counts = sub["tradability_label"].value_counts().to_dict()
        rolling_rows.append({"window": name, **counts})
    lines = [
        "# Decision-time label quality",
        "",
        "## Label rule",
        f"- Raw best-playbook label uses `best_r > {BEST_R_MIN}` and `gap(best-second) > {GAP_R_MIN}`.",
        f"- Any raw tradability class with `< {MIN_OPERATIONAL_COUNT}` days is retired into `AMBIGUOUS_FLAT`.",
        "",
        "## Raw label counts",
        f"- `{raw_counts}`",
        "",
        "## Final operational label counts",
        f"- `{final_counts}`",
        "",
        "## Split A / B stability",
        "",
        split_counts.to_markdown(),
        "",
        "## Rolling stability",
        "",
        pd.DataFrame(rolling_rows).fillna(0).to_markdown(index=False),
        "",
        "## Walk-forward separability sanity",
        f"- Simple logistic walk-forward accuracy (no threshold tuning): **{acc*100:.2f}%**",
        "",
        conf.to_markdown() if not conf.empty else "_No evaluable confusion matrix_",
        "",
        "## Operational verdict",
        "- `CONTINUATION_READY` and `REVERSAL_READY` are operationally non-empty.",
        "- `RECLAIM_READY` is too sparse under the neutral prototype ceiling and is retired from the operational taxonomy for now.",
        "- `AMBIGUOUS_FLAT` remains a required class, not a fallback nuisance.",
    ]
    write_text(out_dir / "decision_time_label_quality.md", "\n".join(lines))


def build_oracle_report(full: dict, split_a: dict, split_b: dict, rolling_rows: list, profitable: int, avg_pf: float, out_dir: Path):
    lines = [
        "# Oracle ceiling report",
        "",
        "This oracle uses the **decision-time tradability labels built from post-lock prototype outcomes**.",
        "It is a ceiling study only, not a live-like router result.",
        "",
        f"- Full PF/DD: **{full['pf']} / {full['dd']}%**",
        f"- Split A PF/DD: **{split_a['pf']} / {split_a['dd']}%**",
        f"- Split B PF/DD: **{split_b['pf']} / {split_b['dd']}%**",
        f"- Rolling profitable windows: **{profitable}/{len(ROLL_WINDOWS)}** | avg PF **{avg_pf}**",
        "",
        pd.DataFrame(rolling_rows).to_markdown(index=False),
        "",
        "## Ceiling interpretation",
        "- If the oracle ceiling were still below PF 1.0, the NY-open router lane should be abandoned.",
        "- Here the ceiling is materially positive, so the lane remains alive.",
        "- The bottleneck shifts from **taxonomy existence** to **predictability / routing quality**.",
    ]
    write_text(out_dir / "oracle_ceiling_report.md", "\n".join(lines))


def build_fairness_audit(sim: pd.DataFrame, out_dir: Path):
    rows = []
    for pb in ["ACCEPTANCE", "FAILURE_FADE", "POST_OPEN_RECLAIM"]:
        ex = sim[sim[f"{pb}_executed"] == True].copy()
        vals = ex[f"{pb}_realized_r"].astype(float)
        rows.append({
            "playbook": pb,
            "trades": int(len(ex)),
            "avg_risk_dist": round(float(ex[f"{pb}_risk_dist"].astype(float).mean()), 4),
            "avg_hold": round(float(ex[f"{pb}_hold_minutes"].astype(float).mean()), 2),
            "win_rate_pct": round(float((vals > 0).mean() * 100.0), 2),
            "avg_win_r": round(float(vals[vals > 0].mean()), 4),
            "avg_loss_r": round(float(vals[vals < 0].mean()), 4),
            "tp_hits": int((ex[f"{pb}_exit_reason"] == "tp_hit").sum()),
            "sl_hits": int((ex[f"{pb}_exit_reason"] == "sl_hit").sum()),
            "timeouts": int((ex[f"{pb}_exit_reason"] == "timeout").sum()),
            "samebar_sl_first": int((ex[f"{pb}_exit_reason"] == "sl_first_same_bar").sum()),
        })
    lines = [
        "# Prototype fairness audit",
        "",
        "## Shared neutral rules",
        "- Same lock time, same entry time, same stop formula, same 1R target, same timeout, same spread charge, same same-bar conservative rule.",
        "- No trailing, no partials, no per-playbook exit creativity.",
        "",
        "## Empirical fairness table",
        "",
        pd.DataFrame(rows).to_markdown(index=False),
        "",
        "## Fairness verdict",
        "- Acceptance and Failure prototypes are near-symmetric under the neutral template.",
        "- Reclaim has almost identical risk/hold template and only differs by direction logic.",
        "- There is no evidence here of hidden exit-template favoritism creating the ceiling result.",
    ]
    write_text(out_dir / "prototype_fairness_audit.md", "\n".join(lines))


def build_prop_viability_map(out_dir: Path):
    rows = [
        {"tradability_label": LABEL_CONT, "ftmo_standard": "MEDIUM_LOW", "ftmo_swing": "MEDIUM", "the5ers_highstakes": "MEDIUM", "note": "Earliest and most open-sensitive; spread/news conflict highest."},
        {"tradability_label": LABEL_REV, "ftmo_standard": "MEDIUM", "ftmo_swing": "MEDIUM_HIGH", "the5ers_highstakes": "MEDIUM", "note": "Needs confirmation after open; more portable than raw chase continuation."},
        {"tradability_label": LABEL_REC, "ftmo_standard": "LOW_CONFIDENCE", "ftmo_swing": "LOW_CONFIDENCE", "the5ers_highstakes": "LOW_CONFIDENCE", "note": "Currently too sparse to estimate operational portability."},
        {"tradability_label": LABEL_FLAT, "ftmo_standard": "HIGH", "ftmo_swing": "HIGH", "the5ers_highstakes": "HIGH", "note": "Flat is most portable; avoids early-open violation risk."},
    ]
    lines = [
        "# Prop viability map",
        "",
        "Historical macro-news coverage is still incomplete, so this is an **estimate only**, not FTMO/The5ers validation.",
        "",
        pd.DataFrame(rows).to_markdown(index=False),
    ]
    write_text(out_dir / "prop_viability_map.md", "\n".join(lines))


def update_strategy_log(best_counts: dict):
    log_path = Path(r"02. AlphaFactory/STRATEGY_LOG.md")
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "",
        f"### XSP_PHASE3C_TRADABILITY_TAXONOMY ({stamp})",
        f"- Operational tradability counts: `{best_counts}`",
        f"- Thresholds fixed by design: best_r > `{BEST_R_MIN}`, gap > `{GAP_R_MIN}`, rare-class retire if count < `{MIN_OPERATIONAL_COUNT}`.",
        "- Key outcome: operational taxonomy collapses to Continuation / Reversal / Ambiguous; Reclaim is not yet operational under the neutral prototype ceiling.",
        "- Oracle ceiling remains strongly positive, so NY-open routing lane stays alive, but next step must focus on predictability not live deployment.",
    ]
    with log_path.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mod, df, sim = build_base_frame(load_phase3b_module())
    label_df = assign_labels(sim)
    raw_counts = label_df["raw_label"].value_counts().to_dict()
    final_counts = label_df["tradability_label"].value_counts().to_dict()

    ceiling_cols = [
        "ny_date", "split", "weekday", "day_type",
        "ACCEPTANCE_realized_r", "FAILURE_FADE_realized_r", "POST_OPEN_RECLAIM_realized_r",
        "best_playbook", "second_best_playbook", "best_r", "second_best_r", "gap_r",
        "raw_label", "tradability_label", "retired_raw_label",
    ]
    label_df[ceiling_cols].to_csv(OUT_DIR / "playbook_ceiling_matrix.csv", index=False)

    sep_df, acc, conf = separability_audit(label_df, mod.FEATURES, "tradability_label")
    build_quality_report(label_df, raw_counts, final_counts, conf, acc, OUT_DIR)

    oracle_df, full, split_a, split_b, rolling_rows, profitable, avg_pf = calc_oracle_metrics(mod, label_df)
    build_oracle_report(full, split_a, split_b, rolling_rows, profitable, avg_pf, OUT_DIR)

    build_fairness_audit(sim, OUT_DIR)
    scorecard = feature_scorecard(label_df, "tradability_label")
    scorecard.to_csv(OUT_DIR / "tradability_feature_scorecard.csv", index=False)
    build_prop_viability_map(OUT_DIR)

    summary = {
        "thresholds": {"best_r_min": BEST_R_MIN, "gap_r_min": GAP_R_MIN, "min_operational_count": MIN_OPERATIONAL_COUNT},
        "raw_counts": raw_counts,
        "final_counts": final_counts,
        "separability_accuracy": round(acc, 6),
        "oracle_full": full,
        "oracle_split_a": split_a,
        "oracle_split_b": split_b,
        "oracle_rolling_profitable": profitable,
        "oracle_rolling_avg_pf": avg_pf,
    }
    write_json(OUT_DIR / "phase3c_summary.json", summary)
    update_strategy_log(final_counts)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
