"""M4 analysis: boxes & breakouts vs the declared P-RAND fake-edge placebo.

Reads out/m4_events_<SYM>.npz (post-review extraction: declared §5
detector + fake-edge placebo).  Contrast machinery identical to M3
(matched strata = side x dow x 4h-bucket x ABR-tercile x symbol; F-FB
adds a height tercile so traversal distance is conditioned; joint
day-block bootstrap; BH-FDR q=0.10; stability = same sign >=4/6 years
and >=3/4 symbols).

Families (plan §5, family size 6):
  F-BO  (1) race24: P(>=1 ABR beyond edge before >=1 ABR back through,
        <=24 bars) real vs placebo breaks;
        (2) buildup (a)-(b) difference on race24 within real breaks.
        fwd_H and MFE stay descriptive.
  F-FB  (3-6) false breaks: P(reach opposite edge <=24 bars) in disjoint
        poke-depth bins (0,1],(1,2],(2,3],(3,5] pips vs placebo pokes.
  F-BX  descriptive: box height & lifetime by session; poke depth dist.
"""

import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import mk_common as K  # noqa: E402
from mk_m3_analyze import (SYM_I, YEARS, PIP, _yr, run_contrast, _fmt,
                           _stab)  # noqa

OUT = K.OUT
SETS = ["BREAK", "POKE", "PPK", "PBRK"]
SESS = {0: "ASIA", 1: "EU", 2: "US", 3: "LATE"}
DEPTH_BINS = [(0.0, 1.0), (1.0, 2.0), (2.0, 3.0), (3.0, 5.0)]
DEPTH_LBL = ["(0,1]", "(1,2]", "(2,3]", "(3,5]"]


def load_all():
    ev = {}
    for sym in K.CORE:
        z = np.load(os.path.join(OUT, f"m4_events_{sym}.npz"))
        ev[sym] = {}
        for name in SETS:
            d = {}
            for k in z.files:
                if k.startswith(name + "__"):
                    d[k.split("__", 1)[1]] = z[k]
            if d:
                ev[sym][name] = d
        for extra in ("BOX__session", "BOX__h_pips", "BOX__born"):
            if extra in z:
                ev[sym].setdefault("BOX", {})[extra.split("__")[1]] = \
                    z[extra]
        # real poke height in ABR (from box height in pips)
        if "POKE" in ev[sym] and len(ev[sym]["POKE"].get("day", [])):
            p = ev[sym]["POKE"]
            p["hgt_abr"] = p["box_h_pips"] * PIP[sym] / p["abr"]
        for n in ("POKE", "PPK"):
            if n in ev[sym] and len(ev[sym][n].get("day", [])):
                ev[sym][n]["depth_pips"] = ev[sym][n]["depth"] / PIP[sym]
    return ev


def edges_per_sym(ev):
    out = {}
    for s in K.CORE:
        abr = np.concatenate([ev[s][n]["abr"] for n in SETS
                              if n in ev[s] and len(ev[s][n].get("day", []))])
        abr = abr[np.isfinite(abr) & (abr > 0)]
        qa = np.quantile(abr, [0.0, 1 / 3, 2 / 3, 1.0])
        hg = np.concatenate([ev[s][n]["hgt_abr"] for n in ("POKE", "PPK")
                             if n in ev[s] and "hgt_abr" in ev[s][n]])
        hg = hg[np.isfinite(hg) & (hg > 0)]
        qh = np.quantile(hg, [0.0, 1 / 3, 2 / 3, 1.0]) if len(hg) \
            else np.zeros(4)
        out[s] = (qa, qh)
    return out


def key_ints(d, sym, qa, qh=None):
    side01 = ((d["side"] + 1) / 2).astype(np.int64)
    dow = d["dow"].astype(np.int64)
    bucket = (d["utc_min"] // 240).astype(np.int64)
    ter = np.clip(np.searchsorted(qa, d["abr"], side="right") - 1, 0, 2)
    si = np.full(len(dow), SYM_I[sym], dtype=np.int64)
    k = (side01 + 2 * (dow + 7 * (bucket + 6 * (ter + 3 * si)))
         ).astype(np.int64)
    if qh is not None and "hgt_abr" in d:
        ht = np.clip(np.searchsorted(qh, d["hgt_abr"], side="right") - 1,
                     0, 2)
        k = k * 3 + ht
    return k


def build_cm(ev, rname, pname, val_fn, mask_r=None, mask_p=None,
             edges=None, hgt_key=False):
    rd, rk, rv, pd_, pk, pv = [], [], [], [], [], []
    for sym in K.CORE:
        qa, qh = edges[sym]
        r = ev[sym][rname]; p = ev[sym][pname]
        mr = np.ones(len(r["day"]), bool) if mask_r is None else mask_r(r)
        mp = np.ones(len(p["day"]), bool) if mask_p is None else mask_p(p)
        rd.append(r["day"][mr])
        rk.append(key_ints(r, sym, qa, qh if hgt_key else None)[mr])
        rv.append(val_fn(r, sym)[mr])
        pd_.append(p["day"][mp])
        pk.append(key_ints(p, sym, qa, qh if hgt_key else None)[mp])
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

    # ---- F-BO (1): race24 real vs placebo breaks ----------------------
    fbo = {}
    cm = build_cm(ev, "BREAK", "PBRK",
                  lambda d, s: d["race24"], edges=edges)
    r = run_contrast(cm, seed=K.SEED + 1000, sym_factor=252)
    fbo["race24"] = r
    tests.append(("race24", r["pooled"]["p"]))
    # (2) buildup (a) - (b): real-vs-real contrast on race24
    cm = build_cm(ev, "BREAK", "BREAK", lambda d, s: d["race24"],
                  mask_r=lambda d: d["buildup"] == 1,
                  mask_p=lambda d: d["buildup"] == 0, edges=edges)
    r = run_contrast(cm, seed=K.SEED + 1010, sym_factor=252)
    fbo["buildup_minus_none"] = r
    tests.append(("buildup_ab", r["pooled"]["p"]))
    # descriptive: fwd drift + MFE vs placebo
    for H in K.HORIZONS:
        cm = build_cm(ev, "BREAK", "PBRK",
                      lambda d, s, H=H: d[f"fwd_{H}"] / d["abr"],
                      edges=edges)
        fbo[f"fwd{H}_desc"] = run_contrast(cm, n_boot_only=True, sym_factor=252)
    cm = build_cm(ev, "BREAK", "PBRK", lambda d, s: d["mfe24"],
                  edges=edges)
    fbo["mfe24_desc"] = run_contrast(cm, n_boot_only=True, sym_factor=252)
    res["families"]["F-BO"] = fbo
    print("[M4] F-BO done", flush=True)

    # ---- F-FB (3-6): failed pokes reach the opposite edge -------------
    ffb = {}
    for bi, (a0, a1) in enumerate(DEPTH_BINS):
        def mr(d, a0=a0, a1=a1):
            dp = d["depth_pips"]
            return (dp > a0) & (dp <= a1)
        cm = build_cm(ev, "POKE", "PPK",
                      lambda d, s: d["reach_opp"],
                      mask_r=mr, mask_p=mr, edges=edges, hgt_key=True)
        r = run_contrast(cm, seed=K.SEED + 1100 + bi, sym_factor=756)
        ffb[DEPTH_LBL[bi]] = r
        tests.append((f"fb{DEPTH_LBL[bi]}", r["pooled"]["p"]))
    res["families"]["F-FB"] = ffb
    print("[M4] F-FB done", flush=True)

    q, _ = K.bh(np.nan_to_num([t[1] for t in tests], nan=1.0))
    fbo["race24"]["q"] = float(q[0])
    fbo["buildup_minus_none"]["q"] = float(q[1])
    for i, lbl in enumerate(DEPTH_LBL):
        ffb[lbl]["q"] = float(q[2 + i])

    # ---- F-BX descriptive ----------------------------------------------
    fbx = {}
    for sym in K.CORE:
        bx = ev[sym].get("BOX", {})
        hh = bx.get("h_pips", np.array([]))
        ss = bx.get("session", np.array([]))
        per = {}
        for code, nm in SESS.items():
            v = hh[ss == code]
            if len(v):
                per[nm] = {"n": int(len(v)),
                           "h_med": float(np.median(v)),
                           "h_p25": float(np.quantile(v, 0.25)),
                           "h_p75": float(np.quantile(v, 0.75))}
        pk = ev[sym]["POKE"]
        dp = pk["depth"] / PIP[sym] if len(pk.get("day", [])) \
            else np.array([])
        fbx[sym] = {"n_boxes": int(len(hh)),
                    "h_med": float(np.median(hh)) if len(hh) else np.nan,
                    "h_p25": float(np.quantile(hh, 0.25)) if len(hh)
                    else np.nan,
                    "h_p75": float(np.quantile(hh, 0.75)) if len(hh)
                    else np.nan,
                    "by_session": per,
                    "n_pokes": int(len(dp)),
                    "depth_p50": float(np.median(dp)) if len(dp)
                    else np.nan,
                    "p_conv": float(np.nanmean(pk["converted"]))
                    if len(dp) else np.nan,
                    "p_reach_opp": float(np.nanmean(pk["reach_opp"]))
                    if len(dp) else np.nan}
        br = ev[sym]["BREAK"]
        if len(br["day"]):
            fbx[sym]["life_med_bars"] = float(np.median(br["box_age"]))
            fbx[sym]["life_p75_bars"] = float(np.quantile(br["box_age"],
                                                          0.75))
            fbx[sym]["n_breaks"] = int(len(br["day"]))
            fbx[sym]["p_buildup"] = float(np.nanmean(br["buildup"]))
        fbx[sym]["n_ppk"] = int(len(ev[sym].get("PPK", {}).get("day", [])))
        fbx[sym]["n_pbrk"] = int(len(ev[sym].get("PBRK", {})
                                     .get("day", [])))
    res["families"]["F-BX"] = fbx
    print("[M4] F-BX done", flush=True)

    K.write_json("m4_results.json", res)
    write_report(res)
    print("[M4] analysis done.", flush=True)


def write_report(res):
    L = ["> **FINAL v2 (REVIEW_3 PASS by Lead Ruling 4)**", "",
         "# M4 — Boxes and breakouts (DESIGN 2016–2021)",
         "",
         "Prereg `abc8b5ba…` — post-review revision: detector is the "
         "declared §5 one (W=30, height 1.5–6 ABR, interleaved touches, "
         "span>=9, 100-bar death); placebo = declared P-RAND fake edges "
         "(24 same-day uniform prices from the M3 PRAND pool, touched "
         ">=2x in trailing-30 — sparse; see D22).  D = matched-strata "
         "contrast; day-block bootstrap B=2000; BH q=0.10; stability "
         "4/6y + 3/4s.",
         "",
         "## F-BX — descriptive (pooled symbols)",
         "",
         "| sym | boxes | h p25/50/75 (pips) | life p50/p75 (bars) | "
         "breaks | P(buildup) | pokes | depth p50 | P(conv<=3b) | "
         "P(opp<=24b) | plac pk/bk |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in K.CORE:
        d = res["families"]["F-BX"][s]
        L.append(f"| {s} | {d['n_boxes']} | {_fmt(d['h_p25'],1)}/"
                 f"{_fmt(d['h_med'],1)}/{_fmt(d['h_p75'],1)} | "
                 f"{_fmt(d.get('life_med_bars'),0)}/"
                 f"{_fmt(d.get('life_p75_bars'),0)} | "
                 f"{d.get('n_breaks', 0)} | {_fmt(d.get('p_buildup'),3)} | "
                 f"{d['n_pokes']} | {_fmt(d['depth_p50'],1)} | "
                 f"{_fmt(d['p_conv'],3)} | {_fmt(d['p_reach_opp'],3)} | "
                 f"{d['n_ppk']}/{d['n_pbrk']} |")
    L += ["", "### box height by session (median pips, n)", "",
          "| sym | ASIA | EU | US | LATE |", "|---|---|---|---|---|---|"]
    for s in K.CORE:
        per = res["families"]["F-BX"][s]["by_session"]
        cells = " | ".join(
            f"{_fmt(per[nm]['h_med'],1)} ({per[nm]['n']})"
            if nm in per else "-" for nm in ("ASIA", "EU", "US", "LATE"))
        L.append(f"| {s} | {cells} |")

    L += ["", "## F-BO — breakout follow-through (declared: race24, "
          "y=1 ABR, H=24)", "", "| test | D | CI | p | q | stable |",
          "|---|---|---|---|---|---|"]
    for k in ("race24", "buildup_minus_none"):
        r = res["families"]["F-BO"][k]
        p = r["pooled"]
        L.append(f"| {k} | {_fmt(p['D'])} | {_fmt(p['lo'])}–{_fmt(p['hi'])} "
                 f"| {_fmt(p['p'])} | {_fmt(r.get('q'))} | "
                 f"{_stab(r)} |")
    L += ["", "descriptive (no q):", "", "| metric | D |",
          "|---|---|"]
    for k, r in res["families"]["F-BO"].items():
        if k.endswith("_desc"):
            L.append(f"| {k} | {_fmt(r['pooled']['D'])} |")

    L += ["", "## F-FB — poke -> reach opposite edge <=24 bars: D vs "
          "fake-edge placebo (height-tercile stratified)", "",
          "WARNING: the declared P-RAND fake edges produce traversal "
          "heights ~0.2 ABR vs real boxes ~5 ABR — the height-tercile "
          "strata barely overlap, so the matched subpopulation is thin "
          "and the D is dominated by the mechanical distance gap.  Treat "
          "as *not identified*; see DEVIATIONS D22.", "",
          "| depth (pips) | D | CI | p | q | n_real | n_plac | stable |",
          "|---|---|---|---|---|---|---|---|"]
    for k, r in res["families"]["F-FB"].items():
        p = r["pooled"]
        L.append(f"| {k} | {_fmt(p['D'])} | {_fmt(p['lo'])}–"
                 f"{_fmt(p['hi'])} | {_fmt(p['p'])} | {_fmt(r.get('q'))} | "
                 f"{p.get('n_real', 0)} | {p.get('n_plac', 0)} | "
                 f"{_stab(r)} |")
    L += ["", "same warning applies to race24 (placebo breaks ~48/symbol):"]
    path = os.path.join(_HERE, "BOXES.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"[M4] wrote {path}", flush=True)


if __name__ == "__main__":
    main()
