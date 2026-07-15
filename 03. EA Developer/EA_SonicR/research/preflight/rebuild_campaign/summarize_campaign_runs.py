import json
import re
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5\02. AlphaFactory\runs")
ELAPSED_WEEKS = 1825 / 7  # 260.7142857


def loadj(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def trades_from_report(report: Path) -> int | None:
    text = report.read_text(encoding="utf-8", errors="ignore")
    # common MT5 HTML patterns
    for pat in [
        r"Total Trades[^0-9]*([0-9]+)",
        r"Total deals[^0-9]*([0-9]+)",
        r">Total Trades</td>\s*<td[^>]*>\s*([0-9]+)",
        r"Total trades[^0-9]*([0-9]+)",
    ]:
        m = re.search(pat, text, re.I)
        if m:
            return int(m.group(1))
    return None


def summarize(ea: str, rid: str):
    p = ROOT / ea / rid
    out = {"ea": ea, "run_id": rid}
    mpath = p / "run_manifest.json"
    spath = p / "analysis" / "enhanced_summary.json"
    rpath = p / "report.html"
    if mpath.exists():
        m = loadj(mpath)
        out["hyp"] = m.get("hypothesis_id")
        out["role"] = m.get("run_role")
        out["symbol"] = m.get("symbol")
        out["overrides"] = m.get("overrides")
        out["deposit"] = m.get("deposit")
    if spath.exists():
        s = loadj(spath)
        out["pf"] = s.get("profit_factor")
        out["net"] = s.get("net_profit")
        out["n"] = s.get("n_trades")
        out["dd"] = s.get("max_drawdown_pct")
        out["expectancy"] = s.get("expectancy_per_trade")
        out["win_rate"] = s.get("win_rate_pct")
    elif rpath.exists():
        out["n"] = trades_from_report(rpath)
        out["note"] = "report_only"
    else:
        out["note"] = "incomplete"
    if out.get("n"):
        out["tpw"] = round(out["n"] / ELAPSED_WEEKS, 4)
    return out


runs = [
    ("EA_SilverBullet", "20260714_191429"),
    ("EA_SilverBullet", "20260714_191547"),
    ("EA_SilverBullet", "20260714_191628"),
    ("EA_M15SparkAsian", "20260714_191507"),
    ("EA_H1LowVolDonchianMR", "20260714_191727"),
    ("EA_ITSM", "20260714_191845"),
    ("EA_ITSM", "20260714_191955"),
    ("EA_ITSM", "20260714_192116"),
]

# also newest dirs after 19:20
for ea in ["EA_SilverBullet", "EA_ITSM", "EA_M15SparkAsian", "EA_H1LowVolDonchianMR"]:
    base = ROOT / ea
    for d in sorted(base.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:6]:
        if d.is_dir() and d.name.startswith("20260714_19"):
            pair = (ea, d.name)
            if pair not in runs:
                runs.append(pair)

for ea, rid in runs:
    s = summarize(ea, rid)
    print(json.dumps(s, ensure_ascii=False))

print("LOCK", (Path(r"d:\Trading EA MT5\02. AlphaFactory\runtime\alpha_backtest.lock")).exists())
