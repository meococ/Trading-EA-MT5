"""zones.py - causal S/R zones (Phase B spec).

Variant (a) WHQ zone: zone around each WHQ grid level, half-width
0.25*ATR14[t] (evaluated at the decision bar - the level is timeless, the
band is volatility-scaled).

Variant (b) swing zone: cluster of >=2 confirmed swing extremes within
0.3*ATR14 of each other ("defended origin", small zone, not a hard line).
  zone range = [min(px)-0.1*ATR, max(px)+0.1*ATR]
  zone dies after a close beyond it by > 0.5*ATR14
  avail_idx  = max(member conf): first decision bar that may see the zone
  origin_idx = min(member idx):  start of the death-check window
  (LEAD_NOTE_3: the two meanings of "birth" are kept separate; death is
  evaluated only over bars <= t, so the stricter origin-window is causal).

A zone (or level) is usable at decision bar t only if every constituent
swing was confirmed at a bar <= t and the zone has not died at a bar <= t.

build_zones() precomputes zones event-wise; zones_at(t) evaluates live
zones lazily - only called on candidate bars (keeps the hot loop cheap).
"""
from __future__ import annotations

import numpy as np

from . import whq as whq_mod


def whq_zone(price: float, symbol: str, atr: float,
             half_width_atr: float = 0.25) -> tuple | None:
    """If `price` is within half_width_atr*atr of a WHQ level, return
    (level, rank, lo, hi) else None."""
    if atr <= 0 or not np.isfinite(atr):
        return None
    pip = whq_mod.pip_size(symbol)
    q = 25.0 * pip
    k = int(round(price / q))
    lvl = k * q
    if abs(price - lvl) <= half_width_atr * atr:
        r = {0: 2, 2: 1, 1: 0, 3: 0}[k % 4]
        return (lvl, r, lvl - half_width_atr * atr, lvl + half_width_atr * atr)
    return None


def _sparse_min(v: np.ndarray):
    """Sparse table for O(1) range-min queries on v (NaN-safe: NaN->inf)."""
    v = np.where(np.isfinite(v), v, np.inf)
    n = len(v)
    lg = np.zeros(n + 1, np.int64)
    for i in range(2, n + 1):
        lg[i] = lg[i // 2] + 1
    kmax = int(lg[n]) + 1
    st = np.empty((kmax, n))
    st[0] = v
    j = 1
    while (1 << j) <= n:
        h = 1 << (j - 1)
        st[j, :n - 2 * h + 1] = np.minimum(st[j - 1, :n - 2 * h + 1],
                                           st[j - 1, h:n - h + 1])
        j += 1
    return st, lg


def _sparse_max(v: np.ndarray):
    """Sparse table for O(1) range-MAX queries (NaN -> -inf)."""
    st, lg = _sparse_min(-np.where(np.isfinite(v), v, -np.inf))
    return -st, lg


class SwingZones:
    """Event-driven swing-cluster zones. Feed confirmed swings in
    confirmation order via `confirm_bar` sweep; query live zones at t.

    Death check is O(1): precomputed sparse tables over
      dn[k] = close[k] + kill*ATR[k]   (support dies if rmin(b,t] < lo)
      up[k] = close[k] - kill*ATR[k]   (resist dies if rmax(b,t] > hi)
    """

    def __init__(self, sw: dict, h: np.ndarray, l: np.ndarray,
                 c: np.ndarray, atr: np.ndarray,
                 cluster_atr: float = 0.3, pad_atr: float = 0.1,
                 kill_atr: float = 0.5, max_age_bars: int = 2400):
        self.sw = sw; self.atr = atr
        self.cluster_atr = cluster_atr
        self.pad_atr = pad_atr
        self.kill_atr = kill_atr
        self.max_age = max_age_bars
        self._c = c
        dn = c + kill_atr * atr
        up = c - kill_atr * atr
        self._st_min, self._lg = _sparse_min(dn)
        self._st_max, _ = _sparse_max(up)
        # confirmed swings sorted by conf bar
        order = np.argsort(sw["conf"], kind="stable")
        self._by_conf = [(int(sw["conf"][i]), int(sw["idx"][i]),
                          float(sw["px"][i]), int(sw["dir"][i]))
                         for i in order]
        self._ptr = 0
        self._confirmed = []          # (idx, px, dir) usable swings
        self._built_t = -1
        self._live = []

    def _rmin(self, a: int, b: int) -> float:
        if a >= b:
            return np.inf
        j = int(self._lg[b - a])
        return float(min(self._st_min[j, a], self._st_min[j, b - (1 << j)]))

    def _rmax(self, a: int, b: int) -> float:
        if a >= b:
            return -np.inf
        j = int(self._lg[b - a])
        return float(max(self._st_max[j, a], self._st_max[j, b - (1 << j)]))

    def _advance(self, t: int):
        while (self._ptr < len(self._by_conf)
               and self._by_conf[self._ptr][0] <= t):
            cf, idx, px, d = self._by_conf[self._ptr]
            self._confirmed.append((idx, px, d, cf))
            self._ptr += 1

    def zones_at(self, t: int):
        """Live zones for decision bar t (all info <= t)."""
        self._advance(t)
        a = self.atr[t]
        if not np.isfinite(a) or a <= 0:
            return []
        # candidates: confirmed swings inside age window
        cands = [(i, p, d, cf) for (i, p, d, cf) in self._confirmed
                 if t - i <= self.max_age]
        # cluster greedily by price within cluster_atr*a
        cands.sort(key=lambda x: x[1])
        zones = []
        used = [False] * len(cands)
        for i, (bi, bp, bd, bcf) in enumerate(cands):
            if used[i]:
                continue
            members = [(bi, bp, bd, bcf)]
            used[i] = True
            for j in range(i + 1, len(cands)):
                if used[j]:
                    continue
                bj, bj_p, bj_d, bj_cf = cands[j]
                if abs(bj_p - bp) <= self.cluster_atr * a:
                    members.append((bj, bj_p, bj_d, bj_cf))
                    used[j] = True
            if len(members) < 2:
                continue
            pxs = [m[1] for m in members]
            lo = min(pxs) - self.pad_atr * a
            hi = max(pxs) + self.pad_atr * a
            # death check (O(1) sparse query): support dies if any close
            # in (birth, t] below lo - kill*ATR[k]; resistance on close
            # above hi + kill*ATR[k].
            zone_dir = 1 if sum(m[2] for m in members) > 0 else -1
            # strict rule: any close through the eventual zone range after
            # the earliest member defense invalidates it
            birth = min(m[0] for m in members)
            if zone_dir == -1:
                dead = self._rmin(birth + 1, t + 1) < lo
            else:
                dead = self._rmax(birth + 1, t + 1) > hi
            if not dead:
                zones.append({"lo": lo, "hi": hi,
                              "mid": (lo + hi) / 2, "dir": zone_dir,
                              "n": len(members),
                              "avail_idx": max(m[3] for m in members),
                              "origin_idx": birth,
                              "members": tuple(int(m[0])
                                               for m in members)})
        return zones


def price_in_zone(price: float, zones: list) -> bool:
    return any(z["lo"] <= price <= z["hi"] for z in zones)
