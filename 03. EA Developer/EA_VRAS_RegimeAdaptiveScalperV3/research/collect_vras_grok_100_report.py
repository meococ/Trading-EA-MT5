#!/usr/bin/env python3
"""Publish the accepted Grok 100-image synthesis into the evidence tree."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RESEARCH = Path(__file__).resolve().parent
EVIDENCE = RESEARCH / "evidence" / "HYP-VRAS-EURUSD-M5-003_GROK_CHART_FORENSICS_100"
CONTEXT = ROOT / ".context" / "vras-003-grok-indicator-rich-100-20260722"
SYNTHESIS = CONTEXT / "synthesis" / "grok-synthesis.json"
REPORT = EVIDENCE / "HYP-VRAS-EURUSD-M5-003_GROK_INDICATOR_RICH_100_REPORT.md"
QC = EVIDENCE / "GROK_INDICATOR_RICH_100_QC.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main() -> None:
    result = json.loads(SYNTHESIS.read_text(encoding="utf-8"))
    report = (
        "# HYP-VRAS-EURUSD-M5-003 — Grok indicator-rich forensics (100 images)\n\n"
        "> Grok-authored synthesis. Corpus: the complete 93-trade Model-0 census plus seven explicitly "
        "non-economic COST_DISTANCE_REJECT diagnostics. This report does not authorize tuning, rerun, rescue, "
        "promotion, or live use.\n\n"
        "## Owner summary (Vietnamese)\n\n"
        f"{result['owner_summary_vi'].strip()}\n\n"
        "## Full Grok report\n\n"
        f"{result['full_report_markdown'].strip()}\n"
    )
    REPORT.write_text(report, encoding="utf-8")

    batch_results = []
    total_cost = 0.0
    total_elapsed = 0.0
    for number in range(1, 21):
        directory = CONTEXT / f"batch-{number:02d}"
        summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
        analysis = directory / "grok-analysis.json"
        total_cost += float(summary.get("total_cost_usd", 0.0))
        total_elapsed += float(summary.get("elapsed_seconds", 0.0))
        batch_results.append(
            {
                "batch": f"B{number:02d}",
                "summary": str((directory / "summary.json").relative_to(ROOT)).replace("\\", "/"),
                "analysis": str(analysis.relative_to(ROOT)).replace("\\", "/"),
                "analysis_sha256": sha256(analysis),
                "runner_success": bool(summary["success"]),
                "runner_stop_reason": summary["stop_reason"],
            }
        )
    synthesis_summary = json.loads((CONTEXT / "synthesis" / "summary.json").read_text(encoding="utf-8"))
    total_cost += float(synthesis_summary.get("total_cost_usd", 0.0))
    total_elapsed += float(synthesis_summary.get("elapsed_seconds", 0.0))
    qc = {
        "schema_version": "vras_grok_indicator_rich_100_qc.v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "hypothesis_id": "HYP-VRAS-EURUSD-M5-003",
        "run_id": "20260722_103759",
        "coverage": result["coverage"],
        "terminal_conclusion": result["terminal_conclusion"],
        "case_ids_sha256": hashlib.sha256("\n".join(result["case_ids_seen"]).encode("utf-8")).hexdigest().upper(),
        "synthesis": str(SYNTHESIS.relative_to(ROOT)).replace("\\", "/"),
        "synthesis_sha256": sha256(SYNTHESIS),
        "published_report": str(REPORT.relative_to(ROOT)).replace("\\", "/"),
        "published_report_sha256": sha256(REPORT),
        "batch_results": batch_results,
        "latest_attempt_cost_usd_sum": round(total_cost, 6),
        "latest_attempt_elapsed_seconds_sum": round(total_elapsed, 3),
        "cost_note": "Sums accepted latest-attempt summaries only; cancelled/resumed attempts archived by the runner are excluded.",
    }
    QC.write_text(json.dumps(qc, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"status": "VRAS_GROK_100_REPORT_PUBLISHED", "report": str(REPORT), "qc": str(QC)}, indent=2))


if __name__ == "__main__":
    main()
