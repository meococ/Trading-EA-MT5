#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
RUNS = ROOT / "02. AlphaFactory" / "runs"
OUT = (
    ROOT
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preflight"
    / "20260714_WAVE4_MODEL0_METRICS.json"
)

SPECS = [
    ("EA_M15IBOverlapBreak", "20260714_223618", "HYP-M15-IB-OVERLAP-BREAK-001"),
    ("EA_H1RVCompressBreak", "20260714_223714", "HYP-H1-RV-COMPRESS-BREAK-001"),
    ("EA_H1GBPJPYLead", "20260714_223748", "HYP-GBPJPY-LEAD-USDJPY-H1-001"),
]


def grab(html: str, label: str) -> str | None:
    # MT5 reports: <td>Label:</td><td nowrap><b>VALUE</b></td>
    pat = re.compile(
        re.escape(label) + r":</td>\s*<td[^>]*>\s*(?:<b>)?\s*([^<]+?)\s*(?:</b>)?\s*</td>",
        re.I,
    )
    m = pat.search(html)
    if not m:
        return None
    return m.group(1).strip().replace("\xa0", " ")


def num(s: str | None):
    if s is None:
        return None
    raw = s.replace("\u00a0", "").replace(" ", "").replace("%", "")
    # keep first token if value like "1.23 (45)"
    raw = raw.split("(")[0]
    try:
        return float(raw)
    except ValueError:
        pass
    # space-thousands already stripped; European comma decimal
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        return s


def main() -> None:
    elapsed_weeks = (date(2025, 12, 31) - date(2021, 1, 1)).days / 7.0
    out = []
    for ea, rid, hyp in SPECS:
        raw = (RUNS / ea / rid / "report.html").read_bytes()
        if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
            html = raw.decode("utf-16")
        else:
            html = raw.decode("utf-8", errors="ignore")
        net = grab(html, "Tổng lợi nhuận ròng")
        pf = grab(html, "Hệ số lợi nhuận")
        trades = grab(html, "Tổng số giao dịch")
        exp = grab(html, "Kỳ vọng lợi nhuận") or grab(html, "Mức lợi nhuận mong muốn")
        dd = grab(html, "Sụt giảm vốn cổ phần tương đối")
        trades_n = num(trades)
        pf_n = num(pf)
        net_n = num(net)
        exp_n = num(exp)
        tpw = (trades_n / elapsed_weeks) if isinstance(trades_n, float) else None
        row = {
            "hypothesis_id": hyp,
            "ea": ea,
            "run_id": rid,
            "pf": pf_n,
            "trades": trades_n,
            "net": net_n,
            "expectancy": exp_n,
            "tpw_elapsed": tpw,
            "dd_relative_raw": dd,
            "elapsed_weeks": elapsed_weeks,
            "raw": {"pf": pf, "trades": trades, "net": net, "exp": exp},
        }
        out.append(row)
        print(json.dumps(row, ensure_ascii=False))
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
