"""Synthetic tests for HYP-G10-XMOM-W1-002 train W1 exporter.

No real MT5, runtime, registry, or production dataset access.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import importlib.util
import pytest

SOURCE = Path(__file__).resolve().parents[1] / "export_g10_xmom_002_train_w1.py"
SPEC = importlib.util.spec_from_file_location("export_g10_xmom_002_train_w1", SOURCE)
assert SPEC and SPEC.loader
sut = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sut)


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")


def week_epoch(year: int, month: int, day: int) -> int:
    return int(datetime(year, month, day, tzinfo=timezone.utc).timestamp())


def synthetic_rows(*, years: tuple[int, ...] = sut.TRAIN_YEARS) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    # One deterministic W1-like bar per symbol per train year (synthetic only).
    for year in years:
        epoch = week_epoch(year, 6, 3)
        for index, symbol in enumerate(sut.SYMBOLS):
            base = 1.0 + 0.01 * index + 0.001 * (year - 2018)
            rows.append(
                {
                    "symbol": symbol,
                    "time_epoch": epoch + index,  # unique per symbol for schema tests
                    "time_server": datetime.fromtimestamp(
                        epoch + index, tz=timezone.utc
                    ).strftime("%Y-%m-%dT%H:%M:%S"),
                    "open": base,
                    "high": base + 0.01,
                    "low": base - 0.01,
                    "close": base + 0.005,
                    "tick_volume": 1000 + index,
                    "spread": 10 + index,
                    "broker_server": sut.EXPECTED_SERVER,
                }
            )
    return rows


@pytest.fixture()
def d_tmp(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Prefer a D-side temp root when available for exclusive-path checks."""

    base = Path(r"D:\Trading EA MT5\02. AlphaFactory\scratch\grok\g10_xmom_export_tests")
    try:
        base.mkdir(parents=True, exist_ok=True)
        root = base / f"t-{os.getpid()}-{os.urandom(4).hex()}"
        root.mkdir(parents=False, exist_ok=False)
    except Exception:
        root = tmp_path_factory.mktemp("g10_export")
    yield root
    # Best-effort cleanup
    try:
        for path in sorted(root.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        root.rmdir()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Import inert / sentinel / AST
# ---------------------------------------------------------------------------


def test_sentinel_is_exactly_disarmed_and_import_inert() -> None:
    assert sut.REVIEWED_REGISTRY_ROW_SHA256 is None
    text = SOURCE.read_bytes()
    assert b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None" in text
    matches = [line for line in text.splitlines() if sut._SENTINEL_RE.match(line.rstrip(b"\n"))]
    assert len(matches) == 1


def test_ast_forbids_toplevel_metatrader_and_network() -> None:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "MetaTrader5"
                assert not alias.name.startswith("MetaTrader5")
                assert alias.name.split(".")[0] not in {
                    "requests",
                    "httpx",
                    "urllib",
                    "socket",
                }
        if isinstance(node, ast.ImportFrom):
            assert node.module != "MetaTrader5"
            if node.module:
                assert node.module.split(".")[0] not in {
                    "requests",
                    "httpx",
                    "urllib",
                    "socket",
                }
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"exec", "eval", "compile"}


def test_lazy_metatrader_import_is_function_local() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    assert "def _lazy_import_metatrader5" in text
    assert 'import_module("MetaTrader5")' in text
    # No static import statement for the terminal package.
    assert not re.search(r"(?m)^\s*import\s+MetaTrader5\b", text)
    assert not re.search(r"(?m)^\s*from\s+MetaTrader5\b", text)
    # AST must not include MetaTrader5 import nodes anywhere.
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] != "MetaTrader5"
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] != "MetaTrader5"


def test_default_main_path_is_disarmed() -> None:
    with pytest.raises(sut.ContractError, match="disarmed|--production"):
        sut.run_production(workspace_root=Path.cwd(), production=False)
    with pytest.raises(sut.ContractError, match="disarmed|sentinel"):
        sut.run_production(workspace_root=Path.cwd(), production=True)


# ---------------------------------------------------------------------------
# Sentinel normalization / hashes
# ---------------------------------------------------------------------------


def test_sentinel_normalization_helper() -> None:
    payload = SOURCE.read_bytes()
    base = sut.normalized_exporter_base_sha256(payload)
    assert base == sut.normalized_base_sha256(payload)
    armed = payload.replace(
        b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None",
        b'REVIEWED_REGISTRY_ROW_SHA256: str | None = "' + b"A" * 64 + b'"',
        1,
    )
    assert sut.normalized_exporter_base_sha256(armed) == base


def test_plan_and_parent_bindings_are_frozen() -> None:
    assert sut.PLAN_SHA256 == (
        "ABA4C2BA7AFBA07DE7C38A709E00275507ADFCEE035F17E70896B3FF8A74351C"
    )
    assert sut.PARENT_INVENTORY_SHA256 == (
        "DCF3754D4B95EFBA2B25A8455CF6DCDF5169C409CE81FE3568F5C7227C98FE01"
    )
    assert sut.PARENT_TERMINAL_SHA256 == (
        "3FF657763271E77E61DA8110FAE1260710AD9733B2F2B14D613A3AAAB8CEC48F"
    )
    assert sut.TRAIN_YEARS == (2018, 2019, 2020, 2021)
    assert sut.HOLDOUT_YEARS_SEALED == (2022, 2023, 2024)


def test_hard_zero_outcome_counters() -> None:
    counters = sut.hard_zero_outcome_counters()
    assert counters["ranks_computed"] == 0
    assert counters["returns_computed"] == 0
    assert counters["signals_generated"] == 0
    assert counters["trades_simulated"] == 0
    assert counters["costs_computed"] == 0
    assert counters["economics_executed"] is False
    assert counters["holdout_bars_exported"] == 0


# ---------------------------------------------------------------------------
# Split / holdout rejection / geometry
# ---------------------------------------------------------------------------


def test_exact_split_and_holdout_rejection() -> None:
    for year in sut.TRAIN_YEARS:
        sut.assert_train_year_only(year)
    for year in (2017, 2022, 2023, 2024, 2025):
        with pytest.raises(sut.ContractError):
            sut.assert_train_year_only(year)
    # Returned bar year checks
    good = week_epoch(2019, 3, 4)
    assert sut.reject_returned_bar_year(good, symbol="EURUSD") == 2019
    bad = week_epoch(2022, 1, 3)
    with pytest.raises(sut.ContractError, match="returned_bar_year_rejected"):
        sut.reject_returned_bar_year(bad, symbol="EURUSD")
    pre = week_epoch(2017, 6, 5)
    with pytest.raises(sut.ContractError, match="returned_bar_year_rejected"):
        sut.reject_returned_bar_year(pre, symbol="EURUSD")


def test_symbol_pip_geometry() -> None:
    sut.validate_symbol_pip_geometry("EURUSD", 5, 0.00001)
    sut.validate_symbol_pip_geometry("USDJPY", 3, 0.001)
    with pytest.raises(sut.ContractError, match="pip|digits"):
        sut.validate_symbol_pip_geometry("EURUSD", 4, 0.0001)
    with pytest.raises(sut.ContractError, match="unmapped"):
        sut.validate_symbol_pip_geometry("XAUUSD", 2, 0.01)


def test_d_side_path_gate(tmp_path: Path) -> None:
    # On Windows, tmp_path may be on C:. require_d_side_path must reject non-D.
    if tmp_path.drive.upper() != "D:":
        with pytest.raises(sut.ContractError, match="D:"):
            sut.require_d_side_path(tmp_path, label="tmp")
    else:
        sut.require_d_side_path(tmp_path, label="tmp")


# ---------------------------------------------------------------------------
# Schema / hash / atomic controls
# ---------------------------------------------------------------------------


def test_manifest_schema_and_hard_zero(d_tmp: Path) -> None:
    if d_tmp.drive.upper() != "D:":
        pytest.skip("D-side temp root unavailable for exclusive path publish test")
    rows = synthetic_rows()
    published = sut.atomic_publish_parquet_and_manifest(
        dataset_root=d_tmp / "dataset",
        rows=rows,
        terminal_metadata={"portable": True, "server": sut.EXPECTED_SERVER},
    )
    manifest_path = Path(published["manifest_path"])
    body = manifest_path.read_bytes()
    assert body.endswith(b"\n")
    assert body.count(b"\n") == 1
    manifest = json.loads(body)
    assert canonical(manifest) + b"\n" == body
    assert manifest["plan_sha256"] == sut.PLAN_SHA256
    assert manifest["parent_inventory_sha256"] == sut.PARENT_INVENTORY_SHA256
    assert manifest["parent_terminal_sha256"] == sut.PARENT_TERMINAL_SHA256
    assert manifest["schema"] == list(sut.SCHEMA_COLUMNS)
    assert manifest["years"] == list(sut.TRAIN_YEARS)
    assert set(manifest["symbols"]) == set(sut.SYMBOLS)
    assert manifest["ranks_computed"] == 0
    assert manifest["returns_computed"] == 0
    assert manifest["signals_generated"] == 0
    assert manifest["economics_executed"] is False
    assert published["parquet_sha256"] == sha(Path(published["parquet_path"]).read_bytes())
    # Exclusive: second publish must fail.
    with pytest.raises(sut.ContractError, match="already exists|exclusive"):
        sut.atomic_publish_parquet_and_manifest(
            dataset_root=d_tmp / "dataset",
            rows=rows,
            terminal_metadata={"portable": True, "server": sut.EXPECTED_SERVER},
        )


def test_rows_reject_holdout_year_payload() -> None:
    rows = synthetic_rows(years=(2018, 2022))
    with pytest.raises(sut.ContractError, match="returned_bar_year_rejected|year"):
        sut.rows_to_dataframe(rows)


def test_rows_require_exact_symbol_year_coverage_and_unique_keys() -> None:
    rows = synthetic_rows()
    frame = sut.rows_to_dataframe(rows)
    assert len(frame) == len(rows)

    duplicate = list(rows) + [dict(rows[0])]
    with pytest.raises(sut.ContractError, match="duplicate"):
        sut.rows_to_dataframe(duplicate)

    missing_symbol_year = [
        row
        for row in rows
        if not (row["symbol"] == "AUDUSD" and datetime.fromtimestamp(
            int(row["time_epoch"]), tz=timezone.utc
        ).year == 2020)
    ]
    with pytest.raises(sut.ContractError, match="coverage"):
        sut.rows_to_dataframe(missing_symbol_year)


def test_manifest_rejects_partial_train_years() -> None:
    with pytest.raises(sut.ContractError, match="exact train years"):
        sut.build_manifest(
            dataset_rel="x",
            parquet_rel="x/train.parquet",
            parquet_sha256="A" * 64,
            row_count=7,
            symbols=sut.SYMBOLS,
            years=(2018,),
            first_bar=None,
            last_bar=None,
            terminal_metadata={},
            plan_sha256=sut.PLAN_SHA256,
            parent_inventory_sha256=sut.PARENT_INVENTORY_SHA256,
            parent_terminal_sha256=sut.PARENT_TERMINAL_SHA256,
            schema=sut.SCHEMA_COLUMNS,
        )


def test_canonical_json_rejects_nan() -> None:
    with pytest.raises(sut.ContractError):
        sut.canonical_json({"x": float("nan")})


# ---------------------------------------------------------------------------
# Registry authority surface
# ---------------------------------------------------------------------------


def test_registry_authority_validation_surface() -> None:
    exporter_payload = SOURCE.read_bytes()
    base_sha = sut.normalized_exporter_base_sha256(exporter_payload)
    test_sha = sha(Path(__file__).read_bytes())
    receipt_sha = sha(b'{"schema_version":"test-review-receipt.v1","status":"PASS"}\n')
    row = {
        "record_type": "hypothesis_state",
        "schema_version": "alphafactory_candidate_registry.v1",
        "hypothesis_id": sut.HYPOTHESIS_ID,
        "ea_name": sut.EA_NAME,
        "state": "probe",
        "prereg_path": sut.PLAN_REL,
        "prereg_sha256": sut.PLAN_SHA256,
        "validation": {
            "train_export_authorized": True,
            "train_acquisition_authorized": True,
            "mt5_authorized": True,
            "holdout_access_authorized": False,
            "economics_authorized": False,
            "one_use": True,
            "reviewed_exporter_path": sut.EXPORTER_REL,
            "reviewed_exporter_base_sha256": base_sha,
            "reviewed_test_path": sut.TEST_REL,
            "reviewed_test_sha256": test_sha,
            "independent_review_receipt_path": sut.REVIEW_RECEIPT_REL,
            "independent_review_receipt_sha256": receipt_sha,
            "parent_inventory_sha256": sut.PARENT_INVENTORY_SHA256,
            "parent_terminal_sha256": sut.PARENT_TERMINAL_SHA256,
        },
    }
    payload = canonical(row) + b"\n"
    latest_sha = sha(payload)
    accepted = sut.validate_production_registry_authority(payload, latest_sha)
    assert accepted["hypothesis_id"] == sut.HYPOTHESIS_ID

    # Wrong one-use / holdout flags fail closed.
    bad = json.loads(payload)
    bad["validation"]["holdout_access_authorized"] = True
    bad_payload = canonical(bad) + b"\n"
    with pytest.raises(sut.ContractError):
        sut.validate_production_registry_authority(bad_payload, sha(bad_payload))

    with pytest.raises(sut.ContractError, match="sentinel|latest row"):
        sut.validate_production_registry_authority(payload, "A" * 64)


def test_cli_parse_production_flag() -> None:
    args = sut.parse_args(["--production", "--workspace-root", "."])
    assert args.production is True


def test_no_self_referential_embedded_exporter_hash() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    own = sha(SOURCE.read_bytes())
    assert own not in text
    assert "EXPORTER_SHA256" not in text
    assert "SELF_SHA" not in text
