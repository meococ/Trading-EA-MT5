from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HYPOTHESIS_ID = "HYP-STBS-XAUUSD-M15-021"
EA_NAME = "EA_SupertrendBurstScalperTradeV8"
PACKAGE = ROOT / "03. EA Developer" / EA_NAME
REGISTRY = ROOT / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
SOURCE = PACKAGE / f"{EA_NAME}.mq5"
PREREG = PACKAGE / "research" / f"{HYPOTHESIS_ID}_MODEL0_BASELINE_PREREG.md"
EA_CONTRACT = PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json"
COST_MANIFEST = PACKAGE / "research" / f"{HYPOTHESIS_ID}_RESEARCH_COST_SOURCE_MANIFEST.json"
OUTPUT = PACKAGE / "research" / "preflight" / HYPOTHESIS_ID / "V1" / "task_packet.control.json"

EXPECTED_SOURCE_SHA256 = "11E44FF9B51DA50F6DF25C54858BFF492C89A58EED04684C828A70740B37FED9"
EXPECTED_PREREG_SHA256 = "ADE0D4831D0C97C4A3E50BB00C0760E00E03B1C5AFE0626BDEA29D03553EE9C9"
EXPECTED_CONTRACT_SHA256 = "891E6636F45B263F6163F5E703C9E87B912846B114CE25D5E45517871FD28057"
EXPECTED_COST_SHA256 = "0FBFDE0F0BCC4E6F829EAA7812D530AF99106E5641444DF3DD2A390353A06215"
EXPECTED_REGISTRY_ROW_SHA256 = "D1A8C24DCBDDDA29D85D340D04FCDABB01B15FA771897A1E70C2C6BB08886B83"
OVERRIDES = (
    "InpAuditOnly=false;InpEnableTelemetry=true;"
    "InpHypothesisId=HYP-STBS-XAUUSD-M15-021;InpMagic=5604121;"
    "InpMaxNewPositionMarginPct=5.0;InpMinProjectedMarginLevelPct=2000.0;"
    "InpMoneyFreeEquityFloorPct=1.0;InpMoneyHeadroomReserveFactor=0.20;"
    "InpPercentStopoutHeadroomFactor=1.25;"
    "InpVariantTag=STBS_H1_FLIP_M15_BURST_TRADE_V8_STABLE_LIFECYCLE"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def repo_relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.rstrip("\r\n")


def latest_registry_identity() -> tuple[str, dict]:
    rows = [line for line in REGISTRY.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise RuntimeError("candidate registry is empty")
    raw = rows[-1]
    row = json.loads(raw)
    row_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()
    if row.get("hypothesis_id") != HYPOTHESIS_ID or row.get("state") != "screened":
        raise RuntimeError("latest registry row is not the frozen HYP021 screened authority")
    if row_hash != EXPECTED_REGISTRY_ROW_SHA256:
        raise RuntimeError(f"HYP021 authority row drift: {row_hash}")
    return row_hash, row


def main() -> None:
    frozen = {
        SOURCE: EXPECTED_SOURCE_SHA256,
        PREREG: EXPECTED_PREREG_SHA256,
        EA_CONTRACT: EXPECTED_CONTRACT_SHA256,
        COST_MANIFEST: EXPECTED_COST_SHA256,
    }
    for path, expected in frozen.items():
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(f"frozen input drift: {repo_relative(path)} {actual}")

    registry_row_sha256, _ = latest_registry_identity()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if not OUTPUT.exists():
        OUTPUT.write_text("{}\n", encoding="utf-8", newline="\n")

    git_status = git("status", "--short", "--untracked-files=all").splitlines()
    git_status_payload = "\n".join(git_status).encode("utf-8")
    packet = {
        "schema_version": "alphafactory_research_task_packet.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "inner_implementation_hypothesis_id": HYPOTHESIS_ID,
        "run_role": "control",
        "ea_name": EA_NAME,
        "symbol": "XAUUSD",
        "period": "M15",
        "from": "2005.01.01",
        "to": "2023.01.01",
        "economic_window": {"from": "2018.01.02", "to": "2022.12.30"},
        "model": 0,
        "execution_mode": 0,
        "fixed_delay_ms": 0,
        "timeout_sec": 900,
        "attempt_id": "STBS021-MODEL0-TRAIN-001",
        "attempt_limit": 1,
        "overrides": OVERRIDES,
        "telemetry_tier": "trade-only",
        "telemetry_profile": "lifecycle-v3",
        "comparison_adapter": "generic-control-improvement-v1",
        "deposit": 100000,
        "leverage": 100,
        "spread": "current",
        "required_sidecars": ["*_LifecycleTrades_*.csv", "*_RunMeta_*.json"],
        "visual_mode": False,
        "indicator_dependencies": [],
        "broker_fingerprint": "E464F31D4B323A66DBC18D9409052E70F3711DB8F23597441648B19296B61D54",
        "server_fingerprint": "30B251638403D085CAB177A77A1B0EB69BD371793B501BE696F08033BE1E8DB0",
        "account_fingerprint": "0A603E7B316F58B39FEA0A1710FE6F250E544909DA2B91967C93AD984317A073",
        "data_fingerprint": "B326D511C805C7998DF1C2FC540770B6EC3054D0D4BCBB41A5A4E3C2E4239D25",
        "symbol_geometry": {"digits": 2, "point": 0.01, "pip_size": 0.01},
        "include_closure_sha256": "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855",
        "data_quality_contract": {
            "history_quality": {"operator": "gt", "value": 97.0},
            "coverage_mode": "fixed_window",
            "availability_asof_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "requested_from": "2005.01.01",
            "requested_to": "2023.01.01",
            "require_tester_journal_bounds": True,
        },
        "source_path": repo_relative(SOURCE),
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "registry_path": repo_relative(REGISTRY),
        "registry_sha256": sha256_file(REGISTRY),
        "registry_row_sha256": registry_row_sha256,
        "prereg_path": repo_relative(PREREG),
        "prereg_sha256": EXPECTED_PREREG_SHA256,
        "ea_contract_path": repo_relative(EA_CONTRACT),
        "ea_contract_sha256": EXPECTED_CONTRACT_SHA256,
        "validation_stage": "challenger",
        "holding_contract": "scalp",
        "include_closure": [],
        "required_manifest_hashes": [
            "source_sha256", "config_sha256", "report_sha256", "ex5_sha256", "includes_sha256"
        ],
        "cost_source_manifest_path": repo_relative(COST_MANIFEST),
        "cost_source_manifest_sha256": EXPECTED_COST_SHA256,
        "cost_evidence_tier": "research_proxy",
        "acceptance_contract": {
            "min_profit_factor": 1.3,
            "min_trades_per_week": 2,
            "max_trades_per_week": 5,
            "max_drawdown_pct": 8,
            "min_cost_pf_x1_5": 1.25,
            "min_cost_pf_x2": 1,
            "max_monte_carlo_p95_dd_pct": 8,
        },
        "baseline_acceptance_contract": {
            "min_completed_trades": 500,
            "min_direction_share": 0.30,
            "max_year_trade_share": 0.30,
            "require_positive_cost_expectancy": True,
            "require_all_calendar_years_positive": True,
        },
        "performance_metrics_authorized": True,
        "economics_authorized": True,
        "promotion_eligible": False,
        "git_commit": git("rev-parse", "HEAD"),
        "git_status": git_status,
        "git_status_sha256": hashlib.sha256(git_status_payload).hexdigest().upper(),
    }

    payload = (json.dumps(packet, ensure_ascii=True, indent=2) + "\n").encode("utf-8")
    fd, temp_name = tempfile.mkstemp(prefix=".task_packet.", suffix=".tmp", dir=OUTPUT.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, OUTPUT)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    print(json.dumps({"status": "BUILT", "path": repo_relative(OUTPUT), "sha256": sha256_file(OUTPUT), "git_status_sha256": packet["git_status_sha256"]}))


if __name__ == "__main__":
    main()
