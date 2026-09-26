"""M3 analysis: LEVELS AS ZONES.

Reads research/market/out/m3_events_<SYM>.npz produced by mk_m3_levels.py,
runs the preregistered matched-placebo contrasts (STUDY_PLAN.md, ledger
T000364), applies BH-FDR within each question family, checks the stability
rule (same sign >=4/6 years and >=3/4 symbols), writes
research/market/out/m3_results.json and research/market/LEVELS.md.

Scopes:
  pooled   - all 4 symbols, symbol folded into the stratum key
  per-sym  - point estimate per symbol (stability count)
  per-year - point estimate per calendar year (stability count)
Only the pooled scope gets a bootstrap CI/p; sign stability uses points.
"""

import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import mk_common as K  # noqa: E402

OUT = K.OUT
YEARS = list(range(2016, 2022))
SYM_I = {s: i for i, s in enumerate(K.CORE)}
PIP = {"EURUSD": 1e-4, "GBPUSD": 1e-4, "USDJPY": 1e-2, "AUDUSD": 1e-4}

FIELDS = ["bar", "day", "year", "utc_min", "cet_min", "dow", "side",
          "level", "zlo", "zhi", "tol", "abr", "approach_atr", "dist_cp",
          "age_bars", "lid", "kind", "touch_no", "out_x1", "out_x2",
          "resbar_x1", "resbar_x2", "overshoot_full", "overshoot_x1",
          "retreat_full", "retreat_x1", "retest_12", "retest_48",
          "role_rev", "fwd_3", "fwd_12", "fwd_48"]

TOUCH_SETS = ["S1", "S2", "PDHPDL", "ASIA", "RND", "PRND20", "PRND10",
              "PRAND"]
CROSS_SETS = ["XRND", "XPRND20", "XPRAND"]
# primary placebo mapping for each real family.  F-R's declared 24 tests
# = 5 sets x 2 x x 2 estimands vs PRAND + RND vs {PRND20,PRND10} x 2 x;
# so the RND primary arm is PRAND (the grid placebos are the +4).
PLAC = {"S1": "PRAND", "S2": "PRAND", "PDHPDL": "PRAND", "ASIA": "PRAND",
        "RND": "PRAND"}
PLAC_SENS = {"RND": "PRND10"}
XPLAC = {"XRND": "XPRND20"}
XPLAC_SENS = {"XRND": "XPRAND"}

AGE_BINS = [(0, 36), (36, 96), (96, 288), (288, 864), (864, 1441)]
AGE_LBL = ["<3h", "3-8h", "8-24h", "1-3d", "3-5d"]


def load_all():
    ev = {}
    for sym in K.CORE:
        z = np.load(os.path.join(OUT, f"m3_events_{sym}.npz"))
        ev[sym] = {}
        for name in TOUCH_SETS + CROSS_SETS:
            d = {}
            for f in FIELDS:
                k = f"{name}__{f}"
                if k in z:
                    d[f] = z[k]
            ev[sym][name] = d
    return ev


# ------------------------------------------------------------------ keys
def edges_per_sym(ev):
    """Stratum edges per plan §3: terciles/deciles on pooled real+placebo
    events *of that symbol* (review fix: previously pooled across symbols,
    which collapsed the ABR tercile for USDJPY)."""
    out = {}
    for s in K.CORE:
        abr = np.concatenate([ev[s][n]["abr"] for n in
                              TOUCH_SETS + CROSS_SETS])
        app = np.concatenate([ev[s][n]["approach_atr"] for n in
                              TOUCH_SETS + CROSS_SETS])
        abr = abr[np.isfinite(abr) & (abr > 0)]
        app = app[np.isfinite(app)]
        qa = np.quantile(abr, [0.0, 1 / 3, 2 / 3, 1.0])
        qp = np.quantile(app, np.linspace(0.0, 1.0, 11)) if len(app) \
            else np.zeros(11)
        out[s] = (qa, qp)
    return out


def key_ints(d, sym, qa, qp):
    """Stratum key int: side,dow,4h bucket,abr tercile,approach decile,sym."""
    side01 = ((d["side"] + 1) / 2).astype(np.int64)
    dow = d["dow"].astype(np.int64)
    bucket = (d["utc_min"] // 240).astype(np.int64)
    ter = np.clip(np.searchsorted(qa, d["abr"], side="right") - 1, 0, 2)
    app = d["approach_atr"]
    dec = np.where(np.isfinite(app),
                   np.clip(np.searchsorted(qp, app, side="right") - 1, 0, 9),
                   10)
    si = np.full(len(dow), SYM_I[sym], dtype=np.int64)
    return (side01 + 2 * (dow + 7 * (bucket + 6 * (ter + 3 * (dec + 11 * si))))
            ).astype(np.int64)


SYM_FACTOR = 2 * 7 * 6 * 3 * 11  # coefficient of sym in key_ints


def _yr(day_int):
    import datetime as _dt
    return (_dt.datetime(1970, 1, 1) + _dt.timedelta(days=int(day_int))).year


def run_contrast(cm, seed=K.SEED, n_boot_only=False,
                 sym_factor=SYM_FACTOR):
    """Pooled bootstrap + per-symbol / per-year point estimates.
    n_boot_only=True skips the pooled bootstrap (descriptive rows).
    `sym_factor` must match the multiplier applied to the symbol index in
    the caller's key_ints (x3 when a slope/height tercile was folded in).
    """
    out = {"pooled": K.contrast_boot(cm, n_boot=0 if n_boot_only else 2000,
                                   seed=seed)}
    keys = np.asarray(cm["keys"], dtype=np.int64)
    days = np.asarray(cm["days"], dtype=np.int64)
    per_sym = {}
    for s, i in SYM_I.items():
        cols = np.flatnonzero(keys // sym_factor == i)
        if len(cols):
            per_sym[s] = K.contrast_boot(cm, n_boot=0, cols=cols)["D"]
    per_year = {}
    for y in YEARS:
        rows = np.array([i for i, d in enumerate(days) if _yr(d) == y],
                        dtype=np.int64)
        if len(rows):
            per_year[y] = K.contrast_boot(cm, n_boot=0, rows=rows)["D"]
    out["per_sym"] = per_sym
    out["per_year"] = per_year
    sy = [v for v in per_year.values() if np.isfinite(v)]
    ss = [v for v in per_sym.values() if np.isfinite(v)]
    if out["pooled"]["D"] is not None and np.isfinite(out["pooled"]["D"]):
        sgn = np.sign(out["pooled"]["D"])
        out["stable"] = (int((np.sign(sy) == sgn).sum()) >= 4
                         and int((np.sign(ss) == sgn).sum()) >= 3)
    else:
        out["stable"] = False
    return out


def _pool(ev, sym, names, field):
    return np.concatenate([ev[sym][n][field] for n in names])


def build_cm(ev, real_name, plac_name, val_fn, mask_real=None,
             mask_plac=None, qa=None, qp=None):
    """Build contrast matrices.  real_name/plac_name may be a set name or
    a list of set names (pooled).  qa/qp: dict sym -> (qa, qp)."""
    if isinstance(real_name, str):
        real_name = [real_name]
    if isinstance(plac_name, str):
        plac_name = [plac_name]
    rd, rk, rv = [], [], []
    pd_, pk, pv = [], [], []
    for sym in K.CORE:
        qa_s, qp_s = qa[sym], qp[sym]
        r = {f: _pool(ev, sym, real_name, f) for f in FIELDS
             if f in ev[sym][real_name[0]]}
        p = {f: _pool(ev, sym, plac_name, f) for f in FIELDS
             if f in ev[sym][plac_name[0]]}
        mr = np.ones(len(r["day"]), bool) if mask_real is None \
            else mask_real(r)
        mp = np.ones(len(p["day"]), bool) if mask_plac is None \
            else mask_plac(p)
        rd.append(r["day"][mr]); rk.append(key_ints(r, sym, qa_s, qp_s)[mr])
        rv.append(val_fn(r, sym)[mr])
        pd_.append(p["day"][mp]); pk.append(key_ints(p, sym, qa_s, qp_s)[mp])
        pv.append(val_fn(p, sym)[mp])
    rd = np.concatenate(rd); rk = np.concatenate(rk); rv = np.concatenate(rv)
    pd_ = np.concatenate(pd_); pk = np.concatenate(pk); pv = np.concatenate(pv)
    fin = np.isfinite(rv)
    finp = np.isfinite(pv)
    return K.contrast_mats_arr(rd[fin], rk[fin], rv[fin],
                               pd_[finp], pk[finp], pv[finp])


def v_bounce(x):
    """Primary estimand: P_rev = BOUNCE / N (all events)."""
    return lambda d, sym: (d[f"out_x{x}"] == 0).astype(np.float64)


def v_bounce_res(x):
    """Secondary estimand: BOUNCE/(BOUNCE+BREAK) among resolved."""
    def f(d, sym):
        o = d[f"out_x{x}"]
        return np.where(o == 2, np.nan, (o == 0).astype(np.float64))
    return f


def v_overshoot_abr(d, sym):
    return np.where(d["out_x1"] == 0,
                    d["overshoot_x1"] / d["abr"], np.nan)


def v_overshoot_pips(d, sym):
    return np.where(d["out_x1"] == 0,
                    d["overshoot_x1"] / PIP[sym], np.nan)


def v_retest(which):
    def f(d, sym):
        return np.where(d["out_x1"] == 1, d[f"retest_{which}"], np.nan)
    return f


def v_rolerev(which):
    def f(d, sym):
        return np.where((d["out_x1"] == 1) & (d[f"retest_{which}"] == 1),
                        d["role_rev"], np.nan)
    return f


def v_fwd(h):
    return lambda d, sym: d[f"fwd_{h}"] / d["abr"]


def quant(d, sym, name):
    v = d[name] / PIP[sym]
    v = v[np.isfinite(v)]
    if not len(v):
        return {}
    q = np.quantile(v, [0.25, 0.5, 0.75, 0.9])
    return {"p25": q[0], "p50": q[1], "p75": q[2], "p90": q[3],
            "n": int(len(v))}


def main():
    ev = load_all()
    edges = edges_per_sym(ev)
    res = {"edges": {s: {"abr_tercile": edges[s][0].tolist(),
                         "approach_decile": edges[s][1].tolist()}
                     for s in K.CORE},
           "families": {}}
    qa = {s: edges[s][0] for s in K.CORE}
    qp = {s: edges[s][1] for s in K.CORE}

    # ---------------------------------------------------------- F-R family
    # declared 24 tests: {S1,S2,PDHPDL,ASIA,RND} x {x1,x2} x {P_rev (all),
    # P_rev|resolved} + RND vs P-RND20 / P-RND10 at x in {1,2} (primary).
    fr = {}
    tests = []
    for name in ["S1", "S2", "PDHPDL", "ASIA", "RND"]:
        for x in (1, 2):
            for est, vf in (("", v_bounce(x)), ("_res", v_bounce_res(x))):
                cm = build_cm(ev, name, PLAC[name], vf, qa=qa, qp=qp)
                r = run_contrast(cm, seed=K.SEED + x)
                r["n_real"] = r["pooled"]["n_real"]
                r["n_plac"] = r["pooled"]["n_plac"]
                fr[f"{name}_x{x}{est}"] = r
                tests.append((f"{name}_x{x}{est}", r["pooled"]["p"]))
    for x in (1, 2):
        for pn in ("PRND20", "PRND10"):
            cm = build_cm(ev, "RND", pn, v_bounce(x), qa=qa, qp=qp)
            r = run_contrast(cm, seed=K.SEED + 100 + x)
            fr[f"RNDvs{pn}_x{x}"] = r
            tests.append((f"RNDvs{pn}_x{x}", r["pooled"]["p"]))
    p = [t[1] for t in tests]
    q, _ = K.bh(np.nan_to_num(p, nan=1.0))
    for (k, _), qq in zip(tests, q):
        fr[k]["q"] = float(qq)
    res["families"]["F-R"] = fr
    print(f"[M3] F-R done ({len(tests)} tests)", flush=True)

    # ---------------------------------------------------------- F-O family
    # plan: descriptive only (quantiles per set) — no contrast, no FDR.
    fo = {}
    # descriptive overshoot quantiles in pips (bounce events)
    desc = {}
    for name in TOUCH_SETS:
        dd = {}
        for sym in K.CORE:
            d = ev[sym][name]
            m = d["out_x1"] == 0
            dd[sym] = quant({"o": d["overshoot_x1"][m]}, sym, "o")
        allv = np.concatenate([ev[s][name]["overshoot_x1"][
            ev[s][name]["out_x1"] == 0] / ev[s][name]["abr"][
            ev[s][name]["out_x1"] == 0] for s in K.CORE])
        allv = allv[np.isfinite(allv)]
        qq_ = np.quantile(allv, [0.25, 0.5, 0.75, 0.9]) if len(allv) \
            else [np.nan] * 4
        dd["ALL(ABR)"] = {"p25": qq_[0], "p50": qq_[1], "p75": qq_[2],
                          "p90": qq_[3], "n": int(len(allv))}
        desc[name] = dd
    res["families"]["F-O"] = {"contrast": fo, "desc_pips": desc}
    print("[M3] F-O done", flush=True)

    # ---------------------------------------------------------- F-A family
    # declared: S1+S2 pooled vs PRAND over 5 age bins (plan §4 F-A).
    fa = {}
    tests = []
    per_bin = []
    for bi, (a0, a1) in enumerate(AGE_BINS):
        def mr(d, a0=a0, a1=a1):
            return (d["age_bars"] >= a0) & (d["age_bars"] < a1)
        cm = build_cm(ev, ["S1", "S2"], "PRAND", v_bounce(1),
                      mask_real=mr, mask_plac=mr, qa=qa, qp=qp)
        r = run_contrast(cm, seed=K.SEED + 300 + bi)
        per_bin.append({"bin": AGE_LBL[bi], "res": r})
        tests.append((AGE_LBL[bi], r["pooled"]["p"]))
    # half-life fit: D(h) = D0 * 2^(-h/tau), bin mid-age in hours
    mids = np.array([1.5, 5.5, 16.0, 48.0, 96.0])
    Ds = np.array([b["res"]["pooled"]["D"] for b in per_bin])
    best = (np.inf, np.nan, np.nan)
    w = np.isfinite(Ds)
    if w.sum() >= 3:
        for tau in np.geomspace(0.5, 2000, 400):
            model = 2.0 ** (-mids / tau)
            d0 = float((Ds[w] * model[w]).sum() / (model[w] ** 2).sum())
            sse = float(((Ds[w] - d0 * model[w]) ** 2).sum())
            if sse < best[0]:
                best = (sse, tau, d0)
    fa["S12_pooled"] = {"bins": per_bin, "half_life_h": best[1],
                        "D0": best[2]}
    # descriptive per-set split (no q)
    for name in ["S1", "S2"]:
        per_bin = []
        for bi, (a0, a1) in enumerate(AGE_BINS):
            def mr(d, a0=a0, a1=a1):
                return (d["age_bars"] >= a0) & (d["age_bars"] < a1)
            cm = build_cm(ev, name, PLAC[name], v_bounce(1),
                          mask_real=mr, mask_plac=mr, qa=qa, qp=qp)
            per_bin.append({"bin": AGE_LBL[bi],
                            "res": run_contrast(cm, n_boot_only=True)})
        fa[f"{name}_desc"] = per_bin
    q, _ = K.bh(np.nan_to_num([t[1] for t in tests], nan=1.0))
    for b, qq in zip(fa["S12_pooled"]["bins"], q):
        b["res"]["q"] = float(qq)
    res["families"]["F-A"] = fa
    print("[M3] F-A done", flush=True)

    # ---------------------------------------------------------- F-T family
    # declared: pooled sets {S1,S2,PDHPDL,ASIA} vs PRAND, touch_no
    # {1,2,3+} x x{1,2} -> 6 tests.
    ft = {"pooled": []}
    tests = []
    for x in (1, 2):
        for cls, lbl in ((1, "t1"), (2, "t2"), (3, "t3p")):
            if cls < 3:
                def mr(d, c=cls):
                    return d["touch_no"] == c
            else:
                def mr(d):
                    return d["touch_no"] >= 3
            cm = build_cm(ev, ["S1", "S2", "PDHPDL", "ASIA"], "PRAND",
                          v_bounce(x), mask_real=mr, mask_plac=mr,
                          qa=qa, qp=qp)
            r = run_contrast(cm, seed=K.SEED + 400 + cls + 10 * x)
            ft["pooled"].append({"x": x, "cls": lbl, "res": r})
            tests.append((f"x{x}_{lbl}", r["pooled"]["p"]))
    # descriptive per-set (x1)
    for name in ["S1", "S2", "PDHPDL", "ASIA", "RND"]:
        per_cls = []
        for cls, lbl in ((1, "t1"), (2, "t2"), (3, "t3p")):
            if cls < 3:
                def mr(d, c=cls):
                    return d["touch_no"] == c
            else:
                def mr(d):
                    return d["touch_no"] >= 3
            cm = build_cm(ev, name, PLAC[name], v_bounce(1),
                          mask_real=mr, mask_plac=mr, qa=qa, qp=qp)
            per_cls.append({"cls": lbl,
                            "res": run_contrast(cm, n_boot_only=True)})
        ft[f"{name}_desc"] = per_cls
    q, _ = K.bh(np.nan_to_num([t[1] for t in tests], nan=1.0))
    for c, qq in zip(ft["pooled"], q):
        c["res"]["q"] = float(qq)
    res["families"]["F-T"] = ft
    print("[M3] F-T done", flush=True)

    # ---------------------------------------------------------- F-B family
    # declared 4 tests (pooled sets): retest12, retest48, role_rev|retest12,
    # role_rev|retest48.  Per-set numbers stay descriptive.
    fb = {"pooled": {}}
    tests = []
    pooled_sets = ["S1", "S2", "PDHPDL", "ASIA"]   # same set scope as F-T
    # (pooled placebo = PRAND for all sets)
    for lbl, vf in (("retest12", v_retest(12)),
                    ("retest48", v_retest(48)),
                    ("role_rev_r12", v_rolerev(12)),
                    ("role_rev_r48", v_rolerev(48))):
        cm = build_cm(ev, pooled_sets, "PRAND", vf, qa=qa, qp=qp)
        r = run_contrast(cm, seed=K.SEED + 500)
        fb["pooled"][lbl] = r
        tests.append((lbl, r["pooled"]["p"]))
    for name in pooled_sets + ["RND"]:
        cm = build_cm(ev, name, PLAC[name], v_retest(12), qa=qa, qp=qp)
        r1 = run_contrast(cm, n_boot_only=True)
        cm = build_cm(ev, name, PLAC[name], v_rolerev(12), qa=qa, qp=qp)
        r2 = run_contrast(cm, n_boot_only=True)
        fb[f"{name}_desc"] = {"retest12": r1, "role_rev": r2}
    q, _ = K.bh(np.nan_to_num([t[1] for t in tests], nan=1.0))
    for (k, _), qq in zip(tests, q):
        fb["pooled"][k]["q"] = float(qq)
    res["families"]["F-B"] = fb
    print("[M3] F-B done", flush=True)

    # ---------------------------------------------------------- F-C family
    # declared 4 tests: {XRND vs XPRND20, XRND vs XPRAND} x h in {3,12}.
    fc = {}
    tests = []
    for h in (3, 12):
        cm = build_cm(ev, "XRND", "XPRND20", v_fwd(h), qa=qa, qp=qp)
        r = run_contrast(cm, seed=K.SEED + 600 + h)
        fc[f"RNDvsPRND20_h{h}"] = r
        tests.append((f"RNDvsPRND20_h{h}", r["pooled"]["p"]))
        cm = build_cm(ev, "XRND", "XPRAND", v_fwd(h), qa=qa, qp=qp)
        r = run_contrast(cm, seed=K.SEED + 650 + h)
        fc[f"RNDvsPRAND_h{h}"] = r
        tests.append((f"RNDvsPRAND_h{h}", r["pooled"]["p"]))
    # h48: descriptive only (was not a preregistered horizon)
    cm = build_cm(ev, "XRND", "XPRND20", v_fwd(48), qa=qa, qp=qp)
    fc["RNDvsPRND20_h48_desc"] = run_contrast(cm, n_boot_only=True)
    q, _ = K.bh(np.nan_to_num([t[1] for t in tests], nan=1.0))
    for (k, _), qq in zip(tests, q):
        fc[k]["q"] = float(qq)
    # raw fwd means in pips for context
    raw = {}
    for name in CROSS_SETS:
        dd = {}
        for h in (3, 12, 48):
            v = np.concatenate([ev[s][name][f"fwd_{h}"] / PIP[s]
                                for s in K.CORE])
            v = v[np.isfinite(v)]
            dd[f"h{h}"] = {"mean": float(v.mean()) if len(v) else np.nan,
                           "med": float(np.median(v)) if len(v) else np.nan,
                           "n": int(len(v))}
        raw[name] = dd
    res["families"]["F-C"] = {"contrast": fc, "raw_pips": raw}
    print("[M3] F-C done", flush=True)

    # ------------------------------------------------------- context stats
    ctx = {}
    for name in TOUCH_SETS:
        dd = {}
        for sym in K.CORE:
            d = ev[sym][name]
            n = len(d["day"])
            b1 = float((d["out_x1"] == 0).mean()) if n else np.nan
            b2 = float((d["out_x2"] == 0).mean()) if n else np.nan
            dd[sym] = {"n": n, "p_bounce_x1": b1, "p_bounce_x2": b2}
        ctx[name] = dd
    res["context"] = ctx

    path = K.write_json("m3_results.json", res)
    print(f"[M3] wrote {path}", flush=True)
    write_report(res)


def _fmt(v, nd=4):
    return "nan" if v is None or not np.isfinite(v) else f"{v:.{nd}f}"


def _stab(r):
    """Stability flag only on formal rows (finite q); descriptive rows
    render an em-dash so a sign-stable desc row can't read as inference."""
    q = (r or {}).get("q")
    if q is None or not np.isfinite(q):
        return "—"
    return "YES" if r["stable"] else "no"


def _row(label, r):
    p = r["pooled"]
    sy = "".join("+" if np.sign(v) == np.sign(p["D"]) else "-"
                 for v in r["per_year"].values())
    ss = "".join("+" if np.sign(v) == np.sign(p["D"]) else "-"
                 for v in r["per_sym"].values())
    return (f"| {label} | {_fmt(p['D'])} | {_fmt(p['lo'])}–{_fmt(p['hi'])} "
            f"| {_fmt(p['p'])} | {_fmt(r.get('q'))} | {sy} ({len(r['per_year'])}) "
            f"| {ss} | {_stab(r)} |")


def write_report(res):
    L = []
    L.append('> **FINAL v2 (REVIEW_3 PASS by Lead Ruling 4)**\n\n')
    L.append("# M3 — Levels as zones (DESIGN 2016–2021)\n")
    L.append("Prereg: STUDY_PLAN.md sha256 `abc8b5ba…` (ledger T000364). "
             "Contrast D = matched-strata Hajek difference vs placebo; "
             "day-block bootstrap (B=2000); BH-FDR q=0.10 per family; "
             "stability = same sign ≥4/6 years AND ≥3/4 symbols.\n")

    ctx = res["context"]
    L.append("\n## Context: raw touch stats (unconditional)\n")
    L.append("| set | symbol | n | P(bounce x1) | P(bounce x2) |")
    L.append("|---|---|---|---|---|")
    for name in TOUCH_SETS:
        for s in K.CORE:
            d = ctx[name][s]
            L.append(f"| {name} | {s} | {d['n']} | {_fmt(d['p_bounce_x1'],3)} "
                     f"| {_fmt(d['p_bounce_x2'],3)} |")

    L.append("\n## F-R — reaction on touch: D = P(bounce|real) − P(bounce|plac)\n")
    L.append("| test | D | CI | p | q | year-signs | sym-signs | stable |")
    L.append("|---|---|---|---|---|---|---|---|")
    for k, r in res["families"]["F-R"].items():
        L.append(_row(k, r))

    L.append("\n## F-O — overshoot quantiles (bounce events; descriptive "
             "per plan, no contrast).  Symbols in pips, ALL in ABR units.\n")
    L.append("| set | scope | p25 | p50 | p75 | p90 | n |")
    L.append("|---|---|---|---|---|---|---|")
    for name, dd in res["families"]["F-O"]["desc_pips"].items():
        for sc in ["ALL(ABR)"] + K.CORE:
            v = dd[sc]
            if not v:
                continue
            L.append(f"| {name} | {sc} | {_fmt(v['p25'],1)} | "
                     f"{_fmt(v['p50'],1)} | {_fmt(v['p75'],1)} | "
                     f"{_fmt(v['p90'],1)} | {v['n']} |")

    L.append("\n## F-A — age decay (x1), declared bins, S1+S2 pooled\n")
    L.append("| bin | D | CI | p | q | stable |")
    L.append("|---|---|---|---|---|---|")
    fa = res["families"]["F-A"]["S12_pooled"]
    for b in fa["bins"]:
        p = b["res"]["pooled"]
        L.append(f"| {b['bin']} | {_fmt(p['D'])} | "
                 f"{_fmt(p['lo'])}–{_fmt(p['hi'])} | {_fmt(p['p'])} | "
                 f"{_fmt(b['res'].get('q'))} | "
                 f"{_stab(b['res'])} |")
    L.append(f"| **half-life** | {fa['half_life_h']:.1f} h "
             f"(D0={_fmt(fa['D0'])}) | | | | |")
    L.append("\nper-set split (descriptive, x1, D only):\n")
    L.append("| set | " + " | ".join(AGE_LBL) + " |")
    L.append("|---|" + "---|" * len(AGE_LBL))
    for name in ("S1", "S2"):
        cells = " | ".join(_fmt(b["res"]["pooled"]["D"])
                           for b in res["families"]["F-A"][f"{name}_desc"])
        L.append(f"| {name} | {cells} |")

    L.append("\n## F-T — touch ordinal, pooled {S1,S2,PDHPDL,ASIA}\n")
    L.append("| x | class | D | CI | p | q | stable |")
    L.append("|---|---|---|---|---|---|---|")
    for c in res["families"]["F-T"]["pooled"]:
        p = c["res"]["pooled"]
        L.append(f"| x{c['x']} | {c['cls']} | {_fmt(p['D'])} | "
                 f"{_fmt(p['lo'])}–{_fmt(p['hi'])} | {_fmt(p['p'])} | "
                 f"{_fmt(c['res'].get('q'))} | "
                 f"{_stab(c['res'])} |")
    L.append("\nper-set split (descriptive, x1, D only):\n")
    L.append("| set | t1 | t2 | t3+ |")
    L.append("|---|---|---|---|")
    for name in ["S1", "S2", "PDHPDL", "ASIA", "RND"]:
        cells = " | ".join(_fmt(c["res"]["pooled"]["D"])
                           for c in res["families"]["F-T"][f"{name}_desc"])
        L.append(f"| {name} | {cells} |")

    L.append("\n## F-B — after a clean break (x1 BREAK), pooled sets\n")
    L.append("| metric | D | CI | p | q | stable |")
    L.append("|---|---|---|---|---|---|")
    for m in ("retest12", "retest48", "role_rev_r12", "role_rev_r48"):
        r = res["families"]["F-B"]["pooled"][m]
        p = r["pooled"]
        L.append(f"| {m} | {_fmt(p['D'])} | "
                 f"{_fmt(p['lo'])}–{_fmt(p['hi'])} | {_fmt(p['p'])} | "
                 f"{_fmt(r.get('q'))} | "
                 f"{_stab(r)} |")
    L.append("\nper-set (descriptive, D only): retest12 / role_rev|r12\n")
    L.append("| set | retest12 | role_rev |")
    L.append("|---|---|---|")
    for name in ["S1", "S2", "PDHPDL", "ASIA", "RND"]:
        d = res["families"]["F-B"][f"{name}_desc"]
        L.append(f"| {name} | {_fmt(d['retest12']['pooled']['D'])} | "
                 f"{_fmt(d['role_rev']['pooled']['D'])} |")

    L.append("\n## F-C — round-number cascades: D of fwd move (ABR), "
             "declared h in {3,12}\n")
    L.append("| test | D | CI | p | q | stable |")
    L.append("|---|---|---|---|---|---|")
    for k, r in res["families"]["F-C"]["contrast"].items():
        p = r["pooled"]
        L.append(f"| {k} | {_fmt(p['D'])} | {_fmt(p['lo'])}–{_fmt(p['hi'])} "
                 f"| {_fmt(p['p'])} | {_fmt(r.get('q'))} | "
                 f"{_stab(r)} |")
    L.append("\nRaw fwd move after cross (pips):\n")
    L.append("| set | horizon | mean | median | n |")
    L.append("|---|---|---|---|---|")
    for name, dd in res["families"]["F-C"]["raw_pips"].items():
        for h, v in dd.items():
            L.append(f"| {name} | {h} | {_fmt(v['mean'],2)} | "
                     f"{_fmt(v['med'],2)} | {v['n']} |")

    path = os.path.join(_HERE, "LEVELS.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"[M3] wrote {path}", flush=True)


if __name__ == "__main__":
    main()
