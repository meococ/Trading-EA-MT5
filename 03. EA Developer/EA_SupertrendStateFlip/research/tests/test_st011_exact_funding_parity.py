from __future__ import annotations

import hashlib
import importlib.util
import json
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

RESEARCH = Path(__file__).resolve().parents[1]
WRAPPER_PATH = RESEARCH / "compare_st011_exact_funding_parity.py"


def load_module():
    spec = importlib.util.spec_from_file_location("st011_wrapper_test", WRAPPER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


wrapper = load_module()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


@dataclass(frozen=True)
class Deal:
    time: datetime
    deal_id: int
    symbol: str
    side: str
    direction: str
    volume: float
    price: float
    order_id: int | None
    commission: float
    swap: float
    profit: float
    balance: float
    comment: str


def exact_deal() -> Deal:
    return Deal(datetime(2005, 1, 1), 1, "", "balance", "", 0.0, 0.0, None, 0.0, 0.0, 10000.0, 10000.0, "")


def authority_row(test_sha: str) -> dict:
    validation = {
        "reviewed_exact_funding_comparator_sha256": file_sha(WRAPPER_PATH),
        "reviewed_hyp010_comparator_sha256": wrapper.HYP010_COMPARATOR_SHA256,
        "reviewed_exact_funding_test_sha256": test_sha,
        "reviewed_sealed_comparator_test_sha256": test_sha,
        "reviewed_mql_source_sha256": wrapper.BASE.BASE.EXPECTED_SOURCE_SHA256,
        "reviewed_mql_source_path": "02. AlphaFactory/runs/EA_SupertrendStateFlip/20260809_064257/snapshot/source/EA_SupertrendStateFlip.mq5",
        "hyp010_terminal_row_sha256": wrapper.HYP010_TERMINAL_ROW_SHA256,
        "hyp010_comparator_start_sha256": wrapper.HYP010_START_SHA256,
        "hyp010_comparator_terminal_sha256": wrapper.HYP010_TERMINAL_SHA256,
        "hyp010_failure_sha256": wrapper.HYP010_FAILURE_SHA256,
        "hyp010_post_failure_review_sha256": wrapper.HYP010_REVIEW_SHA256,
        "tester_report_sha256": wrapper.REPORT_SHA256,
        "quant_analyzer_sha256": wrapper.QUANT_ANALYZER_SHA256,
        "artifact_collection_authorized": False,
        "comparator_execution_authorized": True,
        "comparator_attempt_id": wrapper.COMPARATOR_ATTEMPT_ID,
        "comparator_attempt_limit": 1,
        "mt5_authorized": False,
        "mt5_parity_run_authorized": False,
        "compile_authorized": False,
        "run_compile_authorized": False,
        "mql5_compile_authorized": False,
        "standalone_compile_authorized": False,
        "trade_api_authorized": False,
        "performance_metrics_authorized": False,
        "outcome_prices_authorized": False,
        "post_event_ohlc_authorized": False,
        "economics_authorized": False,
        "optimization_authorized": False,
        "validation_authorized": False,
        "holdout_authorized": False,
        "research_validation_access_authorized": False,
        "research_holdout_access_authorized": False,
        "promotion_eligible": False,
        "paper_trading_authorized": False,
        "live_trading_authorized": False,
        "market_edge_claim_authorized": False,
        "same_id_retry_authorized": False,
        "registry_mutation_allowed": False,
    }
    return {
        "hypothesis_id": wrapper.AUTHORITY_HYPOTHESIS_ID,
        "state": "screened",
        "model": 0,
        "verdict": "FROZEN_ST011_EXACT_FUNDING_COMPARATOR_AUTHORIZED",
        "metrics": {"comparator_attempts_consumed": 0},
        "validation": validation,
    }


def test_fresh_identity_and_frozen_dependency() -> None:
    assert wrapper.AUTHORITY_HYPOTHESIS_ID == "HYP-ST-XAUUSD-H1-011"
    assert wrapper.COMPARATOR_ATTEMPT_ID == "ST011-COMPARATOR-001"
    assert wrapper.HYP010_COMPARATOR_SHA256 == file_sha(RESEARCH / "compare_st010_sealed_recovery_parity.py")


@pytest.mark.parametrize(
    ("field", "mode"),
    [
        ("reviewed_exact_funding_test_sha256", "missing"),
        ("reviewed_sealed_comparator_test_sha256", "missing"),
        ("reviewed_exact_funding_test_sha256", "wrong"),
        ("reviewed_sealed_comparator_test_sha256", "wrong"),
    ],
)
def test_preclaim_requires_both_equal_test_hash_fields(field: str, mode: str, tmp_path: Path) -> None:
    row = authority_row(file_sha(Path(__file__)))
    if mode == "missing":
        del row["validation"][field]
    else:
        row["validation"][field] = "BAD"
    registry = tmp_path / "registry.jsonl"
    registry.write_text(json.dumps(row) + "\n", encoding="utf-8")
    args = SimpleNamespace(mql_source=wrapper.BASE.RUN_SOURCE_SNAPSHOT)
    with pytest.raises(ValueError, match="test_metadata"):
        wrapper.validate_registry_authority(registry, args)


def test_postclaim_rejects_actual_test_hash_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    row = authority_row(file_sha(Path(__file__)))
    registry = tmp_path / "registry.jsonl"
    registry.write_text(json.dumps(row) + "\n", encoding="utf-8")
    wrong_test = tmp_path / "wrong_test.py"
    wrong_test.write_text("tampered", encoding="utf-8")
    monkeypatch.setattr(wrapper, "ORIGINAL_BOUND_VALIDATOR", lambda _args: None)
    args = SimpleNamespace(registry=registry, test_source=wrong_test)
    with pytest.raises(ValueError, match="exact-funding test binding mismatch"):
        wrapper.validate_authority_bound_files(args)


def test_exact_funding_dataclass_only() -> None:
    deal = exact_deal()
    assert wrapper.exact_funding_deals([deal], Deal)
    assert not wrapper.exact_funding_deals([], Deal)
    assert not wrapper.exact_funding_deals([deal, deal], Deal)
    for field, value in {
        "time": datetime(2005, 1, 1, 1),
        "deal_id": 2,
        "symbol": "XAUUSD",
        "side": "buy",
        "direction": "in",
        "volume": 0.01,
        "price": 1.0,
        "order_id": 1,
        "commission": -1.0,
        "swap": 1.0,
        "profit": 9999.0,
        "balance": 9999.0,
        "comment": "funding",
    }.items():
        assert not wrapper.exact_funding_deals([replace(deal, **{field: value})], Deal)


def test_orders_section_requires_exact_empty_shape() -> None:
    header = "".join(f"<td><b>h{i}</b></td>" for i in range(13))
    html = f"<b>Orders</b><tr>{header}</tr><tr><td></td></tr><b>Deals</b>"
    assert wrapper.orders_section_is_empty(html)
    assert wrapper.orders_section_is_empty(html.replace("Orders", "Các lệnh đặt"))
    extra = html.replace("<b>Deals</b>", "<tr><td>order</td></tr><b>Deals</b>")
    assert not wrapper.orders_section_is_empty(extra)
    assert not wrapper.orders_section_is_empty(html.replace("<td></td>", "<td>1</td>"))
    assert not wrapper.orders_section_is_empty(html.replace("</tr><tr>", "</tr>"))


def test_alpha_validator_uses_exact_report_and_analyzer_bindings() -> None:
    text = WRAPPER_PATH.read_text(encoding="utf-8")
    assert "parse_deals_from_html_report" in text
    assert "exact_funding_deals(deals, analyzer.Deal)" in text
    assert "orders_section_is_empty" in text
    assert 'sha256_file(args.tester_report.resolve()) != REPORT_SHA256' in text
    assert 'sha256_file(analyzer_path) != QUANT_ANALYZER_SHA256' in text
    assert "if analyzer.parse_deals_from_html_report(args.tester_report):" not in text


def test_claim_order_and_zero_authority_are_inherited() -> None:
    base_text = (RESEARCH / "compare_st009_existing_run_parity.py").read_text(encoding="utf-8")
    own = WRAPPER_PATH.read_text(encoding="utf-8")
    assert base_text.index("marker = BASE.claim_comparator") < base_text.index("BASE.validate_oracle_chain")
    assert "artifact_collection_authorized" in own
    assert "no_economics" in own
    assert "no_retry_mutation" in own
    assert "subprocess" not in own
    assert "alpha.ps1" not in own


def test_hyp010_terminal_dependencies_are_postclaim_bound() -> None:
    text = WRAPPER_PATH.read_text(encoding="utf-8")
    for label in ("hyp010_start", "hyp010_terminal", "hyp010_failure", "hyp010_review"):
        assert f'"{label}":' in text
    assert "ORIGINAL_BOUND_VALIDATOR(args)" in text
    assert "validate_authority_bound_files(args)" in text
    assert 'sha256_file(args.test_source.resolve()) != validation.get("reviewed_exact_funding_test_sha256")' in text
