from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "generate_dolui_train_table.py"
SPEC = importlib.util.spec_from_file_location("generate_dolui_train_table", SOURCE)
assert SPEC and SPEC.loader
sut = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sut
SPEC.loader.exec_module(sut)


def test_ceil_next_hour_is_strict_for_release_clock() -> None:
    release = datetime(2022, 6, 9, 15, 30)
    assert sut.ceil_next_hour(release) == datetime(2022, 6, 9, 16, 0)


def test_frozen_train_source_generates_exact_causal_table() -> None:
    rows = sut.load_rows()
    assert len(rows) == 260
    assert sum(int(row["direction"]) > 0 for row in rows) == 101
    assert sum(int(row["direction"]) < 0 for row in rows) == 157
    assert sum(int(row["direction"]) == 0 for row in rows) == 2
    assert sum(int(row["availability"]) == 0 for row in rows) == 2
    assert all(int(row["release_server"]) + 1800 == int(row["decision_open"]) for row in rows)
    assert all(int(row["entry_target"]) + 14400 == int(row["exit_target"]) for row in rows)
    assert sut.sha256_bytes(sut.canonical_table(rows)) == "20377DAA5449E0C10D67620768FA127B8FAEF5F49DDC802AF78DD8848F8C5A05"


def test_render_embeds_source_and_table_hashes() -> None:
    rows = sut.load_rows()
    rendered = sut.render(rows)
    assert sut.EXPECTED_SOURCE_SHA256 in rendered
    assert "AF_DOLUI_EVENT_COUNT 260" in rendered
    assert sut.sha256_bytes(sut.canonical_table(rows)) in rendered
