"""M5 analysis: trend lines vs declared placebo lines.

Reads out/m5_events_<SYM>.npz (post-review extraction: placebo = 2
price-shifted copies of each real line sharing anchor times and slope,
scanned by the same touch machinery -> exchangeable).

  F-TL    D[P_rev] at the declared "third touch" (touch_no==1), x in
          {1,2} — TOUCH vs TPLAC, strata + slope class in the key.
          All-touch contrast kept descriptive.
  F-SLOPE declared class-vs-class tests: P(continuation >=1 ABR before
          reversal >=1 ABR within 24 bars) = cont24, rising vs
          (flat|falling) slope class, separately for up-breaks and
          down-breaks (real-vs-real, same contrast engine).  Per-class
          real-vs-BPLAC contrasts stay descriptive.
"""

import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import mk_common as K  # noqa: E402
from mk_m3_analyze import SYM_I, YEARS, _yr, run_contrast, _fmt, _stab  # noqa

OUT = K.OUT
FLAT_EPS = 0.02
SETS = ["TOUCH", "TPLAC", "BREAK", "BPLAC"]


def load_all():
    ev = {}
    for sym in K.CORE:
        z = np.load(os.path.join(OUT, f"m5_events_{sym}.npz"))
        ev[sym] = {}
        for name in SETS:
            d = {}
            for k in z.files:
                if k.startswith(name + "__"):
                    d[k.split("__", 1)[1]] = z[k]
            if d:
                ev[sym][name] = d
    return ev


def edges_per_sym(ev):
    out = {}
    for s in K.CORE:
        abr = np.concatenate([ev[s][n]["abr"] for n in SETS
                              if n in ev[s] and len(ev[s][n].get("day", []))])
        app = np.concatenate([ev[s][n]["approach_atr"] for n in SETS
                              if n in ev[s] and len(ev[s][n].get("day", []))])
        abr = abr[np.isfinite(abr) & (abr > 0)]
        app = app[np.isfinite(app)]
        qa = np.quantile(abr, [0.0, 1 / 3, 2 / 3, 1.0])
        qp = np.quantile(app, np.linspace(0.0, 1.0, 11)) if len(app) \
            else np.zeros(11)
        out[s] = (qa, qp)
    return out


def slope_cls_arr(s):
    s = np.asarray(s, dtype=np.float64)
    out = np.zeros(len(s), dtype=np.int64)
    out[np.isfinite(s) & (s > FLAT_EPS)] = 1
    out[np.isfinite(s) & (s < -FLAT_EPS)] = 2
    return out


def key_ints(d, sym, qa, qp, slope_in_key=False):
    side01 = ((d["side"] + 1) / 2).astype(np.int64)
    dow = d["dow"].astype(np.int64)
    bucket = (d["utc_min"] // 240).astype(np.int64)
    ter = np.clip(np.searchsorted(qa, d["abr"], side="right") - 1, 0, 2)
    app = d["approach_atr"]
    dec = np.where(np.isfinite(app),
                   np.clip(np.searchsorted(qp, app, side="right") - 1, 0, 9),
                   10)
    si = np.full(len(dow), SYM_I[sym], dtype=np.int64)
    k = (side01 + 2 * (dow + 7 * (bucket + 6 * (ter + 3 * (dec + 11 * si))))
         ).astype(np.int64)
    if slope_in_key:
        k = k * 3 + slope_cls_arr(d["slope_abr"])
    return k


def build_cm(ev, rname, pname, val_fn, mask_r=None, mask_p=None,
             edges=None, slope_in_key=False):
    rd, rk, rv, pd_, pk, pv = [], [], [], [], [], []
    for sym in K.CORE:
        qa, qp = edges[sym]
        r = ev[sym][rname]; p = ev[sym][pname]
        mr = np.ones(len(r["day"]), bool) if mask_r is None else mask_r(r)
        mp = np.ones(len(p["day"]), bool) if mask_p is None else mask_p(p)
        rd.append(r["day"][mr])
        rk.append(key_ints(r, sym, qa, qp, slope_in_key)[mr])
        rv.append(val_fn(r, sym)[mr])
        pd_.append(p["day"][mp])
        pk.append(key_ints(p, sym, qa, qp, slope_in_key)[mp])
        pv.append(val_fn(p, sym)[mp])
    rd = np.concatenate(rd); rk = np.concatenate(rk); rv = np.concatenate(rv)
    pd_ = np.concatenate(pd_); pk = np.concatenate(pk); pv = np.concatenate(pv)
    fr = np.isfinite(rv); fp = np.isfinite(pv)
    return K.contrast_mats_arr(rd[fr], rk[fr], rv[fr],
                               pd_[fp], pk[fp], pv[fp])


def main():
    ev = load_all()
    edges = edges_per_sym(ev)
    res = {"families": {}}
    tests = []

    # ---- F-TL: declared "third touch" = touch_no==1, x in {1,2} --------
    ftl = {}
    t1 = lambda d: d["touch_no"] == 1
    for x in (1, 2):
        cm = build_cm(ev, "TOUCH", "TPLAC",
                      lambda d, s, x=x: (d[f"out_x{x}"] == 0
                                         ).astype(np.float64),
                      mask_r=t1, mask_p=t1, edges=edges,
                      slope_in_key=True)
        r = run_contrast(cm, seed=K.SEED + 2000 + x, sym_factor=8316)
        ftl[f"x{x}_t3"] = r
        tests.append((f"x{x}_t3", r["pooled"]["p"]))
    # descriptive: all touches
    for x in (1, 2):
        cm = build_cm(ev, "TOUCH", "TPLAC",
                      lambda d, s, x=x: (d[f"out_x{x}"] == 0
                                         ).astype(np.float64),
                      edges=edges, slope_in_key=True)
        ftl[f"x{x}_all_desc"] = run_contrast(cm, n_boot_only=True,
                                            sym_factor=8316)
    res["families"]["F-TL"] = ftl
    print("[M5] F-TL done", flush=True)

    # ---- F-SLOPE: declared class-vs-class on cont24 --------------------
    fsl = {}
    rising = lambda d: slope_cls_arr(d["slope_abr"]) == 1
    notris = lambda d: slope_cls_arr(d["slope_abr"]) != 1
    for sd, nm in ((1, "up"), (-1, "down")):
        cm = build_cm(ev, "BREAK", "BREAK",
                      lambda d, s: d["cont24"],
                      mask_r=lambda d, sd=sd: (d["side"] == sd)
                      & rising(d),
                      mask_p=lambda d, sd=sd: (d["side"] == sd)
                      & notris(d),
                      edges=edges)
        r = run_contrast(cm, seed=K.SEED + 2100 + sd)
        fsl[f"rising_vs_rest_{nm}"] = r
        tests.append((f"slope_{nm}", r["pooled"]["p"]))
    # descriptive: per-class real vs BPLAC on cont24 and fwd_48
    for cls, nm in ((1, "rising"), (0, "flat"), (2, "falling")):
        m = lambda d, cls=cls: slope_cls_arr(d["slope_abr"]) == cls
        cm = build_cm(ev, "BREAK", "BPLAC",
                      lambda d, s: d["cont24"],
                      mask_r=m, mask_p=m, edges=edges)
        fsl[f"vsPLAC_{nm}_cont_desc"] = run_contrast(cm, n_boot_only=True)
        cm = build_cm(ev, "BREAK", "BPLAC",
                      lambda d, s: d["fwd_48"] / d["abr"],
                      mask_r=m, mask_p=m, edges=edges)
        fsl[f"vsPLAC_{nm}_fwd_desc"] = run_contrast(cm, n_boot_only=True)
    q, _ = K.bh(np.nan_to_num([t[1] for t in tests], nan=1.0))
    i = 0
    for k in ("x1_t3", "x2_t3"):
        ftl[k]["q"] = float(q[i]); i += 1
    for nm in ("up", "down"):
        fsl[f"rising_vs_rest_{nm}"]["q"] = float(q[i]); i += 1
    res["families"]["F-SLOPE"] = fsl
    print("[M5] F-SLOPE done", flush=True)

    # context
    ctx = {}
    for sym in K.CORE:
        d = ev[sym]["TOUCH"]
        p = ev[sym]["TPLAC"]
        ctx[sym] = {
            "n_touch": int(len(d["day"])),
            "n_tplac": int(len(p["day"])),
            "p_bounce_x1": float((d["out_x1"] == 0).mean()),
            "p_bounce_x1_plac": float((p["out_x1"] == 0).mean()),
            "n_break": int(len(ev[sym]["BREAK"]["day"])),
            "n_bplac": int(len(ev[sym]["BPLAC"]["day"])),
            "share_first": float((d["touch_no"] == 1).mean()),
        }
    res["context"] = ctx
    K.write_json("m5_results.json", res)
    write_report(res)
    print("[M5] analysis done.", flush=True)


def write_report(res):
    L = ["> **FINAL v2 (REVIEW_3 PASS by Lead Ruling 4)**", "",
         "# M5 — Trend lines (DESIGN 2016–2021)", "",
         "Prereg `abc8b5ba…` — post-review revision: placebo = 2 "
         "price-shifted copies of each real line (same anchors/slope, "
         "+/-delta*ABR, delta~U[1.5,4]) scanned by the same machinery "
         "(exchangeable).  Strata side x dow x 4h x ABR-tercile x "
         "approach-decile x slope-class x symbol (per-symbol edges).", "",
         "## Context", "", "| sym | touches | plac touches | P(bounce x1) "
         "real | plac | breaks | plac breaks | share first |",
         "|---|---|---|---|---|---|---|---|---|"]
    for s in K.CORE:
        c = res["context"][s]
        L.append(f"| {s} | {c['n_touch']} | {c['n_tplac']} | "
                 f"{c['p_bounce_x1']:.3f} | {c['p_bounce_x1_plac']:.3f} | "
                 f"{c['n_break']} | {c['n_bplac']} | {c['share_first']:.3f} |")
    L += ["", "## F-TL — D = P(bounce|real line) - P(bounce|placebo line) "
          "at the third touch", "", "| test | D | CI | p | q | stable |",
          "|---|---|---|---|---|---|"]
    for k, r in res["families"]["F-TL"].items():
        p = r["pooled"]
        L.append(f"| {k} | {_fmt(p['D'])} | {_fmt(p['lo'])}–{_fmt(p['hi'])} "
                 f"| {_fmt(p['p'])} | {_fmt(r.get('q'))} | "
                 f"{_stab(r)} |")
    L += ["", "## F-SLOPE — cont24 after break: rising vs (flat|falling), "
          "real-vs-real", "", "| test | D | CI | p | q | stable |",
          "|---|---|---|---|---|---|"]
    for k in ("rising_vs_rest_up", "rising_vs_rest_down"):
        r = res["families"]["F-SLOPE"][k]
        p = r["pooled"]
        L.append(f"| {k} | {_fmt(p['D'])} | {_fmt(p['lo'])}–{_fmt(p['hi'])} "
                 f"| {_fmt(p['p'])} | {_fmt(r.get('q'))} | "
                 f"{_stab(r)} |")
    L += ["", "descriptive — per-class real vs placebo lines "
          "(D, no q):", "", "| class | cont24 | fwd_48 (ABR) |",
          "|---|---|---|"]
    for nm in ("rising", "flat", "falling"):
        r1 = res["families"]["F-SLOPE"].get(f"vsPLAC_{nm}_cont_desc")
        r2 = res["families"]["F-SLOPE"].get(f"vsPLAC_{nm}_fwd_desc")
        L.append(f"| {nm} | {_fmt(r1['pooled']['D'] if r1 else None)} | "
                 f"{_fmt(r2['pooled']['D'] if r2 else None)} |")
    path = os.path.join(_HERE, "LINES.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"[M5] wrote {path}", flush=True)


if __name__ == "__main__":
    main()
