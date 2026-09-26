"""VPA-DR1-DIAG — annotated snapshots for the recall trace.

10 Lead A/B cases (window ends at the case/decision bar: no post-decision
bars, as graded) + 10 missed-break events (up to 3 bars after the break).

Annotations: barrier line + touch marks, buildup box, EMA25, signal bar ring,
entry line, room obstacle (orange dashed), failed-gates label.
Trace config = DR2a (signal_atr 0.50 + v1 sessions), stated in INDEX.csv.
Writes PLAN/diag_dr1/snapshots/*.png + INDEX.csv. No outcome fields (E4).
"""

import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
PKG = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(PKG, "PLAN", "diag_dr1")
SNAP = os.path.join(OUT, "snapshots")
GRADING = os.path.join(PKG, "PLAN", "grading")

from vpa_data import load_m5_bars  # noqa: E402
from vpa_trace import classify_cases  # noqa: E402

SEED = 20260920
WINDOW = 120
DR2A = {"signal_atr": 0.50, "eu": (300, 660), "us": (690, 1050)}
AB_PICK = ["case_003", "case_021", "case_085", "case_153", "case_012",
           "case_020", "case_025", "case_065", "case_154", "case_196"]
UP, DOWN, EMA_C, BARRIER_C, OBST_C = "#2DD4BF", "#FB7185", "#818CF8", "#0F766E", "#F59E0B"


def draw(fname, bars, ema, t0, t1, title, barrier=None, touches=(), buildup=None,
         signal_t=None, entry=None, obstacle=None, label="", side=1, ring_t=None):
    o, h, l, c = bars["o"], bars["h"], bars["l"], bars["c"]
    xs = np.arange(t0, t1 + 1)
    fig, ax = plt.subplots(figsize=(13.0, 5.2), dpi=100)
    for k, i in enumerate(xs):
        up = c[i] >= o[i]
        col = UP if up else DOWN
        ax.vlines(k, l[i], h[i], color=col, linewidth=0.9, zorder=2)
        lo, hi = min(o[i], c[i]), max(o[i], c[i])
        ax.add_patch(Rectangle((k - 0.32, lo), 0.64, max(hi - lo, 1e-9),
                               facecolor=col, edgecolor=col, linewidth=0.4, zorder=3))
    ax.plot(np.arange(len(xs)), [ema[i] for i in xs], color=EMA_C, linewidth=1.6, zorder=4, label="EMA25")
    if barrier is not None:
        ax.axhline(barrier, color=BARRIER_C, linewidth=2.0, zorder=5)
        for ti in touches:
            if t0 <= ti <= t1:
                px = h[ti] if side > 0 else l[ti]
                ax.plot([ti - t0], [px], marker="o", markersize=5, markerfacecolor="none",
                        markeredgecolor=BARRIER_C, markeredgewidth=1.4, zorder=6)
    if buildup:
        s, n = buildup
        if t0 <= s < s + n <= t1 + 1:
            ylo = min(l[s:s + n])
            yhi = max(h[s:s + n])
            ax.add_patch(Rectangle((s - t0, ylo), n, yhi - ylo, fill=False,
                                   edgecolor="#6B7280", linewidth=1.2, linestyle="-", zorder=6))
            ax.text(s - t0, yhi, " buildup", fontsize=8, color="#374151", va="bottom")
    if signal_t is not None and t0 <= signal_t <= t1:
        ax.add_patch(Rectangle((signal_t - t0 - 0.45, l[signal_t] - 2e-5), 0.9,
                               (h[signal_t] - l[signal_t]) + 4e-5, fill=False,
                               edgecolor="#16A34A", linewidth=1.6, zorder=7))
    if ring_t is not None and t0 <= ring_t <= t1:
        ax.add_patch(Rectangle((ring_t - t0 - 0.5, l[ring_t]), 1.0, abs(h[ring_t] - l[ring_t]) + 1e-9,
                               fill=False, edgecolor="#111827", linewidth=1.4, zorder=7))
    if entry is not None:
        ax.axhline(entry, color="#111827", linewidth=1.0, linestyle="--", zorder=5)
        ax.text(len(xs) - 1, entry, " entry", va="center", ha="left", fontsize=8, color="#111827")
    if obstacle is not None:
        ax.axhline(obstacle, color=OBST_C, linewidth=1.2, linestyle=":", zorder=5)
        ax.text(0, obstacle, " room obstacle", fontsize=8, color=OBST_C, va="bottom")
    if label:
        ax.text(0.01, 0.02, label, transform=ax.transAxes, fontsize=8.5, color="#7F1D1D",
                va="bottom", ha="left", bbox=dict(boxstyle="round,pad=0.3", fc="#FEF2F2", ec="#FCA5A5", lw=0.8))
    ax.set_xlim(-1, len(xs) + 2)
    lows = [l[i] for i in xs] + [x for x in (entry, barrier, obstacle) if x is not None]
    highs = [h[i] for i in xs] + [x for x in (entry, barrier, obstacle) if x is not None]
    pad = (max(highs) - min(lows)) * 0.08 or 1e-4
    ax.set_ylim(min(lows) - pad, max(highs) + pad)
    ax.set_xticks([])
    ax.tick_params(axis="y", labelsize=8)
    ax.set_title(title, fontsize=10, color="#374151")
    ax.grid(alpha=0.15, linewidth=0.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(SNAP, fname))
    plt.close(fig)


def hhmm(m):
    return "%02d:%02d" % (int(m) // 60, int(m) % 60)


def main():
    os.makedirs(SNAP, exist_ok=True)
    bars = load_m5_bars("EURUSD")
    key = {r["case_id"]: r for r in csv.DictReader(open(os.path.join(GRADING, "KEY_HIDDEN.csv"), encoding="utf-8"))}
    lead = {r["case_id"]: r for r in csv.DictReader(open(os.path.join(GRADING, "GRADES_LEAD_BLIND.csv"), encoding="utf-8"))}
    cases = []
    for cid, k in key.items():
        if cid not in lead:
            continue
        cases.append({"case_id": cid, "lead_grade": lead[cid]["grade"].strip().upper(),
                      "group": k.get("sample_group"), "setup_v1": k.get("setup"),
                      "bar_idx": int(k["bar_idx"]), "side": int(k["side"]),
                      "barrier_level": float(k["barrier_level"]) if k.get("barrier_level") else None,
                      "atr": float(k["atr"]) if k.get("atr") else None})
    cases.sort(key=lambda c: c["case_id"])
    cfg = {"round_grid_price": 50.0 * bars["pip"]}
    cfg.update(DR2A)
    d, rows, _ = classify_cases(bars, cases, half=12, cfg=cfg)
    ema = d.ema
    by_id = {r["case_id"]: r for r in rows}
    lock_touches = {(s, lv, li): tch for (li, s, lv, e, tch) in d.lock_log}
    index = []
    n_draw = 0
    for cid in AB_PICK:
        r = by_id.get(cid)
        if r is None:
            continue
        t = r["bar_idx"]
        side = r["side"]
        t0 = t - WINDOW + 1
        if t0 < 0:
            continue
        b = (r.get("_barriers") or [None])[0]
        barrier = r.get("dr1_barrier")
        touches = lock_touches.get((side, barrier, r.get("dr1_lock_idx")), ()) if b else ()
        last = r.get("_last_rec")
        buildup = signal_t = entry = obstacle = None
        if last:
            g = last.get("gates") or {}
            bu = (g.get("buildup", {}).get("value") or {})
            if bu.get("start") is not None:
                buildup = (bu["start"], bu["n"])
            signal_t = last["bar_idx"]
            derived = g.get("_derived") or {}
            entry = derived.get("entry")
            obs = (g.get("room", {}).get("value") or {}).get("obstacle") or {}
            obstacle = obs.get("price")
        if r["category"].startswith("(ii)"):
            label = "NO EVAL: %s" % (r["reason"] or "")
        elif r["category"].startswith("(iii)"):
            label = "FAIL %s\nfails: %s" % (r["first_fail"], r["fail_set"])
        else:
            label = "EXEC"
        label += "  [DR2a trace]"
        title = "%s  %s  %s  %s UTC  (Lead %s)" % (cid, "long" if side > 0 else "short",
                                                   r.get("setup_v1"), hhmm(bars["utc_min"][t]), r["lead_grade"])
        fname = f"ab_{cid}.png"
        draw(fname, bars, ema, t0, t, title, barrier=barrier, touches=touches, buildup=buildup,
             signal_t=signal_t, entry=entry, obstacle=obstacle, label=label, side=side, ring_t=t)
        index.append({"file": fname, "kind": "lead_ab", "id": cid, "grade": r["lead_grade"],
                      "category": r["category"], "first_fail": r["first_fail"] or "", "fail_set": r["fail_set"] or "",
                      "bar_idx": t, "utc": hhmm(bars["utc_min"][t]), "barrier": barrier,
                      "touches": r.get("touches"), "post_bars": 0, "trace_cfg": "DR2a"})
        n_draw += 1
    # 10 missed-break events (random, seed fixed)
    events = [(t, s, lv, li) for (t, kind, s, lv, li) in d.event_log if kind == "missed" and t >= WINDOW]
    rng = np.random.default_rng(SEED)
    pick = rng.choice(len(events), size=10, replace=False)
    for n, i in enumerate(sorted(pick), start=1):
        t, s, lv, li = events[i]
        t0 = t - WINDOW + 1
        t1 = min(t + 3, len(bars["t"]) - 1)
        touches = lock_touches.get((s, lv, li), ())
        label = "MISSED BREAK: close beyond B+0.25A -> barrier consumed, no eval"
        title = "missed_%02d  %s  barrier %.5f  %s UTC" % (n, "long" if s > 0 else "short", lv,
                                                           hhmm(bars["utc_min"][t]))
        fname = f"missed_{n:02d}.png"
        draw(fname, bars, ema, t0, t1, title, barrier=lv, touches=touches, label=label, side=s, ring_t=t)
        index.append({"file": fname, "kind": "missed_event", "id": f"missed_{n:02d}", "grade": "",
                      "category": "(ii) no signal eval", "first_fail": "", "fail_set": "",
                      "bar_idx": t, "utc": hhmm(bars["utc_min"][t]), "barrier": round(lv, 6),
                      "touches": len(touches), "post_bars": t1 - t, "trace_cfg": "DR2a"})
        n_draw += 1
    with open(os.path.join(OUT, "snapshots", "INDEX.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(index[0].keys()))
        w.writeheader()
        w.writerows(index)
    print(f"snapshots={n_draw} (ab={sum(1 for r in index if r['kind']=='lead_ab')} "
          f"missed={sum(1 for r in index if r['kind']=='missed_event')})")
    print("INDEX ->", os.path.join(SNAP, "INDEX.csv"))


if __name__ == "__main__":
    main()
