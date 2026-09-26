"""f6_volman_box.py — SF01 F6 detector (v1): Volman box break with
buildup.  A compressed M5 box pressed against an armed zone edge;
signal bar closes through box AND zone edge; STOP order 1 pip beyond
the box edge (the correct Volman entry); inv at the far side of the
box.

Spec: rounds/SF01/f6_volman_box/SPEC.md (v1, ledger-preregistered).
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

import pa_costs        # noqa: E402
import pa_clock        # noqa: E402
import pa_random       # noqa: E402
import sf_ctx          # noqa: E402

FAMILY = "f6_volman_box"
ROUND = "SF01"
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]

LADDER = (11.0, 14.0, 18.0, 24.0, 32.0)     # pips, DECISIONS D1

DEFAULTS = {
    "S_pips": 18.0,
    "gen": "line1_cluster",
    "tp_mult": 2.0,
    "buf_pips": 1.0,
    "v_bars": 3,
    "B": 12,
    "box_atr": 4.0,
    "prox_atr": 0.5,
    "min_range_atr": 0.5,
    "cooldown": 12,
    "session": 1,                            # D3: eu|us only
}

GRID = {
    "S_pips": list(LADDER),
    "gen": ["line1_cluster", "sd_base"],
    "box_atr": [2.5, 4.0],
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
            "box": ("last B=12 bars [t-B..t-1]: box range "
                    "<= box_atr * atr_m5[t]"),
            "buildup": ("armed zone at t; long: ceiling (approach -1) "
                        "with |hi - box_hi| <= prox_atr*A5; short: floor "
                        "(approach +1) with |lo - box_lo| <= prox_atr*A5"),
            "trigger": ("c[t] beyond box edge + buf AND beyond zone "
                        "edge; bar range >= min_range_atr*A5"),
            "session": "signal bar closes in eu|us session (D3)",
            "entry": "stop order 1 pip beyond box edge (Volman entry)",
            "inv": "far side of box +/- 1 pip",
            "stop_gate": "smallest ladder rung >= s_struct; s_struct >= 10*c_rt",
            "target": "fixed tp_mult*S (fixed-R, charter-legal)",
            "dedupe": "one signal per (zid, box) episode; cooldown 12; one/bar",
        },
    }


def detect(D, c_rt_pips, params=None):
    """Return entries [{sig, side, inv, atr, order_px, tag, zid}]."""
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
    B = int(p["B"])
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
    last_sig_zid = {}                    # zid -> last sig bar
    entries = []
    warm = np.asarray(D["warmup"], dtype=bool)

    for t in range(first_live, n - 1):
        if warm[t] or not in_sess[t] or t - B < 0:
            continue
        A5 = atr_m5[t]
        if not (A5 == A5 and A5 > 0):
            continue
        if t - last_sig < p["cooldown"]:
            continue
        if (h[t] - l[t]) / pip < p["min_range_atr"] * (A5 / pip):
            continue
        box_hi = float(np.max(h[t - B:t]))
        box_lo = float(np.min(l[t - B:t]))
        if box_hi - box_lo > p["box_atr"] * A5 + eps * pip:
            continue
        tr = 0
        if c[t] > box_hi + buf:
            tr = 1
        elif c[t] < box_lo - buf:
            tr = -1
        if tr == 0:
            continue
        for z in sf_ctx.zones_at(D, t):
            if not z.get("armed"):
                continue
            zid = z["zid"]
            if t - last_sig_zid.get(zid, -10 ** 9) < p["cooldown"]:
                continue
            if tr == 1:
                if z["approach_side"] != -1:
                    continue
                if abs(z["hi"] - box_hi) > p["prox_atr"] * A5 + eps * pip:
                    continue
                if c[t] <= z["hi"]:
                    continue
                order_px = box_hi + buf
                inv = box_lo - buf
                s_struct_p = (order_px - inv) / pip
            else:
                if z["approach_side"] != 1:
                    continue
                if abs(z["lo"] - box_lo) > p["prox_atr"] * A5 + eps * pip:
                    continue
                if c[t] >= z["lo"]:
                    continue
                order_px = box_lo - buf
                inv = box_hi + buf
                s_struct_p = (inv - order_px) / pip
            assigned = None
            if s_struct_p >= c_guard - eps:
                for S in LADDER:
                    if s_struct_p <= S + eps:
                        assigned = S
                        break
            if assigned != rung:
                continue
            entries.append({
                "sig": int(t), "side": int(tr),
                "order_px": float(order_px),
                "inv": float(inv), "atr": float(A5),
                "tag": len(entries), "zid": int(zid),
            })
            last_sig = t
            last_sig_zid[zid] = t
            break                            # one signal per bar
    return entries


def entries_fn(symbol, bars, spec):
    """pa_eval provider callback: entries for ``symbol`` under ``spec``."""
    params = dict(DEFAULTS)
    params.update((spec or {}).get("params") or {})
    key = (symbol, params["gen"])
    if key not in _CACHE:
        _CACHE[key] = sf_ctx.load_cache(symbol, params["gen"])
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


def make_spec(params=None, **extra):
    """Full pa_eval spec dict for one config (engine keys at top level for
    ``pa_fill.resolve_spec``)."""
    s = spec_dict(params)
    s.update(s["engine"])           # flatten: S_pips, tp_mult, order_type, ...
    s["entries_fn"] = entries_fn
    for k, v in extra.items():
        s[k] = v
    return s
