from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "evaluate_eurfximm_eurusd_002_train.py"
SPEC = importlib.util.spec_from_file_location("eurfximm002", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_parent_hash_and_exact_successor_identity() -> None:
    assert MODULE.sha256_file(MODULE.workspace() / MODULE.PARENT_REL) == MODULE.PARENT_SHA256
    foundation = MODULE.configure()
    assert foundation.HYPOTHESIS_ID == MODULE.HYPOTHESIS_ID
    assert foundation.ATTEMPT_ID == MODULE.ATTEMPT_ID
    assert foundation.PLAN_SHA256 == MODULE.PLAN_SHA256
    assert foundation.DISPLAY_TAG == "HYPIMM002"
    assert foundation.ARTIFACT_PREFIX == "EURFXIMM002"
    assert foundation.SCHEMA_PREFIX == "eurfximm002"
    assert foundation.ALLOWED_MISSING_TARGET_DATES == ("2017-09-28",)


def test_terminal_entrypoint_reads_public_primary_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    terminal = tmp_path / "terminal.json"
    terminal.write_text(
        json.dumps(
            {
                "verdict": "KILL_TEST",
                "metrics": {
                    "trade_count": 608,
                    "economic_gate_pass_count": 0,
                    "economic_gate_total": 9,
                    "arms": {
                        "flow_continuation_primary": {
                            "profit_factor": {"x1": 0.75}
                        }
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    fake = SimpleNamespace(
        ContractError=RuntimeError,
        execute=lambda root: terminal,
    )
    monkeypatch.setattr(MODULE, "configure", lambda root=None: fake)
    assert MODULE.main(["--workspace", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "pf_x1=0.75" in out
    assert "trades=608" in out


def test_disarmed_or_armed_sentinel_normalization_is_stable() -> None:
    value = MODULE.REVIEWED_REGISTRY_ROW_SHA256
    assert value is None or (isinstance(value, str) and len(value) == 64)
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
