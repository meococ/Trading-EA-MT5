#!/usr/bin/env python3
"""Render the frozen HYP-EUUSD-EURUSD-M1-001 kill diagnostics."""

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
EVIDENCE = ROOT / "03. EA Developer/EA_EuropeOpenUSDDemand/research/evidence/HYP-EUUSD-EURUSD-M1-001/EUEUR001-TRAIN-ECON-001"
LEDGER = EVIDENCE / "trades.jsonl"
OUTPUT = EVIDENCE / "euusd_eurusd_001_train_kill_diagnostics.png"
EXPECTED_LEDGER_SHA256 = "204050AAA213DB1BC468FD022733425DC3E2E70EF33A742A0A7D620EF8B166E8"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def pf(values: pd.Series) -> float:
    return float(values[values > 0].sum() / -values[values < 0].sum())


def main() -> int:
    if sha256(LEDGER) != EXPECTED_LEDGER_SHA256:
        raise RuntimeError("trade ledger hash drift")
    if OUTPUT.exists():
        raise RuntimeError("diagnostic output already exists")
    frame = pd.DataFrame(json.loads(line) for line in LEDGER.read_text().splitlines())
    frame["date"] = pd.to_datetime(frame["local_date"])
    frame = frame.sort_values("date").reset_index(drop=True)
    for name in ("gross_pips", "primary_net_x1_pips", "reverse_net_x1_pips"):
        frame[f"{name}_curve"] = frame[name].cumsum()
    annual = frame.groupby("year").agg(gross_pf=("gross_pips", pf), x1_pf=("primary_net_x1_pips", pf))
    weekday = frame.groupby("weekday").agg(gross_pf=("gross_pips", pf), x1_pf=("primary_net_x1_pips", pf))
    weekday.index = ["Mon", "Tue", "Wed", "Thu", "Fri"]

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(2, 2, figsize=(15, 9), constrained_layout=True)
    fig.suptitle("HYP-EUUSD-EURUSD-M1-001 — TRAIN kill diagnostics\nShort EURUSD 08:00 Europe/Berlin → 14:15 ECB fix | 2016–2020", fontsize=15, fontweight="bold")

    ax = axes[0, 0]
    ax.plot(frame["date"], frame["gross_pips_curve"], label="Primary gross", color="#4267ac", lw=1.5)
    ax.plot(frame["date"], frame["primary_net_x1_pips_curve"], label="Primary x1", color="#c43b3b", lw=1.8)
    ax.plot(frame["date"], frame["reverse_net_x1_pips_curve"], label="Reverse x1", color="#777777", lw=1.2)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_title("Source-ranked direction has gross drift, but not enough after cost")
    ax.set_ylabel("Cumulative pips")
    ax.legend(loc="best")

    def bars(ax: plt.Axes, table: pd.DataFrame, labels: list[str], title: str) -> None:
        x = np.arange(len(table)); width = 0.36
        ax.bar(x - width / 2, table["gross_pf"], width, label="Gross PF", color="#7096d1")
        ax.bar(x + width / 2, table["x1_pf"], width, label="x1 PF", color="#db6a6a")
        ax.axhline(1.0, color="black", lw=0.9, ls="--")
        ax.axhline(1.3, color="#7b2cbf", lw=0.9, ls=":")
        ax.set_xticks(x, labels); ax.set_title(title); ax.set_ylabel("Profit factor")
        ax.legend(loc="best", fontsize=8)

    bars(axes[0, 1], annual, annual.index.astype(str).tolist(), "Only 2018 and 2020 are positive after x1 cost")
    bars(axes[1, 0], weekday, weekday.index.tolist(), "Wednesday is post-outcome anatomy, not a legal rescue")

    ax = axes[1, 1]
    ax.hist(frame["gross_pips"], bins=60, alpha=0.65, label="Gross", color="#4267ac")
    ax.hist(frame["primary_net_x1_pips"], bins=60, alpha=0.55, label="x1 net", color="#c43b3b")
    ax.axvline(0, color="black", lw=0.9)
    ax.set_title("1.5-pip cost exceeds +1.201-pip gross expectancy")
    ax.set_xlabel("Pips per trade"); ax.set_ylabel("Count"); ax.legend(loc="best")

    fig.text(0.5, 0.002, "N=1,296 | gross PF=1.137 | x1 PF=0.969 | x1 expectancy=-0.299 pips | 2/5 positive years | sign-flip p=0.045 | DSR=0.000269", ha="center", fontsize=10)
    fig.savefig(OUTPUT, dpi=180, facecolor="white")
    plt.close(fig)
    print(f"CHART {OUTPUT}")
    print(f"SHA256 {sha256(OUTPUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
