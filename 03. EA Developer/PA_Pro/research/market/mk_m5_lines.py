"""M5 — TREND LINES (DESIGN only).

Preregistered (STUDY_PLAN.md / ledger T000364), revised after the M8
review (see DEVIATIONS):

  A trend line is drawn through two consecutive same-kind THETA2 causal
  pivots (theta2 = 2.5 ABR directional-change pivots, plan §6).  The line
  is born at the
  CONFIRM bar of the second pivot (causal) and lives until the first close
  beyond line +- tol (a break) or 288 bars, whichever first.

  "Third touch" = first bar after birth that intersects the line zone
  (line +- tol) after > FRESH bars without ANY zone intersection and an
  approach of >= AWAY*ABR within the lookback window.  (Review fix:
  freshness now counts every zone hit, not only accepted events, and the
  resolver evaluates the line at the same bar index as the detector —
  the previous M1-time extrapolation disagreed with detection across
  feed gaps by up to ~650 ABR.)

  Placebo (the DECLARED one, plan §6): for each real line, 2 placebo
  lines sharing the anchor times and slope, price-shifted by
  +/- delta*abr[birth], delta ~ U[1.5,4] seeded per line.  Placebo lines
  die by the same close-beyond rule and are scanned by the same touch
  machinery, so a placebo event exists only when price actually reaches
  the synthetic zone (exchangeable with real touches).

  Families:
    F-TL    P(bounce x1 / x2) at the third touch (touch_no==1) vs placebo.
    F-SLOPE after a line break: 24-bar continuation race (>=1*ABR cont
            before >=1*ABR rev) — rising vs (flat|falling), per direction.

Output: out/m5_events_<SYM>.npz, out/m5_results.json, LINES.md.
"""

import hashlib
import os
import sys
import zlib

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import mk_common as K  # noqa: E402

OUT = K.OUT
PIP = {"EURUSD": 1e-4, "GBPUSD": 1e-4, "USDJPY": 1e-2, "AUDUSD": 1e-4}
YEARS = list(range(2016, 2022))
SYM_I = {s: i for i, s in enumerate(K.CORE)}

LIFE = 288                    # bars a line stays active
FLAT_EPS = 0.02               # |slope| <= 0.02 ABR/bar counts as flat
HOR = 48
RACE_Y, RACE_H = 1.0, 24      # post-break continuation race


# ------------------------------------------------------------ line build
def _line_death(c, tol, birth, L0, m, kind, n):
    """First bar >= birth where the close is beyond line+-tol (the side
    that breaks the line), else birth+LIFE.  Vectorised."""
    e0 = min(n, birth + LIFE)
    idx = np.arange(birth, e0)
    lv = L0 + m * (idx - birth)
    if kind == -1:
        died = c[birth:e0] < lv - tol[birth:e0]
    else:
        died = c[birth:e0] > lv + tol[birth:e0]
    j = np.flatnonzero(died)
    return int(birth + j[0]) if len(j) else int(e0)


def build_lines(m5, abr):
    """Lines through consecutive same-kind theta2 pivots.  Returns list of
    dicts(birth, death, L0 (value at birth), m (price/bar), kind, len_bars,
    anchor bars/prices)."""
    piv = K.dc_pivots(np.asarray(m5["h"]), np.asarray(m5["l"]),
                      np.asarray(m5["c"]), abr * 2.5)
    c = np.asarray(m5["c"])
    tol = K.tol_array(abr, float(m5["pip"]))
    n = len(c)
    lines = []
    for k in range(len(piv) - 2):
        c1, b1, k1, p1 = piv[k]
        c2, b2, k2, p2 = piv[k + 2]
        if k1 != k2 or b2 <= b1:
            continue
        birth = c2
        m = (p2 - p1) / float(b2 - b1)
        L0 = p1 + m * (birth - b1)
        death = _line_death(c, tol, int(birth), L0, m, int(k1), n)
        if death <= birth:
            continue
        lines.append({"birth": int(birth), "death": int(death),
                      "L0": float(L0), "m": float(m), "kind": int(k1),
                      "len_bars": int(b2 - b1), "b1": int(b1),
                      "b2": int(b2), "p1": float(p1), "p2": float(p2)})
    return lines


def placebo_lines(lines, abr, m5, seed=K.SEED):
    """Declared placebo: per real line, 2 copies sharing birth/slope/kind,
    price-shifted by +/- delta*abr[birth], delta ~ U[1.5,4].  Each copy
    gets its own causal death scan.  lid = -(2*li+1/-(2*li+2))."""
    c = np.asarray(m5["c"])
    tol = K.tol_array(abr, float(m5["pip"]))
    n = len(c)
    rng = np.random.default_rng(seed)
    out = []
    for li, ln in enumerate(lines):
        A = abr[ln["birth"]]
        if not np.isfinite(A) or A <= 0:
            continue
        for si, sgn in enumerate((+1, -1)):
            d = float(rng.uniform(1.5, 4.0))
            L0 = ln["L0"] + sgn * d * A
            death = _line_death(c, tol, ln["birth"], L0, ln["m"],
                                ln["kind"], n)
            if death <= ln["birth"]:
                continue
            out.append({"birth": ln["birth"], "death": int(death),
                        "L0": float(L0), "m": ln["m"], "kind": ln["kind"],
                        "len_bars": ln["len_bars"],
                        "lid": -(2 * li + 1 + si),
                        "shift_abr": sgn * d})
    return out


def detect_line_touches(m5, lines, abr, tol, fresh=K.FRESH, away=K.AWAY):
    """Touch events on each line's active window (causal).

    Freshness: the event bar must follow > `fresh` bars with NO zone
    intersection of this line (zone-hit tracking, not just events).
    """
    h = np.asarray(m5["h"]); l = np.asarray(m5["l"]); c = np.asarray(m5["c"])
    warm = np.asarray(m5["warmup"], dtype=bool)
    day = K.day_id(m5); year = K.server_year(m5)
    cetm = K.cet_minutes(m5); dow = np.asarray(m5["dow"])
    utc_min = np.asarray(m5["utc_min"])
    events = []
    for li, ln in enumerate(lines):
        s, e = ln["birth"], ln["death"]
        if e <= s + 1:
            continue
        tt = np.arange(s, e)
        lv = ln["L0"] + ln["m"] * (tt - s)
        zlo = lv - tol[s:e]
        zhi = lv + tol[s:e]
        inter = (l[s:e] <= zhi) & (h[s:e] >= zlo)
        last_hit = -10 ** 9
        tno = 0
        for j in np.flatnonzero(inter):
            t = s + int(j)
            is_fresh = (t - last_hit) > fresh
            last_hit = t                      # every zone hit counts
            if not is_fresh or t == 0 or warm[t] \
                    or not np.isfinite(abr[t]) or abr[t] <= 0:
                continue
            w0 = max(s, t - fresh)
            dc = np.maximum(zlo[j] - c[w0:t], c[w0:t] - zhi[j])
            if not (dc >= away * abr[t]).any():
                continue
            cp = c[t - 1]
            if cp <= zlo[j]:
                side = -1
            elif cp >= zhi[j]:
                side = +1
            else:
                continue
            tno += 1
            events.append({
                "bar": int(t), "day": int(day[t]), "year": int(year[t]),
                "utc_min": int(utc_min[t]), "cet_min": int(cetm[t]),
                "dow": int(dow[t]), "side": int(side),
                "abr": float(abr[t]), "tol": float(tol[t]),
                "approach_atr": float(dc.max() / abr[t]),
                "dist_cp": float(abs(lv[j] - cp) / abr[t]),
                "age_bars": int(t - s),
                "lid": ln.get("lid", li),
                "kind": ln["kind"], "touch_no": tno,
                "L0": ln["L0"], "m": ln["m"], "birth": ln["birth"],
                "death": ln["death"], "len_bars": ln["len_bars"],
                "slope_abr": ln["m"] / abr[t],
                "level": float(lv[j]), "zlo": float(zlo[j]),
                "zhi": float(zhi[j]),
            })
    return events


def detect_line_breaks(m5, lines, abr, tol):
    """Line-death bars that are genuine breaks (close beyond line+-tol)."""
    c = np.asarray(m5["c"])
    warm = np.asarray(m5["warmup"], dtype=bool)
    day = K.day_id(m5); year = K.server_year(m5)
    cetm = K.cet_minutes(m5); dow = np.asarray(m5["dow"])
    utc_min = np.asarray(m5["utc_min"])
    n = len(c)
    evs = []
    for li, ln in enumerate(lines):
        d = ln["death"]
        if d < min(n, ln["birth"] + LIFE):
            lv = ln["L0"] + ln["m"] * (d - ln["birth"])
            brk = (ln["kind"] == -1 and c[d] < lv - tol[d]) or \
                  (ln["kind"] == +1 and c[d] > lv + tol[d])
            if brk and np.isfinite(abr[d]) and not warm[d]:
                evs.append({
                    "bar": int(d), "day": int(day[d]), "year": int(year[d]),
                    "utc_min": int(utc_min[d]), "cet_min": int(cetm[d]),
                    "dow": int(dow[d]),
                    "side": ln["kind"],  # break dir: +1 up break of a
                    # resistance line, -1 down break of a support line
                    "abr": float(abr[d]), "tol": float(tol[d]),
                    "approach_atr": np.nan,
                    "lid": ln.get("lid", li), "kind": ln["kind"],
                    "L0": ln["L0"], "m": ln["m"], "birth": ln["birth"],
                    "len_bars": ln["len_bars"],
                    "slope_abr": ln["m"] / abr[d],
                    "level": lv,
                })
    return evs


# ------------------------------------------------------------ resolution
def resolve_touch(m1, m5, ev, xs=(1.0, 2.0), horizon=HOR):
    """Bounce/break race vs the MOVING line (M1 granularity).

    The line value at each M1 bar is evaluated at the parent M5 bar INDEX
    (identical geometry to the detector); barriers are relative to it.
    """
    t = ev["bar"]; A = ev["abr"]; side = ev["side"]
    m1t = np.asarray(m1["t"]); m5t = np.asarray(m5["t"])
    t1 = min(len(m5t), t + horizon)
    a, b = K.m1_window_for_bars(m1t, m5t, t, t1)
    h = m1["h"]; l = m1["l"]
    par = np.searchsorted(m5t, m1t[a:b], side="right") - 1   # parent M5 idx
    lvv = ev["L0"] + ev["m"] * (par - ev["birth"])
    # touch minute within M5 bar t
    a_end = int(np.searchsorted(m1t, m5t[t] + 300, side="left"))
    start = a_end
    for j in range(a, a_end):
        lvj = lvv[j - a]
        if l[j] <= lvj + ev["tol"] and h[j] >= lvj - ev["tol"]:
            start = j + 1
            break
    first = {"b1": None, "n1": None, "b2": None, "n2": None}
    keys = list(xs)
    i = start
    while i < b:
        lvj = lvv[i - a]
        zlo, zhi = lvj - ev["tol"], lvj + ev["tol"]
        hi = h[i]; lo = l[i]
        if side == -1:          # approached from below (line = resistance)
            if first["b1"] is None and hi >= zhi + keys[0] * A:
                first["b1"] = i
            if first["n1"] is None and lo <= zlo - keys[0] * A:
                first["n1"] = i
            if first["b2"] is None and hi >= zhi + keys[1] * A:
                first["b2"] = i
            if first["n2"] is None and lo <= zlo - keys[1] * A:
                first["n2"] = i
        else:
            if first["b1"] is None and lo <= zlo - keys[0] * A:
                first["b1"] = i
            if first["n1"] is None and hi >= zhi + keys[0] * A:
                first["n1"] = i
            if first["b2"] is None and lo <= zlo - keys[1] * A:
                first["b2"] = i
            if first["n2"] is None and hi >= zhi + keys[1] * A:
                first["n2"] = i
        i += 1
    res = {}
    for xi, x in enumerate(keys):
        fb = first[f"b{xi + 1}"]; fn = first[f"n{xi + 1}"]
        if fb is None and fn is None:
            oc = "NONE"
        elif fb is None:
            oc = "BOUNCE"
        elif fn is None:
            oc = "BREAK"
        else:
            oc = "BREAK" if fb < fn else "BOUNCE"
        res[f"out_x{x:g}"] = oc
    return res


def resolve_fwd(m5, ev, horizons=K.HORIZONS):
    t = ev["bar"]; side = ev["side"]
    c = np.asarray(m5["c"])
    return {f"fwd_{H}": float((c[t + H] - c[t]) * side)
            if t + H < len(c) else np.nan
            for H in horizons}


def resolve_cont(m5, ev, y=RACE_Y, horizon=RACE_H):
    """Post-break continuation race: +1 if price continues >= y*ABR in the
    break direction (from c[t]) before reversing >= y*ABR, within horizon
    M5 bars; 0 if reversal first; NaN if neither."""
    t = ev["bar"]; side = ev["side"]; A = ev["abr"]
    if not np.isfinite(A) or A <= 0:
        return np.nan
    c = np.asarray(m5["c"]); h = np.asarray(m5["h"]); l = np.asarray(m5["l"])
    up = c[t] + y * A
    dn = c[t] - y * A
    n = len(c)
    for u in range(t + 1, min(n, t + 1 + horizon)):
        if side > 0:
            if h[u] >= up:
                return 1.0
            if l[u] <= dn:
                return 0.0
        else:
            if l[u] <= dn:
                return 1.0
            if h[u] >= up:
                return 0.0
    return np.nan


# ---------------------------------------------------------------- main
def main():
    os.makedirs(OUT, exist_ok=True)
    for sym in K.CORE:
        print(f"[M5] {sym} ...", flush=True)
        with K.pa_slots.slot(f"dr-market M5 {sym}", timeout=120):
            dd = K.load_symbol(sym)
            m1, m5 = dd["m1"], dd["m5"]
            abr = K.abr_series(m5)
            tol = K.tol_array(abr, float(m5["pip"]))
            lines = build_lines(m5, abr)
            plines = placebo_lines(lines, abr, m5,
                                   seed=K.SEED + zlib.crc32(
                                       sym.encode()))
            touches = detect_line_touches(m5, lines, abr, tol)
            plac = detect_line_touches(m5, plines, abr, tol)
            breaks = detect_line_breaks(m5, lines, abr, tol)
            pbr = detect_line_breaks(m5, plines, abr, tol)
            print(f"  {sym}: {len(lines)} lines, {len(touches)} touches, "
                  f"{len(breaks)} breaks | plac {len(plines)} lines, "
                  f"{len(plac)} touches, {len(pbr)} breaks", flush=True)
            for e in touches:
                e["res"] = resolve_touch(m1, m5, e)
            for e in plac:
                e["res"] = resolve_touch(m1, m5, e)
            for e in breaks:
                e["res"] = resolve_fwd(m5, e)
                e["res"]["cont24"] = resolve_cont(m5, e)
            for e in pbr:
                e["res"] = resolve_fwd(m5, e)
                e["res"]["cont24"] = resolve_cont(m5, e)
            npz = {}
            keys = ["bar", "day", "year", "utc_min", "cet_min", "dow",
                    "side", "abr", "tol", "approach_atr", "dist_cp",
                    "age_bars", "lid", "kind", "touch_no", "L0", "m",
                    "birth", "len_bars", "slope_abr", "level", "zlo",
                    "zhi", "shift_abr"]
            for name, ev in (("TOUCH", touches), ("TPLAC", plac),
                             ("BREAK", breaks), ("BPLAC", pbr)):
                for kk in keys:
                    npz[f"{name}__{kk}"] = np.array(
                        [e.get(kk, np.nan) for e in ev], dtype=np.float64)
                for kk in ("out_x1", "out_x2", "cont24") + tuple(
                        f"fwd_{H}" for H in K.HORIZONS):
                    vals = []
                    for e in ev:
                        v = e["res"].get(kk)
                        if isinstance(v, str):
                            vals.append({"BOUNCE": 0, "BREAK": 1,
                                         "NONE": 2}[v])
                        elif v is None:
                            vals.append(-1.0)
                        elif isinstance(v, bool):
                            vals.append(float(v))
                        else:
                            vals.append(float(v))
                    npz[f"{name}__{kk}"] = np.array(vals, dtype=np.float64)
            path = os.path.join(OUT, f"m5_events_{sym}.npz")
            np.savez_compressed(path, **npz)
            sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
            print(f"  {sym} saved sha={sha[:12]}", flush=True)
    print("[M5] extraction done.")


if __name__ == "__main__":
    main()
