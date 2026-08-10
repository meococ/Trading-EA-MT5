import importlib.util
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[4]
RUNNER = ROOT / "03. EA Developer" / "EA_SupertrendBurstScalperTradeV4" / "research" / "run_stbs015_model0_audit.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("stbs015_runner", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_outer_and_inner_identities_are_explicit() -> None:
    module = load_runner()
    assert module.HYPOTHESIS_ID == "HYP-STBS-XAUUSD-M15-015"
    assert module.INNER_HYPOTHESIS_ID == "HYP-STBS-XAUUSD-M15-014"
    assert module.ATTEMPT_ID == "STBS015-MODEL0-AUDIT-001"
    assert "InpHypothesisId=HYP-STBS-XAUUSD-M15-014" in module.OVERRIDES


def test_current_spread_is_semantic_only_not_a_cli_argument() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert '"spread": "current"' in source
    assert '"-Spread"' not in source


def test_inner_journal_identity_is_validated() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert '"hypothesis": INNER_HYPOTHESIS_ID' in source
    assert "stable_hypothesis = INNER_HYPOTHESIS_ID" in source


def test_parent_terminal_and_failure_evidence_are_required() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert "parent_hyp014_terminal_row_sha256" in source
    assert "parent_hyp014_failure_path" in source
    assert "parent_hyp014_attempt_terminal_path" in source
