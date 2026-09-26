"""T-VPA-LINE-1 runner: one engine pass -> PLAN/lines1 snapshots + LINE_AUDIT.

  python lines1_run.py --all          # audit + 40 snapshots (default)
  python lines1_run.py --audit        # audit only
  python lines1_run.py --snapshots    # snapshots only

No outcomes (E4/F7): the audit compares line geometry with the burned-case
boundaries and with the DR3 barrier locks only; it never reads fills or PnL.
"""

import argparse
import csv
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
LAB = os.path.abspath(os.path.join(HERE, "..", "lab"))
if LAB not in sys.path:
    sys.path.insert(0, LAB)

from lines1_common import (KIND_COLOR, OUT, SNAP, burned_ab_cases, hhmm,  # noqa: E402
                           load_design, random_design_bars, utc_dt, year_of)
from vpa_lines import LineEngine  # noqa: E402

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

PIP = 1e-4
WINDOW = 120
UP, DOWN, EMA_C = "#2DD4BF", "#FB7185", "#818CF8"
BOUND_C = "#111827"


# --------------------------------------------------------------------- drawing
def draw(fname, bars, ema, t0, t1, title, armed, boundary=None, boundary_label="",
         ring_t=None, note=""):
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
    ax.plot(np.arange(len(xs)), [ema[i] for i in xs], color=EMA_C, linewidth=1.4,
            zorder=4, label="EMA25")
    for a in armed:
        col = KIND_COLOR.get(a.kind, "#374151")
        if abs(a.slope) < 1e-12:
            ax.hlines(a.level, 0, len(xs) - 1 + 2.0, color=col, linewidth=1.9, zorder=6)
            x_lab = len(xs) + 0.2
            y_lab = a.level
        else:
            j0 = max(t0, min(a.anchors))
            xi = np.array([j0 - t0, len(xs) - 1 + 2.0])
            yi = a.level + a.slope * ((xi + t0) - t1)
            ax.plot(xi, yi, color=col, linewidth=1.9, zorder=6)
            x_lab = len(xs) + 0.2
            y_lab = a.level + a.slope * 2.0
        for ti in a.touches:
            if t0 <= ti <= t1:
                px = h[ti] if a.side > 0 else l[ti]
                ax.plot([ti - t0], [px], marker="o", markersize=4.0, markerfacecolor="none",
                        markeredgecolor=col, markeredgewidth=1.1, zorder=7)
        ax.text(x_lab, y_lab, " %s %.2f" % (a.label, a.score), color=col, fontsize=8.2,
                va="center", ha="left", zorder=8,
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec=col, lw=0.6, alpha=0.85))
    if boundary is not None:
        ax.axhline(boundary, color=BOUND_C, linewidth=1.1, linestyle="--", zorder=5)
        ax.text(0.5, boundary, boundary_label, fontsize=8, color=BOUND_C, va="bottom")
    if ring_t is not None and t0 <= ring_t <= t1:
        ax.add_patch(Rectangle((ring_t - t0 - 0.5, l[ring_t] - 1e-5), 1.0,
                               (h[ring_t] - l[ring_t]) + 2e-5, fill=False,
                               edgecolor=BOUND_C, linewidth=1.5, zorder=9))
    if note:
        ax.text(0.01, 0.02, note, transform=ax.transAxes, fontsize=8.5, color="#7F1D1D",
                va="bottom", ha="left",
                bbox=dict(boxstyle="round,pad=0.3", fc="#FEF2F2", ec="#FCA5A5", lw=0.8))
    ax.set_xlim(-1, len(xs) + 9)
    lows = [l[i] for i in xs] + [a.level for a in armed]
    highs = [h[i] for i in xs] + [a.level for a in armed]
    if boundary is not None:
        lows.append(boundary)
        highs.append(boundary)
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


def legend_note(armed):
    kinds = sorted({a.kind for a in armed})
    return "armed: " + ", ".join("%s=%s" % (k, KIND_COLOR.get(k, "#374151")) for k in kinds) \
        if kinds else "no armed lines"


# ---------------------------------------------------------------------- audit
def run_audit(bars, eng, dr3_locks):
    os.makedirs(OUT, exist_ok=True)
    cases = burned_ab_cases()
    atr = eng.atr
    rows = []
    for cs in cases:
        t = cs["bar_idx"]
        A = atr[t]
        raw = eng.armed_at(t, prune=False)
        chart = eng.armed_at(t)
        boundary = cs["case_barrier"] if cs["case_barrier"] is not None else cs["dr3_barrier"]
        best = None
        best_chart = None
        if boundary is not None:
            for a in raw:
                d = abs(a.level - boundary)
                if best is None or d < best[0]:
                    best = (d, a)
            for a in chart:
                d = abs(a.level - boundary)
                if best_chart is None or d < best_chart[0]:
                    best_chart = (d, a)
        tol_eps = 0.10 * A          # the DR3 barrier's own tolerance
        tol_zone = 0.35 * A         # the pro line's touch zone (level_eps_atr)
        rows.append({
            "case_id": cs["case_id"], "grade": cs["grade"], "bar_idx": t,
            "utc": hhmm(bars, t), "setup": cs["setup"], "side": cs["side"],
            "category": cs["category"], "first_fail": cs["first_fail"] or "",
            "case_barrier": "" if cs["case_barrier"] is None else round(cs["case_barrier"], 6),
            "dr3_barrier": "" if cs["dr3_barrier"] is None else round(cs["dr3_barrier"], 6),
            "atr": round(A, 7), "n_raw": len(raw), "n_chart": len(chart),
            "match_eps_kind": "" if best is None or best[0] > tol_eps else best[1].kind,
            "match_eps_score": "" if best is None or best[0] > tol_eps else round(best[1].score, 3),
            "match_zone_kind": "" if best is None or best[0] > tol_zone else best[1].kind,
            "match_zone_score": "" if best is None or best[0] > tol_zone else round(best[1].score, 3),
            "match_zone_on_chart": "" if best_chart is None or best_chart[0] > tol_zone else best_chart[1].kind,
            "nearest_kind": "" if best is None else best[1].kind,
            "nearest_pips": "" if best is None else round(best[0] / PIP, 2),
            "nearest_score": "" if best is None else round(best[1].score, 3),
            "nearest_touches": "" if best is None else best[1].n_touches,
            "nearest_age": "" if best is None else best[1].age,
            "nearest_integrity": "" if best is None else best[1].integrity,
        })
    with open(os.path.join(OUT, "LINE_AUDIT_CASES.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # ---- armed lines per bar (raw and on-chart), sampled DESIGN bars
    stats = []
    dists = []
    step = 100
    for t in range(0, len(bars["t"]), step):
        if atr[t] != atr[t]:
            continue
        raw = eng.armed_at(t, prune=False)
        chart = eng.armed_at(t)
        stats.append((t, len(raw), len(chart)))
        c = bars["c"][t]
        for a in raw:
            dists.append(abs(a.level - c) / atr[t])
    arr = np.array([(a, b) for _, a, b in stats])
    med_raw, p90_raw, max_raw = np.median(arr[:, 0]), np.percentile(arr[:, 0], 90), arr[:, 0].max()
    med_chart, p90_chart, max_chart = np.median(arr[:, 1]), np.percentile(arr[:, 1], 90), arr[:, 1].max()
    darr = np.array(dists)
    med_dist, p90_dist = np.median(darr), np.percentile(darr, 90)
    with open(os.path.join(OUT, "ARMED_COUNTS.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["bar_idx", "utc", "year", "n_raw", "n_chart"])
        for t, nr, nc in stats:
            w.writerow([t, hhmm(bars, t), year_of(bars["t"][t]), nr, nc])

    # ---- DR3 micro-barrier coincidence
    coin = []
    for (lock_idx, side, level, exp_idx, touches) in dr3_locks:
        A = atr[lock_idx]
        if A != A or A <= 0:
            continue
        m_eps = eng.line_near(lock_idx, level, side=None, tol=0.10 * A)
        m_zone = eng.line_near(lock_idx, level, side=None, tol=0.35 * A)
        m_side = eng.line_near(lock_idx, level, side=side, tol=0.35 * A)
        coin.append((lock_idx, side, level, len(touches), m_eps, m_zone, m_side))
    with open(os.path.join(OUT, "DR3_BARRIER_COINCIDENCE.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["lock_idx", "side", "barrier", "touches", "atr",
                    "match_eps_kind", "match_eps_score", "match_zone_kind", "match_zone_score",
                    "match_side_kind", "match_side_score"])
        for (lock_idx, side, level, nt, m_eps, m_zone, m_side) in coin:
            w.writerow([lock_idx, side, round(level, 6), nt, round(atr[lock_idx], 7),
                        "" if m_eps is None else m_eps.kind,
                        "" if m_eps is None else round(m_eps.score, 3),
                        "" if m_zone is None else m_zone.kind,
                        "" if m_zone is None else round(m_zone.score, 3),
                        "" if m_side is None else m_side.kind,
                        "" if m_side is None else round(m_side.score, 3)])
    n = len(coin)
    share_eps = sum(1 for c in coin if c[4] is not None) / n if n else 0.0
    share_zone = sum(1 for c in coin if c[5] is not None) / n if n else 0.0
    share_side = sum(1 for c in coin if c[6] is not None) / n if n else 0.0
    # on-chart share on a 10% sample of the locks (armed_at is the slow path)
    sample = coin[::10]
    n_chart_hit = 0
    chart_rows = []
    for (lock_idx, side, level, nt, m_eps, m_zone, m_side) in sample:
        A = atr[lock_idx]
        hit = None
        for a in eng.armed_at(lock_idx):
            if abs(a.level - level) <= 0.35 * A:
                if hit is None or a.score > hit.score:
                    hit = a
        n_chart_hit += 1 if hit is not None else 0
        chart_rows.append([lock_idx, side, round(level, 6), round(A, 7),
                           1 if hit is not None else 0,
                           "" if hit is None else hit.kind,
                           "" if hit is None else round(hit.score, 3),
                           "" if hit is None else round(abs(hit.level - level) / PIP, 2)])
    with open(os.path.join(OUT, "DR3_BARRIER_COINCIDENCE_CHART_SAMPLE.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["lock_idx", "side", "barrier", "atr", "chart_match", "chart_kind",
                    "chart_score", "chart_pips"])
        w.writerows(chart_rows)
    share_chart = n_chart_hit / len(sample) if sample else 0.0

    # ---- write the report
    n_zone = sum(1 for r in rows if r["match_zone_kind"])
    n_eps = sum(1 for r in rows if r["match_eps_kind"])
    n_chart = sum(1 for r in rows if r["match_zone_on_chart"])
    with open(os.path.join(OUT, "LINE_AUDIT.md"), "w", encoding="utf-8") as f:
        f.write("# LINE_AUDIT — pro lines vs the burned boundaries (T-VPA-LINE-1)\n\n")
        f.write("Engine: `research/lines/vpa_lines.py` (causal, closed bars only). "
                "Score = 0.35*touch + 0.20*age + 0.25*visibility + 0.20*HTF-swing alignment; "
                "armed = score >= 0.50. On-chart = the pruned set "
                "(max 8 lines, max 2 per type, same-price merge 0.15*ATR). "
                "No outcomes anywhere (E4/F7).\n\n")
        f.write("## 1. The 16 Lead-A/B burned cases\n\n")
        f.write("`boundary` = the Lead's key level for the case (`PLAN/grading/KEY_HIDDEN.csv`), "
                "falling back to the DR3 barrier. `match` = best armed line within the DR3 "
                "tolerance (0.10*ATR) / within the pro line zone (0.35*ATR).\n\n")
        f.write("| case | grade | UTC | setup | side | boundary | nearest armed line | d(pips) | score | touches | age | integrity | eps-match | zone-match | on-chart |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
        for r in rows:
            b = r["case_barrier"] if r["case_barrier"] != "" else r["dr3_barrier"]
            f.write("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |\n" % (
                r["case_id"], r["grade"], r["utc"], r["setup"],
                "long" if r["side"] > 0 else "short", b,
                r["nearest_kind"] or "-", r["nearest_pips"], r["nearest_score"],
                r["nearest_touches"], r["nearest_age"],
                "yes" if r["nearest_integrity"] is True else ("no" if r["nearest_integrity"] is False else "-"),
                r["match_eps_kind"] or "-", r["match_zone_kind"] or "-",
                r["match_zone_on_chart"] or "-"))
        f.write("\n**Summary:** eps-match %d/16, zone-match %d/16, zone-match on chart %d/16. "
                "`case_010` is a pullback-reversal case: the DR1/DR3 key carries no barrier "
                "level for it, so it cannot be matched (1 of 16). `d(pips)` = distance from "
                "the boundary to the nearest armed line; `integrity` = that line was never "
                "closed through since it formed.\n\n"
                % (n_eps, n_zone, n_chart))

        f.write("## 2. Armed lines per bar (DESIGN 2016-2021, every 100th bar)\n\n")
        f.write("| metric | raw armed (score >= 0.50) | on chart (pruned) |\n|---|---|---|\n")
        f.write("| median | %.1f | %.1f |\n" % (med_raw, med_chart))
        f.write("| p90 | %.1f | %.1f |\n" % (p90_raw, p90_chart))
        f.write("| max | %d | %d |\n" % (max_raw, max_chart))
        f.write("| bars sampled | %d | %d |\n\n" % (len(stats), len(stats)))
        f.write("Distance of an armed line from the close: median %.2f ATR, p90 %.2f ATR "
                "(raw armed set). A line far from price is a level drawn in advance; "
                "the on-chart set keeps the nearest/best ones.\n\n" % (med_dist, p90_dist))
        f.write("Pruning rule (chart hygiene): sort by score; keep at most %d lines, at most "
                "2 per type; drop a line that sits within 0.15*ATR of an already-kept line "
                "(two lines at the same price are one line). The raw count is the honest "
                "'how many lines exist'; the on-chart count is what the trader sees.\n\n"
                % eng.cfg["max_lines"])

        f.write("## 3. DR3 micro-barriers vs significant lines\n\n")
        f.write("All barriers locked by the frozen DR3 barrier engine "
                "(`research/lab/vpa_core.py`, `barrier_expiry=20`) over DESIGN 2016-2021. "
                "A barrier coincides when an armed line (score >= 0.50) is within tolerance "
                "at the lock bar.\n\n")
        f.write("| tolerance | share | n coincident / n locks |\n|---|---|---|\n")
        f.write("| 0.10*ATR (DR3's own eps) | %.1f%% | %d / %d |\n"
                % (100 * share_eps, sum(1 for c in coin if c[4] is not None), n))
        f.write("| 0.35*ATR (pro line zone) | %.1f%% | %d / %d |\n"
                % (100 * share_zone, sum(1 for c in coin if c[5] is not None), n))
        f.write("| 0.35*ATR + same side | %.1f%% | %d / %d |\n"
                % (100 * share_side, sum(1 for c in coin if c[6] is not None), n))
        f.write("| 0.35*ATR + on chart (10%% sample) | %.1f%% | %d / %d |\n\n"
                % (100 * share_chart, n_chart_hit, len(sample)))
        by_side = {1: [c for c in coin if c[1] > 0], -1: [c for c in coin if c[1] < 0]}
        f.write("| side | n locks | zone share |\n|---|---|---|\n")
        for s, label in ((1, "ceiling"), (-1, "floor")):
            cs = by_side[s]
            sh = 100 * sum(1 for c in cs if c[5] is not None) / len(cs) if cs else 0.0
            f.write("| %s | %d | %.1f%% |\n" % (label, len(cs), sh))
        f.write("\nDetail per lock: `DR3_BARRIER_COINCIDENCE.csv`. Counts per sampled bar: "
                "`ARMED_COUNTS.csv`. Case detail: `LINE_AUDIT_CASES.csv`. The on-chart "
                "sample (every 10th lock, `chart_match` column): "
                "`DR3_BARRIER_COINCIDENCE_CHART_SAMPLE.csv`.\n\n")

        f.write("## 4. Line book (created over DESIGN 2016-2021)\n\n")
        f.write("| kind | lines created |\n|---|---|\n")
        kinds = sorted({l.kind for l in eng.lines.values()})
        for k in kinds:
            f.write("| %s | %d |\n" % (k, sum(1 for l in eng.lines.values() if l.kind == k)))
        f.write("\nEngine counters: `%s`\n\n" % ", ".join(
            "%s=%d" % (k, v) for k, v in sorted(eng.counters.items())))

        f.write("## 5. Method and recompute\n\n")
        f.write("```\n")
        f.write("cd \"03. EA Developer/EA_VolmanPA/research/lines\"\n")
        f.write("python test_vpa_lines.py          # 36/36 fixtures + prefix invariance (synthetic + real data)\n")
        f.write("python lines1_run.py --audit      # this file + the 3 CSVs\n")
        f.write("python lines1_run.py --snapshots  # PLAN/lines1/snapshots/*.png\n")
        f.write("```\n\n")
        f.write("Config = `vpa_lines.DEFAULTS` (the engine prints nothing it does not use). "
                "Causality: a pivot at i is known at i+lag; a line exists only from "
                "`created_idx`; `armed_at(t)` recomputes from bars <= t through the same "
                "`_step_line` path the pass used; `test_prefix_invariance` re-runs on "
                "bars[:t+1] and matches. No outcomes (fills/PnL/win rate) are read or "
                "written anywhere.\n")
    return rows, dict(med_raw=med_raw, p90_raw=p90_raw, med_chart=med_chart,
                      p90_chart=p90_chart, share_eps=share_eps, share_zone=share_zone,
                      share_side=share_side, share_chart=share_chart,
                      med_dist=med_dist, p90_dist=p90_dist,
                      n_locks=n, n_zone=n_zone, n_eps=n_eps, n_chart=n_chart)


# ------------------------------------------------------------------ snapshots
def run_snapshots(bars, eng, random_bars):
    os.makedirs(SNAP, exist_ok=True)
    cases = burned_ab_cases()
    index = []
    for cs in cases:
        t = cs["bar_idx"]
        t0 = max(0, t - WINDOW + 1)
        armed = eng.armed_at(t)
        boundary = cs["case_barrier"] if cs["case_barrier"] is not None else cs["dr3_barrier"]
        title = "%s  %s  %s  %s UTC  (Lead %s)" % (
            cs["case_id"], "long" if cs["side"] > 0 else "short", cs["setup"],
            hhmm(bars, t), cs["grade"])
        note = "%s | raw %d | chart %d\n%s" % (
            cs["first_fail"] or cs["category"], len(eng.armed_at(t, prune=False)),
            len(armed), legend_note(armed))
        fname = "ab_%s.png" % cs["case_id"]
        draw(fname, bars, eng.ema, t0, t, title, armed, boundary=boundary,
             boundary_label="broken boundary %.5f" % boundary if boundary else "",
             ring_t=t, note=note)
        index.append({"file": fname, "kind": "ab_case", "id": cs["case_id"],
                      "bar_idx": t, "utc": hhmm(bars, t), "n_chart": len(armed),
                      "n_raw": len(eng.armed_at(t, prune=False)),
                      "kinds": ";".join(a.kind for a in armed), "last_drawn": t,
                      "n_bars": WINDOW})
    for t in random_bars:
        t0 = max(0, t - WINDOW + 1)
        armed = eng.armed_at(t)
        year = year_of(bars["t"][t])
        title = "random  %s  %s UTC  (%d)" % (hhmm(bars, t), utc_dt(bars["t"][t]).strftime("%Y-%m-%d"), year)
        note = "random DESIGN in-session bar | raw %d | chart %d\n%s" % (
            len(eng.armed_at(t, prune=False)), len(armed), legend_note(armed))
        fname = "random_%s_%d.png" % (utc_dt(bars["t"][t]).strftime("%Y%m%d"), t)
        draw(fname, bars, eng.ema, t0, t, title, armed, ring_t=t, note=note)
        index.append({"file": fname, "kind": "random", "id": "random_%d" % t,
                      "bar_idx": t, "utc": hhmm(bars, t), "n_chart": len(armed),
                      "n_raw": len(eng.armed_at(t, prune=False)),
                      "kinds": ";".join(a.kind for a in armed), "last_drawn": t,
                      "n_bars": WINDOW})
    with open(os.path.join(SNAP, "INDEX.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(index[0].keys()))
        w.writeheader()
        w.writerows(index)
    return index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--snapshots", action="store_true")
    args = ap.parse_args()
    do_audit = args.audit or not (args.audit or args.snapshots)
    do_snap = args.snapshots or not (args.audit or args.snapshots)

    print("[lines1] loading DESIGN 2016-2021 ...")
    bars = load_design()
    print("[lines1] bars:", len(bars["t"]))
    t0 = time.time()
    eng = LineEngine(bars).run()
    print("[lines1] engine pass: %.1fs, lines=%d" % (time.time() - t0, len(eng.lines)))

    if do_snap:
        rb = random_design_bars(bars)
        print("[lines1] random bars:", rb)
        idx = run_snapshots(bars, eng, rb)
        print("[lines1] snapshots:", len(idx))
    if do_audit:
        t0 = time.time()
        import vpa_core
        locks = []
        d = vpa_core.Detector(bars, cfg={"barrier_expiry": 20})
        orig = d._try_lock

        def spy(i, side):
            n0 = len(d.active)
            orig(i, side)
            if len(d.active) > n0:
                b = d.active[-1]
                locks.append((i, b["side"], b["level"], b["exp_idx"], tuple(b["touches"])))
        d._try_lock = spy
        d.run()
        print("[lines1] DR3 barrier locks:", len(locks), "(%.1fs)" % (time.time() - t0))
        rows, summ = run_audit(bars, eng, locks)
        print("[lines1] audit:", summ)


if __name__ == "__main__":
    main()
