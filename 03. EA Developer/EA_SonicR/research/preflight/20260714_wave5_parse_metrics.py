#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
RUNS = ROOT / "02. AlphaFactory" / "runs"
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
TOOLS = ROOT / "02. AlphaFactory" / "tools" / "sonic_cost_stress.py"

SPECS = [
    ("EA_H1ATRPctileBreak", "20260714_225208", "HYP-H1-ATR-PCTILE-BREAK-001"),
    ("EA_EURUSD_H1AsiaBoxLondonBreak", "20260714_225314", "HYP-EURUSD-H1-ASIA-BOX-LONDON-BREAK-001"),
    ("EA_M15NYIBDriveBreak", "20260714_225340", "HYP-M15-NY-IB-DRIVE-BREAK-001"),
]


def grab(html: str, label: str) -> str | None:
    pat = re.compile(
        re.escape(label) + r":</td>\s*<td[^>]*>\s*(?:<b>)?\s*([^<]+?)\s*(?:</b>)?\s*</td>",
        re.I,
    )
    m = pat.search(html)
    return m.group(1).strip().replace("\xa0", " ") if m else None


def num(s: str | None):
    if s is None:
        return None
    raw = s.replace("\u00a0", "").replace(" ", "").replace("%", "")
    raw = raw.split("(")[0]
    try:
        return float(raw)
    except ValueError:
        pass
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        return s


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def main() -> None:
    elapsed_weeks = (date(2025, 12, 31) - date(2021, 1, 1)).days / 7.0
    out = []
    sha_map = {}
    for ea, rid, hyp in SPECS:
        rp = RUNS / ea / rid / "report.html"
        raw = rp.read_bytes()
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
        rsha = sha(rp)
        sha_map[rid] = rsha

        cout = PRE / f"20260714_WAVE5_COSTSTRESS_{rid}.json"
        cmd = [
            sys.executable,
            str(TOOLS),
            str(RUNS / ea / rid),
            "--ea",
            ea,
            "--base-cost-per-trade",
            "12",
            "--start-equity",
            "100000",
            "--out",
            str(cout),
        ]
        subprocess.check_call(cmd)
        stress = json.loads(cout.read_text(encoding="utf-8"))
        scen = {s["scenario"]: s for s in stress.get("scenarios", [])}
        cs = {
            "x1": scen.get("cost_x1_00", {}).get("profit_factor"),
            "x1_5": scen.get("cost_x1_50", {}).get("profit_factor"),
            "x2": scen.get("cost_x2_00", {}).get("profit_factor"),
            "n": stress.get("report_trade_count"),
            "base_report_pf": scen.get("base_report", {}).get("profit_factor"),
        }

        pfv = float(pf_n or 0)
        tpwv = float(tpw or 0)
        n = float(trades_n or 0)
        if pfv < 1.0 or tpwv < 1.0 or tpwv > 6.0 or n < 80:
            verdict = "KILL"
            reason = f"kill screen pf={pfv} tpw={tpwv:.3f} n={n}"
        elif pfv > 1.30 and 2.0 <= tpwv <= 5.0:
            verdict = "HIT_RESEARCH"
            reason = "research bar"
        else:
            verdict = "PARK"
            reason = f"survive but not HIT pf={pfv} tpw={tpwv:.3f}"

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
            "report_sha256": rsha,
            "cost_stress_base_plus_12": cs,
            "cost_note": (
                f"+$12 x1={cs['x1']} x1.5={cs['x1_5']} x2={cs['x2']}"
                if pfv >= 1.20
                else "PF<1.20 — stress diagnostic only"
            ),
            "verdict": verdict,
            "reason": reason,
            "raw": {"pf": pf, "trades": trades, "net": net, "exp": exp},
        }
        out.append(row)
        print(json.dumps(row, ensure_ascii=False))

    (PRE / "20260714_WAVE5_MODEL0_METRICS.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8"
    )
    (PRE / "20260714_WAVE5_REPORT_SHA.json").write_text(
        json.dumps(sha_map, indent=2), encoding="utf-8"
    )
    print("wrote metrics + sha map")


if __name__ == "__main__":
    main()
