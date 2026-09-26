"""T-VPA-ECON-1 (G3) -- matched-random entries for the economic baseline.

Random entries matched to DR3-accepted signals on (session, hour-of-day,
weekday, month) with the same direction mix. This module only SELECTS bars:
it is decoupled from the fill/exit engine, which consumes the returned
(bar_idx, side) rows on its own.

Matching rule (Lead decision G3):
  - cell(bar b) = (session, utc_min(b) // 60, dow(b), month(b));
  - session = "eu" for 05:00-11:00 UTC, "us" for 11:30-17:30 UTC, else None;
  - non-in-session signals are skipped, so they contribute no rows;
  - K bars sampled uniformly WITH replacement from the DESIGN bars of the
    signal's own cell (nothing else excluded; the signal bar itself is
    eligible);
  - side drawn per entry with P(long) = long share of the INPUT signals.

`bars` is the dict from `vpa_data.load_m5_bars` (DESIGN window 2016-2021).
The cell -> bar-index map is precomputed once per call, so sampling never
rescans the bar arrays. Determinism: same seed -> identical output.
"""

import csv
import os

import numpy as np

EU_LO, EU_HI = 300, 660
US_LO, US_HI = 690, 1050


def session_of(utc_min):
    """'eu' | 'us' | None for one minute-of-day value (in-session only)."""
    m = int(utc_min)
    if EU_LO <= m < EU_HI:
        return "eu"
    if US_LO <= m < US_HI:
        return "us"
    return None


def _session_codes(utc_min):
    codes = np.zeros(len(utc_min), dtype=np.int64)
    codes[(utc_min >= EU_LO) & (utc_min < EU_HI)] = 1
    codes[(utc_min >= US_LO) & (utc_min < US_HI)] = 2
    return codes


def _months(t):
    return (t.astype("datetime64[s]").astype("datetime64[M]").astype(np.int64) % 12) + 1


def _cell_keys(t, utc_min, dow):
    sess = _session_codes(utc_min)
    hour = utc_min // 60
    month = _months(t)
    # pack (sess, hour, dow, month-1): sess<=2, hour<=23, dow<=6, month<=11
    key = ((sess * 32 + hour) * 8 + dow) * 16 + (month - 1)
    return sess, key


def _map_from_keys(sess, key):
    ins = np.flatnonzero(sess > 0)
    if len(ins) == 0:
        return {}
    keys = key[ins]
    order = np.argsort(keys, kind="stable")
    sk = keys[order]
    uniq, start = np.unique(sk, return_index=True)
    end = np.append(start[1:], len(sk))
    return {int(k): ins[order[s:e]] for k, s, e in zip(uniq, start, end)}


def build_cell_map(bars):
    """cell key -> indices of every in-session DESIGN bar (exposed for reuse)."""
    t = np.asarray(bars["t"], dtype=np.int64)
    utc_min = np.asarray(bars["utc_min"], dtype=np.int64)
    dow = np.asarray(bars["dow"], dtype=np.int64)
    sess, key = _cell_keys(t, utc_min, dow)
    return _map_from_keys(sess, key)


def match_random(signals, bars, K=20, seed=20260920):
    """Draw K matched random entries per in-session signal bar.

    signals: iterable of dicts with ``bar_idx`` (int) and ``side`` (+1/-1)
    (DR3-accepted records). bars: dict from ``vpa_data.load_m5_bars``.

    Returns an int64 array (n_entries, 2) of (random_bar_idx, side), rows in
    signal-major order -- rows [k*K, (k+1)*K) come from signals[k]. Signals
    outside the EU/US windows are skipped, so n_entries == len(signals)*K
    only when every signal is in-session.
    """
    if K <= 0:
        raise ValueError("K must be positive")
    sig = list(signals)
    if len(sig) == 0:
        return np.empty((0, 2), dtype=np.int64)

    t = np.asarray(bars["t"], dtype=np.int64)
    utc_min = np.asarray(bars["utc_min"], dtype=np.int64)
    dow = np.asarray(bars["dow"], dtype=np.int64)
    if not (len(t) == len(utc_min) == len(dow)):
        raise ValueError("bars arrays must share one length")

    bar_idx = np.asarray([int(s["bar_idx"]) for s in sig], dtype=np.int64)
    side = np.asarray([int(s["side"]) for s in sig], dtype=np.int64)
    if bar_idx.min() < 0 or bar_idx.max() >= len(t):
        raise ValueError("signal bar_idx outside bars range")
    if not np.isin(side, (-1, 1)).all():
        raise ValueError("signal side must be +1 or -1")

    sess, key = _cell_keys(t, utc_min, dow)
    cell_map = _map_from_keys(sess, key)
    p_long = float((side > 0).mean())
    rng = np.random.default_rng(seed)

    rows = []
    for k in range(len(sig)):
        b = int(bar_idx[k])
        if sess[b] == 0:
            continue
        members = cell_map.get(int(key[b]))
        if members is None or len(members) == 0:
            continue
        drawn = rng.choice(members, size=K, replace=True)
        dirs = np.where(rng.random(K) < p_long, 1, -1)
        for j in range(K):
            rows.append((int(drawn[j]), int(dirs[j])))
    if len(rows) == 0:
        return np.empty((0, 2), dtype=np.int64)
    return np.asarray(rows, dtype=np.int64)


def write_matched_csv(path, picks, signals, K):
    """One CSV row per random entry: entry_bar_idx, side, src_signal_bar_idx.

    Row r belongs to signals[r // K] (signal-major ``picks``), so every signal
    must be covered; a partial ``picks`` (skipped signals) cannot be mapped and
    raises ValueError. Returns the path.
    """
    path = os.fspath(path)
    picks = np.asarray(picks, dtype=np.int64).reshape(-1, 2)
    sig = list(signals)
    if K <= 0 or len(picks) != len(sig) * K:
        raise ValueError(
            f"picks covers {len(picks)} rows for {len(sig)} signals x K={K}; "
            "write_matched_csv needs the full signal-major picks array")
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["entry_bar_idx", "side", "src_signal_bar_idx"])
        for r in range(len(picks)):
            w.writerow([int(picks[r, 0]), int(picks[r, 1]), int(sig[r // K]["bar_idx"])])
    return path
