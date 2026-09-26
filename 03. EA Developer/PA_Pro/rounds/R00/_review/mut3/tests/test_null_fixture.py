"""Null fixture: random entries through the engine + matched random baseline
give a lift CI covering 0 (seeded, robust)."""

import numpy as np

import pa_eval

from conftest import make_synthetic_market, synth_provider


def test_null_fixture_lift_ci_covers_zero():
    m1, bars = make_synthetic_market(seed=4242, days=20)
    d = synth_provider(m1, bars)
    rng = np.random.default_rng(31337)
    # in-session M5 bars (the matcher only draws from in-session cells)
    in_sess = np.flatnonzero((bars["utc_min"] >= 300) & (bars["utc_min"] < 1050))
    sigs = rng.choice(in_sess[:-1], size=300, replace=False)
    sides = rng.integers(0, 2, size=300) * 2 - 1
    entries = [{"sig": int(s), "side": int(dd), "tag": int(i)}
               for i, (s, dd) in enumerate(zip(sigs, sides))]

    def entries_fn(symbol, bars_, spec):
        return entries

    spec = {"family": "NULL_FIXTURE", "entries_fn": entries_fn,
            "params": {"group": "null"}, "legacy_flats": False}
    res = pa_eval.evaluate(spec, "DESIGN", ["SYNX"], "M5", ["x1"],
                           round_name="R00", seed=20260920, K_random=20,
                           data_provider=lambda sym, split, tf: d)
    tier = res["tiers"]["x1"]
    assert tier["strategy"]["N"] > 50
    assert tier["random"]["N"] > 800
    lo, hi = tier["lift_ci_pp"]
    assert lo <= 0.0 <= hi, f"lift CI does not cover 0: [{lo}, {hi}]"
    # sanity: the point lift is small
    assert abs(tier["lift_pp"]) < 5.0
