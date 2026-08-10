from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
RUNNER = ROOT / "03. EA Developer" / "EA_SupertrendBurstScalperTradeV5" / "research" / "run_stbs016_model0_audit.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("stbs016_runner", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def make_journal() -> str:
    signals: list[str] = []
    start = 1_514_944_800
    for index in range(690):
        source = start + index * 3600
        decision = source + 3600
        if index < 683:
            direction = "LONG" if index < 339 else "SHORT"
            payload = (
                f"STBS_SIGNAL|source_epoch={source}|decision_epoch={decision}|direction={direction}|"
                "exact_next=true|atr_ready=true|geometry_ready=true|margin_ready=true|"
                "volume=0.09000000|projected_free=99500.00000000|"
                "required_free=93600.00000000|audit=true"
            )
        else:
            payload = (
                f"STBS_SIGNAL|source_epoch={source}|decision_epoch={decision}|direction=LONG|"
                "exact_next=false|consumed=true|audit=true"
            )
        signals.append(payload)
    summary = (
        "STBS_SUMMARY|hypothesis=HYP-STBS-XAUUSD-M15-016|reason=0|raw=690|"
        "executable=683|gaps=7|long=339|short=344|atr_ready=683|geometry_ready=683|"
        "margin_ready=683|margin_rejects=0|margin_emergencies=0|forced_stopouts=0|"
        "entries=0|entry_rejects=0|closes=0|lifecycle_open_rows=0|"
        "lifecycle_final_close_rows=0|lifecycle_positions_opened=0|"
        "lifecycle_positions_final_closed=0|exec_state=0|exit_intent=0|failed=false"
    )
    one_root = [*signals, summary]
    return "\n".join([*one_root, *one_root]) + "\n"


def test_fresh_identity_account_and_cli_contract() -> None:
    module = load_runner()
    source = RUNNER.read_text(encoding="utf-8")
    assert module.HYPOTHESIS_ID == "HYP-STBS-XAUUSD-M15-016"
    assert module.INNER_HYPOTHESIS_ID == "HYP-STBS-XAUUSD-M15-016"
    assert module.PARENT_HYPOTHESIS_ID == "HYP-STBS-XAUUSD-M15-015"
    assert module.ATTEMPT_ID == "STBS016-MODEL0-AUDIT-001"
    assert module.EA_NAME == "EA_SupertrendBurstScalperTradeV5"
    assert module.MAGIC == 5604116
    assert '"deposit": 100000' in source
    assert '"-Deposit", "100000"' in source
    assert '"spread": "current"' in source
    assert '"-Spread"' not in source


def test_complete_duplicate_journal_passes() -> None:
    module = load_runner()
    result = module.validate_journal_text(make_journal())
    assert result["summary_multiplicity"] == 2
    assert result["signal_multiplicity"] == 2
    assert result["verified_counts"]["margin_ready"] == 683


@pytest.mark.parametrize(
    "old,new,error",
    [
        ("required_free=93600.00000000", "required_free=93600.01", "account-safe margin"),
        ("projected_free=99500.00000000", "projected_free=93599.00", "account-safe margin"),
        ("volume=0.09000000", "volume=0.00000000", "account-safe margin"),
        ("decision_epoch=1514948400", "decision_epoch=1514948401", "clock mismatch"),
    ],
)
def test_margin_and_clock_mutations_fail(old: str, new: str, error: str) -> None:
    module = load_runner()
    journal = make_journal().replace(old, new)
    with pytest.raises(RuntimeError, match=error):
        module.validate_journal_text(journal)


def test_signal_schema_and_duplicate_payload_fail_closed() -> None:
    module = load_runner()
    with pytest.raises(RuntimeError, match="field allowlist"):
        module.validate_journal_text(make_journal().replace("|audit=true", "|extra=1|audit=true"))
    journal = make_journal()
    needle = "volume=0.09000000"
    first = journal.find(needle, journal.find("STBS_SUMMARY|") + 1)
    tampered = journal[:first] + "volume=0.08000000" + journal[first + len(needle) :]
    with pytest.raises(RuntimeError, match="non-identical duplicate"):
        module.validate_journal_text(tampered)


def test_parent_and_zero_authority_boundary_are_explicit() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert "E611136E39A8BC6336DFC06995458239EB231BBE5456C1B9B4E685404658E472" in source
    assert "parent_hyp015_failure_path" in source
    assert "parent_hyp015_post_failure_review_path" in source
    assert "parent_hyp015_attempt_terminal_path" in source
    for flag in (
        "trade_api_authorized", "performance_metrics_authorized", "outcome_prices_authorized",
        "economics_authorized", "optimization_authorized", "validation_authorized",
        "holdout_authorized", "paper_trading_authorized", "live_trading_authorized",
        "same_id_retry_authorized", "registry_mutation_allowed",
    ):
        assert flag in source


def test_exact_account_fingerprint_is_100k_contract() -> None:
    module = load_runner()
    assert module.EXPECTED_ACCOUNT_SHA == "0A603E7B316F58B39FEA0A1710FE6F250E544909DA2B91967C93AD984317A073"
    assert module.EXPECTED_DIFF_PROOF_SHA == "9516B9587F0EA8AA01DDC78E8F4C7F671A8CECB777C64E8F4A3CE3C60158F55C"
    assert module.sha256_file(module.DIFF_PROOF) == module.EXPECTED_DIFF_PROOF_SHA
    assert "reviewed_diff_proof_path" in RUNNER.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "mutation,error",
    [
        (lambda text: text.replace("|reason=0|", "|reason=1|"), "summary reason"),
        (lambda text: text.replace("|reason=0|", "|reason=0|reason=0|"), "duplicate"),
        (lambda text: text.replace("|reason=0|", "|reason=0|bare|"), "bare/empty"),
        (lambda text: text.replace("|reason=0|", "|reason=0|extra=1|"), "field allowlist"),
        (lambda text: text.replace("|reason=0|", "|reason=|"), "empty/duplicate"),
    ],
)
def test_summary_parser_is_exact_and_fail_closed(mutation, error: str) -> None:
    module = load_runner()
    with pytest.raises(RuntimeError, match=error):
        module.validate_journal_text(mutation(make_journal()))


def test_complete_journal_manifest_gate_is_exact() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert 'journal_contract.get("max_journal_delta_bytes") == 1048576' in source
    assert 'journal_delta.get("files_read") == 2' in source
    assert 'journal_delta.get("truncated") is False' in source
    assert '0 < journal_delta["bytes_read"] < 1048576' in source
    assert "funding.profit == 100000.0" in source
    assert "funding.balance == 100000.0" in source


def test_reserved_preflight_bytes_and_attempt_root_are_pristine() -> None:
    module = load_runner()
    assert module.TASK_PACKET.read_text(encoding="utf-8-sig").strip() == "{}"
    assert module.RECEIPT.read_text(encoding="utf-8-sig").strip() == "{}"
    assert not module.ATTEMPT_ROOT.exists()
