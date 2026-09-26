"""sf_ctx.py — cached causal context for the SF01 setup families.

One cache file per (symbol, generator): ``rounds/SF01/zcache/<SYM>_<gen>.npz``.

Zone semantics
--------------
The reference interface is ``ZoneGen.run()`` for the zone UNIVERSE (creation,
band updates, retirement — the R01-tested pass) plus ``ZoneGen.views_at(t)``
state = replay of ``_step_zone`` over every bar in ``[born_idx, t]``.

``run_pass`` reproduces that combination incrementally:

- ``gen._on_bar(t)`` + ``gen._step_all(t)`` run exactly as ``run()`` — so the
  set of zones that exist is identical to a plain ``run()``;
- a shadow state ``z.meta["_stx"]`` per zone is stepped over every bar in
  ``[born_idx, t]`` under ``_replaying=True`` (side-effect free) — identical
  to ``state_at(z, t)`` element-wise;
- snapshots apply the same filters as ``views_at`` (``created_idx <= t <=
  end_idx``, finite strength) and the same sort/arming.

A unit test asserts bit-equality against ``run()`` + ``views_at`` on real
slices.

Recorded per bar t (all causal):

- zone records: every LIVE zone whose centre is within ``NEAR_ATR`` x
  ATR14(H1) of the close (armed and non-armed, broken included), padded to
  ``SLOTS`` slots.  ``armed`` follows ``arm_zones`` exactly (applied to the
  full sorted view set — far zones can never be armed, so the subset is
  faithful).
- scalars: atr_h1 (aligned), atr_m5, ema25/ema50 (M5 closes), h1/h4 trend
  sign (HH/HL + EMA20/50 slope; 0 = no trend), last confirmed H1 swing
  high/low (price + bar), plus bookkeeping (first_live_idx, pip).
- pivot tables: confirmed M5 +-3 pivots (same rule as line1_cluster) and H1
  +-2 pivots mapped to M5 index space; consumers gate on confirm_idx <= t.

No outcomes, no fills, no forward-looking values anywhere.
"""

import heapq
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PA_PRO = os.path.dirname(HERE)
ZONES_DIR = os.path.join(PA_PRO, "struct", "zones")
LIB = os.path.join(PA_PRO, "lib")
for _p in (HERE, ZONES_DIR, LIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pa_data  # noqa: E402
import pa_clock  # noqa: E402
from common import (  # noqa: E402
    ZoneContext, ZoneView, arm_zones, wilder_atr, confirmed_pivots,
    _fresh_state,
)

__all__ = [
    "NEAR_ATR", "SLOTS", "ZF", "CACHE_DIR", "cache_path", "build_arrays",
    "build_cache", "load_cache", "ema", "run_pass", "zones_at",
]

NEAR_ATR = 3.5          # record zones whose centre is within this x ATR(H1)
SLOTS = 10              # max zone records per bar (nearest/strongest first)
CACHE_DIR = os.path.join(PA_PRO, "rounds", "SF01", "zcache")

# zone record fields (index into the F axis of zf / columns of zlo/zhi)
ZF = {
    "zid": 0, "strength": 1, "touches": 2, "fresh": 3, "n_respected": 4,
    "role_flip": 5, "broken": 6, "broken_idx": 7, "broken_side": 8,
    "approach_side": 9, "age": 10, "last_touch": 11, "quality": 12,
    "armed": 13, "kind": 14, "scale": 15,
}
ZF_N = len(ZF)
_KINDS = {}   # kind string -> small int (per cache file, codebook in meta)
_SCALE = {"micro": 0, "meso": 1, "macro": 2}


def cache_path(symbol, gen_name, cache_dir=None):
    return os.path.join(cache_dir or CACHE_DIR, f"{symbol}_{gen_name}.npz")


def ema(c, period):
    """Standard EMA (seeded with SMA of first `period` values; NaN before)."""
    c = np.asarray(c, dtype=np.float64)
    n = len(c)
    out = np.full(n, np.nan)
    if n < period:
        return out
    a = 2.0 / (period + 1.0)
    out[period - 1] = c[:period].mean()
    for i in range(period, n):
        out[i] = a * c[i] + (1.0 - a) * out[i - 1]
    return out


def _trend_from(hi2, lo2, ema_fast, ema_slow):
    """+1/-1/0 trend from the last two confirmed swing highs/lows + EMAs.

    ``hi2``/``lo2`` are the running lists of confirmed pivot prices (oldest
    first); only the last two of each are used.  All inputs causal.
    """
    if not (np.isfinite(ema_fast) and np.isfinite(ema_slow)):
        return 0
    if len(hi2) < 2 or len(lo2) < 2:
        return 0
    hh = hi2[-1] > hi2[-2]
    hl = lo2[-1] > lo2[-2]
    lh = hi2[-1] < hi2[-2]
    ll = lo2[-1] < lo2[-2]
    if hh and hl and ema_fast > ema_slow:
        return 1
    if lh and ll and ema_fast < ema_slow:
        return -1
    return 0


def _kind_code(kind):
    if kind not in _KINDS:
        _KINDS[kind] = len(_KINDS) + 1
    return _KINDS[kind]


def run_pass(ctx, gen, cb=None):
    """Forward pass identical to ``ZoneGen.run()`` for the zone UNIVERSE, with
    an exact replay-semantics state track for reads.

    ``_on_bar`` + ``_step_all`` run exactly as ``run()`` does, so zone
    creation, band updates and retirement match the tested pipeline bit for
    bit.  Separately, each zone carries a shadow state ``z.meta["_stx"]``
    stepped over every bar in ``[born_idx, t]`` under ``_replaying=True``
    (side-effect free) — identical to what ``state_at``/``views_at`` would
    compute.  ``cb(t, views)`` receives list[ZoneView] built from the shadow
    states, with ``.meta["_stx_state"]`` = the raw state dict and
    ``.meta["_armed"]`` set by ``arm_zones``.
    """
    n = ctx.n
    bars = ctx.bars
    prev_zones = 0
    for t in range(n):
        gen._t_now = t
        gen._on_bar(t)
        gen._step_all(t)
        # shadow-state track (replay semantics, no lifecycle side effects)
        gen._replaying = True
        try:
            if len(gen._zones) > prev_zones:
                for z in gen._zones[prev_zones:]:
                    st = _fresh_state()
                    z.meta["_stx"] = st
                    for j in range(z.born_idx, t):
                        gen._step_zone(z, j, st)
                prev_zones = len(gen._zones)
            for z in gen._live.values():
                st = z.meta.get("_stx")
                if st is None:
                    st = _fresh_state()
                    z.meta["_stx"] = st
                    for j in range(z.born_idx, t):
                        gen._step_zone(z, j, st)
                if t >= z.born_idx:
                    gen._step_zone(z, t, st)
        finally:
            gen._replaying = False
        if cb is not None:
            A = ctx.a(t)
            views = []
            if A == A and A > 0:
                close = float(bars["c"][t])
                near = NEAR_ATR * A
                for z in gen._live.values():
                    if t < z.created_idx or t < z.born_idx or t > z.end_idx:
                        continue
                    lo, hi = z.band_at(t)
                    if abs(0.5 * (lo + hi) - close) > near:
                        continue
                    stx = z.meta.get("_stx")
                    if stx is None:
                        continue
                    got = gen._strength(z, t, stx)
                    if got is None:
                        continue
                    S, parts = got
                    st = stx
                    fresh = (st["broken"] is None
                             and (st["last_touch"] is None
                                  or (t - st["last_touch"]) > gen.cfg["fresh_bars"]))
                    meta = {k: v for k, v in z.meta.items() if k != "_stx"}
                    meta["_stx_state"] = st
                    views.append(ZoneView(
                        zid=z.zid, kind=z.kind, scale=z.scale, lo=lo, hi=hi,
                        strength=S, born_idx=z.born_idx,
                        touches=st["touches"], fresh=fresh,
                        n_respected=st["n_respected"],
                        broken_idx=st["broken"], role_flip=st["role_flip"],
                        age=t - z.born_idx, last_touch=st["last_touch"],
                        quality=z.quality_at(t), parts=parts,
                        meta=meta))
                views.sort(key=lambda v: (-v.strength, v.zid))
                armed = {v.zid for v in arm_zones(views, close, A, gen.cfg)}
                for v in views:
                    v.meta["_armed"] = v.zid in armed
            cb(t, views)
    gen._reindex()
    return gen


def _make_gen(ctx, gen_name):
    import registry
    return registry.get(gen_name)(ctx)


def build_arrays(ctx, gen_name, symbol, split, h4, progress=None):
    """Run the zone pass on ``ctx`` and return the cache dict (no file I/O).

    ``h4`` = H4 bars dict for the same slice (H4 trend context).  All arrays
    are indexed by M5 bar and are causal: row t uses only information known
    at the close of bar t.
    """
    n = ctx.n
    m5 = ctx.bars
    h1 = ctx.h1
    gen = _make_gen(ctx, gen_name)

    # ---- per-bar scalars ------------------------------------------------
    atr_h1 = np.full(n, np.nan, dtype=np.float64)
    for t in range(n):
        atr_h1[t] = ctx.a(t)
    atr_m5 = np.asarray(ctx.atr_m5, dtype=np.float64)
    ema25 = ema(m5["c"], 25)
    ema50 = ema(m5["c"], 50)
    # H1/H4 trend sign per M5 bar (values known at last closed bucket)
    e20_h1 = ema(h1["c"], 20)
    e50_h1 = ema(h1["c"], 50)
    e20_h4 = ema(h4["c"], 20)
    e50_h4 = ema(h4["c"], 50)
    h1_close_t = np.asarray(h1["t"], dtype=np.int64) + 3600
    h4_close_t = np.asarray(h4["t"], dtype=np.int64) + 14400
    m5_close = np.asarray(m5["t"], dtype=np.int64) + 300
    h1_pos = np.searchsorted(h1_close_t, m5_close, side="right") - 1
    h4_pos = np.searchsorted(h4_close_t, m5_close, side="right") - 1
    h1p = ctx.h1_pivots(2)
    h4piv = confirmed_pivots(h4, 2)
    h4p = []
    for (j, price, side, conf) in h4piv:
        if conf >= len(h4_close_t):
            continue
        m5c = int(np.searchsorted(m5_close, h4_close_t[conf], side="left"))
        m5a = int(np.searchsorted(m5["t"], h4["t"][j], side="left"))
        if m5c < n:
            h4p.append((int(j), float(price), int(side), m5c, m5a))
    tr1 = np.zeros(n, dtype=np.int8)
    tr4 = np.zeros(n, dtype=np.int8)
    h1_hi_px = np.full(n, np.nan)
    h1_lo_px = np.full(n, np.nan)
    h1_hi_i = np.full(n, -1, dtype=np.int64)
    h1_lo_i = np.full(n, -1, dtype=np.int64)
    h1_hi_seen, h1_lo_seen = [], []          # (m5_anchor, price)
    h4_hi_seen, h4_lo_seen = [], []          # prices only (trend)
    pi1 = pi4 = 0
    for t in range(n):
        while pi1 < len(h1p) and h1p[pi1][3] <= t:
            (_hj, px, sd, _mc, ma) = h1p[pi1]
            (h1_hi_seen if sd == 1 else h1_lo_seen).append((ma, px))
            pi1 += 1
        while pi4 < len(h4p) and h4p[pi4][3] <= t:
            (_hj, px, sd, _mc, _ma) = h4p[pi4]
            (h4_hi_seen if sd == 1 else h4_lo_seen).append(px)
            pi4 += 1
        i1, i4 = int(h1_pos[t]), int(h4_pos[t])
        tr1[t] = _trend_from(
            [p for _, p in h1_hi_seen[-2:]], [p for _, p in h1_lo_seen[-2:]],
            e20_h1[i1] if 0 <= i1 else np.nan,
            e50_h1[i1] if 0 <= i1 else np.nan)
        tr4[t] = _trend_from(
            h4_hi_seen[-2:], h4_lo_seen[-2:],
            e20_h4[i4] if 0 <= i4 else np.nan,
            e50_h4[i4] if 0 <= i4 else np.nan)
        if h1_hi_seen:
            h1_hi_i[t], h1_hi_px[t] = h1_hi_seen[-1]
        if h1_lo_seen:
            h1_lo_i[t], h1_lo_px[t] = h1_lo_seen[-1]

    # ---- zone pass -------------------------------------------------------
    zlo = np.full((n, SLOTS), np.nan, dtype=np.float64)
    zhi = np.full((n, SLOTS), np.nan, dtype=np.float64)
    zf = np.zeros((n, SLOTS, ZF_N), dtype=np.float64)
    zcnt = np.zeros(n, dtype=np.int64)

    # broken_side / approach_side live in the pass state (z.st), not in
    # ZoneView — look them up on the live zone objects at snapshot time.
    live_by_zid = {}

    def _snap2(t, views):
        k = min(len(views), SLOTS)
        zcnt[t] = len(views)
        for s in range(k):
            v = views[s]
            z = live_by_zid.get(v.zid)
            st = z.meta.get("_stx") if z is not None else None
            st = st or {}
            zlo[t, s], zhi[t, s] = v.lo, v.hi
            zf[t, s, ZF["zid"]] = v.zid
            zf[t, s, ZF["strength"]] = v.strength
            zf[t, s, ZF["touches"]] = v.touches
            zf[t, s, ZF["fresh"]] = 1.0 if v.fresh else 0.0
            zf[t, s, ZF["n_respected"]] = v.n_respected
            zf[t, s, ZF["role_flip"]] = v.role_flip
            zf[t, s, ZF["broken"]] = 1.0 if v.broken_idx is not None else 0.0
            zf[t, s, ZF["broken_idx"]] = (v.broken_idx
                                         if v.broken_idx is not None else -1)
            zf[t, s, ZF["broken_side"]] = st.get("broken_side") or 0
            zf[t, s, ZF["approach_side"]] = st.get("approach_side") or 0
            zf[t, s, ZF["age"]] = v.age
            zf[t, s, ZF["last_touch"]] = (v.last_touch
                                         if v.last_touch is not None else -1)
            zf[t, s, ZF["quality"]] = v.quality
            zf[t, s, ZF["armed"]] = 1.0 if v.meta.get("_armed") else 0.0
            zf[t, s, ZF["kind"]] = _kind_code(v.kind)
            zf[t, s, ZF["scale"]] = _SCALE.get(v.scale, 0)
        if progress and (t % 50000 == 0):
            progress(t, n)

    def _cb(t, views):
        live_by_zid.clear()
        live_by_zid.update(gen._live)
        _snap2(t, views)

    run_pass(ctx, gen, cb=_cb)

    # ---- pivot tables ----------------------------------------------------
    piv = ctx.pivots(3)
    piv_idx = np.array([p[0] for p in piv], dtype=np.int64)
    piv_px = np.array([p[1] for p in piv], dtype=np.float64)
    piv_side = np.array([p[2] for p in piv], dtype=np.int64)
    piv_conf = np.array([p[3] for p in piv], dtype=np.int64)
    h1pi = np.array([p[0] for p in h1p], dtype=np.int64)
    h1pp = np.array([p[1] for p in h1p], dtype=np.float64)
    h1ps = np.array([p[2] for p in h1p], dtype=np.int64)
    h1pc = np.array([p[3] for p in h1p], dtype=np.int64)
    h1pa = np.array([p[4] for p in h1p], dtype=np.int64)

    warm = np.asarray(m5.get("warmup", np.zeros(n, dtype=bool)), dtype=bool)
    live_i = np.flatnonzero(~warm)
    return {
        "symbol": symbol, "generator": gen_name, "split": split,
        "tf": "M5", "t": np.asarray(m5["t"], dtype=np.int64),
        "o": np.asarray(m5["o"], dtype=np.float64),
        "h": np.asarray(m5["h"], dtype=np.float64),
        "l": np.asarray(m5["l"], dtype=np.float64),
        "c": np.asarray(m5["c"], dtype=np.float64),
        "pip": float(m5["pip"]),
        "first_live_idx": int(live_i[0]) if len(live_i) else n,
        "warmup": warm,
        "s_atr_h1": atr_h1, "s_atr_m5": atr_m5,
        "s_ema25": ema25, "s_ema50": ema50,
        "s_tr_h1": tr1, "s_tr_h4": tr4,
        "s_h1_hi_px": h1_hi_px, "s_h1_lo_px": h1_lo_px,
        "s_h1_hi_i": h1_hi_i, "s_h1_lo_i": h1_lo_i,
        "zlo": zlo, "zhi": zhi, "zf": zf, "zcnt": zcnt,
        "piv_idx": piv_idx, "piv_px": piv_px,
        "piv_side": piv_side, "piv_conf": piv_conf,
        "h1p_i": h1pi, "h1p_px": h1pp, "h1p_side": h1ps,
        "h1p_conf": h1pc, "h1p_anchor": h1pa,
        "kind_codebook": dict(_KINDS),
    }


def build_cache(symbol, gen_name, split="DESIGN", warmup_days=30,
                cache_dir=None, progress=None):
    """Load DESIGN data for ``symbol``, run the zone pass, write npz cache."""
    m1 = pa_data.load_m1(symbol, split=split, warmup_days=warmup_days)
    m5 = pa_data.resample(m1, "M5")
    h1 = pa_data.resample(m1, "H1")
    h4 = pa_data.resample(m1, "H4")
    ctx = ZoneContext(m5, h1)
    out = build_arrays(ctx, gen_name, symbol, split, h4, progress=progress)
    d = cache_dir or CACHE_DIR
    os.makedirs(d, exist_ok=True)
    path = cache_path(symbol, gen_name, d)
    np.savez_compressed(path, **{
        k: (np.array([repr(v)]) if isinstance(v, dict)
            else np.array([v]) if isinstance(v, str) else v)
        for k, v in out.items()})
    return path


def load_cache(symbol, gen_name, cache_dir=None):
    """Load a cache npz; verifies it exists and returns a plain dict."""
    path = cache_path(symbol, gen_name, cache_dir)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"zone cache missing: {path} — build it via build_cache() first")
    z = np.load(path, allow_pickle=False)
    out = {}
    for k in z.files:
        v = z[k]
        if v.shape == (1,) and v.dtype.kind in ("U", "S"):
            out[k] = str(v[0])
        else:
            out[k] = v
    return out


def zones_at(D, t):
    """Zone records at bar ``t`` of a cache dict ``D`` — list of dicts with
    keys = ZF field names + ``lo``/``hi`` (band), strongest first, at most
    ``SLOTS`` entries.  ``broken_idx``/``last_touch`` are -1 when none;
    ``approach_side``/``broken_side`` are -1/0/+1 with 0 = none."""
    out = []
    if t < 0 or t >= len(D["t"]):
        return out
    for s in range(int(D["zcnt"][t]) if "zcnt" in D else SLOTS):
        if s >= D["zf"].shape[1]:
            break
        lo = float(D["zlo"][t, s])
        if lo != lo:  # NaN pad
            continue
        rec = {"lo": lo, "hi": float(D["zhi"][t, s])}
        for name, k in ZF.items():
            rec[name] = D["zf"][t, s, k]
        out.append(rec)
    return out
