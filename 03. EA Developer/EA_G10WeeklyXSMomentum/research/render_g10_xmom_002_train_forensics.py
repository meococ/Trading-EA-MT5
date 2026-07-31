"""Render hash-bound train-only forensics for terminal HYP-G10-XMOM-W1-002.

This script is diagnostic-only. It reads the frozen train evaluation artifacts
and train parquet, never the sealed holdout, and cannot authorize another run.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[3]
RESEARCH = Path(__file__).resolve().parent
EVIDENCE = RESEARCH / "evidence" / "HYP-G10-XMOM-W1-002" / "G10XMOM002-TRAIN-EVAL-001"
OUT = EVIDENCE / "forensics"
LEGS = EVIDENCE / "train_eval_legs.json"
WEEKS = EVIDENCE / "train_eval_weeks.json"
TERMINAL = EVIDENCE / "train_eval_terminal.json"
PARQUET = ROOT / "02. AlphaFactory" / "data" / "fivepercent" / "G10WeeklyXSMomentum" / "HYP-G10-XMOM-W1-002" / "train_w1_bars.parquet"
SAMPLING_PLAN = RESEARCH / "HYP-G10-XMOM-W1-002_TRAIN_FORENSIC_SAMPLING_PLAN.md"
GROK_RECEIPT = OUT / "grok_visual_review_receipt.json"
GROK_RECEIPT_SHA256 = "D02B296C3E69627EC065CE108B31B9145152F8172C018A12B365D898F0599975"

EXPECTED = {
    LEGS: "CF105E71DB2500703D025E0FF60C9367ACB686006A606336CC5CFCFA9937FAEF",
    WEEKS: "6E282704964D6BD323C63B9EAE7CFCC63D0AC4BD4AAECCBCCF4DE5BD07581771",
    TERMINAL: "F115DFB58BE43990FC5CF6C726947093A8F4CE58B86C30CCE529325ACD213FB0",
    PARQUET: "2FB4615129D8B8782F6A71AF8009B47C9210B2040FC57FD2082D0978755B4BB2",
    SAMPLING_PLAN: "A5014B6EDA61EA326CE9CD9E2CC371D362873B12221558EA6EEB318F42B3A14D",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8") + b"\n"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def profit_factor(values: Iterable[float]) -> float | None:
    values = list(values)
    gains = sum(value for value in values if value > 0.0)
    losses = -sum(value for value in values if value < 0.0)
    if losses == 0.0:
        return None if gains == 0.0 else math.inf
    return gains / losses


def arm_stats(rows: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    selected = [row for row in rows if row["arm"] == arm]
    net = [float(row["net_return_x1"]) for row in selected]
    gross = [float(row["gross_return"]) for row in selected]
    costs = [gross_value - net_value for gross_value, net_value in zip(gross, net)]
    wins = [value for value in net if value > 0.0]
    losses = [value for value in net if value < 0.0]
    avg_win = mean(wins) if wins else None
    avg_loss = mean(losses) if losses else None
    breakeven = None
    if avg_win is not None and avg_loss is not None:
        breakeven = abs(avg_loss) / (avg_win + abs(avg_loss))
    sorted_net = sorted(net)
    count_5 = max(1, math.ceil(len(sorted_net) * 0.05))
    total_loss = -sum(value for value in net if value < 0.0)
    return {
        "legs": len(selected),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": len(wins) / len(selected),
        "net_sum": sum(net),
        "expectancy": mean(net),
        "profit_factor_net_x1": profit_factor(net),
        "profit_factor_gross": profit_factor(gross),
        "gross_sum": sum(gross),
        "mean_cost_return": mean(costs),
        "total_cost_return": sum(costs),
        "average_win": avg_win,
        "average_loss": avg_loss,
        "realized_payoff_ratio": None if avg_win is None or avg_loss is None else avg_win / abs(avg_loss),
        "breakeven_win_rate": breakeven,
        "bottom_5pct_loss_share": None
        if total_loss == 0.0
        else -sum(sorted_net[:count_5]) / total_loss,
        "top_5pct_net_sum": sum(sorted_net[-count_5:]),
        "median_net": median(net),
    }


def group_stats(rows: list[dict[str, Any]], key_fn) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        grouped[str(key_fn(row))].append(float(row["net_return_x1"]))
    return {
        key: {
            "count": len(values),
            "net_sum": sum(values),
            "expectancy": mean(values),
            "win_rate": sum(value > 0.0 for value in values) / len(values),
            "profit_factor": profit_factor(values),
        }
        for key, values in sorted(grouped.items())
    }


def formation_quintile_stats(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    ordered = sorted(rows, key=lambda row: (float(row["formation_return"]), row["week_date"], row["symbol"], row["side"]))
    result: dict[str, dict[str, Any]] = {}
    for idx in range(5):
        start = len(ordered) * idx // 5
        end = len(ordered) * (idx + 1) // 5
        bucket = ordered[start:end]
        values = [float(row["net_return_x1"]) for row in bucket]
        result[f"Q{idx + 1}"] = {
            "count": len(values),
            "formation_min": min(float(row["formation_return"]) for row in bucket),
            "formation_max": max(float(row["formation_return"]) for row in bucket),
            "net_sum": sum(values),
            "expectancy": mean(values),
            "win_rate": sum(value > 0.0 for value in values) / len(values),
            "profit_factor": profit_factor(values),
        }
    return result


def select_cases(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    challenger = [row for row in rows if row["arm"] == "challenger"]
    ordered = sorted(
        challenger,
        key=lambda row: (float(row["net_return_x1"]), row["week_date"], row["symbol"], row["side"]),
    )
    positives = [row for row in ordered if float(row["net_return_x1"]) > 0.0]
    negatives = [row for row in ordered if float(row["net_return_x1"]) < 0.0]
    picked: list[tuple[str, dict[str, Any]]] = [
        ("largest_loss", ordered[0]),
        ("median_loss", negatives[(len(negatives) - 1) // 2]),
        ("median_win", positives[(len(positives) - 1) // 2]),
        ("largest_win", ordered[-1]),
    ]
    pairs: list[tuple[tuple[Any, ...], dict[str, Any], dict[str, Any]]] = []
    for winner in positives:
        winner_date = date.fromisoformat(winner["week_date"])
        for loser in negatives:
            if winner["symbol"] != loser["symbol"] or winner["side"] != loser["side"]:
                continue
            loser_date = date.fromisoformat(loser["week_date"])
            key = (
                abs((winner_date - loser_date).days),
                winner["symbol"],
                winner["side"],
                winner["week_date"],
                loser["week_date"],
            )
            pairs.append((key, winner, loser))
    if pairs:
        _, winner, loser = min(pairs, key=lambda item: item[0])
        picked.extend([("matched_win", winner), ("matched_loss", loser)])

    cases: list[dict[str, Any]] = []
    for index, (stratum, row) in enumerate(picked, start=1):
        copied = dict(row)
        copied["case_id"] = f"G10XMOM002-C{index:02d}"
        copied["stratum"] = stratum
        copied["position_id"] = f"CH-{row['week_date']}-{row['symbol']}-{row['side']}"
        cases.append(copied)
    return cases


def candle(ax, x: float, bar: dict[str, Any], color: str) -> None:
    ax.vlines(x, bar["low"], bar["high"], color=color, linewidth=1.5)
    body_low = min(bar["open"], bar["close"])
    height = max(abs(bar["close"] - bar["open"]), abs(bar["open"]) * 1e-6)
    ax.add_patch(plt.Rectangle((x - 0.25, body_low), 0.5, height, facecolor=color, edgecolor=color, alpha=0.75))


def render_case_charts(cases: list[dict[str, Any]], bar_map: dict[tuple[str, int], dict[str, Any]]) -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = []
    cases_dir = OUT / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    for case in cases:
        prior = bar_map[(case["symbol"], int(case["prior_epoch"]))]
        outcome = bar_map[(case["symbol"], int(case["week_epoch"]))]
        decision_path = cases_dir / f"{case['case_id']}_decision.png"
        outcome_path = cases_dir / f"{case['case_id']}_outcome.png"

        fig, ax = plt.subplots(figsize=(6.4, 4.0), constrained_layout=True)
        candle(ax, 0.0, prior, "#2878B5" if prior["close"] >= prior["open"] else "#D9534F")
        ax.set_xticks([0.0], [f"prior W1\n{prior['time_server'][:10]}"])
        ax.set_title(f"{case['case_id']} decision | {case['symbol']} {case['side']} rank {case['rank']}")
        ax.set_ylabel("price")
        ax.grid(alpha=0.2)
        fig.savefig(decision_path, dpi=150)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(7.2, 4.2), constrained_layout=True)
        for x, bar in enumerate((prior, outcome)):
            candle(ax, float(x), bar, "#2878B5" if bar["close"] >= bar["open"] else "#D9534F")
        ax.scatter([1.0], [case["entry"]], marker=">", s=80, color="#F0AD4E", label="entry W1 open")
        ax.scatter([1.0], [case["exit"]], marker="x", s=80, color="#5CB85C", label="exit W1 close")
        ax.set_xticks([0.0, 1.0], [f"formation\n{prior['time_server'][:10]}", f"outcome\n{outcome['time_server'][:10]}"])
        ax.set_title(f"{case['case_id']} outcome | net x1={case['net_return_x1']:.4%}")
        ax.set_ylabel("price")
        ax.grid(alpha=0.2)
        ax.legend(loc="best", fontsize=8)
        fig.savefig(outcome_path, dpi=150)
        plt.close(fig)

        manifest.append(
            {
                "case_id": case["case_id"],
                "stratum": case["stratum"],
                "position_id": case["position_id"],
                "direction": f"{case['side']} / pair_direction={case['pair_direction']}",
                "entry": case["entry"],
                "exit": case["exit"],
                "net_R": None,
                "net_return_x1": case["net_return_x1"],
                "context_reason": f"predeclared {case['stratum']}; formation={case['formation_return']:.6f}; rank={case['rank']}",
                "decision_chart": decision_path.relative_to(ROOT).as_posix(),
                "decision_chart_sha256": sha256_file(decision_path),
                "outcome_chart": outcome_path.relative_to(ROOT).as_posix(),
                "outcome_chart_sha256": sha256_file(outcome_path),
            }
        )
    return manifest


def render_case_montage(case_manifest: list[dict[str, Any]]) -> tuple[str, str]:
    montage_path = OUT / "selected_cases_outcome_montage.png"
    fig, axes = plt.subplots(2, 3, figsize=(15, 8.5), constrained_layout=True)
    for ax, case in zip(axes.flat, case_manifest):
        image = plt.imread(ROOT / case["outcome_chart"])
        ax.imshow(image)
        ax.set_title(f"{case['case_id']} | {case['stratum']}", fontsize=9)
        ax.axis("off")
    fig.suptitle("Predeclared HYP-G10-XMOM-W1-002 train cases", fontsize=14)
    fig.savefig(montage_path, dpi=130)
    plt.close(fig)
    return montage_path.name, sha256_file(montage_path)


def render_population_charts(weeks: list[dict[str, Any]], challenger_rows: list[dict[str, Any]], grouped: dict[str, Any]) -> dict[str, str]:
    weeks = sorted(weeks, key=lambda row: row["week_date"])
    dates = [date.fromisoformat(row["week_date"]) for row in weeks]
    challenger_equity = []
    control_equity = []
    ch_value = ctl_value = 1.0
    for row in weeks:
        ch_value *= 1.0 + float(row["challenger_return_x1"])
        ctl_value *= 1.0 + float(row["control_return_x1"])
        challenger_equity.append(ch_value)
        control_equity.append(ctl_value)
    equity_path = OUT / "equity_curve_challenger_vs_control.png"
    fig, ax = plt.subplots(figsize=(11, 4.8), constrained_layout=True)
    ax.plot(dates, challenger_equity, label="challenger", color="#C43C39", linewidth=1.8)
    ax.plot(dates, control_equity, label="reverse control", color="#2F7ED8", linewidth=1.5)
    ax.axhline(1.0, color="black", linewidth=0.8, alpha=0.5)
    ax.set_title("HYP-G10-XMOM-W1-002 train equity proxy (x1 costs)")
    ax.set_ylabel("compounded equity, 1.0 start")
    ax.grid(alpha=0.2)
    ax.legend()
    fig.savefig(equity_path, dpi=160)
    plt.close(fig)

    month_values: dict[str, float] = defaultdict(float)
    for row in challenger_rows:
        month_values[row["week_date"][:7]] += float(row["net_return_x1"])
    monthly_path = OUT / "challenger_monthly_leg_net_x1.png"
    fig, ax = plt.subplots(figsize=(12, 4.8), constrained_layout=True)
    months = sorted(month_values)
    values = [month_values[key] for key in months]
    ax.bar(months, values, color=["#4C9F70" if value >= 0 else "#C43C39" for value in values])
    ax.axhline(0.0, color="black", linewidth=0.8)
    ax.set_title("Challenger monthly sum of leg net returns (x1 costs)")
    ax.set_ylabel("sum leg net return")
    ax.tick_params(axis="x", rotation=90, labelsize=7)
    ax.grid(axis="y", alpha=0.2)
    fig.savefig(monthly_path, dpi=160)
    plt.close(fig)

    decomposition_path = OUT / "challenger_symbol_side_decomposition.png"
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), constrained_layout=True)
    symbol_stats = grouped["symbol"]
    symbols = list(symbol_stats)
    symbol_net = [symbol_stats[symbol]["net_sum"] for symbol in symbols]
    axes[0].bar(symbols, symbol_net, color=["#4C9F70" if value >= 0 else "#C43C39" for value in symbol_net])
    axes[0].axhline(0.0, color="black", linewidth=0.8)
    axes[0].tick_params(axis="x", rotation=45)
    axes[0].set_title("Net by symbol")
    side_stats = grouped["side"]
    sides = list(side_stats)
    side_net = [side_stats[side]["net_sum"] for side in sides]
    axes[1].bar(sides, side_net, color=["#4C9F70" if value >= 0 else "#C43C39" for value in side_net])
    axes[1].axhline(0.0, color="black", linewidth=0.8)
    axes[1].set_title("Net by currency-side selection")
    for ax in axes:
        ax.set_ylabel("sum leg net return x1")
        ax.grid(axis="y", alpha=0.2)
    fig.savefig(decomposition_path, dpi=160)
    plt.close(fig)

    return {
        path.name: sha256_file(path)
        for path in (equity_path, monthly_path, decomposition_path)
    }


def render_readout(summary: dict[str, Any], case_manifest: list[dict[str, Any]]) -> str:
    ch = summary["arms"]["challenger"]
    ctl = summary["arms"]["control"]
    terminal = summary["terminal"]
    lines = [
        "# HYP-G10-XMOM-W1-002 train forensics",
        "",
        "## 1. Executive verdict",
        "",
        "- **Run identity [OBSERVED]:** `G10XMOM002-TRAIN-EVAL-001`, challenger = prior completed W1 cross-sectional spot momentum; control = the same four selected legs with all directions flipped.",
        "- **Validity [OBSERVED]:** engineering-valid and sample-valid for the frozen 2018-2021 W1 research proxy. Holdout remained sealed.",
        "- **Economic verdict [OBSERVED]:** killed. Challenger PF x1 `%.3f`, net `%.4f`, expectancy `%.6f`; reverse control PF `%.3f`, net `%.4f`." % (terminal["arms"]["challenger"]["profit_factor_x1"], ch["net_sum"], ch["expectancy"], terminal["arms"]["control"]["profit_factor_x1"], ctl["net_sum"]),
        "- **Failure 1 — signal sign/decay [HIGH, INFERENCE]:** both long and short selections lost, six of seven symbols lost, and the challenger underperformed its matched reverse-direction control. The exact one-week ranking has no positive train expectancy under this execution identity.",
        "- **Failure 2 — cost-amplified negative edge [HIGH, OBSERVED]:** gross PF `%.3f` fell to net PF `%.3f`; mean cost drag was `%.6f` per leg. Costs worsen the result but do not alone explain a challenger that also loses relative to control." % (ch["profit_factor_gross"], ch["profit_factor_net_x1"], ch["mean_cost_return"]),
        "- **Failure 3 — broad temporal/tail instability [HIGH, OBSERVED]:** 0/4 positive years, 1/8 positive half-years, and MC P95 DD `%.2f%%` versus the frozen 8%% ceiling." % terminal["arms"]["challenger"]["mc_p95_max_drawdown_pct"],
        "",
        "## 2. Evidence integrity",
        "",
        "- **[OBSERVED]** Input hashes were verified before reading: legs `%s`, weeks `%s`, terminal `%s`, parquet `%s`, sampling plan `%s`." % tuple(value[:12] for value in summary["input_sha256"].values()),
        "- **[OBSERVED]** Terminal, dataset manifest/parquet, prereg, evaluator, tests and independent review are SHA-bound in registry terminal row 344. Evaluator is disarmed after one use.",
        "- **[OBSERVED]** A four-image Grok ACP review passed structured-output validation, cost USD 0.0698892, accessed no holdout, changed no files, and returned `SUPPORTS_KILL`; receipt SHA `%s`." % GROK_RECEIPT_SHA256[:12],
        "- **[LIMIT]** This is an offline W1 research proxy, not an MT5 Strategy Tester report. Cost is a frozen pip proxy; account-currency PnL, real lifecycle fills, spread path, news coverage and execution telemetry are unavailable.",
        "- **[OBSERVED]** Source logic rejects non-train years and holdout access (`evaluate_g10_xmom_002_train.py:267-278`), ranks/selects at `407-437`, constructs legs at `598-780`, and summarizes/gates at `823-1005`.",
        "- **[INFERENCE]** Non-repaint risk is low for this proxy because formation uses only the prior completed W1 bar; no MQL5/tick implementation exists to audit.",
        "",
        "## 3. Population decomposition",
        "",
        "| arm | legs | win rate | PF gross | PF net x1 | net | expectancy | avg win | avg loss | BE win rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        "| challenger | %d | %.2f%% | %.3f | %.3f | %.4f | %.6f | %.6f | %.6f | %.2f%% |" % (ch["legs"], 100 * ch["win_rate"], ch["profit_factor_gross"], ch["profit_factor_net_x1"], ch["net_sum"], ch["expectancy"], ch["average_win"], ch["average_loss"], 100 * ch["breakeven_win_rate"]),
        "| reverse control | %d | %.2f%% | %.3f | %.3f | %.4f | %.6f | %.6f | %.6f | %.2f%% |" % (ctl["legs"], 100 * ctl["win_rate"], ctl["profit_factor_gross"], ctl["profit_factor_net_x1"], ctl["net_sum"], ctl["expectancy"], ctl["average_win"], ctl["average_loss"], 100 * ctl["breakeven_win_rate"]),
        "",
        "- **[OBSERVED]** Cadence is `%.3f` legs per elapsed calendar week; sample is 207 complete weeks / 828 legs per arm." % terminal["arms"]["challenger"]["cadence_legs_per_elapsed_week"],
        "- **[OBSERVED]** Bottom 5%% of challenger legs contribute `%.1f%%` of total gross loss magnitude; this is material tail concentration but does not legalize deleting those outcomes." % (100 * ch["bottom_5pct_loss_share"]),
        "- **[UNKNOWN]** Account-currency PnL, true R, session/hour, holding-time variation, stop width, volatility, news and execution buckets are not present in this W1 proxy.",
        "- **[OBSERVED]** Full year/month/symbol/side/formation-quintile tables are in `population_summary.json`; no bucket is a same-sample filter recommendation.",
        "",
        "## 4. Winner and loser anatomy",
        "",
        "- **[OBSERVED]** Winners and losers are sampled by the frozen plan, including extremes, medians and the nearest same-symbol/same-side contrast.",
        "- **[INFERENCE]** With only one formation bar plus one outcome bar, apparent winner traits cannot be separated reliably from random weekly continuation/reversal. Matching controls symbol, side and calendar distance only; it does not control macro news or intrabar volatility.",
        "- **[OBSERVED]** Winners occur when the selected currency continues in the directed pair over the next W1 bar by more than the cost proxy; this is outcome anatomy, not causal proof.",
        "",
        "## 5. Logic and fidelity choke points",
        "",
        "- **[OBSERVED, HIGH]** `rank_currencies`/`select_basket` (`407-437`) impose the exact top2/bottom2 decision surface; broad losses on both sides connect directly to a weak/decayed one-week continuation premise. Alternative: W1 open/close proxy may misrepresent implementable weekly timing.",
        "- **[OBSERVED, HIGH]** `cost_return` (`374-396`) applies the frozen spread-floor + commission + slippage + rollover proxy. It materially lowers PF. Alternative: real broker costs may differ, but x1 already fails before any promotion claim.",
        "- **[OBSERVED, MEDIUM]** `evaluate_train_bars` (`598-780`) forces Monday-open/Friday-close, all-or-none four-leg baskets. It removes timing flexibility and may blend reversal/continuation subregimes. Testing a mined clock/filter on this sample is prohibited.",
        "- **[DORMANT]** Stops, targets, trailing exits, intraday sessions, news gates, portfolio margin, order filling and MQL5 execution are absent—not merely bypassed—because no EA/Model 0 was built after the probe kill.",
        "",
        "## 6. Case chart manifest",
        "",
        "Sampling was frozen in `HYP-G10-XMOM-W1-002_TRAIN_FORENSIC_SAMPLING_PLAN.md` before individual outcomes were read. Decision charts use only the prior W1 OHLC; outcome charts add the current W1 OHLC and frozen open/close markers. Intrabar path is unavailable.",
        "",
        "| case_id | stratum | position_id | direction | entry | exit | net_R | context_reason | decision_chart | outcome_chart |",
        "|---|---|---|---|---:|---:|---:|---|---|---|",
    ]
    for case in case_manifest:
        lines.append(
            "| {case_id} | {stratum} | {position_id} | {direction} | {entry:.6f} | {exit:.6f} | unknown | {context_reason} | `{decision_chart}` | `{outcome_chart}` |".format(**case)
        )
    lines.extend(
        [
            "",
            "## 7. Conclusions and legal next work",
            "",
            "- **[OBSERVED]** The exact tested rule is negative after cost, fails all PF tiers, fails MC DD, and underperforms its matched reverse control. Its internal holdout must remain sealed.",
            "- **[INFERENCE]** Winning legs are ordinary next-week continuation outcomes large enough to cover cost; the population does not show that the frozen ranking selects them reliably.",
            "- **[LIMIT]** This does not kill other formation horizons, event clocks, futures-based cross-sectional signals, or different mechanisms. It also does not prove a live EA would match the proxy.",
            "- **Fresh idea 1 [HYPOTHESIS]:** cross-sectional *slow* trend with an outcome-blind multi-month formation and fixed rebalancing clock; falsify on a new train contract before holdout.",
            "- **Fresh idea 2 [HYPOTHESIS]:** event-clock currency strength continuation using an independent futures/spot dislocation surface, subject to data/licensing and cost feasibility first.",
            "- **[ADJUDICATION]** Grok's proposed direct reversion and AUD/NZD deletion are rejected: the matched reverse control already lost, while deleting weak symbols is same-sample selection. A different horizon is only conditionally legal under independent research, a fresh ID and a new outcome-blind preregistration.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    for path, expected in EXPECTED.items():
        actual = sha256_file(path)
        if actual != expected:
            raise SystemExit(f"hash_mismatch:{path}:{expected}:{actual}")
    if sha256_file(GROK_RECEIPT) != GROK_RECEIPT_SHA256:
        raise SystemExit("grok_visual_review_receipt_hash_mismatch")
    OUT.mkdir(parents=True, exist_ok=True)
    legs_doc = load_json(LEGS)
    weeks_doc = load_json(WEEKS)
    terminal = load_json(TERMINAL)
    legs = list(legs_doc["legs"])
    weeks = list(weeks_doc["weeks"])
    challenger = [row for row in legs if row["arm"] == "challenger"]
    control = [row for row in legs if row["arm"] == "control"]
    if len(challenger) != 828 or len(control) != 828 or len(weeks) != 207:
        raise SystemExit("population_shape_mismatch")

    bars = pq.read_table(PARQUET).to_pylist()
    bar_map = {(row["symbol"], int(row["time_epoch"])): row for row in bars}
    cases = select_cases(legs)
    case_manifest = render_case_charts(cases, bar_map)
    montage_name, montage_sha = render_case_montage(case_manifest)
    groups = {
        "year": group_stats(challenger, lambda row: row["week_date"][:4]),
        "month": group_stats(challenger, lambda row: row["week_date"][:7]),
        "symbol": group_stats(challenger, lambda row: row["symbol"]),
        "currency": group_stats(challenger, lambda row: row["currency"]),
        "side": group_stats(challenger, lambda row: row["side"]),
        "formation_quintile": formation_quintile_stats(challenger),
    }
    chart_hashes = render_population_charts(weeks, challenger, groups)
    chart_hashes[montage_name] = montage_sha
    best_week = max(weeks, key=lambda row: (float(row["challenger_return_x1"]), row["week_date"]))
    worst_week = min(weeks, key=lambda row: (float(row["challenger_return_x1"]), row["week_date"]))
    summary = {
        "schema_version": "g10_xmom_002_train_forensics.v1",
        "hypothesis_id": "HYP-G10-XMOM-W1-002",
        "attempt_id": "G10XMOM002-TRAIN-EVAL-001",
        "scope": "train_2018_2021_only_holdout_sealed",
        "input_sha256": {path.name: expected for path, expected in EXPECTED.items()},
        "arms": {"challenger": arm_stats(legs, "challenger"), "control": arm_stats(legs, "control")},
        "groups": groups,
        "portfolio_extremes": {"best_week": best_week, "worst_week": worst_week},
        "terminal": terminal,
        "case_count": len(case_manifest),
        "chart_sha256": chart_hashes,
        "unknown_fields": [
            "account_currency_pnl", "true_R", "session", "intraday_hour", "variable_holding_time",
            "stop_width", "intrabar_volatility", "news_coverage", "realized_execution_quality",
        ],
        "legal_use": "diagnostic_only_no_filter_no_rescue_no_holdout_authority",
        "grok_visual_review_receipt_sha256": GROK_RECEIPT_SHA256,
    }
    case_manifest_path = OUT / "case_manifest.json"
    case_manifest_path.write_bytes(canonical_json({"sampling_plan_sha256": EXPECTED[SAMPLING_PLAN], "cases": case_manifest}))
    summary["case_manifest_sha256"] = sha256_file(case_manifest_path)
    summary_path = OUT / "population_summary.json"
    summary_path.write_bytes(canonical_json(summary))
    readout_path = OUT / "HYP-G10-XMOM-W1-002_TRAIN_FORENSIC_READOUT.md"
    readout_path.write_text(render_readout(summary, case_manifest), encoding="utf-8", newline="\n")
    print(json.dumps({
        "verdict": "TRAIN_KILL_HOLDOUT_REMAINS_SEALED",
        "output_root": OUT.relative_to(ROOT).as_posix(),
        "population_summary_sha256": sha256_file(summary_path),
        "case_manifest_sha256": sha256_file(case_manifest_path),
        "readout_sha256": sha256_file(readout_path),
        "case_count": len(case_manifest),
        "charts": chart_hashes,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
