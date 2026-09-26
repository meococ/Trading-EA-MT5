"""Component unit tests on hand-made bars (Phase B requirement)."""
import numpy as np
import pytest

from src.components import indicators as ind
from src.components import pva as pva_mod
from src.components import pvsra as pvsra_mod
from src.components import sessions as sess
from src.components import stops_targets as st
from src.components import swings as sw_mod
from src.components import wave as wave_mod
from src.components import whq as whq_mod
from src.components import zones as zn
from src import data as data_mod


def test_ema_seed_and_recursion():
    x = np.arange(1.0, 11.0)
    e = ind.ema(x, 4)
    assert np.isnan(e[2])
    assert e[3] == pytest.approx(np.mean(x[:4]))
    k = 2 / 5
    assert e[4] == pytest.approx(e[3] + k * (x[4] - e[3]))


def test_atr_wilder():
    h = np.array([2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10.0])
    l = h - 1.5
    c = h - 0.5
    a = ind.atr_wilder(h, l, c, 14)
    assert np.isnan(a[13]) and np.isfinite(a[14])
    tr = np.maximum(h[1:], c[:-1]) - np.minimum(l[1:], c[:-1])
    assert a[14] == pytest.approx(tr[:14].mean())


def test_dragon_and_angle():
    d = {"h": np.linspace(10, 20, 60), "l": np.linspace(8, 18, 60),
         "c": np.linspace(9, 19, 60)}
    dh, dm, dl = ind.dragon(d)
    assert np.all(dh[40:] >= dm[40:]) and np.all(dm[40:] >= dl[40:])
    atr = np.full(60, 0.5)
    ang = ind.dragon_angle_atr(dm, atr, 5)
    assert ang[40] > 0


def test_fractal2_confirmation_lag():
    h = np.array([1., 2., 3., 2., 1., 2., 3., 4., 3., 2.])
    l = np.array([0., 1., 2., 1., 0., 1., 2., 3., 2., 1.])
    sw = sw_mod.fractal2(h, l)
    # swing high at i=2 (3 > 1,2 neighbours), confirmed at i=4
    assert 2 in sw["idx"]
    k = list(sw["idx"]).index(2)
    assert sw["dir"][k] == 1 and sw["conf"][k] == 4
    # usable only for decision bars t >= 4
    assert not sw_mod.swings_usable(sw, 3)[k]
    assert sw_mod.swings_usable(sw, 4)[k]


def test_zigzag_basic():
    n = 40
    c = np.concatenate([np.linspace(1, 5, 15), np.linspace(5, 1, 15),
                        np.linspace(1, 4, 10)])
    h = c + 0.1
    l = c - 0.1
    atr = np.full(n, 0.5)
    sw = sw_mod.atr_zigzag(h, l, c, atr, 1.5)
    assert len(sw["idx"]) >= 2
    # first confirmed = the ORIGIN low at bar 0 (price ran 1.5*ATR up)
    assert sw["dir"][0] == -1 and sw["idx"][0] == 0
    # second = the high near the top of the rise
    assert sw["dir"][1] == 1 and 12 <= sw["idx"][1] <= 17
    assert np.all(sw["conf"] > sw["idx"])


def test_whq_grid_both_symbols():
    assert whq_mod.level_kind(1.1000, "EURUSD") == whq_mod.WHOLE
    assert whq_mod.level_kind(1.1050, "EURUSD") == whq_mod.HALF
    assert whq_mod.level_kind(1.1025, "EURUSD") == whq_mod.QUARTER
    assert whq_mod.level_kind(2350.0, "XAUUSD") == whq_mod.WHOLE
    assert whq_mod.level_kind(2352.5, "XAUUSD") == whq_mod.QUARTER
    assert whq_mod.level_kind(2355.0, "XAUUSD") == whq_mod.HALF
    assert whq_mod.next_whq(1.1001, "EURUSD", 1) == pytest.approx(1.1050)
    assert whq_mod.next_whq(2351.0, "XAUUSD", -1) == pytest.approx(2350.0)


def test_pva_rising_climax():
    n = 30
    h = np.full(n, 2.0); l = np.full(n, 1.0)
    o = np.full(n, 1.2); c = np.full(n, 1.8)
    tv = np.full(n, 100.0)
    tv[15] = 160.0                    # 1.6x avg of prior 10
    l[15] = 1.6                       # narrow range -> sv=160*0.4=64 <100
    tv[20] = 250.0                    # >=2x -> climax
    cls, d, av, hi2 = pva_mod.pva_class(h, l, c, o, tv)
    assert cls[15] == pva_mod.RISING
    assert cls[20] == pva_mod.CLIMAX
    assert cls[5] == pva_mod.NORMAL
    assert d[15] == 1


def _mk_wave_bars():
    """Hand-made L-H-HL then breakout. Dragon flat at 10-11; ema89 below."""
    n = 30
    o = np.full(n, 10.5); c = np.full(n, 10.5)
    h = np.full(n, 10.6); l = np.full(n, 10.4)
    # leg0 low at 5 (below band), leg1 high at 9 (above band), leg2 HL 13
    l[5] = 9.0; h[5] = 10.0
    h[9] = 12.0; l[9] = 10.8; c[9] = 11.8
    l[13] = 10.0; h[13] = 10.7
    h[20] = 11.8; l[20] = 10.9; o[20] = 11.0; c[20] = 11.7   # trigger
    return o, h, l, c


def test_wave_trigger_and_thru():
    o, h, l, c = _mk_wave_bars()
    n = len(o)
    d_hi = np.full(n, 11.0); d_lo = np.full(n, 10.0)
    sw = sw_mod.fractal2(h, l)
    w = wave_mod.wave_at(20, sw, d_lo, d_hi, o, h, l, c, lookback=40)
    assert w is not None and w["dir"] == 1
    assert w["leg0"] == 5 and w["leg1"] == 9 and w["leg2"] == 13
    # leg0.h=10.0 not > 11.0; leg1.l=10.8 not < 10.0 -> thru False
    assert w["thru"] is False
    # now let leg-1's low pierce below the band -> thru True
    l2 = l.copy(); l2[9] = 9.5
    sw2 = sw_mod.fractal2(h, l2)
    w2 = wave_mod.wave_at(20, sw2, d_lo, d_hi, o, h, l2, c, lookback=40)
    assert w2 is not None and w2["thru"] is True


def test_wave_requires_confirmation():
    o, h, l, c = _mk_wave_bars()
    n = len(o)
    d_hi = np.full(n, 11.0); d_lo = np.full(n, 10.0)
    sw = sw_mod.fractal2(h, l)
    # at t=14 the HL at 13 is NOT yet confirmed (needs bar 15)
    assert wave_mod.wave_at(14, sw, d_lo, d_hi, o, h, l, c) is None


def test_sessions_london_dst():
    import datetime as dt
    # 2021-03-15 09:00 UTC: US DST on (server UTC+3 -> ctm = utc+3h),
    # UK DST off (London = UTC) -> London hour 9 -> in 8-16 window.
    u1 = int(dt.datetime(2021, 3, 15, 9, tzinfo=dt.timezone.utc)
             .timestamp())
    ctm = u1 + 3 * 3600
    hour, dow, _ = data_mod.london_parts(np.array([ctm]))
    assert hour[0] == 9 and dow[0] == 0
    # 2021-04-05 same UTC: UK DST on -> London 10:00
    u2 = int(dt.datetime(2021, 4, 5, 9, tzinfo=dt.timezone.utc)
             .timestamp())
    ctm2 = u2 + 3 * 3600
    hour2, _, _ = data_mod.london_parts(np.array([ctm2]))
    assert hour2[0] == 10


def test_swing_zone_cluster_and_death():
    n = 60
    h = np.linspace(10, 11, n); l = h - 0.5; c = h - 0.25
    atr = np.full(n, 0.2)
    sw = {"idx": np.array([5, 10, 30]), "px": np.array([9.8, 9.85, 12.0]),
          "dir": np.array([-1, -1, 1]),
          "conf": np.array([7, 12, 32])}
    z = zn.SwingZones(sw, h, l, c, atr)
    zs = z.zones_at(20)
    assert len(zs) == 1 and zs[0]["dir"] == -1 and zs[0]["n"] == 2
    assert zn.price_in_zone(9.8, zs)


def test_zone_availability_at_second_member_conf():
    """LEAD_NOTE_3: a cluster exists only from the 2nd member's
    confirmation bar; invisible for every t < avail_idx."""
    n = 60
    h = np.linspace(10, 11, n); l = h - 0.5; c = h - 0.25
    atr = np.full(n, 0.2)
    sw = {"idx": np.array([5, 30]), "px": np.array([9.8, 9.85]),
          "dir": np.array([-1, -1]), "conf": np.array([7, 25])}
    z = zn.SwingZones(sw, h, l, c, atr)
    assert z.zones_at(11) == []           # first member confirmed only
    assert z.zones_at(24) == []           # 2nd member pivoted, not conf
    zs = z.zones_at(25)
    assert len(zs) == 1
    assert zs[0]["avail_idx"] == 25 and zs[0]["origin_idx"] == 5
    assert zs[0]["members"] == (5, 30)


def test_stops_targets():
    d = {"h": np.array([11.0] * 30), "l": np.array([10.0] * 30)}
    atr = np.full(30, 0.1)
    w = {"leg0": 5, "leg1": 9, "leg2": 13, "dir": 1}
    d["l"][5] = 9.0
    sl = st.sl_leg0(w, d, 20, atr)
    assert sl == pytest.approx(9.0 - 0.01)
    # R=0.006; nearest half-level 1.1050 is only 0.004 away -> no trade
    assert st.tp_whq(1.1010, 1.0950, 1, "EURUSD") is None
    # R=0.002 -> 1.1050 is >= 1R -> ok
    tp2 = st.tp_whq(1.1010, 1.0990, 1, "EURUSD")
    assert tp2 == pytest.approx(1.1050)


def test_sl_big_swing_strict_side():
    """LEAD errata 1c: SL must sit strictly beyond pending on the stop
    side; None when no qualifying extreme exists. Random synthetic sets:
    SL always correct side and |pending - SL| > 0."""
    rng = np.random.default_rng(3)
    for trial in range(200):
        n = 80
        h = np.cumsum(rng.normal(0, 0.5, n)) + 10
        l = h - abs(rng.normal(0.3, 0.2, n))
        c = (h + l) / 2
        atr = np.full(n, 0.3)
        zig = sw_mod.atr_zigzag(h, l, c, atr, 1.5)
        t = n - 1
        for dr in (1, -1):
            pend = float(c[t] + dr * rng.uniform(0.05, 0.4))
            sl = st.sl_big_swing({"h": h, "l": l, "c": c}, t, atr, zig,
                                 dr, pend)
            if sl is not None:
                assert (pend - sl) * dr > 0          # correct side
            # when it returns None there must be no qualifying extreme
            else:
                side = -1 if dr == 1 else 1
                ok = (zig["conf"] <= t) & (zig["idx"] >= t - 48) \
                    & (zig["dir"] == side)
                if dr == 1:
                    assert not np.any(zig["px"][ok] < pend)
                else:
                    assert not np.any(zig["px"][ok] > pend)


def test_holdout_refused():
    with pytest.raises(PermissionError):
        data_mod.load_m1("EURUSD", data_mod.HOLDOUT_START,
                         data_mod.HOLDOUT_START + 3600)
