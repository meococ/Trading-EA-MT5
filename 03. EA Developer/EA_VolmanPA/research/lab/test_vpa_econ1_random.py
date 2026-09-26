"""T-VPA-ECON-1 tests: matched-random cell match, K rows, direction mix,
determinism, in-session only, CSV round-trip. Synthetic bars, no parquet.
Run: python research/lab/test_vpa_econ1_random.py
"""

import csv
import os
import sys
import tempfile
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from vpa_econ1_random import match_random, write_matched_csv  # noqa: E402

SEED = 20260920
K = 20
N_SIGNALS = 300

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'}  {name} {detail}")


def synth_bars(n=50000):
    """50k bars, utc_min cycling through a few in/out-of-session cells, with
    weekday and month varying with t (2019-01-01 00:00 UTC start)."""
    t0 = 1546300800
    t = t0 + np.arange(n, dtype=np.int64) * 300
    dow = ((t // 86400) + 3) % 7        # epoch day 0 = Thursday -> Monday=0
    cycle = np.array([320, 480, 700, 900, 660, 120, 1050, 300], dtype=np.int64)
    utc_min = cycle[np.arange(n) % len(cycle)]
    return {"t": t, "utc_min": utc_min, "dow": dow, "pip": 1e-4, "symbol": "SYNTH"}


def synth_signals(bars, n=N_SIGNALS):
    in_sess = np.flatnonzero(
        ((bars["utc_min"] >= 300) & (bars["utc_min"] < 660))
        | ((bars["utc_min"] >= 690) & (bars["utc_min"] < 1050))
    )
    idx = in_sess[500::100][:n]
    side = np.where(np.arange(len(idx)) % 20 < 11, 1, -1)   # 55% long
    return [{"bar_idx": int(i), "side": int(s)} for i, s in zip(idx, side)]


def cell_of(bars, i):
    """Independent recomputation of the (session, hour, dow, month) cell."""
    m = int(bars["utc_min"][i])
    if 300 <= m < 660:
        sess = "eu"
    elif 690 <= m < 1050:
        sess = "us"
    else:
        sess = None
    return (sess, m // 60, int(bars["dow"][i]), time.gmtime(int(bars["t"][i])).tm_mon)


def test_match_cell_exact(bars, signals, picks):
    rows = np.unique(np.linspace(0, len(picks) - 1, 200).astype(np.int64))
    bad = []
    for r in rows:
        src = signals[int(r) // K]
        c_rand = cell_of(bars, int(picks[r, 0]))
        c_src = cell_of(bars, int(src["bar_idx"]))
        if c_rand != c_src:
            bad.append((int(r), c_src, c_rand))
    check("match_cell_exact", len(bad) == 0,
          f"rows={len(rows)} mismatches={len(bad)} first={bad[:1]}")


def test_match_k(signals, picks):
    ok = (picks.ndim == 2 and picks.shape[1] == 2
          and np.issubdtype(picks.dtype, np.integer)
          and len(picks) == len(signals) * K)
    check("match_k", ok, f"picks={picks.shape} signals={len(signals)} K={K}")


def test_direction_mix(signals, picks):
    share_in = float(np.mean([1.0 if s["side"] > 0 else 0.0 for s in signals]))
    share_out = float((picks[:, 1] > 0).mean())
    check("direction_mix", len(picks) >= 5000 and abs(share_out - share_in) <= 0.02,
          f"in={share_in:.4f} out={share_out:.4f} n={len(picks)}")


def test_determinism(signals, bars):
    a = match_random(signals, bars, K=K, seed=SEED)
    b = match_random(signals, bars, K=K, seed=SEED)
    c = match_random(signals, bars, K=K, seed=SEED + 1)
    same = bool(np.array_equal(a, b))
    diff = bool(not np.array_equal(a, c))
    check("determinism", same and diff, f"same_seed_identical={same} other_seed_differs={diff}")


def test_insession_only(bars, picks):
    bad = 0
    for i in picks[:, 0]:
        m = int(bars["utc_min"][int(i)])
        if not (300 <= m < 660 or 690 <= m < 1050):
            bad += 1
    check("insession_only", bad == 0, f"n={len(picks)} out_of_session={bad}")


def test_csv_roundtrip(signals, picks):
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "matched.csv")
        out = write_matched_csv(path, picks, signals, K)
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        cols = list(rows[0].keys()) if rows else []
        per_sig = {}
        for r in rows:
            src = int(r["src_signal_bar_idx"])
            per_sig[src] = per_sig.get(src, 0) + 1
        expected = {int(s["bar_idx"]) for s in signals}
        ok = (out == path and len(rows) == len(signals) * K
              and cols == ["entry_bar_idx", "side", "src_signal_bar_idx"]
              and set(per_sig) == expected and all(v == K for v in per_sig.values()))
        check("csv_roundtrip", ok, f"rows={len(rows)} cols={cols} srcs={len(per_sig)}")


def main():
    bars = synth_bars()
    signals = synth_signals(bars)
    picks = match_random(signals, bars, K=K, seed=SEED)
    test_match_cell_exact(bars, signals, picks)
    test_match_k(signals, picks)
    test_direction_mix(signals, picks)
    test_determinism(signals, bars)
    test_insession_only(bars, picks)
    test_csv_roundtrip(signals, picks)
    passed = sum(1 for _, ok in RESULTS if ok)
    print(f"TESTS {'PASS' if passed == len(RESULTS) else 'FAIL'} {passed}/{len(RESULTS)}")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
