# -*- coding: utf-8 -*-
"""Attach Phase 0 trade-series + honest cost provenance for parked SB/Spark runs.

Does NOT read portfolio outcomes / compose books. Updates subset identity JSON only.
Contamination attestation remains blocked — no READY_FOR_PREREG_FREEZE claim.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
SUBSET = (
    ROOT
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preflight"
    / "20260714_PHASE0_PORTFOLIO_CANDIDATE_SUBSET_IDENTITY_V1.json"
)
READOUT = (
    ROOT
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "readouts"
    / "20260714_HYP_PORTFOLIO_COMPOSE_001_PHASE0_ARTIFACT_ATTACH_READOUT.md"
)
ANALYZER = ROOT / "02. AlphaFactory" / "analysis" / "quant_analyzer.py"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def write_cost_manifest(run_root: Path, ea: str, run_id: str) -> Path:
    out = run_root / "analysis" / "research_cost_provenance.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "research_cost_provenance.v1",
        "ea_name": ea,
        "run_id": run_id,
        "cost_label": "UNVERIFIED_TESTER_DEFAULT",
        "broker_server": "MetaQuotes-Demo",
        "spread_binding": "current",
        "commission_verified": False,
        "slippage_verified": False,
        "qfsi_verified": False,
        "note": (
            "Phase 0 identity attach only. Tester current spread is not "
            "FivePercentOnline-Real / QFSI. Missing fields are not zero."
        ),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out


def ensure_spark_trades(run_root: Path) -> Path | None:
    """Extract trades.csv from report without using values for portfolio compose."""
    existing = list(run_root.rglob("*Trades*.csv")) + list(
        (run_root / "analysis").glob("trades.csv") if (run_root / "analysis").exists() else []
    )
    for p in existing:
        if p.is_file() and p.stat().st_size > 0:
            return p
    report = run_root / "report.html"
    if not report.is_file():
        return None
    out_dir = run_root / "analysis" / "phase0_identity"
    out_dir.mkdir(parents=True, exist_ok=True)
    # quant_analyzer writes trades.csv under --out
    cmd = [
        sys.executable,
        str(ANALYZER),
        "--report",
        str(report),
        "--out",
        str(out_dir),
    ]
    subprocess.run(cmd, check=False, capture_output=True, text=True)
    trades = out_dir / "trades.csv"
    return trades if trades.is_file() else None


def main() -> int:
    data = json.loads(SUBSET.read_text(encoding="utf-8"))
    members = data["members"]
    for m in members:
        ea = m["ea_name"]
        rid = m["run_id"]
        run_root = ROOT / "02. AlphaFactory" / "runs" / ea / rid
        reasons = []

        # Trade series
        trade_path = None
        if ea == "EA_SilverBullet":
            cands = list((run_root / "logs").glob("*Trades*.csv")) if (run_root / "logs").exists() else []
            trade_path = cands[0] if cands else None
        elif ea == "EA_M15SparkAsian":
            trade_path = ensure_spark_trades(run_root)

        if trade_path and trade_path.is_file():
            rel = trade_path.relative_to(ROOT).as_posix()
            m["trade_series_path"] = rel
            m["trade_series_path_sha256"] = sha256_file(trade_path)
        else:
            reasons.append("MISSING_TRADE_SERIES_PATH")
            m["trade_series_path"] = None
            m["trade_series_path_sha256"] = None

        # Equity path
        eq = run_root / "analysis" / "enhanced_summary.json"
        if not eq.is_file():
            # analyzer summary as identity surrogate if present
            alt = run_root / "analysis" / "phase0_identity" / "summary.json"
            eq = alt if alt.is_file() else eq
        if eq.is_file():
            m["equity_series_path"] = eq.relative_to(ROOT).as_posix()
            m["equity_series_path_sha256"] = sha256_file(eq)
        else:
            reasons.append("MISSING_EQUITY_SERIES_PATH")
            m["equity_series_path"] = None
            m["equity_series_path_sha256"] = None

        # Cost provenance (honest unverified)
        cost = write_cost_manifest(run_root, ea, rid)
        m["cost_artifact_path"] = cost.relative_to(ROOT).as_posix()
        m["cost_artifact_path_sha256"] = sha256_file(cost)
        reasons.append("COST_PROVENANCE_UNVERIFIED_TESTER_OR_MISSING")

        m["structural_reasons"] = reasons
        m["structural_status"] = "eligible_identity_only"
        m["outcome_fields_read"] = False
        m["broker_server_account_currency_fingerprint"] = "METAQUOTES_DEMO_UNVERIFIED"

    canonical = json.dumps(members, sort_keys=True, separators=(",", ":")).encode("utf-8")
    data["members"] = members
    data["subset_universe_sha256"] = hashlib.sha256(canonical).hexdigest().upper()
    data["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    data["status"] = (
        "DRAFT_SUBSET_ARTIFACTS_ATTACHED / PHASE1_BLOCKED / NO_OUTCOME_COMPOSE"
    )
    data["phase0_verdict"] = "BLOCKED_NOT_READY_FOR_PREREG_FREEZE"
    blockers = []
    for m in members:
        for r in m.get("structural_reasons") or []:
            blockers.append(f"{m['universe_member_id']}:{r}")
    blockers.append("CONTAMINATION_ATTESTATION_REQUIRES_CLEAN_FUTURE_FREEZE_REVIEW")
    data["blockers"] = blockers
    data["artifact_attach_note"] = (
        "Trade-series + research_cost_provenance attached 2026-07-14. "
        "Cost remains UNVERIFIED_TESTER_DEFAULT. Contamination not cleared. "
        "No Phase 1 outcome compose authorized."
    )
    SUBSET.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# HYP-PORTFOLIO-COMPOSE-001 — Phase 0 Artifact Attach Readout",
        "",
        "Date: 2026-07-14",
        "Status: `ARTIFACTS_ATTACHED` / still `BLOCKED_NOT_READY_FOR_PREREG_FREEZE`",
        "",
        "## What changed",
        "",
        "- Bound SB `20260714_002505` existing datalog trades CSV (path+hash only).",
        "- Extracted Spark `20260714_002614` `trades.csv` via quant_analyzer for identity.",
        "- Wrote per-run `analysis/research_cost_provenance.json` labeled "
        "`UNVERIFIED_TESTER_DEFAULT` (honest; not Real QFSI).",
        "",
        f"- New `subset_universe_sha256`: `{data['subset_universe_sha256']}`",
        "",
        "## Still blocked",
        "",
        "- Contamination attestation requires clean future freeze review.",
        "- Cost provenance unverified (Demo tester).",
        "- No Phase 1 outcome composition / correlation / PF cherry-pick.",
        "",
        "## vs GOAL",
        "",
        "No composed-book metrics computed. GOAL unmet.",
        "",
    ]
    READOUT.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({
        "sha": data["subset_universe_sha256"],
        "blockers": blockers,
        "members": [
            {
                "id": m["universe_member_id"],
                "trade": m.get("trade_series_path"),
                "cost": m.get("cost_artifact_path"),
                "reasons": m.get("structural_reasons"),
            }
            for m in members
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
