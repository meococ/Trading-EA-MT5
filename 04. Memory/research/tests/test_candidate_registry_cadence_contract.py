from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "CANDIDATE_REGISTRY.schema.json"


def _contract(minimum: float, maximum: float) -> dict[str, float]:
    return {
        "min_profit_factor": 1.3,
        "min_trades_per_week": minimum,
        "max_trades_per_week": maximum,
        "max_drawdown_pct": 8.0,
        "min_cost_pf_x1_5": 1.25,
        "min_cost_pf_x2": 1.0,
        "max_monte_carlo_p95_dd_pct": 8.0,
    }


def test_schema_allows_mechanism_specific_cadence_outside_legacy_2_to_5() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    cadence_schema = schema["properties"]["acceptance_contract"]

    jsonschema.Draft202012Validator(cadence_schema).validate(_contract(0.25, 1.5))
    jsonschema.Draft202012Validator(cadence_schema).validate(_contract(20.0, 100.0))
    over_legacy_dd = _contract(0.25, 1.5)
    over_legacy_dd["max_drawdown_pct"] = 12.0
    over_legacy_dd["max_monte_carlo_p95_dd_pct"] = 12.0
    jsonschema.Draft202012Validator(cadence_schema).validate(over_legacy_dd)


@pytest.mark.parametrize("minimum,maximum", [(0.0, 5.0), (2.0, 0.0)])
def test_schema_rejects_nonpositive_cadence(minimum: float, maximum: float) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    cadence_schema = schema["properties"]["acceptance_contract"]

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(cadence_schema).validate(
            _contract(minimum, maximum)
        )
