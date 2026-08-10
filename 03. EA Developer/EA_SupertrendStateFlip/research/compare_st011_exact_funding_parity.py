#!/usr/bin/env python3
"""Run HYP011 parity with one exact MT5 funding row and no order rows."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
AUTHORITY_HYPOTHESIS_ID = "HYP-ST-XAUUSD-H1-011"
COMPARATOR_ATTEMPT_ID = "ST011-COMPARATOR-001"
COMPARATOR_ROOT = ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/evidence/HYP-ST-XAUUSD-H1-011/ST011-COMPARATOR-001"
HYP010_COMPARATOR_SHA256 = "434D79CEE674FB19F38F9CFBCDE6E5A2EB0A63F947719B4E78F49DAB5A1C6823"
HYP010_TERMINAL_ROW_SHA256 = "E46E10C7DC99508D2CFD7AA7E14FACA740C40E09172E08AB75A7F631B7314039"
HYP010_START_SHA256 = "42A53DCF431951558EB25706F8E6621A9EADF1CBDE3B55BD4FE7AB9628976F6D"
HYP010_TERMINAL_SHA256 = "3E890897AEEBF902449B4A3726516254A8AB10BAACECA708F83F35C180C17233"
HYP010_FAILURE_SHA256 = "7CF5722F89DECABD6EE1C5F26A1A0719AD733C866B59E966F4C2902B1F828FF0"
HYP010_REVIEW_SHA256 = "4DE34D5F5A708CCCC6D29DD6E0A8E2995C56945536769284CBEFD534834ADBDE"
REPORT_SHA256 = "178901C855F050FA18217762509F791870D8CB2A2903CEF08C0436E8A7EE79EB"
QUANT_ANALYZER_SHA256 = "A7F93E8DC35A2FC7A273419500E7B41DF742F828613C48EDA3D5C766C042616B"
HYP010_START_PATH = ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/evidence/HYP-ST-XAUUSD-H1-010/ST010-COMPARATOR-001/attempt_started.json"
HYP010_TERMINAL_PATH = ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/evidence/HYP-ST-XAUUSD-H1-010/ST010-COMPARATOR-001/attempt_terminal.json"
HYP010_FAILURE_PATH = ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/HYP-ST-XAUUSD-H1-010_ZERO_TRADE_REPORT_VALIDATOR_FAILURE.md"
HYP010_REVIEW_PATH = ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/HYP-ST-XAUUSD-H1-010_POST_FAILURE_REVIEW.md"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_hyp010():
    path = Path(__file__).resolve().with_name("compare_st010_sealed_recovery_parity.py")
    if sha256_file(path) != HYP010_COMPARATOR_SHA256:
        raise ValueError("frozen HYP010 comparator dependency hash drift")
    spec = importlib.util.spec_from_file_location("st011_hyp010_comparator_dependency", path)
    if not spec or not spec.loader:
        raise ValueError("cannot load frozen HYP010 comparator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BASE = load_hyp010()
ORIGINAL_BOUND_VALIDATOR = BASE.validate_authority_bound_files


def registry_rows(path: Path, hypothesis_id: str) -> list[tuple[bytes, dict[str, Any]]]:
    matches: list[tuple[bytes, dict[str, Any]]] = []
    for raw in path.read_bytes().splitlines():
        if raw.strip():
            row = json.loads(raw.decode("utf-8"))
            if row.get("hypothesis_id") == hypothesis_id:
                matches.append((raw, row))
    return matches


def validate_registry_authority(registry_path: Path, args: Any) -> tuple[dict[str, Any], dict[str, str]]:
    matches = registry_rows(registry_path, AUTHORITY_HYPOTHESIS_ID)
    if not matches:
        raise ValueError("missing HYP011 comparator authority")
    raw, row = matches[-1]
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    checks = {
        "state": row.get("state") == "screened",
        "model": row.get("model") == 0,
        "verdict": row.get("verdict") == "FROZEN_ST011_EXACT_FUNDING_COMPARATOR_AUTHORIZED",
        "wrapper": validation.get("reviewed_exact_funding_comparator_sha256") == sha256_file(Path(__file__).resolve()),
        "dependency": validation.get("reviewed_hyp010_comparator_sha256") == HYP010_COMPARATOR_SHA256,
        "test_metadata": isinstance(validation.get("reviewed_exact_funding_test_sha256"), str)
        and len(validation.get("reviewed_exact_funding_test_sha256")) == 64
        and validation.get("reviewed_sealed_comparator_test_sha256")
        == validation.get("reviewed_exact_funding_test_sha256"),
        "source": validation.get("reviewed_mql_source_sha256") == BASE.BASE.EXPECTED_SOURCE_SHA256,
        "source_path": args.mql_source.resolve() == BASE.RUN_SOURCE_SNAPSHOT.resolve()
        and validation.get("reviewed_mql_source_path") == "02. AlphaFactory/runs/EA_SupertrendStateFlip/20260809_064257/snapshot/source/EA_SupertrendStateFlip.mq5",
        "hyp010_row": validation.get("hyp010_terminal_row_sha256") == HYP010_TERMINAL_ROW_SHA256,
        "hyp010_start": validation.get("hyp010_comparator_start_sha256") == HYP010_START_SHA256,
        "hyp010_terminal": validation.get("hyp010_comparator_terminal_sha256") == HYP010_TERMINAL_SHA256,
        "hyp010_failure": validation.get("hyp010_failure_sha256") == HYP010_FAILURE_SHA256,
        "hyp010_review": validation.get("hyp010_post_failure_review_sha256") == HYP010_REVIEW_SHA256,
        "report": validation.get("tester_report_sha256") == REPORT_SHA256,
        "analyzer": validation.get("quant_analyzer_sha256") == QUANT_ANALYZER_SHA256,
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
        raise ValueError(f"HYP011 authority failed: {failed}")
    return row, {
        "registry_sha256": sha256_file(registry_path),
        "latest_row_sha256": hashlib.sha256(raw).hexdigest().upper(),
    }


def validate_authority_bound_files(args: Any) -> None:
    ORIGINAL_BOUND_VALIDATOR(args)
    matches = registry_rows(args.registry.resolve(), AUTHORITY_HYPOTHESIS_ID)
    if not matches:
        raise ValueError("missing HYP011 post-claim authority")
    _, row = matches[-1]
    validation = row.get("validation", {})
    if sha256_file(args.test_source.resolve()) != validation.get("reviewed_exact_funding_test_sha256"):
        raise ValueError("HYP011 exact-funding test binding mismatch")
    bindings = {
        "hyp010_start": (HYP010_START_PATH, validation.get("hyp010_comparator_start_sha256")),
        "hyp010_terminal": (HYP010_TERMINAL_PATH, validation.get("hyp010_comparator_terminal_sha256")),
        "hyp010_failure": (HYP010_FAILURE_PATH, validation.get("hyp010_failure_sha256")),
        "hyp010_review": (HYP010_REVIEW_PATH, validation.get("hyp010_post_failure_review_sha256")),
        "tester_report": (args.tester_report, validation.get("tester_report_sha256")),
        "quant_analyzer": (ROOT / "02. AlphaFactory/analysis/quant_analyzer.py", validation.get("quant_analyzer_sha256")),
    }
    for label, (path, expected) in bindings.items():
        BASE.BASE.BASE.require_bound_file(path.resolve(), str(expected or ""), label)


def validate_oracle_chain_after_claim(args: Any) -> None:
    validate_authority_bound_files(args)
    BASE.ORIGINAL_ORACLE_CHAIN_VALIDATOR(args)


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
    cells = [re.findall(r"<td[^>]*>(.*?)</td>", row, re.I | re.S) for row in rows]
    if len(cells[0]) != 13 or not all(re.search(r"<b>.*?</b>", cell, re.I | re.S) for cell in cells[0]):
        return False
    spacer_text = re.sub(r"<[^>]+>", "", cells[1][0]).strip() if len(cells[1]) == 1 else "not-empty"
    return spacer_text == ""


def exact_funding_deals(deals: list[Any], deal_type: Any) -> bool:
    expected = deal_type(
        time=datetime(2005, 1, 1, 0, 0, 0),
        deal_id=1,
        symbol="",
        side="balance",
        direction="",
        volume=0.0,
        price=0.0,
        order_id=None,
        commission=0.0,
        swap=0.0,
        profit=10000.0,
        balance=10000.0,
        comment="",
    )
    return deals == [expected]


def validate_alpha_run(args: Any, authority_row: dict[str, Any]) -> dict[str, Any]:
    del authority_row
    engine = BASE.BASE
    core = engine.BASE
    run_dir = args.alpha_run_dir.resolve()
    manifest = engine.load_json(args.run_manifest)
    exact = {
        "schema_version": "alphafactory_run_manifest.v2",
        "hypothesis_id": engine.RUN_HYPOTHESIS_ID,
        "run_role": "control",
        "ea_name": "EA_SupertrendStateFlip",
        "symbol": "XAUUSD",
        "period": "H1",
        "from": "2005.01.01",
        "to": "2023.01.01",
        "model": 0,
        "execution_mode": 0,
        "fixed_delay_ms": 0,
        "overrides": core.EXACT_OVERRIDES,
        "telemetry_tier": "off",
        "telemetry_profile": "none",
        "deposit": 10000,
        "leverage": 100,
        "spread": "current",
    }
    wrong = [key for key, value in exact.items() if manifest.get(key) != value]
    if wrong or args.run_manifest.resolve() != run_dir / "run_manifest.json":
        raise ValueError(f"inherited HYP008 run contract mismatch: {wrong}")
    if sha256_file(args.run_manifest) != engine.EXPECTED_RUN_MANIFEST_SHA256:
        raise ValueError("inherited HYP008 run manifest hash mismatch")
    if Path(str(manifest.get("local_run_dir", ""))).resolve() != run_dir:
        raise ValueError("inherited run local_run_dir mismatch")
    source_snapshot = run_dir / "snapshot/source/EA_SupertrendStateFlip.mq5"
    ex5_snapshot = run_dir / "snapshot/build/EA_SupertrendStateFlip.ex5"
    if (
        args.compiled_ex5.resolve() != ex5_snapshot
        or sha256_file(source_snapshot) != engine.EXPECTED_SOURCE_SHA256
        or sha256_file(ex5_snapshot) != engine.EXPECTED_EX5_SHA256
        or manifest.get("source_sha256") != engine.EXPECTED_SOURCE_SHA256
        or manifest.get("ex5_sha256") != engine.EXPECTED_EX5_SHA256
        or manifest.get("tester_ex5_sha256") != engine.EXPECTED_EX5_SHA256
        or sha256_file(args.compile_log.resolve()) != engine.EXPECTED_COMPILE_SHA256
        or sha256_file(args.tester_report.resolve()) != REPORT_SHA256
        or manifest.get("report_sha256") != REPORT_SHA256
        or manifest.get("contract_receipt_sha256") != sha256_file(args.contract_receipt.resolve())
    ):
        raise ValueError("inherited HYP008 source/compile/report binding mismatch")
    compile_text = core.decode_text(args.compile_log)
    if re.search(r"\b0\s+errors?\b", compile_text, re.I) is None or re.search(r"\b0\s+warnings?\b", compile_text, re.I) is None:
        raise ValueError("recovered compile log does not prove 0E/0W")
    journal = core.decode_text(args.tester_journal)
    if journal != engine.FROZEN_SUMMARY + "\n" or "ST003_FATAL" in journal:
        raise ValueError("normalized HYP009 tester summary mismatch")

    analyzer_path = ROOT / "02. AlphaFactory/analysis/quant_analyzer.py"
    if sha256_file(analyzer_path) != QUANT_ANALYZER_SHA256:
        raise ValueError("quant analyzer hash drift")
    spec = importlib.util.spec_from_file_location("st011_quant_analyzer", analyzer_path)
    if not spec or not spec.loader:
        raise ValueError("cannot load quant analyzer")
    analyzer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = analyzer
    spec.loader.exec_module(analyzer)
    deals = analyzer.parse_deals_from_html_report(args.tester_report)
    if not exact_funding_deals(deals, analyzer.Deal):
        raise ValueError("HYP008 report is not exact sole funding-balance row")
    if not orders_section_is_empty(core.decode_text(args.tester_report)):
        raise ValueError("HYP008 report Orders section is not exactly empty")
    core.tree_sha256(run_dir)
    return manifest


def main() -> int:
    BASE.AUTHORITY_HYPOTHESIS_ID = AUTHORITY_HYPOTHESIS_ID
    BASE.COMPARATOR_ATTEMPT_ID = COMPARATOR_ATTEMPT_ID
    BASE.COMPARATOR_ROOT = COMPARATOR_ROOT
    BASE.__file__ = str(Path(__file__).resolve())
    BASE.validate_registry_authority = validate_registry_authority
    BASE.validate_authority_bound_files = validate_authority_bound_files
    BASE.validate_oracle_chain_after_claim = validate_oracle_chain_after_claim
    BASE.BASE.validate_alpha_run = validate_alpha_run
    return BASE.main()


if __name__ == "__main__":
    raise SystemExit(main())
