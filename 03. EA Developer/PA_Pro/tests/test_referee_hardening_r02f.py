"""R02-F regression tests — deployed anchors + complete data_sha256 coverage.

Lead order R02-F after `rounds/R02/REVIEW_REFEREE_FIXES_2.md` (VERDICT FAIL):

1. the anchor must actually be deployed (`ANCHORS.jsonl`, retro-anchored) and
   verified against every record (`verify_against_anchors`);
2. prefix semantics: appends legal, rewrites inside a covered prefix fatal;
3. `data_sha256` must cover every result-deciding provider field and can never
   be asserted by the caller.

Each test fails against the pre-R02-F snapshot in `_scratch/r02f/oldrepo`.
"""

import json
import os

import numpy as np

import pa_eval
import pa_ledger

from conftest import make_synthetic_market, synth_provider

PA_PRO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _seed_ledger(n=3):
    for i in range(n):
        pa_ledger.append({"family": "T", "split": "DESIGN", "n": i})


def _tamper_line(path, idx, old, new):
    with open(path, "rb") as f:
        lines = f.read().split(b"\n")
    assert old in lines[idx]
    lines[idx] = lines[idx].replace(old, new)
    with open(path, "wb") as f:
        f.write(b"\n".join(lines))


# --- 1/2. anchors: deployed, prefix-only, earliest violation ----------------

def test_append_anchor_roundtrip_and_legal_appends():
    _seed_ledger(3)
    rec = pa_ledger.append_anchor(note="unit")
    assert rec["kind"] == "ledger_anchor" and rec["n_lines"] == 3
    assert len(rec["sha256"]) == 64
    assert os.path.exists(pa_ledger.anchors_path())

    ok, v = pa_ledger.verify_against_anchors()
    assert ok and v is None

    pa_ledger.append({"family": "T", "n": 3})       # growth is legal by design
    ok, v = pa_ledger.verify_against_anchors()
    assert ok and v is None


def test_rewrite_inside_covered_prefix_is_detected():
    _seed_ledger(3)
    pa_ledger.append_anchor(note="unit")
    _tamper_line(pa_ledger.ledger_path(), 1, b'"n":1', b'"n":9')
    ok, v = pa_ledger.verify_against_anchors()
    assert not ok
    assert v["n_lines"] == 3 and "mismatch" in v["reason"]


def test_truncation_below_anchor_is_detected():
    _seed_ledger(4)
    pa_ledger.append_anchor(note="unit")
    path = pa_ledger.ledger_path()
    with open(path, "rb") as f:
        lines = f.read().split(b"\n")
    with open(path, "wb") as f:                     # keep only 2 lines
        f.write(b"\n".join(lines[:2]) + b"\n")
    ok, v = pa_ledger.verify_against_anchors()
    assert not ok and "holds 2 lines" in v["reason"]


def test_earliest_violated_anchor_is_reported():
    _seed_ledger(2)
    pa_ledger.append_anchor(note="first")           # anchor #0, n_lines=2
    _seed_ledger(2)
    pa_ledger.append_anchor(note="second")          # anchor #1, n_lines=4
    _tamper_line(pa_ledger.ledger_path(), 0, b'"n":0', b'"n":7')
    ok, v = pa_ledger.verify_against_anchors()
    assert not ok and v["index"] == 0 and v["n_lines"] == 2


def test_degenerate_and_missing_anchors_fail_closed():
    _seed_ledger(2)
    ap = pa_ledger.anchors_path()
    os.makedirs(os.path.dirname(ap), exist_ok=True)
    with open(ap, "w", encoding="utf-8") as f:      # forged n_lines=0 anchor
        f.write(json.dumps({"kind": "ledger_anchor", "n_lines": 0,
                            "sha256": "e3b0c44298fc1c149afbf4c8996fb924"
                                      "27ae41e4649b934ca495991b7852b855"}) + "\n")
    ok, v = pa_ledger.verify_against_anchors()
    assert not ok and "protects nothing" in v["reason"]

    os.unlink(ap)
    ok, v = pa_ledger.verify_against_anchors()
    assert not ok and "no anchors file" in v["reason"]


def test_real_repo_ledger_is_anchored():
    """The deployment lock: the real ledger must carry anchors that verify."""
    real = os.path.join(PA_PRO, "ledger", "TRIALS.jsonl")
    ap = os.path.join(PA_PRO, "ledger", "ANCHORS.jsonl")
    assert os.path.exists(ap), "ledger/ANCHORS.jsonl missing: nothing deployed"
    ok, v = pa_ledger.verify_against_anchors(path=real, anchors_file=ap)
    assert ok, v
    with open(ap, encoding="utf-8") as f:
        first = json.loads(f.read().splitlines()[0])
    assert "nothing before this line" in (first.get("note") or "").lower(), \
        "first retro-anchor must state the pre-anchor history is unprotected"


# --- 3. data_sha256 covers every result-deciding field ----------------------

def _provider_all_fields():
    m1, bars = make_synthetic_market(seed=31, days=2)
    d = synth_provider(m1, bars)
    d["utc_end"] = int(bars["t"][-1]) + 300
    return d


def _copy_provider(d):
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out[k] = dict(v)
        elif hasattr(v, "dtype"):
            out[k] = v.copy()
        else:
            out[k] = v
    return out


def _perturb(d, group, key):
    d2 = _copy_provider(d)
    target = d2 if group == "" else d2[group]
    v = target.get(key)
    if v is None:
        target[key] = [1, 2, 3]
    elif isinstance(v, dict):
        first = sorted(v)[0]
        arr = np.asarray(v[first])
        target[key] = dict(v)
        target[key][first] = ~arr if arr.dtype == bool else arr + 1
    elif hasattr(v, "dtype"):
        target[key] = ~v if v.dtype == bool else v + 1
    elif isinstance(v, (list, tuple)):
        target[key] = list(v) + [1]
    elif isinstance(v, bool):
        target[key] = not v
    elif isinstance(v, (int, float)):
        target[key] = v + 1
    else:
        target[key] = str(v) + "X"
    return d2


def test_data_sha256_covers_every_listed_field():
    d = _provider_all_fields()
    base = pa_eval._provider_data_sha256(d)
    for group, key in pa_eval._DATA_SHA_FIELDS:
        d2 = _perturb(d, group, key)
        assert pa_eval._provider_data_sha256(d2) != base, \
            f"data_sha256 does not cover {group or '<top>'}.{key}"


def test_frozen_field_list_contains_the_red_team_fields():
    required = {("", "pip"), ("", "starts"), ("", "m5_t"), ("", "next_end"),
                ("", "sess_mask"), ("", "first_live_idx"), ("", "c_rt_pips"),
                ("m5", "o"), ("bars", "utc_min"), ("bars", "dow")}
    assert required <= set(pa_eval._DATA_SHA_FIELDS)


def test_provider_cannot_assert_data_sha256():
    m1, bars = make_synthetic_market(seed=33, days=2)
    d = synth_provider(m1, bars)
    d["data_sha256"] = "f" * 64
    base = pa_eval._provider_data_sha256(d)
    d_without = dict(d)
    del d_without["data_sha256"]
    assert base == pa_eval._provider_data_sha256(d_without)

    def provider(symbol, split, tf):
        return d

    def entries_fn(symbol, bars_, spec):
        return [{"sig": 100, "side": +1, "tag": 0}]

    spec = {"family": "R02F_ASSERT", "entries_fn": entries_fn, "legacy_flats": True}
    res = pa_eval.evaluate(spec, "DESIGN", ["SYNX"], "M5", ["gross"],
                           round_name="R02", data_provider=provider)
    line = pa_ledger.read_lines()[-1]
    assert line["data_sha256"] != "f" * 64
    assert line["data_sha256"] == res["data_sha256"]
    assert line["data_sha256"] == pa_eval._combine_data_sha256({"SYNX": base})
