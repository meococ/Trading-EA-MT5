"""runner.py — render the SHORTLIST zone generators on the FROZEN 8 windows.

Reads `research/zones/WINDOWS.json` (fixed seed 20260920, chosen before any
picture existed) and, for every registered generator:

- plots the 120 M5 bars ENDING at the decision bar (no bar after it is drawn
  or used anywhere in this file);
- draws every ARMED zone at the decision bar as a SHADED BAND with opacity
  proportional to strength v0; a zone's band steps follow its causal geometry
  history (`Zone.geom_hist`), clipped to the window;
- marks the current close;
- writes `research/zones/snapshots/<generator>/win_<i>_<UTC>.png` plus
  `research/zones/snapshots/INDEX.csv` (counts only).

NO OUTCOMES: no bounce/break counts, no returns, no forward bars are read
after the decision bar.  Heavy run: goes through `lib/pa_slots.py`.
"""

import csv
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PA_PRO = os.path.dirname(os.path.dirname(HERE))
for _p in (HERE, os.path.join(PA_PRO, "lib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

import pa_slots  # noqa: E402
from data_helpers import load_ctx  # noqa: E402

WINDOWS_JSON = os.path.join(PA_PRO, "research", "zones", "WINDOWS.json")
SNAP_ROOT = os.path.join(PA_PRO, "research", "zones", "snapshots")
INDEX_CSV = os.path.join(SNAP_ROOT, "INDEX.csv")

KIND_COLOR = {
    "swing": "#0F766E", "swing_h1": "#4338CA", "density": "#7C3AED",
    "profile_poc": "#EA580C", "demand": "#16A34A", "supply": "#DC2626",
    "pdh": "#CA8A04", "pdl": "#CA8A04", "pdc": "#B45309",
    "asia_hi": "#0891B2", "asia_lo": "#0891B2",
    "wk_hi": "#2563EB", "wk_lo": "#2563EB", "round": "#4B5563",
}


def draw_candles(ax, bars, i0, i1, base):
    """Thin OHLC bars for the window (x = window-relative bar index)."""
    for k in range(i0, i1 + 1):
        x = k - i0
        o, h, l, c = bars["o"][k], bars["h"][k], bars["l"][k], bars["c"][k]
        ax.plot([x, x], [l, h], color="#374151", lw=0.7, zorder=3)
        up = c >= o
        ax.add_patch(Rectangle((x - 0.32, min(o, c)), 0.64, abs(c - o),
                               facecolor="#FAFAFA" if up else "#111827",
                               edgecolor="#374151", lw=0.5, zorder=4))


def draw_zone_steps(ax, zone, t, i0, i1, color, alpha, dashed=False):
    """Draw a zone band over the window following its causal geometry steps."""
    steps = list(zip(zone.geom_idx, zone.geom_hist))
    for s in range(len(steps)):
        idx, (lo, hi) = steps[s]
        nxt = steps[s + 1][0] if s + 1 < len(steps) else t + 1
        xa = max(idx, i0)
        xb = min(nxt - 1, t)
        if xb < xa:
            continue
        ax.add_patch(Rectangle(
            (xa - i0 - 0.5, lo), (xb - xa) + 1.0, hi - lo,
            facecolor="none" if dashed else color,
            edgecolor=color, alpha=alpha, lw=0.5 if dashed else 0.4,
            ls=":" if dashed else "-", zorder=2 if not dashed else 1))


def main():
    with open(WINDOWS_JSON, "r", encoding="utf-8") as f:
        wins = json.load(f)
    window_bars = int(wins["window_bars"])
    ctx = load_ctx(wins["symbol"])
    bars = ctx.bars
    import registry

    os.makedirs(SNAP_ROOT, exist_ok=True)
    rows = []
    t0all = time.time()
    for name, cls in registry.import_registry():
        t0 = time.time()
        g = cls(ctx).run()
        run_s = time.time() - t0
        outdir = os.path.join(SNAP_ROOT, name)
        os.makedirs(outdir, exist_ok=True)
        by_zid = {z.zid: z for z in g._zones}
        for w in wins["windows"]:
            t = int(w["bar_idx"])
            i0 = t - window_bars + 1
            views = g.views_at(t, arm=True)
            live = g.views_at(t, arm=False)
            armed_ids = {v.zid for v in views}
            utc = w["utc_close"].replace(":", "").replace("-", "")[:13]
            fname = f"win_{w['window_id']}_{utc}.png"
            fpath = os.path.join(outdir, fname)
            fig, ax = plt.subplots(figsize=(13.0, 6.2), dpi=110)
            draw_candles(ax, bars, i0, t, None)
            for v in live:
                if v.zid in armed_ids:
                    continue
                z = by_zid.get(v.zid)
                color = KIND_COLOR.get(v.kind, "#111827")
                if z is not None:
                    draw_zone_steps(ax, z, t, i0, t, color, 0.55, dashed=True)
                xa = max(z.born_idx if z is not None else i0, i0) - i0
                ax.text(xa, v.hi, f"{v.kind} {v.strength:.2f} (live)",
                        fontsize=5.5, color="#6B7280", va="bottom", zorder=6)
            for v in views:
                color = KIND_COLOR.get(v.kind, "#111827")
                alpha = 0.10 + 0.55 * float(v.strength)
                z = by_zid.get(v.zid)
                if z is not None:
                    draw_zone_steps(ax, z, t, i0, t, color, alpha)
                xa = max(z.born_idx if z is not None else i0, i0) - i0
                ax.text(xa, v.hi, f"{v.kind} {v.strength:.2f}",
                        fontsize=6.0, color=color, va="bottom", zorder=6)
            close = float(bars["c"][t])
            ax.axhline(close, color="#B91C1C", lw=0.9, ls=":", zorder=5)
            ax.plot([window_bars - 1], [close], marker="o", ms=4,
                    color="#B91C1C", zorder=7)
            ax.annotate(f"close {close:.5f}", xy=(window_bars - 1, close),
                        xytext=(-64, 9), textcoords="offset points",
                        fontsize=7, color="#B91C1C")
            A = ctx.a(t)
            b_lo = float(bars["l"][i0:t + 1].min())
            b_hi = float(bars["h"][i0:t + 1].max())
            cand = [v for v in views
                    if v.lo <= b_hi + 4 * A and v.hi >= b_lo - 4 * A]
            cand += [v for v in live if v.zid not in armed_ids
                     and v.lo <= b_hi + 4 * A and v.hi >= b_lo - 4 * A]
            lo = min([b_lo] + [v.lo for v in cand])
            hi = max([b_hi] + [v.hi for v in cand])
            pad = 0.12 * (hi - lo)
            ax.set_ylim(lo - pad, hi + pad)
            ax.set_xlim(-1, window_bars)
            A = ctx.a(t)
            ax.set_title(
                f"{name} | window {w['window_id']} | close {w['utc_close']} UTC | "
                f"armed {len(views)} of {len(live)} live | "
                f"ATR14(H1) {A:.5f} | run {run_s:.1f}s", fontsize=9)
            ax.set_xlabel("M5 bars (120 bars ending at the decision bar; no future bars)",
                          fontsize=8)
            ax.grid(True, color="#E5E7EB", lw=0.4, zorder=0)
            ax.tick_params(labelsize=7)
            fig.tight_layout()
            fig.savefig(fpath)
            plt.close(fig)
            A = ctx.a(t)
            rows.append({
                "generator": name, "window_id": w["window_id"],
                "bar_idx": t, "utc_close": w["utc_close"],
                "close": f"{close:.5f}", "atr_h1": f"{A:.5f}",
                "n_live": len(live), "n_armed": len(views),
                "width_atr_med": f"{np.median([v.hi - v.lo for v in views]) / A:.3f}"
                if views else "",
                "file": os.path.relpath(fpath, SNAP_ROOT).replace("\\", "/"),
            })
        print(f"{name}: {len(g._zones)} zones, run {run_s:.1f}s, "
              f"{len(wins['windows'])} snapshots")
    with open(INDEX_CSV, "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)
    print(f"wrote {INDEX_CSV} ({len(rows)} rows); total {time.time() - t0all:.1f}s")


if __name__ == "__main__":
    with pa_slots.slot("zone1_snapshots", timeout=900):
        main()
