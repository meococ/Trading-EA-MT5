"""f5_second_entry.py — SF01 F5 detector (v1): Brooks second entry —
two-legged pullback in trend.  Fires on the CONFIRMATION bar of the
second leg's pivot (L2 in uptrend / H2 in downtrend); stop order beyond
the pivot bar; inv at the pivot extreme.

Spec: rounds/SF01/f5_second_entry/SPEC.md (v1, ledger-preregistered).
S ladder per DECISIONS D1.  All reads causal on the sf_ctx cache; no
outcomes here.
"""

import bisect
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

FAMILY = "f5_second_entry"
ROUND = "SF01"
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]

LADDER = (11.0, 14.0, 18.0, 24.0, 32.0)     # pips, DECISIONS D1

DEFAULTS = {
    "S_pips": 18.0,
    "tp_mult": 2.0,
    "buf_pips": 1.0,
    "v_bars": 3,
    "min_range_atr": 0.5,
    "leg_span": 48,
    "tol_atr": 1.0,
    "cooldown": 12,
    "session": 1,                            # D3: eu|us only
    "tr_src": "h1",                          # h1 | h4
}

GRID = {
    "S_pips": list(LADDER),
    "tr_src": ["h1", "h4"],
    "tol_atr": [0.5, 1.0],
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
            "trend": "tr = s_tr_<src>[t] in {-1,+1}",
            "legs": ("fire at conf bar of 2nd leg pivot (L2/H2); opposite "
                     "pivot strictly between legs; i2-i1<=leg_span; "
                     "|px2-px1|<=tol_atr*atr_m5"),
            "session": "signal bar closes in eu|us session (D3)",
            "entry": "stop order beyond pivot bar extreme by buf_pips",
            "inv": "deepest point of the two-legged pullback +/- buf_pips (v2)",
            "stop_gate": "smallest ladder rung >= s_struct; s_struct >= 10*c_rt",
            "target": "fixed tp_mult*S (fixed-R, charter-legal)",
            "dedupe": "one signal per pivot; cooldown 12; one/bar",
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
    leg_span = int(p["leg_span"])
    tol_atr = float(p["tol_atr"])
    eps = 1e-6

    if p["session"]:
        utc = pa_clock.server_to_utc_epoch(np.asarray(t_arr, dtype=np.int64))
        utc_min = (utc % 86400) // 60
        in_sess = np.array(
            [pa_random.session_of(m) is not None for m in utc_min],
            dtype=bool)
    else:
        in_sess = np.ones(n, dtype=bool)

    # pivots: (bar_idx, price, side, conf_bar) — bucket by conf bar
    pi, pp, ps, pc = (D["piv_idx"], D["piv_px"], D["piv_side"],
                      D["piv_conf"])
    by_conf = {}
    for j in range(len(pi)):
        by_conf.setdefault(int(pc[j]), []).append(j)

    conf_lo = []          # confirmed lows (idx, px), append order
    conf_hi = []          # confirmed highs (idx, px)
    hi_bars = []          # confirmed high bar idx (sorted for bisect)
    lo_bars = []
    last_sig = -10 ** 9
    entries = []
    warm = np.asarray(D["warmup"], dtype=bool)

    for t in range(first_live, n - 1):
        if warm[t]:
            continue
        tr = int(tr_arr[t]) if t < len(tr_arr) else 0
        sig_done = False
        for j in by_conf.get(t, ()):
            if sig_done:
                break
            i2 = int(pi[j])
            px2 = float(pp[j])
            side_piv = int(ps[j])
            A5 = atr_m5[t]
            ok_bar = (A5 == A5 and A5 > 0 and in_sess[t]
                      and tr != 0
                      and t - last_sig >= p["cooldown"]
                      and (h[t] - l[t]) / pip
                      >= p["min_range_atr"] * (A5 / pip))
            if ok_bar and tr == 1 and side_piv == -1 and conf_lo:
                # L2 just confirmed; L1 = latest earlier confirmed low
                i1, px1 = conf_lo[-1]
                if not (i1 < i2 and i2 - i1 <= leg_span):
                    pass
                elif abs(px2 - px1) > tol_atr * A5:
                    pass
                elif not any(i1 < b < i2 for b in hi_bars):
                    pass                 # need a bounce high between legs
                else:
                    order_px = h[i2] + buf
                    inv = min(l[i1], l[i2]) - buf   # v2: pullback deep (D10)
                    s_struct_p = (order_px - inv) / pip
                    assigned = None
                    if s_struct_p >= c_guard - eps:
                        for S in LADDER:
                            if s_struct_p <= S + eps:
                                assigned = S
                                break
                    if assigned == rung:
                        entries.append({
                            "sig": int(t), "side": 1,
                            "order_px": float(order_px),
                            "inv": float(inv), "atr": float(A5),
                            "tag": len(entries), "zid": i2,
                        })
                        last_sig = t
                        sig_done = True
            if ok_bar and tr == -1 and side_piv == 1 and conf_hi:
                i1, px1 = conf_hi[-1]
                if not (i1 < i2 and i2 - i1 <= leg_span):
                    pass
                elif abs(px2 - px1) > tol_atr * A5:
                    pass
                elif not any(i1 < b < i2 for b in lo_bars):
                    pass                 # need a bounce low between legs
                else:
                    order_px = l[i2] - buf
                    inv = max(h[i1], h[i2]) + buf   # v2: pullback deep (D10)
                    s_struct_p = (inv - order_px) / pip
                    assigned = None
                    if s_struct_p >= c_guard - eps:
                        for S in LADDER:
                            if s_struct_p <= S + eps:
                                assigned = S
                                break
                    if assigned == rung:
                        entries.append({
                            "sig": int(t), "side": -1,
                            "order_px": float(order_px),
                            "inv": float(inv), "atr": float(A5),
                            "tag": len(entries), "zid": i2,
                        })
                        last_sig = t
                        sig_done = True
            # register the confirmed pivot regardless of signal outcome
            if side_piv == -1:
                conf_lo.append((i2, px2))
                bisect.insort(lo_bars, i2)
            else:
                conf_hi.append((i2, px2))
                bisect.insort(hi_bars, i2)
    return entries


def entries_fn(symbol, bars, spec):
    """pa_eval provider callback: entries for ``symbol`` under ``spec``."""
    params = dict(DEFAULTS)
    params.update((spec or {}).get("params") or {})
    key = symbol
    if key not in _CACHE:
        _CACHE[key] = _load(symbol)
    D = _CACHE[key]
    bt = np.asarray(bars["t"], dtype=np.int64)
    if len(bt) != len(D["t"]) or not np.array_equal(bt, D["t"]):
        raise ValueError(
            f"cache/provider bar misalignment for {symbol}: "
            f"{len(bt)} vs {len(D['t'])}")
    c_rt = pa_costs.C_RT_P90.get(symbol)
    if c_rt is None:
        raise KeyError(f"no c_rt for {symbol}")
    return detect(D, c_rt, params)


_CACHE = {}


def _load(symbol):
    """F5 needs no zones — reuse any cache for the shared context arrays."""
    import sf_ctx
    return sf_ctx.load_cache(symbol, "line1_cluster")


def make_spec(params=None, **extra):
    """Full pa_eval spec dict for one config (engine keys at top level for
    ``pa_fill.resolve_spec``)."""
    s = spec_dict(params)
    s.update(s["engine"])           # flatten: S_pips, tp_mult, order_type, ...
    s["entries_fn"] = entries_fn
    for k, v in extra.items():
        s[k] = v
    return s
