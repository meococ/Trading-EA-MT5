from __future__ import annotations

import hashlib
import importlib.util
import unicodedata
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
WRAPPER_PATH = RESEARCH / "compare_stbs005_exact_orders_heading.py"
BASE_PATH = RESEARCH / "compare_stbs004_existing_run.py"


def load_module():
    spec = importlib.util.spec_from_file_location("stbs005_wrapper_test", WRAPPER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def orders_html(*, heading: str = "Orders", deals: str = "Deals", extra: str = "", spacer: str = "") -> str:
    spans = [1, 1, 1, 1, 2, 1, 1, 1, 2, 1, 1]
    header = "".join(
        f'<td{(" colspan=" + chr(34) + str(span) + chr(34)) if span != 1 else ""}><b>h{i}</b></td>'
        for i, span in enumerate(spans)
    )
    return (
        f"<b>{heading}</b><tr>{header}</tr><tr><td>{spacer}</td></tr>"
        f"{extra}<b>{deals}</b>"
    )


def test_fresh_identity_and_frozen_base() -> None:
    wrapper = load_module()
    assert wrapper.HYPOTHESIS_ID == "HYP-STBS-XAUUSD-M15-005"
    assert wrapper.ATTEMPT_ID == "STBS005-COMPARATOR-001"
    assert wrapper.HYP004_TERMINAL_ROW_SHA256 == "74C14309567C96AC54A0DEACE93B08B7487D016752EF262D52830476C9DCF252"
    assert wrapper.BASE_SHA256 == file_sha(BASE_PATH)


def test_exact_english_and_vietnamese_nfc_pass() -> None:
    wrapper = load_module()
    vietnamese = "C\u00e1c l\u1ec7nh \u0111\u1eb7t"
    assert wrapper.orders_section_is_empty(orders_html())
    assert wrapper.orders_section_is_empty(orders_html(heading=vietnamese))


def test_mojibake_nfd_and_misspelling_fail() -> None:
    wrapper = load_module()
    vietnamese = "C\u00e1c l\u1ec7nh \u0111\u1eb7t"
    for bad in (
        "CÃ¡c lá»‡nh Ä‘áº·t",
        unicodedata.normalize("NFD", vietnamese),
        "Các lệnh dat",
        "Order",
    ):
        assert not wrapper.orders_section_is_empty(orders_html(heading=bad))


def test_duplicate_or_missing_headings_fail() -> None:
    wrapper = load_module()
    assert not wrapper.orders_section_is_empty(orders_html(extra="<b>Orders</b>"))
    assert not wrapper.orders_section_is_empty(orders_html(deals="Missing"))
    assert not wrapper.orders_section_is_empty(orders_html(extra="<b>Deals</b>"))
    assert not wrapper.orders_section_is_empty(orders_html(heading="Missing"))


def test_exact_empty_orders_structure_remains_frozen() -> None:
    wrapper = load_module()
    good = orders_html()
    assert not wrapper.orders_section_is_empty(good.replace('<td><b>h0', '<td colspan="2"><b>h0'))
    assert not wrapper.orders_section_is_empty(orders_html(spacer="order"))
    assert not wrapper.orders_section_is_empty(good.replace("<b>h0</b>", "h0"))
    assert not wrapper.orders_section_is_empty(good.replace('<td><b>h0', '<td colspan="bad"><b>h0'))
    assert not wrapper.orders_section_is_empty(good.replace('<td><b>h0', '<td colspan="1" colspan="1"><b>h0'))
    assert not wrapper.orders_section_is_empty(good.replace("</tr><tr><td></td></tr>", "</tr><tr><td></td></tr><tr><td>order</td></tr>"))


def test_wrapper_source_preserves_claim_order_and_zero_authority() -> None:
    text = WRAPPER_PATH.read_text(encoding="utf-8")
    assert text.index("OUTPUT_DIR.mkdir") < text.index("for label, (path, expected) in BASE.STATIC_BINDINGS.items()")
    assert "same_id_retry_authorized" in text
    assert "FALSE_AUTHORITIES" in text
    assert "economics_evaluated\": False" in text
    assert "subprocess" not in text


def test_base_dependency_is_single_capture_and_same_buffer_bound() -> None:
    wrapper = load_module()
    text = WRAPPER_PATH.read_text(encoding="utf-8")
    assert text.count("BASE_PATH.read_bytes()") == 1
    assert "compile(BASE_RAW" in text
    assert 'captured["base_comparator"] = BASE_RAW' in text
    assert wrapper.sha256_bytes(wrapper.BASE_RAW) == wrapper.BASE_SHA256


def test_hyp005_report_schema_is_fresh_and_fail_closed() -> None:
    wrapper = load_module()
    base = {"schema_version": "stbs004_existing_run_comparator_report.v1", "hypothesis_id": wrapper.HYPOTHESIS_ID}
    revised = wrapper.revise_report(base)
    assert revised["schema_version"] == "stbs005_exact_orders_heading_comparator_report.v1"
    assert revised["heading_revision"] == "EXACT_ENGLISH_OR_NFC_VIETNAMESE_NO_NORMALIZATION"
    assert base["schema_version"] == "stbs004_existing_run_comparator_report.v1"
    try:
        wrapper.revise_report({"schema_version": "wrong"})
    except ValueError:
        pass
    else:
        raise AssertionError("wrong inherited report schema must fail")


def test_hyp004_failure_chain_is_postclaim_bound() -> None:
    text = WRAPPER_PATH.read_text(encoding="utf-8")
    for label in ("hyp004_start", "hyp004_terminal", "hyp004_failure", "hyp004_review"):
        assert f'"{label}"' in text
    assert "HYP004_TERMINAL_ROW_SHA256" in text
