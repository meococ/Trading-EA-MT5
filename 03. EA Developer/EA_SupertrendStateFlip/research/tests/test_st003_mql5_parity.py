from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


RESEARCH = Path(__file__).resolve().parents[1]


def load(name: str, filename: str):
    path = RESEARCH / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILDER = load("build_st003_parity_oracle", "build_st003_parity_oracle.py")
COMPARATOR = load("compare_st003_mql5_parity", "compare_st003_mql5_parity.py")
MQL_PATH = RESEARCH.parent / "EA_SupertrendStateFlip.mq5"


def synthetic_source(rows: int = 40) -> pd.DataFrame:
    time_utc = pd.date_range("2018-01-01T00:00:00Z", periods=rows, freq="1h")
    server_epoch = (time_utc.view("int64") // 1_000_000_000 + 2 * 3600).astype("int64")
    price = np.r_[np.full(15, 100.0), np.linspace(100.0, 130.0, rows - 15)]
    return pd.DataFrame({
        "symbol": "XAUUSD", "timeframe": "H1", "source_epoch": server_epoch,
        "time_utc": time_utc, "utc_ambiguous": False,
        "high": price + 1.0, "low": price - 1.0, "close": price,
    })


def test_oracle_is_full_state_but_contains_no_raw_price_or_outcome() -> None:
    rows, report = BUILDER.build_oracle_rows(synthetic_source())
    assert rows
    assert set(rows[0]) == BUILDER.ORACLE_KEYS
    forbidden = {"open", "high", "low", "close", "return", "pnl", "profit_factor", "mfe", "mae"}
    assert not (set(rows[0]) & forbidden)
    assert report["returns_computed"] == report["trades_simulated"] == 0


def test_oracle_accepts_flat_bars_without_reset() -> None:
    source = synthetic_source()
    source.loc[9, ["high", "low"]] = source.at[9, "close"]
    source.loc[20, ["high", "low"]] = source.at[20, "close"]
    rows, _ = BUILDER.build_oracle_rows(source)
    assert rows
    assert all(row["state"] in {"UP", "DOWN"} for row in rows)


def test_clock_mapping_is_not_a_constant_offset_assumption() -> None:
    winter_server = datetime(2022, 1, 15, 12, 0)
    summer_server = datetime(2022, 7, 15, 12, 0)
    assert BUILDER.CLOCK.server_to_utc(winter_server) == datetime(2022, 1, 15, 10, 0)
    assert BUILDER.CLOCK.server_to_utc(summer_server) == datetime(2022, 7, 15, 9, 0)


def test_exact_next_uses_source_epoch_even_when_utc_delta_disagrees() -> None:
    current_epoch = 1_500_000_000
    current_utc = pd.Timestamp("2022-03-27T00:00:00Z")
    next_utc = current_utc + pd.Timedelta(hours=1)
    assert next_utc-current_utc == pd.Timedelta(hours=1)
    assert BUILDER.is_exact_next(current_epoch, current_epoch+7200) is False
    assert BUILDER.is_exact_next(current_epoch, current_epoch+3600) is True


def test_oracle_attempt_claim_is_exclusive(tmp_path: Path) -> None:
    authority = {"registry_sha256": "A" * 64, "latest_row_sha256": "B" * 64}
    _, marker = BUILDER.claim_attempt(tmp_path / "attempt", authority)
    assert marker.exists()
    with pytest.raises(ValueError, match="already exists"):
        BUILDER.claim_attempt(tmp_path / "attempt", authority)


def full_count_fixture() -> tuple[list[dict], list[dict[str, str]]]:
    oracle: list[dict] = []
    mql: list[dict[str, str]] = []
    server_start = datetime(2018, 1, 1, 2, 0, tzinfo=timezone.utc)
    for index in range(690):
        server_time = server_start + timedelta(hours=index)
        source_epoch = int(server_time.timestamp())
        utc = server_time - timedelta(hours=2)
        executable = index < 683
        direction = "LONG" if index < 339 else "SHORT" if index < 683 else "LONG"
        prior_state, state = ("DOWN", "UP") if direction == "LONG" else ("UP", "DOWN")
        expected = {
            "schema_version": "st003_source_parity_oracle.v1",
            "hypothesis_id": COMPARATOR.HYPOTHESIS_ID,
            "source_epoch": source_epoch,
            "time_utc": utc.isoformat().replace("+00:00", "Z"),
            "atr10": 10.0 + index / 1000.0,
            "final_upper": 2000.0 + index,
            "final_lower": 1900.0 + index,
            "supertrend": (1900.0 + index) if state == "UP" else (2000.0 + index),
            "prior_state": prior_state, "state": state, "raw_event": 1,
            "next_source_epoch": source_epoch + (3600 if executable else 7200),
            "exact_next": int(executable), "executable_event": int(executable),
            "direction": direction,
        }
        actual = {
            "schema_version": "st003_mql5_parity.v1",
            "hypothesis_id": COMPARATOR.HYPOTHESIS_ID,
            "audit_run_id": COMPARATOR.AUDIT_RUN_ID,
            "source_epoch": str(source_epoch),
            "time_server": server_time.strftime("%Y.%m.%d %H:%M:%S"),
            "atr10": format(expected["atr10"], ".17g"),
            "final_upper": format(expected["final_upper"], ".17g"),
            "final_lower": format(expected["final_lower"], ".17g"),
            "supertrend": format(expected["supertrend"], ".17g"),
            "prior_state": prior_state, "state": state, "raw_event": "1",
            "next_source_epoch": str(expected["next_source_epoch"]),
            "exact_next": str(expected["exact_next"]),
            "executable_event": str(expected["executable_event"]),
            "direction": direction,
        }
        oracle.append(expected)
        mql.append(actual)
    return oracle, mql


def test_comparator_enforces_every_row_and_frozen_counts() -> None:
    oracle, mql = full_count_fixture()
    report = COMPARATOR.compare_rows(oracle, mql)
    assert report["all_gates_pass"] is True
    assert report["executable_events"] == 683


def test_comparator_fails_on_single_numeric_deviation() -> None:
    oracle, mql = full_count_fixture()
    mql[400]["atr10"] = str(float(mql[400]["atr10"]) + 1e-4)
    with pytest.raises(ValueError, match="numeric parity mismatch"):
        COMPARATOR.compare_rows(oracle, mql)


def test_mql_source_is_audit_only_and_direct_formula() -> None:
    source = MQL_PATH.read_text(encoding="utf-8")
    for forbidden in ("CTrade", "OrderSend", ".Buy(", ".Sell(", "iATR(", "iCustom(", "NormalizeDouble("):
        assert forbidden not in source
    for required in (
        "InpAuditOnly", "CopyRates", "SOURCE_START_TIME", "9.0*g_atr+tr",
        "SameBandIdentity(g_supertrend,g_final_upper)", "iTime(_Symbol,PERIOD_H1,1)",
    ):
        assert required in source


def test_nonrepaint_audit_must_bind_exact_source_and_pass(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    audit = {
        "schema_version": "alphafactory_nonrepaint_audit.v1",
        "status": "PASS",
        "hypothesis_id": COMPARATOR.HYPOTHESIS_ID,
        "run_id": "ST003-MQL5-STATIC-001",
        "manifest_sha256": COMPARATOR.sha256_file(manifest),
        "collection_authority_verified": False,
        "audited_files": [{"path": str(MQL_PATH), "sha256": COMPARATOR.MQL_SOURCE_SHA256}],
        "findings": [],
    }
    path = tmp_path / "audit.json"
    path.write_text(json.dumps(audit), encoding="utf-8")
    COMPARATOR.validate_nonrepaint_audit(path, manifest)
    audit["status"] = "FAIL"
    path.write_text(json.dumps(audit), encoding="utf-8")
    with pytest.raises(ValueError, match="non-repaint audit"):
        COMPARATOR.validate_nonrepaint_audit(path, manifest)


def test_run_tree_hash_rejects_empty_directory(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="absent or empty"):
        COMPARATOR.tree_sha256(tmp_path)
