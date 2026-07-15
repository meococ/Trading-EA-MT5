#!/usr/bin/env python3
"""Honest multi-day cost table from QFSI ticks + autonomous live deal import.

Never invents spreads. SHA-freeze only if research-grade (not this run).
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
EV = ROOT / "02. AlphaFactory" / "evidence" / "execution" / "FivePercentOnline-Real"
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
OUT_JSON = PRE / "20260715_COST_MULTIDAY_TABLE_R24.json"
OUT_MD = READ / "20260715_COST_MULTIDAY_TABLE_R24.md"
IMP = EV / "20260715_DEAL_HISTORY_IMPORT_LIVE_R24"

SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]
SESS = {
    "ASIA": range(0, 7),
    "LONDON": range(7, 12),
    "LONDON_NY": range(12, 16),
    "NY": range(16, 21),
    "OFF": range(21, 24),
}


def sess(h: int) -> str:
    for n, r in SESS.items():
        if h in r:
            return n
    return "OFF"


def pct(xs: list[float], q: float) -> float | None:
    if not xs:
        return None
    ys = sorted(xs)
    pos = (len(ys) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return ys[lo]
    return ys[lo] * (1 - (pos - lo)) + ys[hi] * (pos - lo)


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def main() -> None:
    quote_days: set[str] = set()
    hour_spreads: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    tick_n: dict[str, int] = defaultdict(int)
    sessions: list[str] = []

    for d in sorted(EV.iterdir()):
        if not d.is_dir():
            continue
        if "QFSI_REAL" not in d.name and "COST_TICK" not in d.name:
            continue
        sessions.append(d.name)
        for sym in SYMBOLS:
            qp = d / f"{sym}_quote_ticks.csv"
            if not qp.exists():
                continue
            with qp.open(encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    try:
                        bid = float(row.get("bid") or row.get("Bid") or 0)
                        ask = float(row.get("ask") or row.get("Ask") or 0)
                    except ValueError:
                        continue
                    if bid <= 0 or ask <= bid:
                        continue
                    ts = (
                        row.get("time_utc")
                        or row.get("time")
                        or row.get("Time")
                        or ""
                    )
                    day = ts[:10] if ts else None
                    hour = None
                    if "T" in ts:
                        try:
                            hour = int(ts[11:13])
                        except ValueError:
                            pass
                    elif " " in ts:
                        try:
                            hour = int(ts.split(" ")[1][:2])
                        except (ValueError, IndexError):
                            pass
                    spr = ask - bid
                    if day:
                        quote_days.add(day)
                    tick_n[sym] += 1
                    if hour is not None:
                        hour_spreads[sym][f"{sess(hour)}|{hour:02d}"].append(spr)

    comm: dict[str, dict] = {}
    for sym in SYMBOLS + ["BTCUSD"]:
        p = IMP / f"{sym}_commission_lifecycles.csv"
        rows: list[dict] = []
        if p.exists():
            with p.open(encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
        vals = [
            float(r["round_turn_account_per_lot"])
            for r in rows
            if r.get("round_turn_account_per_lot")
        ]
        days = sorted(
            {
                (r.get("open_time_utc") or "")[:10]
                for r in rows
                if r.get("open_time_utc")
            }
        )
        days = [d for d in days if d]
        comm[sym] = {
            "n": len(vals),
            "p50": pct(vals, 0.5),
            "p90": pct(vals, 0.9),
            "unique_days": days,
            "need": 30,
        }

    table: dict[str, dict] = {}
    for sym in SYMBOLS:
        table[sym] = {}
        for key, xs in sorted(hour_spreads[sym].items()):
            table[sym][key] = {
                "n": len(xs),
                "p50": pct(xs, 0.5),
                "p90": pct(xs, 0.9),
            }

    man = IMP / "import_manifest.json"
    man_sha = sha256_file(man) if man.exists() else None
    raw_sha = (
        sha256_file(IMP / "raw_history_deals.csv")
        if (IMP / "raw_history_deals.csv").exists()
        else None
    )

    payload = {
        "schema_version": "cost_multiday_table_r24.v1_diagnostic",
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "grade": "SINGLE_DAY_OR_SHALLOW_HISTORY_DIAGNOSTIC_ONLY",
        "freeze_eligible": False,
        "qfsi_sessions_scanned": sessions,
        "quote_days_unique": sorted(quote_days),
        "quote_days_count": len(quote_days),
        "quote_days_need": 90,
        "tick_counts": dict(tick_n),
        "commission_from_live_history_deals": comm,
        "live_import": {
            "dir": str(IMP),
            "manifest_sha256": man_sha,
            "raw_deals_sha256": raw_sha,
            "raw_deal_count": 11,
        },
        "slippage": "MISSING_NOT_ZERO_CANNOT_MINT",
        "session_hour_spread_price_units": table,
        "notes": [
            "Spreads are observed bid-ask from QFSI quote ticks only — not invented.",
            "Coverage is shallow (few calendar days). NOT research-grade freeze.",
            "Live history_deals_get 3650d returned 11 raw deals; EURUSD comm=2/30.",
            "Owner deal-export optional; not headline ask.",
        ],
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    payload["artifact_sha256"] = sha256_file(OUT_JSON)
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Multi-day cost table R24 (diagnostic)",
        "",
        f"Generated: {payload['generated_at_utc']}",
        f"Grade: `{payload['grade']}` — freeze_eligible=**False**",
        f"Artifact SHA256: `{payload['artifact_sha256']}`",
        "",
        "## Coverage",
        f"- Unique quote UTC days: **{len(quote_days)}**/90 → `{sorted(quote_days)}`",
        f"- Tick counts: `{dict(tick_n)}`",
        "- Live deals import (autonomous `history_deals_get` 3650d): raw=**11**; "
        "EURUSD comm=**2**/30; USDJPY=**0**/30; slip **MISSING≠0**",
        f"- Import manifest SHA: `{man_sha}`",
        f"- Raw deals SHA: `{raw_sha}`",
        "",
        "## Commission (autonomous live history)",
        "| Symbol | N | P50 $/lot RT | unique open days |",
        "|---|---:|---:|---|",
    ]
    for sym, c in comm.items():
        days_s = ", ".join(c["unique_days"]) if c["unique_days"] else "—"
        lines.append(f"| {sym} | {c['n']} | {c['p50']} | {days_s} |")
    lines += ["", "## Session×hour spread P50 (price units, observed ticks only)", ""]
    for sym in SYMBOLS:
        rows = table.get(sym) or {}
        if not rows:
            lines.append(f"### {sym}: no ticks")
            continue
        lines.append(f"### {sym}")
        lines.append("| Session|Hour | N | P50 | P90 |")
        lines.append("|---|---:|---:|---:|")
        for k, v in list(rows.items())[:48]:
            lines.append(f"| {k} | {v['n']} | {v['p50']} | {v['p90']} |")
        if len(rows) > 48:
            lines.append(f"… {len(rows) - 48} more hour buckets omitted")
        lines.append("")
    lines += [
        "## Remaining GAP",
        "- quote_days ≪ 90",
        "- commission primary symbols ≪ 30",
        "- slip samples = 0 (MISSING ≠ 0)",
        "- **No research-grade SHA freeze.** Do not invent spreads.",
        "- Keep QFSI 007 accumulate; retry `history_deals_get` as account ages.",
        "",
        f"JSON: `preflight/{OUT_JSON.name}`",
        "",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "quote_days": len(quote_days),
                "days": sorted(quote_days),
                "ticks": dict(tick_n),
                "comm": {k: v["n"] for k, v in comm.items()},
                "artifact_sha": payload["artifact_sha256"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
