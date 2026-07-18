"""Contract tests for br_sessdrift_offline_probe (PROBE_PLAN section 4)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from br_sessdrift_offline_probe import simulate, wilder_atr14

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(("PASS  " if cond else "FAIL  ") + name + ("  " + detail if detail else ""))
    if not cond:
        FAILS.append(name)


def frame(hours_prices: list[tuple[str, float, float, float, float]]) -> pd.DataFrame:
    rows = []
    for ts, o, h, l, c in hours_prices:
        rows.append({"time_utc": pd.Timestamp(ts), "open": o, "high": h, "low": l, "close": c})
    df = pd.DataFrame(rows)
    df["time_server"] = df["time_utc"] + pd.Timedelta(hours=2)
    df["atr14"] = 0.0010  # 10 pips fixed for tests
    return df


BASE = 1.10000
DAY = "2021-06-07"


def mk_day(day: str, prices: dict[int, float]) -> list[tuple[str, float, float, float, float]]:
    out = []
    for hour in range(0, 24):
        p = prices.get(hour, BASE)
        out.append((f"{day} {hour:02d}:00", p, p + 0.0002, p - 0.0002, p))
    return out


# 1. Bar selection + short PnL sign: price falls 07->11 => short wins
df = frame(mk_day(DAY, {7: 1.10000, 11: 1.09800, 13: 1.10000, 17: 1.10000}))
trades, skips = simulate(df, use_sl=False)
short = [t for t in trades if t["direction"] == -1]
check("two windows per day", len(trades) == 2, f"n={len(trades)}")
check("short entry at 07 open / exit at 11 open",
      len(short) == 1 and abs(short[0]["entry"] - 1.10000) < 1e-9 and abs(short[0]["exit"] - 1.09800) < 1e-9)
# gross_r = -1 * (1.09800-1.10000) / (2*0.0010) = +1.0
check("short gross_r sign/magnitude", abs(short[0]["gross_r"] - 1.0) < 1e-9, f"{short[0]['gross_r']}")

# 2. Missing end bar -> day skipped for that window
rows = [r for r in mk_day(DAY, {}) if not r[0].endswith("11:00")]
df = frame(rows)
trades, skips = simulate(df, use_sl=False)
check("missing 11:00 bar skips short window", len([t for t in trades if t["direction"] == -1]) == 0
      and skips["missing_bars"] >= 1)

# 3. Cost math: net_x1 = gross - 1.5/r_pips ; r_pips = 20
df = frame(mk_day(DAY, {7: 1.10000, 11: 1.10000}))
trades, _ = simulate(df, use_sl=False)
t0 = [t for t in trades if t["direction"] == -1][0]
check("cost x1 = 1.5 pips over 20-pip R", abs(t0["net_r_x1"] - (0.0 - 1.5 / 20.0)) < 1e-9, f"{t0['net_r_x1']}")
check("cost x2 doubles", abs(t0["net_r_x2"] - (0.0 - 3.0 / 20.0)) < 1e-9)

# 4. SL arm: short SL at entry + 2xATR touched intrabar -> -1R exit
prices = mk_day(DAY, {7: 1.10000, 11: 1.09000})
rows = []
for ts, o, h, l, c in prices:
    if ts.endswith("09:00"):
        rows.append((ts, o, 1.10300, o - 0.0002, o))  # spike through SL 1.10200
    else:
        rows.append((ts, o, h, l, c))
trades, _ = simulate(frame(rows), use_sl=True)
t_sl = [t for t in trades if t["direction"] == -1][0]
check("SL arm exits at SL for -1R", t_sl["reason"] == "SL" and abs(t_sl["gross_r"] + 1.0) < 1e-9,
      f"{t_sl['reason']} {t_sl['gross_r']}")
trades_ns, _ = simulate(frame(rows), use_sl=False)
t_ns = [t for t in trades_ns if t["direction"] == -1][0]
check("nostop arm ignores the spike", t_ns["reason"] == "WINDOW_END")

# 5. ATR warm-up skip: first bars with NaN ATR are skipped
df = frame(mk_day(DAY, {}))
df.loc[: df.index[df["time_utc"].dt.hour == 7][0], "atr14"] = np.nan
trades, skips = simulate(df, use_sl=False)
check("NaN ATR before entry skips window", skips["atr_nan"] >= 1)

# 6. wilder_atr14 sanity on constant range
cf = frame(mk_day(DAY, {}))
atr = wilder_atr14(cf)
check("ATR14 ~ bar range on synthetic", np.isfinite(atr[-1]) and abs(atr[-1] - 0.0004) < 0.0002, f"{atr[-1]:.5f}")

print()
print("ALL PASS" if not FAILS else f"FAILED: {FAILS}")
sys.exit(0 if not FAILS else 1)
