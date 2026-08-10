from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WRAPPER_PATH = RESEARCH / "compare_st012_exact_orders_parity.py"


def load_module():
    spec = importlib.util.spec_from_file_location("st012_wrapper_test", WRAPPER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


wrapper = load_module()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def orders_html(*, vector: list[int] | None = None, spacer: str = "", extra: str = "") -> str:
    spans = vector or wrapper.EXPECTED_COLSPANS
    header = "".join(
        f'<td{(" colspan=\"" + str(span) + "\"") if span != 1 else ""}><b>h{i}</b></td>'
        for i, span in enumerate(spans)
    )
    return f"<b>Orders</b><tr>{header}</tr><tr><td>{spacer}</td></tr>{extra}<b>Deals</b>"


def test_fresh_identity_and_dependency() -> None:
    assert wrapper.AUTHORITY_HYPOTHESIS_ID == "HYP-ST-XAUUSD-H1-012"
    assert wrapper.COMPARATOR_ATTEMPT_ID == "ST012-COMPARATOR-001"
    assert wrapper.HYP011_COMPARATOR_SHA256 == file_sha(RESEARCH / "compare_st011_exact_funding_parity.py")


def test_all_three_test_hash_aliases_must_match() -> None:
    good = "A" * 64
    fields = {
        "reviewed_exact_orders_test_sha256": good,
        "reviewed_exact_funding_test_sha256": good,
        "reviewed_sealed_comparator_test_sha256": good,
    }
    assert wrapper.consistent_test_hashes(fields)
    for field in tuple(fields):
        missing = dict(fields)
        del missing[field]
        assert not wrapper.consistent_test_hashes(missing)
        wrong = dict(fields)
        wrong[field] = "BAD"
        assert not wrapper.consistent_test_hashes(wrong)


def test_exact_orders_shape_passes() -> None:
    assert wrapper.orders_section_is_empty(orders_html())
    assert wrapper.orders_section_is_empty(orders_html().replace("Orders", "Các lệnh đặt"))
    cells = [("", "x"), (' colspan="2"', "x")]
    assert wrapper.parse_colspans(cells) == [1, 2]


def test_every_orders_shape_deviation_fails() -> None:
    assert not wrapper.orders_section_is_empty(orders_html(vector=[1] * 11))
    assert not wrapper.orders_section_is_empty(orders_html(vector=wrapper.EXPECTED_COLSPANS[:-1]))
    assert not wrapper.orders_section_is_empty(orders_html(spacer="order"))
    assert not wrapper.orders_section_is_empty(orders_html(extra="<tr><td>order</td></tr>"))
    assert not wrapper.orders_section_is_empty(orders_html().replace("<b>h0</b>", "h0"))
    assert not wrapper.orders_section_is_empty(orders_html().replace("<td><b>h0", '<td colspan="2"><b>h0'))
    duplicate = [(" colspan=2 colspan=2", "x")]
    assert wrapper.parse_colspans(duplicate) is None
    assert wrapper.parse_colspans([(" colspan=0", "x")]) is None
    assert wrapper.parse_colspans([(" colspan=-1", "x")]) is None
    assert wrapper.parse_colspans([(" colspan=x", "x")]) is None
    assert wrapper.parse_colspans([(" colspan", "x")]) is None
    assert wrapper.parse_colspans([(" colspan=1.5", "x")]) is None
    assert wrapper.parse_colspans([(" colspan=1x", "x")]) is None
    assert wrapper.parse_colspans([(' colspan=""', "x")]) is None
    for bad in ("bad", "-1", '""', "1.5", "1x", "bad colspan=1"):
        mutated_header = orders_html().replace("<td><b>h0", f"<td colspan={bad}><b>h0")
        assert not wrapper.orders_section_is_empty(mutated_header)
        mutated_spacer = orders_html().replace("<tr><td></td></tr>", f"<tr><td colspan={bad}></td></tr>")
        assert not wrapper.orders_section_is_empty(mutated_spacer)


def test_inherits_exact_funding_and_claim_order() -> None:
    text = WRAPPER_PATH.read_text(encoding="utf-8")
    funding = (RESEARCH / "compare_st011_exact_funding_parity.py").read_text(encoding="utf-8")
    engine = (RESEARCH / "compare_st009_existing_run_parity.py").read_text(encoding="utf-8")
    assert "exact_funding_deals" in funding
    assert engine.index("marker = BASE.claim_comparator") < engine.index("BASE.validate_oracle_chain")
    assert "ORIGINAL_BOUND_VALIDATOR(args)" in text
    assert "artifact_collection_authorized" in text
    assert "no_economics" in text
    assert "subprocess" not in text


def test_hyp011_terminal_chain_is_postclaim_bound() -> None:
    text = WRAPPER_PATH.read_text(encoding="utf-8")
    for label in ("hyp011_start", "hyp011_terminal", "hyp011_failure", "hyp011_review"):
        assert f'"{label}":' in text
    assert "validate_authority_bound_files(args)" in text
