#!/usr/bin/env python3
"""Build four strict alphafactory_research_task_packet.v1 preflight packets for MZMS HYP-007..010.

Each arm remains a standalone run_role=control lifecycle packet. InpSignalMode is
not forced to 0; frozen mode identity remains 2/007, 3/008, 4/009, 5/010.

Cost evidence is RESEARCH_PROXY only (promotion_eligible=false), bound to the
campaign full-window M1 spread export plus reused Unicorn non-fill commission
and quote-latency proxy sources.

Post-run identity fields (broker/server/account/data fingerprints) bind the
named report-identity basis derived from completed HYP-007/HYP-008 manifests
using alpha.ps1 Get-ReportIdentity semantics. Spread-export audit fingerprints
remain distinct provenance and must never masquerade as post-run report identity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


EA_NAME = "EA_MZMS_Scalper"
FROM_DATE = "2018.01.01"
TO_DATE = "2026.07.22"
CAMPAIGN_ID = "HYP-MZMS-XAU-M5-007-010"
SHARED_PREREG_NAME = "HYP-MZMS-XAU-M5-007-010_FROZEN_PREREG.md"
SHARED_SNAPSHOT_NAME = "EA_MZMS_Scalper_HYP-MZMS-XAU-M5-007-010.mq5"
EXPECTED_SOURCE_SHA256 = "96A4E8D0CADB0A8B229C124CEB9C70146266A583EEC3D98BB5C406617C80692A"
EXPECTED_PREREG_SHA256 = "ADF33F53F9976FCD12DFA2C78D42F9EBB5D9F09CE1EC5937F00332C4043748F9"
EXPECTED_COMMISSION_SHA256 = "EE5BD051D400D0E49177671DA9AC9C082DC3EBA54F0D45E39566B4AA2744CCEF"
EXPECTED_QUOTE_SHA256 = "515619377D67EADAC3B4A55AFCEE49FC2C5A7EE3D39BBE07B54316D9B9A4836E"

REPORT_IDENTITY_BASIS_NAME = f"{CAMPAIGN_ID}_REPORT_IDENTITY_BASIS.json"
SPREAD_EXPORT_AUDIT_NAME = f"{CAMPAIGN_ID}_SPREAD_EXPORT_AUDIT.json"
REPORT_IDENTITY_SCHEMA = "mzms_report_identity_basis.v1"
IDENTITY_FIELDS = (
    "broker_fingerprint",
    "server_fingerprint",
    "account_fingerprint",
    "data_fingerprint",
)
# Fields that must never silently equal spread-export formulas (broker company may coincide).
EXPORT_CONTRAST_FIELDS = (
    "server_fingerprint",
    "account_fingerprint",
    "data_fingerprint",
)

COMMON_INPUTS = {
    "InpAdxPeriod": "14",
    "InpAtrPeriod": "14",
    "InpBreakEvenR": "1.00",
    "InpCooldownBars": "5",
    "InpDailyLossPct": "1.50",
    "InpEmaPeriod": "200",
    "InpEnableTelemetry": "true",
    "InpFlattenUtcHour": "18",
    "InpFlattenUtcMinute": "15",
    "InpMacdFast": "12",
    "InpMacdSignal": "9",
    "InpMacdSlow": "26",
    "InpMaxAccountDrawdownPct": "8.00",
    "InpMaxHoldBars": "15",
    "InpMaxSpreadPips": "35.00",
    "InpMaxTradesPerDay": "5",
    "InpMinAdx": "18.0",
    "InpMinHistDeltaAtr": "0.01",
    "InpNewsBlackoutMinutes": "15",
    "InpRequireNewsGuard": "false",
    "InpResearchAutoMode": "true",
    "InpRiskPercent": "0.01",
    "InpRsiLower": "42.0",
    "InpRsiPeriod": "14",
    "InpRsiUpper": "58.0",
    "InpServerUsesEuropeDst": "true",
    "InpServerUtcOffsetWinterHours": "2",
    "InpSessionEndUtcHour": "17",
    "InpSessionStartUtcHour": "8",
    "InpStopAtrMultiple": "1.50",
    "InpStopBufferPips": "40.00",
    "InpStopLookbackBars": "5",
    "InpTargetRR": "1.60",
    "InpUseBreakEven": "false",
}

REQUIRED_SIDECARS = [
    "*_LifecycleTrades_*.csv",
    "*_RunMeta_*.json",
    "*_StateTelemetry_*.csv",
]

REQUIRED_MANIFEST_HASHES = [
    "source_sha256",
    "config_sha256",
    "report_sha256",
    "ex5_sha256",
    "includes_sha256",
]

ACCEPTANCE = {
    "min_profit_factor": 1.35,
    "min_trades_per_week": 2.0,
    "max_trades_per_week": 5.0,
    "max_drawdown_pct": 6.0,
    "min_cost_pf_x1_5": 1.25,
    "min_cost_pf_x2": 1.0,
    "max_monte_carlo_p95_dd_pct": 6.0,
}

SYMBOL_GEOMETRY = {
    "digits": 2,
    "point": 0.01,
    "pip_size": 0.01,
}

INCLUDES = (
    "02. AlphaFactory/runtime/mt5-portable-fivepercent/MQL5/Include/Trade/Trade.mqh",
    "02. AlphaFactory/runtime/mt5-portable-fivepercent/MQL5/Include/Object.mqh",
    "02. AlphaFactory/runtime/mt5-portable-fivepercent/MQL5/Include/Trade/OrderInfo.mqh",
    "02. AlphaFactory/runtime/mt5-portable-fivepercent/MQL5/Include/Trade/HistoryOrderInfo.mqh",
    "02. AlphaFactory/runtime/mt5-portable-fivepercent/MQL5/Include/Trade/PositionInfo.mqh",
    "02. AlphaFactory/runtime/mt5-portable-fivepercent/MQL5/Include/Trade/DealInfo.mqh",
    "02. AlphaFactory/runtime/mt5-portable-fivepercent/MQL5/Include/StdLibErr.mqh",
    "03. EA Developer/EA_MZMS_Scalper/NewsCalendar2019_2022.mqh",
)

CANDIDATES = (
    {
        "hypothesis_id": "HYP-MZMS-XAU-M5-007",
        "signal_mode": "2",
        "magic": "5600727",
        "mechanism": "Donchian20FreshImpulseAtrExpansionAdxRise",
    },
    {
        "hypothesis_id": "HYP-MZMS-XAU-M5-008",
        "signal_mode": "3",
        "magic": "5600728",
        "mechanism": "EMA20EMA100TrendPullbackPivotReclaim",
    },
    {
        "hypothesis_id": "HYP-MZMS-XAU-M5-009",
        "signal_mode": "4",
        "magic": "5600729",
        "mechanism": "Bollinger20ATRCompressionEnvelopeBreakout",
    },
    {
        "hypothesis_id": "HYP-MZMS-XAU-M5-010",
        "signal_mode": "5",
        "magic": "5600730",
        "mechanism": "RSIWickADXRollExhaustionRejectionFade",
    },
)

# Fixed candidate table keyed by full hypothesis_id (order preserved from CANDIDATES).
CANDIDATE_BY_ID: dict[str, dict[str, str]] = {
    item["hypothesis_id"]: item for item in CANDIDATES
}
# Short tokens accepted by --ids: "007".."010" (zero-padded three digits).
SHORT_ID_RE = re.compile(r"^\d{3}$")
FULL_ID_PREFIX = "HYP-MZMS-XAU-M5-"


def normalize_id_token(token: str) -> str:
    """Map a CLI token to a full hypothesis_id from the fixed candidate table.

    Accepts short forms (``008``) or full IDs (``HYP-MZMS-XAU-M5-008``).
    """
    raw = str(token).strip()
    if not raw:
        raise ValueError("empty --ids token is not allowed")
    if SHORT_ID_RE.fullmatch(raw):
        hypothesis_id = f"{FULL_ID_PREFIX}{raw}"
    elif raw in CANDIDATE_BY_ID:
        hypothesis_id = raw
    else:
        raise ValueError(
            f"unknown candidate id {token!r}; "
            f"allowed short tokens are 007..010 or full HYP-MZMS-XAU-M5-00N"
        )
    if hypothesis_id not in CANDIDATE_BY_ID:
        raise ValueError(
            f"candidate id {hypothesis_id!r} is not in the fixed HYP-007..010 table"
        )
    return hypothesis_id


def select_candidates(ids: Sequence[str] | None) -> list[dict[str, str]]:
    """Return ordered candidates for rebuild.

    ``None`` / empty selection keeps backward-compatible default: all four.
    Explicit IDs are validated against the fixed candidate table; duplicates
    are rejected; table order is preserved (not CLI order).
    """
    if not ids:
        return [dict(item) for item in CANDIDATES]

    resolved: list[str] = []
    seen: set[str] = set()
    for token in ids:
        hypothesis_id = normalize_id_token(token)
        if hypothesis_id in seen:
            raise ValueError(f"duplicate candidate id in --ids: {hypothesis_id}")
        seen.add(hypothesis_id)
        resolved.append(hypothesis_id)

    # Preserve fixed-table order, not CLI order.
    selected = [dict(CANDIDATE_BY_ID[item["hypothesis_id"]]) for item in CANDIDATES if item["hypothesis_id"] in seen]
    if len(selected) != len(resolved):
        missing = sorted(seen - {item["hypothesis_id"] for item in selected})
        raise ValueError(f"candidate id(s) not in fixed table: {missing}")
    return selected


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build alphafactory_research_task_packet.v1 preflight packets for "
            "MZMS HYP-007..010. Default rebuilds all four; use --ids to select."
        )
    )
    parser.add_argument(
        "--ids",
        nargs="+",
        metavar="ID",
        default=None,
        help=(
            "Optional subset of campaign arms to rebuild, e.g. "
            "'--ids 008 009 010' or full hypothesis IDs. "
            "Unselected preflight packets/receipts are left byte-for-byte untouched. "
            "Default: all four (007 008 009 010)."
        ),
    )
    return parser.parse_args(argv)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def sha256_text(value: str) -> str:
    """UTF-8 SHA256 uppercase — mirrors alpha.ps1 Get-TextSha256 for report identity."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def rel_posix(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def require_sha256_hex(value: Any, field: str) -> str:
    text = str(value or "").upper()
    if len(text) != 64 or any(ch not in "0123456789ABCDEF" for ch in text):
        raise ValueError(f"{field} is not 64-hex SHA256")
    return text


def compute_report_identity_fingerprints(
    basis: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, str]:
    """Recompute post-run fingerprints using alpha.ps1 Get-ReportIdentity formulas.

    broker  = SHA256(basis.broker)
    server  = SHA256(basis.server)  # includes ' (Build N)'
    account = SHA256(currency|initial_deposit|leverage|deposit|leverage|spread)
    data    = SHA256(symbol|period|from|to|model|history_quality|bars|ticks|digits|point|pip_size)
    """
    account_payload = "|".join(
        [
            str(basis["currency"]),
            str(basis["initial_deposit"]),
            str(basis["leverage"]),
            str(contract["deposit"]),
            str(contract["leverage"]),
            str(contract["spread"]),
        ]
    )
    data_payload = "|".join(
        [
            str(contract["symbol"]),
            str(contract["period"]),
            str(contract["from"]),
            str(contract["to"]),
            str(contract["model"]),
            str(basis["history_quality"]),
            str(basis["bars"]),
            str(basis["ticks"]),
            str(basis["digits"]),
            str(basis["point"]),
            str(basis["pip_size"]),
        ]
    )
    return {
        "broker_fingerprint": sha256_text(str(basis["broker"])),
        "server_fingerprint": sha256_text(str(basis["server"])),
        "account_fingerprint": sha256_text(account_payload),
        "data_fingerprint": sha256_text(data_payload),
        "account_payload": account_payload,
        "data_payload": data_payload,
    }


def _extract_manifest_identity(manifest: dict[str, Any]) -> dict[str, Any]:
    basis = manifest.get("fingerprint_basis")
    if not isinstance(basis, dict):
        raise ValueError("run_manifest missing fingerprint_basis")
    identity = {
        field: require_sha256_hex(manifest.get(field), f"run_manifest.{field}")
        for field in IDENTITY_FIELDS
    }
    identity["fingerprint_basis"] = basis
    return identity


def load_report_identity_basis(path: Path, root: Path) -> dict[str, Any]:
    """Load named report-identity receipt, re-verify source manifests, recompute hashes.

    Fail-closed on any cross-agreement, formula, path, or hash mismatch.
    """
    if not path.is_file():
        raise ValueError(f"report identity basis missing: {path}")
    receipt = json.loads(path.read_text(encoding="utf-8-sig"))
    if receipt.get("schema_version") != REPORT_IDENTITY_SCHEMA:
        raise ValueError(
            f"report identity basis schema must be {REPORT_IDENTITY_SCHEMA}, "
            f"got {receipt.get('schema_version')!r}"
        )
    if receipt.get("campaign_id") != CAMPAIGN_ID:
        raise ValueError("report identity basis campaign_id mismatch")
    if receipt.get("identity_semantics") != "alpha.ps1_Get-ReportIdentity_post_run_report":
        raise ValueError("report identity basis has unexpected identity_semantics")
    if receipt.get("promotion_eligible") is not False:
        raise ValueError("report identity basis must declare promotion_eligible=false")

    sources = receipt.get("sources")
    if not isinstance(sources, list) or len(sources) != 2:
        raise ValueError("report identity basis requires exactly two source manifests")

    observed: list[dict[str, Any]] = []
    for source in sources:
        rel = str(source.get("manifest_path") or "")
        manifest_path = root / Path(*rel.split("/"))
        if not manifest_path.is_file():
            raise ValueError(f"report identity source manifest missing: {manifest_path}")
        actual_sha = sha256_file(manifest_path)
        expected_sha = require_sha256_hex(
            source.get("manifest_sha256"), "source.manifest_sha256"
        )
        if actual_sha != expected_sha:
            raise ValueError(
                f"report identity source manifest SHA mismatch for {rel}: "
                f"expected {expected_sha}, got {actual_sha}"
            )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        if str(manifest.get("run_id") or "") != str(source.get("run_id") or ""):
            raise ValueError(f"report identity source run_id mismatch for {rel}")
        if str(manifest.get("hypothesis_id") or "") != str(source.get("hypothesis_id") or ""):
            raise ValueError(f"report identity source hypothesis_id mismatch for {rel}")
        # Contract window must match campaign binding.
        for key, expected in (
            ("symbol", "XAUUSD"),
            ("period", "M5"),
            ("from", FROM_DATE),
            ("to", TO_DATE),
        ):
            if str(manifest.get(key) or "") != expected:
                raise ValueError(f"source manifest {rel} {key} is not campaign binding")
        if "model" not in manifest or int(manifest["model"]) != 0:
            raise ValueError(f"source manifest {rel} model is not 0")
        observed.append(_extract_manifest_identity(manifest))

    # Fail-closed cross-agreement across both completed witnesses.
    first = observed[0]
    for other in observed[1:]:
        for field in IDENTITY_FIELDS:
            if first[field] != other[field]:
                raise ValueError(
                    f"report identity cross-agreement failed on {field}: "
                    f"{first[field]} vs {other[field]}"
                )
        if first["fingerprint_basis"] != other["fingerprint_basis"]:
            raise ValueError("report identity cross-agreement failed on fingerprint_basis")

    basis = first["fingerprint_basis"]
    contract = receipt.get("contract_binding") or {}
    for key, expected in (
        ("symbol", "XAUUSD"),
        ("period", "M5"),
        ("from", FROM_DATE),
        ("to", TO_DATE),
        ("spread", "current"),
    ):
        if str(contract.get(key) or "") != expected:
            raise ValueError(f"report identity contract_binding.{key} mismatch")
    if "model" not in contract or int(contract["model"]) != 0:
        raise ValueError("report identity contract_binding.model must be 0")
    if "deposit" not in contract or int(contract["deposit"]) != 100000:
        raise ValueError("report identity contract_binding.deposit must be 100000")
    if "leverage" not in contract or int(contract["leverage"]) != 100:
        raise ValueError("report identity contract_binding.leverage must be 100")

    recomputed = compute_report_identity_fingerprints(basis, contract)
    for field in IDENTITY_FIELDS:
        receipt_value = require_sha256_hex(receipt.get(field), f"receipt.{field}")
        if receipt_value != first[field]:
            raise ValueError(
                f"report identity receipt {field} does not match source manifests"
            )
        if receipt_value != recomputed[field]:
            raise ValueError(
                f"report identity receipt {field} does not recompute from basis/formula "
                f"(receipt={receipt_value}, recomputed={recomputed[field]})"
            )

    # Receipt payload strings must match the exact hashed inputs.
    if str(receipt.get("account_payload") or "") != recomputed["account_payload"]:
        raise ValueError("report identity account_payload does not match formula input")
    if str(receipt.get("data_payload") or "") != recomputed["data_payload"]:
        raise ValueError("report identity data_payload does not match formula input")

    receipt_basis = receipt.get("fingerprint_basis")
    if not isinstance(receipt_basis, dict) or receipt_basis != basis:
        raise ValueError("report identity receipt fingerprint_basis does not match sources")

    return {
        "path": path,
        "sha256": sha256_file(path),
        "broker_fingerprint": first["broker_fingerprint"],
        "server_fingerprint": first["server_fingerprint"],
        "account_fingerprint": first["account_fingerprint"],
        "data_fingerprint": first["data_fingerprint"],
        "fingerprint_basis": basis,
        "contract_binding": contract,
        "sources": sources,
        "receipt": receipt,
    }


def assert_report_vs_export_identity_distinct(
    report_identity: dict[str, Any],
    export_audit: dict[str, Any],
) -> None:
    """Fail-closed: export-audit fingerprints must not masquerade as report identity.

    Broker company hash may legitimately coincide. Server/account/data use different
    formulas and must differ so a silent copy of export fields cannot pass post-run.
    """
    for field in EXPORT_CONTRAST_FIELDS:
        export_value = require_sha256_hex(
            export_audit.get(field), f"export_audit.{field}"
        )
        report_value = require_sha256_hex(
            report_identity.get(field), f"report_identity.{field}"
        )
        if export_value == report_value:
            raise ValueError(
                f"spread-export {field} equals report-identity {field}; "
                "export formulas must remain distinct from post-run report identity "
                "and cannot silently masquerade as task-packet fingerprints"
            )


def file_evidence(label: str, path: Path) -> dict[str, str]:
    return {
        "label": label,
        "kind": "file",
        "path": str(path.resolve()),
        "sha256": sha256_file(path),
    }


def git_snapshot(root: Path) -> tuple[str, list[str], str]:
    import subprocess

    commit = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()
    status = subprocess.run(
        ["git", "-C", str(root), "status", "--short", "--untracked-files=all"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.splitlines()
    return commit, status, sha256_bytes("\n".join(status).encode("utf-8"))


def overrides_for(candidate: dict[str, str]) -> str:
    values = dict(COMMON_INPUTS)
    values["InpSignalMode"] = candidate["signal_mode"]
    values["InpHypothesisId"] = candidate["hypothesis_id"]
    values["InpMagic"] = candidate["magic"]
    return ";".join(f"{key}={values[key]}" for key in sorted(values))


def latest_registry_row(registry: Path, hypothesis_id: str) -> tuple[str, dict[str, Any]]:
    matches: list[tuple[str, dict[str, Any]]] = []
    for raw in registry.read_text(encoding="utf-8-sig").splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        if row.get("hypothesis_id") == hypothesis_id:
            matches.append((raw, row))
    if not matches:
        raise ValueError(f"registry has no row for {hypothesis_id}")
    raw, row = matches[-1]
    if row.get("state") != "screened" or row.get("model") != 0:
        raise ValueError(f"latest {hypothesis_id} registry row is not screened Model 0")
    return raw, row


def include_closure_records(root: Path) -> tuple[list[dict[str, str]], str]:
    entries: list[dict[str, str]] = []
    for relative in INCLUDES:
        path = root / Path(*relative.split("/"))
        if not path.is_file():
            raise ValueError(f"required include is missing: {path}")
        entries.append(
            {
                "path": relative,
                "sha256": sha256_file(path),
                "resolved_path": str(path.resolve()),
            }
        )
    records = [
        f"{str(Path(item['resolved_path']).resolve()).lower()}\t{item['sha256'].upper()}"
        for item in sorted(entries, key=lambda item: str(Path(item["resolved_path"]).resolve()).lower())
    ]
    digest = sha256_bytes("\n".join(records).encode("utf-8"))
    public_entries = [{"path": item["path"], "sha256": item["sha256"]} for item in entries]
    return public_entries, digest


def ensure_shared_snapshot(source: Path, snapshot: Path) -> str:
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, snapshot)
    source_hash = sha256_file(source)
    snapshot_hash = sha256_file(snapshot)
    if source_hash != EXPECTED_SOURCE_SHA256:
        raise ValueError(
            f"canonical source SHA mismatch: expected {EXPECTED_SOURCE_SHA256}, got {source_hash}"
        )
    if snapshot_hash != source_hash:
        raise ValueError("shared immutable source snapshot SHA does not equal current source")
    return source_hash


def load_export_audit(audit_path: Path) -> dict[str, Any]:
    if not audit_path.is_file():
        raise ValueError(f"spread export audit missing: {audit_path}")
    audit = json.loads(audit_path.read_text(encoding="utf-8-sig"))
    if audit.get("promotion_eligible") is not False:
        raise ValueError("spread export audit must declare promotion_eligible=false")
    if not audit.get("full_window_coverage"):
        raise ValueError(
            "spread export does not honestly cover the requested full window; "
            "refusing to emit RESEARCH_PROXY packets (do not fabricate coverage)"
        )
    for field in (
        "broker_fingerprint",
        "server_fingerprint",
        "account_fingerprint",
        "data_fingerprint",
        "source_sha256",
        "row_count",
        "actual_first_timestamp_utc",
        "actual_last_timestamp_utc",
    ):
        if field not in audit:
            raise ValueError(f"spread export audit missing field: {field}")
    for field in (
        "broker_fingerprint",
        "server_fingerprint",
        "account_fingerprint",
        "data_fingerprint",
        "source_sha256",
    ):
        value = str(audit.get(field) or "")
        if len(value) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in value):
            raise ValueError(f"spread export audit field {field} is not 64-hex")
    return audit


def build_cost_manifest(
    *,
    root: Path,
    evidence: Path,
    audit: dict[str, Any],
    report_identity: dict[str, Any],
    cost_path: Path,
) -> dict[str, Any]:
    spread_csv = evidence / f"{CAMPAIGN_ID}_HISTORICAL_SPREAD_M1.csv"
    commission_csv = evidence / f"{CAMPAIGN_ID}_TESTER_COMMISSION_MAX.csv"
    quote_csv = evidence / f"{CAMPAIGN_ID}_QUOTE_LATENCY_1000MS.csv"
    proxy_receipt = evidence / f"{CAMPAIGN_ID}_RESEARCH_COST_PROXY_RECEIPT.json"
    for path in (spread_csv, commission_csv, quote_csv, proxy_receipt):
        if not path.is_file():
            raise ValueError(f"required cost evidence missing: {path}")

    spread_hash = sha256_file(spread_csv)
    if spread_hash != str(audit["source_sha256"]).upper():
        raise ValueError("spread CSV hash does not match export audit")
    commission_hash = sha256_file(commission_csv)
    quote_hash = sha256_file(quote_csv)
    if commission_hash != EXPECTED_COMMISSION_SHA256:
        raise ValueError(
            f"commission proxy hash mismatch: expected {EXPECTED_COMMISSION_SHA256}, got {commission_hash}"
        )
    if quote_hash != EXPECTED_QUOTE_SHA256:
        raise ValueError(
            f"quote-latency proxy hash mismatch: expected {EXPECTED_QUOTE_SHA256}, got {quote_hash}"
        )

    row_count = int(audit["row_count"])
    if row_count <= 0:
        raise ValueError("spread export has zero rows")

    # Human-readable server label may come from export metadata; post-run
    # identity fingerprints come only from the report-identity basis.
    server_label = f"{audit['server']} (Build {audit['terminal_build']})"
    cost = {
        "schema_version": "alphafactory_cost_source_manifest.v1",
        "evidence_tier": "RESEARCH_PROXY",
        "provenance_status": "VERIFIED_RESEARCH_PROXY",
        "audit_status": "PASS_RESEARCH_ONLY",
        "verdict": "PASS_RESEARCH_ONLY",
        "promotion_eligible": False,
        "broker": str(audit["broker_company"]),
        "server": server_label,
        "account_currency": str(audit.get("account_currency") or "USD"),
        "broker_fingerprint": str(report_identity["broker_fingerprint"]).upper(),
        "server_fingerprint": str(report_identity["server_fingerprint"]).upper(),
        "account_fingerprint": str(report_identity["account_fingerprint"]).upper(),
        "data_fingerprint": str(report_identity["data_fingerprint"]).upper(),
        "symbol": "XAUUSD",
        "from": FROM_DATE,
        "to": TO_DATE,
        "symbol_geometry": SYMBOL_GEOMETRY,
        "historical_spread_provenance": {
            "verification_status": "VERIFIED",
            "symbol": "XAUUSD",
            "source": rel_posix(spread_csv, root),
            "source_sha256": spread_hash,
            "coverage": {
                "from": FROM_DATE,
                "to": TO_DATE,
                "sample_count": row_count,
                "total_count": row_count,
                "coverage_ratio": 1.0,
            },
            "actual_first_timestamp_utc": audit["actual_first_timestamp_utc"],
            "actual_last_timestamp_utc": audit["actual_last_timestamp_utc"],
            "missing_calendar_days_count": audit.get("missing_calendar_days_count"),
            "calendar_coverage_ratio": audit.get("calendar_coverage_ratio"),
        },
        "commission_provenance": {
            "verification_status": "VERIFIED_RESEARCH_PROXY",
            "symbol": "XAUUSD",
            "value": 4.4,
            "statistic": "maximum",
            "sample_count": 335,
            "same_symbol_lifecycles": True,
            "source_kind": "strategy_tester_simulation",
            "method": (
                "Maximum tester-observed round-turn commission per lot; "
                "research falsification only; not observed live fills"
            ),
            "source": rel_posix(commission_csv, root),
            "source_sha256": commission_hash,
        },
        "slippage_provenance": {
            "verification_status": "VERIFIED_RESEARCH_PROXY",
            "symbol": "XAUUSD",
            "source": rel_posix(quote_csv, root),
            "source_sha256": quote_hash,
            "sample_count": 31176,
            "buy_count": 15588,
            "sell_count": 15588,
            "independent_reference": False,
            "independent_quote_reference": True,
            "fill_observed": False,
            "buy_reference_side": "ask",
            "sell_reference_side": "bid",
            "slippage_unit": "pips",
            "fixed_latency_ms": 1000,
            "max_quote_wait_ms": 500,
            "method": (
                "Non-overlapping fixed-latency future executable quote proxy; no fill claimed"
            ),
            "p90_buy": 40.000000000009095,
            "p90_sell": 40.000000000009095,
            "p90_roundturn": 80.00000000001819,
        },
        "direction_aware_methodology": {
            "verification_status": "VERIFIED_RESEARCH_PROXY",
            "direction_aware": True,
            "long_cost_treatment": (
                "Model-0 spread plus maximum tester commission and ask-to-future-ask adverse quote movement"
            ),
            "short_cost_treatment": (
                "Model-0 spread plus maximum tester commission and bid-to-future-bid adverse quote movement"
            ),
        },
        "lineage_receipt": rel_posix(proxy_receipt, root),
        "blocker": (
            "Research-only cost proxy. No observed XAU fill/commission sample exists; "
            "promotion remains blocked under every result."
        ),
    }
    write_json(cost_path, cost)
    return cost


def build_candidate(
    candidate: dict[str, str],
    *,
    root: Path,
    package: Path,
    source: Path,
    snapshot: Path,
    prereg: Path,
    registry: Path,
    ea_contract: Path,
    source_hash: str,
    prereg_hash: str,
    include_entries: list[dict[str, str]],
    include_closure_sha256: str,
    commit: str,
    status: list[str],
    status_hash: str,
    comparison_adapter: str,
    telemetry_profile: str,
    report_identity: dict[str, Any],
    shared_cost_path: Path,
    shared_cost_hash: str,
) -> dict[str, Any]:
    hypothesis_id = candidate["hypothesis_id"]
    preflight = package / "research" / "preflight" / hypothesis_id
    task_path = preflight / "task_packet.control.json"
    receipt_path = preflight / "contract_receipt.control.json"
    # Per-arm cost path remains the CLI-bound path; content is the shared RESEARCH_PROXY manifest.
    cost_manifest = preflight / "cost_source_manifest.json"

    raw_registry_row, registry_row = latest_registry_row(registry, hypothesis_id)
    if registry_row.get("source_hash") != source_hash:
        raise ValueError(f"{hypothesis_id}: screened registry source hash does not match disk")
    if registry_row.get("prereg_sha256") != prereg_hash:
        raise ValueError(f"{hypothesis_id}: screened registry prereg hash does not match disk")
    if registry_row.get("source_path") != rel_posix(source, root):
        raise ValueError(f"{hypothesis_id}: screened registry source_path is not canonical source")
    if registry_row.get("prereg_path") != rel_posix(prereg, root):
        raise ValueError(f"{hypothesis_id}: screened registry prereg_path is not shared prereg")
    validation = registry_row.get("validation") or {}
    if validation.get("promotion_eligible") is not False:
        raise ValueError(f"{hypothesis_id}: promotion_eligible must remain false")
    acceptance = registry_row.get("acceptance_contract") or ACCEPTANCE
    for key, expected in ACCEPTANCE.items():
        actual = acceptance.get(key)
        if actual is None:
            raise ValueError(f"{hypothesis_id}: acceptance_contract missing {key}")
        if float(actual) != float(expected):
            raise ValueError(f"{hypothesis_id}: acceptance_contract.{key} mismatch")

    # Materialize the exact CLI-bound cost path with the shared RESEARCH_PROXY payload.
    shutil.copy2(shared_cost_path, cost_manifest)
    cost_hash = sha256_file(cost_manifest)
    if cost_hash != shared_cost_hash:
        raise ValueError(f"{hypothesis_id}: per-arm cost manifest hash drifted from shared source")

    overrides = overrides_for(candidate)
    task = {
        "schema_version": "alphafactory_research_task_packet.v1",
        "hypothesis_id": hypothesis_id,
        "run_role": "control",
        "ea_name": EA_NAME,
        "source_path": rel_posix(source, root),
        "source_sha256": source_hash,
        "registry_path": rel_posix(registry, root),
        "registry_sha256": sha256_file(registry),
        "registry_row_sha256": sha256_bytes(raw_registry_row.encode("utf-8")),
        "prereg_path": rel_posix(prereg, root),
        "prereg_sha256": prereg_hash,
        "ea_contract_path": rel_posix(ea_contract, root),
        "ea_contract_sha256": sha256_file(ea_contract),
        "telemetry_profile": telemetry_profile,
        "comparison_adapter": comparison_adapter,
        "symbol": "XAUUSD",
        "period": "M5",
        "from": FROM_DATE,
        "to": TO_DATE,
        "model": 0,
        "execution_mode": 0,
        "fixed_delay_ms": 0,
        "overrides": overrides,
        "telemetry_tier": "trade-only",
        "deposit": 100000,
        "leverage": 100,
        "spread": "current",
        "validation_stage": "challenger",
        "holding_contract": "scalp",
        "cost_evidence_tier": "research_proxy",
        "acceptance_contract": {
            "min_profit_factor": float(acceptance["min_profit_factor"]),
            "min_trades_per_week": float(acceptance["min_trades_per_week"]),
            "max_trades_per_week": float(acceptance["max_trades_per_week"]),
            "max_drawdown_pct": float(acceptance["max_drawdown_pct"]),
            "min_cost_pf_x1_5": float(acceptance["min_cost_pf_x1_5"]),
            "min_cost_pf_x2": float(acceptance["min_cost_pf_x2"]),
            "max_monte_carlo_p95_dd_pct": float(acceptance["max_monte_carlo_p95_dd_pct"]),
        },
        "git_commit": commit,
        "git_status": status,
        "git_status_sha256": status_hash,
        "include_closure": include_entries,
        "include_closure_sha256": include_closure_sha256,
        "broker_fingerprint": str(report_identity["broker_fingerprint"]).upper(),
        "server_fingerprint": str(report_identity["server_fingerprint"]).upper(),
        "account_fingerprint": str(report_identity["account_fingerprint"]).upper(),
        "data_fingerprint": str(report_identity["data_fingerprint"]).upper(),
        "symbol_geometry": SYMBOL_GEOMETRY,
        "required_sidecars": REQUIRED_SIDECARS,
        "required_manifest_hashes": REQUIRED_MANIFEST_HASHES,
        "cost_source_manifest_path": rel_posix(cost_manifest, root),
        "cost_source_manifest_sha256": cost_hash,
        "matched_control_run_id": "",
        "matched_control_hypothesis_id": "",
        "matched_control_manifest_sha256": "",
        "matched_control_report_sha256": "",
        "matched_control_overrides": "",
        "matched_control_source_sha256": "",
        "matched_control_config_sha256": "",
        "matched_control_ex5_sha256": "",
        "matched_control_includes_sha256": "",
        "matched_control_git_commit": "",
        "matched_control_git_status_sha256": "",
        "wfa_artifact_path": "",
        "wfa_artifact_sha256": "",
        "variants_dir": "",
        "variants_sha256": "",
    }
    write_json(task_path, task)

    evidence = [
        file_evidence("task_packet", task_path),
        file_evidence("source", source),
        file_evidence("source_snapshot", snapshot),
        file_evidence("prereg", prereg),
        file_evidence("ea_contract", ea_contract),
        file_evidence("cost_source_manifest", cost_manifest),
        file_evidence(
            "report_identity_basis",
            package / "research" / "evidence" / REPORT_IDENTITY_BASIS_NAME,
        ),
        file_evidence(
            "spread_export_audit",
            package / "research" / "evidence" / SPREAD_EXPORT_AUDIT_NAME,
        ),
        file_evidence("historical_spread_m1", package / "research" / "evidence" / f"{CAMPAIGN_ID}_HISTORICAL_SPREAD_M1.csv"),
        file_evidence("commission_proxy", package / "research" / "evidence" / f"{CAMPAIGN_ID}_TESTER_COMMISSION_MAX.csv"),
        file_evidence("quote_latency_proxy", package / "research" / "evidence" / f"{CAMPAIGN_ID}_QUOTE_LATENCY_1000MS.csv"),
    ]
    for index, relative in enumerate(INCLUDES, start=1):
        evidence.append(file_evidence(f"include_{index:04d}", root / Path(*relative.split("/"))))

    receipt = {
        "schema_version": "alphafactory_execution_receipt.v1",
        "hypothesis_id": hypothesis_id,
        "registry_row_sha256": sha256_bytes(raw_registry_row.encode("utf-8")),
        "task_packet_sha256": evidence[0]["sha256"],
        "git_commit": commit,
        "git_status_sha256": status_hash,
        "binding": {
            "hypothesis_id": hypothesis_id,
            "run_role": "control",
            "ea_name": EA_NAME,
            "campaign_id": CAMPAIGN_ID,
            "mechanism": candidate["mechanism"],
            "symbol": "XAUUSD",
            "period": "M5",
            "from": FROM_DATE,
            "to": TO_DATE,
            "model": 0,
            "execution_mode": 0,
            "fixed_delay_ms": 0,
            "overrides": overrides,
            "telemetry_tier": "trade-only",
            "telemetry_profile": telemetry_profile,
            "comparison_adapter": comparison_adapter,
            "validation_stage": "challenger",
            "holding_contract": "scalp",
            "cost_evidence_tier": "research_proxy",
            "deposit": 100000,
            "leverage": 100,
            "spread": "current",
            "required_sidecars": REQUIRED_SIDECARS,
            "required_manifest_hashes": REQUIRED_MANIFEST_HASHES,
            "symbol_geometry": SYMBOL_GEOMETRY,
            "include_closure_sha256": include_closure_sha256,
            "source_sha256": source_hash,
            "source_snapshot_sha256": source_hash,
            "registry_row_sha256": sha256_bytes(raw_registry_row.encode("utf-8")),
            "prereg_sha256": prereg_hash,
            "ea_contract_sha256": sha256_file(ea_contract),
            "cost_source_manifest_path": rel_posix(cost_manifest, root),
            "cost_source_manifest_sha256": cost_hash,
            "broker_fingerprint": str(report_identity["broker_fingerprint"]).upper(),
            "server_fingerprint": str(report_identity["server_fingerprint"]).upper(),
            "account_fingerprint": str(report_identity["account_fingerprint"]).upper(),
            "data_fingerprint": str(report_identity["data_fingerprint"]).upper(),
            "promotion_eligible": False,
        },
        "evidence": evidence,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": (
            "Strict research_task_packet.v1 control preflight for one frozen campaign arm. "
            "RESEARCH_PROXY cost only; promotion remains false. "
            "Post-run identity binds mzms_report_identity_basis.v1 (Get-ReportIdentity), "
            "not spread-export audit fingerprints. "
            f"Identity remains mode/{candidate['signal_mode']}/{hypothesis_id}/{candidate['magic']}."
        ),
    }
    write_json(receipt_path, receipt)
    return {
        "hypothesis_id": hypothesis_id,
        "task_packet": str(task_path),
        "task_packet_sha256": sha256_file(task_path),
        "contract_receipt": str(receipt_path),
        "contract_receipt_sha256": sha256_file(receipt_path),
        "cost_source_manifest": str(cost_manifest),
        "cost_source_manifest_sha256": cost_hash,
        "registry_row_sha256": sha256_bytes(raw_registry_row.encode("utf-8")),
        "signal_mode": candidate["signal_mode"],
        "magic": candidate["magic"],
        "overrides": overrides,
    }


def build_selected_candidates(
    selected: Sequence[dict[str, str]],
    *,
    root: Path,
    package: Path,
    source: Path,
    snapshot: Path,
    prereg: Path,
    registry: Path,
    ea_contract: Path,
    source_hash: str,
    prereg_hash: str,
    include_entries: list[dict[str, str]],
    include_closure_sha256: str,
    comparison_adapter: str,
    telemetry_profile: str,
    report_identity: dict[str, Any],
    shared_cost_path: Path,
    shared_cost_hash: str,
) -> tuple[list[dict[str, Any]], str, list[str], str]:
    """Two-pass freeze for *selected* candidates only.

    Unselected preflight dirs are never opened or rewritten.
    """
    results: list[dict[str, Any]] = []
    commit = ""
    status: list[str] = []
    status_hash = ""
    for pass_index in (1, 2):
        commit, status, status_hash = git_snapshot(root)
        results = []
        for candidate in selected:
            results.append(
                build_candidate(
                    candidate,
                    root=root,
                    package=package,
                    source=source,
                    snapshot=snapshot,
                    prereg=prereg,
                    registry=registry,
                    ea_contract=ea_contract,
                    source_hash=source_hash,
                    prereg_hash=prereg_hash,
                    include_entries=include_entries,
                    include_closure_sha256=include_closure_sha256,
                    commit=commit,
                    status=status,
                    status_hash=status_hash,
                    comparison_adapter=comparison_adapter,
                    telemetry_profile=telemetry_profile,
                    report_identity=report_identity,
                    shared_cost_path=shared_cost_path,
                    shared_cost_hash=shared_cost_hash,
                )
            )
        # Pass-2 status should equal post-write status when only content hashes change.
        if pass_index == 2:
            post_commit, post_status, post_status_hash = git_snapshot(root)
            if post_status_hash != status_hash or post_commit != commit:
                # One extra rewrite with the post-write porcelain.
                commit, status, status_hash = post_commit, post_status, post_status_hash
                results = []
                for candidate in selected:
                    results.append(
                        build_candidate(
                            candidate,
                            root=root,
                            package=package,
                            source=source,
                            snapshot=snapshot,
                            prereg=prereg,
                            registry=registry,
                            ea_contract=ea_contract,
                            source_hash=source_hash,
                            prereg_hash=prereg_hash,
                            include_entries=include_entries,
                            include_closure_sha256=include_closure_sha256,
                            commit=commit,
                            status=status,
                            status_hash=status_hash,
                            comparison_adapter=comparison_adapter,
                            telemetry_profile=telemetry_profile,
                            report_identity=report_identity,
                            shared_cost_path=shared_cost_path,
                            shared_cost_hash=shared_cost_hash,
                        )
                    )
    return results, commit, status, status_hash


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    selected = select_candidates(args.ids)
    selected_ids = [item["hypothesis_id"] for item in selected]

    root = Path(__file__).resolve().parents[3]
    package = root / "03. EA Developer" / EA_NAME
    source = package / f"{EA_NAME}.mq5"
    prereg = package / "research" / SHARED_PREREG_NAME
    snapshot = package / "research" / "source_snapshots" / SHARED_SNAPSHOT_NAME
    registry = root / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
    ea_contract = package / "ALPHAFACTORY_EA_CONTRACT.json"
    evidence = package / "research" / "evidence"
    audit_path = evidence / SPREAD_EXPORT_AUDIT_NAME
    report_identity_path = evidence / REPORT_IDENTITY_BASIS_NAME
    shared_cost_path = evidence / f"{CAMPAIGN_ID}_COST_SOURCE_MANIFEST.json"

    required = [source, prereg, registry, ea_contract, audit_path, report_identity_path]
    required.extend(root / Path(*item.split("/")) for item in INCLUDES)
    for path in required:
        if not path.is_file():
            raise ValueError(f"required evidence is missing: {path}")

    contract = json.loads(ea_contract.read_text(encoding="utf-8-sig"))
    comparison_adapter = str(contract.get("comparison_adapter") or "").strip()
    telemetry_profile = str(contract.get("telemetry_profile") or "").strip()
    if comparison_adapter != "generic-control-improvement-v1":
        raise ValueError(f"unexpected comparison_adapter from EA contract: {comparison_adapter}")
    if telemetry_profile != "lifecycle-v3":
        raise ValueError(f"unexpected telemetry_profile from EA contract: {telemetry_profile}")

    audit = load_export_audit(audit_path)
    report_identity = load_report_identity_basis(report_identity_path, root)
    assert_report_vs_export_identity_distinct(report_identity, audit)
    source_hash = ensure_shared_snapshot(source, snapshot)
    prereg_hash = sha256_file(prereg)
    if prereg_hash != EXPECTED_PREREG_SHA256:
        raise ValueError(
            f"shared prereg SHA mismatch: expected {EXPECTED_PREREG_SHA256}, got {prereg_hash}"
        )

    build_cost_manifest(
        root=root,
        evidence=evidence,
        audit=audit,
        report_identity=report_identity,
        cost_path=shared_cost_path,
    )
    shared_cost_hash = sha256_file(shared_cost_path)

    include_entries, include_closure_sha256 = include_closure_records(root)

    results, commit, _status, status_hash = build_selected_candidates(
        selected,
        root=root,
        package=package,
        source=source,
        snapshot=snapshot,
        prereg=prereg,
        registry=registry,
        ea_contract=ea_contract,
        source_hash=source_hash,
        prereg_hash=prereg_hash,
        include_entries=include_entries,
        include_closure_sha256=include_closure_sha256,
        comparison_adapter=comparison_adapter,
        telemetry_profile=telemetry_profile,
        report_identity=report_identity,
        shared_cost_path=shared_cost_path,
        shared_cost_hash=shared_cost_hash,
    )

    builder_path = Path(__file__).resolve()
    summary = {
        "campaign_id": CAMPAIGN_ID,
        "builder_path": rel_posix(builder_path, root),
        "builder_sha256": sha256_file(builder_path),
        "schema_version": "alphafactory_research_task_packet.v1",
        "cost_evidence_tier": "research_proxy",
        "validation_stage": "challenger",
        "holding_contract": "scalp",
        "comparison_adapter": comparison_adapter,
        "selected_ids": selected_ids,
        "source_sha256": source_hash,
        "source_snapshot": rel_posix(snapshot, root),
        "source_snapshot_sha256": source_hash,
        "prereg_sha256": prereg_hash,
        "include_closure_sha256": include_closure_sha256,
        "shared_cost_source_manifest": rel_posix(shared_cost_path, root),
        "shared_cost_source_manifest_sha256": shared_cost_hash,
        "report_identity_basis": rel_posix(report_identity_path, root),
        "report_identity_basis_sha256": report_identity["sha256"],
        "identity_semantics": "alpha.ps1_Get-ReportIdentity_post_run_report",
        "broker_fingerprint": str(report_identity["broker_fingerprint"]).upper(),
        "server_fingerprint": str(report_identity["server_fingerprint"]).upper(),
        "account_fingerprint": str(report_identity["account_fingerprint"]).upper(),
        "data_fingerprint": str(report_identity["data_fingerprint"]).upper(),
        "export_audit_server_fingerprint": str(audit["server_fingerprint"]).upper(),
        "export_audit_account_fingerprint": str(audit["account_fingerprint"]).upper(),
        "export_audit_data_fingerprint": str(audit["data_fingerprint"]).upper(),
        "git_commit": commit,
        "git_status_sha256": status_hash,
        "promotion_eligible": False,
        "run_role": "control",
        "candidates": results,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
