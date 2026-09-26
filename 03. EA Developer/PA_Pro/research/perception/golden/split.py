"""P1.6 — split the golden catalogue into TUNE / HOLD and hash HOLD.

TUNE = casebook sessions 2012-03-01 .. 2012-05-31 (Mar-May).
HOLD = 2012-06-01 .. 2012-08-31 (Jun-Aug).  HOLD's file sha256 goes into
the project ledger with kind ``perception_golden``; HOLD must not be
scored until the Lead authorizes it.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(
    os.path.join(HERE, "..", "..", "..", "lib")))
import pa_ledger  # noqa: E402

SRC = os.path.join(HERE, "BOOK2012.jsonl")
TUNE_OUT = os.path.join(HERE, "BOOK2012_TUNE.jsonl")
HOLD_OUT = os.path.join(HERE, "BOOK2012_HOLD.jsonl")
HOLD_LO = "2012-06-01"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    recs = [json.loads(l) for l in open(SRC, encoding="utf8")]
    tune = [r for r in recs if r["date"] < HOLD_LO]
    hold = [r for r in recs if r["date"] >= HOLD_LO]
    with open(TUNE_OUT, "w", encoding="utf8") as f:
        for r in tune:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    with open(HOLD_OUT, "w", encoding="utf8") as f:
        for r in hold:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    hold_sha = sha256_file(HOLD_OUT)
    tune_sha = sha256_file(TUNE_OUT)
    tid = pa_ledger.append({
        "kind": "perception_golden",
        "note": "P1.6 golden split: HOLD hashed, NOT scored (Lead auth "
                "required). TUNE hash recorded for provenance.",
        "hold_file": os.path.basename(HOLD_OUT),
        "hold_sha256": hold_sha,
        "hold_panels": len(hold),
        "tune_file": os.path.basename(TUNE_OUT),
        "tune_sha256": tune_sha,
        "tune_panels": len(tune),
        "split_rule": "TUNE date < 2012-06-01 <= HOLD",
    })
    print("TUNE", len(tune), tune_sha[:16])
    print("HOLD", len(hold), hold_sha[:16], "-> ledger", tid)


if __name__ == "__main__":
    main()
