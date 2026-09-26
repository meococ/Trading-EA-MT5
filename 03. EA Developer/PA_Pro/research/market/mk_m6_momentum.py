"""M6 — MOMENTUM, PULLBACKS, EMA25 (DESIGN only).

Preregistered (STUDY_PLAN §7 / ledger T000364), revised after the M8
review (DEVIATIONS): pivot scales corrected to theta1=1.0 / theta2=2.5
(was 2.0, mislabeled S2); warmup bars never produce pivots in the
pullback/EMA stats; return segments now break at >300s feed gaps (not
just warmup/session edges); EMA lengths {15,20,25,35,50} and the four
declared formal contrasts are actually computed; B=2000 day-block
bootstrap throughout (sufficient-statistic engine — stats are additive
over day-tagged segments).

  F-M  per plan: lag-1 autocorr by session (4 tests), VR(12) vs 1 by
       session (4 tests), EMA25-vs-20/50 proximity contrasts at
       x in {0.5,1.0} (4 tests).  BH q=0.10, family size 12.
  Descriptive: full acf/VR curves, pullback-depth distribution, EMA
  proximity table incl. x=0.25.

Sessions (CET): ASIA 00-08, EU 08-14:30, US 14:30-18:00, LATE 18-24.
Pullback legs use theta2 DC triples (impulse leg p1->p2, pullback leg
p2->p3; depth = |p3-p2|/|p2-p1|).  EMA pivot ends = theta1 pivots whose
kind is counter to the current theta2 direction, measured at the pivot
extreme bar.

Output: out/m6_results.json, MOMENTUM.md.
"""

import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import mk_common as K  # noqa: E402

OUT = K.OUT
PIP = {"EURUSD": 1e-4, "GBPUSD": 1e-4, "USDJPY": 1e-2, "AUDUSD": 1e-4}
LAGS = list(range(1, 13))
VRK = (2, 4, 8, 12, 24, 48)
EMA_LENS = (15, 20, 25, 35, 50)
X_BANDS = (0.25, 0.5, 1.0)
B_BOOT = 2000

TH1, TH2 = 1.0, 2.5           # declared DC scales (ABR units)
SESS_EDGES = (480, 870, 1080)  # 08:00 / 14:30 / 18:00 CET


def session_idx(cet):
    """0 ASIA (<480) 1 EU (480-870) 2 US (870-1080) 3 LATE (>=1080)."""
    return np.digitize(np.asarray(cet), SESS_EDGES)


def sess_name(i):
    return ("ASIA", "EU", "US", "LATE")[i]


def make_segments(cet, warm, t_arr):
    """Contiguous non-warm same-session index ranges, broken at feed gaps
    (>300 s between consecutive bar opens).  Returns list of
    (a, b, sess, day)."""
    s = session_idx(cet)
    n = len(s)
    day = (np.asarray(t_arr, dtype=np.int64) // 86400).astype(np.int64)
    out = []
    a = None
    for t in range(n):
        gap = t > 0 and (t_arr[t] - t_arr[t - 1]) > 300
        if warm[t] or gap:
            if a is not None:
                out.append((a, t, int(s[a]), int(day[a])))
                a = None
            if warm[t]:
                continue
        if a is None:
            a = t
        elif s[t] != s[a]:
            out.append((a, t, int(s[a]), int(day[a])))
            a = t
    if a is not None:
        out.append((a, n, int(s[a]), int(day[a])))
    return out


def seg_suff(r, segs):
    """Per-segment sufficient statistics for acf lags and VR ks.

    acf(k): x=r[:-k], y=r[k:] within the segment; stats num=sum xy_c,
    s0=sum x_c^2, s1=sum y_c^2 (segment-centred), n=len(x).
    VR(k): pooled formulation — k-sums m=len(conv), s1k=sum(conv),
    s2k=sum(conv^2); level: nr=len(r), sr=sum(r), sr2=sum(r^2).
    Returns dict seg_i -> dict of stats, plus day/session tags."""
    out = []
    for (a, b, sess, d) in segs:
        # drop the first return of each segment: r[a] spans the boundary
        # (session change or >300s feed gap) that created the segment.
        rr = np.nan_to_num(r[a + 1:b])
        st = {"sess": sess, "day": d, "n": len(rr)}
        st["sr"] = float(rr.sum()); st["sr2"] = float((rr ** 2).sum())
        for k in LAGS:
            if len(rr) > k + 2:
                x = rr[:-k]; y = rr[k:]
                xc = x - x.mean(); yc = y - y.mean()
                st[f"ac{k}_num"] = float(np.dot(xc, yc))
                st[f"ac{k}_s0"] = float((xc ** 2).sum())
                st[f"ac{k}_s1"] = float((yc ** 2).sum())
            else:
                st[f"ac{k}_num"] = st[f"ac{k}_s0"] = st[f"ac{k}_s1"] = 0.0
        for k in VRK:
            if len(rr) > k:
                cv = np.convolve(rr, np.ones(k), "valid")
                st[f"vr{k}_s1"] = float(cv.sum())
                st[f"vr{k}_s2"] = float((cv ** 2).sum())
                st[f"vr{k}_m"] = float(len(cv))
            else:
                st[f"vr{k}_s1"] = st[f"vr{k}_s2"] = st[f"vr{k}_m"] = 0.0
        out.append(st)
    return out


def acf_from(S):
    """rho = sum num / sqrt(sum s0 * sum s1) from suff-stat rows S."""
    num = S[:, 0].sum(); s0 = S[:, 1].sum(); s1 = S[:, 2].sum()
    if s0 <= 0 or s1 <= 0:
        return np.nan
    return float(num / np.sqrt(s0 * s1))


def vr_from(S, k):
    """Pooled VR(k) = var(k-sums) / (k * var(r)).  S cols: vr_s1, vr_s2,
    vr_m, sr, sr2, n."""
    m = S[:, 2].sum()
    n = S[:, 5].sum()
    if m <= 1 or n <= 1:
        return np.nan
    vs = S[:, 1].sum() / m - (S[:, 0].sum() / m) ** 2
    v1 = S[:, 4].sum() / n - (S[:, 3].sum() / n) ** 2
    if v1 <= 0:
        return np.nan
    return float(vs / (k * v1))


def boot_days(day_vals, stat_fn, B=B_BOOT, seed=K.SEED):
    """Matrix day-block bootstrap over additive per-day stat rows."""
    days = np.array(sorted(day_vals))
    M = np.stack([day_vals[d] for d in days])        # days x stats
    point = stat_fn(M)
    rng = np.random.default_rng(seed)
    Wm = rng.multinomial(len(days), np.full(len(days), 1.0 / len(days)),
                         size=B).astype(np.float64)
    SM = Wm @ M
    # stat_fn expects a matrix of suff-stat rows; Wm@M gives one summed row
    vals = np.array([stat_fn(SM[i][None, :]) for i in range(B)])
    vv = vals[np.isfinite(vals)]
    if len(vv) < 50:
        return point, np.nan, np.nan, np.nan
    lo, hi = np.percentile(vv, [2.5, 97.5])
    p = 2.0 * min(float((vv <= 0).mean()), float((vv > 0).mean()))
    return point, float(lo), float(hi), float(max(p, 1.0 / (len(vv) + 1)))


def day_rows(segs, cols_fn):
    """Aggregate per-segment suff-stats into per-day rows for a scope."""
    rows = {}
    for st in segs:
        d = st["day"]
        if d not in rows:
            rows[d] = cols_fn(st)
        else:
            rows[d] += cols_fn(st)
    return rows


def main():
    res = {"symbols": {}}
    for sym in K.CORE:
        print(f"[M6] {sym} ...", flush=True)
        with K.pa_slots.slot(f"dr-market M6 {sym}", timeout=120):
            dd = K.load_symbol(sym)
            m5 = dd["m5"]
            c = np.asarray(m5["c"])
            t_arr = np.asarray(m5["t"], dtype=np.int64)
            warm = np.asarray(m5["warmup"], dtype=bool)
            cet = K.cet_minutes(m5)
            day = K.day_id(m5)
            year = K.server_year(m5)
            abr = K.abr_series(m5)
            r = np.diff(np.log(c))
            r = np.concatenate(([np.nan], r))
            segs = make_segments(cet, warm, t_arr)
            suff = seg_suff(r, segs)

            # ---- F-AC / F-VR: per-day suff-stat rows per scope ---------
            acf_res = {}
            vr_res = {}
            tests = []
            for si in range(4):
                ss = [s for s in suff if s["sess"] == si]
                rows = {}
                for st in ss:
                    d = st["day"]
                    if d not in rows:
                        rows[d] = {k: 0.0 for k in st
                                   if k not in ("sess", "day")}
                    for k in rows[d]:
                        rows[d][k] += st[k]
                nm = sess_name(si)
                # acf lags
                for k in LAGS:
                    cols = {d: np.array([v[f"ac{k}_num"], v[f"ac{k}_s0"],
                                         v[f"ac{k}_s1"]])
                            for d, v in rows.items()}
                    pt, lo, hi, p = boot_days(cols, acf_from,
                                              seed=K.SEED + 100 * si + k)
                    acf_res[f"{nm}_lag{k}"] = {
                        "rho": pt, "lo": lo, "hi": hi,
                        "n": int(sum(v[f"ac{k}_s0"] > 0 for v in
                                     rows.values()))}
                    if k == 1:
                        acf_res[f"{nm}_lag1"]["p"] = p
                        tests.append((f"acf_{nm}_lag1", p))
                # VR
                for k in VRK:
                    cols = {d: np.array([v[f"vr{k}_s1"], v[f"vr{k}_s2"],
                                         v[f"vr{k}_m"], v["sr"],
                                         v["sr2"], v["n"]])
                            for d, v in rows.items()}
                    pt, lo, hi, _ = boot_days(
                        cols, lambda M, k=k: vr_from(M, k),
                        seed=K.SEED + 500 + 10 * si + k)
                    ent = {"vr": pt, "lo": lo, "hi": hi}
                    if k == 12:
                        # test VR(12) vs 1: bootstrap of vr-1
                        cols1 = {d: v for d, v in cols.items()}
                        pt1, lo1, hi1, p1 = boot_days(
                            cols1, lambda M: vr_from(M, 12) - 1.0,
                            seed=K.SEED + 700 + si)
                        ent["p_vs1"] = p1
                        tests.append((f"vr_{nm}_k12", p1))
                    vr_res[f"{nm}_k{k}"] = ent
            # pooled ALL scope: all segments
            rows_all = {}
            for st in suff:
                d = st["day"]
                if d not in rows_all:
                    rows_all[d] = {k: 0.0 for k in st
                                   if k not in ("sess", "day")}
                for k in rows_all[d]:
                    rows_all[d][k] += st[k]
            for k in LAGS:
                cols = {d: np.array([v[f"ac{k}_num"], v[f"ac{k}_s0"],
                                     v[f"ac{k}_s1"]])
                        for d, v in rows_all.items()}
                pt, lo, hi, _ = boot_days(cols, acf_from,
                                          seed=K.SEED + 900 + k)
                acf_res[f"ALL_lag{k}"] = {"rho": pt, "lo": lo, "hi": hi}
            for k in VRK:
                cols = {d: np.array([v[f"vr{k}_s1"], v[f"vr{k}_s2"],
                                     v[f"vr{k}_m"], v["sr"], v["sr2"],
                                     v["n"]])
                        for d, v in rows_all.items()}
                pt, lo, hi, _ = boot_days(cols, lambda M, k=k: vr_from(M, k),
                                          seed=K.SEED + 950 + k)
                vr_res[f"ALL_k{k}"] = {"vr": pt, "lo": lo, "hi": hi}

            # ---- F-PB: pullback depth on theta2 legs -------------------
            piv2 = K.dc_pivots(np.asarray(m5["h"]), np.asarray(m5["l"]),
                               c, abr * TH2)
            pulls = []
            for i in range(2, len(piv2)):
                c1, b1, k1, p1 = piv2[i - 2]
                c2, b2, k2, p2 = piv2[i - 1]
                c3, b3, k3, p3 = piv2[i]
                if k1 == k2 or k2 == k3:
                    continue
                leg1 = abs(p2 - p1)
                leg2 = abs(p3 - p2)
                if leg1 <= 0 or warm[b3]:
                    continue
                A = abr[b3]
                pulls.append({"bar": int(b3), "day": int(day[b3]),
                              "year": int(year[b3]),
                              "frac": float(leg2 / leg1),
                              "depth_abr": float(leg2 / A)
                              if np.isfinite(A) else np.nan})

            # ---- F-EMA: theta1 pivots counter to theta2 direction ------
            piv1 = K.dc_pivots(np.asarray(m5["h"]), np.asarray(m5["l"]),
                               c, abr * TH1)
            # theta2 direction at each bar: -kind of last confirmed pivot
            dir2 = np.zeros(len(c), dtype=np.int64)
            for (ci, ei, kk, pp) in piv2:
                dir2[ci:] = -int(kk)
            emas = {L: K.ema(c, L) for L in EMA_LENS}
            epivs = []
            for (ci, ei, kk, pp) in piv1:
                if warm[ei] or not np.isfinite(abr[ei]) or abr[ei] <= 0:
                    continue
                if dir2[ci] == 0 or kk != -dir2[ci]:
                    continue          # keep only counter-direction pivots
                A = abr[ei]
                e = {"day": int(day[ei]), "year": int(year[ei]),
                     "kind": int(kk)}
                for L in EMA_LENS:
                    e[f"d{L}"] = float(abs(pp - emas[L][ei]) / A)
                epivs.append(e)

            # EMA contrasts: P(|d25|<=x) - P(|dL|<=x), paired, day-boot
            ema_tests = {}
            for Loth in (20, 50):
                for x in (0.5, 1.0):
                    rows = {}
                    for e in epivs:
                        d = e["day"]
                        v = (float(abs(e["d25"]) <= x)
                             - float(abs(e[f"d{Loth}"]) <= x))
                        if d not in rows:
                            rows[d] = [0.0, 0.0]
                        rows[d][0] += v
                        rows[d][1] += 1.0
                    cols = {d: np.array(v) for d, v in rows.items()}
                    pt, lo, hi, p = boot_days(
                        cols, lambda M: M[:, 0].sum() / M[:, 1].sum()
                        if M[:, 1].sum() > 0 else np.nan,
                        seed=K.SEED + 1100 + Loth + int(10 * x))
                    ema_tests[f"ema25-{Loth}_x{x}"] = {
                        "D": pt, "lo": lo, "hi": hi, "p": p}
                    tests.append((f"ema25-{Loth}_x{x}", p))

            # EMA descriptive proximity table
            near = {}
            for L in EMA_LENS:
                d = np.array([e[f"d{L}"] for e in epivs])
                d = d[np.isfinite(d)]
                near[L] = {f"p{int(x * 100)}": float(
                    (d <= x).mean()) if len(d) else np.nan
                    for x in X_BANDS}
                near[L]["med_abs"] = float(np.median(d)) if len(d) \
                    else np.nan
                near[L]["n"] = int(len(d))

            fq = {}
            fr = np.array([e["frac"] for e in pulls])
            fr = fr[np.isfinite(fr)]
            da = np.array([e["depth_abr"] for e in pulls])
            da = da[np.isfinite(da)]
            if len(fr):
                fq = {"n": int(len(fr)),
                      "frac_p25": float(np.quantile(fr, 0.25)),
                      "frac_p50": float(np.quantile(fr, 0.5)),
                      "frac_p75": float(np.quantile(fr, 0.75)),
                      "frac_p90": float(np.quantile(fr, 0.9)),
                      "depth_abr_p50": float(np.median(da)),
                      "depth_abr_p90": float(np.quantile(da, 0.9))}

            q, _ = K.bh(np.nan_to_num([t[1] for t in tests], nan=1.0))
            for (k, _), qq in zip(tests, q):
                if k.startswith("acf_"):
                    acf_res[k[4:]]["q"] = float(qq)
                elif k.startswith("vr_"):
                    vr_res[k[3:]]["q"] = float(qq)
                elif k.startswith("ema"):
                    ema_tests[k]["q"] = float(qq)

            res["symbols"][sym] = {
                "acf": acf_res, "vr": vr_res, "ema_tests": ema_tests,
                "ema_near": {str(L): near[L] for L in EMA_LENS},
                "pullback": fq, "n_piv2": len(piv2), "n_epiv": len(epivs),
                "tests": {k: q_ for (k, _), q_ in zip(tests, q)}}
            print(f"  {sym}: piv2={len(piv2)} pulls={len(pulls)} "
                  f"epivs={len(epivs)}", flush=True)
    K.write_json("m6_results.json", res)
    write_report(res)


def write_report(res):
    L = ["# M6 — Momentum, pullbacks, EMA25 (DESIGN 2016–2021)", "",
         "Descriptive + 12 formal tests per prereg `abc8b5ba…` "
         "(post-review revision: theta1=1.0/theta2=2.5 scales, warmup "
         "excluded, gap-broken segments, EMA L in {15,20,25,35,50}, "
         "B=2000). Sessions in CET.", "",
         "## F-M — formal tests (BH q=0.10, family size 12)", "",
         "| test | D/stat | CI | p | q |", "|---|---|---|---|---|"]
    for s in K.CORE:
        sy = res["symbols"][s]
        for sc in ("ASIA", "EU", "US", "LATE"):
            e = sy["acf"][f"{sc}_lag1"]
            L.append(f"| {s} acf {sc} lag1 | {e['rho']:+.3f} | "
                     f"{e['lo']:+.3f}–{e['hi']:+.3f} | {e.get('p'):.4f} | "
                     f"{e.get('q', float('nan')):.4f} |")
        for sc in ("ASIA", "EU", "US", "LATE"):
            e = sy["vr"][f"{sc}_k12"]
            L.append(f"| {s} VR {sc} k12−1 | {e['vr'] - 1:+.3f} | "
                     f"{e['lo'] - 1:+.3f}–{e['hi'] - 1:+.3f} | "
                     f"{e.get('p_vs1'):.4f} | {e.get('q', float('nan')):.4f} |")
        for k, e in sy["ema_tests"].items():
            L.append(f"| {s} {k} | {e['D']:+.4f} | "
                     f"{e['lo']:+.4f}–{e['hi']:+.4f} | {e['p']:.4f} | "
                     f"{e.get('q', float('nan')):.4f} |")
    L += ["", "## F-AC — M5 log-return autocorrelation (descriptive)", "",
          "| sym | scope | lag1 | lag2 | lag3 | lag4 | lag8 | lag12 |",
          "|---|---|---|---|---|---|---|---|"]
    for s in K.CORE:
        f = res["symbols"][s]["acf"]
        for sc in ("ALL", "ASIA", "EU", "US", "LATE"):
            def g(k):
                v = f.get(f"{sc}_lag{k}", {}).get("rho", np.nan)
                return "nan" if not np.isfinite(v) else f"{v:+.3f}"
            L.append(f"| {s} | {sc} | {g(1)} | {g(2)} | {g(3)} | {g(4)} "
                     f"| {g(8)} | {g(12)} |")
    L += ["", "## F-VR — variance ratios VR(k) (pooled within session)", "",
          "| sym | scope | k=2 | k=4 | k=8 | k=12 | k=24 | k=48 |",
          "|---|---|---|---|---|---|---|---|"]
    for s in K.CORE:
        f = res["symbols"][s]["vr"]
        for sc in ("ALL", "ASIA", "EU", "US", "LATE"):
            def g(k):
                v = f.get(f"{sc}_k{k}", {}).get("vr", np.nan)
                return "nan" if not np.isfinite(v) else f"{v:.3f}"
            L.append(f"| {s} | {sc} | {g(2)} | {g(4)} | {g(8)} | {g(12)} "
                     f"| {g(24)} | {g(48)} |")
    L += ["", "## F-PB — pullback depth within theta2 legs", "",
          "| sym | n | frac p25/50/75/90 | depth ABR p50/p90 |",
          "|---|---|---|---|"]
    for s in K.CORE:
        f = res["symbols"][s]["pullback"]
        if not f:
            continue
        L.append(f"| {s} | {f['n']} | {f['frac_p25']:.2f}/"
                 f"{f['frac_p50']:.2f}/{f['frac_p75']:.2f}/"
                 f"{f['frac_p90']:.2f} | {f['depth_abr_p50']:.2f}/"
                 f"{f['depth_abr_p90']:.2f} |")
    L += ["", "## F-EMA — P(|pivot - EMA_L| <= x*ABR) at counter-trend "
          "theta1 pivots", "",
          "| sym | L | P(.25) | P(.5) | P(1.0) | med |dist| (ABR) | n |",
          "|---|---|---|---|---|---|---|"]
    for s in K.CORE:
        em = res["symbols"][s]["ema_near"]
        for Ln in EMA_LENS:
            d = em[str(Ln)]
            L.append(f"| {s} | {Ln} | {d['p25']:.3f} | {d['p50']:.3f} | "
                     f"{d['p100']:.3f} | {d['med_abs']:.2f} | {d['n']} |")
    path = os.path.join(_HERE, "MOMENTUM.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"[M6] wrote {path}", flush=True)


if __name__ == "__main__":
    main()
