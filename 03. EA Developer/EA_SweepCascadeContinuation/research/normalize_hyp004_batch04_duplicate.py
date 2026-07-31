#!/usr/bin/env python3
"""Normalize the exact duplicated, substantive Grok batch04 JSON downstream."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import validate


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main() -> int:
    workspace = Path(__file__).resolve().parents[3]
    batch = workspace / ".context" / "scc-hyp004-random100-gfi" / "batch04"
    failed_run = batch / "run"
    candidates = list(failed_run.glob(".grok-response.candidate.*.json"))
    if len(candidates) != 1:
        raise SystemExit(f"Expected one failed candidate, got {len(candidates)}")
    candidate_path = candidates[0]
    candidate = json.loads(candidate_path.read_text(encoding="utf-8-sig"))
    text = candidate["output_text"]

    decoder = json.JSONDecoder()
    first, index = decoder.raw_decode(text)
    second, index2 = decoder.raw_decode(text, index)
    if text[index2:].strip():
        raise SystemExit("Candidate contains more than two JSON values")
    if first != second:
        raise SystemExit("The two candidate JSON values are not exact duplicates")

    request_path = batch / "grok-request.json"
    request = json.loads(request_path.read_text(encoding="utf-8-sig"))
    schema = request["request"]["response_format"]["json_schema"]["schema"]
    validate(instance=first, schema=schema)
    expected_ids = request["meta"]["case_ids"]
    reviews = first["case_reviews"]
    if {row["case_id"] for row in reviews} != set(expected_ids):
        raise SystemExit("Candidate case IDs do not match request")
    for row in reviews:
        combined = " ".join(
            row["decision_observations"]
            + row["anatomy_observations"]
            + [row["data_quality_note"]]
        ).lower()
        if "placeholder" in combined or "pending" in combined:
            raise SystemExit(f"Generic placeholder content: {row['case_id']}")
        if min(
            len(row["decision_observations"][0]),
            len(row["anatomy_observations"][0]),
        ) < 30:
            raise SystemExit(f"Observations too short: {row['case_id']}")

    output = {
        "schema_version": "scc_caller_normalized_grok_response.v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "batch_id": "batch04",
        "normalization": {
            "type": "EXACT_DUPLICATE_JSON_INSTANCE_EXTRACTION",
            "instances_found": 2,
            "instances_equal": True,
            "content_edited": False,
            "reason": (
                "Grok ended normally and produced a substantive schema-valid object "
                "twice. The runner correctly rejected the transport shape; this caller "
                "artifact preserves exactly one byte-equivalent parsed instance."
            ),
        },
        "source_candidate": {
            "path": candidate_path.relative_to(workspace).as_posix(),
            "bytes": candidate_path.stat().st_size,
            "sha256": sha256(candidate_path),
        },
        "source_summary": {
            "path": (failed_run / "summary.json").relative_to(workspace).as_posix(),
            "bytes": (failed_run / "summary.json").stat().st_size,
            "sha256": sha256(failed_run / "summary.json"),
            "runner_stop_reason": "EndTurn",
            "runner_failure_reason": "schema_validation_failed_exact_duplicate_output",
        },
        "request": {
            "path": request_path.relative_to(workspace).as_posix(),
            "bytes": request_path.stat().st_size,
            "sha256": sha256(request_path),
        },
        "payload": first,
    }
    output_path = batch / "normalized_duplicate_response.json"
    output_path.write_text(
        json.dumps(output, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        "SCC_BATCH04_DUPLICATE_NORMALIZED_OK "
        f"cases=5 artifact_sha256={sha256(output_path)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
