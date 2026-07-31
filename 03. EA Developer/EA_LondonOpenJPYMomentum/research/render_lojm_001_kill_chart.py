#!/usr/bin/env python3
"""Render the frozen LOJM001 kill diagnostics without parameter exploration.

Chart contract
--------------
Question: Is the failure isolated or persistent across time and cost stress?
Takeaway: Compare cumulative x1 net pips, PF against frozen gates, and annual
net pips on the exact 1,283-trade terminal population.
Surface: standalone static PNG in the attempt evidence directory.
Palette: blue primary, gold reverse/control, charcoal frozen gate; line style
and direct labels provide non-color distinction.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / (
    "03. EA Developer/EA_LondonOpenJPYMomentum/research/evidence/"
    "HYP-LOJM-USDJPY-M1-001/LOJM001-TRAIN-ECON-001"
)
TERMINAL = EVIDENCE / "train_economic_terminal.json"
TRADES = EVIDENCE / "trades.jsonl"
OUTPUT = EVIDENCE / "lojm_001_train_kill_diagnostics.png"
EXPECTED_TERMINAL_SHA = "FCBCC6B5C54796B0D96F81B71BAD825A809DB605EDFDD88374F84AE1129A86FB"
EXPECTED_TRADES_SHA = "6985108DEEDF59A503F5A96285F7D5CC8D8CE303FC03A599B5C3E414E0ECDC98"

BLUE = "#2F6B9A"
GOLD = "#C18A28"
CHARCOAL = "#33383D"
GRID = "#D9DEE3"
LIGHT_BLUE = "#C8DBE9"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    if OUTPUT.exists():
        raise RuntimeError("chart output already exists")
    if sha256(TERMINAL) != EXPECTED_TERMINAL_SHA:
        raise RuntimeError("terminal hash mismatch")
    if sha256(TRADES) != EXPECTED_TRADES_SHA:
        raise RuntimeError("trade ledger hash mismatch")
    terminal = json.loads(TERMINAL.read_text(encoding="utf-8"))
    if terminal.get("verdict") != "KILL_TRAIN_PROXY_HOLDOUT_REMAINS_SEALED":
        raise RuntimeError("chart is only valid for the frozen kill terminal")
    records = [json.loads(line) for line in TRADES.read_text(encoding="utf-8").splitlines()]
    frame = pd.DataFrame(records)
    if len(frame) != 1283:
        raise RuntimeError("trade population mismatch")
    frame["local_date"] = pd.to_datetime(frame["local_date"])
    frame = frame.sort_values("local_date").reset_index(drop=True)
    frame["primary_equity"] = frame["primary_net_x1_pips"].cumsum()
    frame["reverse_equity"] = frame["reverse_net_x1_pips"].cumsum()

    metrics = terminal["metrics"]
    pf = metrics["profit_factor"]["primary"]
    annual = metrics["annual_primary_x1_net_pips"]

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.edgecolor": CHARCOAL,
            "axes.labelcolor": CHARCOAL,
            "xtick.color": CHARCOAL,
            "ytick.color": CHARCOAL,
            "text.color": CHARCOAL,
        }
    )
    fig = plt.figure(figsize=(14, 9), facecolor="white")
    grid = fig.add_gridspec(2, 2, height_ratios=[1.35, 1.0], hspace=0.38, wspace=0.26)
    ax_equity = fig.add_subplot(grid[0, :])
    ax_pf = fig.add_subplot(grid[1, 0])
    ax_year = fig.add_subplot(grid[1, 1])

    ax_equity.plot(
        frame["local_date"],
        frame["primary_equity"],
        color=BLUE,
        linewidth=2.1,
        label="Primary: London-open sign",
    )
    ax_equity.plot(
        frame["local_date"],
        frame["reverse_equity"],
        color=GOLD,
        linewidth=1.8,
        linestyle="--",
        label="Matched reverse control",
    )
    ax_equity.axhline(0, color=CHARCOAL, linewidth=1.0)
    ax_equity.set_title("Cumulative net pips at x1 cost", loc="left", fontsize=13, weight="bold")
    ax_equity.set_ylabel("Cumulative net pips")
    ax_equity.grid(axis="y", color=GRID, linewidth=0.8)
    ax_equity.legend(frameon=False, loc="lower left", ncol=2)

    labels = ["x1\n1.50 pip", "x1.5\n2.25 pip", "x2\n3.00 pip"]
    values = [pf["x1"], pf["x1_5"], pf["x2"]]
    gates = [1.30, 1.25, 1.00]
    x = np.arange(3)
    width = 0.36
    bars = ax_pf.bar(x - width / 2, values, width, color=BLUE, edgecolor=CHARCOAL, label="Observed PF")
    ax_pf.bar(x + width / 2, gates, width, color=LIGHT_BLUE, edgecolor=CHARCOAL, hatch="//", label="Frozen gate")
    ax_pf.set_xticks(x, labels)
    ax_pf.set_ylim(0, 1.55)
    ax_pf.set_ylabel("Profit factor")
    ax_pf.set_title("Profit factor vs frozen cost gates", loc="left", fontsize=13, weight="bold")
    ax_pf.grid(axis="y", color=GRID, linewidth=0.8)
    ax_pf.legend(frameon=False, fontsize=9)
    for bar, value in zip(bars, values):
        ax_pf.text(bar.get_x() + bar.get_width() / 2, value + 0.035, f"{value:.3f}", ha="center", fontsize=9)

    years = list(annual.keys())
    year_values = [annual[year] for year in years]
    year_colors = [BLUE if value >= 0 else LIGHT_BLUE for value in year_values]
    year_bars = ax_year.bar(years, year_values, color=year_colors, edgecolor=CHARCOAL)
    ax_year.axhline(0, color=CHARCOAL, linewidth=1.0)
    ax_year.set_title("Annual primary net pips at x1", loc="left", fontsize=13, weight="bold")
    ax_year.set_ylabel("Net pips")
    ax_year.grid(axis="y", color=GRID, linewidth=0.8)
    for bar, value in zip(year_bars, year_values):
        offset = 35 if value >= 0 else -70
        ax_year.text(bar.get_x() + bar.get_width() / 2, value + offset, f"{value:+.0f}", ha="center", fontsize=9)

    fig.suptitle(
        "HYP-LOJM-USDJPY-M1-001 — TRAIN proxy diagnostics",
        x=0.065,
        y=0.985,
        ha="left",
        fontsize=18,
        weight="bold",
    )
    fig.text(
        0.065,
        0.945,
        "FivePercent completed Bid M1 close proxy · Europe/London DST · 2016–2020 · "
        "N=1,283 · one trade per complete weekday · close-only, not deploy-ready",
        ha="left",
        fontsize=10.5,
        color="#5B6268",
    )
    fig.text(
        0.065,
        0.018,
        "Source: frozen terminal FCBCC6B5… · PF 0.793 / 0.741 / 0.693 · "
        "x1 expectancy −2.576 pips · positive years 1/5 · permutation p=0.8618",
        ha="left",
        fontsize=9.5,
        color="#5B6268",
    )
    fig.subplots_adjust(top=0.89, bottom=0.09, left=0.065, right=0.975)
    fig.savefig(OUTPUT, dpi=180, facecolor="white")
    plt.close(fig)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
