"""volman_setups.py — Q2' draft detectors for the five Volman setups.

Pre-P-FREEZE work per LEAD_RULINGS Review 1: detectors are written
against the minimal Snapshot contract in
rounds/SF02/q2prime/SNAPSHOT_CONTRACT.md and exercised on synthetic
fixtures only.  No census, no screen, no prereg — binding versions are
re-specified on the frozen Snapshot API later.

Setups: PB (pattern break), PBP (pattern break pullback),
PBC (combi), PR (pullback reversal), TFF (trade-for-failure).

Each detect_*(snap, params) inspects ONE closed bar (the snapshot's
current bar t) and returns a signal dict {sig, side, order_px, inv,
why} or None.  Everything is causal by construction: the fixture only
contains bars <= t and objects known at t.
"""

import numpy as np

# ---------------------------------------------------------------- shared

DEFAULTS = {
    "room_pips": 14.0,        # 14-pip obstacle rule (p167)
    "room_soft": 13.0,
    "tol_min_pips": 1.0,      # edge tol = max(1 pip, 0.25*ABR)
    "tol_abr": 0.25,
    "buf_pips": 1.0,
    "strong_range_abr": 1.5,  # combi strong bar
    "sig_range_abr": 1.0,     # TFF reversal bar
    "edge_band_abr": 1.0,     # buildup "resting on the edge"
    "tff_lookback": 24,       # bars since the counter-break
    "pull_max": 48,           # PR pullback scan window
}


def _P(params):
    p = dict(DEFAULTS)
    p.update(params or {})
    return p


def tol_pips(snap, p):
    return max(p["tol_min_pips"], p["tol_abr"] * float(snap["abr"]))


def pressure(snap):
    """+1 UP / -1 DOWN / 0 otherwise."""
    s = (snap.get("pressure") or {}).get("state", "NEUTRAL")
    return {"UP": 1, "DOWN": -1}.get(s, 0)


def stand_aside(snap):
    return list((snap.get("facts") or {}).get("stand_aside") or [])


def room_ok(snap, side, entry_px, p):
    """First real obstacle in the trade direction >= room_pips."""
    f = (snap.get("facts") or {})
    obs = f.get("obstacles_up" if side > 0 else "obstacles_dn") or []
    if not obs:
        return True                      # nothing mapped = clear air
    d = min(o["dist_pips"] for o in obs)
    return d >= p["room_pips"]


def _long_bars_nearby(snap, p, k=3, before=1):
    """Veto: abnormal long bars (>= 2*ABR) in the k bars ending
    `before` bars back — the signal bar (and for a combi the strong
    bar) may legitimately be strong."""
    abr_px = float(snap["abr"]) * float(snap["pip"])
    h, l = snap["h"], snap["l"]
    t = snap["t"] - before + 1
    lo = max(0, t - k)
    return bool(np.any((h[lo:t] - l[lo:t]) >= 2.0 * abr_px))


def boxes(snap, states=("live",)):
    return [o for o in snap.get("objects", [])
            if o.get("type") == "BOX" and o.get("state") in states]


def lines(snap, types=("PATTERN_LINE", "MINI_LEVEL")):
    return [o for o in snap.get("objects", []) if o.get("type") in types]


def _edge_touch_count(box, side):
    """Touches recorded on the breakout-side edge."""
    n = 0
    for tc in box.get("touches") or []:
        if (tc.get("edge") == "hi") == (side > 0):
            n += 1
    return n


def _break_edge(box, side):
    return float(box["hi"] if side > 0 else box["lo"])


def _proper_buildup(snap, box, side, p):
    """Bars just before the break rest ON the edge with shrinking
    ranges (spec §3.3 'proper'); facts.break_class wins if present."""
    bc = (snap.get("facts") or {}).get("break_class")
    if bc and bc.get("obj_id") == box.get("id"):
        return bc.get("cls") == "proper"
    t = snap["t"]
    h, l, c = snap["h"], snap["l"], snap["c"]
    edge = _break_edge(box, side)
    band = p["edge_band_abr"] * snap["abr"] * snap["pip"]
    on_edge = sum(1 for j in range(max(0, t - 3), t)
                  if abs(float(c[j]) - edge) <= band
                  or (side > 0 and float(h[j]) >= edge - band)
                  or (side < 0 and float(l[j]) <= edge + band))
    rng = h[max(0, t - 3):t] - l[max(0, t - 3):t]
    shrinking = len(rng) == 0 or float(rng[-1]) <= float(np.mean(rng))
    return on_edge >= 2 and shrinking


def _sig(side, snap, order_px, inv, why):
    return {"sig": int(snap["t"]), "side": int(side),
            "order_px": float(order_px), "inv": float(inv),
            "why": why}


def _entry_px(snap, side, p):
    """Stop order buf beyond the signal bar's with-trend extreme."""
    t = snap["t"]
    buf = p["buf_pips"] * snap["pip"]
    return (float(snap["h"][t]) + buf) if side > 0 else \
        (float(snap["l"][t]) - buf)


# ---------------------------------------------------------------- PB

def detect_pb(snap, params=None):
    """Pattern break: with-pressure close beyond (or ON) a frozen box
    edge out of a proper buildup; 14-pip room."""
    p = _P(params)
    if stand_aside(snap) or _long_bars_nearby(snap, p):
        return None
    d = pressure(snap)
    if d == 0:
        return None
    t = snap["t"]
    c = float(snap["c"][t])
    tol = tol_pips(snap, p) * snap["pip"]
    for box in boxes(snap, ("live",)):
        if box.get("t_left", 0) > t:
            continue
        if _edge_touch_count(box, d) < 2:
            continue
        edge = _break_edge(box, d)
        # break = close beyond the edge by >= tol (spec 3.3); a close ON
        # the edge counts only when a squeeze fills the last gap
        beyond = (c >= edge + tol) if d > 0 else (c <= edge - tol)
        on_it = abs(c - edge) <= tol and \
            (snap.get("facts") or {}).get("squeeze") is not None
        if not (beyond or on_it):
            continue
        if not _proper_buildup(snap, box, d, p):
            continue
        px = _entry_px(snap, d, p)
        if not room_ok(snap, d, px, p):
            continue
        inv = float(box["lo"] if d > 0 else box["hi"])
        return _sig(d, snap, px, inv, "pb")
    return None


# ---------------------------------------------------------------- PBP

def detect_pbp(snap, params=None):
    """Pullback to a broken edge's extension; trigger = poke through +
    close back with-trend, or a stall on the line."""
    p = _P(params)
    if stand_aside(snap) or _long_bars_nearby(snap, p):
        return None
    d = pressure(snap)
    if d == 0:
        return None
    t = snap["t"]
    tol = tol_pips(snap, p) * snap["pip"]
    h, l, c = (snap["h"], snap["l"], snap["c"])
    for box in boxes(snap, ("broken",)):
        edge = _break_edge(box, d)
        # pullback reached the extension and closed back on our side
        pokes = (float(l[t]) <= edge + tol and float(c[t]) >= edge) \
            if d > 0 else \
            (float(h[t]) >= edge - tol and float(c[t]) <= edge)
        if not pokes:
            continue
        # must not have re-entered deep (far half of the old box)
        mid = 0.5 * (float(box["hi"]) + float(box["lo"]))
        too_deep = (float(l[t]) < mid) if d > 0 else (float(h[t]) > mid)
        if too_deep:
            continue
        px = _entry_px(snap, d, p)
        if not room_ok(snap, d, px, p):
            continue
        inv = float(l[t]) - p["buf_pips"] * snap["pip"] if d > 0 else \
            float(h[t]) + p["buf_pips"] * snap["pip"]
        return _sig(d, snap, px, inv, "pbp")
    return None


# ---------------------------------------------------------------- PBC

def _strong_bar(snap, j, d, p):
    """Bar j is a strong bar in direction d: range >= 1.5*ABR and the
    close sits in the with-trend third."""
    rng = float(snap["h"][j]) - float(snap["l"][j])
    if rng < p["strong_range_abr"] * snap["abr"] * snap["pip"]:
        return False
    c, o = float(snap["c"][j]), float(snap["o"][j])
    third = rng / 3.0
    if d > 0:
        return c >= float(snap["h"][j]) - third and c > o
    return c <= float(snap["l"][j]) + third and c < o


def _inside_bar(snap, j):
    return float(snap["h"][j]) <= float(snap["h"][j - 1]) and \
        float(snap["l"][j]) >= float(snap["l"][j - 1])


def _inside_colour_ok(snap, j, d):
    o, c = float(snap["o"][j]), float(snap["c"][j])
    pj = j - 1
    mid = 0.5 * (float(snap["h"][pj]) + float(snap["l"][pj]))
    if (d > 0 and c >= o) or (d < 0 and c <= o):
        return True                       # same colour
    flat = abs(c - o) <= 0.2 * (float(snap["h"][j]) - float(snap["l"][j]))
    if flat:
        return True                       # neutral doji body
    # opposite colour acceptable only in the with-trend half of bar j-1
    return (c >= mid) if d > 0 else (c <= mid)


def detect_pbc(snap, params=None):
    """Combi: strong bar + inside bar AT a breakout boundary, entry on
    the inside-bar break.  Timing tool only — needs the context."""
    p = _P(params)
    if stand_aside(snap) or _long_bars_nearby(snap, p, k=1, before=2):
        return None
    d = pressure(snap)
    if d == 0:
        return None
    t = snap["t"]
    if t < 1 or not _inside_bar(snap, t):
        return None
    if not _strong_bar(snap, t - 1, d, p):
        return None
    if not _inside_colour_ok(snap, t, d):
        return None
    # context: a boundary object within ~1*ABR of the pair
    band = p["edge_band_abr"] * snap["abr"] * snap["pip"]
    hi = float(snap["h"][t])
    lo = float(snap["l"][t])
    near = False
    for o in snap.get("objects", []):
        if o.get("type") in ("BOX", "LEVEL_CARRIED", "MINI_LEVEL"):
            e = _break_edge(o, d) if "hi" in o else None
            if e is not None and abs(e - (hi if d > 0 else lo)) <= band:
                near = True
        elif o.get("type") == "PATTERN_LINE" and "a" in o:
            lv = float(o["a"]) * t + float(o["b"])
            if abs(lv - (hi if d > 0 else lo)) <= band:
                near = True
    if not near:
        return None
    px = _entry_px(snap, d, p)
    if not room_ok(snap, d, px, p):
        return None
    inv = float(snap["l"][t]) - p["buf_pips"] * snap["pip"] if d > 0 \
        else float(snap["h"][t]) + p["buf_pips"] * snap["pip"]
    return _sig(d, snap, px, inv, "pbc")


# ---------------------------------------------------------------- PR

def detect_pr(snap, params=None):
    """Pullback reversal: counter-wave to EMA25 turns back with the
    pressure.  Trigger = with-trend close through the pullback's own
    PATTERN_LINE / MINI_LEVEL, or a second break (2-bar high/low)."""
    p = _P(params)
    if stand_aside(snap) or _long_bars_nearby(snap, p):
        return None
    d = pressure(snap)
    if d == 0:
        return None
    t = snap["t"]
    ema = snap["ema25"]
    l, h, c = snap["l"], snap["h"], snap["c"]
    lo = max(1, t - p["pull_max"])
    # a) the pullback touched/pierced EMA25 within the window
    if d > 0:
        touched = np.any(l[lo:t] <= ema[lo:t])
    else:
        touched = np.any(h[lo:t] >= ema[lo:t])
    if not touched:
        return None
    # b) trigger: with-trend break of a trigger object or 2-bar extreme
    trig = False
    tol = tol_pips(snap, p) * snap["pip"]
    for o in lines(snap):
        if o.get("role") not in (None, "pullback", "mw_mid", "trigger"):
            continue
        if "a" in o:                              # PATTERN_LINE px = a*t+b
            lv = float(o["a"]) * t + float(o["b"])
            trig = trig or ((c[t] >= lv - tol) if d > 0
                            else (c[t] <= lv + tol))
        elif "hi" in o:                           # MINI_LEVEL
            lv = float(o["hi"] if d > 0 else o["lo"])
            trig = trig or ((c[t] >= lv) if d > 0 else (c[t] <= lv))
    if not trig:
        prev2 = max(float(h[t - 1]), float(h[t - 2])) if t >= 2 else 0
        prev2l = min(float(l[t - 1]), float(l[t - 2])) if t >= 2 else 0
        trig = (c[t] > prev2) if d > 0 else (c[t] < prev2l)
    if not trig:
        return None
    px = _entry_px(snap, d, p)
    if not room_ok(snap, d, px, p):
        return None
    inv = float(np.min(l[lo:t + 1])) - p["buf_pips"] * snap["pip"] \
        if d > 0 else \
        float(np.max(h[lo:t + 1])) + p["buf_pips"] * snap["pip"]
    return _sig(d, snap, px, inv, "pr")


# ---------------------------------------------------------------- TFF

def detect_tff(snap, params=None):
    """Trade-for-failure: a counter-pressure break failed; the signal
    bar is a strong reversal bar whose extreme is back across the
    barrier (barrier-reclaim rule)."""
    p = _P(params)
    if stand_aside(snap) or _long_bars_nearby(snap, p, k=1):
        return None
    d = pressure(snap)
    if d == 0:
        return None
    t = snap["t"]
    tol = tol_pips(snap, p) * snap["pip"]
    h, l, c, o_arr = snap["h"], snap["l"], snap["c"], snap["o"]
    for obj in snap.get("objects", []):
        if obj.get("type") not in ("BOX", "LEVEL_CARRIED",
                                   "PATTERN_LINE", "RANGE_OPEN"):
            continue
        # the object must show a counter-break event within lookback
        evs = [e for e in (obj.get("events") or [])
               if e.get("kind") == "break"
               and int(e.get("side", 0)) == -d
               and 0 <= t - int(e.get("t", -999)) <= p["tff_lookback"]]
        if not evs:
            continue
        # barrier level: the edge that was counter-broken
        if "hi" in obj:
            barrier = float(obj["lo"] if d > 0 else obj["hi"])
        else:
            barrier = float(obj["a"]) * t + float(obj["b"])
        # failed to hold: no FURTHER close beyond the barrier on the
        # counter side after the break bar (its own close is the break)
        tev = int(evs[-1]["t"])
        if d > 0:
            held = np.any(c[tev + 1:t] < barrier - tol)
            reclaim = float(h[t]) >= barrier - tol
        else:
            held = np.any(c[tev + 1:t] > barrier + tol)
            reclaim = float(l[t]) <= barrier + tol
        if held or not reclaim:
            continue
        # strong reversal bar in the dominant direction
        rng = float(h[t]) - float(l[t])
        if rng < p["sig_range_abr"] * snap["abr"] * snap["pip"]:
            continue
        third = rng / 3.0
        strong = (float(c[t]) >= float(h[t]) - third and
                  float(c[t]) > float(o_arr[t])) if d > 0 else \
            (float(c[t]) <= float(l[t]) + third and
             float(c[t]) < float(o_arr[t]))
        if not strong:
            continue
        px = _entry_px(snap, d, p)
        if not room_ok(snap, d, px, p):
            continue
        # invalidation = the counter-break's deepest poke
        lo_w = float(np.min(l[tev:t + 1])) if d > 0 else \
            float(np.max(h[tev:t + 1]))
        buf = p["buf_pips"] * snap["pip"]
        inv = lo_w - buf if d > 0 else lo_w + buf
        return _sig(d, snap, px, inv, "tff")
    return None
