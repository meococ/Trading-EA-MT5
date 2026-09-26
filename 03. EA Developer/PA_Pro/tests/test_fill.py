"""pa_fill: SL-first on an ambiguous M1 bar, gap-aware fill, prefix invariance."""

import numpy as np

import pa_data
import pa_fill


def _flat_market(n_bars_m5=12, start=int(1546300800) + 2 * 3600):
    n = n_bars_m5 * 5
    t = np.int64(start) + np.arange(n, dtype=np.int64) * 60
    o = np.full(n, 1.1000)
    h = np.full(n, 1.1000)
    l = np.full(n, 1.1000)
    c = np.full(n, 1.1000)
    return {"t": t, "o": o, "h": h, "l": l, "c": c,
            "pip": 1e-4, "symbol": "SYNX", "split": "DESIGN",
            "warmup": np.zeros(n, dtype=bool)}


def _ctx(m1, bars):
    starts = np.searchsorted(m1["t"], bars["t"], side="left")
    return pa_fill.build_ctx(m1, bars, bars["t"], starts, m1["pip"],
                             symbol="SYNX", c_rt_pips=1.0)


def test_sl_first_when_one_m1_bar_touches_both():
    m1 = _flat_market()
    m1["h"][0] = 1.1005          # signal bar high -> stop = 1.1005 + 1 pip
    m1["l"][0] = 1.0995
    # bar 5: touches the stop AND then both SL and TP inside the same M1 bar
    m1["o"][5] = 1.1000
    m1["h"][5] = 1.1030
    m1["l"][5] = 1.0995
    m1["c"][5] = 1.1000
    bars = pa_data.resample(m1, "M5")
    ctx = _ctx(m1, bars)
    spec = pa_fill.resolve_spec({"legacy_flats": False})
    tr = pa_fill.simulate(spec, ctx, [{"sig": 0, "side": +1, "tag": 1}], "gross")
    assert len(tr) == 1
    t = tr[0]
    assert t["status"] == "FILLED"
    assert abs(t["fill"] - 1.1006) < 1e-12
    assert abs(t["sl"] - 1.0998) < 1e-12
    assert abs(t["tp"] - 1.1022) < 1e-12
    # bar 5 low <= SL and high >= TP -> SL must win
    assert t["exit_idx"] == 5 and t["reason"] == "SL" and t["r"] == -1.0


def test_gap_fill_uses_open_not_stop():
    m1 = _flat_market()
    m1["h"][0] = 1.1005          # stop = 1.1006
    m1["l"][0] = 1.0995
    # bar 5 opens above the stop -> fill at the open, not at the stop
    m1["o"][5] = 1.1015
    m1["h"][5] = 1.1016
    m1["l"][5] = 1.1014
    m1["c"][5] = 1.1015
    for i in range(6, len(m1["o"])):
        m1["o"][i] = m1["h"][i] = m1["l"][i] = m1["c"][i] = 1.1035
    bars = pa_data.resample(m1, "M5")
    ctx = _ctx(m1, bars)
    spec = pa_fill.resolve_spec({"legacy_flats": False})
    tr = pa_fill.simulate(spec, ctx, [{"sig": 0, "side": +1, "tag": 1}], "gross")
    t = tr[0]
    assert t["status"] == "FILLED"
    assert t["stop"] == 1.1006
    assert abs(t["fill"] - 1.1015) < 1e-12     # max(open, stop)
    assert t["r"] == 2.0                       # TP = 1.1015 + 0.0016 reached


def test_tp_exit_r_uses_tp_mult_not_hardcoded_2():
    """Regression for the hardcoded r=2.0 on TP exits (Lead order R01-D1 D8c)."""
    m1 = _flat_market()
    m1["h"][0] = 1.1005          # stop = 1.1005 + 1 pip, S = 8 pips
    m1["l"][0] = 1.0995
    for i in range(1, len(m1["o"])):
        m1["o"][i] = m1["h"][i] = m1["l"][i] = m1["c"][i] = 1.1000
    # bar 5 hits TP for tp_mult=3.0 (fill 1.1006 + 0.0024 = 1.1030) and not SL
    m1["o"][5] = 1.1000
    m1["h"][5] = 1.1035
    m1["l"][5] = 1.1000
    m1["c"][5] = 1.1020
    bars = pa_data.resample(m1, "M5")
    ctx = _ctx(m1, bars)
    spec = pa_fill.resolve_spec({"legacy_flats": False, "tp_mult": 3.0})
    tr = pa_fill.simulate(spec, ctx, [{"sig": 0, "side": +1, "tag": 1}], "gross")
    t = tr[0]
    assert t["status"] == "FILLED"
    assert t["reason"] == "TP"
    assert t["r"] == 3.0


def test_prefix_invariance_appending_future_bars():
    from conftest import make_synthetic_market

    m1_full, bars_full = make_synthetic_market(seed=99, days=6)
    rng = np.random.default_rng(5)
    sigs = rng.choice(np.arange(20, 800), size=60, replace=False)
    entries = [{"sig": int(s), "side": int(rng.integers(0, 2)) * 2 - 1,
                "tag": int(i)} for i, s in enumerate(sigs)]
    spec = pa_fill.resolve_spec({"legacy_flats": True})
    ctx_full = _ctx(m1_full, bars_full)
    full = pa_fill.simulate(spec, ctx_full, entries, "x1")

    cut = 6000
    m1_pre = {k: (m1_full[k][:cut] if k != "warmup" else m1_full[k][:cut])
              for k in ("t", "o", "h", "l", "c", "warmup")}
    m1_pre["pip"] = m1_full["pip"]
    bars_pre = pa_data.resample(m1_pre, "M5")
    ctx_pre = _ctx(m1_pre, bars_pre)
    pre = pa_fill.simulate(spec, ctx_pre, entries, "x1")

    assert len(full) == len(pre) == len(entries)
    n_checked = 0
    for a, b in zip(full, pre):
        # every entry sits far before the cut, so its ORDER status must match
        assert a["status"] == b["status"], a["tag"]
        if a["status"] != "FILLED":
            continue
        if a["exit_idx"] < cut - 5:            # already resolved in the prefix
            n_checked += 1
            for f in ("fill_idx", "fill", "sl", "tp", "exit_idx", "exit_px",
                      "reason", "r"):
                assert a[f] == b[f], (a["tag"], f)
    assert n_checked > 20
