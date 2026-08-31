import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "runs_db.py"
SPEC = importlib.util.spec_from_file_location("alphafactory_runs_db", MODULE_PATH)
runs_db = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(runs_db)


def _write_summary(run_dir: Path, *, bom: bool = False, net_profit: float = 1.0):
    analysis_dir = run_dir / "analysis"
    analysis_dir.mkdir(parents=True)
    payload = (
        '{"n_trades": 10, "net_profit": %s, "profit_factor": 1.5, '
        '"win_rate_pct": 50, "start_equity": 10000, "final_equity": 10001}'
        % net_profit
    )
    (analysis_dir / "enhanced_summary.json").write_text(
        payload,
        encoding="utf-8-sig" if bom else "utf-8",
    )


def test_load_json_accepts_utf8_bom(tmp_path):
    path = tmp_path / "summary.json"
    path.write_text('{"ok": true}', encoding="utf-8-sig")

    assert runs_db.load_json(path) == {"ok": True}


def test_build_preserves_duplicate_timestamps_across_eas(tmp_path):
    runs_root = tmp_path / "runs"
    run_id = "20260621_170259"
    _write_summary(runs_root / "EA_A" / run_id, bom=True, net_profit=10)
    _write_summary(runs_root / "EA_B" / run_id, net_profit=20)

    with runs_db.RunsDB(tmp_path / "runs.db") as db:
        inserted, skipped, errors = db.build(runs_root)
        rows = db.query_raw(
            "SELECT ea_name, run_id, net_profit FROM runs ORDER BY ea_name"
        )

    assert (inserted, skipped, errors) == (2, 0, 0)
    assert [(row["ea_name"], row["run_id"]) for row in rows] == [
        ("EA_A", run_id),
        ("EA_B", run_id),
    ]


def test_unqualified_duplicate_reference_fails_closed(tmp_path):
    runs_root = tmp_path / "runs"
    run_id = "20260621_170259"
    _write_summary(runs_root / "EA_A" / run_id)
    _write_summary(runs_root / "EA_B" / run_id)

    with runs_db.RunsDB(tmp_path / "runs.db") as db:
        db.build(runs_root)
        with pytest.raises(ValueError, match="Ambiguous run reference"):
            db.get_run(run_id)


def test_qualified_reference_resolves_duplicate_timestamp(tmp_path):
    runs_root = tmp_path / "runs"
    run_id = "20260621_170259"
    _write_summary(runs_root / "EA_A" / run_id, net_profit=10)
    _write_summary(runs_root / "EA_B" / run_id, net_profit=20)

    with runs_db.RunsDB(tmp_path / "runs.db") as db:
        db.build(runs_root)
        row = db.get_run(f"EA_B/{run_id}")

    assert row is not None
    assert row["ea_name"] == "EA_B"
    assert row["net_profit"] == 20
