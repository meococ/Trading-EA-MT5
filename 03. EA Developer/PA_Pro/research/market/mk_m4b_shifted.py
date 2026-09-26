"""M4b — SHIFTED-EDGE placebo (P-SHIFT) per STUDY_PLAN_ADDENDUM_M4B.md
(ledger prereg T000392, sha 4abca652…; supersedes T000390 sha 9c1972ac —
same two-arm design, re-registered after post-T000390 caveat edits).

Arm OUT (fake pokes for F-FB): fake edges E_up = hi + g*A_b /
E_dn = lo - g*A_b, g ~ U[0.5,2], alive during the parent box's [b,d);
same streak-merged poke machinery (wick beyond edge, close back);
opposite traversal target at distance h (the parent height).
Arm IN (fake breaks for F-BO): interior level E_in = lo + u*h,
u ~ U[0.2,0.8]; fake break = first close >= tol beyond it while the
parent is alive; same race24/fwd/mfe24 outcomes.

Output: out/m4b_events_<SYM>.npz  (SPK pokes, SBRK breaks)
"""

import hashlib
import os
import sys
import zlib

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import mk_common as K              # noqa: E402
import mk_m4_boxes as MB           # noqa: E402

OUT = K.OUT


def _seed(sym, box_i, side):
    return zlib.crc32(f"{sym}|{box_i}|{side}".encode()) & 0x7FFFFFFF


def shifted_events(bars, abr, tol, sym):
    """Fake-edge events for every real box.  Returns (pokes, breaks)."""
    h = np.asarray(bars["h"]); l = np.asarray(bars["l"])
    c = np.asarray(bars["c"])
    warm = np.asarray(bars["warmup"], dtype=bool)
    day = K.day_id(bars); year = K.server_year(bars)
    cetm = K.cet_minutes(bars); dow = np.asarray(bars["dow"])
    utc_min = np.asarray(bars["utc_min"])
    n = len(c)

    boxes, _p, _b = MB.detect_boxes(bars, abr, tol)
    pokes, brks = [], []
    for i, bx in enumerate(boxes):
        b = bx["born_at"]
        d = bx.get("died_at", n)
        hgt = bx["hi"] - bx["lo"]
        A_b = abr[b]
        if not (np.isfinite(A_b) and A_b > 0):
            continue
        for side in (1, -1):                    # Arm OUT: 1=E_up, -1=E_dn
            rng = np.random.default_rng(_seed(sym, i, side))
            g = 0.5 + 1.5 * float(rng.random())          # U[0.5,2]
            if side > 0:
                E = bx["hi"] + g * A_b
                O = E - hgt
            else:
                E = bx["lo"] - g * A_b
                O = E + hgt
            streak = None
            for t in range(b, min(d, n)):
                if warm[t]:
                    continue
                brk = c[t] > E + tol[t] if side > 0 else \
                    c[t] < E - tol[t]
                if brk:
                    if streak:
                        pokes.append(streak); streak = None
                    brks.append(_ev(t, side, day, year, cetm, dow,
                                    utc_min, abr, E, O, hgt, bx))
                    break                            # edge dies
                is_pk = (h[t] > E and c[t] <= E) if side > 0 else \
                    (l[t] < E and c[t] >= E)
                if is_pk:
                    dep = float(h[t] - E) if side > 0 else \
                        float(E - l[t])
                    if streak is not None:
                        streak["depth"] = max(streak["depth"], dep)
                        streak["end"] = t
                    else:
                        streak = _ev(t, side, day, year, cetm, dow,
                                     utc_min, abr, E, O, hgt, bx)
                        streak["depth"] = dep
                        streak["end"] = t
                elif streak is not None:
                    pokes.append(streak); streak = None
            if streak is not None:
                pokes.append(streak)
        # ---- Arm IN: interior level E_in = lo + u*h, u ~ U[0.2,0.8] ----
        rng = np.random.default_rng(_seed(sym, i, 0))
        u = 0.2 + 0.6 * float(rng.random())
        E_in = bx["lo"] + u * hgt
        for t in range(b, min(d, n)):
            if warm[t]:
                continue
            if c[t] > E_in + tol[t] and c[t - 1] <= E_in + tol[t - 1]:
                brks.append(_ev(t, 1, day, year, cetm, dow, utc_min,
                                abr, E_in, np.nan, hgt, bx))
                break
            if c[t] < E_in - tol[t] and c[t - 1] >= E_in - tol[t - 1]:
                brks.append(_ev(t, -1, day, year, cetm, dow, utc_min,
                                abr, E_in, np.nan, hgt, bx))
                break
    return pokes, brks


def _ev(t, side, day, year, cetm, dow, utc_min, abr, E, O, hgt, bx):
    return {"bar": int(t), "day": int(day[t]), "year": int(year[t]),
            "utc_min": int(utc_min[t]), "cet_min": int(cetm[t]),
            "dow": int(dow[t]), "side": int(side), "abr": float(abr[t]),
            "approach_atr": float("nan"), "edge": float(E),
            "opp": float(O), "hgt_abr": float(hgt / abr[t]),
            "box_h": float(hgt), "box_age": int(t - bx["born_at"]),
            "session": bx["session"]}


def main():
    os.makedirs(OUT, exist_ok=True)
    for sym in K.CORE:
        print(f"[M4b] {sym} ...", flush=True)
        with K.pa_slots.slot(f"dr-market M4b {sym}", timeout=120):
            dd = K.load_symbol(sym)
            m5 = dd["m5"]
            pip = float(m5["pip"])
            abr = K.abr_series(m5)
            tol = K.tol_array(abr, pip)
            spk, sbrk = shifted_events(m5, abr, tol, sym)
            print(f"  {sym}: shifted-edge {len(spk)} pokes, "
                  f"{len(sbrk)} breaks", flush=True)
            cc = np.asarray(m5["c"])
            for e in sbrk:
                e["res"] = {"race24": MB.race24(m5, e["bar"], e["edge"],
                                              e["side"], e["abr"]),
                            "mfe24": MB.mfe(m5, e["bar"], e["edge"],
                                            e["side"], e["abr"])}
                for H in K.HORIZONS:
                    j = e["bar"] + H
                    e["res"][f"fwd_{H}"] = float(
                        (cc[j] - cc[e["bar"]]) * e["side"]) \
                        if j < len(cc) else np.nan
            for p in spk:
                p["res"] = MB.resolve_poke_plac(m5, p)
                conv = False
                tol_t = float(tol[p["bar"]])
                for u in range(p["end"] + 1,
                               min(len(cc),
                                   p["end"] + 1 + MB.CONV_HORIZON)):
                    if (p["side"] > 0 and cc[u] > p["edge"] + tol_t) or \
                            (p["side"] < 0 and cc[u] < p["edge"] - tol_t):
                        conv = True
                        break
                p["res"]["converted"] = conv
            npz = {}
            sesc = {"ASIA": 0, "EU": 1, "US": 2, "LATE": 3}
            for name, ev in (("SPK", spk), ("SBRK", sbrk)):
                keys = ["bar", "end", "day", "year", "utc_min", "cet_min",
                        "dow", "side", "abr", "approach_atr", "edge",
                        "opp", "hgt_abr", "depth", "box_age"]
                for kk in keys:
                    npz[f"{name}__{kk}"] = np.array(
                        [float(e.get(kk, np.nan)) for e in ev],
                        dtype=np.float64)
                npz[f"{name}__session"] = np.array(
                    [sesc.get(e["session"], np.nan) for e in ev],
                    dtype=np.float64)
                npz[f"{name}__box_h_pips"] = np.array(
                    [e["box_h"] / pip for e in ev], dtype=np.float64)
            npz["SPK__depth_pips"] = np.array(
                [p["depth"] / pip for p in spk], dtype=np.float64)
            for kk in ("reach_opp", "converted"):
                npz[f"SPK__{kk}"] = np.array(
                    [float(p["res"][kk]) for p in spk], dtype=np.float64)
            for kk in [f"fwd_{H}" for H in K.HORIZONS] + \
                    ["race24", "mfe24"]:
                npz[f"SBRK__{kk}"] = np.array(
                    [e["res"].get(kk, np.nan) for e in sbrk],
                    dtype=np.float64)
            path = os.path.join(OUT, f"m4b_events_{sym}.npz")
            np.savez_compressed(path, **npz)
            sha = hashlib.sha256(open(path, "rb").read()).hexdigest()[:12]
            print(f"  {sym}: wrote {path} sha={sha}", flush=True)


if __name__ == "__main__":
    main()
