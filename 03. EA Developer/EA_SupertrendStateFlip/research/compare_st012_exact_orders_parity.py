#!/usr/bin/env python3
"""Run HYP012 parity with exact physical/logical MT5 Orders shape."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
AUTHORITY_HYPOTHESIS_ID = "HYP-ST-XAUUSD-H1-012"
COMPARATOR_ATTEMPT_ID = "ST012-COMPARATOR-001"
COMPARATOR_ROOT = ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/evidence/HYP-ST-XAUUSD-H1-012/ST012-COMPARATOR-001"
HYP011_COMPARATOR_SHA256 = "1782402317C28CDA45ED5F1B4B10E571E361F26A3B025C38CEC1E0E059FFA48C"
HYP011_TERMINAL_ROW_SHA256 = "8B6A6F8EAD19C653DE4CD1FCC360639FF9B473DE336DE78320865014311BEE39"
HYP011_START_SHA256 = "4A5D28D2103898C74FC06148B984DE1F02CD5D12A4FC3F167D676B10FA40B82F"
HYP011_TERMINAL_SHA256 = "912130D0E3C5789EFFFB8AE58ABEC4F0032EF1A3ACEAD81B5E17CD9B23F4F45B"
HYP011_FAILURE_SHA256 = "B38C8A4CC5A336060FFDECBD6DFBFCE6AA46A4F96812CC6EBDD811EBABD5F377"
HYP011_REVIEW_SHA256 = "4381EBB8EFBA87192D8434764C14BDE0228CE2EDFB6FE86495BD1FA63C872F5E"
HYP011_START_PATH = ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/evidence/HYP-ST-XAUUSD-H1-011/ST011-COMPARATOR-001/attempt_started.json"
HYP011_TERMINAL_PATH = ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/evidence/HYP-ST-XAUUSD-H1-011/ST011-COMPARATOR-001/attempt_terminal.json"
HYP011_FAILURE_PATH = ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/HYP-ST-XAUUSD-H1-011_ORDERS_HEADER_SHAPE_FAILURE.md"
HYP011_REVIEW_PATH = ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/HYP-ST-XAUUSD-H1-011_POST_FAILURE_REVIEW.md"
EXPECTED_COLSPANS = [1, 1, 1, 1, 2, 1, 1, 1, 2, 1, 1]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_hyp011():
    path = Path(__file__).resolve().with_name("compare_st011_exact_funding_parity.py")
    if sha256_file(path) != HYP011_COMPARATOR_SHA256:
        raise ValueError("frozen HYP011 comparator dependency hash drift")
    spec = importlib.util.spec_from_file_location("st012_hyp011_comparator_dependency", path)
    if not spec or not spec.loader:
        raise ValueError("cannot load frozen HYP011 comparator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BASE = load_hyp011()
ORIGINAL_BOUND_VALIDATOR = BASE.validate_authority_bound_files


def registry_rows(path: Path, hypothesis_id: str) -> list[tuple[bytes, dict[str, Any]]]:
    matches: list[tuple[bytes, dict[str, Any]]] = []
    for raw in path.read_bytes().splitlines():
        if raw.strip():
            row = json.loads(raw.decode("utf-8"))
            if row.get("hypothesis_id") == hypothesis_id:
                matches.append((raw, row))
    return matches


def consistent_test_hashes(validation: dict[str, Any]) -> bool:
    test_sha = validation.get("reviewed_exact_orders_test_sha256")
    return (
        isinstance(test_sha, str)
        and len(test_sha) == 64
        and validation.get("reviewed_exact_funding_test_sha256") == test_sha
        and validation.get("reviewed_sealed_comparator_test_sha256") == test_sha
    )


def validate_registry_authority(registry_path: Path, args: Any) -> tuple[dict[str, Any], dict[str, str]]:
    matches = registry_rows(registry_path, AUTHORITY_HYPOTHESIS_ID)
    if not matches:
        raise ValueError("missing HYP012 comparator authority")
    raw, row = matches[-1]
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    checks = {
        "state": row.get("state") == "screened",
        "model": row.get("model") == 0,
        "verdict": row.get("verdict") == "FROZEN_ST012_EXACT_ORDERS_COMPARATOR_AUTHORIZED",
        "wrapper": validation.get("reviewed_exact_orders_comparator_sha256") == sha256_file(Path(__file__).resolve()),
        "dependency": validation.get("reviewed_hyp011_comparator_sha256") == HYP011_COMPARATOR_SHA256,
        "test_metadata": consistent_test_hashes(validation),
        "source": validation.get("reviewed_mql_source_sha256") == BASE.BASE.BASE.EXPECTED_SOURCE_SHA256,
        "source_path": args.mql_source.resolve() == BASE.BASE.RUN_SOURCE_SNAPSHOT.resolve()
        and validation.get("reviewed_mql_source_path") == "02. AlphaFactory/runs/EA_SupertrendStateFlip/20260809_064257/snapshot/source/EA_SupertrendStateFlip.mq5",
        "hyp011_row": validation.get("hyp011_terminal_row_sha256") == HYP011_TERMINAL_ROW_SHA256,
        "hyp011_start": validation.get("hyp011_comparator_start_sha256") == HYP011_START_SHA256,
        "hyp011_terminal": validation.get("hyp011_comparator_terminal_sha256") == HYP011_TERMINAL_SHA256,
        "hyp011_failure": validation.get("hyp011_failure_sha256") == HYP011_FAILURE_SHA256,
        "hyp011_review": validation.get("hyp011_post_failure_review_sha256") == HYP011_REVIEW_SHA256,
        "report": validation.get("tester_report_sha256") == BASE.REPORT_SHA256,
        "analyzer": validation.get("quant_analyzer_sha256") == BASE.QUANT_ANALYZER_SHA256,
        "no_collection": validation.get("artifact_collection_authorized") is False,
        "compare": validation.get("comparator_execution_authorized") is True,
        "compare_id": validation.get("comparator_attempt_id") == COMPARATOR_ATTEMPT_ID,
        "compare_limit": validation.get("comparator_attempt_limit") == 1,
        "compare_unconsumed": metrics.get("comparator_attempts_consumed") == 0,
        "no_mt5": validation.get("mt5_authorized") is False and validation.get("mt5_parity_run_authorized") is False,
        "no_compile": validation.get("compile_authorized") is False
        and validation.get("run_compile_authorized") is False
        and validation.get("mql5_compile_authorized") is False
        and validation.get("standalone_compile_authorized") is False,
        "no_trade": validation.get("trade_api_authorized") is False,
        "no_outcomes": validation.get("performance_metrics_authorized") is False
        and validation.get("outcome_prices_authorized") is False
        and validation.get("post_event_ohlc_authorized") is False,
        "no_economics": validation.get("economics_authorized") is False,
        "no_research": validation.get("optimization_authorized") is False
        and validation.get("validation_authorized") is False
        and validation.get("holdout_authorized") is False
        and validation.get("research_validation_access_authorized") is False
        and validation.get("research_holdout_access_authorized") is False,
        "no_deploy": validation.get("promotion_eligible") is False
        and validation.get("paper_trading_authorized") is False
        and validation.get("live_trading_authorized") is False
        and validation.get("market_edge_claim_authorized") is False,
        "no_retry_mutation": validation.get("same_id_retry_authorized") is False
        and validation.get("registry_mutation_allowed") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"HYP012 authority failed: {failed}")
    return row, {
        "registry_sha256": sha256_file(registry_path),
        "latest_row_sha256": hashlib.sha256(raw).hexdigest().upper(),
    }


def validate_authority_bound_files(args: Any) -> None:
    ORIGINAL_BOUND_VALIDATOR(args)
    matches = registry_rows(args.registry.resolve(), AUTHORITY_HYPOTHESIS_ID)
    if not matches:
        raise ValueError("missing HYP012 post-claim authority")
    _, row = matches[-1]
    validation = row.get("validation", {})
    if sha256_file(args.test_source.resolve()) != validation.get("reviewed_exact_orders_test_sha256"):
        raise ValueError("HYP012 exact-Orders test binding mismatch")
    bindings = {
        "hyp011_start": (HYP011_START_PATH, validation.get("hyp011_comparator_start_sha256")),
        "hyp011_terminal": (HYP011_TERMINAL_PATH, validation.get("hyp011_comparator_terminal_sha256")),
        "hyp011_failure": (HYP011_FAILURE_PATH, validation.get("hyp011_failure_sha256")),
        "hyp011_review": (HYP011_REVIEW_PATH, validation.get("hyp011_post_failure_review_sha256")),
    }
    for label, (path, expected) in bindings.items():
        BASE.BASE.BASE.BASE.require_bound_file(path.resolve(), str(expected or ""), label)


def validate_oracle_chain_after_claim(args: Any) -> None:
    validate_authority_bound_files(args)
    BASE.BASE.ORIGINAL_ORACLE_CHAIN_VALIDATOR(args)


def parse_colspans(cells: list[tuple[str, str]]) -> list[int] | None:
    values: list[int] = []
    for attrs, _ in cells:
        occurrences = len(re.findall(r"\bcolspan\b", attrs, re.I))
        matches = re.findall(
            r"\bcolspan\s*=\s*(?:\"([0-9]+)\"|'([0-9]+)'|([0-9]+))(?=\s|$)",
            attrs,
            re.I,
        )
        if occurrences > 1 or (occurrences == 1 and len(matches) != 1):
            return None
        digits = next((part for part in matches[0] if part), "") if matches else ""
        value = int(digits) if digits else 1
        if value <= 0:
            return None
        values.append(value)
    return values


def orders_section_is_empty(html: str) -> bool:
    start = re.search(r"<b>\s*(?:Orders|Các\s+lệnh\s+đặt)\s*</b>", html, re.I)
    if not start:
        return False
    end = re.search(r"<b>\s*Deals\s*</b>", html[start.end():], re.I)
    if not end:
        return False
    section = html[start.end(): start.end() + end.start()]
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", section, re.I | re.S)
    if len(rows) != 2:
        return False
    td_re = re.compile(r"<td([^>]*)>(.*?)</td>", re.I | re.S)
    header = td_re.findall(rows[0])
    spacer = td_re.findall(rows[1])
    if len(header) != 11 or parse_colspans(header) != EXPECTED_COLSPANS or sum(EXPECTED_COLSPANS) != 13:
        return False
    if not all(re.fullmatch(r"\s*<b>.*?</b>\s*", inner, re.I | re.S) for _, inner in header):
        return False
    if len(spacer) != 1 or parse_colspans(spacer) != [1]:
        return False
    return re.sub(r"<[^>]+>", "", spacer[0][1]).strip() == ""


def main() -> int:
    BASE.AUTHORITY_HYPOTHESIS_ID = AUTHORITY_HYPOTHESIS_ID
    BASE.COMPARATOR_ATTEMPT_ID = COMPARATOR_ATTEMPT_ID
    BASE.COMPARATOR_ROOT = COMPARATOR_ROOT
    BASE.__file__ = str(Path(__file__).resolve())
    BASE.validate_registry_authority = validate_registry_authority
    BASE.validate_authority_bound_files = validate_authority_bound_files
    BASE.validate_oracle_chain_after_claim = validate_oracle_chain_after_claim
    BASE.orders_section_is_empty = orders_section_is_empty
    return BASE.main()


if __name__ == "__main__":
    raise SystemExit(main())
