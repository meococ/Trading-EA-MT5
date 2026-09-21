"""R02-A F5: the freeze-ordering guard is real (not just documented)."""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PHYS = os.path.dirname(HERE)
if PHYS not in sys.path:
    sys.path.insert(0, PHYS)

import phys_analysis as pa  # noqa: E402

OLD = 1_600_000_000.0
NEW = 1_700_000_000.0


def _touch(path, ts):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("{}")
    os.utime(path, (ts, ts))


def test_freeze_must_exist(tmp_path, monkeypatch):
    freeze = str(tmp_path / "FREEZE.json")
    monkeypatch.setattr(pa, "FREEZE", freeze)
    ok, why = pa._freeze_ok(tables=[])
    assert not ok and "missing" in why


def test_table_newer_than_freeze_refused(tmp_path, monkeypatch):
    freeze = str(tmp_path / "FREEZE.json")
    table = str(tmp_path / "EVENTS_X.csv")
    _touch(freeze, OLD)
    _touch(table, NEW)
    monkeypatch.setattr(pa, "FREEZE", freeze)
    ok, why = pa._freeze_ok(tables=[table])
    assert not ok and "newer than" in why
    ok2, why2 = pa._freeze_ok()          # production shape with monkeypatched OUT
    monkeypatch.setattr(pa, "OUT", str(tmp_path))
    ok2, why2 = pa._freeze_ok()
    assert not ok2 and "newer than" in why2


def test_freeze_before_tables_ok(tmp_path, monkeypatch):
    freeze = str(tmp_path / "FREEZE.json")
    table = str(tmp_path / "CONTROLS_X.csv")
    _touch(freeze, NEW)
    _touch(table, OLD)
    monkeypatch.setattr(pa, "FREEZE", freeze)
    ok, why = pa._freeze_ok(tables=[table])
    assert ok and why is None
