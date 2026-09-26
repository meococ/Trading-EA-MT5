"""VPA-ECON-1 simulator tests — hand-computed fixtures.

Covers: trigger+TP, expiry (no-look-ahead fill rule), invalidation cancel,
same-bar TP+SL (SL first), gap fill, safety flats (daily 22:00 server, Friday
20:00 server, Friday veto, midnight fallback), cost shift x1/x2.
Run: python test_vpa_econ1_sim.py
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from vpa_econ1_sim import build_ctx, metrics, simulate_entries  # noqa: E402

RESULTS = []
PIP = 1e-4


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'}  {name} {detail}")


def build(m1_rows, t0):
    """m1_rows: list of (o,h,l,c) for consecutive M1 bars from t0.
    M5 bars = groups of 5; starts = every 5th M1 index."""
    n = len(m1_rows)
    assert n % 5 == 0, n
    t = np.array([t0 + 60 * i for i in range(n)], dtype=np.int64)
    o = np.array([r[0] for r in m1_rows]); h = np.array([r[1] for r in m1_rows])
    l = np.array([r[2] for r in m1_rows]); c = np.array([r[3] for r in m1_rows])
    n5 = n // 5
    m5h = np.array([h[5 * k:5 * k + 5].max() for k in range(n5)])
    m5l = np.array([l[5 * k:5 * k + 5].min() for k in range(n5)])
    m5_t = np.array([t0 + 300 * k for k in range(n5)], dtype=np.int64)
    starts = np.array([5 * k for k in range(n5 + 1)], dtype=np.int64)
    m1 = {"t": t, "o": o, "h": h, "l": l, "c": c}
    m5 = {"h": m5h, "l": m5l}
    return m1, m5, m5_t, starts


def flat_bar(px, rng=2 * PIP):
    return (px, px + rng, px - rng, px)


# ---------------- 1. trigger + TP ----------------
def test_trigger_tp():
    # signal bar (M5 0) h=1.1005 -> long stop = 1.1006; cost x1 -> fill 1.1007
    rows = [flat_bar(1.1000) for _ in range(4)] + [(1.1000, 1.1005, 1.0998, 1.1002)]                       # M5 0
    rows += [flat_bar(1.1002), flat_bar(1.1003),
             (1.1004, 1.1008, 1.1003, 1.1007),                        # M1 7: entry touched
             flat_bar(1.1010), flat_bar(1.1015)]                      # M5 1
    rows += [flat_bar(1.1015), flat_bar(1.1020), (1.1021, 1.1026, 1.1019, 1.1024),
             flat_bar(1.1020), flat_bar(1.1020)]                      # M5 2: TP (1.1023) hit at M1 12
    rows += [flat_bar(1.1020) for _ in range(10)]
    m1, m5, m5_t, starts = build(rows, t0=1690000000)
    ctx = build_ctx(m1, m5, m5_t, starts, PIP)
    tr = simulate_entries([{"sig": 0, "side": 1, "atr": 3 * PIP}], ctx, mult=1.0)
    t = tr[0]
    check("trigger_filled", t["status"] == "FILLED" and t["reason"] == "TP", f"{t.get('status')} {t.get('reason')}")
    check("trigger_fill_level", abs(t["fill"] - (1.1006 + 1 * PIP)) < 1e-12, f"fill={t['fill']}")
    check("trigger_r_plus2", t["r"] == 2.0, f"r={t['r']}")
    # x2 cost: fill 2 pips worse -> TP at 1.1024, still TP (high 1.1026)
    tr2 = simulate_entries([{"sig": 0, "side": 1, "atr": 3 * PIP}], ctx, mult=2.0)
    check("trigger_cost_x2", abs(tr2[0]["fill"] - (1.1006 + 2 * PIP)) < 1e-12 and tr2[0]["r"] == 2.0,
          f"fill={tr2[0]['fill']} r={tr2[0]['r']}")


# ---------------- 2. expiry / no-look-ahead ----------------
def test_expiry_no_lookahead():
    rows = [flat_bar(1.1000) for _ in range(4)] + [(1.1000, 1.1005, 1.0998, 1.1002)]
    rows += [flat_bar(1.1002) for _ in range(15)]                     # V=3 window: no touch
    rows += [flat_bar(1.1010) for _ in range(5)]                      # M1 20: entry reached LATER
    m1, m5, m5_t, starts = build(rows, t0=1690000000)
    ctx = build_ctx(m1, m5, m5_t, starts, PIP)
    tr = simulate_entries([{"sig": 0, "side": 1, "atr": 3 * PIP}], ctx, mult=1.0)
    check("expiry_no_fill", tr[0]["status"] == "EXPIRED", f"{tr[0]['status']}")


# ---------------- 3. invalidation cancel ----------------
def test_invalidation_cancel():
    rows = [flat_bar(1.1000) for _ in range(4)] + [(1.1000, 1.1005, 1.0998, 1.1002)]
    rows += [flat_bar(1.1002), (1.1001, 1.1003, 1.0989, 1.0990),      # M1 6: inv touched first
             (1.1004, 1.1008, 1.1003, 1.1007), flat_bar(1.1010), flat_bar(1.1010)]
    rows += [flat_bar(1.1010) for _ in range(15)]
    m1, m5, m5_t, starts = build(rows, t0=1690000000)
    ctx = build_ctx(m1, m5, m5_t, starts, PIP)
    tr = simulate_entries([{"sig": 0, "side": 1, "inv": 1.0990, "atr": 3 * PIP}], ctx, mult=1.0)
    check("invalidation_cancel", tr[0]["status"] == "CANCELLED", f"{tr[0]['status']}")
    tr2 = simulate_entries([{"sig": 0, "side": 1, "atr": 3 * PIP}], ctx, mult=1.0, invalidation=False)
    check("no_inv_when_disabled", tr2[0]["status"] == "FILLED", f"{tr2[0]['status']}")


# ---------------- 4. same-bar TP+SL -> SL first ----------------
def test_same_bar_sl_first():
    rows = [flat_bar(1.1000) for _ in range(4)] + [(1.1000, 1.1005, 1.0998, 1.1002)]
    rows += [flat_bar(1.1002), flat_bar(1.1003),
             (1.1004, 1.1008, 1.1003, 1.1007), flat_bar(1.1010), flat_bar(1.1010)]
    rows += [(1.1000, 1.1026, 1.0990, 1.1000)]                        # M1 10: both TP and SL
    rows += [flat_bar(1.1000) for _ in range(14)]
    m1, m5, m5_t, starts = build(rows, t0=1690000000)
    ctx = build_ctx(m1, m5, m5_t, starts, PIP)
    tr = simulate_entries([{"sig": 0, "side": 1, "atr": 3 * PIP}], ctx, mult=1.0)
    check("same_bar_sl_first", tr[0]["reason"] == "SL" and tr[0]["r"] == -1.0,
          f"{tr[0]['reason']} r={tr[0]['r']}")


# ---------------- 5. gap fill ----------------
def test_gap_fill():
    rows = [flat_bar(1.1000) for _ in range(4)] + [(1.1000, 1.1005, 1.0998, 1.1002)]
    rows += [flat_bar(1.1002), flat_bar(1.1003),
             (1.1012, 1.1015, 1.1010, 1.1013),                        # opens beyond the stop
             flat_bar(1.1013), flat_bar(1.1013)]
    rows += [flat_bar(1.1013) for _ in range(15)]
    m1, m5, m5_t, starts = build(rows, t0=1690000000)
    ctx = build_ctx(m1, m5, m5_t, starts, PIP)
    tr = simulate_entries([{"sig": 0, "side": 1, "atr": 3 * PIP}], ctx, mult=1.0)
    t = tr[0]
    check("gap_fill_at_open", t["status"] == "FILLED" and abs(t["fill"] - (1.1012 + 1 * PIP)) < 1e-12,
          f"fill={t.get('fill')}")
    check("gap_flag", t["gap_atr"] is not None and abs(t["gap_atr"] - (6 * PIP) / (3 * PIP)) < 1e-9,
          f"gap_atr={t['gap_atr']}")


# ---------------- 6. flats ----------------
def test_flats():
    # daily 22:00 server: fill at 21:50 server, next bars at 22:00 -> DAILY close
    t0 = 1690038000 - (1690038000 % 86400) + 21 * 3600 + 50 * 60     # 21:50 server
    rows = [flat_bar(1.1000) for _ in range(4)] + [(1.1000, 1.1005, 1.0998, 1.1002)]
    rows += [flat_bar(1.1002), flat_bar(1.1003),
             (1.1004, 1.1008, 1.1003, 1.1007), flat_bar(1.1005), flat_bar(1.1005)]
    rows += [flat_bar(1.1005) for _ in range(15)]                     # 22:00+ reached at M1 10
    m1, m5, m5_t, starts = build(rows, t0=t0)
    ctx = build_ctx(m1, m5, m5_t, starts, PIP)
    tr = simulate_entries([{"sig": 0, "side": 1, "atr": 3 * PIP}], ctx, mult=1.0)
    check("daily_flat_2200", tr[0]["status"] == "FILLED" and tr[0]["reason"] == "DAILY",
          f"{tr[0].get('status')} {tr[0].get('reason')}")
    # Friday 20:00 server veto on the signal bar
    t0f = 19565 * 86400 + 20 * 3600                                  # Friday 20:00 server
    m1f, m5f, m5_tf, startsf = build([flat_bar(1.1000) for _ in range(4)] + [(1.1000, 1.1005, 1.0998, 1.1002)] + [flat_bar(1.1000) for _ in range(10)], t0=t0f)
    ctxf = build_ctx(m1f, m5f, m5_tf, startsf, PIP)
    trf = simulate_entries([{"sig": 0, "side": 1, "atr": 3 * PIP}], ctxf, mult=1.0)
    check("friday_veto", trf[0]["status"] == "VETO_FRIDAY", f"{trf[0]['status']}")
    # Friday 20:00 server flat on an open position
    t0g = 19565 * 86400 + 19 * 3600 + 50 * 60                        # Friday 19:50 server
    rowsg = [flat_bar(1.1000) for _ in range(4)] + [(1.1000, 1.1005, 1.0998, 1.1002)]
    rowsg += [flat_bar(1.1002), flat_bar(1.1003),
              (1.1004, 1.1008, 1.1003, 1.1007), flat_bar(1.1005), flat_bar(1.1005)]
    rowsg += [flat_bar(1.1005) for _ in range(15)]
    m1g, m5g, m5_tg, startsg = build(rowsg, t0=t0g)
    ctxg = build_ctx(m1g, m5g, m5_tg, startsg, PIP)
    trg = simulate_entries([{"sig": 0, "side": 1, "atr": 3 * PIP}], ctxg, mult=1.0)
    check("friday_flat_2000", trg[0]["status"] == "FILLED" and trg[0]["reason"] == "FRIDAY",
          f"{trg[0].get('status')} {trg[0].get('reason')}")
    # midnight fallback with flats disabled
    t0m = 1690038000 - (1690038000 % 86400) + 23 * 3600 + 50 * 60    # 23:50 server
    rowsm = [flat_bar(1.1000) for _ in range(4)] + [(1.1000, 1.1005, 1.0998, 1.1002)]
    rowsm += [flat_bar(1.1002), flat_bar(1.1003),
              (1.1004, 1.1008, 1.1003, 1.1007), flat_bar(1.1005), flat_bar(1.1005)]
    rowsm += [flat_bar(1.1005) for _ in range(15)]
    m1m, m5m, m5_tm, startsm = build(rowsm, t0=t0m)
    ctxm = build_ctx(m1m, m5m, m5_tm, startsm, PIP)
    trm = simulate_entries([{"sig": 0, "side": 1, "atr": 3 * PIP}], ctxm, mult=1.0, flats=False)
    check("midnight_fallback", trm[0]["status"] == "FILLED" and trm[0]["reason"] == "MIDNIGHT",
          f"{trm[0].get('status')} {trm[0].get('reason')}")


# ---------------- 7. session-end cancel ----------------
def test_session_end_cancel():
    rows = [flat_bar(1.1000) for _ in range(4)] + [(1.1000, 1.1005, 1.0998, 1.1002)]
    rows += [flat_bar(1.1002) for _ in range(5)]                      # M5 1
    rows += [flat_bar(1.1010) for _ in range(5)]                      # M5 2: entry reached here
    rows += [flat_bar(1.1010) for _ in range(5)]
    m1, m5, m5_t, starts = build(rows, t0=1690000000)
    # session containing M5 bars 0-1 ends at M1 10 -> the order must not fill at M1 10
    next_end = [10, 10, 20, 20]
    ctx = build_ctx(m1, m5, m5_t, starts, PIP, next_end=next_end)
    tr = simulate_entries([{"sig": 0, "side": 1, "atr": 3 * PIP}], ctx, mult=1.0)
    check("session_end_cancel", tr[0]["status"] == "EXPIRED", f"{tr[0]['status']}")
    ctx2 = build_ctx(m1, m5, m5_t, starts, PIP)
    tr2 = simulate_entries([{"sig": 0, "side": 1, "atr": 3 * PIP}], ctx2, mult=1.0)
    check("no_session_cap_when_absent", tr2[0]["status"] == "FILLED", f"{tr2[0]['status']}")


# ---------------- 8. metrics sanity ----------------
def test_metrics():
    trades = [{"status": "FILLED", "r": 2.0, "reason": "TP", "exit_t": 1},
              {"status": "FILLED", "r": -1.0, "reason": "SL", "exit_t": 2},
              {"status": "FILLED", "r": -1.0, "reason": "SL", "exit_t": 3}]
    m = metrics(trades)
    check("metrics_pf", abs(m["PF"] - 1.0) < 1e-9, f"PF={m['PF']}")
    check("metrics_wr", abs(m["WR"] - 1 / 3) < 1e-9, f"WR={m['WR']}")
    check("metrics_dd", m["max_dd_pct"] > 0, f"dd={m['max_dd_pct']}")


def main():
    test_trigger_tp()
    test_expiry_no_lookahead()
    test_invalidation_cancel()
    test_same_bar_sl_first()
    test_gap_fill()
    test_flats()
    test_session_end_cancel()
    test_metrics()
    passed = sum(1 for _, ok in RESULTS if ok)
    print(f"TESTS {'PASS' if passed == len(RESULTS) else 'FAIL'} {passed}/{len(RESULTS)}")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
