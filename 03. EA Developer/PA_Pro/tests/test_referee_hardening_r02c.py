"""R02-C regression tests — ledger anchor, sidecar refusal, closure-held gate.

Lead order R02-C (2026-09-21) after `rounds/R02/REVIEW_REFEREE_FIXES.md`
(VERDICT FAIL, 7 token-gate bypasses + the `.tail` laundering vector):

(a) every FREEZE.json / round report carries ``sha256(ledger prefix)+n_lines``;
(b) a missing ``.tail`` is ``(False, last)`` and is never bootstrapped;
(c) ``_token_check`` / ``_evaluate_body`` are not module attributes and the
    checker cell lives in ``pa_metrics._build_gate``'s closure.

Each test below fails against the pre-R02-C source (run against the snapshot
in ``_scratch/r02c/oldrepo``; evidence in the R02-C report).
"""

import os

import pytest

import pa_eval
import pa_ledger
import pa_metrics

from conftest import make_synthetic_market, synth_provider


# --- (c) the gate has no module-level attack surface ------------------------

def test_token_checker_and_eval_body_are_not_module_attributes():
    assert not hasattr(pa_eval, "_token_check")
    assert not hasattr(pa_eval, "_evaluate_body")
    assert not hasattr(pa_eval, "_decoy_mint")
    assert not hasattr(pa_metrics, "_TOKEN_CHECKER")
    assert not hasattr(pa_metrics, "_require_token")
    # historical decoy names still exist, but only as raisers
    for name in ("_mint_token", "_enter_eval", "_leave_eval"):
        with pytest.raises(pa_metrics.EvalTokenError):
            getattr(pa_eval, name)("DESIGN")


def test_redteam_closure_attacks_4_to_6_are_dead():
    """Attacks #4/#5/#6 from REVIEW_REFEREE_FIXES no longer have a target."""
    # #4 closure-dig the token class/state out of `_token_check`
    with pytest.raises(AttributeError):
        pa_eval._token_check.__closure__
    # #5 rewrite the checker cell: there is no module-level cell to rewrite
    with pytest.raises(AttributeError):
        pa_metrics._TOKEN_CHECKER["fn"] = lambda o: True
    # #6 monkeypatch the gate function: setting the name is now a no-op —
    # `compute` closes over its own gate, so the forged attribute changes nothing
    assert "_require_token" not in vars(pa_metrics)
    pa_metrics._require_token = lambda t: None
    with pytest.raises(pa_metrics.EvalTokenError):
        pa_metrics.compute([], object())
    del pa_metrics._require_token
    # and a forged object still cannot aggregate
    with pytest.raises(pa_metrics.EvalTokenError):
        pa_metrics.compute([], object())


# --- (b) the sidecar is mandatory, verify() never writes --------------------

def test_missing_sidecar_refused_and_not_recreated(tmp_path):
    path = str(tmp_path / "TRIALS.jsonl")
    pa_ledger.set_ledger_path(path)
    for i in range(2):
        pa_ledger.append({"family": "T", "n": i})
    os.unlink(path + ".tail")
    ok, idx = pa_ledger.verify()
    assert not ok and idx == 1
    assert not os.path.exists(path + ".tail")


# --- (a) the ledger head anchor ---------------------------------------------

def _append_n(n):
    for i in range(n):
        pa_ledger.append({"family": "T", "split": "DESIGN", "n": i})


def test_anchor_survives_append_but_detects_history_rewrite(tmp_path):
    _append_n(3)
    a = pa_ledger.anchor()
    assert a["n_lines"] == 3 and len(a["sha256"]) == 64
    assert a["ledger"] == "TRIALS.jsonl"
    ok, why = pa_ledger.check_anchor(a)
    assert ok and why is None

    _append_n(1)                                   # later appends are fine
    ok, why = pa_ledger.check_anchor(a)
    assert ok and why is None

    path = pa_ledger.ledger_path()
    with open(path, "rb") as f:
        lines = f.read().split(b"\n")[:-1]
    lines[1] = lines[1].replace(b'"n":1', b'"n":9')  # rewrite covered history
    with open(path, "wb") as f:
        f.write(b"\n".join(lines) + b"\n")
    ok, why = pa_ledger.check_anchor(a)
    assert not ok and "mismatch" in why


def test_anchor_detects_truncation(tmp_path):
    _append_n(4)
    a = pa_ledger.anchor()
    path = pa_ledger.ledger_path()
    with open(path, "rb") as f:
        lines = f.read().split(b"\n")[:-1]
    with open(path, "wb") as f:                    # drop the newest 2 lines
        f.write(b"\n".join(lines[:2]) + b"\n")
    ok, why = pa_ledger.check_anchor(a)
    assert not ok and "holds 2 lines" in why


def test_anchor_md_names_sha_and_line_count():
    _append_n(2)
    a = pa_ledger.anchor()
    md = pa_ledger.anchor_md(a)
    assert a["sha256"] in md and "n_lines = 2" in md and "TRIALS.jsonl" in md


# --- (a2) the line commits to the data it describes -------------------------

def test_honest_line_carries_data_sha256_and_tracks_the_input():
    m1, bars = make_synthetic_market(seed=21, days=3)
    d = synth_provider(m1, bars)

    def provider(symbol, split, tf):
        return d

    def entries_fn(symbol, bars_, spec):
        return [{"sig": 100, "side": +1, "tag": 0}]

    spec = {"family": "R02C_DATA", "entries_fn": entries_fn, "legacy_flats": True}
    res = pa_eval.evaluate(spec, "DESIGN", ["SYNX"], "M5", ["gross"],
                           round_name="R02", data_provider=provider)
    line = pa_ledger.read_lines()[-1]
    assert line["data_sha256"] == res["data_sha256"]
    assert line["data_sha256_by_symbol"]["SYNX"] == res["data_sha256_by_symbol"]["SYNX"]
    assert len(line["data_sha256"]) == 64
    assert line["data_sha256"] == pa_eval._combine_data_sha256(
        {"SYNX": pa_eval._provider_data_sha256(d)})

    other = dict(d)
    other["m1"] = {k: (v + 0.5 if k == "c" else v) for k, v in d["m1"].items()}
    assert pa_eval._provider_data_sha256(other) != pa_eval._provider_data_sha256(d)


# --- R02-D: audit scratch never changes a code bundle -----------------------

def test_scratch_never_changes_the_lib_bundle(tmp_path):
    d = tmp_path / "libcopy"
    d.mkdir()
    (d / "pa_x.py").write_text("X", encoding="utf-8")
    h1 = pa_ledger.code_sha256(str(d))
    (d / "_probe.py").write_text("P", encoding="utf-8")
    (d / "_scratch").mkdir()
    (d / "_scratch" / "audit.py").write_text("A", encoding="utf-8")
    assert pa_ledger.code_sha256(str(d)) == h1
    (d / "pa_y.py").write_text("Y", encoding="utf-8")
    assert pa_ledger.code_sha256(str(d)) != h1

