"""F2 regression — the two historical eval-token bypasses must now raise.

Reviewer R01-PREFLIGHT F2 (MAJOR): both of these returned metrics with NO
ledger append against the pre-R02-A code:

(a) ``pa_eval._enter_eval(); t = pa_eval._mint_token("DESIGN");
    pa_eval._leave_eval(); pa_metrics.compute([], t)``
(b) ``pa_metrics.register_token_checker(lambda o: True);
    pa_metrics.compute([], object())``

The repair moves the token machinery into the closure that defines
``evaluate`` (R02-A F2).  Each test below fails against the old code.
"""

import pytest

import pa_eval
import pa_ledger
import pa_metrics

from conftest import make_synthetic_market, synth_provider


def test_bypass_a_enter_mint_is_dead():
    """Historical bypass (a): the old enter/mint names must only raise."""
    with pytest.raises(pa_metrics.EvalTokenError):
        pa_eval._enter_eval()
    with pytest.raises(pa_metrics.EvalTokenError):
        pa_eval._mint_token("DESIGN")
    with pytest.raises(pa_metrics.EvalTokenError):
        pa_eval._mint_token("DESIGN", cand_id="cand1")
    with pytest.raises(pa_metrics.EvalTokenError):
        pa_eval._leave_eval()
    # no minted token can exist, so a forged one still cannot aggregate
    with pytest.raises(pa_metrics.EvalTokenError):
        pa_metrics.compute([], object())
    # the token class itself is not a module attribute
    assert getattr(pa_eval, "_EvalToken", None) is None


def test_bypass_b_register_checker_is_dead():
    """Historical bypass (b): the public registration hook is removed."""
    assert not hasattr(pa_metrics, "register_token_checker")
    with pytest.raises(AttributeError):
        pa_metrics.register_token_checker(lambda o: True)
    # the one-shot private handshake refuses re-registration
    with pytest.raises(RuntimeError):
        pa_metrics._register_token_checker(lambda o: True)
    # and a forged object cannot aggregate even after that attempt
    with pytest.raises(pa_metrics.EvalTokenError):
        pa_metrics.compute([], object())


def test_honest_path_works_and_appends_exactly_one_line():
    m1, bars = make_synthetic_market(seed=11, days=3)
    d = synth_provider(m1, bars)

    def provider(symbol, split, tf):
        return d

    def entries_fn(symbol, bars_, spec):
        return [{"sig": 100, "side": +1, "tag": 0},
                {"sig": 150, "side": -1, "tag": 1}]

    spec = {"family": "EVAL_GATE", "entries_fn": entries_fn, "legacy_flats": True}
    before = len(pa_ledger.read_lines())
    res = pa_eval.evaluate(spec, "DESIGN", ["SYNX"], "M5", ["gross"],
                           round_name="R02", data_provider=provider)
    lines = pa_ledger.read_lines()
    assert len(lines) == before + 1
    assert lines[-1]["status"] == "OK" and lines[-1]["family"] == "EVAL_GATE"
    assert lines[-1]["n"] == res["tiers"]["gross"]["strategy"]["N"]
    ok, bad = pa_ledger.verify()
    assert ok and bad is None
