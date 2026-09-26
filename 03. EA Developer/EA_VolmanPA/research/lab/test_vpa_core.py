"""Unit fixtures + prefix-invariance + benchmark for the VPA detector.

Run:  python test_vpa_core.py
Prints one line per test and a final TESTS PASS summary. Exit code 0 on PASS.
"""

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from fixture_series import build_series  # noqa: E402
from vpa_core import Detector, run_detector  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"{'PASS' if cond else 'FAIL'}  {name} {detail}")


def test_pressure_direction():
    bars = build_series()
    d = Detector(bars)
    for t in range(len(bars["t"])):
        d._update_bar(t)
    # bars 43-47 are the pressure leg; check a window ending at 47
    comp = d._pressure_components(47, +1)
    check("pressure_long_leg_positive", comp["ok"], f"comps={ {k: round(v,3) for k,v in comp.items() if k!='ok'} }")
    comp_short = d._pressure_components(47, -1)
    check("pressure_long_leg_not_short", not comp_short["ok"])
    check("pressure_duration_ge_2", d.pdur[47] >= 2, f"pdur={d.pdur[47]}")


def test_barrier_lock():
    bars = build_series()
    d = Detector(bars)
    seen = []
    orig = d._try_lock

    def spy(i, side):
        n0 = len(d.active)
        orig(i, side)
        if len(d.active) > n0:
            seen.append(d.active[-1])

    d._try_lock = spy
    for t in range(len(bars["t"])):
        d._update_bar(t)
        if t > 14:
            d._confirm_pivots(t)
            d._barrier_update(t)
    check("barrier_locked", len(seen) == 1, f"n={len(seen)}")
    if seen:
        b = seen[0]
        check("barrier_side_upper", b["side"] == 1)
        check("barrier_touch_count_ge_2", len(b["touches"]) >= 2, f"touches={b['touches']}")
        check("barrier_level_matches", abs(b["level"] - 1.1) < 1e-9, f"level={b['level']!r}")


def test_pattern_break_executable():
    bars = build_series()
    recs, cnt = run_detector(bars)
    ex = [r for r in recs if r.get("executable")]
    check("executable_candidate_present", len(ex) == 1, f"n={len(ex)}")
    if ex:
        r = ex[0]
        check("executable_is_long", r["side"] == 1)
        check("executable_bar_54", r["bar_idx"] == 54, f"bar={r['bar_idx']}")
        check("executable_session_london", r["session"] == "london")
        check("executable_buildup_n", r["n"] == 6, f"n={r['n']}")
        check("executable_room_inf", r["room_pips"] == float("inf"))
        check("executable_rho", abs(r["rho"] - 0.125) < 1e-9)
        check("executable_no_skip", r["skip_reason"] is None)
        check("counters_executable", cnt.get("executable_pattern_break") == 1)


def test_negative_no_buildup():
    bars = build_series()
    for i in range(48, 54):  # keep highs/lows, push only opens/closes 3 pips below the barrier
        bars["c"][i] -= 0.0003
        bars["o"][i] -= 0.0003
    recs, cnt = run_detector(bars)
    ex = [r for r in recs if r.get("executable")]
    check("negative_no_buildup_no_executable", len(ex) == 0, f"n={len(ex)}")
    reasons = [r.get("skip_reason") for r in recs]
    check("negative_no_buildup_reason", "skip_no_buildup" in reasons, f"reasons={reasons}")


def test_prefix_invariance_synthetic():
    bars = build_series()
    full_recs, _ = run_detector(bars)
    K = 55  # includes the trigger bar 54
    prefix = {
        "symbol": bars["symbol"], "t": bars["t"][:K], "o": bars["o"][:K], "h": bars["h"][:K],
        "l": bars["l"][:K], "c": bars["c"][:K], "utc_min": bars["utc_min"][:K],
        "srv_min": bars["srv_min"][:K], "dow": bars["dow"][:K], "pip": bars["pip"], "tick": bars["tick"],
    }
    pre_recs, _ = run_detector(prefix)
    a = [r for r in full_recs if r["bar_idx"] < K]
    b = [r for r in pre_recs if r["bar_idx"] < K]
    check("prefix_invariance_synthetic", len(a) >= 1 and json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str),
          f"full={len(a)} prefix={len(b)}")


def test_prefix_invariance_real(n_bars=4000):
    try:
        from vpa_data import load_m5_bars
        bars = load_m5_bars("EURUSD")
    except Exception as exc:  # data absent -> skip, do not fake PASS
        check("prefix_invariance_real", False, f"DATA_MISSING {exc}")
        return
    K = n_bars // 2
    full_recs, _ = run_detector(bars, max_bars=n_bars)
    prefix = {k: (v[:K] if isinstance(v, list) else v) for k, v in bars.items()}
    pre_recs, _ = run_detector(prefix)
    a = [r for r in full_recs if r["bar_idx"] < K]
    b = [r for r in pre_recs if r["bar_idx"] < K]
    check("prefix_invariance_real", json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str),
          f"n_bars={n_bars} full={len(a)} prefix={len(b)}")


def test_benchmark(max_seconds=60.0):
    try:
        from vpa_data import load_m5_bars
        bars = load_m5_bars("EURUSD")
    except Exception as exc:
        check("benchmark_design_eurusd", False, f"DATA_MISSING {exc}")
        return
    t0 = time.time()
    recs, cnt = run_detector(bars)
    dt = time.time() - t0
    check("benchmark_design_eurusd", dt < max_seconds, f"{dt:.1f}s bars={len(bars['t'])} records={len(recs)}")
    print("BENCHMARK_DETAIL", json.dumps({"seconds": round(dt, 2), "bars": len(bars["t"]), "records": len(recs), "counters": cnt}, sort_keys=True))


def main():
    test_pressure_direction()
    test_barrier_lock()
    test_pattern_break_executable()
    test_negative_no_buildup()
    test_prefix_invariance_synthetic()
    test_prefix_invariance_real()
    test_benchmark()
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"TESTS {'PASS' if passed == total else 'FAIL'} {passed}/{total}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
