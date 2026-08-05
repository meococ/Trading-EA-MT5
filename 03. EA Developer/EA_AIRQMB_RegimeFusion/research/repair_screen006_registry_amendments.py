from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"


def main() -> None:
    lines = REGISTRY.read_text(encoding="utf-8").splitlines()
    repaired = 0
    for index, raw in enumerate(lines):
        row = json.loads(raw)
        hypothesis_id = str(row.get("hypothesis_id", ""))
        validation = row.get("validation", {})
        if (
            hypothesis_id.startswith("HYP-AIRQMB-")
            and hypothesis_id.endswith("-M5-SCREEN-004")
            and row.get("state") == "parked"
            and validation.get("source_snapshot_sha256")
            == "AB4D63AD66984636F1E8D6D6291B91280220D85E30E52ECB04F1ACF7F40FC4B0"
            and row.get("updated_at_utc") == "2026-08-05T19:10:00Z"
        ):
            row["reason"] = (
                str(row["reason"])
                + " Immutable terminal source snapshot recorded after the canonical EA advanced."
            )
            row["updated_at_utc"] = "2026-08-05T19:16:01Z"
            lines[index] = json.dumps(row, separators=(",", ":"), ensure_ascii=True)
            repaired += 1
    if repaired != 9:
        raise SystemExit(f"expected 9 SCREEN-004 amendments, found {repaired}")
    REGISTRY.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"repaired {repaired} SCREEN-004 terminal snapshot amendments")


if __name__ == "__main__":
    main()
