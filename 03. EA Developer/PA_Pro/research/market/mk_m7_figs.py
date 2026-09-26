"""M7 support — figures for MARKET_MECHANICS.md + extra descriptives.

Renders PNGs into research/market/figs/ from the saved JSON results, plus
one extra descriptive pass (daily range distribution for the 60-pip
low-vol parameter).  Read-only w.r.t. upstream artifacts.
"""

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import mk_common as K  # noqa: E402

OUT = K.OUT
FIGS = os.path.join(_HERE, "figs")


def f_rhythm(res):
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
    for s in K.CORE:
        hh = res[s]["halfhour"]
        mins = np.array([e["cet_min"] for e in hh])
        med = np.array([e["abr_med_pips"] for e in hh])
        axes[0].plot(mins / 60, med, label=s, lw=1)
    axes[0].set_title("Median M5 ABR by CET time (pips)")
    axes[0].set_xlabel("CET hour")
    axes[0].legend(fontsize=7)
    for s in K.CORE:
        hh = res[s]["halfhour"]
        mins = np.array([e["cet_min"] for e in hh])
        sp = np.array([e["spike_freq"] for e in hh])
        axes[1].plot(mins / 60, sp, label=s, lw=1)
    axes[1].set_title("P(bar range > 3xABR) by CET time")
    axes[1].set_xlabel("CET hour")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "fig_rhythm.png"), dpi=110)
    plt.close(fig)


def f_levels(m3):
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6))
    # age decay (declared 5 bins, pooled S1+S2 + per-set split)
    mids_h = [1.5, 5.5, 16.0, 48.0, 96.0]
    fa_p = m3["families"]["F-A"]["S12_pooled"]["bins"]
    axes[0].plot(mids_h, [b["res"]["pooled"]["D"] for b in fa_p],
                 "o-", label="S1+S2 pooled", lw=1.5)
    for name, mk in (("S1", "o"), ("S2", "s")):
        fa = m3["families"]["F-A"][f"{name}_desc"]
        ys = [b["res"]["pooled"]["D"] for b in fa]
        axes[0].plot(mids_h, ys, mk + "--", label=name, ms=4, lw=0.8)
    axes[0].set_xscale("log")
    axes[0].set_title("Level bounce premium vs age")
    axes[0].set_xlabel("level age (hours, log)")
    axes[0].set_ylabel("D (P bounce - placebo)")
    axes[0].axhline(0, color="k", lw=0.5)
    axes[0].legend(fontsize=7)
    # touch ordinal (pooled formal + per-set desc)
    ft = m3["families"]["F-T"]
    x1 = [c["res"]["pooled"]["D"] for c in ft["pooled"] if c["x"] == 1]
    axes[1].plot([1, 2, 3], x1, "o-", label="pooled (formal)", lw=1.5)
    for name in ("S1", "S2"):
        ys = [c["res"]["pooled"]["D"] for c in ft[f"{name}_desc"]]
        axes[1].plot([1, 2, 3], ys, "o--", label=name, ms=4, lw=0.8)
    axes[1].set_xticks([1, 2, 3])
    axes[1].set_xticklabels(["1st", "2nd", "3rd+"])
    axes[1].set_title("Bounce premium by touch ordinal (x1)")
    axes[1].axhline(0, color="k", lw=0.5)
    axes[1].legend(fontsize=7)
    # overshoot quantiles
    desc = m3["families"]["F-O"]["desc_pips"]
    names = ["S1", "S2", "PDHPDL", "ASIA", "RND", "PRAND"]
    p50 = [desc[n]["ALL(ABR)"]["p50"] for n in names]
    p90 = [desc[n]["ALL(ABR)"]["p90"] for n in names]
    x = np.arange(len(names))
    axes[2].bar(x - 0.2, p50, width=0.4, label="p50")
    axes[2].bar(x + 0.2, p90, width=0.4, label="p90")
    axes[2].set_xticks(x); axes[2].set_xticklabels(names, fontsize=7)
    axes[2].set_title("Overshoot beyond zone (ABR)")
    axes[2].legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "fig_levels.png"), dpi=110)
    plt.close(fig)


def f_boxes(m4):
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.6))
    ffb = m4["families"]["F-FB"]
    lbls = ["(0,1]", "(1,2]", "(2,3]", "(3,5]"]
    deps = [0.5, 1.5, 2.5, 4.0]
    D = [ffb[k]["pooled"]["D"] for k in lbls]
    lo = [ffb[k]["pooled"]["lo"] for k in lbls]
    hi = [ffb[k]["pooled"]["hi"] for k in lbls]
    axes[0].errorbar(deps, D, yerr=[np.array(D) - np.array(lo),
                                    np.array(hi) - np.array(D)],
                     fmt="o-")
    axes[0].set_title("Failed poke -> reach opposite edge (D vs placebo)")
    axes[0].set_xlabel("poke depth (pips, bin centres)")
    axes[0].axhline(0, color="k", lw=0.5)
    fbo = m4["families"]["F-BO"]
    Hs = [6, 12, 24, 48]
    D = [fbo[f"fwd{h}_desc"]["pooled"]["D"] for h in Hs]
    axes[1].plot(Hs, D, "o-")
    r = fbo["race24"]["pooled"]
    axes[1].axhline(0, color="k", lw=0.5)
    axes[1].set_title(f"Breakout follow-through (desc) | race24 D="
                      f"{r['D']:+.3f} p={r.get('p', float('nan')):.3f}")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "fig_boxes.png"), dpi=110)
    plt.close(fig)


def f_lines(m5, m6):
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.6))
    ftl = m5["families"]["F-TL"]
    ks = ["x1_t3", "x2_t3", "x1_all_desc", "x2_all_desc"]
    D = [ftl[k]["pooled"]["D"] for k in ks]
    lo = [ftl[k]["pooled"].get("lo", np.nan) for k in ks]
    hi = [ftl[k]["pooled"].get("hi", np.nan) for k in ks]
    lo = [d if np.isfinite(d) else D[i] for i, d in enumerate(lo)]
    hi = [d if np.isfinite(d) else D[i] for i, d in enumerate(hi)]
    axes[0].bar(range(4), D, yerr=[np.array(D) - np.array(lo),
                                   np.array(hi) - np.array(D)])
    axes[0].set_xticks(range(4))
    axes[0].set_xticklabels(["x1 3rd", "x2 3rd", "x1 all", "x2 all"],
                            fontsize=7)
    axes[0].set_title("Line touch: D = P(bounce|real) - P(bounce|plac)")
    axes[0].axhline(0, color="k", lw=0.5)
    em = m6["symbols"]["EURUSD"]["ema_near"]
    lens = [15, 20, 25, 35, 50]
    for xb, mk in (("p25", "o"), ("p50", "s"), ("p100", "^")):
        axes[1].plot(lens, [em[str(L)][xb] for L in lens],
                     mk + "-", label=f"P(|d|<= {float(xb[1:]) / 100} ABR)")
    axes[1].set_title("EURUSD: pullbacks stopping near EMA-L")
    axes[1].set_xlabel("EMA length")
    axes[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "fig_lines_ema.png"), dpi=110)
    plt.close(fig)


def daily_ranges():
    """DESIGN daily range (server day) in pips — feeds low-vol param."""
    out = {}
    for sym in K.CORE:
        dd = K.load_symbol(sym)
        m5 = dd["m5"]
        h = np.asarray(m5["h"]); l = np.asarray(m5["l"])
        day = K.day_id(m5)
        warm = np.asarray(m5["warmup"], dtype=bool)
        pip = float(m5["pip"])
        dr = {}
        for d in np.unique(day[~warm]):
            m = (day == d) & ~warm
            if m.sum() < 100:
                continue
            dr[d] = (h[m].max() - l[m].min()) / pip
        v = np.array(list(dr.values()))
        out[sym] = {"n": len(v), "p10": float(np.quantile(v, 0.10)),
                    "p25": float(np.quantile(v, 0.25)),
                    "p50": float(np.quantile(v, 0.50)),
                    "p75": float(np.quantile(v, 0.75)),
                    "share_le_60": float((v <= 60).mean())}
        del dd
    return out


def main():
    os.makedirs(FIGS, exist_ok=True)
    rhythm = json.load(open(os.path.join(OUT, "rhythm.json")))
    m3 = json.load(open(os.path.join(OUT, "m3_results.json")))
    m4 = json.load(open(os.path.join(OUT, "m4_results.json")))
    m5 = json.load(open(os.path.join(OUT, "m5_results.json")))
    m6 = json.load(open(os.path.join(OUT, "m6_results.json")))
    f_rhythm(rhythm)
    f_levels(m3)
    f_boxes(m4)
    f_lines(m5, m6)
    dr = daily_ranges()
    K.write_json("m7_daily_range.json", dr)
    print("[M7] figs + daily ranges done", flush=True)


if __name__ == "__main__":
    main()
