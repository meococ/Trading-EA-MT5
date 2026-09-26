"""common.py — shared causal zone infrastructure for the T-PAPRO-ZONE-1 bake-off.

Authority: `docs/CHARTER_ADDENDUM_1.md` (PERCEPTION IS ZONE-FIRST: horizontal
structure is ZONES ``[lo, hi]`` with width 0.2-0.6 x ATR14(H1); at most ~4-6
zones armed near price; never exact prices) and `struct/PERCEPTION_SPEC.md`
(causal contract: every object at bar t uses bars <= t only; strength v0 §5).

No outcomes live here: no fills, no PnL, no forward returns.  A zone is a
static band plus a causal state machine; `zones_at(t)` is a pure function of
bars <= t (prefix invariance is tested in `tests/test_prefix_invariance.py`).

Design (mirrors the LINE-1 causal pattern, `EA_VolmanPA/research/lines/vpa_lines.py`):
- one forward pass `run()`; a zone's state is updated bar by bar through
  `_step_zone`; a query at an arbitrary past bar `t` replays the same
  `_step_zone` over bars[born..t] so the reported state is exactly the state
  the pass built (single source of truth, same idea as `_state_at` :808-840).
  Replays are side-effect free (`_replaying` guard).
- geometry has a step history: a zone born at `born_idx` may widen when new
  swings join the cluster (`set_band`), and `band_at(t)` is causal by index.
  Generator quality (member count, density height, impulse amplitude) is a
  step history too (`add_quality` / `quality_at`), so no query can see a
  future update.
- generators only create/update bands (`_on_bar`); touch/response/break/
  reclaim/retire logic is IDENTICAL for every candidate (bake-off fairness).

Zone state semantics (pre-declared v0, frozen for the physics run):
- TOUCH: bar range intersects ``[lo, hi]``; episodes separated by
  `min_touch_sep` = 2 bars.  A wick through the band that closes back inside
  is a touch, not a break (addendum 1 item 1).
- BREAK: a close through the zone to the FAR side of its role, by more than
  `break_atr` = 0.10 x ATR14(H1): a ceiling (approach from below) breaks on
  close > hi + brk, a floor (approach from above) on close < lo - brk.  A
  close back on the approach side is a TEST, never a break, so a 1.0 x A
  response can be counted.  A zone with no touch yet has no role and cannot
  break (declared v0).
- RECLAIM (BREAK_FAIL): after a break, a close back inside the band within
  `reclaim_bars` = 96 bars restores the intact state (pre-break role kept);
  counted in `n_reclaims`.
- FLIP_CONFIRMED: if the reclaim window lapses and price still closes beyond
  the break threshold, the zone's role flips (`role_flip` = 1); only then the
  zone is usable in its new role (PERCEPTION_SPEC §4 role-flip rule).
- RESPECTED TEST: a touch followed within `resp_window` = 48 bars by a close
  `resp_move_atr` = 1.0 x ATR14(H1) away from the near edge (on the approach
  side) and no break before that close; counted in `n_respected`.
- FRESH: intact and no range-intersection in the last `fresh_bars` = 24 bars.
- RETIRE: at `born_idx + max_age_bars` (generator default 2880 = 10 server
  days), or `break + break_keep_bars` (192) after a break.

Strength score v0 (pre-declared weights, sum 1.00; PERCEPTION_SPEC §5 with a
generator-quality term; `T_vol` is 0 for every generator because the PA-PRO
loader does not expose tick volume — a uniform term, so within-generator
ranking is unaffected; `T_ref` is filled by `refs.py`):

    S = 0.30*T_touch + 0.20*T_resp + 0.15*T_rec + 0.10*T_age
      + 0.10*T_scale + 0.05*T_role + 0.05*T_ref + 0.05*T_qual

Arming rule (addendum 1 item 3, LEAD_REVIEW item 3): keep zones whose
distance to the close is <= `arm_near_atr` (2.0) x ATR14(H1); drop a weaker
candidate whose center is within `arm_dedupe_atr` (0.25) x ATR14(H1) of an
already-armed stronger zone; keep at most `arm_max` (6), strongest first.
"""

import bisect
import heapq
import math

import numpy as np

__all__ = [
    "DEFAULTS", "Zone", "AtrH1", "ZoneContext", "ZoneGen", "ZoneView",
    "wilder_atr", "confirmed_pivots", "zone_dict", "arm_zones",
]

DEFAULTS = {
    # widths / geometry (ATR14(H1) units)
    "width_atr": 0.25,          # zone band width around the cluster (0.2-0.6 band)
    "max_width_atr": 0.60,      # hard cap (addendum 1 item 1)
    "break_atr": 0.10,          # close beyond band edge by > this = BREAK
    "min_touch_sep": 2,         # bars between two counted touch episodes
    "resp_move_atr": 1.0,       # respected test: 1.0 x ATR14(H1) away
    "resp_window": 48,          # ... within 48 closed bars
    "reclaim_bars": 96,         # close back inside within this = BREAK_FAIL
    "fresh_bars": 24,           # no touch in the last 24 bars = fresh
    "max_age_bars": 2880,       # retire 10 server days after birth
    "break_keep_bars": 192,     # a broken zone stays 1 day for role reversal
    # arming
    "arm_near_atr": 2.0,        # only zones within +-2 x ATR14(H1) of close
    "arm_dedupe_atr": 0.25,     # centers closer than this are one zone
    "arm_max": 6,               # at most 6 armed zones on the chart
    # strength weights (sum = 1.00 - pre-declared v0)
    "w_touch": 0.30,
    "w_resp": 0.20,
    "w_rec": 0.15,
    "w_age": 0.10,
    "w_scale": 0.10,
    "w_role": 0.05,
    "w_ref": 0.05,
    "w_qual": 0.05,
    "touch_full": 4.0,
    "resp_full": 3.0,
    "rec_half_life": 288.0,     # 1 server day
    "age_full": 288.0,
    "scale_micro": 0.4,
    "scale_meso": 0.7,
    "scale_macro": 1.0,
}


def wilder_atr(h, l, c, period=14):
    """Wilder ATR on closed bars; NaN until bar `period-1`.  Vectorized."""
    h = np.asarray(h, dtype=np.float64)
    l = np.asarray(l, dtype=np.float64)
    c = np.asarray(c, dtype=np.float64)
    n = len(h)
    out = np.full(n, np.nan)
    if n == 0:
        return out
    tr = np.empty(n)
    tr[0] = h[0] - l[0]
    if n > 1:
        tr[1:] = np.maximum.reduce(
            [h[1:] - l[1:], np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])]
        )
    if n < period:
        return out
    out[period - 1] = tr[:period].mean()
    a = (period - 1.0) / period
    for i in range(period, n):
        out[i] = a * out[i - 1] + (1.0 - a) * tr[i]
    return out


def confirmed_pivots(bars, k):
    """Confirmed +-k-bar fractals, LINE-1's rule (`vpa_lines.py:436-450`).

    A pivot high at j is ``h[j] > max(h[j-k:j])`` and
    ``h[j] >= max(h[j+1:j+k+1])``; it is known only at ``confirm_idx = j + k``.
    Returns ``(idx, price, side, confirm_idx)`` sorted by confirm_idx.
    Precomputing the whole array is causal because every consumer gates on
    ``confirm_idx <= t``.  (This is the swing rule only: LINE-1's scoring,
    including the look-ahead-buggy `_htf_align`, is deliberately NOT used.)
    """
    h = np.asarray(bars["h"], dtype=np.float64)
    l = np.asarray(bars["l"], dtype=np.float64)
    n = len(h)
    out = []
    for j in range(k, n - k):
        if h[j] > h[j - k:j].max() and h[j] >= h[j + 1:j + k + 1].max():
            out.append((j, float(h[j]), +1, j + k))
        if l[j] < l[j - k:j].min() and l[j] <= l[j + 1:j + k + 1].min():
            out.append((j, float(l[j]), -1, j + k))
    out.sort(key=lambda p: (p[3], p[0]))
    return out


class AtrH1:
    """ATR14(H1) aligned to M5 bars: the newest H1 bucket CLOSED at or before
    the M5 bar's close (causal; the H1 bucket that contains t is never used)."""

    def __init__(self, h1, period=14):
        self.t = np.asarray(h1["t"], dtype=np.int64)
        self.close_t = self.t + 3600
        self.atr = wilder_atr(h1["h"], h1["l"], h1["c"], period)
        self._period = period

    def align(self, m5_t):
        """Index of the newest H1 bucket whose close <= (m5 close = t + 300)."""
        m5_close = np.asarray(m5_t, dtype=np.int64) + 300
        return np.searchsorted(self.close_t, m5_close, side="right") - 1

    def at(self, idx):
        if idx < 0 or idx >= len(self.atr):
            return float("nan")
        return float(self.atr[idx])

    def valid(self, idx):
        a = self.at(idx)
        return a == a and a > 0


class Zone:
    """One horizontal zone band with causal step histories for geometry and
    generator quality."""

    __slots__ = ("zid", "kind", "scale", "born_idx", "created_idx", "end_idx",
                 "geom_idx", "geom_hist", "qual_idx", "qual_hist", "st", "meta")

    def __init__(self, zid, kind, scale, born_idx, created_idx, lo, hi,
                 end_idx, quality=0.0, meta=None):
        self.zid = zid
        self.kind = kind
        self.scale = scale
        self.born_idx = int(born_idx)
        self.created_idx = int(created_idx)
        self.end_idx = int(end_idx)
        self.geom_idx = [int(created_idx)]
        self.geom_hist = [(float(lo), float(hi))]
        self.qual_idx = [int(created_idx)]
        self.qual_hist = [float(quality)]
        self.st = _fresh_state()
        self.meta = dict(meta or {})

    def band_at(self, t):
        k = bisect.bisect_right(self.geom_idx, t) - 1
        if k < 0:
            k = 0
        return self.geom_hist[k]

    def set_band(self, t, lo, hi):
        lo0, hi0 = self.geom_hist[-1]
        if abs(lo - lo0) > 1e-12 or abs(hi - hi0) > 1e-12:
            self.geom_idx.append(int(t))
            self.geom_hist.append((float(lo), float(hi)))

    def add_quality(self, t, quality):
        if abs(float(quality) - self.qual_hist[-1]) > 1e-12:
            self.qual_idx.append(int(t))
            self.qual_hist.append(float(quality))

    def quality_at(self, t):
        k = bisect.bisect_right(self.qual_idx, t) - 1
        if k < 0:
            k = 0
        return self.qual_hist[k]


def _fresh_state():
    return {
        "touches": 0, "last_touch": None, "n_respected": 0,
        "n_reclaims": 0, "broken": None, "role_flip": 0, "broken_side": None,
        "pending_from": None, "pending_until": None, "approach_side": None,
        "flip_deadline": -1,
    }


class ZoneView:
    """Immutable view returned by `zones_at` (the required common interface)."""

    __slots__ = ("zid", "kind", "scale", "lo", "hi", "strength", "born_idx",
                 "touches", "fresh", "n_respected", "broken_idx", "role_flip",
                 "age", "last_touch", "quality", "parts", "meta")

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

    @property
    def center(self):
        return 0.5 * (self.lo + self.hi)

    @property
    def width(self):
        return self.hi - self.lo

    def as_dict(self):
        return {
            "zid": self.zid, "kind": self.kind, "scale": self.scale,
            "lo": round(self.lo, 6), "hi": round(self.hi, 6),
            "strength": round(self.strength, 4),
            "born_idx": self.born_idx, "touches": self.touches,
            "fresh": bool(self.fresh), "n_respected": self.n_respected,
            "broken_idx": self.broken_idx, "role_flip": int(self.role_flip),
            "age": self.age, "last_touch": self.last_touch,
            "quality": round(self.quality, 4),
            "parts": {k: round(v, 4) for k, v in self.parts.items()},
            "meta": dict(self.meta),
        }


def zone_dict(z):
    """Common-interface dict: {lo, hi, kind, strength, born_idx, touches, fresh}."""
    return {
        "lo": z.lo, "hi": z.hi, "kind": z.kind, "strength": z.strength,
        "born_idx": z.born_idx, "touches": z.touches, "fresh": bool(z.fresh),
    }


class ZoneContext:
    """Shared, immutable market context every generator consumes."""

    def __init__(self, bars, h1):
        self.bars = bars
        self.h1 = h1
        self.pip = float(bars["pip"])
        self.symbol = bars.get("symbol")
        self.n = len(bars["t"])
        self.atr_h1 = AtrH1(h1, 14)
        self.atr_m5 = wilder_atr(bars["h"], bars["l"], bars["c"], 14)
        self.h1_idx = self.atr_h1.align(bars["t"])
        self._piv_cache = {}
        self._h1_piv_cache = {}
        self.m5_close = np.asarray(bars["t"], dtype=np.int64) + 300
        self.h1_close = np.asarray(h1["t"], dtype=np.int64) + 3600
        self.h1_start = np.asarray(h1["t"], dtype=np.int64)
        from refs import RefBook
        self.refs = RefBook(bars, self)

    def a(self, t):
        """ATR14(H1) known at the close of M5 bar t (NaN when not ready)."""
        if t < 0 or t >= self.n:
            return float("nan")
        return self.atr_h1.at(int(self.h1_idx[t]))

    def pivots(self, k):
        """Cached `confirmed_pivots(bars, k)` (causal via confirm_idx gating)."""
        if k not in self._piv_cache:
            self._piv_cache[k] = confirmed_pivots(self.bars, k)
        return self._piv_cache[k]

    def h1_pivots(self, k=2):
        """Cached +-k-bar H1 fractals mapped into M5 index space.

        Returns ``(h1_idx, price, side, m5_confirm, m5_anchor)``:
        - ``m5_confirm`` = first M5 bar whose close >= the close of the H1
          confirm bucket (j + k); the pivot is usable only from that bar;
        - ``m5_anchor`` = first M5 bar of the pivot's own H1 bucket.
        Entries whose confirm bucket lies beyond the M5 slice are dropped.
        """
        if k in self._h1_piv_cache:
            return self._h1_piv_cache[k]
        piv = confirmed_pivots(self.h1, k)
        out = []
        n_m5 = len(self.bars["t"])
        for (j, price, side, conf) in piv:
            if conf >= len(self.h1_close):
                continue
            m5c = int(np.searchsorted(self.m5_close, self.h1_close[conf],
                                      side="left"))
            if m5c >= n_m5:
                continue
            m5a = int(np.searchsorted(self.bars["t"], self.h1_start[j],
                                      side="left"))
            out.append((int(j), float(price), int(side), m5c, m5a))
        self._h1_piv_cache[k] = out
        return out


class ZoneGen:
    """Base class: forward causal pass + replay-based queries."""

    NAME = "base"
    SCALE = "micro"
    QUAL_REF = 1.0
    DEFAULTS = {}

    def __init__(self, ctx, params=None, name=None):
        self.ctx = ctx
        self.cfg = dict(DEFAULTS)
        self.cfg.update(self.DEFAULTS)
        if params:
            self.cfg.update(params)
        if name:
            self.NAME = name
        self.n = ctx.n
        self.bars = ctx.bars
        self._zones = []
        self._live = {}            # zid -> Zone (alive in the pass)
        self._pending = []         # zones created since last reindex
        self._sorted = []          # (lo, zid) live zones, rebuilt periodically
        self._warm = {}            # zid -> last bar that needs response steps
        self._retire_heap = []
        self._next_zid = 1
        self._reindex_every = 256
        self._t_now = -1
        self._replaying = False
        self.counters = {}

    # --------------------------------------------------------------- helpers
    def _cnt(self, key, n=1):
        self.counters[key] = self.counters.get(key, 0) + n

    def _new_zone(self, kind, scale, born_idx, created_idx, lo, hi,
                  end_idx=None, quality=0.0, meta=None):
        end = born_idx + self.cfg["max_age_bars"] if end_idx is None else end_idx
        z = Zone(self._next_zid, kind, scale, born_idx, created_idx, lo, hi,
                 end, quality=quality, meta=meta)
        self._next_zid += 1
        self._zones.append(z)
        self._live[z.zid] = z
        self._pending.append(z)
        self._push_retire(z.zid, end)
        self._cnt("zone_created")
        return z

    def _push_retire(self, zid, end):
        heapq.heappush(self._retire_heap, (int(end), int(zid)))

    def _retire(self, z, idx):
        z.end_idx = min(z.end_idx, int(idx))
        self._live.pop(z.zid, None)
        self._warm.pop(z.zid, None)

    # -------------------------------------------------- generator hook (toys)
    def _on_bar(self, t):
        """Generator-specific: create/update zone bands using bars <= t only."""
        raise NotImplementedError

    def _step_all(self, t):
        """Update the state of live zones affected by bar t."""
        A = self.ctx.a(t)
        if A != A or A <= 0:
            return
        b = self.bars
        lo_b, hi_b = b["l"][t], b["h"][t]
        pad = A * self.cfg["break_atr"] + 1e-9
        ids = set()
        arr = self._sorted
        if arr:
            Hi = hi_b + pad
            Lo = lo_b - pad
            k0 = bisect.bisect_left(
                arr, (Lo - self.cfg["max_width_atr"] * A, -1))
            for (zlo, zid) in arr[k0:]:
                if zlo > Hi:
                    break
                z = self._live.get(zid)
                if z is None:
                    continue
                z_lo, z_hi = z.band_at(t)
                if z_hi + pad >= Lo and z_lo - pad <= Hi:
                    ids.add(zid)
        for z in self._pending:
            z_lo, z_hi = z.band_at(t)
            if z_hi + pad >= lo_b and z_lo - pad <= hi_b:
                ids.add(z.zid)
        for zid, expiry in list(self._warm.items()):
            if t <= expiry:
                ids.add(zid)
            else:
                self._warm.pop(zid, None)
        for zid in ids:
            z = self._live.get(zid)
            if z is None or t < z.born_idx or t < z.created_idx:
                continue
            self._step_zone(z, t, z.st)
        while self._retire_heap and self._retire_heap[0][0] < t:
            end, zid = heapq.heappop(self._retire_heap)
            z = self._live.get(zid)
            if z is not None and z.end_idx <= t:
                self._retire(z, z.end_idx)
        if t % self._reindex_every == 0:
            self._reindex()

    def _reindex(self):
        self._sorted = sorted((z.band_at(self._t_now)[0], z.zid)
                              for z in self._live.values())
        self._pending = []

    # ------------------------------------------------------- state machine
    def _step_zone(self, z, j, st):
        """One bar of a zone's life.  Shared by the pass and by replay, so the
        reported state is exactly the state that was built (LINE-1 pattern).
        Side-effect free while `_replaying` is set."""
        A = self.ctx.a(j)
        if A != A or A <= 0 or j < z.born_idx:
            return
        b = self.bars
        lo, hi = z.band_at(j)
        h, l, c = b["h"][j], b["l"][j], b["c"][j]
        brk = self.cfg["break_atr"] * A
        # --- response to a previous touch -----------------------------------
        if st["pending_from"] is not None and j >= st["pending_from"]:
            if st["broken"] is not None:
                st["pending_from"] = st["pending_until"] = None
            elif j <= st["pending_until"]:
                if st["approach_side"] == -1 and c <= lo - self.cfg["resp_move_atr"] * A:
                    st["n_respected"] += 1
                    st["pending_from"] = st["pending_until"] = None
                elif st["approach_side"] == +1 and c >= hi + self.cfg["resp_move_atr"] * A:
                    st["n_respected"] += 1
                    st["pending_from"] = st["pending_until"] = None
            else:
                st["pending_from"] = st["pending_until"] = None
        # --- break / reclaim / flip -----------------------------------------
        # A BREAK is a close through the zone to the far side of its role:
        # a ceiling (price came from below) breaks on a close > hi + brk; a
        # floor (price came from above) breaks on a close < lo - brk.  A close
        # back on the approach side is a TEST (the zone held), never a break,
        # so a 1.0 x A response can be counted.  A zone with no touch yet has
        # no role and cannot break (declared v0).
        if st["broken"] is None:
            side = st["approach_side"]
            broke = False
            if side == -1:
                broke = c > hi + brk
            elif side == +1:
                broke = c < lo - brk
            if j > z.born_idx and broke:
                st["broken"] = j
                st["broken_side"] = side
                st["pending_from"] = st["pending_until"] = None
                st["flip_deadline"] = j + self.cfg["reclaim_bars"]
                if not self._replaying:
                    z.end_idx = min(z.end_idx, j + self.cfg["break_keep_bars"])
                    self._push_retire(z.zid, z.end_idx)
                    self._cnt("zone_break")
        else:
            if (lo - brk) <= c <= (hi + brk) and j <= st["flip_deadline"]:
                st["broken"] = None
                st["n_reclaims"] += 1
                if not self._replaying:
                    self._cnt("zone_reclaim")
            elif j > st["flip_deadline"] and st["role_flip"] == 0:
                side = st["broken_side"] or +1
                if (side < 0 and c > hi + brk) or (side > 0 and c < lo - brk):
                    st["role_flip"] = 1
                    st["broken"] = None
                    st["approach_side"] = -side     # role flips: ceiling <-> floor
                    if not self._replaying:
                        self._cnt("zone_flip")
        # --- touch episodes --------------------------------------------------
        touched = (l <= hi) and (h >= lo)
        if touched:
            if st["last_touch"] is None or (j - st["last_touch"]) >= self.cfg["min_touch_sep"]:
                st["touches"] += 1
                st["last_touch"] = j
                prev_c = c if j == 0 else b["c"][j - 1]
                if prev_c < lo:
                    st["approach_side"] = -1
                elif prev_c > hi:
                    st["approach_side"] = +1
                elif st["approach_side"] is None:
                    st["approach_side"] = 1
                st["pending_from"] = j + 1
                st["pending_until"] = j + self.cfg["resp_window"]
                if not self._replaying:
                    self._warm[z.zid] = j + self.cfg["resp_window"] + 1
                    self._cnt("zone_touch")

    # ------------------------------------------------------------- queries
    def state_at(self, z, t):
        """Replay the zone's life up to bar t with a fresh state (causal,
        side-effect free)."""
        st = _fresh_state()
        was = self._replaying
        self._replaying = True
        try:
            for j in range(z.born_idx, t + 1):
                self._step_zone(z, j, st)
        finally:
            self._replaying = was
        return st

    def _strength(self, z, t, st):
        A = self.ctx.a(t)
        if A != A or A <= 0:
            return None
        s_touch = min(1.0, st["touches"] / self.cfg["touch_full"])
        s_resp = min(1.0, st["n_respected"] / self.cfg["resp_full"])
        if st["last_touch"] is None:
            s_rec = 0.0
        else:
            s_rec = math.exp(-(t - st["last_touch"]) / self.cfg["rec_half_life"])
        s_age = min(1.0, max(0, t - z.born_idx) / self.cfg["age_full"])
        s_scale = {"micro": self.cfg["scale_micro"], "meso": self.cfg["scale_meso"],
                   "macro": self.cfg["scale_macro"]}.get(z.scale, self.cfg["scale_micro"])
        s_role = 1.0 if st["role_flip"] else 0.0
        lo, hi = z.band_at(t)
        s_ref = self.ctx.refs.confluence(lo, hi, t)
        s_qual = min(1.0, z.quality_at(t) / self.QUAL_REF) if self.QUAL_REF > 0 else 0.0
        S = (self.cfg["w_touch"] * s_touch + self.cfg["w_resp"] * s_resp
             + self.cfg["w_rec"] * s_rec + self.cfg["w_age"] * s_age
             + self.cfg["w_scale"] * s_scale + self.cfg["w_role"] * s_role
             + self.cfg["w_ref"] * s_ref + self.cfg["w_qual"] * s_qual)
        parts = {"touch": s_touch, "resp": s_resp, "rec": s_rec, "age": s_age,
                 "scale": s_scale, "role": s_role, "ref": s_ref, "qual": s_qual}
        return float(S), parts

    def views_at(self, t, arm=True):
        """All live zones at bar t as ZoneView objects (armed by default)."""
        out = []
        A = self.ctx.a(t)
        if A != A or A <= 0:
            return out
        for z in self._zones:
            if t < z.created_idx or t < z.born_idx or t > z.end_idx:
                continue
            st = self.state_at(z, t)
            got = self._strength(z, t, st)
            if got is None:
                continue
            S, parts = got
            lo, hi = z.band_at(t)
            fresh = (st["broken"] is None
                     and (st["last_touch"] is None
                          or (t - st["last_touch"]) > self.cfg["fresh_bars"]))
            out.append(ZoneView(
                zid=z.zid, kind=z.kind, scale=z.scale, lo=lo, hi=hi,
                strength=S, born_idx=z.born_idx, touches=st["touches"],
                fresh=fresh, n_respected=st["n_respected"],
                broken_idx=st["broken"], role_flip=st["role_flip"],
                age=t - z.born_idx, last_touch=st["last_touch"],
                quality=z.quality_at(t), parts=parts, meta=dict(z.meta),
            ))
        out.sort(key=lambda v: (-v.strength, v.zid))
        close = float(self.bars["c"][t])
        return arm_zones(out, close, A, self.cfg) if arm else out

    def zones_at(self, t):
        """Common interface: list of {lo, hi, kind, strength, born_idx,
        touches, fresh} for the zones armed at the close of bar t."""
        return [zone_dict(v) for v in self.views_at(int(t), arm=True)]

    def live_dicts(self, t):
        """Full live-zone book at bar t as plain dicts (diagnostics/prefix
        tests; includes broken and far-from-price zones)."""
        return [v.as_dict() for v in self.views_at(int(t), arm=False)]

    def counts_at(self, t):
        """Diagnostics: (live, armed) zone counts at bar t."""
        live = self.views_at(int(t), arm=False)
        close = float(self.bars["c"][int(t)])
        armed = arm_zones(live, close, self.ctx.a(int(t)), self.cfg)
        return len(live), len(armed)

    # ------------------------------------------------------------- the pass
    def run(self, max_bars=None):
        n = self.n if max_bars is None else min(self.n, int(max_bars))
        for t in range(n):
            self._t_now = t
            self._on_bar(t)
            self._step_all(t)
        self._reindex()
        return self


def arm_zones(views, close, A, cfg):
    """Chart hygiene (addendum 1 item 3): zones near price only, deduped by
    center, capped, strongest first.  Views must be pre-sorted by strength.

    Armed = `broken_idx is None` (intact, or role-flipped and holding in the
    new role); a currently-BROKEN zone stays in the live book for diagnostics
    but is not armed (charter addendum 1 + PHYSICS_PREREG §3 primary
    population)."""
    if A != A or A <= 0:
        return []
    near = cfg["arm_near_atr"] * A
    dedupe = cfg["arm_dedupe_atr"] * A
    out = []
    for v in views:
        if v.broken_idx is not None:
            continue
        c = 0.5 * (v.lo + v.hi)
        if abs(c - close) > near:
            continue
        if any(abs(c - 0.5 * (o.lo + o.hi)) < dedupe for o in out):
            continue
        out.append(v)
        if len(out) >= cfg["arm_max"]:
            break
    return out
