from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
SYMBOLS = ["EURUSD", "USDJPY", "GBPUSD", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD", "XAUUSD", "BTCUSD"]
SNAPSHOT_PATH = (
    "03. EA Developer/EA_AIRQMB_RegimeFusion/research/source_snapshots/"
    "EA_AIRQMB_RegimeFusion_A0622C7BCB22F1DB.mq5"
)
SNAPSHOT_SHA256 = "A0622C7BCB22F1DBAABD707B1159679283D6B2C1AD0CFE642C5301E4573B1A81"


def main() -> None:
    lines = [line for line in REGISTRY.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    latest: dict[str, dict] = {}
    for line in lines:
        row = json.loads(line)
        latest[row["hypothesis_id"]] = row
    amendments: list[dict] = []
    for symbol in SYMBOLS:
        hypothesis_id = f"HYP-AIRQMB-{symbol}-M5-BASE-001"
        prior = latest[hypothesis_id]
        if prior.get("state") != "parked":
            raise SystemExit(f"latest row is not parked: {hypothesis_id}")
        validation = prior.get("validation") or {}
        if "source_snapshot_path" in validation:
            raise SystemExit(f"snapshot already bound: {hypothesis_id}")
        row = deepcopy(prior)
        row["updated_at_utc"] = "2026-08-05T18:33:00Z"
        row["reason"] = (
            prior["reason"]
            + " Immutable terminal source snapshot added after the outcome-blind engine successor changed the canonical source."
        )
        row["validation"]["source_snapshot_path"] = SNAPSHOT_PATH
        row["validation"]["source_snapshot_sha256"] = SNAPSHOT_SHA256
        amendments.append(row)
    with REGISTRY.open("a", encoding="utf-8", newline="\n") as handle:
        for row in amendments:
            handle.write(json.dumps(row, separators=(",", ":"), ensure_ascii=True) + "\n")
    print(f"appended {len(amendments)} immutable BASE-001 source snapshot amendments")


if __name__ == "__main__":
    main()
