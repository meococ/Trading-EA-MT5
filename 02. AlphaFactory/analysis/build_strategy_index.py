#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build Strategy Index — Parse STRATEGY_LOG.md into structured JSON
=================================================================

Parses the STRATEGY_LOG.md file and produces a structured strategy_index.json
with per-strategy fields: id, name, status, pf, dd, wfa_pass, mc_p95, date, lessons.

Usage:
    python build_strategy_index.py
    python build_strategy_index.py --log "path/to/STRATEGY_LOG.md" --output "strategy_index.json"
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional


@dataclass
class StrategyEntry:
    """Structured representation of a single strategy in the log."""
    id: str
    name: str
    status: str
    pf: Optional[float] = None
    max_dd_pct: Optional[float] = None
    wfa_pass_rate: Optional[float] = None
    mc_p95_dd: Optional[float] = None
    date: Optional[str] = None
    total_trades: Optional[int] = None
    lessons: List[str] = field(default_factory=list)
    notes: Optional[str] = None


# ── Status normalization ─────────────────────────────────────────────

STATUS_MAP = {
    "PASSED": "PASSED",
    "FAILED": "FAILED",
    "WEAK": "WEAK",
    "TESTING": "TESTING",
    "TUNING": "TUNING",
    "BASELINE": "BASELINE",
    "REGIME": "REGIME",
    "VALIDATED": "VALIDATED",
}


def normalize_status(raw: str) -> str:
    """Normalize status string to canonical form."""
    upper = raw.upper().strip()
    for key, val in STATUS_MAP.items():
        if key in upper:
            return val
    return upper


# ── Quick-table parser ───────────────────────────────────────────────

_TABLE_ROW_RE = re.compile(
    r"\|\s*(S\d+)\s*\|\s*(.+?)\s*\|\s*(?:[❌⚠️✅🔬]*\s*)?(\w+)\s*\|\s*([\d.]+)\s*\|\s*(.*?)\s*\|"
)


def parse_quick_table(lines: List[str]) -> List[StrategyEntry]:
    """Parse the quick-overview table at the top of STRATEGY_LOG.md."""
    entries: List[StrategyEntry] = []
    for line in lines:
        m = _TABLE_ROW_RE.search(line)
        if m:
            sid = m.group(1).strip()
            name = m.group(2).strip()
            status = normalize_status(m.group(3).strip())
            pf_raw = m.group(4).strip()
            notes = m.group(5).strip()

            pf: Optional[float] = None
            try:
                pf = float(pf_raw)
            except ValueError:
                pass

            entries.append(StrategyEntry(
                id=sid,
                name=name,
                status=status,
                pf=pf,
                notes=notes if notes else None,
            ))
    return entries


# ── Detail-section parser ────────────────────────────────────────────

_SECTION_HEADER_RE = re.compile(r"^###\s+(S\d+):\s*(.+)")
_DATE_RE = re.compile(r"\*\*Date:\*\*\s*(.+)")
_STATUS_RE = re.compile(r"\*\*Status:\*\*\s*(.+)")
_TRADES_RE = re.compile(r"Trades:\s*(\d+)")
_DD_RE = re.compile(r"(?:Max\s+)?(?:DD|Drawdown):\s*([\d.]+)%?")
_WFA_RE = re.compile(r"WFA.*?(?:Pass|pass).*?(\d+)[/](\d+)|WFA.*?([\d.]+)%")
_MC_RE = re.compile(r"Monte\s*Carlo.*?P95.*?DD.*?([\d.]+)%?")
_LESSON_RE = re.compile(r"^>\s*⚠️?\s*(.+)")


def parse_detail_sections(text: str, entries: List[StrategyEntry]) -> None:
    """Enrich entries with data from detailed sections."""
    entry_map = {e.id: e for e in entries}

    sections = re.split(r"(?=^###\s+S\d+)", text, flags=re.MULTILINE)
    for section in sections:
        header_m = _SECTION_HEADER_RE.search(section)
        if not header_m:
            continue
        sid = header_m.group(1)
        entry = entry_map.get(sid)
        if entry is None:
            # Strategy in detail but not in quick table — create new entry
            entry = StrategyEntry(id=sid, name=header_m.group(2).strip(), status="UNKNOWN")
            entries.append(entry)
            entry_map[sid] = entry

        # Date
        date_m = _DATE_RE.search(section)
        if date_m:
            entry.date = date_m.group(1).strip()

        # Status (if not already set from table)
        status_m = _STATUS_RE.search(section)
        if status_m and entry.status == "UNKNOWN":
            entry.status = normalize_status(status_m.group(1))

        # Total trades
        trades_m = _TRADES_RE.search(section)
        if trades_m:
            entry.total_trades = int(trades_m.group(1))

        # Max DD
        dd_m = _DD_RE.search(section)
        if dd_m:
            try:
                entry.max_dd_pct = float(dd_m.group(1))
            except (ValueError, TypeError):
                pass

        # WFA
        wfa_m = _WFA_RE.search(section)
        if wfa_m:
            if wfa_m.group(1) and wfa_m.group(2):
                entry.wfa_pass_rate = int(wfa_m.group(1)) / int(wfa_m.group(2))
            elif wfa_m.group(3):
                entry.wfa_pass_rate = float(wfa_m.group(3)) / 100.0

        # Monte Carlo
        mc_m = _MC_RE.search(section)
        if mc_m:
            try:
                entry.mc_p95_dd = float(mc_m.group(1))
            except (ValueError, TypeError):
                pass

        # Lessons
        for line in section.split("\n"):
            lesson_m = _LESSON_RE.match(line.strip())
            if lesson_m:
                entry.lessons.append(lesson_m.group(1).strip())


def parse_strategy_log(filepath: Path) -> List[StrategyEntry]:
    """Parse a STRATEGY_LOG.md file into structured entries."""
    text = filepath.read_text(encoding="utf-8")
    lines = text.split("\n")

    # Parse quick-overview table
    entries = parse_quick_table(lines)

    # Enrich with detail sections
    parse_detail_sections(text, entries)

    # Sort by strategy ID
    entries.sort(key=lambda e: int(re.sub(r"\D", "", e.id) or "0"))

    return entries


def build_index(entries: List[StrategyEntry]) -> dict:
    """Build the strategy index document."""
    stats = {
        "total": len(entries),
        "passed": sum(1 for e in entries if e.status == "PASSED"),
        "failed": sum(1 for e in entries if e.status == "FAILED"),
        "weak": sum(1 for e in entries if e.status == "WEAK"),
        "testing": sum(1 for e in entries if e.status in ("TESTING", "TUNING", "BASELINE")),
    }

    return {
        "version": "1.0",
        "source": "STRATEGY_LOG.md",
        "stats": stats,
        "strategies": [asdict(e) for e in entries],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse STRATEGY_LOG.md into strategy_index.json"
    )
    parser.add_argument(
        "--log",
        type=str,
        default=None,
        help="Path to STRATEGY_LOG.md (default: auto-detect)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON path (default: strategy_index.json next to log)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON to stdout",
    )

    args = parser.parse_args()

    # Resolve log path
    if args.log:
        log_path = Path(args.log)
    else:
        # Auto-detect: look relative to script location
        script_dir = Path(__file__).resolve().parent
        candidates = [
            script_dir.parent / "STRATEGY_LOG.md",
            script_dir / "STRATEGY_LOG.md",
        ]
        log_path = None
        for c in candidates:
            if c.exists():
                log_path = c
                break
        if log_path is None:
            print("ERROR: Cannot find STRATEGY_LOG.md. Use --log to specify path.", file=sys.stderr)
            sys.exit(1)

    if not log_path.exists():
        print(f"ERROR: File not found: {log_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Parsing: {log_path}")
    entries = parse_strategy_log(log_path)
    index = build_index(entries)

    # Output
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = log_path.parent / "strategy_index.json"

    if args.json:
        print(json.dumps(index, indent=2, ensure_ascii=False))
    else:
        out_path.write_text(
            json.dumps(index, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Index written to: {out_path}")
        print(f"  Total: {index['stats']['total']} strategies")
        print(f"  Passed: {index['stats']['passed']}")
        print(f"  Failed: {index['stats']['failed']}")
        print(f"  Weak: {index['stats']['weak']}")
        print(f"  Testing: {index['stats']['testing']}")


if __name__ == "__main__":
    main()
