from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "research" / "dukascopy_jetta_h1_validate.py"
spec = importlib.util.spec_from_file_location("dukascopy_jetta_h1_validate", TOOL)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def bar(epoch: int, open_: float, high: float, low: float, close: float):
    return module.source.H1Bar(epoch, open_, high, low, close, 1)


def test_annual_d1_url_handles_static_and_partial_years() -> None:
    assert module.annual_d1_url("EUR-USD", 2025, partial=False).endswith(
        "/day/EUR-USD/BID/2025"
    )
    assert module.annual_d1_url("EUR-USD", 2026, partial=True).endswith(
        "/day/EUR-USD/BID?from=1767225600000"
    )


def test_session_comparison_uses_official_boundaries() -> None:
    h1 = [
        bar(0, 1.0, 1.0, 1.0, 1.0),
        bar(3600, 1.0, 1.2, 0.9, 1.1),
        bar(7200, 1.1, 1.3, 1.0, 1.2),
        bar(10800, 1.2, 1.25, 1.1, 1.15),
    ]
    d1 = [
        bar(0, 1.0, 1.2, 0.9, 1.1),
        bar(7200, 1.1, 1.3, 1.0, 1.15),
        bar(14400, 1.15, 1.15, 1.15, 1.15),
    ]
    result = module.compare_sessions(h1, d1, 0.00001, 0, 14400)
    assert result["status"] == "PASS"
    assert result["common_sessions"] == 2
    assert result["within_one_point_rate"] == 1.0
