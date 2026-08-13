import json
import importlib.util
from datetime import datetime
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "audit_calendar_pit_runtime.py"
SPEC = importlib.util.spec_from_file_location("audit_calendar_pit_runtime", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
audit = MODULE.audit


SAFE = {
    "outcome_accessed": False,
    "prices_read": False,
    "orders": False,
    "trading_disabled": True,
}


def prime_rows(ts_prefix: str = "2026.08.13 01:00") -> list[dict]:
    return [
        {
            "kind": "PRIME",
            "ts_local": f"{ts_prefix}:{index:02d}",
            "change_id": 123,
            "values_returned": 0,
            "currency_filter": currency,
            **SAFE,
        }
        for index, currency in enumerate(
            ("USD", "EUR", "JPY", "GBP", "CHF", "CAD", "AUD", "NZD"), start=1
        )
    ]


def write_runtime(root: Path, records: list[dict], state: str | None = None) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "calendar_pit.jsonl").write_text(
        "\n".join(json.dumps(row) for row in records) + "\n", encoding="utf-8"
    )
    if state is None:
        state = "rows=0\n" + "".join(
            f"{currency}_change_id=123\n{currency}_primed=1\n"
            for currency in ("USD", "EUR", "JPY", "GBP", "CHF", "CAD", "AUD", "NZD")
        )
    (root / "currency_state.txt").write_text(state, encoding="utf-8")


def test_valid_primed_runtime_passes(tmp_path: Path) -> None:
    write_runtime(
        tmp_path,
        [
            {"kind": "INIT", "ts_local": "2026.08.13 01:00:00", **SAFE},
            *prime_rows(),
            {"kind": "HEARTBEAT", "ts_local": "2026.08.13 01:01:00", **SAFE},
        ],
    )
    result = audit(tmp_path, now=datetime(2026, 8, 13, 1, 1, 10))
    assert result["status"] == "PASS"
    assert result["heartbeat_seen"] is True


def test_unsafe_or_non_target_value_fails(tmp_path: Path) -> None:
    write_runtime(
        tmp_path,
        [
            {"kind": "INIT", "ts_local": "2026.08.13 01:00:00", **SAFE},
            *prime_rows(),
            {
                "kind": "VALUE",
                "ts_local": "2026.08.13 01:00:02",
                "scope_status": "TARGET",
                "currency": "CNY",
                "payload_hash": "abc",
                **SAFE,
            },
        ],
    )
    result = audit(tmp_path, now=datetime(2026, 8, 13, 1, 0, 5))
    assert result["status"] == "FAIL"
    assert any("non-target currency" in error for error in result["errors"])


def test_stale_runtime_fails(tmp_path: Path) -> None:
    write_runtime(
        tmp_path,
        [
            {"kind": "INIT", "ts_local": "2026.08.13 01:00:00", **SAFE},
            *prime_rows(),
        ],
    )
    result = audit(tmp_path, now=datetime(2026, 8, 13, 1, 3, 0))
    assert result["status"] == "FAIL"
    assert any("collector stale" in error for error in result["errors"])


def test_only_latest_init_session_controls_runtime_verdict(tmp_path: Path) -> None:
    historical_unsafe = {**SAFE, "prices_read": True}
    write_runtime(
        tmp_path,
        [
            {"kind": "INIT", "ts_local": "2026.08.13 00:00:00", **historical_unsafe},
            {"kind": "API_ERROR", "ts_local": "2026.08.13 00:00:30", **historical_unsafe},
            {"kind": "INIT", "ts_local": "2026.08.13 01:00:00", "collector_version": "1.3.0", **SAFE},
            *prime_rows(),
            {"kind": "HEARTBEAT", "ts_local": "2026.08.13 01:01:00", **SAFE},
        ],
    )

    result = audit(tmp_path, now=datetime(2026, 8, 13, 1, 1, 10))

    assert result["status"] == "PASS"
    assert result["collector_version"] == "1.3.0"
    assert result["api_errors"] == 0
    assert result["total_records"] > result["session_records"]


def test_api_error_in_latest_session_fails(tmp_path: Path) -> None:
    write_runtime(
        tmp_path,
        [
            {"kind": "INIT", "ts_local": "2026.08.13 01:00:00", **SAFE},
            *prime_rows(),
            {"kind": "API_ERROR", "ts_local": "2026.08.13 01:00:20", **SAFE},
        ],
    )

    result = audit(tmp_path, now=datetime(2026, 8, 13, 1, 0, 30))

    assert result["status"] == "FAIL"
    assert any("latest runtime session has 1" in error for error in result["errors"])


def test_v141_complete_discovery_prime_and_idle_proof_passes(tmp_path: Path) -> None:
    records = [
        {
            "kind": "INIT",
            "ts_local": "2026.08.13 01:00:00",
            "collector_version": "1.4.1",
            "countries_loaded": False,
            **SAFE,
        },
        {"kind": "DISCOVERY_COUNTRIES", "ts_local": "2026.08.13 01:00:01", **SAFE},
    ]
    records.extend(
        {
            "kind": "DISCOVERY_EVENT_DEFS",
            "ts_local": f"2026.08.13 01:00:{index:02d}",
            "currency": currency,
            **SAFE,
        }
        for index, currency in enumerate(
            ("USD", "EUR", "JPY", "GBP", "CHF", "CAD", "AUD", "NZD"), start=2
        )
    )
    records.extend(
        [
            {
                "kind": "PRIME_EVENT",
                "ts_local": "2026.08.13 01:00:10",
                "event_id": 1001,
                "values_returned": 0,
                "change_id_after": 123,
                **SAFE,
            },
            {
                "kind": "PRIME_EVENT",
                "ts_local": "2026.08.13 01:00:11",
                "event_id": 1002,
                "values_returned": 0,
                "change_id_after": 123,
                **SAFE,
            },
            {
                "kind": "IDLE_PROOF_EVENT",
                "ts_local": "2026.08.13 01:01:00",
                "event_id": 1001,
                **SAFE,
            },
            {"kind": "HEARTBEAT", "ts_local": "2026.08.13 01:01:01", **SAFE},
        ]
    )
    (tmp_path / "calendar_pit_v141.jsonl").write_text(
        "\n".join(json.dumps(row) for row in records) + "\n", encoding="utf-8"
    )
    (tmp_path / "event_state_v141.txt").write_text(
        "countries_ok=1\n"
        "enum_ok=1,1,1,1,1,1,1,1\n"
        "nev=2\n"
        "E\t1001\t123\t1\t1\t0\tUSD\n"
        "E\t1002\t123\t1\t0\t0\tEUR\n",
        encoding="utf-8",
    )

    result = audit(tmp_path, now=datetime(2026, 8, 13, 1, 1, 10))

    assert result["status"] == "PASS"
    assert result["collector_version"] == "1.4.1"
    assert result["durable_event_count"] == 2
    assert result["primed_event_count"] == 2
    assert result["acceptance_evidence_seen"] is True


def test_v15_frozen_catalog_and_paired_history_proof_passes(tmp_path: Path) -> None:
    identity = {
        "event_id": 840010001,
        "value_id": 9001,
        "scheduled": 1786608000,
        "period": 1783987200,
    }
    records = [
        {
            "kind": "INIT",
            "ts_local": "2026.08.13 01:00:00",
            "collector_version": "1.5.0",
            "enum_ok_loaded": 8,
            "countries_loaded": True,
            "catalog_frozen": True,
            **SAFE,
        },
        {
            "kind": "FUTURE_DISCOVERY_HISTORY",
            "ts_local": "2026.08.13 01:00:10",
            **identity,
            **SAFE,
        },
        {
            "kind": "IDLE_PROOF_HISTORY",
            "ts_local": "2026.08.13 01:00:20",
            **identity,
            **SAFE,
        },
        {"kind": "HEARTBEAT", "ts_local": "2026.08.13 01:00:30", **SAFE},
    ]
    (tmp_path / "calendar_pit_v15.jsonl").write_text(
        "\n".join(json.dumps(row) for row in records) + "\n", encoding="utf-8"
    )
    (tmp_path / "catalog_state_v15.txt").write_text(
        "schema=15\n"
        "version=1.5.0\n"
        "frozen=1\n"
        "n_all=1\n"
        "n_sel=1\n"
        "catalog_hash=123\n"
        "rr=0\n"
        "enum_ok=1,1,1,1,1,1,1,1\n"
        "E\t840010001\tUSD\t840\t3\t1\t0\t1\t0\tcore-pce\tCore PCE\n",
        encoding="utf-8",
    )
    (tmp_path / "occurrence_v15.txt").write_text(
        "schema=15\n"
        "n_occ=1\n"
        "O\t840010001\t9001\t1786608000\t1783987200\t0\t1\t0\t1\t1\t123\t1\t2\t3\t2\t0\t1\t1\n",
        encoding="utf-8",
    )

    result = audit(tmp_path, now=datetime(2026, 8, 13, 1, 0, 40))

    assert result["status"] == "PASS"
    assert result["collector_version"] == "1.5.0"
    assert result["selected_event_count"] == 1
    assert result["occurrence_count"] == 1
    assert result["paired_history_proof"] is True
    assert result["acceptance_evidence_seen"] is True


def test_v15_history_api_error_and_missing_proofs_fail(tmp_path: Path) -> None:
    records = [
        {
            "kind": "INIT",
            "ts_local": "2026.08.13 01:00:00",
            "collector_version": "1.5.0",
            "enum_ok_loaded": 8,
            "countries_loaded": True,
            "catalog_frozen": True,
            **SAFE,
        },
        {
            "kind": "API_ERROR_HISTORY",
            "ts_local": "2026.08.13 01:00:20",
            "event_id": 840010001,
            "api_error": 5401,
            **SAFE,
        },
    ]
    (tmp_path / "calendar_pit_v15.jsonl").write_text(
        "\n".join(json.dumps(row) for row in records) + "\n", encoding="utf-8"
    )
    (tmp_path / "catalog_state_v15.txt").write_text(
        "schema=15\n"
        "version=1.5.0\n"
        "frozen=1\n"
        "n_all=1\n"
        "n_sel=1\n"
        "catalog_hash=123\n"
        "rr=0\n"
        "enum_ok=1,1,1,1,1,1,1,1\n"
        "E\t840010001\tUSD\t840\t3\t1\t0\t1\t0\tcore-pce\tCore PCE\n",
        encoding="utf-8",
    )
    (tmp_path / "occurrence_v15.txt").write_text("schema=15\nn_occ=0\n", encoding="utf-8")

    result = audit(tmp_path, now=datetime(2026, 8, 13, 1, 0, 30))

    assert result["status"] == "FAIL"
    assert result["api_errors"] == 1
    assert any("missing FUTURE_DISCOVERY_HISTORY" in error for error in result["errors"])
    assert any("missing IDLE_PROOF_HISTORY" in error for error in result["errors"])
