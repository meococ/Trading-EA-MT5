"""phys_controls — K=5 matched fake-zone controls (OUTCOME-BLIND).

Implements `PHYSICS_PREREG_DRAFT.md` section 5 (the reading flagged there is
adopted in the frozen prereg):

- per real event, K=5 slots, each slot drawn from
  `np.random.default_rng([SEED, symbol_ord, t])`;
- same side, same width, near edge >= 1.0 x A(t) away from `c[t-1]`
  (the same minimum distance the freshness rule uses);
- center price ~ Uniform over the recent 5-day range (bars t-1440..t-1)
  restricted to the allowed side and the distance rule;
- no real zone (union over all shortlisted generators, live or broken) and no
  reference level within 2 widths of the fake band, checked at the anchor bar
  `t` and at the fake event bar `t_k`;
- the fake event is the FIRST fresh approach to the static fake band within
  `[t, t+1440]`, using the same rules as `phys_extract` (side, freshness,
  away-bar, A(t_k) valid);
- up to 20 redraws per slot; fewer than 5 realized controls is logged.

Structure index: per bucket of 8 M5 bars, a price-bin bitset (bin = 0.5 pip,
bins rounded OUTWARD on both marking and query) unioned over every zone of
every generator.  The bucket union can only over-reject (conservative).  This
is declared in the frozen prereg.
"""

import numpy as np

import phys_common as pc

__all__ = ["StructureIndex", "RefIndex", "prepare_anchor", "draw_controls",
           "extract_controls", "CONTROL_FIELDS"]

CONTROL_FIELDS = [
    "symbol", "generator", "anchor_i", "anchor_bar_idx", "anchor_zid", "slot",
    "draw", "bar_idx", "bar_t", "side", "lo", "hi", "w", "near", "far", "m",
    "utc_min", "year", "session", "contam_zone", "contam_ref", "tk_dt",
]

# CHARTER ADDENDUM 2 (binding): the primary control is a geometry-matched
# arbitrary band with NO structure exclusion except the triggering zone Z
# itself.  `R5_CAP` stays True: the addendum mandates the 5-day-range sample.
R5_CAP = True


def bands_overlap(a_lo, a_hi, b_lo, b_hi):
    """True when two bands overlap (distance <= 0)."""
    return max(a_lo - b_hi, b_lo - a_hi) <= 0.0


def ref_inside(ref, flo, fhi, t, grid_pips=None):
    """True when a reference level lies inside [flo, fhi] at bar t."""
    book = getattr(ref, "refs", ref)
    for item in book.levels_at(int(t)):
        lvl = item[1] if isinstance(item, tuple) else item
        if flo <= lvl <= fhi:
            return True
    grid = getattr(ref, "grid", 0.0) or getattr(book, "grid", 0.0) or 0.0
    if grid > 0:
        k = np.floor(0.5 * (flo + fhi) / grid)
        for g in (float(k * grid), float((k + 1) * grid)):
            if flo <= g <= fhi:
                return True
    return False



class StructureIndex:
    """Union of every generator's zone bands, 8-bar buckets, 0.5-pip bins."""

    def __init__(self, sources, bars, bucket=8, bin_pips=0.5):
        self.bars = bars
        self.n = len(bars["t"])
        self.bucket = int(bucket)
        pip = float(bars["pip"])
        self.bin = float(bin_pips) * pip
        pad = 64.0 * self.bin
        self.price_lo = float(np.min(bars["l"]))
        self.price_hi = float(np.max(bars["h"]))
        self.p0 = np.floor((self.price_lo - pad) / self.bin) * self.bin
        p1 = np.ceil((self.price_hi + pad) / self.bin) * self.bin
        self.nbins = int((p1 - self.p0) / self.bin) + 1
        self.nwords = (self.nbins + 63) // 64
        nb = (self.n + self.bucket - 1) // self.bucket
        self.occ = np.zeros((nb, self.nwords), dtype=np.uint64)
        self.n_segments = 0
        for src in sources:
            for (zid, kind, scale, born, created, end, z) in src.zones():
                gidx, glo, ghi = src._geom_of(z)
                for s in range(len(gidx)):
                    t0 = int(gidx[s])
                    t1 = int(gidx[s + 1]) if s + 1 < len(gidx) else int(end)
                    t1 = min(t1 - 1, self.n - 1)
                    if t1 < t0:
                        continue
                    self._mark(t0, t1, float(glo[s]), float(ghi[s]))
                    self.n_segments += 1

    def _mark(self, t0, t1, lo, hi):
        b0 = t0 // self.bucket
        b1 = min(t1 // self.bucket, self.occ.shape[0] - 1)
        j0 = int(np.floor(lo / self.bin - self.p0 / self.bin))
        j1 = int(np.ceil(hi / self.bin - self.p0 / self.bin))
        j0 = max(0, j0)
        j1 = min(self.nbins - 1, j1)
        if j1 < j0 or b1 < b0:
            return
        w0, w1 = j0 >> 6, j1 >> 6
        if w0 == w1:
            mask = ((1 << (j1 - j0 + 1)) - 1) << (j0 & 63)
            self.occ[b0:b1 + 1, w0] |= np.uint64(mask)
        else:
            m0 = ((1 << (64 - (j0 & 63))) - 1) << (j0 & 63)
            m1 = (1 << ((j1 & 63) + 1)) - 1
            self.occ[b0:b1 + 1, w0] |= np.uint64(m0)
            self.occ[b0:b1 + 1, w1] |= np.uint64(m1)
            if w1 - w0 > 1:
                self.occ[b0:b1 + 1, w0 + 1:w1] = np.uint64(0xFFFFFFFFFFFFFFFF)

    def near(self, flo, fhi, t, w):
        """True when any real zone band is within 2w of [flo, fhi] at bar t."""
        b = int(t) // self.bucket
        if b < 0 or b >= self.occ.shape[0]:
            return False
        a = flo - 2.0 * w
        z = fhi + 2.0 * w
        j0 = max(0, int(np.floor((a - self.p0) / self.bin)))
        j1 = min(self.nbins - 1, int(np.ceil((z - self.p0) / self.bin)))
        if j1 < j0:
            return False
        w0, w1 = j0 >> 6, j1 >> 6
        row = self.occ[b]
        if w0 == w1:
            mask = np.uint64(((1 << (j1 - j0 + 1)) - 1) << (j0 & 63))
            return bool(row[w0] & mask)
        m0 = np.uint64(((1 << (64 - (j0 & 63))) - 1) << (j0 & 63))
        if row[w0] & m0:
            return True
        m1 = np.uint64((1 << ((j1 & 63) + 1)) - 1)
        if row[w1] & m1:
            return True
        if w1 - w0 > 1 and row[w0 + 1:w1].any():
            return True
        return False


class RefIndex:
    """Reference levels (PDH/PDL/PDC/Asia/week/round) for eligibility."""

    def __init__(self, refs, grid_pips=50.0, bars=None):
        self.refs = refs
        self.grid = float(grid_pips) * float(bars["pip"]) if bars is not None else 0.0

    def _levels(self, t):
        return [lvl for _n, lvl in self.refs.levels_at(int(t))]

    def near(self, flo, fhi, t, w):
        a = flo - 2.0 * w
        z = fhi + 2.0 * w
        for lvl in self._levels(t):
            if a <= lvl <= z:
                return True
        if self.grid > 0:
            for edge in (a, z, flo, fhi):
                k = np.floor(edge / self.grid)
                for g in (float(k * self.grid), float((k + 1) * self.grid)):
                    if a <= g <= z:
                        return True
        return False


def prepare_anchor(event, bars):
    """Anchor-bar data for control sampling (all read from bars <= t)."""
    t = int(event["bar_idx"])
    l = bars["l"]
    h = bars["h"]
    t0 = max(0, t - pc.CTRL_SEARCH)
    r5_lo = float(np.min(l[t0:t]))
    r5_hi = float(np.max(h[t0:t]))
    return {
        "t": t,
        "c_prev": float(event["close_prev"]),
        "A": float(event["m"]),
        "w": float(event["w"]),
        "side": int(event["side"]),
        "r5_lo": r5_lo,
        "r5_hi": r5_hi,
    }


def _scan_fake_event(bars, A, A_valid, t_start, flo, fhi, t_end):
    """First fresh approach to the static fake band in [t_start, t_end]."""
    l = bars["l"]
    h = bars["h"]
    c = bars["c"]
    t1 = min(int(t_end), len(bars["t"]) - 1)
    j0 = int(t_start)
    if j0 > t1:
        return None
    while j0 <= t1:
        sl = slice(j0, t1 + 1)
        ins = (l[sl] <= fhi) & (h[sl] >= flo)
        k = int(np.argmax(ins)) if ins.any() else -1
        if k < 0:
            return None
        j = j0 + k
        w0 = max(0, j - pc.FRESH_BARS)
        if j > 0:
            ins_w = (l[w0:j] <= fhi) & (h[w0:j] >= flo)
            if ins_w.any():
                j0 = j + 1
                continue
        if not A_valid[j]:
            j0 = j + 1
            continue
        Aev = A[j]
        if j > 0:
            d = np.maximum(flo - c[w0:j], c[w0:j] - fhi)
            if not (d >= pc.AWAY_ATR * Aev).any():
                j0 = j + 1
                continue
        cp = c[j - 1] if j > 0 else np.nan
        if cp <= flo:
            side = -1
        elif cp >= fhi:
            side = +1
        else:
            j0 = j + 1
            continue
        return j, side
    return None


def draw_controls(event, src, ref, bars, rng, anchor_i=None):
    """Draw up to K=5 matched arbitrary bands for one real event.

    CHARTER ADDENDUM 2: same anchor, side, width, near-edge distance; centre
    Uniform over the eligible same-side part of R5; the fake event is the first
    fresh approach under the identical event rules; the ONLY placement
    exclusion is overlap with the triggering zone Z itself.
    """
    t = int(event["bar_idx"])
    w = float(event["w"])
    side = int(event["side"])
    Aev = float(event["m"])
    c_prev = float(event["close_prev"])
    zlo, zhi = float(event["lo"]), float(event["hi"])
    A = src.A
    A_valid = src.A_valid
    t0 = max(0, t - pc.CTRL_SEARCH)
    r5_lo = float(np.min(bars["l"][t0:t]))
    r5_hi = float(np.max(bars["h"][t0:t]))
    half = 0.5 * w
    out = []
    counters = {"slots_empty": 0, "draws": 0, "reject_zone_self": 0,
                "reject_no_event": 0, "reject_empty_interval": 0}
    for slot in range(pc.K_CTRL):
        accepted = None
        for draw in range(pc.CTRL_REDRAWS):
            counters["draws"] += 1
            if side == -1:
                lo_p = max(r5_lo, c_prev + pc.AWAY_ATR * Aev + half)
                hi_p = r5_hi
            else:
                lo_p = r5_lo
                hi_p = min(r5_hi, c_prev - pc.AWAY_ATR * Aev - half)
            if hi_p <= lo_p:
                counters["reject_empty_interval"] += 1
                break
            center = float(rng.uniform(lo_p, hi_p))
            flo = center - half
            fhi = center + half
            if bands_overlap(flo, fhi, zlo, zhi):
                counters["reject_zone_self"] += 1
                continue
            got = _scan_fake_event(bars, A, A_valid, t, flo, fhi,
                                   t + pc.CTRL_SEARCH)
            if got is None:
                counters["reject_no_event"] += 1
                continue
            tk, side_k = got
            if side_k != side:
                counters["reject_no_event"] += 1
                continue
            armed = src.armed_views_cached(tk)
            contam_zone = any(bands_overlap(flo, fhi, blo, bhi)
                              for (_zid, blo, bhi, _S) in armed)
            accepted = {
                "symbol": event.get("symbol"),
                "generator": event["generator"],
                "anchor_i": int(anchor_i) if anchor_i is not None else -1,
                "anchor_bar_idx": t,
                "anchor_zid": int(event["zid"]),
                "slot": int(slot),
                "draw": int(draw),
                "bar_idx": int(tk),
                "bar_t": int(bars["t"][tk]),
                "side": int(side_k),
                "lo": float(flo), "hi": float(fhi), "w": float(w),
                "near": float(flo) if side_k == -1 else float(fhi),
                "far": float(fhi) if side_k == -1 else float(flo),
                "m": float(A[tk]),
                "contam_zone": bool(contam_zone),
                "contam_ref": bool(ref_inside(ref, flo, fhi, tk)),
                "tk_dt": int(tk - t),
            }
            break
        if accepted is None:
            counters["slots_empty"] += 1
        else:
            out.append(accepted)
    return out, counters


def extract_controls(events, src, ref, bars, symbol):
    """K=5 controls for every real event, deterministic per-event RNG."""
    out = []
    counters = {"events": 0, "controls": 0, "events_with_lt5": 0,
                "slots_empty": 0, "draws": 0, "reject_zone_self": 0,
                "reject_no_event": 0, "reject_empty_interval": 0,
                "contam_zone": 0, "contam_ref": 0, "paired_tk_delta_med": None}
    ordn = pc.SYMBOL_ORD.get(symbol, 0)
    deltas = []
    for i, e in enumerate(events):
        rng = np.random.default_rng([pc.SEED, ordn, int(e["bar_idx"])])
        got, cnt = draw_controls(e, src, ref, bars, rng, anchor_i=i)
        counters["events"] += 1
        counters["controls"] += len(got)
        counters["slots_empty"] += cnt["slots_empty"]
        counters["draws"] += cnt["draws"]
        counters["reject_zone_self"] += cnt["reject_zone_self"]
        counters["reject_no_event"] += cnt["reject_no_event"]
        counters["reject_empty_interval"] += cnt["reject_empty_interval"]
        if len(got) < pc.K_CTRL:
            counters["events_with_lt5"] += 1
        for g in got:
            deltas.append(g["tk_dt"])
            counters["contam_zone"] += int(g["contam_zone"])
            counters["contam_ref"] += int(g["contam_ref"])
        out.extend(got)
    if deltas:
        counters["paired_tk_delta_med"] = float(np.median(deltas))
    return out, counters
