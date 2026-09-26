"""M4b analysis — F-Xb: real box events vs P-SHIFT placebo
(STUDY_PLAN_ADDENDUM_M4B.md, prereg T000392).

Real BREAK/POKE come from out/m4_events_<SYM>.npz; placebo SPK/SBRK
from out/m4b_events_<SYM>.npz.  Same strata + machinery as M4.
Family F-Xb (5 tests, BH q=0.10): race24 + 4 poke-depth bins.
"""

import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import mk_common as K  # noqa: E402
from mk_m3_analyze import SYM_I, PIP, run_contrast, _fmt, _stab  # noqa: E402

OUT = K.OUT
DEPTH_BINS = [(0.0, 1.0), (1.0, 2.0), (2.0, 3.0), (3.0, 5.0)]
DEPTH_LBL = ["(0,1]", "(1,2]", "(2,3]", "(3,5]"]


def load_all():
    ev = {}
    for sym in K.CORE:
        ev[sym] = {}
        z = np.load(os.path.join(OUT, f"m4_events_{sym}.npz"))
        for name in ("BREAK", "POKE"):
            d = {k.split("__", 1)[1]: z[k] for k in z.files
                 if k.startswith(name + "__")}
            if d:
                ev[sym][name] = d
        z = np.load(os.path.join(OUT, f"m4b_events_{sym}.npz"))
        for name in ("SPK", "SBRK"):
            d = {k.split("__", 1)[1]: z[k] for k in z.files
                 if k.startswith(name + "__")}
            if d:
                ev[sym][name] = d
        ev[sym]["POKE"]["hgt_abr"] = ev[sym]["POKE"]["box_h_pips"] * \
            PIP[sym] / ev[sym]["POKE"]["abr"]
        ev[sym]["POKE"]["depth_pips"] = ev[sym]["POKE"]["depth"] / PIP[sym]
    return ev


def edges_per_sym(ev):
    out = {}
    for s in K.CORE:
        abr = np.concatenate([ev[s][n]["abr"]
                              for n in ("BREAK", "POKE", "SPK", "SBRK")])
        qa = np.quantile(abr[np.isfinite(abr) & (abr > 0)],
                         [0.0, 1 / 3, 2 / 3, 1.0])
        hg = np.concatenate([ev[s][n]["hgt_abr"] for n in ("POKE", "SPK")])
        qh = np.quantile(hg[np.isfinite(hg) & (hg > 0)],
                         [0.0, 1 / 3, 2 / 3, 1.0])
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
    if qh is not None:
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
    res = {"families": {"F-Xb": {}}, "counts": {}}
    tests = []

    for s in K.CORE:
        res["counts"][s] = {"n_spk": int(len(ev[s]["SPK"]["day"])),
                            "n_sbrk": int(len(ev[s]["SBRK"]["day"]))}

    # F-Xb test 1: race24 real break vs shifted-interior fake break
    cm = build_cm(ev, "BREAK", "SBRK", lambda d, s: d["race24"],
                  edges=edges)
    r = run_contrast(cm, seed=K.SEED + 2000, sym_factor=252)
    res["families"]["F-Xb"]["race24"] = r
    tests.append(("race24", r["pooled"]["p"]))

    # F-Xb tests 2-5: poke -> reach opp edge, depth bins
    for bi, (a0, a1) in enumerate(DEPTH_BINS):
        cm = build_cm(ev, "POKE", "SPK", lambda d, s: d["reach_opp"],
                      mask_r=lambda d: (d["depth_pips"] > a0)
                      & (d["depth_pips"] <= a1),
                      mask_p=lambda d: (d["depth_pips"] > a0)
                      & (d["depth_pips"] <= a1),
                      edges=edges, hgt_key=True)
        r = run_contrast(cm, seed=K.SEED + 2100 + bi, sym_factor=756)
        res["families"]["F-Xb"][f"fb{DEPTH_LBL[bi]}"] = r
        tests.append((f"fb{DEPTH_LBL[bi]}", r["pooled"]["p"]))

    q, _ = K.bh(np.nan_to_num([t[1] for t in tests], nan=1.0))
    res["families"]["F-Xb"]["race24"]["q"] = float(q[0])
    for i, lbl in enumerate(DEPTH_LBL):
        res["families"]["F-Xb"][f"fb{lbl}"]["q"] = float(q[1 + i])

    # descriptive: pooled rates + fwd drift
    desc = {}
    for s in K.CORE:
        pk, sp = ev[s]["POKE"], ev[s]["SPK"]
        desc[s] = {
            "p_reach_real": float(np.nanmean(pk["reach_opp"])),
            "p_reach_plac": float(np.nanmean(sp["reach_opp"])),
            "p_conv_real": float(np.nanmean(pk["converted"])),
            "p_conv_plac": float(np.nanmean(sp["converted"])),
            "depth_med_real": float(np.median(pk["depth_pips"])),
            "depth_med_plac": float(np.median(sp["depth_pips"])),
            "race24_real": float(np.nanmean(ev[s]["BREAK"]["race24"])),
            "race24_plac": float(np.nanmean(ev[s]["SBRK"]["race24"]))}
    res["descriptive"] = desc
    for H in K.HORIZONS:
        cm = build_cm(ev, "BREAK", "SBRK",
                      lambda d, s, H=H: d[f"fwd_{H}"] / d["abr"],
                      edges=edges)
        res["families"]["F-Xb"][f"fwd{H}_desc"] = run_contrast(
            cm, n_boot_only=True, sym_factor=252)

    K.write_json("m4b_results.json", res)
    write_report(res)
    print("[M4b] analysis done.", flush=True)


def write_report(res):
    L = ["> **FINAL v2 (REVIEW_3 PASS by Lead Ruling 4)**", "",
         "# M4b — shifted-edge placebo (P-SHIFT) — DESIGN 2016–2021", "",
         "Addendum `STUDY_PLAN_ADDENDUM_M4B.md` prereg T000392.  Arm OUT:",
         "fake edges g~U[0.5,2]*ABR beyond real edges (fake pokes); Arm "
         "IN: interior level lo+u*h, u~U[0.2,0.8] (fake breaks).",
         "D = matched-strata contrast; B=2000; BH q=0.10 over 5 tests.", "",
         "Caveat: OUT-arm fake pokes can only occur during excursions "
         ">= g*ABR beyond the real edge (the parent box dies at its own "
         "break), i.e. deeper-wick episodes than the average real poke.  "
         "Strata control side/time/ABR/height/depth but not that "
         "episode-level selection — treat the sign of D as directional.",
         "",
         "## counts (acceptance: >=500 pooled, >=30/symbol/arm)", "",
         "| sym | SPK pokes | SBRK breaks |", "|---|---|---|"]
    for s in K.CORE:
        c = res["counts"][s]
        L.append(f"| {s} | {c['n_spk']} | {c['n_sbrk']} |")
    L += ["", "## descriptive rates", "",
          "| sym | P(reach opp) real | plac | P(conv) real | plac | "
          "race24 real | plac |", "|---|---|---|---|---|---|---|"]
    for s in K.CORE:
        d = res["descriptive"][s]
        L.append(f"| {s} | {_fmt(d['p_reach_real'],3)} | "
                 f"{_fmt(d['p_reach_plac'],3)} | {_fmt(d['p_conv_real'],3)}"
                 f" | {_fmt(d['p_conv_plac'],3)} | "
                 f"{_fmt(d['race24_real'],3)} | {_fmt(d['race24_plac'],3)} |")
    L += ["", "## F-Xb — formal tests (BH q=0.10)", "",
          "| test | D | CI | p | q | n_real | n_plac | stable |",
          "|---|---|---|---|---|---|---|---|"]
    for k in ("race24",) + tuple(f"fb{x}" for x in DEPTH_LBL):
        r = res["families"]["F-Xb"][k]
        p = r["pooled"]
        L.append(f"| {k} | {_fmt(p['D'])} | {_fmt(p['lo'])}–"
                 f"{_fmt(p['hi'])} | {_fmt(p['p'])} | {_fmt(r.get('q'))} | "
                 f"{p.get('n_real', 0)} | {p.get('n_plac', 0)} | "
                 f"{_stab(r)} |")
    L += ["", "descriptive fwd-move D (ABR):", "", "| metric | D |",
          "|---|---|"]
    for k, r in res["families"]["F-Xb"].items():
        if k.endswith("_desc"):
            L.append(f"| {k} | {_fmt(r['pooled']['D'])} |")
    path = os.path.join(_HERE, "BOXES_M4B.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"[M4b] wrote {path}", flush=True)


if __name__ == "__main__":
    main()
