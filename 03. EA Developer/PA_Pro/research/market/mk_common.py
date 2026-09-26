"""mk_common — shared machinery for the DR-MARKET lane (descriptive science).

Walls honoured here:
- DESIGN data only, via ``lib/pa_data.load_m1`` (the sealed loader gates
  everything; this module never asks for another split).
- No `pa_fill`, `pa_eval`, `pa_random` imports — no trading numbers exist.
- All structure is causal: every object at bar t is built from bars <= t
  (pivot confirmation lags are explicit in ``dc_pivots``).

Conventions
-----------
- ``bars`` = M5 dict from ``pa_data.resample`` (fields t,o,h,l,c,utc_min,
  srv_min,dow,warmup,pip,...).  ``m1`` = the M1 dict behind it.
- ABR = mean (h-l) of the last 50 closed M5 bars BEFORE bar t, i.e.
  ``abr[t] = mean(rng[t-50:t])`` (spec v1 abr_len=50; strictly causal).
- CET minute-of-day = server minute-of-day - 60 (mod 1440): the server clock
  is UTC+2/+3 (EU DST) and CET/CEST is UTC+1/+2 on the same EU schedule, so
  the difference is a constant one hour.  Proven empirically in M0.
- Block bootstrap: resample server days with replacement; the statistic is
  recomputed from the per-day event aggregates of the chosen days.
- Placebo matching: each real event is matched to placebo events in the same
  stratum (side x dow x utc 4h-bucket x ABR tercile x approach-distance
  decile); the contrast D = mean(real) - mean(placebo within stratum) is
  pooled over strata with a day-block bootstrap CI.
"""

import hashlib
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PA_PRO = os.path.dirname(os.path.dirname(_HERE))
for _p in (os.path.join(_PA_PRO, "lib"),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pa_clock          # noqa: E402
import pa_data           # noqa: E402
import pa_ledger         # noqa: E402
import pa_slots          # noqa: E402  (import side effects: thread caps, priority)

__all__ = [
    "CORE", "SEED", "HORIZONS", "FRESH", "AWAY", "TOL_PIPS", "TOL_ABR",
    "load_symbol", "abr_series", "cet_minutes", "server_year", "day_id",
    "day_blocks", "dc_pivots", "ema", "wilson", "bh", "ledger_row",
    "sha256_text",
    "pip_round_grid", "m1_window_for_bars", "first_hit", "write_json",
    "OUT",
]

CORE = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
SEED = 20260921
HORIZONS = (6, 12, 24, 48)          # M5 bars
FRESH = 24                          # bars with no touch (charter FRESH_BARS)
AWAY = 1.0                          # approach distance in ABR (charter AWAY_ATR)
TOL_PIPS = 1.0                      # edge_tol = max(1 pip, 0.25*ABR)
TOL_ABR = 0.25
OUT = os.path.join(_HERE, "out")
os.makedirs(OUT, exist_ok=True)


# ---------------------------------------------------------------- loading
def load_symbol(sym):
    """Return {"m1": m1dict, "m5": m5dict} for DESIGN.  One symbol at a time
    (memory ~100 MB each); callers del the dict when done."""
    m1 = pa_data.load_m1(sym, split="DESIGN", warmup_days=30)
    m5 = pa_data.resample(m1, "M5")
    return {"m1": m1, "m5": m5}


def abr_series(bars, length=50):
    """ABR[t] = mean high-low of the `length` closed bars BEFORE t (causal).
    NaN until enough history exists."""
    h = np.asarray(bars["h"], dtype=np.float64)
    l = np.asarray(bars["l"], dtype=np.float64)
    rng = h - l
    n = len(rng)
    cs = np.concatenate(([0.0], np.cumsum(rng)))
    abr = np.full(n, np.nan)
    if n > length:
        abr[length:] = (cs[length:n] - cs[:n - length]) / float(length)
    # abr[t] currently = mean of rng[t-length:t]  -> bars t-length..t-1. good.
    return abr


def ema(x, length):
    """Standard EMA with alpha=2/(length+1), seeded on x[0]; causal."""
    x = np.asarray(x, dtype=np.float64)
    a = 2.0 / (length + 1.0)
    out = np.empty_like(x)
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = a * x[i] + (1.0 - a) * out[i - 1]
    return out


def cet_minutes(bars):
    """CET minute-of-day of the bar CLOSE (server-60, mod 1440)."""
    sec = 300 if bars.get("tf", "M5") == "M5" else 60
    t_close = np.asarray(bars["t"], dtype=np.int64) + sec
    return ((t_close % 86400) // 60 - 60) % 1440


def server_year(bars):
    sec = 300 if bars.get("tf", "M5") == "M5" else 60
    return pa_clock.server_year(np.asarray(bars["t"], dtype=np.int64) + sec)


def day_id(bars):
    """Server-day index of each bar (t // 86400 on bar open time)."""
    return (np.asarray(bars["t"], dtype=np.int64) // 86400).astype(np.int64)


def day_blocks(bars, warmup_mask=True):
    """Unique day ids and per-day [start,end) bar ranges, warm-up days dropped
    when warmup_mask=True (warm-up bars never produce events)."""
    d = day_id(bars)
    warm = np.asarray(bars.get("warmup", np.zeros(len(d), bool)), dtype=bool)
    if warmup_mask:
        keep = ~warm
    else:
        keep = np.ones(len(d), bool)
    dk = d[keep]
    idx = np.flatnonzero(keep)
    edges = np.flatnonzero(np.concatenate(([True], dk[1:] != dk[:-1])))
    blocks = []
    for i, s in enumerate(edges):
        e = edges[i + 1] if i + 1 < len(edges) else len(dk)
        blocks.append((int(dk[s]), int(idx[s]), int(idx[e - 1]) + 1))
    return blocks


# ---------------------------------------------------------------- pivots
def dc_pivots(h, l, c, theta):
    """Directional-change pivots (Guillaume-style) on M5 bars.

    theta[i] = reversal threshold in PRICE units at bar i (e.g. k*ABR).
    A pivot is CONFIRMED at the bar where price has retraced theta from the
    running extreme.  Returns list of (confirm_idx, extreme_idx, kind, price)
    with kind +1 = swing high, -1 = swing low, ordered by confirm_idx.
    All confirmation info uses bars <= confirm_idx (causal).
    """
    n = len(c)
    pivots = []
    if n == 0:
        return pivots
    state = 0                     # +1 upswing (tracking highs), -1 downswing
    ext_idx = 0
    ext_price = h[0]
    # find first theta move to fix initial state
    hi = h[0]
    lo = l[0]
    hi_i = lo_i = 0
    started = False
    for i in range(1, n):
        th = theta[i]
        if not np.isfinite(th) or th <= 0:
            continue
        if not started:
            if h[i] > hi:
                hi = h[i]
                hi_i = i
            if l[i] < lo:
                lo = l[i]
                lo_i = i
            if hi - l[i] >= th:
                pivots.append((i, hi_i, +1, hi))
                state = -1
                ext_idx = lo_i
                ext_price = lo
                started = True
            elif h[i] - lo >= th:
                pivots.append((i, lo_i, -1, lo))
                state = +1
                ext_idx = hi_i
                ext_price = hi
                started = True
            continue
        if state == +1:           # upswing: track high, confirm low on retrace
            if h[i] > ext_price:
                ext_price = h[i]
                ext_idx = i
            if ext_price - l[i] >= th:
                pivots.append((i, ext_idx, +1, ext_price))
                state = -1
                ext_price = l[i]
                ext_idx = i
        else:
            if l[i] < ext_price:
                ext_price = l[i]
                ext_idx = i
            if h[i] - ext_price >= th:
                pivots.append((i, ext_idx, -1, ext_price))
                state = +1
                ext_price = h[i]
                ext_idx = i
    return pivots


# ------------------------------------------------------- touch machinery
def tol_array(abr, pip):
    """Per-bar edge tolerance: max(TOL_PIPS pips, TOL_ABR * ABR)."""
    return np.maximum(TOL_PIPS * pip, TOL_ABR * abr)


# ------------------------------------------------- outcome resolution (M1)
def m1_window_for_bars(m1_t, m5_t, t0, t1):
    """M1 index range [a,b) covering M5 bars [t0, t1)."""
    a = int(np.searchsorted(m1_t, m5_t[t0], side="left"))
    if t1 >= len(m5_t):
        b = len(m1_t)
    else:
        b = int(np.searchsorted(m1_t, m5_t[t1], side="left"))
    return a, b


def first_hit(m1, a, b, up_level, dn_level):
    """Scan M1 bars [a,b); return ("up"|"dn"|None, hit_idx, extreme_so_far).

    up_level/dn_level are absolute prices; NaN disables a barrier.
    extreme_so_far = (max_high, min_low) over the scanned path up to and incl.
    the hit bar (or the whole window on None).
    """
    h = m1["h"]
    l = m1["l"]
    mx = -np.inf
    mn = np.inf
    for i in range(a, b):
        hi = h[i]
        lo = l[i]
        if np.isfinite(up_level) and hi >= up_level:
            return "up", i, (max(mx, hi), min(mn, lo))
        if np.isfinite(dn_level) and lo <= dn_level:
            return "dn", i, (max(mx, hi), min(mn, lo))
        if hi > mx:
            mx = hi
        if lo < mn:
            mn = lo
    return None, b, (mx, mn)


# ------------------------------------------------- placebo machinery
def placebo_grid_levels(bars, abr, n_levels, span_abr, seed, offset_mode=None):
    """Per-day random placebo levels: dict day -> list of (price, birth).

    Uniform prices in [day_open - span*A, day_open + span*A], drawn once per
    day (birth = day start).  `offset_mode` None|'round20'|'round10' selects
    the 50-pip grid shifted by +20/+10 pips instead of uniform draws.
    """
    o = np.asarray(bars["o"], dtype=np.float64)
    pip = float(bars["pip"])
    out = {}
    for day, s, e in day_blocks(bars):
        A = float(abr[s]) if e > s else float("nan")  # causal: day-open ABR
        if not np.isfinite(A) or A <= 0:
            continue
        lo = o[s] - span_abr * A
        hi = o[s] + span_abr * A
        if offset_mode is None:
            import zlib as _zl
            rng = np.random.default_rng(
                SEED ^ (_zl.crc32(f"{day}".encode()) & 0x7FFFFFFF))
            prices = rng.uniform(lo, hi, size=n_levels).tolist()
        else:
            g = 50.0 * pip
            off = (20.0 if offset_mode == "round20" else 10.0) * pip
            k0 = int(np.floor(lo / g)) - 1
            k1 = int(np.ceil(hi / g)) + 1
            prices = [k * g + off for k in range(k0, k1 + 1)]
        out[day] = [(float(p), s) for p in prices]
    return out


# ------------------------------------------------------------- statistics


def default_key(e):
    """Stratum key: side x dow x 4h utc bucket x atr tercile x approach decile.
    Callers pre-bucket atr/approach into small ints on the event dict."""
    return (e["side"], e["dow"], e["utc_min"] // 240,
            e.get("atr_ter", 0), e.get("app_dec", 0))


def contrast_mats(real, plac, key_fn, val_fn):
    """Build dense (day x stratum) sum/count matrices for matched contrasts.

    Returns dict with matrices RS,RN,PS,PN, the day axis, stratum keys and
    per-event strata/day index arrays.  All downstream statistics (pooled,
    per-symbol, per-year) are cheap views of these four matrices.
    """
    rv = np.asarray([val_fn(e) for e in real], dtype=np.float64)
    pv = np.asarray([val_fn(e) for e in plac], dtype=np.float64)
    keys_r = [key_fn(e) for e in real]
    keys_p = [key_fn(e) for e in plac]
    strata = {}
    for i, k in enumerate(keys_r):
        strata.setdefault(k, {"r": [], "p": []})["r"].append(i)
    for j, k in enumerate(keys_p):
        if k in strata:
            strata[k]["p"].append(j)
    strata = {k: v for k, v in strata.items() if v["r"] and v["p"]}
    klist = sorted(strata, key=repr)
    kidx = {k: i for i, k in enumerate(klist)}
    days = sorted({e["day"] for e in real} | {e["day"] for e in plac})
    didx = {d: i for i, d in enumerate(days)}
    nd, ns = len(days), len(klist)
    RS = np.zeros((nd, ns)); RN = np.zeros((nd, ns))
    PS = np.zeros((nd, ns)); PN = np.zeros((nd, ns))
    rrow = np.empty(len(real), dtype=np.int64)
    rcol = np.full(len(real), -1, dtype=np.int64)
    prow = np.empty(len(plac), dtype=np.int64)
    pcol = np.full(len(plac), -1, dtype=np.int64)
    for i, e in enumerate(real):
        rrow[i] = didx[e["day"]]
        rcol[i] = kidx.get(keys_r[i], -1)
    for j, e in enumerate(plac):
        prow[j] = didx[e["day"]]
        pcol[j] = kidx.get(keys_p[j], -1)
    m = rcol >= 0
    np.add.at(RS, (rrow[m], rcol[m]), rv[m])
    np.add.at(RN, (rrow[m], rcol[m]), 1.0)
    m = pcol >= 0
    np.add.at(PS, (prow[m], pcol[m]), pv[m])
    np.add.at(PN, (prow[m], pcol[m]), 1.0)
    return {"RS": RS, "RN": RN, "PS": PS, "PN": PN, "days": days,
            "keys": klist}


def contrast_mats_arr(rday, rkey, rval, pday, pkey, pval):
    """Vectorized contrast_mats: events given as (day, key_int, value)
    arrays instead of dicts.  Same return schema as contrast_mats."""
    rday = np.asarray(rday); pday = np.asarray(pday)
    rkey = np.asarray(rkey); pkey = np.asarray(pkey)
    rval = np.asarray(rval, dtype=np.float64)
    pval = np.asarray(pval, dtype=np.float64)
    allk = np.unique(np.concatenate([rkey, pkey]))
    keep = np.isin(allk, rkey) & np.isin(allk, pkey)
    remap = np.full(len(allk), -1, np.int64)
    remap[keep] = np.arange(int(keep.sum()))
    days = np.unique(np.concatenate([rday, pday]))
    rrow = np.searchsorted(days, rday)
    prow = np.searchsorted(days, pday)
    rcol = remap[np.searchsorted(allk, rkey)]
    pcol = remap[np.searchsorted(allk, pkey)]
    nd, ns = len(days), int(keep.sum())
    RS = np.zeros((nd, ns)); RN = np.zeros((nd, ns))
    PS = np.zeros((nd, ns)); PN = np.zeros((nd, ns))
    m = rcol >= 0
    np.add.at(RS, (rrow[m], rcol[m]), rval[m])
    np.add.at(RN, (rrow[m], rcol[m]), 1.0)
    m = pcol >= 0
    np.add.at(PS, (prow[m], pcol[m]), pval[m])
    np.add.at(PN, (prow[m], pcol[m]), 1.0)
    return {"RS": RS, "RN": RN, "PS": PS, "PN": PN,
            "days": days.tolist(), "keys": allk[keep].tolist()}


def contrast_boot(cm, n_boot=2000, seed=SEED, min_cell=5, rows=None,
                  cols=None):
    """Hajek-weighted stratum contrast + joint day-block bootstrap.

    `rows`/`cols` optionally restrict the day axis / stratum axis (e.g. a
    single year or a single symbol's strata).  The bootstrap draws all day
    multiplicities at once (B x nd multinomial) and uses one BLAS multiply
    per arm matrix, so 2000 reps cost ~4 matrix products.
    """
    RS, RN, PS, PN = cm["RS"], cm["RN"], cm["PS"], cm["PN"]
    days = cm["days"]
    if rows is not None:
        RS, RN, PS, PN = RS[rows], RN[rows], PS[rows], PN[rows]
        days = [days[i] for i in rows]
    if cols is not None:
        RS, RN, PS, PN = RS[:, cols], RN[:, cols], PS[:, cols], PN[:, cols]
    nd, ns = RN.shape
    if ns == 0 or nd == 0:
        return {"D": float("nan"), "lo": float("nan"), "hi": float("nan"),
                "p": float("nan"), "n_strata": 0, "n_real": 0, "n_plac": 0,
                "days": days}

    # Stratum eligibility is decided once on UNWEIGHTED pooled support, so
    # the point estimate and every bootstrap replicate use the same stratum
    # set (previously reps could qualify cells that pooled support lacked,
    # producing D=nan with a finite CI).
    elig = (RN.sum(0) >= min_cell) & (PN.sum(0) >= min_cell)

    def stats(RS_, RN_, PS_, PN_):
        with np.errstate(divide="ignore", invalid="ignore"):
            rdif = np.where(RN_ > 0, RS_ / np.where(RN_ > 0, RN_, 1), 0.0)
            pdif = np.where(PN_ > 0, PS_ / np.where(PN_ > 0, PN_, 1), 0.0)
        present = (RN_ > 0) & (PN_ > 0)          # both arms in this rep
        valid = elig & present
        diffs = np.where(valid, rdif - pdif, 0.0)
        wgt = np.where(valid, RN_, 0.0)
        den = wgt.sum(axis=-1)
        num = (diffs * wgt).sum(axis=-1)
        return np.where(den > 0, num / np.where(den > 0, den, 1),
                        float("nan"))

    point = float(stats(RS.sum(0), RN.sum(0), PS.sum(0), PN.sum(0)))
    rng = np.random.default_rng(seed)
    if n_boot <= 0:
        return {"D": point, "lo": float("nan"), "hi": float("nan"),
                "p": float("nan"), "n_strata": int(ns),
                "n_real": int(RN.sum()), "n_plac": int(PN.sum()),
                "days": days, "boot": np.empty(0)}
    W = rng.multinomial(nd, np.full(nd, 1.0 / nd), size=n_boot).astype(
        np.float64)
    B = stats(W @ RS, W @ RN, W @ PS, W @ PN)
    Bf = B[np.isfinite(B)]
    out = {"D": point, "n_strata": int(ns),
           "n_real": int(RN.sum()), "n_plac": int(PN.sum()), "days": days,
           "boot": B}
    if len(Bf) >= 100:
        lo, hi = np.percentile(Bf, [2.5, 97.5])
        p = 2.0 * min(float((Bf <= 0).mean()), float((Bf > 0).mean()))
        out.update({"lo": float(lo), "hi": float(hi),
                    "p": min(1.0, max(p, 1.0 / (len(Bf) + 1)))})
    else:
        out.update({"lo": float("nan"), "hi": float("nan"),
                    "p": float("nan")})
    return out


def strat_assign(events, pool_vals):
    """Assign 'atr_ter'/'app_dec' strata fields in-place from pooled edges."""
    qa = np.quantile(pool_vals["abr"], [0.0, 1 / 3, 2 / 3, 1.0])
    qp = np.quantile(pool_vals["app"], np.linspace(0.0, 1.0, 11))
    for e in events:
        e["atr_ter"] = int(np.searchsorted(qa, e["abr"], side="right") - 1)
        e["app_dec"] = int(np.searchsorted(qp, e["approach_atr"],
                                           side="right") - 1)


def wilson(k, n, z=1.959963984540054):
    k = float(k)
    n = float(n)
    if n <= 0:
        return float("nan"), float("nan")
    p = k / n
    den = 1.0 + z * z / n
    ctr = (p + z * z / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, ctr - half), min(1.0, ctr + half)


def bh(pvals, q=0.10):
    """BH-FDR step-up q-values (same as pa_stats.bh_fdr, local copy)."""
    p = np.asarray(pvals, dtype=np.float64)
    n = p.shape[0]
    if n == 0:
        return np.array([]), np.array([], dtype=bool)
    order = np.argsort(p, kind="stable")
    ranked = p[order]
    qv = ranked * n / (np.arange(n) + 1)
    qv = np.minimum.accumulate(qv[::-1])[::-1]
    qv = np.clip(qv, 0, 1)
    out = np.empty(n)
    out[order] = qv
    return out, out <= q


def pip_round_grid(bars, off_pips=0.0):
    """Round-number grid step in price (50 pips) and offset."""
    pip = float(bars["pip"])
    return 50.0 * pip, off_pips * pip


# ---------------------------------------------------------------- ledger
def sha256_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def ledger_row(kind, family, params, key_metrics, n=None, symbols=None,
               tf="M5", split="DESIGN", extra=None):
    """Append one ledger row for the market lane."""
    body = {
        "round": "DR-MARKET",
        "family": family,
        "spec_sha256": params.pop("spec_sha256", None),
        "params": params,
        "split": split,
        "symbols": symbols or CORE,
        "tf": tf,
        "n": n,
        "key_metrics": key_metrics,
        "code_sha256": pa_ledger.code_sha256(),
        "data_sha256": None,
        "data_sha256_by_symbol": None,
    }
    if extra:
        body.update(extra)
    return pa_ledger.append(body, kind=kind)


def write_json(name, obj):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, sort_keys=True, default=str)
    return path
