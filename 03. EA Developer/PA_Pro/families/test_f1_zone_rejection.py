"""test_f1_zone_rejection.py — unit + adversarial tests for the F1 detector (v2).

Adversarial coverage (mandate): lookahead (prefix cut), boundary bars,
repeated signals (cooldown), invalid geometry (10x-cost guard, ladder
overflow, rung partition), future-bar mutation, zone role/expiry errors
(broken/unarmed/no-role).

Run:  python test_f1_zone_rejection.py
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE,):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import sf_ctx                     # noqa: E402
import f1_zone_rejection as f1    # noqa: E402

PIP = 1e-4
N = 300


def _mk_D(n=N, atr_pips=20.0):
    """Minimal synthetic cache dict: flat bars, caller injects zones/bars."""
    t = 1451606400 + 300 * np.arange(n, dtype=np.int64)
    return {
        "symbol": "SYN", "t": t,
        "o": np.full(n, 1.1000), "h": np.full(n, 1.1005),
        "l": np.full(n, 1.0995), "c": np.full(n, 1.1000),
        "pip": PIP, "first_live_idx": 0, "warmup": np.zeros(n, dtype=bool),
        "s_atr_m5": np.full(n, atr_pips * PIP),
        "s_atr_h1": np.full(n, 80 * PIP),
        "zlo": np.full((n, sf_ctx.SLOTS), np.nan),
        "zhi": np.full((n, sf_ctx.SLOTS), np.nan),
        "zf": np.zeros((n, sf_ctx.SLOTS, sf_ctx.ZF_N)),
        "zcnt": np.zeros(n, dtype=np.int64),
        "h1p_i": np.zeros(0, dtype=np.int64),
        "h1p_px": np.zeros(0, dtype=np.float64),
        "h1p_side": np.zeros(0, dtype=np.int64),
        "h1p_conf": np.zeros(0, dtype=np.int64),
        "h1p_anchor": np.zeros(0, dtype=np.int64),
    }


def _put_zone(D, t, lo, hi, armed=1, broken=0, approach=-1, touches=2,
              slot=0, zid=100):
    D["zlo"][t, slot] = lo
    D["zhi"][t, slot] = hi
    D["zcnt"][t] = max(D["zcnt"][t], slot + 1)
    f = D["zf"][t, slot]
    f[sf_ctx.ZF["zid"]] = zid
    f[sf_ctx.ZF["armed"]] = armed
    f[sf_ctx.ZF["broken"]] = broken
    f[sf_ctx.ZF["approach_side"]] = approach
    f[sf_ctx.ZF["touches"]] = touches
    f[sf_ctx.ZF["strength"]] = 0.9


def _good_ceiling_probe(D, t):
    """Bar t probes an armed ceiling zone [1.1020,1.1030] and rejects.
    range = 18p -> s_struct = 20p -> rung 24."""
    _put_zone(D, t, 1.1020, 1.1030, armed=1, broken=0, approach=-1)
    D["o"][t] = 1.1018
    D["h"][t] = 1.1026          # enters band (>= lo 1.1020)
    D["l"][t] = 1.1008
    D["c"][t] = 1.1014          # closed back below lo, bearish body
    D["c"][t - 1] = 1.1005      # prev close on approach side (<= hi)


def test_basic_signal():
    D = _mk_D()
    _good_ceiling_probe(D, 50)
    ent = f1.detect(D, 1.0, {"S_pips": 24.0})
    assert len(ent) == 1, ent
    e = ent[0]
    assert e["sig"] == 50 and e["side"] == -1
    assert abs(e["order_px"] - (1.1008 - PIP)) < 1e-9
    assert abs(e["inv"] - (1.1026 + PIP)) < 1e-9
    # rung partition: emitted only for rung 24, not 18 or 32
    assert f1.detect(D, 1.0, {"S_pips": 18.0}) == []
    assert f1.detect(D, 1.0, {"S_pips": 32.0}) == []
    print("basic signal + rung partition: OK")


def test_floor_signal():
    D = _mk_D()
    _put_zone(D, 60, 1.0980, 1.0990, armed=1, approach=1)
    D["o"][60] = 1.0992
    D["h"][60] = 1.1004
    D["l"][60] = 1.0986          # enters band
    D["c"][60] = 1.0998          # closed back above hi, bullish
    D["c"][59] = 1.1005
    # range 18p -> s_struct 20p -> rung 24
    ent = f1.detect(D, 1.0, {"S_pips": 24.0})
    assert len(ent) == 1 and ent[0]["side"] == 1
    assert abs(ent[0]["order_px"] - (1.1004 + PIP)) < 1e-9
    print("floor signal: OK")


def test_role_errors():
    # broken zone -> no signal
    D = _mk_D()
    _put_zone(D, 50, 1.1020, 1.1030, armed=1, broken=1, approach=-1)
    D["o"][50], D["h"][50], D["l"][50], D["c"][50] = 1.1018, 1.1026, 1.1008, 1.1014
    D["c"][49] = 1.1005
    assert f1.detect(D, 1.0, {"S_pips": 24.0}) == []
    # unarmed zone -> no signal
    D = _mk_D()
    _put_zone(D, 50, 1.1020, 1.1030, armed=0, broken=0, approach=-1)
    D["o"][50], D["h"][50], D["l"][50], D["c"][50] = 1.1018, 1.1026, 1.1008, 1.1014
    D["c"][49] = 1.1005
    assert f1.detect(D, 1.0, {"S_pips": 24.0}) == []
    # approach_side == 0 (no role) -> no signal
    D = _mk_D()
    _put_zone(D, 50, 1.1020, 1.1030, armed=1, broken=0, approach=0)
    D["o"][50], D["h"][50], D["l"][50], D["c"][50] = 1.1018, 1.1026, 1.1008, 1.1014
    D["c"][49] = 1.1005
    assert f1.detect(D, 1.0, {"S_pips": 24.0}) == []
    print("role/expiry errors rejected: OK")


def test_geometry_guards():
    # s_struct < 10*c_rt -> skip (isolate cost guard: low ATR passes range gate)
    D = _mk_D(atr_pips=8.0)
    _put_zone(D, 50, 1.1020, 1.1030, armed=1, approach=-1)
    D["o"][50], D["h"][50], D["l"][50], D["c"][50] = 1.1019, 1.1021, 1.1015, 1.1016
    D["c"][49] = 1.1010
    assert f1.detect(D, 1.0, {"S_pips": 11.0}) == []   # 8p < 10p guard
    # s_struct > max rung -> skip (probe bar too tall for any rung)
    D = _mk_D()
    _put_zone(D, 50, 1.1020, 1.1030, armed=1, approach=-1)
    D["o"][50], D["h"][50], D["l"][50], D["c"][50] = 1.1018, 1.1050, 1.1000, 1.1010
    D["c"][49] = 1.1005
    assert f1.detect(D, 1.0, {"S_pips": 32.0}) == []   # 52p > 32p ladder top
    # min-range gate: tiny bar fails even when geometry fine
    D = _mk_D(atr_pips=40.0)
    _put_zone(D, 50, 1.1020, 1.1030, armed=1, approach=-1)
    D["o"][50], D["h"][50], D["l"][50], D["c"][50] = 1.1018, 1.1026, 1.1008, 1.1014
    D["c"][49] = 1.1005
    assert f1.detect(D, 1.0, {"S_pips": 24.0}) == []   # 18p < 0.5*40p
    print("geometry guards: OK")


def test_boundary_and_warmup():
    D = _mk_D()
    _good_ceiling_probe(D, N - 1)
    ent = f1.detect(D, 1.0, {"S_pips": 24.0})
    assert all(e["sig"] < N for e in ent)
    D = _mk_D()
    D["warmup"][:100] = True
    D["first_live_idx"] = 100
    _good_ceiling_probe(D, 50)
    assert f1.detect(D, 1.0, {"S_pips": 24.0}) == []
    print("boundary/warmup: OK")


def test_cooldown_repeat():
    D = _mk_D()
    for t in (50, 55, 80):
        _good_ceiling_probe(D, t)
    ent = f1.detect(D, 1.0, {"S_pips": 24.0})
    sigs = [e["sig"] for e in ent]
    assert sigs == [50, 80], sigs        # t=55 suppressed (cooldown 12)
    print("cooldown dedupe: OK")


def _truncate_D(D, T):
    out = {}
    for k, v in D.items():
        a = np.asarray(v)
        if k in ("t", "o", "h", "l", "c", "warmup", "s_atr_m5", "s_atr_h1",
                 "zcnt", "zlo", "zhi", "zf"):
            out[k] = a[:T].copy()
        elif k in ("h1p_i", "h1p_px", "h1p_side", "h1p_conf", "h1p_anchor"):
            m = D["h1p_conf"] <= T
            out[k] = a[m].copy()
        else:
            out[k] = v
    return out


def test_prefix_invariance():
    D = _mk_D()
    for t in (50, 120, 200):
        _good_ceiling_probe(D, t)
    prm = {"S_pips": 24.0}
    full = f1.detect(D, 1.0, prm)
    cut = f1.detect(_truncate_D(D, 160), 1.0, prm)
    assert [e["sig"] for e in cut] == [e["sig"] for e in full if e["sig"] < 158]
    print("detector prefix invariance: OK")


def test_future_mutation():
    D = _mk_D()
    _good_ceiling_probe(D, 50)
    prm = {"S_pips": 24.0}
    base = f1.detect(D, 1.0, prm)
    Dm = _mk_D()
    _good_ceiling_probe(Dm, 50)
    Dm["h"][60:] = Dm["h"][60:] * 2
    Dm["l"][60:] = Dm["l"][60:] / 2
    Dm["c"][60:] = Dm["c"][60:] * 1.5
    mut = f1.detect(Dm, 1.0, prm)
    assert [(e["sig"], e["side"], e["order_px"]) for e in mut
            if e["sig"] <= 50] == \
           [(e["sig"], e["side"], e["order_px"]) for e in base]
    print("future mutation: OK")


if __name__ == "__main__":
    test_basic_signal()
    test_floor_signal()
    test_role_errors()
    test_geometry_guards()
    test_boundary_and_warmup()
    test_cooldown_repeat()
    test_prefix_invariance()
    test_future_mutation()
    print("ALL F1 detector tests passed")
