"""sf_snap.py — PNG snapshots of detector signals for visual QA.

Draws a candlestick window around each chosen signal: zone bands recorded in
the cache (per-bar, keyed by zid), the signal bar, entry order price, the
pre-fill invalidation level, and the engine SL/TP levels implied by the fill
spec (SL = order_px -/+ S, TP = order_px +/- tp_mult*S).

Usage: python sf_snap.py f1_zone_rejection [--params k=v] [--n 12]
            [--symbols EURUSD,...] [--out DIR]
"""

import importlib
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "lib")
for _p in (HERE, LIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import sf_ctx      # noqa: E402
import pa_costs    # noqa: E402

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
LEFT, RIGHT = 120, 40


def _color(i):
    return plt.cm.tab10(i % 10)


def render(D, sig, e, params, path):
    """Render one signal: window [sig-LEFT, sig+RIGHT]."""
    n = len(D["t"])
    a, b = max(0, sig - LEFT), min(n - 1, sig + RIGHT)
    o, h, l, c = D["o"], D["h"], D["l"], D["c"]
    pip = float(D["pip"])
    S = params["S_pips"] * pip
    tp_d = params["tp_mult"] * S
    side = e["side"]

    fig, ax = plt.subplots(figsize=(14, 7))
    xs = np.arange(a, b + 1)
    for j in xs:
        up = c[j] >= o[j]
        col = "#26a69a" if up else "#ef5350"
        ax.plot([j, j], [l[j], h[j]], color=col, lw=0.7, zorder=2)
        ax.add_patch(Rectangle(
            (j - 0.32, min(o[j], c[j])), 0.64,
            max(abs(c[j] - o[j]), 1e-9),
            facecolor=col, edgecolor=col, zorder=3))
    # zone bands per bar (per zid -> connected segments)
    segs = {}
    for j in xs:
        for z in sf_ctx.zones_at(D, j):
            segs.setdefault(int(z["zid"]), {"x": [], "lo": [], "hi": [],
                                            "armed": False})
            s = segs[int(z["zid"])]
            s["x"].append(j)
            s["lo"].append(z["lo"])
            s["hi"].append(z["hi"])
            s["armed"] = s["armed"] or bool(z["armed"])
    sig_zid = e.get("zid", e.get("tag"))
    for k, (zid, s) in enumerate(sorted(segs.items())):
        col = "#ff9800" if zid == sig_zid else "#90a4ae"
        lw = 2.2 if zid == sig_zid else 1.0
        al = 0.95 if zid == sig_zid else 0.5
        ax.fill_between(s["x"], s["lo"], s["hi"], color=col, alpha=0.18,
                        zorder=1)
        ax.plot(s["x"], s["lo"], color=col, lw=lw, alpha=al, zorder=4)
        ax.plot(s["x"], s["hi"], color=col, lw=lw, alpha=al, zorder=4)
    # signal bar + order levels
    ax.axvline(sig, color="#1e88e5", lw=1.2, ls="--", zorder=5)
    x0, x1 = sig, b
    op = e["order_px"]
    ax.hlines(op, x0, x1, color="#1e88e5", lw=1.6, ls="-",
              label="order_px", zorder=6)
    if e.get("inv") is not None:
        ax.hlines(e["inv"], x0, x1, color="#8e24aa", lw=1.2, ls=":",
                  label="inv", zorder=6)
    ax.hlines(op - side * S, x0, x1, color="#e53935", lw=1.6, ls="-",
              label="SL", zorder=6)
    ax.hlines(op + side * tp_d, x0, x1, color="#43a047", lw=1.6, ls="-",
              label="TP", zorder=6)
    ttl = (f"{D['symbol']} {params.get('gen')} sig={sig} "
           f"side={side:+d} zid={sig_zid}")
    ax.set_title(ttl)
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def pick_signals(entries, n_pick=12):
    """Deterministic spread of signals across the sample."""
    if len(entries) <= n_pick:
        return list(range(len(entries)))
    idx = np.linspace(0, len(entries) - 1, n_pick).round().astype(int)
    return sorted(set(idx.tolist()))


def run(fam, params=None, n_pick=12, symbols=SYMBOLS, out_dir=None):
    params = params or {}
    mod = importlib.import_module(fam)
    gen = params.get("gen", mod.DEFAULTS.get("gen", "line1_cluster"))
    per = max(1, n_pick // len(symbols))
    for sym in symbols:
        if hasattr(mod, "_load"):
            D = mod._load(sym) if "gen" not in params else \
                sf_ctx.load_cache(sym, gen)
        else:
            D = sf_ctx.load_cache(sym, gen)
        ent = mod.detect(D, pa_costs.C_RT_P90[sym], params)
        picks = pick_signals(ent, per)
        odir = out_dir or os.path.join(
            os.path.dirname(HERE), "rounds", "SF01", fam, "snapshots")
        os.makedirs(odir, exist_ok=True)
        for i, ei in enumerate(picks):
            e = ent[ei]
            path = os.path.join(odir, f"{sym}_{i:02d}_sig{e['sig']}.png")
            render(D, e["sig"], e, {**mod.DEFAULTS, **params}, path)
            print("wrote", path)


if __name__ == "__main__":
    fam = sys.argv[1] if len(sys.argv) > 1 else "f1_zone_rejection"
    kw = {}
    for a in sys.argv[2:]:
        if a.startswith("--params="):
            for kv in a.split("=", 1)[1].split(","):
                k, v = kv.split("=", 1)
                try:
                    v = int(v)
                except ValueError:
                    try:
                        v = float(v)
                    except ValueError:
                        pass
                kw[k] = v
        elif a.startswith("--n="):
            kw["n_pick"] = int(a.split("=", 1)[1])
    run(fam, params={k: v for k, v in kw.items() if k != "n_pick"},
        n_pick=kw.get("n_pick", 12))
