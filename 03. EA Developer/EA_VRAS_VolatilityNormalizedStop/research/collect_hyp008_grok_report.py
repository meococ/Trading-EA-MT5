#!/usr/bin/env python3
"""Publish only a fully validated HYP008 two-pass Grok synthesis."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import build_hyp008_grok_requests as build
import validate_hyp008_grok_forensics as validate


REPORT = build.EVIDENCE / "HYP-VRAS-EURUSD-M5-008_GROK_RANDOM100_FORENSIC_REPORT.md"
QC = build.EVIDENCE / "HYP-VRAS-EURUSD-M5-008_GROK_RANDOM100_QC.json"
SYNTHESIS_ACCEPTED = build.VALIDATED / "synthesis.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(build.ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


def validated_truth() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not SYNTHESIS_ACCEPTED.is_file():
        raise FileNotFoundError(f"validated synthesis missing: {SYNTHESIS_ACCEPTED}")
    accepted = build.load_json(SYNTHESIS_ACCEPTED)
    current = validate.validate_synthesis(Path(str(accepted["attempt_dir"])))
    if accepted != current:
        raise RuntimeError("accepted synthesis drifted from its validated attempt")
    jobs: list[dict[str, Any]] = []
    for stage in ("pass-a", "pass-b"):
        for number in range(1, build.JOB_COUNT + 1):
            path = build.VALIDATED / stage / f"job-{number:02d}.json"
            record = build.load_json(path)
            if record != validate.validate_job(Path(str(record["attempt_dir"]))):
                raise RuntimeError(f"accepted job drift: {path}")
            jobs.append(record)
    if len(jobs) != 40:
        raise RuntimeError(f"expected 40 validated jobs, got {len(jobs)}")
    return accepted, jobs


def build_report(result: dict[str, Any]) -> str:
    return (
        "# HYP-VRAS-EURUSD-M5-008 — Grok random-100 two-pass forensics\n\n"
        "> Read-only diagnostic synthesis over the unchanged frozen random sample. "
        "Pass A reviewed 100 decision-as-of images without outcomes; independent "
        "stateless Pass B reviewed 100 anatomy images after reading validated Pass A. "
        "This artifact cannot tune or rescue HYP008 and grants no rerun, promotion, "
        "paper, or live authority.\n\n"
        "## Owner summary (Vietnamese)\n\n"
        f"{str(result['owner_summary_vi']).strip()}\n\n"
        "## Full Grok synthesis\n\n"
        f"{str(result['full_report_markdown']).strip()}\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect validated HYP008 Grok report")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    accepted, jobs = validated_truth()
    result = accepted["result"]
    if args.check_only:
        print(json.dumps({
            "status": "HYP008_GROK_REPORT_READY_TO_PUBLISH",
            "jobs": len(jobs), "images": result["coverage"]["images_opened"],
            "hypotheses": len(result["fresh_mechanism_hypotheses"]),
        }, indent=2))
        return 0

    report_text = build_report(result)
    REPORT.write_text(report_text, encoding="utf-8")

    job_qc: list[dict[str, Any]] = []
    total_cost = 0.0
    total_elapsed = 0.0
    for record in jobs:
        summary_path = Path(record["summary"])
        summary = build.load_json(summary_path)
        total_cost += float(summary.get("total_cost_usd") or 0.0)
        total_elapsed += float(summary.get("elapsed_seconds") or 0.0)
        job_qc.append({
            "stage": record["stage"],
            "job_id": record["job_id"],
            "case_ids": record["expected_case_ids"],
            "request": rel(Path(record["request"])),
            "request_sha256": record["request_sha256"],
            "response": rel(Path(record["response"])),
            "response_sha256": record["response_sha256"],
            "summary": rel(summary_path),
            "summary_sha256": record["summary_sha256"],
            "stop_reason": summary["stop_reason"],
            "images_opened": record["result"]["coverage"]["images_opened"],
        })
    synthesis_summary = build.load_json(Path(accepted["summary"]))
    total_cost += float(synthesis_summary.get("total_cost_usd") or 0.0)
    total_elapsed += float(synthesis_summary.get("elapsed_seconds") or 0.0)
    qc = {
        "schema_version": "vras_hyp008_grok_random100_qc.v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "campaign_id": build.CAMPAIGN_ID,
        "hypothesis_id": build.HYPOTHESIS_ID,
        "run_id": build.RUN_ID,
        "forensic_only": True,
        "promotion_blocked": True,
        "post_hoc_rescue_blocked": True,
        "coverage": result["coverage"],
        "case_ids_sha256": hashlib.sha256("\n".join(result["case_ids_seen"]).encode("utf-8")).hexdigest().upper(),
        "selection_manifest": rel(build.SELECTION),
        "selection_manifest_sha256": sha256_file(build.SELECTION),
        "chart_manifest": rel(build.CHART_MANIFEST),
        "chart_manifest_sha256": sha256_file(build.CHART_MANIFEST),
        "synthesis_accepted": rel(SYNTHESIS_ACCEPTED),
        "synthesis_accepted_sha256": sha256_file(SYNTHESIS_ACCEPTED),
        "synthesis_response": rel(Path(accepted["response"])),
        "synthesis_response_sha256": accepted["response_sha256"],
        "published_report": rel(REPORT),
        "published_report_sha256": sha256_file(REPORT),
        "jobs": job_qc,
        "accepted_job_count": len(job_qc),
        "latest_accepted_cost_usd_sum": round(total_cost, 6),
        "latest_accepted_elapsed_seconds_sum": round(total_elapsed, 3),
        "cost_note": "Accepted current-attempt summaries only; dry-runs and failed retries excluded.",
        "limitations_acknowledged": result["limitations_acknowledged"],
    }
    QC.write_text(json.dumps(qc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "HYP008_GROK_REPORT_PUBLISHED",
        "report": str(REPORT), "report_sha256": sha256_file(REPORT),
        "qc": str(QC), "qc_sha256": sha256_file(QC),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
