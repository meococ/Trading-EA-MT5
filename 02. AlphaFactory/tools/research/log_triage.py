#!/usr/bin/env python3
"""Standard triage battery for heavy tester/EA text logs (streaming, capped).

Runs a fixed error-pattern battery over a large log without loading it into
memory or agent context, and writes one compact JSON summary. Use this FIRST;
open raw windows only where triage points (large_log_reader.py window).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "log_triage.v1"
BATTERY: list[tuple[str, str]] = [
    ("ledger_fatal", r"M2_LEDGER_FATAL|ledger_fatal"),
    ("order_reject", r"\breject(ed)?\b|TRADE_RETCODE_REJECT"),
    ("requote", r"requote|TRADE_RETCODE_REQUOTE"),
    ("invalid_stops", r"invalid stops|TRADE_RETCODE_INVALID_STOPS|not enough money"),
    ("margin", r"margin|TRADE_RETCODE_NO_MONEY"),
    ("timeout", r"timeout|TRADE_RETCODE_TIMEOUT"),
    ("array_range", r"array out of range|zero divide|critical error"),
    ("oninit_fail", r"OnInit .*(fail|INIT_FAILED)|INIT_PARAMETERS_INCORRECT"),
    ("cannot_open", r"cannot open|file open error|history .*(missing|not found)"),
]
SAMPLE_CAP = 3
SAMPLE_CHARS = 200


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("log", type=Path)
    ap.add_argument("--extra-pattern", action="append", default=[],
                    help="name=regex, repeatable")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    battery = list(BATTERY)
    for spec in args.extra_pattern:
        name, _, rx = spec.partition("=")
        battery.append((name, rx))
    compiled = [(name, re.compile(rx, re.IGNORECASE)) for name, rx in battery]

    hits: dict[str, dict] = {name: {"count": 0, "first_line": None, "last_line": None,
                                    "samples": []} for name, _ in compiled}
    total = 0
    with args.log.open("r", encoding="utf-8", errors="replace") as fh:
        for lineno, line in enumerate(fh, 1):
            total = lineno
            for name, rx in compiled:
                if rx.search(line):
                    h = hits[name]
                    h["count"] += 1
                    h["first_line"] = h["first_line"] or lineno
                    h["last_line"] = lineno
                    if len(h["samples"]) < SAMPLE_CAP:
                        h["samples"].append(
                            {"line": lineno, "text": line.strip()[:SAMPLE_CHARS]})

    summary = {
        "schema_version": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "log": str(args.log), "bytes": args.log.stat().st_size,
        "lines": total,
        "log_sha256_first_1mb": hashlib.sha256(
            args.log.open("rb").read(1 << 20)).hexdigest().upper(),
        "battery": {name: h for name, h in hits.items()},
        "clean": all(h["count"] == 0 for h in hits.values()),
    }
    out = args.out or args.log.with_suffix(args.log.suffix + ".triage.json")
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    flagged = {n: h["count"] for n, h in hits.items() if h["count"]}
    print(f"LOG_TRIAGE lines={total} flagged={flagged or 'CLEAN'} out={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
