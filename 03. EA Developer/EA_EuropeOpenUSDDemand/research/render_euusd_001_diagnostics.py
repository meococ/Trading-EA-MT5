#!/usr/bin/env python3
"""Render the frozen HYP-EUUSD-USDJPY-M1-001 kill diagnostics."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = (
    ROOT
    / "03. EA Developer/EA_EuropeOpenUSDDemand/research/evidence"
    / "HYP-EUUSD-USDJPY-M1-001/EUUSD001-TRAIN-ECON-001"
)
LEDGER = EVIDENCE / "trades.jsonl"
OUTPUT = EVIDENCE / "euusd_001_train_kill_diagnostics.png"
EXPECTED_LEDGER_SHA256 = "18D8C2333FE421DFA279325D30A29D759AAD4333A304BA1FC68E7B485009E10C"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def profit_factor(values: pd.Series) -> float:
    wins = float(values[values > 0].sum())
    losses = float(-values[values < 0].sum())
    return wins / losses


def main() -> int:
    if sha256(LEDGER) != EXPECTED_LEDGER_SHA256:
        raise RuntimeError("trade ledger hash drift")
    if OUTPUT.exists():
        raise RuntimeError("diagnostic output already exists")
    frame = pd.DataFrame(json.loads(line) for line in LEDGER.read_text().splitlines())
    frame["date"] = pd.to_datetime(frame["local_date"])
    frame = frame.sort_values("date").reset_index(drop=True)
    frame["gross_curve"] = frame["gross_pips"].cumsum()
    frame["x1_curve"] = frame["primary_net_x1_pips"].cumsum()
    frame["reverse_x1_curve"] = frame["reverse_net_x1_pips"].cumsum()

    annual = frame.groupby("year").agg(
        gross_pf=("gross_pips", profit_factor),
        x1_pf=("primary_net_x1_pips", profit_factor),
    )
    weekday = frame.groupby("weekday").agg(
        gross_pf=("gross_pips", profit_factor),
        x1_pf=("primary_net_x1_pips", profit_factor),
    )
    weekday.index = ["Mon", "Tue", "Wed", "Thu", "Fri"]

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(2, 2, figsize=(15, 9), constrained_layout=True)
    fig.suptitle(
        "HYP-EUUSD-USDJPY-M1-001 — TRAIN kill diagnostics\n"
        "Long USDJPY 08:00 Europe/Berlin → 14:15 ECB fix | 2016–2020",
        fontsize=15,
        fontweight="bold",
    )

    ax = axes[0, 0]
    ax.plot(frame["date"], frame["gross_curve"], label="Primary gross", color="#4267ac", lw=1.5)
    ax.plot(frame["date"], frame["x1_curve"], label="Primary x1 cost", color="#c43b3b", lw=1.8)
    ax.plot(frame["date"], frame["reverse_x1_curve"], label="Reverse x1", color="#777777", lw=1.2)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_title("Small positive gross drift cannot pay the fixed cost")
    ax.set_ylabel("Cumulative pips")
    ax.legend(loc="best")

    ax = axes[0, 1]
    x = np.arange(len(annual))
    width = 0.36
    ax.bar(x - width / 2, annual["gross_pf"], width, label="Gross PF", color="#7096d1")
    ax.bar(x + width / 2, annual["x1_pf"], width, label="x1 PF", color="#db6a6a")
    ax.axhline(1.0, color="black", lw=0.9, ls="--", label="Breakeven PF")
    ax.axhline(1.3, color="#7b2cbf", lw=0.9, ls=":", label="Target PF 1.30")
    ax.set_xticks(x, annual.index.astype(str))
    ax.set_ylim(0, max(1.5, float(annual.to_numpy().max()) + 0.15))
    ax.set_title("Only 2017 is positive after x1 cost")
    ax.set_ylabel("Profit factor")
    ax.legend(loc="best", fontsize=8)

    ax = axes[1, 0]
    x = np.arange(len(weekday))
    ax.bar(x - width / 2, weekday["gross_pf"], width, label="Gross PF", color="#7096d1")
    ax.bar(x + width / 2, weekday["x1_pf"], width, label="x1 PF", color="#db6a6a")
    ax.axhline(1.0, color="black", lw=0.9, ls="--")
    ax.axhline(1.3, color="#7b2cbf", lw=0.9, ls=":")
    ax.set_xticks(x, weekday.index)
    ax.set_title("No weekday reaches the PF 1.30 target after cost")
    ax.set_ylabel("Profit factor")
    ax.legend(loc="best", fontsize=8)

    ax = axes[1, 1]
    ax.hist(frame["gross_pips"], bins=60, alpha=0.65, label="Gross", color="#4267ac")
    ax.hist(frame["primary_net_x1_pips"], bins=60, alpha=0.55, label="x1 net", color="#c43b3b")
    ax.axvline(0, color="black", lw=0.9)
    ax.set_title("A 1.5-pip cost overwhelms +0.443 pip gross expectancy")
    ax.set_xlabel("Pips per trade")
    ax.set_ylabel("Count")
    ax.legend(loc="best")

    fig.text(
        0.5,
        0.002,
        "N=1,296 | gross PF=1.051 | x1 PF=0.888 | x1 expectancy=-1.057 pips | "
        "1/5 positive years | sign-flip p=0.283 | DSR=0.000008",
        ha="center",
        fontsize=10,
    )
    fig.savefig(OUTPUT, dpi=180, facecolor="white")
    plt.close(fig)
    print(f"CHART {OUTPUT}")
    print(f"SHA256 {sha256(OUTPUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
