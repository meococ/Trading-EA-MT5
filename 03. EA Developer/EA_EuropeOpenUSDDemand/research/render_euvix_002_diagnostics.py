#!/usr/bin/env python3
"""Render frozen HYP-EUVIX-EURUSD-M1-002 kill diagnostics."""

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
EVIDENCE = ROOT / "03. EA Developer/EA_EuropeOpenUSDDemand/research/evidence/HYP-EUVIX-EURUSD-M1-002/EUVIX002-TRAIN-ECON-001"
LEDGER = EVIDENCE / "trades.jsonl"
OUTPUT = EVIDENCE / "euvix_002_train_kill_diagnostics.png"
EXPECTED_LEDGER_SHA256 = "B2C9CA21F80F307BDBCB9B8DFE34D4477D3B7CFF78B164823D6810563EA66F1E"


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
    frame["gross_curve"] = frame["gross_pips"].cumsum()
    frame["x1_curve"] = frame["primary_net_x1_pips"].cumsum()
    frame["reverse_curve"] = frame["reverse_net_x1_pips"].cumsum()
    annual = frame.groupby("year").agg(count=("trade_id", "count"), gross_pf=("gross_pips", pf), x1_pf=("primary_net_x1_pips", pf))

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(2, 2, figsize=(15, 9), constrained_layout=True)
    fig.suptitle("HYP-EUVIX-EURUSD-M1-002 — TRAIN kill diagnostics\nShort EURUSD pre-ECB only in strict-lag high-VIX state | 2016–2020", fontsize=15, fontweight="bold")

    ax = axes[0, 0]
    ax.plot(frame["date"], frame["gross_curve"], label="Filtered gross", color="#4267ac", lw=1.5)
    ax.plot(frame["date"], frame["x1_curve"], label="Filtered x1", color="#c43b3b", lw=1.8)
    ax.plot(frame["date"], frame["reverse_curve"], label="Reverse x1", color="#777777", lw=1.2)
    ax.axhline(0, color="black", lw=0.8); ax.set_ylabel("Cumulative pips")
    ax.set_title("High-VIX conditioning does not create a cost survivor"); ax.legend(loc="best")

    ax = axes[0, 1]
    x = np.arange(len(annual)); width = .36
    ax.bar(x - width / 2, annual["gross_pf"], width, label="Gross PF", color="#7096d1")
    ax.bar(x + width / 2, annual["x1_pf"], width, label="x1 PF", color="#db6a6a")
    ax.axhline(1, color="black", ls="--", lw=.9); ax.axhline(1.3, color="#7b2cbf", ls=":", lw=.9)
    ax.set_xticks(x, annual.index.astype(str)); ax.set_ylabel("Profit factor")
    ax.set_title("Only 2/5 years positive after x1 cost"); ax.legend(loc="best", fontsize=8)

    ax = axes[1, 0]
    ax.bar(annual.index.astype(str), annual["count"], color="#547aa5")
    ax.axhline(30, color="black", ls="--", lw=.9, label="Frozen minimum/year")
    ax.set_title("High-VIX trades cluster in 2018 and 2020")
    ax.set_ylabel("Selected trades"); ax.legend(loc="best")

    ax = axes[1, 1]
    excess = frame["vix_close"] - frame["vix_trailing_prior_252_median"]
    ax.scatter(excess, frame["gross_pips"], s=12, alpha=.42, color="#4267ac")
    slope = np.polyfit(excess, frame["gross_pips"], 1)
    grid = np.linspace(float(excess.min()), float(excess.max()), 100)
    ax.plot(grid, slope[0] * grid + slope[1], color="#c43b3b", lw=1.5)
    ax.axhline(1.5, color="black", ls="--", lw=.9, label="x1 cost")
    ax.set_title("More VIX excess does not visibly amplify daily gross PnL")
    ax.set_xlabel("VIX close minus trailing prior median"); ax.set_ylabel("Gross pips")
    ax.legend(loc="best", fontsize=8)

    fig.text(.5, .002, "N=592 | cadence=2.268/week | gross PF=1.128 | x1 PF=0.977 | x1 expectancy=-0.247 pips | 2/5 positive years | p=0.145 | DSR=0.009", ha="center", fontsize=10)
    fig.savefig(OUTPUT, dpi=180, facecolor="white"); plt.close(fig)
    print(f"CHART {OUTPUT}"); print(f"SHA256 {sha256(OUTPUT)}"); return 0


if __name__ == "__main__":
    raise SystemExit(main())
