"""f4_trend_pullback.py — SF01 F4 detector (v1): H1/H4 trend-aligned
pullback into an armed zone + momentum resumption bar (close out of the
band on the trend side AND beyond the previous bar's extreme).

Spec: rounds/SF01/f4_trend_pullback/SPEC.md (v1, ledger-preregistered).
S ladder per DECISIONS D1.  All reads causal on the sf_ctx cache; no
outcomes here.
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

FAMILY = "f4_trend_pullback"
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
    "pull_win": 24,
    "cooldown": 12,
    "session": 1,                            # D3: eu|us only
    "tr_src": "h1",                          # h1 | h4
}

GRID = {
    "S_pips": list(LADDER),
    "gen": ["line1_cluster", "sd_base"],
    "tr_src": ["h1", "h4"],
}


def spec_dict(params=None):
    """Canonical, JSON-able spec for hashing / ledger prereg."""
    p = dict(DEFAULTS)
    p.update(params or {})
    return {
        "family": FAMILY,
        "version": "v1",
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
            "trend": "tr = s_tr_<src>[t] in {-1,+1}",
            "zone": ("armed==1, broken==0, approach_side==tr, "
                     "touches>=touches_min, last_touch in [t-pull_win, t]"),
            "resume": ("long: c>hi & c>h[t-1]; short: c<lo & c<l[t-1]; "
                       "optional body gate"),
            "session": "signal bar closes in eu|us session (D3)",
            "entry": "stop order beyond signal bar extreme by buf_pips",
            "inv": "pullback extreme over [last_touch, t] +/- buf_pips",
            "stop_gate": "smallest ladder rung >= s_struct; s_struct >= 10*c_rt",
            "target": "fixed tp_mult*S (fixed-R, charter-legal)",
            "dedupe": "one signal per (zid,last_touch); cooldown 12; one/bar",
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
    tr_arr = D["s_tr_h1"] if p["tr_src"] == "h1" else D["s_tr_h4"]
    pip = float(D["pip"])
    first_live = int(D["first_live_idx"])
    buf = p["buf_pips"] * pip
    c_guard = 10.0 * c_rt_pips          # pips
    rung = float(p["S_pips"])
    win = int(p["pull_win"])
    eps = 1e-6

    if p["session"]:
        utc = pa_clock.server_to_utc_epoch(np.asarray(t_arr, dtype=np.int64))
        utc_min = (utc % 86400) // 60
        in_sess = np.array(
            [pa_random.session_of(m) is not None for m in utc_min],
            dtype=bool)
    else:
        in_sess = np.ones(n, dtype=bool)

    fired_ep = set()     # (zid, last_touch) already signalled
    last_sig_zid = {}
    entries = []
    warm = np.asarray(D["warmup"], dtype=bool)

    for t in range(first_live, n - 1):
        if warm[t]:
            continue
        tr = int(tr_arr[t]) if t < len(tr_arr) else 0
        if tr == 0:
            continue
        A5 = atr_m5[t]
        if not (A5 == A5 and A5 > 0):
            continue
        if not in_sess[t]:
            continue
        rng_p = (h[t] - l[t]) / pip
        if rng_p < p["min_range_atr"] * (A5 / pip):
            continue
        zones = sf_ctx.zones_at(D, t)
        sig_done = False
        for z in zones:
            if sig_done:
                break
            zid = int(z["zid"])
            if not (z["armed"] == 1.0 and z["broken"] == 0.0):
                continue
            if int(z["approach_side"]) != tr:
                continue
            if z["touches"] < p["touches_min"]:
                continue
            lt = int(z["last_touch"])
            if lt < 0 or t - lt > win:
                continue
            if (zid, lt) in fired_ep:
                continue
            if t - last_sig_zid.get(zid, -10 ** 9) < p["cooldown"]:
                continue
            zlo, zhi = z["lo"], z["hi"]
            if tr == 1:                      # uptrend -> long resumption
                if not (c[t] > zhi and c[t] > h[t - 1]):
                    continue
                if p["rej_body"] and not (c[t] > o[t]):
                    continue
                side = 1
                order_px = h[t] + buf
                inv = float(np.min(l[lt:t + 1])) - buf
            else:                            # downtrend -> short resumption
                if not (c[t] < zlo and c[t] < l[t - 1]):
                    continue
                if p["rej_body"] and not (c[t] < o[t]):
                    continue
                side = -1
                order_px = l[t] - buf
                inv = float(np.max(h[lt:t + 1])) + buf
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
            fired_ep.add((zid, lt))
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
