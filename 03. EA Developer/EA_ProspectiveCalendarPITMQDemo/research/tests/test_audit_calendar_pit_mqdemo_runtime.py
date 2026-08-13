import importlib.util
import json
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "audit_calendar_pit_mqdemo_runtime.py"
SPEC = importlib.util.spec_from_file_location("mqdemo_audit", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _base(kind: str) -> dict:
    return {
        "kind": kind,
        "hypothesis_id": "HYP-CALENDAR-PIT-MQDEMO-001",
        "expected_server": "MetaQuotes-Demo",
        "account_server": "MetaQuotes-Demo",
        "outcome_accessed": False,
        "prices_read": False,
        "orders": False,
        "trading_disabled": True,
    }


def _write(path: Path, records: list[dict]) -> None:
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")


def test_accepts_only_full_pair_and_clean_runtime(tmp_path: Path) -> None:
    records = []
    for currency in ("USD", "EUR", "JPY", "GBP", "CHF", "CAD", "AUD", "NZD"):
        record = _base("DISCOVERY_EVENT_DEFS")
        record["currency"] = currency
        records.append(record)
    records.append(_base("CATALOG_FROZEN"))
    first = _base("FUTURE_DISCOVERY_HISTORY")
    first.update(event_id=1, value_id=2, scheduled_unix=3, period_unix=4, payload_hash="5")
    records.append(first)
    second = _base("IDLE_PROOF_HISTORY")
    second.update(event_id=1, value_id=2, scheduled_unix=3, period_unix=4, payload_hash="5")
    records.append(second)
    path = tmp_path / "pass.jsonl"
    _write(path, records)
    assert MODULE.audit(path)["verdict"] == "ADMISSIBLE_MQDEMO_CAPABILITY_CHILD"


def test_api_error_kills_and_multiple_errors_fail_stop_contract(tmp_path: Path) -> None:
    records = [_base("API_ERROR_HISTORY"), _base("API_ERROR_HISTORY"), _base("SHUTDOWN")]
    path = tmp_path / "fail.jsonl"
    _write(path, records)
    result = MODULE.audit(path)
    assert result["verdict"] == "KILL_MQDEMO_CAPABILITY_CHILD"
    assert result["checks"]["stop_after_first_fatal"] is False
