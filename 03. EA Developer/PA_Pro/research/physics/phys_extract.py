"""phys_extract — fresh-approach event extraction (OUTCOME-BLIND).

Implements `rounds/R01/PHYSICS_PREREG_DRAFT.md` section 3 exactly:

    Event at bar t on zone Z iff all hold:
    1. bar t's range intersects the zone band at t (band = `band_at(t)`);
    2. freshness: no bar j in [t-24, t-1] has range intersecting the band at j,
       and some j in that window has close distance d(j, Z_j) >= 1.0 x A(t)
       where `A(t)` = ATR14(H1) at the close of bar t;
    3. approach side: c[t-1] <= lo(t) (side -1) or c[t-1] >= hi(t) (side +1);
    4. the zone is usable: created_idx <= t-24, t <= end_idx, state intact
       (`broken_idx is None` at t), strength available, A(t) valid, and bar t
       is not a warm-up bar.

No price after bar t is read anywhere in this module.  The `overlap`
diagnostic counts same-zone events inside the 48-bar outcome window of the
previous event (an event-table property, not a filter).
"""

import bisect as _bisect
import csv
import os

import numpy as np

import phys_common as pc

__all__ = ["extract_events", "write_events_csv", "EVENT_FIELDS"]

EVENT_FIELDS = [
    "symbol", "generator", "zid", "kind", "scale", "bar_idx", "bar_t",
    "utc_min", "year", "session", "side", "lo", "hi", "w", "near", "far",
    "m", "strength", "touches", "n_respected", "role_flip", "age_bars",
    "close_prev", "close_t", "overlap",
]


def extract_events(src, split="DESIGN", population="armed"):
    """Return (events, counters) for one source (generator) on one symbol.

    `population="armed"` (primary, per Lead ruling + SHORTLIST section 4) keeps
    only fresh approaches to zones that are ARMED at the event bar, using the
    harness's exact replica of the generator's own arming; "all" keeps every
    intact live zone (pre-declared sensitivity view).
    """
    bars = src.bars
    n = int(src.n)
    h = np.asarray(bars["h"], dtype=np.float64)
    l = np.asarray(bars["l"], dtype=np.float64)
    c = np.asarray(bars["c"], dtype=np.float64)
    t_arr = np.asarray(bars["t"], dtype=np.int64)
    warm = np.asarray(bars.get("warmup", np.zeros(n, dtype=bool)), dtype=bool)
    A = np.asarray(src.A, dtype=np.float64)
    A_valid = np.asarray(src.A_valid, dtype=bool)
    utc_min = bars.get("utc_min")

    import pa_clock

    years = pa_clock.server_year(t_arr + 300) if n else np.zeros(0, dtype=np.int64)

    counters = {
        "zones_total": 0, "zones_short": 0, "events": 0,
        "events_all_live": 0, "events_armed": 0, "skip_not_armed": 0,
        "skip_window": 0, "skip_no_away": 0, "skip_side": 0, "skip_broken": 0,
        "skip_atr": 0, "skip_strength": 0, "skip_warm": 0,
        "overlap_events": 0, "zones_with_events": 0,
    }
    events = []
    symbol = bars.get("symbol")
    for rec in src.zones():
        zid, kind, scale, born, created, end, handle = rec
        counters["zones_total"] += 1
        j1 = int(min(end, n - 1))
        if j1 < int(created) + pc.FRESH_BARS + 1:
            counters["zones_short"] += 1
            continue
        idx = np.arange(int(created), j1 + 1, dtype=np.int64)
        lo, hi = src.band_range(handle, idx)
        ins = (l[idx] <= hi) & (h[idx] >= lo)
        prev = np.concatenate(([False], ins[:-1]))
        first = ins & ~prev & A_valid[idx] & ~warm[idx]
        if not first.any():
            continue
        last_ev_bar = -10 ** 9
        z_events = 0
        for k in np.flatnonzero(first):
            t = int(idx[k])
            if t - int(created) < pc.FRESH_BARS:
                counters["skip_window"] += 1
                continue
            w0 = k - pc.FRESH_BARS
            if ins[w0:k].any():
                counters["skip_window"] += 1
                continue
            if not A_valid[t]:
                counters["skip_atr"] += 1
                continue
            Aev = A[t]
            d = np.maximum(lo[w0:k] - c[idx[w0:k]], c[idx[w0:k]] - hi[w0:k])
            if not (d >= pc.AWAY_ATR * Aev).any():
                counters["skip_no_away"] += 1
                continue
            cp = c[t - 1]
            if cp <= lo[k]:
                side = -1
            elif cp >= hi[k]:
                side = +1
            else:
                counters["skip_side"] += 1
                continue
            st = src.state_at(handle, t)
            if st.get("broken") is not None:
                counters["skip_broken"] += 1
                continue
            got = src.strength_at(handle, t)
            if got is None:
                counters["skip_strength"] += 1
                continue
            S, _parts = got
            near = float(lo[k]) if side == -1 else float(hi[k])
            far = float(hi[k]) if side == -1 else float(lo[k])
            overlap = 1 if (t - last_ev_bar) <= pc.HORIZON else 0
            if last_ev_bar > -10 ** 8 and t - last_ev_bar <= pc.HORIZON:
                counters["overlap_events"] += 1
            last_ev_bar = t
            z_events += 1
            events.append({
                "symbol": symbol,
                "generator": src.name,
                "zid": int(zid),
                "kind": str(kind),
                "scale": str(scale),
                "bar_idx": t,
                "bar_t": int(t_arr[t]),
                "utc_min": int(utc_min[t]) if utc_min is not None else -1,
                "year": int(years[t]),
                "session": pc.session_of(int(utc_min[t])) if utc_min is not None else "off",
                "side": int(side),
                "lo": float(lo[k]), "hi": float(hi[k]),
                "w": float(hi[k] - lo[k]),
                "near": near, "far": far, "m": float(Aev),
                "strength": float(S),
                "touches": int(st.get("touches", 0)),
                "n_respected": int(st.get("n_respected", 0)),
                "role_flip": int(st.get("role_flip", 0)),
                "age_bars": t - int(born),
                "close_prev": float(cp),
                "close_t": float(c[t]),
                "overlap": int(overlap),
            })
        if z_events:
            counters["zones_with_events"] += 1
        counters["events"] += z_events
    events.sort(key=lambda e: (e["bar_idx"], e["zid"]))
    counters["events_all_live"] = len(events)
    if population == "armed":
        kept = []
        cur = None
        armed = set()
        for e in events:
            if e["bar_idx"] != cur:
                cur = e["bar_idx"]
                armed = src.armed_ids_from(src.active_at_fast(cur), cur)
            if e["zid"] in armed:
                kept.append(e)
            else:
                counters["skip_not_armed"] += 1
        events = kept
    counters["events_armed"] = len(events)
    counters["events"] = len(events)
    return events, counters


def write_events_csv(events, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=EVENT_FIELDS)
        wr.writeheader()
        for e in events:
            wr.writerow({k: e.get(k) for k in EVENT_FIELDS})
    return path


def read_events_csv(path):
    with open(path, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def tercile_bounds(strengths):
    """q33/q67 of a strength array (for the frozen strength strata)."""
    s = np.asarray(strengths, dtype=np.float64)
    if s.size == 0:
        return float("nan"), float("nan")
    return float(np.percentile(s, 100.0 / 3.0)), float(np.percentile(s, 200.0 / 3.0))


def tercile_of(s, q33, q67):
    if not np.isfinite(s):
        return "nan"
    if s <= q33:
        return "bot"
    if s <= q67:
        return "mid"
    return "top"
