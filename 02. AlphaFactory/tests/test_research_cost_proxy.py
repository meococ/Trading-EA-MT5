from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest


ALPHA_ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ALPHA_ROOT / "tools" / "build_verified_cost_artifact.py"
UNIFIED_PATH = ALPHA_ROOT / "analysis" / "unified_validation.py"
RUNNER_PATH = ALPHA_ROOT / "tools" / "research_loop_engine.ps1"


def _load_builder():
    spec = importlib.util.spec_from_file_location("research_cost_proxy_builder", BUILDER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_unified():
    spec = importlib.util.spec_from_file_location("research_cost_proxy_unified", UNIFIED_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _proxy_fixture(tmp_path: Path) -> tuple[dict, Path, dict]:
    spread_path = tmp_path / "spread.csv"
    _write_csv(
        spread_path,
        ["timestamp", "symbol", "bid", "ask"],
        [
            {"timestamp": "2024-01-02 08:00:00", "symbol": "XAUUSD", "bid": 2040.00, "ask": 2040.20},
            {"timestamp": "2025-12-24 08:00:00", "symbol": "XAUUSD", "bid": 2600.00, "ask": 2600.25},
        ],
    )

    commission_path = tmp_path / "commission.csv"
    _write_csv(
        commission_path,
        [
            "position_id",
            "symbol",
            "account_currency",
            "round_turn_account_per_lot",
            "source_kind",
        ],
        [
            {
                "position_id": str(index + 1),
                "symbol": "XAUUSD",
                "account_currency": "USD",
                "round_turn_account_per_lot": 4.4 if index == 29 else 2.0,
                "source_kind": "strategy_tester_simulation",
            }
            for index in range(30)
        ],
    )

    quote_path = tmp_path / "quote_latency.csv"
    quote_rows: list[dict[str, object]] = []
    start = datetime(2026, 7, 14, 8, 0, 0)
    for index in range(50):
        reference = 2400.0 + index * 0.01
        adverse_pips = index % 5
        reference_time = start + timedelta(seconds=index * 2)
        future_time = reference_time + timedelta(seconds=1)
        quote_rows.append(
            {
                "sample_id": f"BUY-{index}",
                "reference_timestamp": reference_time.isoformat(),
                "future_timestamp": future_time.isoformat(),
                "symbol": "XAUUSD",
                "side": "BUY",
                "reference_side": "ask",
                "reference_price": reference,
                "future_quote_price": reference + adverse_pips * 0.01,
                "pip_size": 0.01,
                "latency_ms": 1000,
                "actual_delay_ms": 1000,
            }
        )
        quote_rows.append(
            {
                "sample_id": f"SELL-{index}",
                "reference_timestamp": reference_time.isoformat(),
                "future_timestamp": future_time.isoformat(),
                "symbol": "XAUUSD",
                "side": "SELL",
                "reference_side": "bid",
                "reference_price": reference,
                "future_quote_price": reference - adverse_pips * 0.01,
                "pip_size": 0.01,
                "latency_ms": 1000,
                "actual_delay_ms": 1000,
            }
        )
    quote_fields = list(quote_rows[0])
    _write_csv(quote_path, quote_fields, quote_rows)

    manifest = {
        "broker_fingerprint": "A" * 64,
        "server_fingerprint": "B" * 64,
        "account_fingerprint": "C" * 64,
        "data_fingerprint": "D" * 64,
        "symbol": "XAUUSD",
        "from": "2024.01.01",
        "to": "2025.12.25",
        "fingerprint_basis": {
            "broker": "Five Percent Online Ltd",
            "server": "FivePercentOnline-Real (Build 6006)",
            "currency": "USD",
            "digits": 2,
            "point": 0.01,
            "pip_size": 0.01,
        },
    }
    payload = {
        "schema_version": "alphafactory_cost_source_manifest.v1",
        "evidence_tier": "RESEARCH_PROXY",
        "provenance_status": "VERIFIED_RESEARCH_PROXY",
        "audit_status": "PASS_RESEARCH_ONLY",
        "verdict": "PASS_RESEARCH_ONLY",
        "promotion_eligible": False,
        "broker": manifest["fingerprint_basis"]["broker"],
        "server": manifest["fingerprint_basis"]["server"],
        "account_currency": "USD",
        "broker_fingerprint": manifest["broker_fingerprint"],
        "server_fingerprint": manifest["server_fingerprint"],
        "account_fingerprint": manifest["account_fingerprint"],
        "data_fingerprint": manifest["data_fingerprint"],
        "symbol": "XAUUSD",
        "from": manifest["from"],
        "to": manifest["to"],
        "symbol_geometry": {"digits": 2, "point": 0.01, "pip_size": 0.01},
        "historical_spread_provenance": {
            "verification_status": "VERIFIED",
            "symbol": "XAUUSD",
            "source": spread_path.name,
            "source_sha256": _sha(spread_path),
            "coverage": {
                "from": manifest["from"],
                "to": manifest["to"],
                "sample_count": 2,
                "total_count": 2,
                "coverage_ratio": 1.0,
            },
        },
        "commission_provenance": {
            "verification_status": "VERIFIED_RESEARCH_PROXY",
            "symbol": "XAUUSD",
            "value": 4.4,
            "statistic": "maximum",
            "sample_count": 30,
            "same_symbol_lifecycles": True,
            "source_kind": "strategy_tester_simulation",
            "method": "maximum tester-observed round-turn commission per lot",
            "source": commission_path.name,
            "source_sha256": _sha(commission_path),
        },
        "slippage_provenance": {
            "verification_status": "VERIFIED_RESEARCH_PROXY",
            "symbol": "XAUUSD",
            "source": quote_path.name,
            "source_sha256": _sha(quote_path),
            "sample_count": 100,
            "buy_count": 50,
            "sell_count": 50,
            "independent_reference": False,
            "independent_quote_reference": True,
            "fill_observed": False,
            "buy_reference_side": "ask",
            "sell_reference_side": "bid",
            "slippage_unit": "pips",
            "fixed_latency_ms": 1000,
            "max_quote_wait_ms": 500,
            "method": "non-overlapping fixed-latency future executable quote proxy",
            "p90_buy": 4.0,
            "p90_sell": 4.0,
            "p90_roundturn": 8.0,
        },
        "direction_aware_methodology": {
            "verification_status": "VERIFIED_RESEARCH_PROXY",
            "direction_aware": True,
            "long_cost_treatment": "ask-to-future-ask adverse move",
            "short_cost_treatment": "bid-to-future-bid adverse move",
        },
    }
    source_path = tmp_path / "cost_source_manifest.json"
    source_path.write_text(json.dumps(payload), encoding="utf-8")
    return payload, source_path, manifest


def test_research_proxy_cost_source_is_explicitly_non_promotable(tmp_path: Path) -> None:
    builder = _load_builder()
    payload, source_path, manifest = _proxy_fixture(tmp_path)

    result = builder.validate_cost_source(payload, source_path, manifest)

    assert result["evidence_tier"] == "RESEARCH_PROXY"
    assert result["promotion_eligible"] is False
    assert result["commission_value"] == pytest.approx(4.4)
    assert result["slippage_p90_roundturn"] == pytest.approx(8.0)
    assert result["slippage"]["fill_observed"] is False


def test_research_proxy_root_cannot_claim_promotion_eligibility(tmp_path: Path) -> None:
    builder = _load_builder()
    payload, source_path, manifest = _proxy_fixture(tmp_path)
    payload["promotion_eligible"] = True

    with pytest.raises(ValueError, match="promotion_eligible"):
        builder.validate_cost_source(payload, source_path, manifest)


def test_unified_validator_requires_explicit_proxy_opt_in() -> None:
    unified = _load_unified()
    payload = {
        "schema_version": "research_execution_cost_proxy.v1",
        "provenance_status": "VERIFIED_RESEARCH_PROXY",
        "stress_mode": "run_bound_research_cost_proxy_repricing",
        "promotion_eligible": False,
        "execution_provenance": {
            "evidence_tier": "RESEARCH_PROXY",
            "promotion_eligible": False,
        },
    }

    with pytest.raises(ValueError, match="explicit opt-in"):
        unified._cost_evidence_scope(payload, allow_research_cost_proxy=False)

    scope = unified._cost_evidence_scope(payload, allow_research_cost_proxy=True)
    assert scope == {
        "evidence_tier": "RESEARCH_PROXY",
        "research_falsification_eligible": True,
        "promotion_eligible": False,
    }


def test_runner_exposes_fail_closed_research_proxy_switch() -> None:
    text = RUNNER_PATH.read_text(encoding="utf-8-sig")
    assert "[switch]$AllowResearchCostProxy" in text
    assert "cost_evidence_tier" in text
    assert "RESEARCH_PROXY requires RunRole=control" in text
    assert '"--allow-research-cost-proxy"' in text
    assert "$backtestParameters = @{" in text
    assert "& $alphaPs1 backtest $EaName @backtestParameters" in text
