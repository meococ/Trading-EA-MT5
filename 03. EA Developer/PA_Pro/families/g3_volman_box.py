"""g3_volman_box.py — SF02 G3 detector (v2): Volman build-up break.

Spec: rounds/SF02/g3_volman_box/SPEC.md (v2, ledger-preregistered).

v2 (pre-outcome, census-driven, DECISIONS D2): v1 required the break on
the compression bar itself -> ~0.05 signals/week (the joint event
"compressed AND breaking through the zone's far edge in one bar" is near
nonexistent).  Volman's build-up is an EPISODE: compression presses
against the level and the break may come several bars later.  v2 model:

- a compression episode = contiguous bars (<= CMAX=24) where the 12-bar
  window ending at that bar passes pct_max + body gates AND the box is
  within prox_atr*ATR_M5 of an armed salient zone edge;
- the episode's box = the full cluster extent [lo, hi];
- the trigger = a close beyond the cluster edge + buf within E=6 bars of
  the last compression bar, aligned with s_tr_h4 at trigger time;
- inv = far side of the cluster; s_struct = cluster height + 2p;
- S ladder assignment + 10*c_rt guard as usual.
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
from sf_autopsy import salience   # noqa: E402

FAMILY = "g3_volman_box"
ROUND = "SF02"
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]

LADDER = (11.0, 14.0, 18.0, 24.0, 32.0)

DEFAULTS = {
    "S_pips": 18.0,
    "gen": "line1_cluster",
    "tp_mult": 2.0,
    "buf_pips": 1.0,
    "v_bars": 3,
    "B": 12,                 # percentile window = 12-bar range
    "W_pct": 576,            # rolling window for range percentile (~2d)
    "pct_max": 20.0,         # 12-bar range <= this percentile of W_pct
    "body_max_atr": 0.5,     # mean |c-o| over the window <= 0.5*ATR_M5
    "CMAX": 24,              # max contiguous compressed cluster length
    "E": 6,                  # break must come within E bars of episode end
    "prox_atr": 1.0,         # box edge within this of a zone edge
    "sal_min": 2.0,
    "min_range_atr": 0.3,    # trigger bar range floor
    "cooldown": 12,
    "session": 1,
    "tr_src": "h4",
}

GRID = {                   # 5 x 2 x 2 = 20 cells <= 24 budget
    "S_pips": list(LADDER),
    "gen": ["line1_cluster", "sd_base"],
    "pct_max": [10.0, 20.0],
}


def spec_dict(params=None):
    p = dict(DEFAULTS)
    p.update(params or {})
    return {
        "family": FAMILY, "version": "v2", "round": ROUND, "tf": "M5",
        "symbols": SYMBOLS, "ladder": list(LADDER),
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
            "compression": ("12-bar range ending at bar j <= pct_max-th "
                            "percentile of rolling 12-bar ranges over "
                            "W_pct bars AND mean|c-o| <= 0.5*ATR_M5"),
            "episode": ("contiguous compressed bars (<= CMAX) form the "
                        "build-up cluster; box = cluster extent"),
            "buildup": ("at a compression bar, an armed zone with "
                        "salience >= sal_min whose either edge is within "
                        "prox_atr*ATR_M5 of the cluster edge, "
                        "approach_side == break side"),
            "trigger": ("c[t] beyond cluster edge + buf within E bars of "
                        "the last compression bar; direction == "
                        "s_tr_h4[t]; trigger bar range >= "
                        "min_range_atr*ATR_M5"),
            "entry": "STOP order at cluster edge + buf",
            "inv": "far side of cluster +/- buf",
            "stop_gate": "smallest ladder rung >= s_struct >= 10*c_rt",
            "session": "eu|us (D3)",
            "dedupe": "one signal per (zid) per cooldown; one/bar",
        },
    }


def _compressed(D, t, B, W, body_max, pct_max, A5):
    """Is the 12-bar window ending just before bar ``t`` compressed?
    Returns (pct, box_hi, box_lo) or None."""
    if t - W - B < 0:
        return None
    h, l, c, o = D["h"], D["l"], D["c"], D["o"]
    box_hi = float(np.max(h[t - B:t]))
    box_lo = float(np.min(l[t - B:t]))
    rng = box_hi - box_lo
    lo_ = max(0, t - W - B + 1)
    seg_h = h[lo_:t - B]
    seg_l = l[lo_:t - B]
    if len(seg_h) < B:
        return None
    sh = np.lib.stride_tricks.sliding_window_view(seg_h, B)
    sl = np.lib.stride_tricks.sliding_window_view(seg_l, B)
    hist = sh.max(1) - sl.min(1)
    pct = 100.0 * float((hist <= rng).mean())
    if pct > pct_max:
        return None
    body = float(np.mean(np.abs(c[t - B:t] - o[t - B:t])))
    if body > body_max * A5:
        return None
    return pct, box_hi, box_lo


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
    B = int(p["B"]); W = int(p["W_pct"])
    CMAX = int(p["CMAX"]); E = int(p["E"])
    eps = 1e-6

    if p["session"]:
        utc = pa_clock.server_to_utc_epoch(np.asarray(t_arr, dtype=np.int64))
        utc_min = (utc % 86400) // 60
        in_sess = np.array(
            [pa_random.session_of(m) is not None for m in utc_min],
            dtype=bool)
    else:
        in_sess = np.ones(n, dtype=bool)

    warm = np.asarray(D["warmup"], dtype=bool)
    entries = []
    last_sig = -10 ** 9
    last_sig_zid = {}
    # episode state per side: dict or None
    # keys: hi, lo (cluster extent), expiry, zid
    ep = {1: None, -1: None}

    for t in range(first_live, n - 1):
        if warm[t]:
            continue
        A5, A1 = atr_m5[t], atr_h1[t]
        ok_atr = (A5 == A5 and A5 > 0 and A1 == A1 and A1 > 0)
        # --- refresh episode state on compression bars ----------------
        comp = _compressed(D, t, B, W, p["body_max_atr"], p["pct_max"], A5) \
            if ok_atr else None
        if comp is not None:
            _, bh12, bl12 = comp
            # cluster extent: walk back while contiguous compression
            j = t
            jstart = t
            while j - 1 > first_live and t - (j - 1) < CMAX:
                cj = _compressed(D, j - 1, B, W,
                                 p["body_max_atr"], p["pct_max"],
                                 atr_m5[j - 1])
                if cj is None:
                    break
                jstart = j - 1
                j -= 1
            bh = float(np.max(h[jstart - B + 1:t])) \
                if jstart - B + 1 >= 0 else bh12
            bl = float(np.min(l[jstart - B + 1:t])) \
                if jstart - B + 1 >= 0 else bl12
            # qualifying salient zone for each side at this bar
            for z in sf_ctx.zones_at(D, t):
                if not z.get("armed"):
                    continue
                if salience(z, D, t, A1) < p["sal_min"]:
                    continue
                zid = int(z["zid"])
                if z["approach_side"] == -1 and (
                        abs(z["lo"] - bh) <= p["prox_atr"] * A5 or
                        abs(z["hi"] - bh) <= p["prox_atr"] * A5):
                    ep[1] = {"hi": bh, "lo": bl, "exp": t + E,
                             "zid": zid}
                if z["approach_side"] == 1 and (
                        abs(z["hi"] - bl) <= p["prox_atr"] * A5 or
                        abs(z["lo"] - bl) <= p["prox_atr"] * A5):
                    ep[-1] = {"hi": bh, "lo": bl, "exp": t + E,
                              "zid": zid}
        if not in_sess[t]:
            continue
        if not ok_atr:
            continue
        tr = int(tr_arr[t]) if t < len(tr_arr) else 0
        if tr == 0 or t - last_sig < p["cooldown"]:
            continue
        if (h[t] - l[t]) / pip < p["min_range_atr"] * (A5 / pip):
            continue
        s = ep.get(tr)
        if s is None or t > s["exp"]:
            continue
        bh, bl = s["hi"], s["lo"]
        if tr == 1 and c[t] <= bh + buf:
            continue
        if tr == -1 and c[t] >= bl - buf:
            continue
        order_px = (bh + buf) if tr == 1 else (bl - buf)
        inv = (bl - buf) if tr == 1 else (bh + buf)
        s_struct_p = abs(order_px - inv) / pip
        if s_struct_p < c_guard - eps or s_struct_p > LADDER[-1] + eps:
            ep[tr] = None                      # dead episode
            continue
        assigned = None
        for S in LADDER:
            if s_struct_p <= S + eps:
                assigned = S
                break
        if assigned != rung:
            continue
        zid = s["zid"]
        if t - last_sig_zid.get(zid, -10 ** 9) < p["cooldown"]:
            continue
        entries.append({
            "sig": int(t), "side": int(tr), "order_px": float(order_px),
            "inv": float(inv), "atr": float(A5),
            "tag": len(entries), "zid": zid,
        })
        last_sig = t
        last_sig_zid[zid] = t
        ep[tr] = None                          # episode consumed
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


def make_spec(params=None, **extra):
    s = spec_dict(params)
    s.update(s["engine"])
    s["entries_fn"] = entries_fn
    for k, v in extra.items():
        s[k] = v
    return s
