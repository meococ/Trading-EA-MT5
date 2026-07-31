from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "evaluate_eurfximm_eurusd_003_train.py"
SPEC = importlib.util.spec_from_file_location("eurfximm003", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_exact_successor_identity_and_only_structural_delta() -> None:
    assert MODULE.sha256_file(MODULE.workspace() / MODULE.PARENT_REL) == MODULE.PARENT_SHA256
    foundation = MODULE.configure()
    assert foundation.HYPOTHESIS_ID == MODULE.HYPOTHESIS_ID
    assert foundation.ATTEMPT_ID == MODULE.ATTEMPT_ID
    assert foundation.ALLOWED_MISSING_TARGET_DATES == ()
    assert MODULE.EXPECTED_TRADES == 609
    assert foundation.DISPLAY_TAG == "HYPIMM003"


def test_summary_correction_replaces_only_exact_trade_gate() -> None:
    trades = list(range(609))
    original = lambda *args, **kwargs: {
        "structural_gates": {
            "source_population_reconciled": True,
            "exact_608_trades": False,
        },
        "structural_gate_pass_count": 1,
        "structural_gate_total": 2,
    }
    metrics = MODULE._correct_summary(original, trades, {}, {}, None)
    assert "exact_608_trades" not in metrics["structural_gates"]
    assert metrics["structural_gates"]["exact_609_trades"] is True
    assert metrics["structural_gate_pass_count"] == 2


def test_terminal_entrypoint_uses_public_primary_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    terminal = tmp_path / "terminal.json"
    terminal.write_text(
        json.dumps(
            {
                "verdict": "KILL_TEST",
                "metrics": {
                    "trade_count": 609,
                    "economic_gate_pass_count": 0,
                    "economic_gate_total": 9,
                    "arms": {
                        "flow_continuation_primary": {
                            "profit_factor": {"x1": 0.81}
                        }
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        MODULE,
        "configure",
        lambda root=None: SimpleNamespace(ContractError=RuntimeError, execute=lambda root: terminal),
    )
    assert MODULE.main(["--workspace", str(tmp_path)]) == 0
    assert "trades=609" in capsys.readouterr().out


def test_disarmed_or_armed_sentinel_normalization_is_stable() -> None:
    value = MODULE.REVIEWED_REGISTRY_ROW_SHA256
    payload = SCRIPT.read_bytes()
    base = MODULE.normalized_evaluator_base_sha256(payload)
    if value is None:
        armed = payload.replace(
            b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None",
            b'REVIEWED_REGISTRY_ROW_SHA256: str | None = "' + b"A" * 64 + b'"',
            1,
        )
    else:
        armed = payload.replace(value.encode("ascii"), b"A" * 64, 1)
    assert MODULE.normalized_evaluator_base_sha256(armed) == base


def test_authority_fails_closed_while_disarmed(tmp_path: Path) -> None:
    foundation = MODULE.configure()
    if MODULE.REVIEWED_REGISTRY_ROW_SHA256 is None:
        with pytest.raises(foundation.ContractError, match="not armed"):
            foundation.validate_authority(tmp_path)
