"""R02-A F9: the ledger's LAST line is covered by a sidecar tail hash."""

import os

import pa_ledger


def test_last_line_tamper_detected(tmp_path):
    path = str(tmp_path / "TRIALS.jsonl")
    pa_ledger.set_ledger_path(path)
    for i in range(3):
        pa_ledger.append({"family": "T", "split": "DESIGN", "n": i})
    assert os.path.exists(path + ".tail")
    ok, idx = pa_ledger.verify()
    assert ok and idx is None

    with open(path, "rb") as f:
        lines = f.read().split(b"\n")[:-1]
    assert b'"n":2' in lines[2]
    tampered = lines[2].replace(b'"n":2', b'"n":9')   # JSON stays valid
    with open(path, "wb") as f:
        f.write(b"\n".join([lines[0], lines[1], tampered]) + b"\n")
    ok, idx = pa_ledger.verify()
    assert not ok and idx == 2


def test_missing_sidecar_refused_never_bootstraps(tmp_path):
    """R02-C (b): a missing `.tail` is an ERROR on a non-empty ledger.

    The pre-R02-C code bootstrapped the sidecar from the current last line,
    which blessed a tampered/deleted history (red-team L4/L5 laundering).
    """
    path = str(tmp_path / "TRIALS.jsonl")
    pa_ledger.set_ledger_path(path)
    for i in range(3):
        pa_ledger.append({"family": "T", "split": "DESIGN", "n": i})
    os.unlink(path + ".tail")
    ok, idx = pa_ledger.verify()
    assert not ok and idx == 2            # last line is the unverifiable one
    assert not os.path.exists(path + ".tail")   # verify() never writes it back
    ok, idx = pa_ledger.verify()
    assert not ok and idx == 2            # deterministic, not one-shot


def test_append_updates_sidecar(tmp_path):
    path = str(tmp_path / "TRIALS.jsonl")
    pa_ledger.set_ledger_path(path)
    pa_ledger.append({"family": "T", "n": 0})
    with open(path + ".tail", "r", encoding="ascii") as f:
        first = f.read().strip()
    pa_ledger.append({"family": "T", "n": 1})
    with open(path + ".tail", "r", encoding="ascii") as f:
        second = f.read().strip()
    assert first != second
    ok, idx = pa_ledger.verify()
    assert ok and idx is None
