"""Fixtures + prefix-invariance tests for the pro line engine (T-VPA-LINE-1).

One fixture per line type:
  box, ascending trendline, flag, triangle, double top (level), round number,
  prior-day high, session high/low (EU session).  Plus:
  - prefix invariance on synthetic bars (run on bars[:t+1] == armed set at t);
  - prefix invariance on REAL EURUSD M5 2016 (the query-path leak guard);
  - query determinism (cache does not change the answer);
  - pruning cap (<= max_lines);
  - no-future-access (created/anchors/touches/broken are all <= t).

Run:  python test_vpa_lines.py
Prints one line per test and a final TESTS PASS summary. Exit code 0 on PASS.
The real-data test reads the parquet cache read-only and takes ~1 minute.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from vpa_lines import LineEngine, DEFAULTS  # noqa: E402

RESULTS = []
PIP = 1e-4
TICK = 1e-5


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"{'PASS' if cond else 'FAIL'}  {name} {detail}")


# --------------------------------------------------------------------- helpers
def mk_bars(rows, start_t=0, pip=PIP, tick=TICK):
    n = len(rows)
    t = [start_t + 300 * i for i in range(n)]
    utc = [(int(tt) // 60) % 1440 for tt in t]
    return {
        "t": t,
        "o": [r[0] for r in rows], "h": [r[1] for r in rows],
        "l": [r[2] for r in rows], "c": [r[3] for r in rows],
        "utc_min": utc, "srv_min": utc, "dow": [0] * n,
        "pip": pip, "tick": tick,
    }


def synth(path, half=PIP, **kw):
    rows = []
    prev = path[0]
    for p in path:
        o = prev
        h = max(o, p) + half
        l = min(o, p) - half
        rows.append((o, h, l, p))
        prev = p
    return mk_bars(rows, **kw)


def run(bars, cfg=None):
    return LineEngine(bars, cfg).run()


def kinds_at(eng, t):
    out = {}
    for a in eng.armed_at(t):
        out.setdefault(a.kind, []).append(a)
    return out


def find_kind(eng, t, *kinds):
    got = kinds_at(eng, t)
    for k in kinds:
        if got.get(k):
            return got[k][0]
    return None


# --------------------------------------------------------------------- fixtures
def box_path():
    """Tight 10-pip range for 50 bars after a small drift (tr. 156)."""
    path = [1.1000 - 0.00004 * i for i in range(12)]
    for i in range(50):
        path.append(1.0990 + (0.0010 if i % 4 < 2 else 0.0))
    return path


def trendline_path():
    """Ascending line with swing lows exactly on it at 20/50/80 (tr. 95, 109)."""
    n = 100
    path = []
    for i in range(n):
        lv = 1.0900 + 2e-5 * i
        if i in (20, 50, 80):
            path.append(lv + 1e-5)
        else:
            path.append(lv + (3e-4 if (i // 10) % 2 == 0 else 0.6e-4))
    return path


def flag_path():
    """Pole up 70 pips then a shallow counter-drift flag (tr. 113)."""
    path = [1.0900 + 0.0005 * i for i in range(14)]
    for i in range(46):
        base = 1.0970 - 0.00002 * i
        path.append(base + (0.0009 if i % 8 < 4 else 0.0))
    return path


def triangle_path():
    """Pole down, then converging boundaries (tr. 101, 105)."""
    path = [1.1030 - 0.00030 * i for i in range(10)]
    for i in range(48):
        hi = 1.1000 - 0.00002 * i
        lo = 1.0970 + 0.00002 * i
        if lo >= hi:
            lo = hi - 1e-4
        phase = i % 8
        if phase < 4:
            path.append(hi - 0.00003 * phase)
        else:
            path.append(lo + 0.00003 * (8 - phase))
    return path


def double_top_path():
    """Two equal peaks with an 8-pip trough between (tr. 157, 170, 172)."""
    path = [1.1000 + 0.00004 * i for i in range(10)]           # 0..9 up
    path += [1.1004 + 0.00008 * i for i in range(10)]          # 10..19 up to peak
    path += [1.1012 - 0.00016 * i for i in range(10)]          # 20..29 down
    path += [1.0996 + 0.00016 * i for i in range(10)]          # 30..39 up to peak
    path += [1.1012 - 0.00002 * i for i in range(20)]          # 40..59 drift
    return path


def round_path():
    """Oscillation around 1.1000 (00/50 grid, tr. 43)."""
    path = []
    for i in range(80):
        path.append(1.1000 + (0.0005 if (i // 5) % 2 == 0 else -0.0005))
    return path


def pdh_path():
    """Day 0 builds a high at 1.1100; day 1 tests it twice (tr. 42/44, 234/244)."""
    path = [1.1000 + 0.00005 * i for i in range(200)]                 # rise to 1.1100
    path += [1.10995 - 0.0000568 * (i - 199) for i in range(200, 288)]  # fall to ~1.105
    path += [1.1050 + 0.000167 * i for i in range(32)]                # day 1 up to 1.1103
    path += [1.1103 - 0.00005 * i for i in range(8)]                  # dip
    path += [1.1099 + 0.00002 * i for i in range(12)]                 # second test
    path += [1.1101 - 0.00005 * i for i in range(9)]                  # drift off
    return path


def sess_path():
    """EU session (bars 60..131 = 05:00-11:00 UTC): a session high made at
    bar 70 and tested twice afterwards (tr. 355, 362)."""
    path = [1.1000 + 0.00002 * (i % 10) for i in range(60)]
    path += [1.1000 + 0.00015 * (i + 1) for i in range(11)]      # rise to 1.10165
    path += [1.10165 - 0.00005 * (i % 6) for i in range(25)]     # oscillate below
    path += [1.1014 - 0.00009 * i for i in range(15)]            # dip
    path += [1.1002 + 0.00009 * i for i in range(29)]            # back up to test
    return path


# ------------------------------------------------------------------- test cases
def test_box():
    bars = synth(box_path())
    eng = run(bars)
    t = len(bars["t"]) - 1
    top = find_kind(eng, t, "box_top")
    bot = find_kind(eng, t, "box_bottom")
    check("box_top_armed", top is not None,
          f"kinds={sorted(kinds_at(eng, t))}" + (f" score={top.score:.2f}" if top else ""))
    check("box_bottom_armed", bot is not None,
          f"score={bot.score:.2f} n={bot.n_touches}" if bot else "")
    if top:
        check("box_top_is_horizontal", abs(top.slope) < 1e-12)
        check("box_top_score_ge_threshold", top.score >= DEFAULTS["score_threshold"],
              f"score={top.score:.3f} parts={ {k: round(v,2) for k,v in top.parts.items()} }")
    if bot:
        check("box_bottom_side", bot.side == -1)


def test_trendline():
    bars = synth(trendline_path())
    eng = run(bars)
    t = len(bars["t"]) - 1
    tl = find_kind(eng, t, "trendline")
    check("trendline_armed", tl is not None, f"kinds={sorted(kinds_at(eng, t))}")
    if tl:
        check("trendline_slope_positive", tl.slope > 0, f"slope={tl.slope:.3e}")
        check("trendline_two_plus_touches", tl.n_touches >= 2, f"n={tl.n_touches}")
        check("trendline_integrity", tl.integrity)
        check("trendline_age_ge_50", tl.age >= 50, f"age={tl.age}")


def test_flag():
    bars = synth(flag_path())
    eng = run(bars)
    t = len(bars["t"]) - 1
    fl = find_kind(eng, t, "flag_upper", "flag_lower")
    check("flag_boundary_armed", fl is not None, f"kinds={sorted(kinds_at(eng, t))}")
    if fl:
        check("flag_kind_name", fl.kind.startswith("flag"), fl.kind)
        check("flag_score_ge_threshold", fl.score >= DEFAULTS["score_threshold"],
              f"score={fl.score:.3f}")


def test_triangle():
    bars = synth(triangle_path())
    eng = run(bars)
    t = len(bars["t"]) - 1
    tr = find_kind(eng, t, "tri_upper", "tri_lower")
    check("triangle_boundary_armed", tr is not None, f"kinds={sorted(kinds_at(eng, t))}")
    if tr:
        check("triangle_kind_name", tr.kind.startswith("tri"), tr.kind)


def test_double_top():
    bars = synth(double_top_path())
    eng = run(bars)
    t = len(bars["t"]) - 1
    raw = [a for a in eng.armed_at(t, prune=False) if a.kind == "level"]
    check("double_top_level_armed", len(raw) > 0,
          f"raw_levels={[(a.kind, round(a.level,5)) for a in raw]}")
    if raw:
        lv = max(raw, key=lambda a: a.score)
        check("double_top_level_price", abs(lv.level - 1.1013) <= 2e-4,
              f"level={lv.level:.5f} touches={lv.n_touches}")
        check("double_top_touches_ge_2", lv.n_touches >= 2, f"n={lv.n_touches}")
    # the chart-hygiene merge must leave one line at that price, any kind
    on_chart = [a for a in eng.armed_at(t) if abs(a.level - 1.1013) <= 3e-4]
    check("double_top_on_chart", len(on_chart) == 1,
          f"lines_at_price={[(a.kind, round(a.level,5)) for a in on_chart]}")


def test_round_number():
    bars = synth(round_path())
    eng = run(bars)
    t = len(bars["t"]) - 1
    rn = find_kind(eng, t, "round")
    check("round_armed", rn is not None, f"kinds={sorted(kinds_at(eng, t))}")
    if rn:
        check("round_level_on_grid", abs((rn.level / (50 * PIP)) - round(rn.level / (50 * PIP))) < 1e-6,
              f"level={rn.level:.5f}")
        check("round_score_ge_threshold", rn.score >= DEFAULTS["score_threshold"],
              f"score={rn.score:.3f}")


def test_pdh():
    bars = synth(pdh_path())
    eng = run(bars)
    t = len(bars["t"]) - 9
    p = find_kind(eng, t, "pdh")
    check("pdh_armed", p is not None, f"kinds={sorted(kinds_at(eng, t))}")
    if p:
        day0_hi = max(synth(pdh_path())["h"][:288])
        check("pdh_level_matches_prior_day_high", abs(p.level - day0_hi) < 1e-9,
              f"level={p.level:.5f} day0_hi={day0_hi:.5f}")
        check("pdh_age_le_day", p.age <= 288, f"age={p.age}")


def test_session_extremes():
    bars = synth(sess_path())
    eng = run(bars)
    t = len(bars["t"]) - 1
    raw = eng.armed_at(t, prune=False)
    hi = next((a for a in raw if a.kind == "sess_hi"), None)
    lo = next((a for a in raw if a.kind == "sess_lo"), None)
    check("sess_hi_armed", hi is not None, f"kinds={sorted(kinds_at(eng, t))}")
    check("sess_lo_armed", lo is not None,
          f"score={lo.score:.3f}" if lo else "")
    if hi:
        day_hi = max(bars["h"][60:132])
        check("sess_hi_level_is_session_high", abs(hi.level - day_hi) < 1e-9,
              f"level={hi.level:.5f} session_high={day_hi:.5f}")
        check("sess_hi_age_le_session", hi.age <= 132, f"age={hi.age}")
    if lo:
        day_lo = min(bars["l"][60:132])
        check("sess_lo_level_is_session_low", abs(lo.level - day_lo) < 1e-9,
              f"level={lo.level:.5f} session_low={day_lo:.5f}")


def test_prefix_invariance():
    """The strongest causality check: armed_at(t) from the full run must equal
    armed_at(t) from a run over bars[:t+1] only (synthetic)."""
    bars = synth(box_path() + trendline_path())
    n = len(bars["t"])
    full = run(bars)
    probes = [60, 90, 120, 150, n - 1]
    bad = []
    for t in probes:
        pref = run({k: (v[:t + 1] if isinstance(v, list) else v) for k, v in bars.items()})
        a = sorted((x.kind, round(x.level, 6), round(x.score, 6)) for x in full.armed_at(t))
        b = sorted((x.kind, round(x.level, 6), round(x.score, 6)) for x in pref.armed_at(t))
        if a != b:
            bad.append((t, a, b))
    check("prefix_invariance", not bad, f"probes={probes} bad={bad[:1]}")


def test_prefix_invariance_real_data():
    """Real EURUSD M5 2016 (DESIGN): the full run and a run on bars[:t+1] must
    give the same armed set at the probe bars.  This is the test that catches
    the query-path leak the synthetic fixtures cannot reach (swing history)."""
    lab = os.path.abspath(os.path.join(HERE, "..", "lab"))
    if lab not in sys.path:
        sys.path.insert(0, lab)
    try:
        from vpa_data import load_m5_bars
    except Exception as exc:  # noqa: BLE001
        check("prefix_invariance_real_data", False, f"loader unavailable: {exc!r}")
        return
    bars = load_m5_bars("EURUSD", 2016, 2016)
    n = len(bars["t"])
    full = run(bars)
    probes = [5000, 20000, 40000, 60000, n - 1]
    bad = []
    for t in probes:
        pref = run({k: (v[:t + 1] if isinstance(v, list) else v) for k, v in bars.items()})
        a = sorted((x.kind, round(x.level, 6), round(x.score, 6)) for x in full.armed_at(t))
        b = sorted((x.kind, round(x.level, 6), round(x.score, 6)) for x in pref.armed_at(t))
        if a != b:
            bad.append((t, len(a), len(b)))
    check("prefix_invariance_real_data", not bad,
          f"bars={n} probes={probes} mismatch={bad}")


def test_query_matches_pass():
    """`armed_at` must be deterministic and unaffected by its state cache."""
    bars = synth(box_path())
    eng = run(bars)
    tt = len(bars["t"]) - 1
    a1 = [(a.kind, round(a.score, 9), a.lid) for a in eng.armed_at(tt)]
    eng._state_cache.clear()
    a2 = [(a.kind, round(a.score, 9), a.lid) for a in eng.armed_at(tt)]
    check("query_deterministic", a1 == a2, f"{a1} vs {a2}")
    check("query_nonempty", len(a1) > 0, f"n={len(a1)}")


def test_pruning_cap():
    bars = synth(round_path() + box_path())
    eng = run(bars)
    worst = 0
    worst_raw = 0
    for t in range(60, len(bars["t"]), 3):
        worst = max(worst, len(eng.armed_at(t)))
        worst_raw = max(worst_raw, len(eng.armed_at(t, prune=False)))
    check("pruning_cap", worst <= DEFAULTS["max_lines"],
          f"max_pruned={worst} max_raw={worst_raw} cap={DEFAULTS['max_lines']}")


def test_no_future_access():
    """Every armed line at t must have created_idx <= t and anchors <= t, and
    every touch must be <= t (no bar after the decision bar is read)."""
    bars = synth(box_path())
    eng = run(bars)
    bad = []
    for t in range(len(bars["t"])):
        for a in eng.armed_at(t):
            ln = eng.lines[a.lid]
            if ln.created_idx > t or max(ln.anchors) > t or ln.born_idx > t:
                bad.append(("created", t, a.lid, ln.created_idx))
            if a.touches and max(a.touches) > t:
                bad.append(("touch", t, a.lid, max(a.touches)))
            if a.broken_idx is not None and a.broken_idx > t:
                bad.append(("broken", t, a.lid, a.broken_idx))
    check("no_future_access", not bad, f"bad={bad[:2]}")


def main():
    for fn in (test_box, test_trendline, test_flag, test_triangle, test_double_top,
               test_round_number, test_pdh, test_session_extremes,
               test_prefix_invariance, test_prefix_invariance_real_data,
               test_query_matches_pass, test_pruning_cap, test_no_future_access):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            check(fn.__name__ + "_EXCEPTION", False, repr(exc))
    n_pass = sum(1 for _, ok, _ in RESULTS if ok)
    n_all = len(RESULTS)
    print(f"TESTS PASS {n_pass}/{n_all}")
    return 0 if n_pass == n_all else 1


if __name__ == "__main__":
    sys.exit(main())
