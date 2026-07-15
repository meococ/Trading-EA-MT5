import json
from pathlib import Path

root = Path(r"d:\Trading EA MT5\02. AlphaFactory\runs")
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


def loadj(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def pick(d: dict, *keys):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None


for ea, rid in runs:
    p = root / ea / rid
    print("====", ea, rid, "====")
    m = p / "run_manifest.json"
    s = p / "analysis" / "enhanced_summary.json"
    r = p / "report.html"
    if m.exists():
        d = loadj(m)
        print("hyp", d.get("hypothesis_id"), "role", d.get("run_role"))
        print("ovr", d.get("overrides"))
        print("sym", d.get("symbol"), "dep", d.get("deposit"))
    if s.exists():
        d = loadj(s)
        print("keys", list(d.keys())[:30])
        nested = d.get("summary") if isinstance(d.get("summary"), dict) else d
        if isinstance(d.get("metrics"), dict):
            nested = {**nested, **d["metrics"]}
        print(
            "PF",
            pick(nested, "profit_factor", "ProfitFactor", "pf"),
            "trades",
            pick(nested, "total_trades", "TotalTrades", "trades"),
            "net",
            pick(nested, "net_profit", "NetProfit", "net"),
            "dd",
            pick(nested, "max_equity_dd_pct", "max_drawdown_pct", "MaxEquityDD"),
        )
    elif r.exists():
        print("report exists, no enhanced_summary")
    else:
        print("INCOMPLETE")

lock = Path(r"d:\Trading EA MT5\02. AlphaFactory\runtime\alpha_backtest.lock")
print("LOCK", lock.exists())
