#!/usr/bin/env python3
"""Parse ITSM Model 0 report metrics (one-shot helper)."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")


def parse_report(path: Path) -> dict:
    raw = path.read_bytes()
    text = None
    for enc in ("utf-16-le", "utf-16", "utf-8", "cp1252"):
        try:
            text = raw.decode(enc)
            break
        except Exception:
            continue
    if text is None:
        text = raw.decode("utf-8", errors="replace")
    text = text.replace("\x00", "")
    out: dict = {}
    pats = {
        "pf": r"Profit factor[^0-9]*([\d.]+)",
        "trades": r"Total trades[^0-9]*(\d+)",
        "net": r"Total net profit[^-\d]*([-\d.\s]+)",
        "expectancy": r"Expected payoff[^-\d]*([-\d.]+)",
        "dd_pct": r"Equity drawdown maximal[^%]*\(([\d.]+)%\)",
        "history_quality": r"History Quality[^0-9]*(\d+)%",
    }
    for k, p in pats.items():
        m = re.search(p, text, re.I)
        if m:
            out[k] = m.group(1).replace(" ", "").strip()
    return out


def main() -> int:
    for rid in ("20260714_003735", "20260714_003635"):
        root = ROOT / "02. AlphaFactory" / "runs" / "EA_ITSM" / rid
        m = json.loads((root / "run_manifest.json").read_text(encoding="utf-8-sig"))
        print("====", rid)
        for k in (
            "hypothesis_id",
            "run_id",
            "ea_name",
            "symbol",
            "period",
            "model",
            "overrides",
            "deposit",
            "leverage",
            "run_role",
            "from_date",
            "to_date",
            "from",
            "to",
            "spread",
            "receipt_sha256",
            "contract_receipt_sha256",
        ):
            if k in m:
                print(f"  {k}={m[k]}")
        print("  keys=", sorted(m.keys()))
        ov = (root / "overrides.txt").read_text(encoding="utf-8", errors="replace").strip()
        print("  overrides.txt=", ov)
        rep = root / "report.html"
        print("  report_sha=", hashlib.sha256(rep.read_bytes()).hexdigest().upper())
        print("  metrics=", parse_report(rep))
        # enhanced summary if present
        enh = root / "analysis" / "enhanced_summary.json"
        if enh.is_file():
            e = json.loads(enh.read_text(encoding="utf-8"))
            print("  enhanced=", {k: e.get(k) for k in ("profit_factor", "total_trades", "net_profit", "expected_payoff", "max_equity_drawdown_pct") if k in e or True})
            print("  enhanced_keys_sample=", list(e.keys())[:25])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
