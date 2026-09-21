"""phys_resolve — BOUNCE / BREAK / NONE + break-continuation resolver.

Implements `PHYSICS_PREREG_DRAFT.md` section 4.  RUN ONLY AFTER
`rounds/R01/FREEZE.json` EXISTS — this is the only module in the package that
reads bars after the event bar.

M5 completeness (`pa_data.resample`) makes each M5 bar's own high/low the exact
M1-path extremes of that bar, so the "first touch on the M1 path" rule reduces
to `l[j] <= level <= h[j]`; within-bar ordering is resolved by the frozen
adverse-first convention (BREAK beats BOUNCE in the same M5 bar; RETURN beats
CONTINUATION in the same M5 bar).  This equivalence is declared in the prereg.
"""

import numpy as np

import phys_common as pc

__all__ = ["resolve_events", "RESULT_FIELDS"]

RESULT_FIELDS = [
    "outcome", "bounce_bar", "break_bar", "break_close",
    "cont_outcome", "cont_bar", "return_bar", "resolved", "window_ok",
]


def _touch(l, h, lvl):
    return (l <= lvl) & (h >= lvl)


def resolve_events(events, bars):
    """Resolve one event table.  Returns (results, counters).

    `events` rows must carry: bar_idx, side, lo, hi, near, far, m.
    """
    l = np.asarray(bars["l"], dtype=np.float64)
    h = np.asarray(bars["h"], dtype=np.float64)
    c = np.asarray(bars["c"], dtype=np.float64)
    n = len(c)
    out = []
    counters = {
        "events": 0, "dropped_window": 0, "bounce": 0, "break": 0, "none": 0,
        "resolved": 0, "cont_window_missing": 0, "cont": 0, "ret": 0,
        "cont_none": 0,
    }
    for e in events:
        t = int(e["bar_idx"])
        side = int(e["side"])
        m = float(e["m"])
        near = float(e["near"])
        far = float(e["far"])
        zmid = 0.5 * (float(e["lo"]) + float(e["hi"]))
        if t + pc.HORIZON >= n:
            out.append({"outcome": "DROPPED", "window_ok": False,
                        "resolved": False, "cont_outcome": "DROPPED"})
            counters["dropped_window"] += 1
            continue
        j0 = t + 1
        j1 = t + pc.HORIZON
        outcome = "NONE"
        bounce_bar = break_bar = -1
        break_close = float("nan")
        for j in range(j0, j1 + 1):
            if side == -1:
                lvl = near - m
                brk = c[j] >= far + m
            else:
                lvl = near + m
                brk = c[j] <= far - m
            if brk:
                outcome = "BREAK"
                break_bar = j
                break_close = float(c[j])
                break
            if _touch(l[j], h[j], lvl):
                outcome = "BOUNCE"
                bounce_bar = j
                break
        cont_outcome = "NONE"
        cont_bar = ret_bar = -1
        if outcome == "BREAK":
            side_b = -side
            c_b = break_close
            k0 = break_bar + 1
            k1 = break_bar + pc.HORIZON
            if k1 >= n:
                cont_outcome = "DROPPED"
                counters["cont_window_missing"] += 1
            else:
                lvl_cont = c_b + side_b * m
                for k in range(k0, k1 + 1):
                    hit_ret = bool(_touch(l[k], h[k], zmid))
                    hit_cont = bool(_touch(l[k], h[k], lvl_cont))
                    if hit_ret and hit_cont:
                        cont_outcome = "RETURN"
                        ret_bar = k
                        break
                    if hit_ret:
                        cont_outcome = "RETURN"
                        ret_bar = k
                        break
                    if hit_cont:
                        cont_outcome = "CONT"
                        cont_bar = k
                        break
        out.append({
            "outcome": outcome,
            "bounce_bar": bounce_bar,
            "break_bar": break_bar,
            "break_close": break_close,
            "cont_outcome": cont_outcome,
            "cont_bar": cont_bar,
            "return_bar": ret_bar,
            "resolved": outcome in ("BOUNCE", "BREAK"),
            "window_ok": True,
        })
        counters["events"] += 1
        counters[outcome.lower()] += 1
        if outcome in ("BOUNCE", "BREAK"):
            counters["resolved"] += 1
        if outcome == "BREAK":
            if cont_outcome == "CONT":
                counters["cont"] += 1
            elif cont_outcome == "RETURN":
                counters["ret"] += 1
            elif cont_outcome == "NONE":
                counters["cont_none"] += 1
    return out, counters


def is_bounce(results, i):
    return 1.0 if results[i]["outcome"] == "BOUNCE" else 0.0


def is_break(results, i):
    return 1.0 if results[i]["outcome"] == "BREAK" else 0.0


def bounce_cond(results, i):
    r = results[i]
    if r["outcome"] == "BOUNCE":
        return 1.0
    if r["outcome"] == "BREAK":
        return 0.0
    return None


def cont_cond(results, i):
    r = results[i]
    if r["outcome"] != "BREAK":
        return None
    if r["cont_outcome"] == "CONT":
        return 1.0
    if r["cont_outcome"] == "RETURN":
        return 0.0
    return None
