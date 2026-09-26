"""DR1 tests: one positive + one negative fixture per gate, direction rule,
combi context, prefix invariance. Run: python test_vpa_dr1.py
"""

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from fixture_dr1 import build_dr1_series  # noqa: E402
from vpa_dr1 import Dr1Detector, run_dr1  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'}  {name} {detail}")


def ex_at(recs, t):
    return [r for r in recs if r.get("executable") and r["bar_idx"] == t]


def reason_at(recs, t):
    rs = [r for r in recs if r["bar_idx"] == t]
    return rs[-1].get("skip_reason") if rs else None


def run(bars, cfg=None):
    return run_dr1(bars, cfg=cfg)


# ---------------- positive base ----------------
def test_base_positive():
    bars = build_dr1_series()
    recs, cnt = run(bars)
    ex = ex_at(recs, 65)
    check("base_executable_present", len(ex) == 1, f"n={len(ex)}")
    if ex:
        r = ex[0]
        pip = bars["pip"]
        check("base_side_long", r["side"] == 1)
        check("base_setup_pb", r["setup"] == "pattern_break")
        check("base_entry_level", abs(r["entry_level"] - (bars["h"][65] + pip)) < 1e-12)
        inv = min(bars["l"][r["buildup_start"]:65]) - 0.10 * r["atr"]
        check("base_invalidation", abs(r["invalidation"] - inv) < 1e-12)
        check("base_room_ge_2R", r["room_r"] >= 2.0, f"room_r={r['room_r']}")
        check("base_no_skip", r["skip_reason"] is None)
        check("base_no_outcome_fields", not any(k in r for k in ("pnl", "win", "mfe", "mae", "exit")))


# ---------------- per-gate negatives ----------------
def test_gate_warmup():
    bars = build_dr1_series()
    recs, _ = run(bars, cfg={"warmup_bars": 70})
    check("neg_warmup", len(ex_at(recs, 65)) == 0 and reason_at(recs, 65) == "skip_warmup")


def test_gate_session():
    bars = build_dr1_series()
    bars["utc_min"] = [700] * len(bars["utc_min"])   # outside EU/US
    recs, _ = run(bars)
    check("neg_session", len(ex_at(recs, 65)) == 0 and reason_at(recs, 65) == "skip_session")


def test_gate_direction():
    # bearish signal bar that still closes AT the barrier
    bars = build_dr1_series(mut={"o": {65: 1.10203}, "c": {65: 1.10200},
                                 "h": {65: 1.10204}, "l": {65: 1.10198}})
    recs, _ = run(bars)
    check("neg_direction", len(ex_at(recs, 65)) == 0 and reason_at(recs, 65) == "skip_direction",
          f"reason={reason_at(recs, 65)}")


def test_gate_direction_doji_allowed():
    bars = build_dr1_series(mut={"c": {65: 1.10199}, "o": {65: 1.10199}})
    recs, _ = run(bars)
    check("pos_direction_doji_allowed", len(ex_at(recs, 65)) == 1)


def test_gate_trend():
    bars = build_dr1_series()
    recs, _ = run(bars, cfg={"theta_slope": 5.0})
    check("neg_trend_slope", len(ex_at(recs, 65)) == 0 and reason_at(recs, 65) == "skip_trend")
    recs2, _ = run(build_dr1_series(), cfg={"frac_side_min": 1.01})
    check("neg_trend_frac", len(ex_at(recs2, 65)) == 0 and reason_at(recs2, 65) == "skip_trend")


def test_gate_buildup():
    bars = build_dr1_series()
    for i in range(55, 65):          # highs far from the barrier -> no touch
        bars["h"][i] = 1.10260
    recs, _ = run(bars)
    check("neg_buildup", len(ex_at(recs, 65)) == 0 and reason_at(recs, 65) == "skip_no_buildup",
          f"reason={reason_at(recs, 65)}")


def test_gate_chop():
    # choppy dojis in the 4 pre-signal bars (full overlap, falling lows) and a
    # buildup that fails on the touch count -> chop must reject before no_buildup
    bars = build_dr1_series()
    for i in range(61, 65):
        bars["o"][i] = 1.10188
        bars["c"][i] = 1.10188
        bars["h"][i] = 1.10195
        bars["l"][i] = 1.10180 - (i - 61) * 0.000001
    recs, _ = run(bars, cfg={"min_touches": 50})
    check("neg_chop", len(ex_at(recs, 65)) == 0 and reason_at(recs, 65) == "skip_chop",
          f"reason={reason_at(recs, 65)}")


def test_gate_room():
    bars = build_dr1_series(mut={"h": {55: 1.10220}})   # pivot high 1 pip above the entry
    recs, _ = run(bars)
    check("neg_room", len(ex_at(recs, 65)) == 0 and reason_at(recs, 65) == "skip_room",
          f"reason={reason_at(recs, 65)}")


def test_gate_adverse():
    bars = build_dr1_series()
    recs, _ = run(bars, cfg={"adverse_pivot_r": 1.5})   # dip pivot low falls in the band
    check("neg_adverse", len(ex_at(recs, 65)) == 0 and reason_at(recs, 65) == "skip_adverse_magnet",
          f"reason={reason_at(recs, 65)}")


def test_gate_anti_chase():
    bars = build_dr1_series(mut={"h": {65: 1.10260}})   # signal range >> 1.5 ATR
    recs, _ = run(bars)
    check("neg_anti_chase", len(ex_at(recs, 65)) == 0 and reason_at(recs, 65) == "skip_anti_chase")


def test_gate_cost():
    bars = build_dr1_series()
    recs, _ = run(bars, cfg={"cost_pips": 10.0})
    check("neg_cost", len(ex_at(recs, 65)) == 0 and reason_at(recs, 65) == "skip_cost")


def test_missed_break():
    bars = build_dr1_series(mut={"c": {60: 1.10220}, "o": {60: 1.10200}})
    recs, cnt = run(bars)
    check("neg_missed_break", len(ex_at(recs, 65)) == 0 and cnt.get("skip_missed_break", 0) >= 1)


# ---------------- combi context ----------------
def test_combi_inside_pb():
    # strong bar at 64 closes BELOW the signal threshold; inside bar at 65 is the signal
    bars = build_dr1_series(mut={"o": {64: 1.10188}, "h": {64: 1.10200}, "l": {64: 1.10187},
                                 "c": {64: 1.10198}})
    recs, _ = run(bars)
    ex = ex_at(recs, 65)
    check("pos_combi_in_pb", len(ex) == 1 and ex[0]["setup"] == "combi",
          f"setup={ex[0]['setup'] if ex else None}")


def test_combi_never_standalone():
    # strong bar + inside bar in the quiet phase, no barrier context: no candidate
    bars = build_dr1_series(mut={"o": {20: 1.10070}, "h": {20: 1.10085}, "l": {20: 1.10068},
                                 "c": {20: 1.10084}, "o": {21: 1.10084}, "h": {21: 1.10085},
                                 "l": {21: 1.10075}, "c": {21: 1.10084}})
    recs, _ = run(bars)
    ex = [r for r in recs if r.get("executable") and r["bar_idx"] in (20, 21)]
    check("combi_never_standalone", len(ex) == 0)


# ---------------- per-gate positives (F1) ----------------
def test_gate_positives():
    """Each gate's passing condition is asserted on the base run."""
    bars = build_dr1_series()
    recs, _ = run(bars)
    ex = ex_at(recs, 65)
    check("pos_gate_all_reach_exec", len(ex) == 1)
    if not ex:
        return
    r = ex[0]
    # session
    check("pos_session_eu", r["session"] == "eu")
    # direction (bullish signal bar)
    check("pos_direction_bullish", bars["c"][65] > bars["o"][65])
    # trend
    check("pos_trend", r["trend_slope"] >= 0.10 and r["frac_side"] >= 0.6,
          f"slope={r['trend_slope']} frac={r['frac_side']}")
    # buildup sub-conditions
    check("pos_buildup_band", r["band_closes"] >= 2, f"band={r['band_closes']}")
    check("pos_buildup_touches", r["touches_in_buildup"] >= 1, f"touches={r['touches_in_buildup']}")
    check("pos_buildup_overlap", r["overlap"] >= 0.45, f"overlap={r['overlap']}")
    check("pos_buildup_contraction", r["contraction"] <= 0.85, f"contraction={r['contraction']}")
    # chop (base must not be chop, and the buildup exemption path is exercised elsewhere)
    check("pos_chop_absent", not Dr1Detector(bars)._chop_dr1(65))
    # room
    check("pos_room", r["room_r"] >= 2.0, f"room_r={r['room_r']}")
    # adverse
    check("pos_adverse_absent", r["adverse_magnet"] is False)
    # anti-chase components
    pip = bars["pip"]
    check("pos_anti_entry_b", (r["entry_level"] - r["level"]) <= pip + 0.35 * r["atr"])
    check("pos_anti_signal_range", (bars["h"][65] - bars["l"][65]) <= 1.5 * r["atr"])
    check("pos_anti_ema", abs(r["entry_level"] - r["ema"]) <= 1.5 * r["atr"])
    # cost
    check("pos_cost", r["rho"] <= 0.20, f"rho={r['rho']}")


def test_buildup_overlap_negative():
    # alternate deep lows -> adjacent bars stop overlapping -> no buildup
    bars = build_dr1_series()
    for i in range(55, 65):
        if i % 2 == 0:
            bars["l"][i] = 1.10100
            bars["h"][i] = 1.10110
        else:
            bars["l"][i] = 1.10210
            bars["h"][i] = 1.10220
    recs, _ = run(bars)
    check("neg_buildup_overlap", len(ex_at(recs, 65)) == 0
          and reason_at(recs, 65) in ("skip_no_buildup", "skip_chop"),
          f"reason={reason_at(recs, 65)}")


def test_buildup_contraction_negative():
    # wide buildup bars vs a tight prior window -> contraction > 0.85
    bars = build_dr1_series()
    for i in range(55, 65):
        bars["l"][i] = 1.10140
        bars["h"][i] = 1.10200
    d = Dr1Detector(bars)
    for t in range(66):
        d._update_bar(t)
    bu = d._buildup_dr1(65, 1, 1.10200, d.atr[65])
    check("neg_buildup_contraction", bu is None, f"bu={bu}")


# ---------------- causality ----------------
def test_prefix_invariance():
    bars = build_dr1_series()
    full, _ = run(bars)
    K = 70                       # includes the bar-65 record; full series has 76 bars
    prefix = {k: (v[:K] if isinstance(v, list) else v) for k, v in bars.items()}
    pre, _ = run(prefix)
    a = [r for r in full if r["bar_idx"] < K]
    b = [r for r in pre if r["bar_idx"] < K]
    check("prefix_invariance", len(a) >= 1 and len(a) == len(b) and
          json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str),
          f"full={len(a)} prefix={len(b)}")


def test_determinism():
    bars = build_dr1_series()
    r1, c1 = run(bars)
    r2, c2 = run(build_dr1_series())
    check("deterministic_replay",
          json.dumps(r1, sort_keys=True, default=str) == json.dumps(r2, sort_keys=True, default=str)
          and c1 == c2)


def test_benchmark_real(max_seconds=60.0):
    try:
        from vpa_data import load_m5_bars
        bars = load_m5_bars("EURUSD")
    except Exception as exc:
        check("benchmark_real_eurusd", False, f"DATA_MISSING {exc}")
        return
    # deterministic grid from the DESIGN median ATR (context/obstacle grid only)
    d0 = Dr1Detector(bars)
    for t in range(len(bars["t"])):
        d0._update_bar(t)
    import statistics
    med_atr = statistics.median([a for a in d0.atr[100:] if a == a])
    t0 = time.time()
    recs, cnt = run(bars, cfg={"round_grid_price": 50.0 * bars["pip"]})
    dt = time.time() - t0
    ex = sum(1 for r in recs if r.get("executable"))
    check("benchmark_real_eurusd", dt < max_seconds,
          f"{dt:.1f}s bars={len(bars['t'])} records={len(recs)} executable={ex} medATR={med_atr/bars['pip']:.2f}p")
    print("BENCHMARK_DETAIL", json.dumps({"seconds": round(dt, 2), "bars": len(bars["t"]),
                                          "records": len(recs), "executable": ex,
                                          "median_atr_pips": round(med_atr / bars["pip"], 3)}, sort_keys=True))


def test_gate_integrity():
    # positive: the base fixture's barrier holds (no close beyond B + eps)
    bars = build_dr1_series()
    recs, _ = run(bars, cfg={"collect_gates": True})
    r = [x for x in recs if x["bar_idx"] == 65]
    gi = r[-1]["gates"]["integrity"] if r else {}
    check("pos_integrity", bool(gi.get("pass")) and gi["value"]["first_touch"] is not None
          and len(ex_at(recs, 65)) == 1, f"value={gi.get('value')}")
    # negative: a close beyond B + 0.10*ATR (but below the 0.25*ATR missed-break
    # threshold) between the first touch and the signal bar
    bars = build_dr1_series(mut={"h": {55: 1.10205}, "c": {55: 1.102045}})
    recs, _ = run(bars)
    got = [r for r in recs if r["bar_idx"] == 65]
    check("neg_integrity", len(ex_at(recs, 65)) == 0 and any(r.get("skip_reason") == "skip_integrity" for r in got),
          f"reasons={[r.get('skip_reason') for r in got]}")


def test_room_zone_exclusion():
    # obstacle 1 pip above the entry: DR1 (no zone) rejects on room, DR3 ignores
    # it because it is inside the barrier zone (F3)
    bars = build_dr1_series(mut={"h": {55: 1.10220}})
    recs0, _ = run(bars)
    check("zone_off_room_fails", len(ex_at(recs0, 65)) == 0 and reason_at(recs0, 65) == "skip_room",
          f"reason={reason_at(recs0, 65)}")
    cfg = {"collect_gates": True, "room_zone_touch": True, "room_zone_r": 0.5,
           "room_significant_only": True}
    recs, _ = run(bars, cfg=cfg)
    r = [x for x in recs if x["bar_idx"] == 65]
    gv = (r[-1]["gates"]["room"]["value"] if r else None) or {}
    obs = gv.get("obstacle") or {}
    check("zone_on_room_passes", len(ex_at(recs, 65)) == 1 and gv.get("room_r") >= 2.0
          and obs.get("type") != "pivot_sig",
          f"room_r={gv.get('room_r')} obstacle={obs}")


def test_chop_window():
    # choppy impulse bars in the 4 pre-signal bars (legacy chop True) but the
    # buildup window [start,65) has prog > 1/3 -> windowed chop False (F3)
    bars = build_dr1_series()
    for i in range(61, 65):
        bars["o"][i] = 1.10188
        bars["c"][i] = 1.10188
        bars["h"][i] = 1.10195
        bars["l"][i] = 1.10180 - (i - 61) * 0.000001
    recs, _ = run(bars, cfg={"collect_gates": True, "chop_in_buildup": True})
    r = [x for x in recs if x["bar_idx"] == 65]
    cv = (r[-1]["gates"]["chop"]["value"] if r else None) or {}
    check("chop_window", cv.get("chop") is True and cv.get("chop_window") is False
          and cv.get("buildup_start") is not None,
          f"legacy={cv.get('chop')} window={cv.get('chop_window')} start={cv.get('buildup_start')}")


def test_buildup_variants_logged():
    bars = build_dr1_series()
    recs, _ = run(bars, cfg={"collect_gates": True, "buildup_variants": True})
    r = [x for x in recs if x["bar_idx"] == 65]
    bv = (r[-1]["gates"]["buildup"]["value"] if r else None) or {}
    check("buildup_variants_logged",
          bv.get("v2of4") is not None and bv.get("vtight") is not None
          and bv.get("conditions_passed") == 4,
          f"4c={bv.get('conditions_passed')} v2={bv.get('v2of4', {}).get('n') if bv.get('v2of4') else None}")


def test_dr3_cfg_hard_gates():
    """DR3 config: only the F2 hard gates decide; the feature gates do not.
    With signal_atr 0.50 the fixture fires at the lock bar (50), not 65."""
    from vpa_dr1 import DR3_CFG
    bars = build_dr1_series()
    recs, _ = run(bars, cfg=dict(DR3_CFG, collect_gates=True))
    ex = [r for r in recs if r.get("executable")]
    check("dr3_exec_present", len(ex) == 1 and ex[0]["bar_idx"] == 50
          and ex[0]["hard_gates"] == list(DR3_CFG["hard_gates"]),
          f"bars={[r['bar_idx'] for r in ex]} hard={ex[0].get('hard_gates') if ex else None}")


def test_trace_equals_detector():
    """The trace path must be the detector's own verdicts: for every candidate
    record, verdict_from_gates(gates) == (executable, skip_reason)."""
    from vpa_trace import run_trace
    from vpa_dr1 import verdict_from_gates
    try:
        from vpa_data import load_m5_bars
        bars = load_m5_bars("EURUSD")
    except Exception as exc:
        check("trace_equals_detector", False, f"DATA_MISSING {exc}")
        return
    d, recs, cnt = run_trace(bars, max_bars=60000)
    n_cand = 0
    bad = 0
    for r in recs:
        if not r.get("gates"):
            continue
        n_cand += 1
        if verdict_from_gates(r["gates"], r.get("hard_gates")) != (r.get("executable"), r.get("skip_reason")):
            bad += 1
    check("trace_equals_detector", n_cand >= 2000 and bad == 0,
          f"candidates={n_cand} mismatches={bad}")


def test_trace_module_shares_code():
    """vpa_trace.py must import the gate path, not re-implement gates."""
    import vpa_trace
    src = open(vpa_trace.__file__, encoding="utf-8").read()
    ok = ("from vpa_dr1 import" in src and "full_fail_set" in src
          and "def _dr1_gates" not in src and "def verdict_from_gates" not in src)
    check("trace_module_shares_code", ok)


def main():
    test_base_positive()
    test_gate_warmup()
    test_gate_session()
    test_gate_direction()
    test_gate_direction_doji_allowed()
    test_gate_trend()
    test_gate_buildup()
    test_gate_chop()
    test_gate_room()
    test_gate_adverse()
    test_gate_anti_chase()
    test_gate_cost()
    test_missed_break()
    test_combi_inside_pb()
    test_combi_never_standalone()
    test_gate_positives()
    test_buildup_overlap_negative()
    test_buildup_contraction_negative()
    test_prefix_invariance()
    test_determinism()
    test_gate_integrity()
    test_room_zone_exclusion()
    test_chop_window()
    test_buildup_variants_logged()
    test_dr3_cfg_hard_gates()
    test_trace_equals_detector()
    test_trace_module_shares_code()
    test_benchmark_real()
    passed = sum(1 for _, ok in RESULTS if ok)
    print(f"TESTS {'PASS' if passed == len(RESULTS) else 'FAIL'} {passed}/{len(RESULTS)}")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
