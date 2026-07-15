#!/usr/bin/env python3
"""Phase 0 identity-only candidate subset for HYP-PORTFOLIO-COMPOSE-001.

Selection rule (non-outcome):
  Fixed hypothesis_id list declared a priori for Owner autonomy portfolio path:
    HYP-SB-WEEKEND-FLAT-001, HYP-SPARK-ASIAN-M15-001
  For each ID, bind the run_id listed in the latest registry row that carries
  that hypothesis_id and a non-empty run_ids / matched_control_run_id field,
  preferring challenger role when a two-run list exists (identity order:
  last element of run_ids if len==2 else sole run). Never reads report PF/net.

Does NOT freeze PROBE_A, does NOT authorize Phase 1 / compile / backtest /
outcome composition.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(r"d:\Trading EA MT5")
REG = (
    WORKSPACE
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "CANDIDATE_REGISTRY.jsonl"
)
OUT = (
    WORKSPACE
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preflight"
    / "20260714_PHASE0_PORTFOLIO_CANDIDATE_SUBSET_IDENTITY_V1.json"
)
READOUT = (
    WORKSPACE
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "readouts"
    / "20260714_HYP_PORTFOLIO_COMPOSE_001_PHASE0_SUBSET_IDENTITY_READOUT.md"
)

HYP_ORDER = [
    "HYP-SB-WEEKEND-FLAT-001",
    "HYP-SPARK-ASIAN-M15-001",
]

EA_BY_HYP = {
    "HYP-SB-WEEKEND-FLAT-001": "EA_SilverBullet",
    "HYP-SPARK-ASIAN-M15-001": "EA_M15SparkAsian",
}

SOURCE_BY_HYP = {
    "HYP-SB-WEEKEND-FLAT-001": "03. EA Developer/EA_SilverBullet/EA_SilverBullet_v2.mq5",
    "HYP-SPARK-ASIAN-M15-001": "03. EA Developer/EA_M15SparkAsian/EA_M15SparkAsian.mq5",
}


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def latest_registry_row(hyp_id: str) -> dict | None:
    last = None
    with REG.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("hypothesis_id") == hyp_id:
                last = row
    return last


def pick_run_id(row: dict) -> str | None:
    runs = row.get("run_ids") or []
    if isinstance(runs, list) and len(runs) >= 2:
        return str(runs[-1])  # challenger slot by identity order
    if isinstance(runs, list) and len(runs) == 1:
        return str(runs[0])
    m = row.get("matched_control_run_id")
    return str(m) if m else None


def member_for(hyp_id: str) -> dict:
    row = latest_registry_row(hyp_id)
    ea = EA_BY_HYP[hyp_id]
    run_id = pick_run_id(row) if row else None
    run_root = WORKSPACE / "02. AlphaFactory" / "runs" / ea / (run_id or "_missing")
    manifest = run_root / "run_manifest.json"
    if not manifest.is_file():
        alt = run_root / "config" / "run_manifest.json"
        manifest = alt if alt.is_file() else manifest
    report = run_root / "report.html"
    config = run_root / "config.ini"
    if not config.is_file():
        config = run_root / "config" / "config.ini"
    source = WORKSPACE / SOURCE_BY_HYP[hyp_id]

    # Trade/equity paths: identity presence only (hash file bytes, no parse of PnL).
    trade_candidates = [
        run_root / "analysis" / "datalog" / "trades.csv",
        run_root / "analysis" / "datalog" / "trades_summary.json",
        run_root / "logs" / "trades.csv",
    ]
    equity_candidates = [
        run_root / "analysis" / "equity.csv",
        run_root / "analysis" / "enhanced_summary.json",
    ]
    trade_path = next((p for p in trade_candidates if p.is_file()), None)
    equity_path = next((p for p in equity_candidates if p.is_file()), None)

    cost_candidates = [
        run_root / "analysis" / "tca_summary.json",
        run_root / "analysis" / "cost_stress_0_50.json",
    ]
    cost_path = next((p for p in cost_candidates if p.is_file()), None)

    identity = {}
    if manifest.is_file():
        try:
            identity = json.loads(manifest.read_text(encoding="utf-8-sig"))
        except Exception as exc:  # noqa: BLE001
            identity = {"_manifest_parse_error": str(exc)}

    structural = "eligible_identity_only"
    reasons: list[str] = []
    if not run_id:
        structural = "invalid"
        reasons.append("MISSING_RUN_ID_IN_REGISTRY")
    if not run_root.is_dir():
        structural = "invalid"
        reasons.append("MISSING_RUN_ROOT")
    if not manifest.is_file():
        structural = "invalid"
        reasons.append("MISSING_RUN_MANIFEST")
    if not report.is_file():
        reasons.append("MISSING_REPORT_HTML")
    if trade_path is None:
        reasons.append("MISSING_TRADE_SERIES_PATH")
    if equity_path is None:
        reasons.append("MISSING_EQUITY_SERIES_PATH")
    if cost_path is None:
        reasons.append("MISSING_COST_ARTIFACT")
    # Verified broker cost never present on Demo tester runs — explicit.
    reasons.append("COST_PROVENANCE_UNVERIFIED_TESTER_OR_MISSING")

    return {
        "universe_member_id": f"{ea}/{run_id}" if run_id else f"{ea}/MISSING",
        "hypothesis_id": hyp_id,
        "run_root": f"02. AlphaFactory/runs/{ea}/{run_id}" if run_id else None,
        "ea_name": ea,
        "run_id": run_id,
        "canonical_main_file": SOURCE_BY_HYP[hyp_id],
        "source_sha256": sha256_file(source),
        "compiled_sha256": None,
        "config_sha256": sha256_file(config),
        "report_sha256": sha256_file(report),
        "run_manifest_sha256": sha256_file(manifest),
        "trade_series_path": (
            str(trade_path.relative_to(WORKSPACE)).replace("\\", "/")
            if trade_path
            else None
        ),
        "trade_series_path_sha256": sha256_file(trade_path) if trade_path else None,
        "equity_series_path": (
            str(equity_path.relative_to(WORKSPACE)).replace("\\", "/")
            if equity_path
            else None
        ),
        "equity_series_path_sha256": sha256_file(equity_path) if equity_path else None,
        "cost_artifact_path": (
            str(cost_path.relative_to(WORKSPACE)).replace("\\", "/")
            if cost_path
            else None
        ),
        "cost_artifact_path_sha256": sha256_file(cost_path) if cost_path else None,
        "symbol": identity.get("symbol"),
        "suffix": identity.get("suffix"),
        "timeframe": identity.get("period") or identity.get("timeframe"),
        "model": identity.get("model"),
        "from": identity.get("from"),
        "to": identity.get("to"),
        "broker_server_account_currency_fingerprint": "UNSET_DEMO_OR_UNKNOWN",
        "duplicate_group": None,
        "structural_status": structural,
        "structural_reasons": reasons,
        "outcome_fields_read": False,
        "registry_state_at_bind": row.get("state") if row else None,
    }


def main() -> int:
    members = [member_for(h) for h in HYP_ORDER]
    canonical = json.dumps(members, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    blockers = []
    for m in members:
        if m["structural_status"] != "eligible_identity_only":
            blockers.append(f"{m['universe_member_id']}:invalid")
        for r in m.get("structural_reasons") or []:
            if r.startswith("MISSING_") or r.startswith("COST_"):
                blockers.append(f"{m['universe_member_id']}:{r}")

    # Deduplicate blockers while preserving order
    seen = set()
    blockers_u = []
    for b in blockers:
        if b not in seen:
            seen.add(b)
            blockers_u.append(b)

    payload = {
        "schema": "phase0_portfolio_candidate_subset_identity.v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "DRAFT_SUBSET_NOT_FROZEN / PHASE1_BLOCKED / NO_OUTCOME_COMPOSE",
        "hypothesis_id": "HYP-PORTFOLIO-COMPOSE-001",
        "selection_rule": (
            "FIXED_HYPOTHESIS_ID_LIST_THEN_REGISTRY_RUN_IDS_LAST_AS_CHALLENGER_SLOT;"
            "NO_PF_NET_CADENCE_RANKING"
        ),
        "hypothesis_ids": HYP_ORDER,
        "member_count": len(members),
        "subset_universe_sha256": hashlib.sha256(canonical).hexdigest().upper(),
        "contamination_attestation": (
            "preflight/20260711_PHASE0_COORDINATION_CONTAMINATION_ATTESTATION_V1.json "
            "still BLOCKED_REQUIRES_CLEAN_FUTURE_FREEZE_REVIEW — this draft does "
            "not clear it"
        ),
        "phase0_verdict": "BLOCKED_NOT_READY_FOR_PREREG_FREEZE",
        "blockers": blockers_u,
        "members": members,
        "explicitly_not_authorized": [
            "Phase 1 outcome composition",
            "correlation/overlap screens",
            "compile",
            "MT5 backtest",
            "PF cherry-pick / best-run selection",
        ],
        "next_required": [
            "Owner clean freeze review of exact subset + weight/common-window contracts",
            "Verified same-broker cost provenance (QFSI / FivePercentOnline-Real)",
            "Trade + equity series identity complete for every member",
            "Rewrite Phase 0 sufficiency spec candidate_runs only after freeze",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# HYP-PORTFOLIO-COMPOSE-001 — Phase 0 Candidate Subset Identity Readout",
        "",
        f"Date: {datetime.now(timezone.utc).date().isoformat()}",
        "Status: `DRAFT_SUBSET_NOT_FROZEN` / `PHASE1_BLOCKED` / **GOAL unmet**",
        "",
        "## Decision",
        "",
        "Price-M15 dual-filter shelf is EMPTY (kill/park list exhausted).",
        "Shortest legal autonomous path without Real login: Phase 0 portfolio",
        "identity subset freeze work for `HYP-PORTFOLIO-COMPOSE-001`.",
        "",
        "## Selection rule (non-outcome)",
        "",
        "- Fixed hypothesis IDs: `HYP-SB-WEEKEND-FLAT-001`, `HYP-SPARK-ASIAN-M15-001`",
        "- Run bind from latest registry `run_ids` (challenger = last of two)",
        "- No PF / net / cadence ranking",
        "",
        f"- `subset_universe_sha256`: `{payload['subset_universe_sha256']}`",
        f"- Artifact: `{OUT.relative_to(WORKSPACE).as_posix()}`",
        "",
        "## Members (identity only)",
        "",
        "| hypothesis_id | member | structural | key blockers |",
        "|---|---|---|---|",
    ]
    for m in members:
        br = ", ".join(m.get("structural_reasons") or []) or "none"
        lines.append(
            f"| `{m['hypothesis_id']}` | `{m['universe_member_id']}` | "
            f"{m['structural_status']} | {br} |"
        )
    lines += [
        "",
        "## Phase 0 verdict",
        "",
        f"**`{payload['phase0_verdict']}`**",
        "",
        "Contamination attestation still requires a clean future freeze review.",
        "Cost provenance remains unverified (Demo tester / missing).",
        "No Phase 1 composition, compile, or backtest authorized by this readout.",
        "",
        "## vs GOAL",
        "",
        "No research-pass and no confirmed book. Cadence/PF of a composed book",
        "were **not** computed (outcome access forbidden in Phase 0).",
        "",
        "## Next",
        "",
        "1. Owner freeze review of this exact subset + weight/common-window contracts.",
        "2. FivePercentOnline-Real login + QFSI cost capture.",
        "3. New independent M15/exogenous thesis outside kill shelf (self-research).",
        "",
    ]
    READOUT.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"out": str(OUT), "sha": payload["subset_universe_sha256"], "blockers": len(blockers_u)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
