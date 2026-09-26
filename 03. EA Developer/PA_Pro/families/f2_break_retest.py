"""f2_break_retest.py — SF01 F2 detector (v2): first pullback into a broken
(or role-flipped) zone rejected in the break direction — continuation.

Spec: rounds/SF01/f2_break_retest/SPEC.md (v2, ledger-preregistered).
Episode anchor = the break bar (broken_idx); it persists through the
engine's break -> reclaim | flip lifecycle.  side = -broken_side for both
phases (broken ceiling that broke up -> LONG; flipped floor keeps the same
broken_side).  S ladder per DECISIONS D1: each signal lands on the smallest
rung >= its structural stop distance, so configs partition the signal set.
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
import pa_clock        # noqa: E402
import pa_random       # noqa: E402

FAMILY = "f2_break_retest"
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
    "retest_win": 48,
    "cooldown": 12,
    "session": 1,                            # D3: eu|us only
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
            "episode": ("broken==1 (broken_idx anchor) OR role_flip==1 "
                        "(anchor carries over); broken_side!=0"),
            "zone": ("(broken OR (role_flip AND armed)), touches>=touches_min, "
                     "approach_side == -broken_side"),
            "retest": ("first last_touch > anchor; t - ft_touch <= retest_win; "
                       "one signal per anchor episode"),
            "reject": ("long: c>hi & prev_c<=hi; short: c<lo & prev_c>=lo"),
            "session": "signal bar closes in eu|us session (D3)",
            "entry": "stop order beyond signal bar extreme by buf_pips",
            "inv": "pullback extreme over [ft_touch, t] +/- buf_pips",
            "stop_gate": "smallest ladder rung >= s_struct; s_struct >= 10*c_rt",
            "target": "fixed tp_mult*S (fixed-R, charter-legal)",
            "dedupe": "one signal per zid per episode; cooldown 12; one/bar",
        },
    }


def detect(D, c_rt_pips, params=None):
    """Return entries [{sig, side, inv, atr, order_px, tag}] for one symbol."""
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
    win = int(p["retest_win"])
    eps = 1e-6

    if p["session"]:
        utc = pa_clock.server_to_utc_epoch(np.asarray(t_arr, dtype=np.int64))
        utc_min = (utc % 86400) // 60
        in_sess = np.array(
            [pa_random.session_of(m) is not None for m in utc_min],
            dtype=bool)
    else:
        in_sess = np.ones(n, dtype=bool)

    anchor = {}       # zid -> episode anchor bar (broken_idx or flip obs.)
    ft_touch = {}     # zid -> first post-anchor touch bar
    fired = {}        # zid -> True once the episode produced a signal
    last_sig_zid = {}
    entries = []
    warm = np.asarray(D["warmup"], dtype=bool)

    for t in range(first_live, n - 1):
        if warm[t]:
            continue
        zones = sf_ctx.zones_at(D, t)
        # --- latch per-zid episode state (causal, over live zones) -------
        for z in zones:
            zid = int(z["zid"])
            brk = int(z["broken_idx"]) if z["broken"] == 1.0 else -1
            flip = z["role_flip"] == 1.0
            if brk >= 0:
                if anchor.get(zid) != brk:
                    anchor[zid] = brk            # new break episode
                    ft_touch.pop(zid, None)
                    fired.pop(zid, None)
            elif flip:
                anchor.setdefault(zid, t)        # carries the break anchor
            else:
                anchor.pop(zid, None)            # reclaimed / retired
                ft_touch.pop(zid, None)
                fired.pop(zid, None)
                continue
            lt = int(z["last_touch"])
            if lt > anchor[zid] and zid not in ft_touch:
                ft_touch[zid] = lt
        # --- signal scan -------------------------------------------------
        A5 = atr_m5[t]
        if not (A5 == A5 and A5 > 0):
            continue
        if not in_sess[t]:
            continue
        rng_p = (h[t] - l[t]) / pip
        if rng_p < p["min_range_atr"] * (A5 / pip):
            continue
        sig_done = False
        for z in zones:
            if sig_done:
                break
            zid = int(z["zid"])
            broken = z["broken"] == 1.0
            flip = z["role_flip"] == 1.0
            if not (broken or (flip and z["armed"] == 1.0)):
                continue
            bs = int(z["broken_side"])
            if bs == 0 or z["touches"] < p["touches_min"]:
                continue
            side = -bs
            if int(z["approach_side"]) != side:
                continue
            if fired.get(zid):
                continue
            ft = ft_touch.get(zid)
            if ft is None or t - ft > win:
                continue
            if t - last_sig_zid.get(zid, -10 ** 9) < p["cooldown"]:
                continue
            zlo, zhi = z["lo"], z["hi"]
            if side == 1:                    # broke up -> long
                if not (c[t] > zhi and c[t - 1] <= zhi):
                    continue
                if p["rej_body"] and not (c[t] > o[t]):
                    continue
                order_px = h[t] + buf
                inv = float(np.min(l[ft:t + 1])) - buf
            else:                            # broke down -> short
                if not (c[t] < zlo and c[t - 1] >= zlo):
                    continue
                if p["rej_body"] and not (c[t] < o[t]):
                    continue
                order_px = l[t] - buf
                inv = float(np.max(h[ft:t + 1])) + buf
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
                "sig": int(t), "side": int(side),
                "order_px": float(order_px), "inv": float(inv),
                "atr": float(A5), "tag": len(entries), "zid": zid,
            })
            fired[zid] = True
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
