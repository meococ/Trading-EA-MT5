from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "02. AlphaFactory" / "tools" / "backtest_storage_inventory.py"
SPEC = importlib.util.spec_from_file_location("backtest_storage_inventory", MODULE_PATH)
assert SPEC and SPEC.loader
inventory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory)


def test_inventory_counts_orphans_and_potential_mirrors(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    primary = runs / "EA_Test" / "RUN-1" / "logs" / "events.csv"
    mirror = runs / "EA_Test" / "RUN-1" / "analysis" / "logs" / "events.csv"
    orphan = runs / "EA_Test" / "features_EURUSD.csv"
    primary.parent.mkdir(parents=True)
    mirror.parent.mkdir(parents=True)
    payload = b"header\nrow\n"
    primary.write_bytes(payload)
    mirror.write_bytes(payload)
    orphan.write_bytes(b"orphan-data")

    result = inventory.scan_storage(runs, top_n=10)
    assert result["total_file_count"] == 3
    assert result["total_size_bytes"] == len(payload) * 2 + len(b"orphan-data")
    assert result["direct_orphan_file_count"] == 1
    assert result["direct_orphan_size_bytes"] == len(b"orphan-data")
    assert result["potential_mirror_pair_count"] == 1
    assert result["potential_mirror_reclaimable_bytes"] == len(payload)
    assert result["potential_mirrors"][0]["status"] == "size_match_requires_sha256_dedupe_tool"
    assert result["already_hardlinked_mirror_pair_count"] == 0
    assert result["estimated_physical_size_bytes"] == result["total_size_bytes"]


def test_inventory_excludes_existing_hardlink_from_reclaimable_bytes(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    primary = runs / "EA_Test" / "RUN-1" / "logs" / "events.csv"
    mirror = runs / "EA_Test" / "RUN-1" / "analysis" / "logs" / "events.csv"
    primary.parent.mkdir(parents=True)
    mirror.parent.mkdir(parents=True)
    payload = b"header\nrow\n"
    primary.write_bytes(payload)
    mirror.hardlink_to(primary)

    result = inventory.scan_storage(runs, top_n=10)
    assert result["potential_mirror_pair_count"] == 0
    assert result["potential_mirror_reclaimable_bytes"] == 0
    assert result["already_hardlinked_mirror_pair_count"] == 1
    assert result["already_hardlinked_mirror_logical_bytes"] == len(payload)
    assert result["estimated_physical_size_bytes"] == len(payload)


def test_cli_writes_compact_json(tmp_path: Path, capsys) -> None:
    runs = tmp_path / "runs"
    runs.mkdir()
    (runs / "root.txt").write_text("x", encoding="utf-8")
    output = tmp_path / "inventory.json"
    assert inventory.main(["--runs-root", str(runs), "--out", str(output), "--top", "5"]) == 0
    assert capsys.readouterr().out.startswith("BACKTEST_STORAGE_INVENTORY_CREATED")
    parsed = json.loads(output.read_text(encoding="utf-8"))
    assert parsed["schema_version"] == inventory.SCHEMA
    assert parsed["total_file_count"] == 1
