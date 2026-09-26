"""VPA-DR3 fidelity set (F5): 120 accepted + 60 rejected, stratified by year,
excluding +-50 bars around the 60 burned cases; one blind set of 180.

Outputs (PLAN/grading_dr3/): snapshots/case_001..180.png (120 bars ending at
the decision/trigger bar, NO bars after), INDEX_BLIND.csv, KEY_HIDDEN_DR3.csv,
DRAW_QA.csv, LEAD_SPOTCHECK_INDEX.csv (20 blind cases: 12 accepted, 8 rejected).
No outcome fields (F7/E4).
"""

import csv
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
OUT = os.path.join(PKG, "PLAN", "grading_dr3")
SNAP = os.path.join(OUT, "snapshots")
GRADING = os.path.join(PKG, "PLAN", "grading")

from vpa_data import load_m5_bars  # noqa: E402
from vpa_dr1 import run_dr1, DR3_CFG  # noqa: E402
from vpa_random_baseline import eu_server_offset_hours  # noqa: E402

SEED = 20260920
WINDOW = 120
N_ACC, N_REJ = 120, 60
EXCL = 50
UP, DOWN, EMA_C, BARRIER_C, OTHER_C = "#2DD4BF", "#FB7185", "#818CF8", "#0F766E", "#9CA3AF"


def draw(case_id, bars, ema, t, side, level, touches, entry, stop, active_others):
    o, h, l, c = bars["o"], bars["h"], bars["l"], bars["c"]
    i0 = t - WINDOW + 1
    xs = np.arange(i0, t + 1)
    fig, ax = plt.subplots(figsize=(12.0, 4.8), dpi=100)
    for k, i in enumerate(xs):
        up = c[i] >= o[i]
        col = UP if up else DOWN
        ax.vlines(k, l[i], h[i], color=col, linewidth=0.9, zorder=2)
        lo, hi = min(o[i], c[i]), max(o[i], c[i])
        ax.add_patch(Rectangle((k - 0.32, lo), 0.64, max(hi - lo, 1e-9),
                               facecolor=col, edgecolor=col, linewidth=0.4, zorder=3))
    ax.plot(np.arange(len(xs)), [ema[i] for i in xs], color=EMA_C, linewidth=1.6, zorder=4)
    if level is not None:
        ax.axhline(level, color=BARRIER_C, linewidth=2.0, zorder=5)
        for ti in touches:
            if i0 <= ti <= t:
                px = h[ti] if side > 0 else l[ti]
                ax.plot([ti - i0], [px], marker="o", markersize=5, markerfacecolor="none",
                        markeredgecolor=BARRIER_C, markeredgewidth=1.4, zorder=6)
    for (_s, bl) in active_others:
        ax.axhline(bl, color=OTHER_C, linewidth=0.8, linestyle=":", zorder=1)
    ax.axhline(entry, color="#111827", linewidth=1.0, linestyle="--", zorder=5)
    ax.axhline(stop, color="#B91C1C", linewidth=0.8, linestyle=":", zorder=5)
    ax.add_patch(Rectangle((len(xs) - 0.5, min(l[t], o[t])), 1.0, abs(h[t] - l[t]) + 1e-9,
                           fill=False, edgecolor="#111827", linewidth=1.4, zorder=7))
    ax.set_xlim(-1, len(xs) + 2)
    lows = [l[i] for i in xs] + [stop, entry] + ([level] if level is not None else [])
    highs = [h[i] for i in xs] + [stop, entry] + ([level] if level is not None else [])
    pad = (max(highs) - min(lows)) * 0.08 or 1e-4
    ax.set_ylim(min(lows) - pad, max(highs) + pad)
    ax.set_xticks([])
    ax.tick_params(axis="y", labelsize=8)
    ax.set_title(f"{case_id}  EURUSD", fontsize=10, color="#374151")
    ax.grid(alpha=0.15, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(SNAP, f"{case_id}.png"))
    plt.close(fig)
    return i0, int(xs[-1])


def main():
    os.makedirs(SNAP, exist_ok=True)
    bars = load_m5_bars("EURUSD")
    pip = bars["pip"]
    cfg = dict(DR3_CFG, round_grid_price=50.0 * pip, collect_gates=True)
    recs, _ = run_dr1(bars, cfg=cfg)
    # burned neighbourhoods (E3/F5): +-50 bars around every burned case
    key = {r["case_id"]: r for r in csv.DictReader(open(os.path.join(GRADING, "KEY_HIDDEN.csv"), encoding="utf-8"))}
    lead = {r["case_id"]: r for r in csv.DictReader(open(os.path.join(GRADING, "GRADES_LEAD_BLIND.csv"), encoding="utf-8"))}
    burned = np.array(sorted(int(k["bar_idx"]) for cid, k in key.items() if cid in lead))
    ema = None
    # detector for EMA
    from vpa_dr1 import Dr1Detector
    d0 = Dr1Detector(bars, cfg=cfg)
    for i in range(len(bars["t"])):
        d0._update_bar(i)
    ema = d0.ema

    def excluded(t):
        j = int(np.searchsorted(burned, t))
        for jj in (j - 1, j):
            if 0 <= jj < len(burned) and abs(int(burned[jj]) - t) <= EXCL:
                return True
        return False

    accepted, rejected = [], []
    for r in recs:
        t = r.get("trigger_idx", r["bar_idx"])
        if t < WINDOW or excluded(t):
            continue
        if r.get("executable"):
            accepted.append(r)
        elif r.get("skip_reason") in ("skip_trend", "skip_integrity"):
            rejected.append(r)
    print(f"eligible: accepted {len(accepted)} rejected {len(rejected)}")
    rng = np.random.default_rng(SEED)
    import datetime as _dt

    def year_of(r):
        return _dt.datetime.utcfromtimestamp(int(bars["t"][r["bar_idx"]])).year

    def strat_sample(pool, n):
        out = []
        years = sorted(set(year_of(r) for r in pool))
        per = n // len(years)
        for y in years:
            ys = [r for r in pool if year_of(r) == y]
            idx = rng.choice(len(ys), size=min(per, len(ys)), replace=False)
            out += [ys[i] for i in idx]
        rest = [r for r in pool if r not in out]
        while len(out) < n and rest:
            i = int(rng.integers(0, len(rest)))
            out.append(rest.pop(i))
        return out[:n]

    sa = strat_sample(accepted, N_ACC)
    sr = strat_sample(rejected, N_REJ)
    cases = [("accepted", r) for r in sa] + [("rejected", r) for r in sr]
    order = rng.permutation(len(cases))
    cases = [cases[i] for i in order]

    index_rows, key_rows, qa_rows = [], [], []
    for n, (grp, r) in enumerate(cases, start=1):
        cid = f"case_{n:03d}"
        t = r.get("trigger_idx", r["bar_idx"])
        side = r["side"]
        g = r.get("gates") or {}
        derived = g.get("_derived") or {}
        entry = derived.get("entry")
        if entry is None:
            entry = (bars["h"][t] + 1.0 * pip) if side > 0 else (bars["l"][t] - 1.0 * pip)
        stop = entry - side * d0.cfg["stop_pips"] * pip
        i0, last_drawn = draw(cid, bars, ema, t, side, r.get("level"), r.get("touches") or [], entry, stop,
                              r.get("active_others") or [])
        dt = np.datetime64(int(bars["t"][t]), "s").astype("datetime64[m]")
        naive = pd.to_datetime([int(bars["t"][t]) + 300], unit="s", utc=False)
        off = eu_server_offset_hours(naive)[0]
        decision_utc = (naive[0] - pd.Timedelta(hours=int(off))).strftime("%Y-%m-%dT%H:%M:%SZ")
        index_rows.append({"case_id": cid, "symbol": "EURUSD", "decision_utc": decision_utc,
                           "side": "long" if side > 0 else "short",
                           "entry": f"{entry:.5f}", "stop": f"{stop:.5f}"})
        key_rows.append({"case_id": cid, "group": grp, "first_fail": r.get("skip_reason") or "executable",
                         "bar_idx": t, "signal_idx": r["bar_idx"], "side": side,
                         "session": r.get("session"), "year": int(str(dt)[:4]),
                         "level": r.get("level"), "touches": len(r.get("touches") or []),
                         "n": r.get("n"), "setup": r.get("setup")})
        qa_rows.append({"case_id": cid, "decision_bar_idx": t, "first_drawn": i0, "last_drawn": last_drawn,
                        "n_bars": t - i0 + 1, "ok_last_is_decision": int(last_drawn == t and t - i0 + 1 == WINDOW),
                        "ok_no_future": int(i0 >= 0 and t - i0 + 1 == WINDOW),
                        "file_bytes": os.path.getsize(os.path.join(SNAP, f"{cid}.png"))})
    with open(os.path.join(OUT, "INDEX_BLIND.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(index_rows[0].keys()))
        w.writeheader(); w.writerows(index_rows)
    with open(os.path.join(OUT, "KEY_HIDDEN_DR3.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(key_rows[0].keys()))
        w.writeheader(); w.writerows(key_rows)
    with open(os.path.join(OUT, "DRAW_QA.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(qa_rows[0].keys()))
        w.writeheader(); w.writerows(qa_rows)
    # blind spot-check: 12 accepted + 8 rejected, no labels
    ai = [r["case_id"] for r in key_rows if r["group"] == "accepted"]
    ri = [r["case_id"] for r in key_rows if r["group"] == "rejected"]
    pick = [ai[i] for i in rng.choice(len(ai), size=12, replace=False)] + \
           [ri[i] for i in rng.choice(len(ri), size=8, replace=False)]
    pick = sorted(pick)
    with open(os.path.join(OUT, "LEAD_SPOTCHECK_INDEX.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(index_rows[0].keys()))
        w.writeheader()
        for cid in pick:
            w.writerow([r for r in index_rows if r["case_id"] == cid][0])
    ok = all(r["ok_last_is_decision"] and r["ok_no_future"] for r in qa_rows)
    print(f"snapshots={len(qa_rows)} draw_qa_ok={ok} spotcheck={len(pick)}")
    print("[write]", OUT)


if __name__ == "__main__":
    main()
