"""Ledger: chain verifies, middle-line tampering is detected, append is atomic."""

import hashlib
import json

import pa_ledger


def test_chain_verifies_and_middle_tamper_detected(tmp_path):
    path = str(tmp_path / "TRIALS.jsonl")
    pa_ledger.set_ledger_path(path)
    ids = [pa_ledger.append({"family": "T", "split": "DESIGN", "n": i})
           for i in range(3)]
    assert ids == ["T000001", "T000002", "T000003"]
    ok, idx = pa_ledger.verify()
    assert ok and idx is None

    # manual chain check: line i+1 stores sha256 of line i's raw bytes
    with open(path, "rb") as f:
        raw = f.read()
    lines = raw.split(b"\n")[:-1]
    assert len(lines) == 3
    assert json.loads(lines[0])["prev_line_sha256"] == "0" * 64
    for i in range(1, 3):
        assert json.loads(lines[i])["prev_line_sha256"] == \
            hashlib.sha256(lines[i - 1]).hexdigest()

    # tamper the middle line WITHOUT breaking its JSON: n=1 -> n=9
    assert b'"n":1' in lines[1]
    tampered = lines[1].replace(b'"n":1', b'"n":9')
    with open(path, "wb") as f:
        f.write(b"\n".join([lines[0], tampered, lines[2]]) + b"\n")
    ok, idx = pa_ledger.verify()
    assert not ok
    assert idx == 2                      # the link stored in line 2 is broken

    # appending after tampering cannot repair the chain
    pa_ledger.append({"family": "T", "split": "DESIGN", "n": 4})
    ok, idx = pa_ledger.verify()
    assert not ok and idx == 2
    assert len(pa_ledger.read_lines()) == 4
