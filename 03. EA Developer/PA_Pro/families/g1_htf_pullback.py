"""g1_htf_pullback.py — SF02 G1 detector (v1): HTF-structure pullback
entered AT a salient zone edge — no chase.

Spec: rounds/SF02/g1_htf_pullback/SPEC.md (v1, ledger-preregistered).
The SF01 autopsy showed (i) ~6 armed zones within +-2xATR_H1 make "at a
zone" nearly always true, and (ii) the F4-style entry chases ~12 pips
beyond the zone.  G1 fixes both: only the SINGLE most salient armed zone
per side may trigger, and the entry is a LIMIT order at the zone edge
(fill only if price returns to the level), never beyond it.

Salience is the AUTOPSY_PLAN formula (ledger T000229) — causal fields of
the zone record plus H1-pivot and round-number confluence.
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "lib")
for _p in (HERE, LIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pa_costs        # noqa: E402
import pa_clock        # noqa: E402
import pa_random       # noqa: E402
import sf_ctx          # noqa: E402
import sf_provider     # noqa: E402
from sf_autopsy import salience   # noqa: E402  (plan-fixed formula)

FAMILY = "g1_htf_pullback"
ROUND = "SF02"
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]

LADDER = (18.0, 24.0, 32.0, 40.0, 55.0)     # wider rungs (rung 2)

DEFAULTS = {
    "S_pips": 32.0,
    "gen": "line1_cluster",
    "tp_mult": 2.0,
    "buf_pips": 1.0,
    "v_bars": 6,
    "min_range_atr": 0.3,
    "touch_atr": 0.35,       # signal bar must reach within this of edge
    "sal_min": 2.0,          # minimum salience for the triggering zone
    "room_min_R": 2.0,       # room to opposing salient zone >= R*S
    "cooldown": 12,
    "session": 1,
    "tr_src": "h4",          # h1 | h4
    "pull_max": 96,          # pullback may span at most ~2 days of M5
}

GRID = {                   # 5 x 2 x 2 = 20 cells <= 24 budget
    "S_pips": list(LADDER),
    "gen": ["line1_cluster", "sd_base"],
    "tr_src": ["h1", "h4"],
}


def spec_dict(params=None):
    p = dict(DEFAULTS)
    p.update(params or {})
    return {
        "family": FAMILY, "version": "v2", "round": ROUND, "tf": "M5",
        "symbols": SYMBOLS, "ladder": list(LADDER),
        "grid": {k: list(v) for k, v in GRID.items()},
        "engine": {
            "order_type": "limit", "v_bars": p["v_bars"],
            "invalidation": True, "session_cancel": True,
            "flats": True, "legacy_flats": False,
            "daily_flat_hour": 22, "friday_flat_hour": 20,
            "weekend_veto": True,
            "S_pips": p["S_pips"], "tp_mult": p["tp_mult"],
        },
        "params": p,
        "rules": {
            "trend": "tr = s_tr_<src>[t] in {-1,+1}",
            "zone": ("single most salient armed zone per side; "
                     "salience = plan formula (T000229); "
                     "salience >= sal_min"),
            "touch": ("long: floor zone (approach +1), proximal edge z.hi, "
                      "l[t] <= z.hi + touch_atr*A5; short: ceiling, "
                      "proximal edge z.lo, h[t] >= z.lo - touch_atr*A5"),
            "entry": ("LIMIT at the proximal edge: long order_px = "
                      "z.hi - buf, short = z.lo + buf — fills only if "
                      "price returns to the edge"),
            "inv": ("deeper of (zone far edge, pullback extreme) +/- buf; "
                    "pullback leg = bars since the last bar fully on the "
                    "approach side (long: l > edge + touch_atr*A5; short: "
                    "h < edge - tol), capped at pull_max bars"),
            "room": ("nearest opposing armed-salient zone edge >= "
                     "room_min_R * S from order_px, else skip"),
            "stop_gate": "smallest ladder rung >= s_struct >= 10*c_rt",
            "target": "fixed tp_mult*S",
            "dedupe": "one signal per zid per cooldown; one/bar",
        },
    }


def _opposing_room(D, t, side, px, sal_min, atr_h1):
    """Distance to nearest opposing armed+salient zone edge (price units)."""
    best = np.inf
    for z in sf_ctx.zones_at(D, t):
        if not z.get("armed"):
            continue
        if side > 0 and z["approach_side"] != -1:
            continue           # opposing = ceiling above price
        if side < 0 and z["approach_side"] != 1:
            continue
        if salience(z, D, t, atr_h1) < sal_min:
            continue
        edge = z["lo"] if side > 0 else z["hi"]
        dist = (edge - px) * side
        if dist > 0:
            best = min(best, dist)
    return best


def detect(D, c_rt_pips, params=None):
    p = dict(DEFAULTS)
    p.update(params or {})
    t_arr = D["t"]
    n = len(t_arr)
    h, l, c = D["h"], D["l"], D["c"]
    atr_m5 = D["s_atr_m5"]
    atr_h1 = D["s_atr_h1"]
    tr_arr = D["s_tr_h1"] if p["tr_src"] == "h1" else D["s_tr_h4"]
    pip = float(D["pip"])
    first_live = int(D["first_live_idx"])
    buf = p["buf_pips"] * pip
    c_guard = 10.0 * c_rt_pips
    rung = float(p["S_pips"])
    eps = 1e-6

    if p["session"]:
        utc = pa_clock.server_to_utc_epoch(np.asarray(t_arr, dtype=np.int64))
        utc_min = (utc % 86400) // 60
        in_sess = np.array(
            [pa_random.session_of(m) is not None for m in utc_min],
            dtype=bool)
    else:
        in_sess = np.ones(n, dtype=bool)

    last_sig = -10 ** 9
    last_sig_zid = {}
    entries = []
    warm = np.asarray(D["warmup"], dtype=bool)

    for t in range(first_live, n - 1):
        if warm[t] or not in_sess[t]:
            continue
        A5, A1 = atr_m5[t], atr_h1[t]
        if not (A5 == A5 and A5 > 0 and A1 == A1 and A1 > 0):
            continue
        tr = int(tr_arr[t]) if t < len(tr_arr) else 0
        if tr == 0 or t - last_sig < p["cooldown"]:
            continue
        if (h[t] - l[t]) / pip < p["min_range_atr"] * (A5 / pip):
            continue
        # single most salient armed zone on the trend-aligned side
        best_z, best_s = None, -np.inf
        for z in sf_ctx.zones_at(D, t):
            if not z.get("armed"):
                continue
            if tr == 1 and z["approach_side"] != 1:
                continue           # uptrend -> floor zones below price
            if tr == -1 and z["approach_side"] != -1:
                continue           # downtrend -> ceiling above price
            s = salience(z, D, t, A1)
            if s >= p["sal_min"] and s > best_s:
                best_z, best_s = z, s
        if best_z is None:
            continue
        z = best_z
        if tr == 1:
            # floor band [lo,hi] approached from above: proximal edge = hi
            edge = z["hi"]
            if l[t] > edge + p["touch_atr"] * A5:
                continue                          # didn't reach the edge
            if c[t] < z["lo"]:
                continue                          # closed through the zone
            order_px = edge - buf                 # LIMIT buy at edge
            # inv: deeper of zone far edge and pullback extreme (D1 v2).
            # Leg = since the last bar FULLY on the approach side
            # (long: whole bar above edge + tol) — captures the swing low
            # the pullback retraced from, not just the latest dip.
            j0 = max(first_live, t - int(p["pull_max"]))
            for j in range(t, j0 - 1, -1):
                if l[j] > edge + p["touch_atr"] * A5:
                    break
            else:
                j = j0 - 1
            pull_lo = float(np.min(l[j + 1:t + 1]))
            inv = min(z["lo"], pull_lo) - buf
        else:
            edge = z["lo"]
            if h[t] < edge - p["touch_atr"] * A5:
                continue
            if c[t] > z["hi"]:
                continue
            order_px = edge + buf
            j0 = max(first_live, t - int(p["pull_max"]))
            for j in range(t, j0 - 1, -1):
                if h[j] < edge - p["touch_atr"] * A5:
                    break
            else:
                j = j0 - 1
            pull_hi = float(np.max(h[j + 1:t + 1]))
            inv = max(z["hi"], pull_hi) + buf
        s_struct_p = abs(order_px - inv) / pip
        if s_struct_p < c_guard - eps or s_struct_p > LADDER[-1] + eps:
            continue
        # no-chase: the limit must sit at/beyond current price only as
        # far as the touch tolerance already enforces; extra guard:
        if tr == 1 and order_px > c[t] + p["touch_atr"] * A5:
            continue
        if tr == -1 and order_px < c[t] - p["touch_atr"] * A5:
            continue
        room = _opposing_room(D, t, tr, order_px, p["sal_min"], A1)
        if np.isfinite(room) and room < p["room_min_R"] * rung * pip:
            continue
        assigned = None
        for S in LADDER:
            if s_struct_p <= S + eps:
                assigned = S
                break
        if assigned != rung:
            continue
        if t - last_sig_zid.get(int(z["zid"]), -10 ** 9) < p["cooldown"]:
            continue
        entries.append({
            "sig": int(t), "side": int(tr), "order_px": float(order_px),
            "inv": float(inv), "atr": float(A5),
            "tag": len(entries), "zid": int(z["zid"]),
        })
        last_sig = t
        last_sig_zid[int(z["zid"])] = t
    return entries


def entries_fn(symbol, bars, spec):
    params = dict(DEFAULTS)
    params.update((spec or {}).get("params") or {})
    key = (symbol, params["gen"])
    if key not in _CACHE:
        _CACHE[key] = sf_ctx.load_cache(symbol, params["gen"])
    D = _CACHE[key]
    bt = np.asarray(bars["t"], dtype=np.int64)
    if len(bt) != len(D["t"]) or not np.array_equal(bt, D["t"]):
        raise ValueError(f"cache/provider misalignment {symbol}")
    c_rt = pa_costs.C_RT_P90.get(symbol)
    if c_rt is None:
        raise KeyError(f"no c_rt for {symbol}")
    return detect(D, c_rt, params)


_CACHE = {}
_ENT = {}


def _entries_cached(symbol, bars, spec):
    params = dict(DEFAULTS)
    params.update((spec or {}).get("params") or {})
    key = (symbol, json.dumps(params, sort_keys=True, default=str))
    if key not in _ENT:
        _ENT[key] = entries_fn(symbol, bars, spec)
    return _ENT[key]


PAIRED_RANDOM = True   # limit orders: referee randoms need order_px


def paired_random_entries(symbol, bars, spec, K=20, seed=20260921):
    """Geometry-fair matched randoms for the LIMIT family.

    Replicates the referee's construction exactly: match_random on the
    strategy signals (skips out-of-session internally), tag = source
    signal's index among kept (in-session) signals, warmup drop by
    utc_start.  The one addition the referee cannot express: limit orders
    need order_px — randoms get the symmetric null, a limit at the signal
    bar's own extreme -/+ buf (long: l[sig]-buf; short: h[sig]+buf).
    """
    ent = _entries_cached(symbol, bars, spec)
    if not ent:
        return []
    picks = pa_random.match_random(
        [{"bar_idx": e["sig"], "side": e["side"]} for e in ent],
        bars, K=K, seed=seed)
    utc_min = np.asarray(bars["utc_min"], dtype=np.int64)
    kept = [i for i, e in enumerate(ent)
            if pa_random.session_of(utc_min[int(e["sig"])]) is not None]
    live_cut = 0
    try:
        d = sf_provider.provider(symbol, "DESIGN", "M5")
        live_cut = int(d.get("utc_start", 0))
    except Exception:
        live_cut = 0
    utc_all = pa_clock.server_to_utc_epoch(
        np.asarray(bars["t"], dtype=np.int64))
    lo_arr = np.asarray(bars["l"], dtype=np.float64)
    hi_arr = np.asarray(bars["h"], dtype=np.float64)
    buf = DEFAULTS["buf_pips"] * float(bars["pip"])
    out = []
    for i, pk in enumerate(picks):
        src = kept[i // K]
        b = int(pk[0]); sd = int(pk[1])
        if live_cut and int(utc_all[b]) < live_cut:
            continue
        order = (lo_arr[b] - buf) if sd > 0 else (hi_arr[b] + buf)
        out.append({"sig": b, "side": sd, "tag": src,
                    "order_px": float(order)})
    return out


def make_spec(params=None, **extra):
    s = spec_dict(params)
    s.update(s["engine"])
    s["entries_fn"] = entries_fn
    for k, v in extra.items():
        s[k] = v
    return s
