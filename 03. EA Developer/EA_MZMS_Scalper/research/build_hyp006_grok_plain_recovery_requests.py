#!/usr/bin/env python3
"""Build small plain-text Grok requests when schema-heavy chunks cancel."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RESEARCH = Path(__file__).resolve().parent
HYPOTHESIS_ID = "HYP-MZMS-MACD-HIST-SLOPE-XAUUSD-M5-006"
EVIDENCE = RESEARCH / "evidence" / f"{HYPOTHESIS_ID}_GROK_INDICATOR_FORENSICS_200"
CONTEXT = ROOT / ".context"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_request(worker: str, chunk_number: int, part_number: int, rows: list[dict]) -> dict:
    short = "a" if worker == "worker_a" else "b"
    case_lines = "\n".join(
        f"- {row['case_id']} | position_id={row['position_id']} | side={row['side']} | PNG={row['absolute_path']}"
        for row in rows
    )
    task = f"mzms-xau-indicator-{short}-plain-c{chunk_number:02d}-p{part_number}"
    prompt = f"""Visually open and inspect exactly these {len(rows)} XAUUSD M5 indicator-rich PNGs:
{case_lines}

For every case, combine the chart with the frozen strategy contract: 100% closed-bar; direction uses EMA200 side, MACD 12/26/9 histogram local extremum at s2 using s3/s2/s1, ATR-normalized histogram delta gate 0.01, RSI14 in 42-58 with one-bar directional slope, and ADX14 >=18. The stop is the farther of structure+buffer and 1.5 ATR; TP is 1.6R; break-even is OFF; max hold is 15 M5 bars. Each chart already shows decision vs outcome, EMA200, MACD main/signal/hist and s3/s2/s1, RSI14, ADX14, ATR14, entry, SL, TP, exit, hold, and net R.

For each manifest case, write one section starting exactly `CASE_ID=<id> | POSITION_ID=<id> | IMAGE_OPENED=true`. Then give concise OBSERVED bullets for price/EMA context, MACD+RSI+ADX+ATR cluster, and outcome path; add one clearly labeled INFERENCE for the most plausible failure mechanism. Do not omit a case. Do not emit JSON, schema shells, progress reports, or placeholders. If a PNG cannot be opened, use IMAGE_OPENED=false for that exact case and do not fabricate.

Hard boundary: parent run is invalid because history quality is 98% below the frozen 99% gate. Chart NON-PARITY is post-run recomputation fidelity evidence, not an EA logic violation; lifecycle/source are execution truth. This loser-only diagnostic cannot authorize filters, tuned thresholds, BE/timeout changes, promotion, or live use. Use local evidence only; no web and no subagents."""
    return {
        "task": task,
        "request": {
            "reasoning_effort": "high",
            "input": [
                {
                    "role": "system",
                    "content": "You are a read-only senior systematic-trading chart forensic reviewer. Open every listed image and separate observed chart facts from inference.",
                },
                {"role": "user", "content": prompt},
            ],
        },
        "meta": {
            "worker": worker,
            "chunk_id": f"chunk_{chunk_number:02d}",
            "part": part_number,
            "case_ids": [row["case_id"] for row in rows],
            "position_ids": [row["position_id"] for row in rows],
            "purpose": "plain-text small-batch recovery after schema-heavy cancellation",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", choices=("worker_a", "worker_b"), required=True)
    parser.add_argument("--chunks", required=True, help="Comma-separated chunk numbers, for example 1,8,9,10")
    parser.add_argument("--batch-size", type=int, default=5)
    args = parser.parse_args()
    if args.batch_size < 1 or args.batch_size > 10:
        raise SystemExit("batch-size must be between 1 and 10")
    short = "a" if args.worker == "worker_a" else "b"
    created = 0
    for chunk_number in [int(value) for value in args.chunks.split(",")]:
        manifest_path = (
            EVIDENCE
            / "grok_chunks10"
            / args.worker
            / f"chunk_{chunk_number:02d}"
            / "chunk_manifest.json"
        )
        rows = load_json(manifest_path)["images"]
        for offset in range(0, len(rows), args.batch_size):
            part_number = offset // args.batch_size + 1
            selected = rows[offset : offset + args.batch_size]
            task = f"mzms-xau-indicator-{short}-plain-c{chunk_number:02d}-p{part_number}"
            task_dir = CONTEXT / task
            task_dir.mkdir(parents=True, exist_ok=True)
            request_path = task_dir / "grok-request.json"
            if request_path.exists():
                raise SystemExit(f"refusing to overwrite existing request: {request_path}")
            request = build_request(args.worker, chunk_number, part_number, selected)
            request_path.write_text(json.dumps(request, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(request_path)
            created += 1
    print(f"PLAIN_RECOVERY_REQUESTS_OK worker={args.worker} created={created} batch_size={args.batch_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
