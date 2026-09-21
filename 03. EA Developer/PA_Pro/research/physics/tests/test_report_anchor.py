"""R02-C/R02-F: the freeze writer and the results/report writer emit the ledger
anchor (``sha256`` of the ledger prefix + ``n_lines``) into their artifacts AND
record it in ``ledger/ANCHORS.jsonl``.

These tests exercise the production writers' real code paths: the FREEZE.json
written here goes to a tmp round directory, and the results artifact to a tmp
round directory; the real R01 frozen artifacts are only READ (as inputs) and
never rewritten.  The ledger itself is redirected to a tmp path so a test run
never writes to the program ledger or its anchors file.
"""

import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PHYS = os.path.dirname(HERE)
PA_PRO = os.path.dirname(os.path.dirname(PHYS))
LIB = os.path.join(PA_PRO, "lib")
for _p in (PHYS, LIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pa_ledger            # noqa: E402
import phys_analysis as pa  # noqa: E402
import phys_freeze as pf    # noqa: E402


def _last_anchor_record():
    with open(pa_ledger.anchors_path(), "r", encoding="utf-8") as f:
        return json.loads(f.read().strip().splitlines()[-1])


def test_freeze_writer_embeds_ledger_anchor(tmp_path, monkeypatch):
    old = pa_ledger.set_ledger_path(str(tmp_path / "ledger" / "TRIALS.jsonl"))
    try:
        for i in range(2):                      # a non-empty head to anchor
            pa_ledger.append({"family": "T", "n": i})
        rounds_tmp = tmp_path / "R01"
        rounds_tmp.mkdir()
        for name in ("PHYSICS_PREREG.md", "00_LEAD_RULINGS_READ_FIRST.md",
                     "PARITY.md"):
            shutil.copy(os.path.join(pf.ROUNDS, name), str(rounds_tmp / name))
        out = tmp_path / "bakeoff"
        out.mkdir()
        monkeypatch.setattr(pf, "ROUNDS", str(rounds_tmp))
        monkeypatch.setattr(pf, "OUT", str(out))

        pf.main()

        with open(rounds_tmp / "FREEZE.json", "r", encoding="utf-8") as f:
            free = json.load(f)
        a = free["ledger_anchor"]
        assert a["n_lines"] == 2
        ok, why = pa_ledger.check_anchor(a)
        assert ok, why
        ok, v = pa_ledger.verify_against_anchors()
        assert ok, v
        rec = _last_anchor_record()
        assert (rec["n_lines"], rec["sha256"]) == (a["n_lines"], a["sha256"])
    finally:
        pa_ledger.set_ledger_path(old)


def test_scratch_never_changes_a_bundle_hash(tmp_path):
    """R02-D: ``_``-prefixed audit scratch is excluded from code bundles."""
    import phys_common as pc

    d = tmp_path / "bundle"
    d.mkdir()
    (d / "a.py").write_text("A", encoding="utf-8")
    h1 = pc.dir_code_sha256(str(d))
    (d / "_probe.py").write_text("PROBE", encoding="utf-8")
    (d / "_diag").mkdir()
    (d / "_diag" / "r01d1_diag.py").write_text("D", encoding="utf-8")
    assert pc.dir_code_sha256(str(d)) == h1
    (d / "b.py").write_text("B", encoding="utf-8")
    assert pc.dir_code_sha256(str(d)) != h1


def test_results_writer_embeds_ledger_anchor(tmp_path, monkeypatch):
    old = pa_ledger.set_ledger_path(str(tmp_path / "ledger" / "TRIALS.jsonl"))
    try:
        pa_ledger.append({"family": "T", "n": 0})
        monkeypatch.setattr(pa, "ROUNDS", str(tmp_path))
        freeze = {"split": "DESIGN", "tf": "M5", "prereg_sha256": "0" * 64,
                  "addendum2_sha256": "1" * 64, "physics_code_sha256": "2" * 64,
                  "zones_code_sha256": "3" * 64, "freeze_sha256": "4" * 64}
        summary = {"_winner": {"ranked": [], "passes": [], "winner": None,
                               "baseline": "line1_cluster"}}

        pa._write_results_md([], summary, freeze, [])

        text = (tmp_path / "PHYSICS_RESULTS.md").read_text(encoding="utf-8")
        rec = _last_anchor_record()
        assert "Ledger anchor" in text
        assert rec["sha256"] in text
        assert f"n_lines = {rec['n_lines']}" in text
        ok, v = pa_ledger.verify_against_anchors()
        assert ok, v
    finally:
        pa_ledger.set_ledger_path(old)
