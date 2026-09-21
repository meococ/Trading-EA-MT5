"""phys_source — adapter from ZONE-1 zone generators to the physics harness.

The ZONE-1 contract (`struct/zones/common.py`) exposes `run()` + `zones_at(t)`;
the physics bake-off additionally needs (a) the FULL live set per bar, not the
armed subset (arming clips to +-2 ATR14(H1) around price, which would bias
event extraction), (b) the causal state at an arbitrary past bar, and
(c) the strength score at that bar.  This adapter reads those from the
generator's own objects and code paths:

- it wraps the instance's `_step_zone` (assigning an instance attribute; the
  ZONE-1 files are never edited) and records a compact state timeline per zone
  only when the state actually changes, skipping replay calls
  (`gen._replaying`), so the recorded state is exactly the state the forward
  pass built;
- band geometry comes from `Zone.band_at`, which is index-causal by design;
- the strength score is computed by the generator's own `_strength` with the
  recorded state.

`research/physics/` never writes under `struct/zones/` or `research/zones/`.

Generic protocol consumed by `phys_extract`:
    n, bars, A, A_valid, atr_of(t)
    zones() -> [(zid, kind, scale, born, created, end, handle), ...]
    band_range(handle, idx) -> (lo[], hi[])
    state_at(handle, t) -> dict
    strength_at(handle, t) -> (S, parts) | None
    info() -> human-readable generator descriptor (name, module, params)
"""

import bisect
import os
import sys

import numpy as np

import phys_common as pc

__all__ = ["GenSource", "fresh_state"]

_fresh_state = None


class _View:
    """Minimal view for `common.arm_zones` (same fields the real one exposes)."""

    __slots__ = ("zid", "lo", "hi", "strength", "state", "parts", "broken_idx")

    def __init__(self, z, lo, hi, strength, state, parts):
        self.zid = z.zid
        self.lo = lo
        self.hi = hi
        self.strength = strength
        self.state = state
        self.parts = parts
        self.broken_idx = state.get("broken")


def fresh_state():
    global _fresh_state
    if _fresh_state is None:
        from common import _fresh_state as fs

        _fresh_state = fs
    return _fresh_state()


class GenSource:
    """ZONE-1 `ZoneGen` instance -> physics source (read-only adapter)."""

    def __init__(self, name, cls, ctx, params=None):
        self.name = str(name)
        self.cls = cls
        self.ctx = ctx
        self.gen = cls(ctx, params) if params else cls(ctx)
        self.bars = ctx.bars
        self.n = int(ctx.n)
        atr = ctx.atr_h1.atr
        hi_idx = np.asarray(ctx.h1_idx, dtype=np.int64)
        ok = (hi_idx >= 0) & (hi_idx < len(atr))
        idx = np.clip(hi_idx, 0, max(0, len(atr) - 1))
        self.A = np.asarray(atr[idx], dtype=np.float64).copy()
        self.A[~ok] = np.nan
        self.A_valid = ok & np.isfinite(self.A) & (self.A > 0)
        self._tl = {}
        self._mystates = {}
        self._geom = {}
        self._zrec = None
        self._armed_cache = {}
        self._install()

    # ------------------------------------------------------------------ hook
    def _install(self):
        """Keep a bound reference to the generator's own step function.

        The pass-built states are NOT used: `views_at` (the parity reference)
        derives every state from `state_at`, a replay from `born_idx`, and the
        forward pass can skip bars the replay processes (band widening vs the
        reindexed sort key, gap bars).  `build_timelines` therefore replays
        each zone once with the generator's own `_step_zone` and records the
        state changes; no ZONE-1 file is edited.
        """
        self._step = self.gen._step_zone

    def build_timelines(self, max_bars=None):
        gen = self.gen
        n = self.n if max_bars is None else min(self.n, int(max_bars))
        was = gen._replaying
        gen._replaying = True
        try:
            for z in gen._zones:
                end = min(int(z.end_idx), n - 1)
                j0 = int(z.born_idx)
                if end < j0:
                    continue
                st = fresh_state()
                idx = []
                hist = []
                for j in range(j0, end + 1):
                    before = dict(st)
                    self._step(z, j, st)
                    if st != before:
                        idx.append(j)
                        hist.append(dict(st))
                if idx:
                    self._tl[z.zid] = (idx, hist)
        finally:
            gen._replaying = was
        return self

    def run(self, max_bars=None):
        self.gen.run(max_bars=max_bars)
        self.build_timelines(max_bars=max_bars)
        return self

    # -------------------------------------------------------------- protocol
    def atr_of(self, t):
        return float(self.A[int(t)]) if 0 <= int(t) < self.n else float("nan")

    def zones(self):
        out = []
        for z in self.gen._zones:
            out.append((z.zid, z.kind, z.scale, int(z.born_idx),
                        int(z.created_idx), int(z.end_idx), z))
        return out

    def _geom_of(self, z):
        g = self._geom.get(z.zid)
        if g is None:
            g = (np.asarray(z.geom_idx, dtype=np.int64),
                 np.asarray([v[0] for v in z.geom_hist], dtype=np.float64),
                 np.asarray([v[1] for v in z.geom_hist], dtype=np.float64))
            self._geom[z.zid] = g
        return g

    def band_range(self, z, idx):
        gidx, glo, ghi = self._geom_of(z)
        idx = np.asarray(idx, dtype=np.int64)
        k = np.searchsorted(gidx, idx, side="right") - 1
        np.clip(k, 0, len(gidx) - 1, out=k)
        return glo[k], ghi[k]

    def state_at(self, z, t):
        rec = self._tl.get(z.zid)
        if not rec:
            return fresh_state()
        k = bisect.bisect_right(rec[0], int(t)) - 1
        if k < 0:
            return fresh_state()
        return rec[1][k]

    def strength_at(self, z, t):
        st = self.state_at(z, t)
        got = self.gen._strength(z, int(t), st)
        if got is None:
            return None
        return got

    # --------------------------------------------------------- armed-parity
    def active_at(self, t):
        """Zone objects live at bar t (`views_at` live predicate, no strength)."""
        out = []
        for z in self.gen._zones:
            if t < z.created_idx or t < z.born_idx or t > z.end_idx:
                continue
            out.append(z)
        return out

    def armed_ids_from(self, zones, t):
        """Exact replica of `views_at(t, arm=True)` over an explicit live set.

        `views_at` builds all live views, sorts by (-strength, zid), then calls
        `common.arm_zones` (near window, centre dedupe, cap).  This function
        applies the identical order and the same `arm_zones` code path to the
        given live zones.
        """
        return {v[0] for v in self.armed_views_from(zones, t)}

    def armed_ids(self, t):
        """Reference path (slow): full live scan + exact arming."""
        return self.armed_ids_from(self.active_at(t), t)

    # ------------------------------------------------- fast live-set lookup
    def _index_arrays(self):
        if self._zrec is None:
            recs = sorted(self.zones(), key=lambda r: r[4])
            self._zrec = recs
            self._z_created = np.asarray([r[4] for r in recs], dtype=np.int64)
            self._z_end = np.asarray([r[5] for r in recs], dtype=np.int64)
        return self._zrec

    def active_at_fast(self, t):
        recs = self._index_arrays()
        if not recs:
            return []
        k = int(np.searchsorted(self._z_created, int(t), side="right"))
        if k == 0:
            return []
        idx = np.flatnonzero(self._z_end[:k] >= int(t))
        return [recs[i][6] for i in idx]

    def armed_views_from(self, zones, t):
        """(zid, lo, hi, strength) of the armed zones, in arming order."""
        from common import arm_zones

        A = self.ctx.a(t)
        if A != A or A <= 0:
            return []
        views = []
        for z in zones:
            st = self.state_at(z, t)
            if st.get("broken") is not None:
                continue
            got = self.gen._strength(z, int(t), st)
            if got is None:
                continue
            S, parts = got
            lo, hi = z.band_at(int(t))
            views.append(_View(z, lo, hi, S, st, parts))
        views.sort(key=lambda v: (-v.strength, v.zid))
        close = float(self.bars["c"][int(t)])
        armed = arm_zones(views, close, A, self.gen.cfg)
        return [(v.zid, v.lo, v.hi, v.strength) for v in armed]

    def armed_views_cached(self, t):
        t = int(t)
        hit = self._armed_cache.get(t)
        if hit is None:
            hit = self.armed_views_from(self.active_at_fast(t), t)
            if len(self._armed_cache) >= 8192:
                self._armed_cache.clear()
            self._armed_cache[t] = hit
        return hit

    def armed_coverage(self, t):
        """Share of the +-2 x ATR14(H1) window around the close covered by
        armed bands (descriptive view (ii); union length / window length)."""
        A = self.ctx.a(int(t))
        if A != A or A <= 0:
            return float("nan")
        close = float(self.bars["c"][int(t)])
        half = self.gen.cfg["arm_near_atr"] * A
        lo_w, hi_w = close - half, close + half
        armed = self.armed_views_cached(t)
        if not armed:
            return 0.0
        spans = []
        for (_zid, lo, hi, _S) in armed:
            a, b = max(lo, lo_w), min(hi, hi_w)
            if b > a:
                spans.append((a, b))
        spans.sort()
        covered = 0.0
        cur_lo = cur_hi = None
        for a, b in spans:
            if cur_lo is None:
                cur_lo, cur_hi = a, b
            elif a <= cur_hi:
                cur_hi = max(cur_hi, b)
            else:
                covered += cur_hi - cur_lo
                cur_lo, cur_hi = a, b
        if cur_lo is not None:
            covered += cur_hi - cur_lo
        return covered / (2.0 * half)

    def info(self):
        mod = sys.modules.get(self.cls.__module__)
        path = getattr(mod, "__file__", "")
        return {
            "generator": self.name,
            "class": self.cls.__name__,
            "module": os.path.basename(path),
            "module_sha256": pc.sha256_file(path) if path and os.path.exists(path) else "",
            "params": dict(self.gen.cfg),
            "scale": self.gen.SCALE,
        }
