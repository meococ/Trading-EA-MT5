#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import importlib.util
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(r"02. AlphaFactory/runs/XAU_Scalp_Portfolio")
OUT_DIR = ROOT / "phase3d_actionability_20260308"
PHASE3B_SCRIPT = Path(r"02. AlphaFactory/analysis/phase3b_router_simulation.py")

PRIMARY_FEATURES = ["or_mid_status_30", "vwap_dist_30_norm", "impulse30_norm", "london_pos_at_open"]
SECONDARY_FEATURE = "or10_width_norm"
SCORECARD_FEATURES = PRIMARY_FEATURES + [SECONDARY_FEATURE]
BEST_R_MIN = 0.15
GAP_R_MIN = 0.20

LABEL_CONT = "CONTINUATION_OK"
LABEL_REV = "REVERSAL_OK"
LABEL_ABS = "ABSTAIN"


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


def action_label_for_row(r):
    cont = float(r["ACCEPTANCE_realized_r"])
    rev = float(r["FAILURE_FADE_realized_r"])
    ranked = sorted([(LABEL_CONT, cont), (LABEL_REV, rev), (LABEL_ABS, 0.0)], key=lambda kv: kv[1], reverse=True)
    best_action, best_r = ranked[0]
    second_action, second_r = ranked[1]
    gap_r = best_r - second_r
    label = LABEL_ABS if (best_action == LABEL_ABS or best_r <= BEST_R_MIN or gap_r <= GAP_R_MIN) else best_action
    return {
        "continuation_r": cont,
        "reversal_r": rev,
        "abstain_r": 0.0,
        "best_action": best_action,
        "second_best_action": second_action,
        "best_r": round(best_r, 5),
        "second_best_r": round(second_r, 5),
        "winner_gap_r": round(gap_r, 5),
        "actionability_label": label,
    }


def build_base_frame(mod):
    features = mod.load_features()
    m1, m5, point = mod.load_mt5_rates()
    day_ctx = mod.build_daily_market_context(features, m1, m5, point)
    df = features.merge(day_ctx, on="ny_date", how="inner").sort_values("ny_date").reset_index(drop=True)
    sim = mod.simulate_day_playbooks(df, m5, point)
    label_df = pd.DataFrame([action_label_for_row(r) for _, r in sim.iterrows()])
    frame = pd.concat([sim.reset_index(drop=True), label_df], axis=1)
    return mod, frame, m5, point


def fit_scorecard(train: pd.DataFrame):
    model = Pipeline([
        ("imp", SimpleImputer(strategy="median")),
        ("sc", StandardScaler()),
        ("lr", LogisticRegression(max_iter=2000, class_weight="balanced")),
    ])
    model.fit(train[SCORECARD_FEATURES], train["actionability_label"])
    return model


def apply_scorecard(model, frame: pd.DataFrame):
    probs = model.predict_proba(frame[SCORECARD_FEATURES])
    classes = list(model.named_steps["lr"].classes_)
    preds, confs, margins = [], [], []
    for pr in probs:
        pmap = dict(zip(classes, pr))
        for lbl in [LABEL_ABS, LABEL_CONT, LABEL_REV]:
            pmap.setdefault(lbl, 0.0)
        ranked = sorted(pmap.items(), key=lambda kv: kv[1], reverse=True)
        preds.append(ranked[0][0])
        confs.append(float(ranked[0][1]))
        margins.append(float(ranked[0][1] - ranked[1][1]))
    out = frame.copy()
    out["score_pred"] = preds
    out["score_conf"] = confs
    out["score_margin"] = margins
    return out


def apply_simple_abstain_first(frame: pd.DataFrame):
    train = frame[frame["split"] == "A"].copy()
    imp_thr = float(train["impulse30_norm"].abs().median())
    vwap_thr = float(train["vwap_dist_30_norm"].median())
    mid_thr = float(train["or_mid_status_30"].abs().median())
    out = frame.copy()
    out["simple_abstain_pred"] = np.where(
        (out["impulse30_norm"].abs() < imp_thr)
        & (out["vwap_dist_30_norm"] < vwap_thr)
        & (out["or_mid_status_30"].abs() < mid_thr),
        LABEL_ABS,
        np.where(out["impulse30_norm"] >= 0, LABEL_CONT, LABEL_REV),
    )
    return out, {"impulse_abs_median": imp_thr, "vwap_dist_median": vwap_thr, "or_mid_abs_median": mid_thr}


def build_prior_tradability_router(mod, frame: pd.DataFrame):
    rows = []
    for _, r in frame.iterrows():
        vals = [
            ("CONT", float(r["ACCEPTANCE_realized_r"])),
            ("REV", float(r["FAILURE_FADE_realized_r"])),
            ("REC", float(r["POST_OPEN_RECLAIM_realized_r"])),
            ("FLAT", 0.0),
        ]
        ranked = sorted(vals, key=lambda kv: kv[1], reverse=True)
        best, bv = ranked[0]
        second, sv = ranked[1]
        label = "FLAT" if (best == "FLAT" or bv <= BEST_R_MIN or (bv - sv) <= GAP_R_MIN) else best
        rows.append(label)
    prior = frame.copy()
    prior["prior_label"] = rows
    if int((prior["prior_label"] == "REC").sum()) < 30:
        prior.loc[prior["prior_label"] == "REC", "prior_label"] = "FLAT"
    model = Pipeline([
        ("imp", SimpleImputer(strategy="median")),
        ("sc", StandardScaler()),
        ("lr", LogisticRegression(max_iter=2000, class_weight="balanced")),
    ])
    train = prior[prior["split"] == "A"]
    model.fit(train[SCORECARD_FEATURES], train["prior_label"])
    prior["prior_pred"] = model.predict(prior[SCORECARD_FEATURES])
    return prior


def build_phase3b_router(mod, frame: pd.DataFrame, m5, point):
    base_features = frame[[c for c in frame.columns if c in mod.load_features().columns]].copy()
    pred = mod.fit_predict_walk_forward(base_features)
    sim0 = mod.simulate_day_playbooks(pred, m5, point)
    return mod.build_router_frame(sim0)


def strategy_metrics(mod, frame: pd.DataFrame, pred_col: str):
    s = frame.copy()
    s["strategy_executed"] = s[pred_col] != LABEL_ABS
    s["strategy_r"] = s.apply(
        lambda r: 0.0 if r[pred_col] == LABEL_ABS else float(r["continuation_r"]) if r[pred_col] == LABEL_CONT else float(r["reversal_r"]),
        axis=1,
    )
    s["strategy_hold"] = 15.0
    full = mod.calc_strategy_metrics(s)
    split_a = mod.calc_strategy_metrics(mod.window_slice(s, mod.FULL_START, mod.SPLIT_A_END))
    split_b = mod.calc_strategy_metrics(mod.window_slice(s, mod.SPLIT_B_START, mod.FULL_END))
    rolling_rows, profitable, avg_pf = mod.rolling_summary(s)
    return s, full, split_a, split_b, rolling_rows, profitable, avg_pf


def baseline_metrics(mod, frame: pd.DataFrame, name: str):
    s = frame.copy()
    if name == "ALWAYS_CONTINUATION":
        s["strategy_executed"] = True
        s["strategy_r"] = s["continuation_r"]
    elif name == "ALWAYS_REVERSAL":
        s["strategy_executed"] = True
        s["strategy_r"] = s["reversal_r"]
    else:
        raise ValueError(name)
    s["strategy_hold"] = 15.0
    full = mod.calc_strategy_metrics(s)
    split_a = mod.calc_strategy_metrics(mod.window_slice(s, mod.FULL_START, mod.SPLIT_A_END))
    split_b = mod.calc_strategy_metrics(mod.window_slice(s, mod.SPLIT_B_START, mod.FULL_END))
    rolling_rows, profitable, avg_pf = mod.rolling_summary(s)
    return s, full, split_a, split_b, rolling_rows, profitable, avg_pf


def build_conditional_expectancy_audit(mod, frame: pd.DataFrame, out_dir: Path):
    rows = []
    lines = ["# Conditional expectancy audit", ""]
    for lbl in [LABEL_CONT, LABEL_REV]:
        sub = frame[frame["score_pred"] == lbl].copy()
        s, full, split_a, split_b, rolling_rows, profitable, avg_pf = strategy_metrics(mod, sub.assign(score_pred=lbl), "score_pred")
        rows.append({
            "predicted_action": lbl,
            "trades": full["trades"],
            "full_pf": full["pf"],
            "full_dd": full["dd"],
            "splitA_pf": split_a["pf"],
            "splitB_pf": split_b["pf"],
            "rolling_profitable": f"{profitable}/{len(mod.ROLL_WINDOWS)}" if hasattr(mod, 'ROLL_WINDOWS') else f"{profitable}/6",
            "rolling_avg_pf": avg_pf,
        })
    exec_df = frame[frame["score_pred"] != LABEL_ABS].copy()
    wrong = exec_df[exec_df["score_pred"] != exec_df["actionability_label"]].copy()
    abst = frame[frame["score_pred"] == LABEL_ABS].copy()
    lines.extend([
        pd.DataFrame(rows).to_markdown(index=False),
        "",
        "## Wrong-action cost",
        f"- Executed wrong-action days: **{len(wrong)}**",
        f"- Total wrong-action cost (oracle best minus chosen): **{wrong['wrong_cost_r'].sum():.4f}R**",
        f"- Average wrong-action cost: **{wrong['wrong_cost_r'].mean() if len(wrong) else 0.0:.4f}R/day**",
        "",
        "## ABSTAIN value inside primary scorecard",
        f"- Predicted ABSTAIN days: **{len(abst)}**",
        f"- Good opportunities blocked (`oracle label != ABSTAIN`): **{int((abst['actionability_label'] != LABEL_ABS).sum())}**",
        f"- Sum of blocked best-action R: **{abst['best_r'].sum():.4f}R**",
        f"- True abstain days kept flat: **{int((abst['actionability_label'] == LABEL_ABS).sum())}**",
        "",
        "## Material tradability verdict",
        "- A predicted action subset is materially tradeable only if its full and split B expectancy are both positive with non-trivial sample.",
    ])
    write_text(out_dir / "conditional_expectancy_audit.md", "\n".join(lines))


def build_abstention_quality_report(mod, frame: pd.DataFrame, out_dir: Path):
    rows = []
    base = frame.copy()
    variants = [
        ("ARGMAX", base["score_pred"]),
        ("CONF_GATED_045_005", base.apply(lambda r: LABEL_ABS if (r["score_conf"] < 0.45 or r["score_margin"] < 0.05) else r["score_pred"], axis=1)),
        ("CONF_GATED_055_005", base.apply(lambda r: LABEL_ABS if (r["score_conf"] < 0.55 or r["score_margin"] < 0.05) else r["score_pred"], axis=1)),
    ]
    for name, pred in variants:
        s = base.copy()
        s["variant_pred"] = pred
        strat, full, split_a, split_b, rolling_rows, profitable, avg_pf = strategy_metrics(mod, s, "variant_pred")
        extra = s[(s["score_pred"] != LABEL_ABS) & (s["variant_pred"] == LABEL_ABS)].copy()
        rows.append({
            "variant": name,
            "trades": full["trades"],
            "pf": full["pf"],
            "dd": full["dd"],
            "splitB_pf": split_b["pf"],
            "splitB_dd": split_b["dd"],
            "abstain_days": int((s["variant_pred"] == LABEL_ABS).sum()),
            "additional_abstains_vs_argmax": int(len(extra)),
            "toxic_actions_avoided": int((extra["chosen_action_r"] < 0).sum()),
            "good_opportunities_blocked": int((extra["chosen_action_r"] > 0).sum()),
        })
    lines = [
        "# Abstention quality report",
        "",
        "These rows test whether confidence gating improves action quality or merely suppresses activity.",
        "",
        pd.DataFrame(rows).to_markdown(index=False),
        "",
        "## Interpretation rule",
        "- A useful confidence gate should improve split B quality without collapsing trade count.",
        "- If it mostly increases abstains while blocking similar numbers of good and bad actions, it is not a meaningful permission layer.",
    ]
    write_text(out_dir / "abstention_quality_report.md", "\n".join(lines))


def build_scorecard_md(model, simple_thresholds: dict, out_dir: Path):
    lr = model.named_steps["lr"]
    rows = []
    for cls, intercept, coef in zip(lr.classes_, lr.intercept_, lr.coef_):
        rows.append({
            "action": cls,
            "intercept": round(float(intercept), 4),
            **{feat: round(float(v), 4) for feat, v in zip(SCORECARD_FEATURES, coef)},
        })
    lines = [
        "# Actionability scorecard",
        "",
        "## Minimal interpretable feature set",
        f"- Primary: `{PRIMARY_FEATURES}`",
        f"- Secondary: `{SECONDARY_FEATURE}`",
        "- No feature explosion and no threshold chase.",
        "- Scorecard is a split-A-fitted linear multinomial logistic model used only as an interpretable additive score.",
        "",
        "## Standardized coefficient table",
        "",
        pd.DataFrame(rows).to_markdown(index=False),
        "",
        "## Simple abstention-first baseline",
        f"- `|impulse30_norm| < {simple_thresholds['impulse_abs_median']:.4f}`",
        f"- `vwap_dist_30_norm < {simple_thresholds['vwap_dist_median']:.4f}`",
        f"- `|or_mid_status_30| < {simple_thresholds['or_mid_abs_median']:.4f}`",
        "- If all three hold => `ABSTAIN`, else choose continuation if `impulse30_norm >= 0`, otherwise reversal.",
    ]
    write_text(out_dir / "actionability_scorecard.md", "\n".join(lines))


def build_split_rolling_report(result_rows: list, subset_rows: list, out_dir: Path):
    lines = [
        "# Split / rolling actionability report",
        "",
        "## Strategy-level comparison",
        "",
        pd.DataFrame(result_rows).to_markdown(index=False),
        "",
        "## Predicted action subset stability",
        "",
        pd.DataFrame(subset_rows).to_markdown(index=False),
    ]
    write_text(out_dir / "split_rolling_actionability_report.md", "\n".join(lines))


def build_prop_gap(out_dir: Path):
    lines = [
        "# Prop actionability gap",
        "",
        "- Historical news/calendar coverage is still incomplete, so early-open actionability cannot be mapped reliably to FTMO/The5ers restricted-news windows.",
        "- No firm-rule clock reconciliation has been validated in this phase.",
        "- No MT5 tester realism campaign (real ticks + delay + cost stress) was run for the scorecard itself in Phase 3D.",
        "- No server-activity / order-modification audit was done for a future live actionability router implementation.",
        "- Therefore market-actionability and prop-actionability remain separate; this phase only answers whether a permission model might exist.",
    ]
    write_text(out_dir / "prop_actionability_gap.md", "\n".join(lines))


def build_trade_stories(frame: pd.DataFrame, out_dir: Path):
    trade_rows, blocked_rows = [], []
    for _, r in frame.iterrows():
        common = {
            "ny_date": str(r["ny_date"]),
            "predicted_action": r["score_pred"],
            "oracle_action_label": r["actionability_label"],
            "best_action": r["best_action"],
            "second_best_action": r["second_best_action"],
            "winner_gap_r": round(float(r["winner_gap_r"]), 4),
            "score_conf": round(float(r["score_conf"]), 4),
            "score_margin": round(float(r["score_margin"]), 4),
            "features": {f: (round(float(r[f]), 4) if pd.notna(r[f]) else None) for f in SCORECARD_FEATURES},
            "counterfactual": {
                LABEL_CONT: round(float(r["continuation_r"]), 4),
                LABEL_REV: round(float(r["reversal_r"]), 4),
                LABEL_ABS: 0.0,
            },
        }
        if r["score_pred"] == LABEL_ABS:
            blocked_rows.append({
                **common,
                "blocked_reason": "scorecard_abstain",
                "blocked_good_opportunity": bool(r["actionability_label"] != LABEL_ABS),
            })
        else:
            chosen_r = float(r["continuation_r"]) if r["score_pred"] == LABEL_CONT else float(r["reversal_r"])
            trade_rows.append({
                **common,
                "chosen_r": round(chosen_r, 4),
                "wrong_action_cost_r": round(float(r["wrong_cost_r"]), 4),
                "entry_time_ny": r["entry_ny_seed"],
                "playbook_direction_note": "Continuation follows first-30m impulse" if r["score_pred"] == LABEL_CONT else "Reversal fades first-30m impulse",
            })
    write_jsonl(out_dir / "trade_story.jsonl", trade_rows)
    write_jsonl(out_dir / "blocked_signal_story.jsonl", blocked_rows)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mod, frame, m5, point = build_base_frame(load_phase3b())

    action_cols = [
        "ny_date", "split", "weekday",
        "continuation_r", "reversal_r", "abstain_r",
        "best_action", "second_best_action", "best_r", "second_best_r", "winner_gap_r", "actionability_label",
    ]
    frame[action_cols].to_csv(OUT_DIR / "actionability_matrix.csv", index=False)

    train = frame[frame["split"] == "A"].copy()
    scorecard = fit_scorecard(train)
    scored = apply_scorecard(scorecard, frame)
    scored["chosen_action_r"] = scored.apply(
        lambda r: 0.0 if r["score_pred"] == LABEL_ABS else float(r["continuation_r"]) if r["score_pred"] == LABEL_CONT else float(r["reversal_r"]),
        axis=1,
    )
    scored["wrong_cost_r"] = scored["best_r"] - scored["chosen_action_r"]

    scored, simple_thresholds = apply_simple_abstain_first(scored)
    prior = build_prior_tradability_router(mod, scored)

    # Primary strategy
    primary_s, primary_full, primary_split_a, primary_split_b, primary_rolls, primary_prof, primary_avg_pf = strategy_metrics(mod, scored, "score_pred")
    cont_sub = scored[scored["score_pred"] == LABEL_CONT].copy()
    rev_sub = scored[scored["score_pred"] == LABEL_REV].copy()
    cont_s, cont_full, cont_sa, cont_sb, cont_rolls, cont_prof, cont_avg_pf = strategy_metrics(mod, cont_sub.assign(score_pred=LABEL_CONT), "score_pred")
    rev_s, rev_full, rev_sa, rev_sb, rev_rolls, rev_prof, rev_avg_pf = strategy_metrics(mod, rev_sub.assign(score_pred=LABEL_REV), "score_pred")

    # Baselines
    _, ac_full, ac_sa, ac_sb, ac_rolls, ac_prof, ac_avg_pf = baseline_metrics(mod, scored, "ALWAYS_CONTINUATION")
    _, ar_full, ar_sa, ar_sb, ar_rolls, ar_prof, ar_avg_pf = baseline_metrics(mod, scored, "ALWAYS_REVERSAL")
    simple_s, simple_full, simple_sa, simple_sb, simple_rolls, simple_prof, simple_avg_pf = strategy_metrics(mod, scored.rename(columns={"simple_abstain_pred": "simple_pred"}), "simple_pred")
    prior_s = prior.copy()
    prior_s["prior_action_pred"] = prior_s["prior_pred"].map({"CONT": LABEL_CONT, "REV": LABEL_REV, "FLAT": LABEL_ABS, "REC": LABEL_ABS})
    prior_strat, prior_full, prior_sa, prior_sb, prior_rolls, prior_prof, prior_avg_pf = strategy_metrics(mod, prior_s, "prior_action_pred")

    result_rows = [
        {"strategy": "ACTIONABILITY_SCORECARD", "trades": primary_full["trades"], "pf": primary_full["pf"], "dd": primary_full["dd"], "splitA_pf": primary_split_a["pf"], "splitB_pf": primary_split_b["pf"], "rolling_profitable": f"{primary_prof}/6", "rolling_avg_pf": primary_avg_pf},
        {"strategy": "ALWAYS_CONTINUATION", "trades": ac_full["trades"], "pf": ac_full["pf"], "dd": ac_full["dd"], "splitA_pf": ac_sa["pf"], "splitB_pf": ac_sb["pf"], "rolling_profitable": f"{ac_prof}/6", "rolling_avg_pf": ac_avg_pf},
        {"strategy": "ALWAYS_REVERSAL", "trades": ar_full["trades"], "pf": ar_full["pf"], "dd": ar_full["dd"], "splitA_pf": ar_sa["pf"], "splitB_pf": ar_sb["pf"], "rolling_profitable": f"{ar_prof}/6", "rolling_avg_pf": ar_avg_pf},
        {"strategy": "SIMPLE_ABSTAIN_FIRST", "trades": simple_full["trades"], "pf": simple_full["pf"], "dd": simple_full["dd"], "splitA_pf": simple_sa["pf"], "splitB_pf": simple_sb["pf"], "rolling_profitable": f"{simple_prof}/6", "rolling_avg_pf": simple_avg_pf},
        {"strategy": "PRIOR_3CLASS_TRADABILITY_ROUTER", "trades": prior_full["trades"], "pf": prior_full["pf"], "dd": prior_full["dd"], "splitA_pf": prior_sa["pf"], "splitB_pf": prior_sb["pf"], "rolling_profitable": f"{prior_prof}/6", "rolling_avg_pf": prior_avg_pf},
    ]
    pd.DataFrame(result_rows).to_csv(OUT_DIR / "router_vs_actionability_baselines.csv", index=False)

    subset_rows = [
        {"subset": LABEL_CONT, "trades": cont_full["trades"], "full_pf": cont_full["pf"], "full_dd": cont_full["dd"], "splitA_pf": cont_sa["pf"], "splitB_pf": cont_sb["pf"], "rolling_profitable": f"{cont_prof}/6", "rolling_avg_pf": cont_avg_pf},
        {"subset": LABEL_REV, "trades": rev_full["trades"], "full_pf": rev_full["pf"], "full_dd": rev_full["dd"], "splitA_pf": rev_sa["pf"], "splitB_pf": rev_sb["pf"], "rolling_profitable": f"{rev_prof}/6", "rolling_avg_pf": rev_avg_pf},
    ]

    build_conditional_expectancy_audit(mod, scored, OUT_DIR)
    build_abstention_quality_report(mod, scored, OUT_DIR)
    build_scorecard_md(scorecard, simple_thresholds, OUT_DIR)
    build_split_rolling_report(result_rows, subset_rows, OUT_DIR)
    build_prop_gap(OUT_DIR)
    build_trade_stories(scored, OUT_DIR)

    summary = {
        "label_counts": scored["actionability_label"].value_counts().to_dict(),
        "predicted_counts": scored["score_pred"].value_counts().to_dict(),
        "primary_metrics": result_rows[0],
        "subset_metrics": subset_rows,
    }
    write_json(OUT_DIR / "phase3d_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
