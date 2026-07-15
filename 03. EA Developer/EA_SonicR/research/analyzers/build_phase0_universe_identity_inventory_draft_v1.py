#!/usr/bin/env python3
"""Draft non-outcome identity inventory for Phase 0 PROBE_A.

Enumerates runs/<EA>/<run_id>/run_manifest.json only. Does not read report
outcomes, PF, trades, or equity. Does NOT freeze the Phase 0 sufficiency
spec (FROZEN_SPEC_SHA256 remains Owner/freeze-review gated).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(r"d:\Trading EA MT5")
RUN_ROOT = WORKSPACE / "02. AlphaFactory" / "runs"
OUT = (
    WORKSPACE
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preflight"
    / "20260713_PHASE0_UNIVERSE_IDENTITY_INVENTORY_DRAFT_V1.json"
)

IDENTITY_KEYS = ("run_id", "ea_name", "symbol", "period", "model", "from", "to")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    members: list[dict] = []
    errors: list[dict] = []

    if not RUN_ROOT.is_dir():
        raise SystemExit(f"missing run root: {RUN_ROOT}")

    for ea_dir in sorted(p for p in RUN_ROOT.iterdir() if p.is_dir()):
        # Skip operational/archive namespaces from identity draft.
        if ea_dir.name.startswith("_"):
            continue
        for run_dir in sorted(p for p in ea_dir.iterdir() if p.is_dir()):
            manifest_path = run_dir / "run_manifest.json"
            alt_manifest = run_dir / "config" / "run_manifest.json"
            member_id = f"{ea_dir.name}/{run_dir.name}"
            if not manifest_path.is_file():
                if alt_manifest.is_file():
                    manifest_path = alt_manifest
                else:
                    errors.append(
                        {
                            "universe_member_id": member_id,
                            "structural_status": "invalid",
                            "reason": "MISSING_RUN_MANIFEST",
                        }
                    )
                    continue
            try:
                raw = manifest_path.read_bytes()
                data = json.loads(raw.decode("utf-8-sig"))
            except Exception as exc:  # noqa: BLE001
                errors.append(
                    {
                        "universe_member_id": member_id,
                        "structural_status": "invalid",
                        "reason": f"MANIFEST_PARSE_FAIL:{exc}",
                    }
                )
                continue

            identity = {k: data.get(k) for k in IDENTITY_KEYS}
            # Keep only identity/config fields; never copy performance blocks.
            members.append(
                {
                    "universe_member_id": member_id,
                    "run_root": f"02. AlphaFactory/runs/{member_id}",
                    "ea_name": identity.get("ea_name") or ea_dir.name,
                    "run_id": identity.get("run_id") or run_dir.name,
                    "symbol": identity.get("symbol"),
                    "period": identity.get("period"),
                    "model": identity.get("model"),
                    "from": identity.get("from"),
                    "to": identity.get("to"),
                    "run_manifest_path": str(
                        manifest_path.relative_to(WORKSPACE)
                    ).replace("\\", "/"),
                    "run_manifest_sha256": hashlib.sha256(raw).hexdigest(),
                    "structural_status": "eligible_identity_only",
                    "outcome_fields_read": False,
                }
            )

    # Canonical sorted serialization for draft universe hash (not a freeze).
    canonical = json.dumps(members, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    draft = {
        "schema": "phase0_universe_identity_inventory_draft.v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "DRAFT_NOT_FROZEN / NO_PHASE1 / NO_COMPILE / NO_BACKTEST",
        "authority": (
            "Phase 0 identity-only contract work under autonomy portfolio memo; "
            "does not clear contamination freeze review; does not populate "
            "PROBE_A candidate_runs"
        ),
        "run_root": "02. AlphaFactory/runs",
        "member_count": len(members),
        "error_count": len(errors),
        "draft_universe_sha256": hashlib.sha256(canonical).hexdigest(),
        "selection_rule": "ALL_RUNS_WITH_RUN_MANIFEST_NO_OUTCOME_RANKING",
        "members": members,
        "errors": errors,
        "next_owner_gate": (
            "Clean freeze review + explicit Owner freeze of exact subset or "
            "full tried-family rule before rewriting Phase 0 sufficiency spec"
        ),
    }
    OUT.write_text(json.dumps(draft, indent=2), encoding="utf-8")
    print(
        f"wrote {OUT} members={len(members)} errors={len(errors)} "
        f"sha={draft['draft_universe_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
