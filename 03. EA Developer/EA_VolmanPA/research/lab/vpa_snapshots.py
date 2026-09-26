"""VPA-P2b — blind grading sample + snapshots.

Per PLAN/GRADING_PREREG.md (frozen pre-grading):
  - SRS N=160 from the 9,778 in-session raw breaks (EURUSD M5 DESIGN);
  - N=40 SRS from the 62 executables (detector precision);
  - 200 neutral PNGs (120 M5 bars ENDING at the decision bar, zero bars after);
  - INDEX_BLIND.csv (case_id, symbol, decision_utc, side, entry, stop);
  - KEY_HIDDEN.csv (case_id -> group, funnel stage, features) — do not open
    during grading;
  - DRAW_QA.csv verifying the last drawn bar is the decision bar.

No outcome, no PnL, no MT5. Writes only under PLAN/grading/.
"""

import csv
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
PKG = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(PKG, "PLAN", "grading")
SNAP = os.path.join(OUT, "snapshots")

from vpa_core import run_detector  # noqa: E402
from vpa_data import load_m5_bars  # noqa: E402
from vpa_random_baseline import eu_server_offset_hours  # noqa: E402

SEED = 20260920
N_SRS = 160
N_EXEC = 40
WINDOW = 120
STOP_PIPS = 8.0

UP = "#2DD4BF"
DOWN = "#FB7185"
EMA_C = "#818CF8"
BARRIER_C = "#0F766E"
OTHER_C = "#9CA3AF"


def draw_case(case_id, rec, bars, t, symbol):
    o, h, l, c = bars["o"], bars["h"], bars["l"], bars["c"]
    i0 = t - WINDOW + 1
    assert i0 >= 0, f"case {case_id}: not enough history"
    xs = np.arange(i0, t + 1)
    assert xs[-1] == t and len(xs) == WINDOW, "window must end at the decision bar"
    pip = bars["pip"]
    side = rec["side"]
    entry = (h[t] + 1.0 * pip) if side > 0 else (l[t] - 1.0 * pip)
    stop = entry - side * STOP_PIPS * pip

    fig, ax = plt.subplots(figsize=(13.0, 5.2), dpi=100)
    for k, i in enumerate(xs):
        up = c[i] >= o[i]
        col = UP if up else DOWN
        ax.vlines(k, l[i], h[i], color=col, linewidth=0.9, zorder=2)
        lo, hi = min(o[i], c[i]), max(o[i], c[i])
        ax.add_patch(Rectangle((k - 0.32, lo), 0.64, max(hi - lo, 1e-9),
                               facecolor=col, edgecolor=col, linewidth=0.4, zorder=3))
    ema = np.asarray([bars_ema[i] for i in xs], dtype=float)
    ax.plot(np.arange(len(xs)), ema, color=EMA_C, linewidth=1.6, zorder=4, label="EMA25")

    # broken barrier + touch marks
    level = rec.get("level")
    if level is not None:
        ax.axhline(level, color=BARRIER_C, linewidth=2.0, zorder=5)
        for ti in rec.get("touches", []):
            if i0 <= ti <= t:
                px = h[ti] if side > 0 else l[ti]
                ax.plot([ti - i0], [px], marker="o", markersize=5,
                        markerfacecolor="none", markeredgecolor=BARRIER_C, markeredgewidth=1.4, zorder=6)
    # other active barriers (thin)
    for bs, bl in rec.get("active_others", []) or []:
        ax.axhline(bl, color=OTHER_C, linewidth=0.8, linestyle=":", zorder=1)

    # stop-entry line
    ax.axhline(entry, color="#111827", linewidth=1.0, linestyle="--", zorder=5)
    ax.text(len(xs) - 1, entry, " entry", va="center", ha="left", fontsize=8, color="#111827")

    # highlight the break/decision bar (last)
    ax.add_patch(Rectangle((len(xs) - 0.5, min(l[t], o[t])), 1.0, abs(h[t] - l[t]) + 1e-9,
                           fill=False, edgecolor="#111827", linewidth=1.4, zorder=7))

    ax.set_xlim(-1, len(xs) + 2)
    lo_all = min(min(l[i0:t + 1]), stop, entry, level if level is not None else 1e9)
    hi_all = max(max(h[i0:t + 1]), stop, entry, level if level is not None else -1e9)
    pad = (hi_all - lo_all) * 0.08 or 1e-4
    ax.set_ylim(lo_all - pad, hi_all + pad)
    ax.set_xticks([])
    ax.tick_params(axis="y", labelsize=8)
    ax.set_title(f"case_{case_id:03d}  {symbol}", fontsize=10, color="#374151")
    ax.grid(alpha=0.15, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    path = os.path.join(SNAP, f"case_{case_id:03d}.png")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path, entry, stop, i0


def main():
    os.makedirs(SNAP, exist_ok=True)
    bars = load_m5_bars("EURUSD")
    global bars_ema
    recs, counters = run_detector(bars)
    # rebuild EMA array for drawing: run a fresh Detector to expose ema
    from vpa_core import Detector
    d = Detector(bars)
    for t in range(len(bars["t"])):
        d._update_bar(t)
    bars_ema = d.ema
    assert len(bars_ema) == len(bars["t"])

    srs = [r for r in recs if r.get("setup") == "pattern_break" and r.get("session") in ("london", "ny")]
    # drawing constraint: 120 bars of history must exist before the decision bar.
    # 2 of the 9,778 in-session breaks sit in the first 119 bars; they are excluded
    # here and the exclusion is reported in G2_FREQUENCY_ESTIMATE.md.
    srs = [r for r in srs if r["bar_idx"] >= WINDOW - 1]
    execs = [r for r in recs if r.get("executable")]
    print(f"frame srs={len(srs)} exec={len(execs)}")
    assert len(srs) == 9776, f"unexpected SRS frame {len(srs)}"
    assert len(execs) == 62, f"unexpected exec frame {len(execs)}"

    rng = np.random.default_rng(SEED)
    srs_pick = rng.choice(len(srs), size=N_SRS, replace=False)
    exec_pick = rng.choice(len(execs), size=N_EXEC, replace=False)
    cases = [("srs", srs[i]) for i in srs_pick] + [("exec", execs[i]) for i in exec_pick]
    order = rng.permutation(len(cases))
    cases = [cases[i] for i in order]

    index_rows, key_rows, qa_rows = [], [], []
    selected = []
    for n, (group, rec) in enumerate(cases, start=1):
        t = rec["bar_idx"]
        path, entry, stop, i0 = draw_case(n, rec, bars, t, "EURUSD")
        naive = pd.to_datetime([int(bars["t"][t]) + 300], unit="s", utc=False)
        off = eu_server_offset_hours(naive)[0]
        decision_utc = (naive[0] - pd.Timedelta(hours=int(off))).strftime("%Y-%m-%dT%H:%M:%SZ")
        index_rows.append({"case_id": f"case_{n:03d}", "symbol": "EURUSD",
                           "decision_utc": decision_utc, "side": "long" if rec["side"] > 0 else "short",
                           "entry": f"{entry:.5f}", "stop": f"{stop:.5f}"})
        feat = {
            "case_id": f"case_{n:03d}", "sample_group": group, "setup": rec.get("setup"),
            "funnel_stage": rec.get("skip_reason") or "executable",
            "bar_idx": t, "session": rec.get("session"), "side": rec.get("side"),
            "bias": rec.get("bias"), "atr": rec.get("atr"), "ema": rec.get("ema"),
            "n_buildup": rec.get("n"), "contraction": rec.get("contraction"),
            "overlap": rec.get("overlap"), "progression": rec.get("progression"),
            "counter": rec.get("counter"), "room_pips": rec.get("room_pips"),
            "rho": rec.get("rho"), "barrier_level": rec.get("level"),
            "touches": len(rec.get("touches") or []),
            "active_others": len(rec.get("active_others") or []),
            "pr_depth": rec.get("pr_depth"), "pr_corr_er": rec.get("pr_corr_er"),
        }
        key_rows.append(feat)
        qa_rows.append({"case_id": f"case_{n:03d}", "decision_bar_idx": t, "first_drawn": i0,
                        "last_drawn": t, "n_bars": t - i0 + 1,
                        "ok_last_is_decision": int((t - i0 + 1) == WINDOW and t == t),
                        "ok_no_future": int(i0 >= 0 and t - i0 + 1 == WINDOW),
                        "file_bytes": os.path.getsize(path)})
        cp = dict(rec)
        cp.pop("touches", None)
        cp.pop("active_others", None)
        selected.append(cp)
    with open(os.path.join(OUT, "INDEX_BLIND.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["case_id", "symbol", "decision_utc", "side", "entry", "stop"])
        w.writeheader()
        w.writerows(index_rows)
    with open(os.path.join(OUT, "KEY_HIDDEN.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(key_rows[0].keys()))
        w.writeheader()
        w.writerows(key_rows)
    with open(os.path.join(OUT, "DRAW_QA.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(qa_rows[0].keys()))
        w.writeheader()
        w.writerows(qa_rows)
    with open(os.path.join(OUT, "selected_cases.json"), "w", encoding="utf-8") as f:
        json.dump(selected, f, default=str)
    ok = all(r["ok_last_is_decision"] and r["ok_no_future"] and r["n_bars"] == WINDOW for r in qa_rows)
    print(f"snapshots={len(qa_rows)} draw_qa_ok={ok}")
    print("INDEX_BLIND, KEY_HIDDEN, DRAW_QA, selected_cases.json written to", OUT)


if __name__ == "__main__":
    main()
