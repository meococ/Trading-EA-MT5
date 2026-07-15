from pathlib import Path
import re
import json

run = Path(r"D:\Trading EA MT5\02. AlphaFactory\runs\EA_M15VolExpansion\20260714_000432")
html = (run / "report.html").read_text(encoding="utf-16-le")
html = html.replace("\xa0", " ").replace("\u00a0", " ")
text = re.sub(r"<[^>]+>", "\n", html)
text = re.sub(r"[ \t]+", " ", text)
lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

interesting = []
i = 0
while i < len(lines):
    line = lines[i]
    if line.endswith(":") and i + 1 < len(lines):
        row = [line, lines[i + 1]]
        # sometimes next pairs continue on same visual row
        j = i + 2
        while j + 1 < len(lines) and lines[j].endswith(":") and not lines[j].startswith("http"):
            row.extend([lines[j], lines[j + 1]])
            j += 2
            if len(row) >= 6:
                break
        interesting.append(row)
        i = j if j > i + 2 else i + 2
        continue
    i += 1

def grab(prefix: str):
    for row in interesting:
        for k in range(0, len(row) - 1, 2):
            if row[k].startswith(prefix):
                return row[k + 1]
    return None

pf = grab("Hệ số lợi nhuận")
trades = grab("Tổng số giao dịch")
net = grab("Tổng lợi nhuận ròng")
exp = grab("Mức lợi nhuận mong muốn")
bal_dd = grab("Số dư sụt giảm lớn nhất")
eq_dd = grab("Vốn chủ sở hữu sụt giảm lớn nhất")
win = grab("Giao dịch có lãi")
if not win:
    win = grab("Giao dịch có lãi (% trên tổng số)")

def pct_from(cell):
    if not cell:
        return None
    m = re.search(r"\(([0-9.]+)%\)", cell)
    return m.group(1) if m else None

weeks = 1825 / 7.0
trades_n = float(trades.replace(" ", "")) if trades else None
out = {
    "run_id": "20260714_000432",
    "profit_factor": pf,
    "total_trades": trades.replace(" ", "") if trades else None,
    "net_profit": net.replace(" ", "") if net else None,
    "expectancy": exp,
    "max_balance_dd_pct": pct_from(bal_dd),
    "max_equity_dd_pct": pct_from(eq_dd),
    "win_rate_cell": win,
    "elapsed_calendar_weeks": round(weeks, 2),
    "trades_per_elapsed_week": round(trades_n / weeks, 2) if trades_n else None,
    "history_quality": grab("History Quality"),
    "bars": grab("Thanh"),
    "interesting": interesting[:20],
}
(run / "analysis").mkdir(parents=True, exist_ok=True)
(run / "analysis" / "parsed_metrics_probe.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
)
(run / "analysis" / "report_key_rows.txt").write_text(
    "\n".join(f"{r}" for r in interesting[:30]), encoding="utf-8"
)
summary_path = run / "analysis" / "summary_ascii.json"
summary = {k: v for k, v in out.items() if k != "interesting"}
summary_path.write_text(json.dumps(summary, ensure_ascii=True, indent=2), encoding="utf-8")
print(summary_path.read_text(encoding="utf-8"))
