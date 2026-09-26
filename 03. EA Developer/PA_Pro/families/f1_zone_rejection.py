"""f1_zone_rejection.py — SF01 F1 detector (v2): probe into an armed zone that
closes back outside the band; stop-order entry beyond the signal bar.

Spec: rounds/SF01/f1_zone_rejection/SPEC.md (v2, ledger-preregistered).
S ladder per DECISIONS D1: each signal lands on the smallest rung >= its
structural stop distance, so configs partition the signal set.
All reads causal on the sf_ctx cache; no outcomes here.
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "lib")
for _p in (HERE, LIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import sf_ctx          # noqa: E402
import pa_costs        # noqa: E402

FAMILY = "f1_zone_rejection"
ROUND = "SF01"
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]

LADDER = (11.0, 14.0, 18.0, 24.0, 32.0)     # pips, DECISIONS D1

DEFAULTS = {
    "gen": "line1_cluster",
    "S_pips": 18.0,
    "tp_mult": 2.0,
    "touches_min": 1,
    "rej_body": 0,
    "buf_pips": 1.0,
    "v_bars": 3,
    "min_range_atr": 0.5,
    "cooldown": 12,
}

GRID = {
    "S_pips": list(LADDER),
    "gen": ["line1_cluster", "sd_base"],
    "rej_body": [0, 1],
}


def spec_dict(params=None):
    """Canonical, JSON-able spec for hashing / ledger prereg."""
    p = dict(DEFAULTS)
    p.update(params or {})
    return {
        "family": FAMILY,
        "version": "v2",
        "round": ROUND,
        "tf": "M5",
        "symbols": SYMBOLS,
        "ladder": list(LADDER),
        "grid": {k: list(v) for k, v in GRID.items()},
        "engine": {
            "order_type": "stop", "v_bars": p["v_bars"],
            "invalidation": True, "session_cancel": True,
            "flats": True, "legacy_flats": False,
            "daily_flat_hour": 22, "friday_flat_hour": 20,
            "weekend_veto": True,
            "S_pips": p["S_pips"], "tp_mult": p["tp_mult"],
        },
        "params": p,
        "rules": {
            "zone": "armed==1, broken==0, approach_side!=0, touches>=touches_min",
            "probe": "ceiling: h>=lo & c<lo & prev_c<=hi; floor: l<=hi & c>hi & prev_c>=lo",
            "entry": "stop order beyond signal bar extreme by buf_pips",
            "inv": "probe extreme +/- buf_pips",
            "stop_gate": "smallest ladder rung >= s_struct; s_struct >= 10*c_rt",
            "target": "fixed tp_mult*S (fixed-R, charter-legal)",
            "dedupe": "same zid at most once per cooldown bars; one signal/bar",
        },
    }


def detect(D, c_rt_pips, params=None):
    """Return entries [{sig, side, inv, atr, order_px, tag}] for one symbol.

    ``D`` = sf_ctx cache dict for (symbol, params['gen']).  Only signals whose
    structural stop distance lands on rung ``params['S_pips']`` are emitted.
    """
    p = dict(DEFAULTS)
    p.update(params or {})
    t_arr = D["t"]
    n = len(t_arr)
    o, h, l, c = D["o"], D["h"], D["l"], D["c"]
    atr_m5 = D["s_atr_m5"]
    pip = float(D["pip"])
    first_live = int(D["first_live_idx"])
    buf = p["buf_pips"] * pip
    c_guard = 10.0 * c_rt_pips          # pips
    rung = float(p["S_pips"])
    eps = 1e-6

    last_sig_zid = {}
    entries = []
    warm = np.asarray(D["warmup"], dtype=bool)

    for t in range(first_live, n - 1):
        if warm[t]:
            continue
        A5 = atr_m5[t]
        if not (A5 == A5 and A5 > 0):
            continue
        rng_p = (h[t] - l[t]) / pip
        if rng_p < p["min_range_atr"] * (A5 / pip):
            continue
        zones = sf_ctx.zones_at(D, t)
        if not zones:
            continue
        sig_done = False
        for z in zones:
            if sig_done:
                break
            if not (z["armed"] == 1.0 and z["broken"] == 0.0
                    and z["approach_side"] != 0.0
                    and z["touches"] >= p["touches_min"]):
                continue
            zid = int(z["zid"])
            if t - last_sig_zid.get(zid, -10 ** 9) < p["cooldown"]:
                continue
            ap = int(z["approach_side"])
            zlo, zhi = z["lo"], z["hi"]
            if ap == -1:                    # ceiling -> short
                if not (h[t] >= zlo and c[t] < zlo and c[t - 1] <= zhi):
                    continue
                if p["rej_body"] and not (c[t] < o[t]):
                    continue
                side = -1
                order_px = l[t] - buf
                inv = h[t] + buf
            else:                           # floor -> long
                if not (l[t] <= zhi and c[t] > zhi and c[t - 1] >= zlo):
                    continue
                if p["rej_body"] and not (c[t] > o[t]):
                    continue
                side = 1
                order_px = h[t] + buf
                inv = l[t] - buf
            s_struct_p = abs(inv - order_px) / pip
            if s_struct_p < c_guard - eps:
                continue
            assigned = None
            for S in LADDER:
                if s_struct_p <= S + eps:
                    assigned = S
                    break
            if assigned is None or assigned != rung:
                continue
            entries.append({
                "sig": int(t), "side": side,
                "order_px": float(order_px), "inv": float(inv),
                "atr": float(A5), "tag": len(entries), "zid": zid,
            })
            last_sig_zid[zid] = t
            sig_done = True
    return entries


_CACHE = {}


def entries_fn(symbol, bars, spec):
    """pa_eval provider callback: entries for ``symbol`` under ``spec``."""
    params = dict(DEFAULTS)
    params.update((spec or {}).get("params") or {})
    gen = params["gen"]
    key = (symbol, gen)
    if key not in _CACHE:
        _CACHE[key] = sf_ctx.load_cache(symbol, gen)
    D = _CACHE[key]
    bt = np.asarray(bars["t"], dtype=np.int64)
    if len(bt) != len(D["t"]) or not np.array_equal(bt, D["t"]):
        raise ValueError(
            f"cache/provider bar misalignment for {symbol}/{gen}: "
            f"{len(bt)} vs {len(D['t'])}")
    c_rt = pa_costs.C_RT_P90.get(symbol)
    if c_rt is None:
        raise KeyError(f"no c_rt for {symbol}")
    return detect(D, c_rt, params)


def make_spec(params=None, **extra):
    """Full pa_eval spec dict for one config (engine keys at top level for
    ``pa_fill.resolve_spec``)."""
    s = spec_dict(params)
    s.update(s["engine"])           # flatten: S_pips, tp_mult, order_type, ...
    s["entries_fn"] = entries_fn
    for k, v in extra.items():
        s[k] = v
    return s
