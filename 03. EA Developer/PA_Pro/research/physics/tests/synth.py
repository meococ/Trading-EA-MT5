"""SynthSource — synthetic zone source for unit tests (no real data)."""

import bisect
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PHYS = os.path.dirname(HERE)
if PHYS not in sys.path:
    sys.path.insert(0, PHYS)


class SynthSource:
    """Minimal source implementing the phys_extract/phys_controls protocol."""

    def __init__(self, bars, A, zones, name="synth", pip=0.0001):
        self.bars = bars
        self.name = name
        self.n = len(bars["t"])
        self.A = np.asarray(A, dtype=np.float64)
        self.A_valid = np.isfinite(self.A) & (self.A > 0)
        self.bars.setdefault("pip", pip)
        self.bars.setdefault("symbol", "SYNTH")
        self._zones = zones

    def zones(self):
        out = []
        for z in self._zones:
            out.append((z["zid"], z.get("kind", "swing"), z.get("scale", "micro"),
                        z["born"], z["created"], z["end"], z))
        return out

    def _geom_of(self, z):
        return (np.asarray(z["gidx"], dtype=np.int64),
                np.asarray(z["glo"], dtype=np.float64),
                np.asarray(z["ghi"], dtype=np.float64))

    def band_range(self, z, idx):
        idx = np.asarray(idx, dtype=np.int64)
        gidx = np.asarray(z["gidx"], dtype=np.int64)
        k = np.searchsorted(gidx, idx, side="right") - 1
        np.clip(k, 0, len(gidx) - 1, out=k)
        return (np.asarray(z["glo"], dtype=np.float64)[k],
                np.asarray(z["ghi"], dtype=np.float64)[k])

    def state_at(self, z, t):
        st = dict(z.get("state", {"broken": None, "touches": 1,
                                  "n_respected": 0, "role_flip": 0}))
        return st

    def strength_at(self, z, t):
        return float(z.get("strength", 0.5)), {}

    def active_at_fast(self, t):
        return [z for z in self._zones
                if z["created"] <= int(t) <= z["end"]]

    def armed_views_from(self, zones, t):
        A = float(self.A[int(t)]) if 0 <= int(t) < self.n else float("nan")
        if not (A == A and A > 0):
            return []
        close = float(self.bars["c"][int(t)])
        out = []
        for z in zones:
            lo, hi = self.band_range(z, [int(t)])
            lo, hi = float(lo[0]), float(hi[0])
            if abs(0.5 * (lo + hi) - close) > 2.0 * A:
                continue
            out.append((z["zid"], lo, hi, float(z.get("strength", 0.5))))
        out.sort(key=lambda v: (-v[3], v[0]))
        return out[:6]

    def armed_ids_from(self, zones, t):
        return {v[0] for v in self.armed_views_from(zones, t)}

    def armed_views_cached(self, t):
        return self.armed_views_from(self.active_at_fast(t), t)


def make_bars(closes, spread=0.0002, t0=1451606400, warmup=0, period=300):
    """OHLC bars from a close path; l/c/h padded by `spread`."""
    closes = np.asarray(closes, dtype=np.float64)
    n = len(closes)
    t = t0 + period * np.arange(n, dtype=np.int64)
    o = np.empty(n)
    o[0] = closes[0]
    o[1:] = closes[:-1]
    h = np.maximum(o, closes) + spread
    l = np.minimum(o, closes) - spread
    wu = np.zeros(n, dtype=bool)
    wu[: int(warmup)] = True
    utc_min = (t % 86400 // 60).astype(np.int64)
    return {"t": t, "o": o, "h": h, "l": l, "c": closes.copy(),
            "warmup": wu, "utc_min": utc_min, "pip": 0.0001, "symbol": "SYNTH"}


def flat_zone(zid, lo, hi, born=0, created=0, end=10 ** 9, **kw):
    z = {"zid": zid, "kind": kw.pop("kind", "swing"),
         "scale": kw.pop("scale", "micro"), "born": born, "created": created,
         "end": end, "gidx": np.array([created], dtype=np.int64),
         "glo": np.array([lo], dtype=np.float64),
         "ghi": np.array([hi], dtype=np.float64),
         "state": kw.pop("state", {"broken": None, "touches": 1,
                                   "n_respected": 0, "role_flip": 0})}
    z.update(kw)
    return z
