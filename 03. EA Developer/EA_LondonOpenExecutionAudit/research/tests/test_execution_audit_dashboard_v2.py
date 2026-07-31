from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest


PACKAGE = Path(__file__).resolve().parents[2]
RESEARCH = PACKAGE / "research"
RENDERER = RESEARCH / "render_execution_audit_dashboard_v2.py"
VALIDATOR_RESULT = (
    RESEARCH
    / "evidence"
    / "HYP-LOMX-EXEC-AUDIT-M1-003_MODEL0_AUDIT_READOUT_V2.json"
)


def load_renderer():
    if str(RESEARCH) not in sys.path:
        sys.path.insert(0, str(RESEARCH))
    spec = importlib.util.spec_from_file_location("audit_dashboard_v2", RENDERER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def valid_inputs(module):
    payload = json.loads(VALIDATOR_RESULT.read_text(encoding="utf-8"))
    run_dirs = {
        row["scenario"]: Path(row["run_dir"])
        for row in payload["scenario_results"]
    }
    return payload, run_dirs


def test_dashboard_gate_accepts_only_v2_bound_runs() -> None:
    module = load_renderer()
    payload, run_dirs = valid_inputs(module)
    module.validate_validator_payload(payload, run_dirs)


@pytest.mark.parametrize("mutation", ["failed", "wrong_run"])
def test_dashboard_gate_rejects_false_pass_or_substituted_run(mutation: str) -> None:
    module = load_renderer()
    payload, run_dirs = valid_inputs(module)
    payload = copy.deepcopy(payload)
    if mutation == "failed":
        payload["passed"] = False
    else:
        payload["scenario_results"][0]["run_dir"] = str(Path("D:/substituted-run"))
    with pytest.raises(RuntimeError):
        module.validate_validator_payload(payload, run_dirs)
