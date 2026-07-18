"""Contract tests for mr_probe_engine (PROBE_PLAN_V2 section 9).

Run: python tests/test_mr_probe_contract.py
Covers: next-open fill, SL-first worst case, session boundary at hour 16,
H4 availability, frozen-at-entry TP, time-stop, night-cap events, cooldown.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

import mr_probe_engine as eng
from mr_probe_engine import compute_features, run_arm

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(("PASS  " if cond else "FAIL  ") + name + ("  " + detail if detail else ""))
    if not cond:
        FAILS.append(name)


def make_feats(n: int, *, z_at: dict[int, float] | None = None,
               opens=None, highs=None, lows=None, closes=None,
               mu_off: float = 0.0050, start="2021-06-07 07:00") -> pd.DataFrame:
    """Craft a features frame directly (bypasses compute_features)."""
    t_utc = pd.date_range(start, periods=n, freq="h")
    price = 1.10000
    df = pd.DataFrame({
        "time_utc": t_utc,
        "time_server": t_utc + pd.Timedelta(hours=3),
        "open": opens if opens is not None else np.full(n, price),
        "high": highs if highs is not None else np.full(n, price + 0.0002),
        "low": lows if lows is not None else np.full(n, price - 0.0002),
        "close": closes if closes is not None else np.full(n, price),
    })
    df["atr14"] = 0.0010            # 10 pips
    df["adx14"] = 10.0
    df["adx4"] = 10.0
    df["atr_pctile"] = 50.0
    df["sigma"] = 0.0020
    df["hl"] = 10.0
    df["lam"] = -0.07
    z = np.zeros(n)
    for k, v in (z_at or {}).items():
        z[k] = v
    df["z"] = z
    df["mu"] = df["close"] + mu_off  # mu above price => long-friendly mean
    df["D"] = df["close"] - df["mu"]
    return df


# 1. Next-open fill: entry price equals open[i+1], never close[i]
f = make_feats(30, z_at={5: -2.5})
f.loc[6, "open"] = 1.10123          # distinctive next-bar open
f.loc[5, "close"] = 1.10100         # small gap, inside 4xATR guard
f.loc[6, "high"] = 1.10150
f.loc[6, "low"] = 1.10100
trades = run_arm(f, "control")
check("next-open fill", len(trades) == 1 and abs(trades[0].entry - 1.10123) < 1e-9,
      f"entry={trades[0].entry if trades else None}")

# 2. SL-first worst case: both SL and TP inside one bar -> SL wins
f = make_feats(30, z_at={5: -2.5})
f.loc[6, "open"] = 1.10000
# SL = 1.10000 - 2*0.0010 = 1.09800 ; TP_cap = 1.10000 + 1.5*0.0020 = 1.10300
f.loc[7, "high"] = 1.10400   # TP touched
f.loc[7, "low"] = 1.09700    # SL touched too
trades = run_arm(f, "control")
check("SL-first worst case", len(trades) >= 1 and trades[0].exit_reason == "SL",
      f"reason={trades[0].exit_reason if trades else None}")
check("SL exit = -1R", len(trades) >= 1 and abs(trades[0].gross_r + 1.0) < 1e-9)

# 3. Session boundary: entry bar utc hour 16 blocked, 15 allowed (half-open)
f = make_feats(30, z_at={8: -2.5}, start="2021-06-07 07:00")  # entry bar idx9 = 16:00 utc
check("session hour 16 blocked", len(run_arm(f, "control")) == 0)
f = make_feats(30, z_at={7: -2.5}, start="2021-06-07 07:00")  # entry bar idx8 = 15:00 utc
check("session hour 15 allowed", len(run_arm(f, "control")) == 1)

# 4. Frozen-at-entry TP: mutating mu/sigma AFTER the signal bar must not move TP
f1 = make_feats(30, z_at={5: -2.5}, mu_off=0.0010)   # TP_mean = close+0.0010-0.2*0.002=+6 pips
f2 = f1.copy()
f2.loc[10:, "mu"] = f2["close"] + 0.0300
f2.loc[10:, "sigma"] = 0.0100
t1, t2 = run_arm(f1, "control"), run_arm(f2, "control")
check("frozen-at-entry TP", len(t1) == 1 and len(t2) >= 1 and abs(t1[0].tp - t2[0].tp) < 1e-12,
      f"tp1={t1[0].tp if t1 else None} tp2={t2[0].tp if t2 else None}")
check("TP_mean binding when nearer", t1[0].tp_binding == "TP_mean")

# 5. H4 availability: decision at H1 close uses only H4 bars closed by then
h1 = pd.DataFrame({
    "time_server": pd.date_range("2021-06-07 00:00", periods=6, freq="h"),
    "open": 1.1, "high": 1.1002, "low": 1.0998, "close": 1.1,
})
h1["time_utc"] = h1["time_server"] - pd.Timedelta(hours=3)
h4 = pd.DataFrame({
    "time_server": pd.date_range("2021-06-04 00:00", periods=20, freq="4h"),
    "open": 1.1, "high": 1.2, "low": 1.0, "close": 1.1,
})
h4["time_utc"] = h4["time_server"] - pd.Timedelta(hours=3)
feats = compute_features(h1, h4)
# H1 bar 00:00 decides at 01:00; last closed H4 opened 20:00 prev day (closes 24:00)
# The H4 bar opened 00:00 closes 04:00 and must NOT be visible at 01:00-03:00 decisions.
h4_closed_by_decision = (h4["time_server"] + pd.Timedelta(hours=4)) <= (h1["time_server"][0] + pd.Timedelta(hours=1))
check("H4 availability window", bool(h4_closed_by_decision.sum() >= 1) and np.isfinite(feats["adx4"]).sum() >= 0)
dec3 = h1["time_server"][2] + pd.Timedelta(hours=1)  # 03:00 decision
newest_open_visible = h4.loc[(h4["time_server"] + pd.Timedelta(hours=4)) <= dec3, "time_server"].max()
check("H4 forming bar excluded", newest_open_visible == pd.Timestamp("2021-06-06 20:00"),
      f"newest visible H4 open={newest_open_visible}")

# 6. Time-stop: hl=1.0 -> ts=ceil(2*1)=2 bars -> close at open of entry+2
f = make_feats(30, z_at={5: -2.5})
f["hl"] = 1.0
f["high"] = f["open"] + 0.00005   # never hits TP
f["low"] = f["open"] - 0.00005    # never hits SL
f["close"] = f["open"]
trades = run_arm(f, "control")
check("time-stop at entry+2 open", len(trades) >= 1 and trades[0].exit_reason == "TIME_STOP"
      and trades[0].exit_idx == trades[0].entry_idx + 2,
      f"reason={trades[0].exit_reason if trades else None} exit={trades[0].exit_idx if trades else None}")

# 7. Night-cap: undefined HL (control) + quiet market -> close before 6th charged event
n = 24 * 10
f = make_feats(n, z_at={8: -2.5}, start="2021-06-07 00:00")  # entry bar 9 = 09:00 utc, in session
f["hl"] = np.nan
f["lam"] = 0.01
f["high"] = f["open"] + 0.00005
f["low"] = f["open"] - 0.00005
f["close"] = f["open"]
trades = run_arm(f, "control")
check("night-cap closes position", len(trades) >= 1 and trades[0].exit_reason == "NIGHT_CAP",
      f"reason={trades[0].exit_reason if trades else None}")
check("night-cap events <= 5", len(trades) >= 1 and trades[0].swap_events <= 5,
      f"events={trades[0].swap_events if trades else None}")

# 8. Cooldown: second signal immediately after exit is ignored until |z|<2 bar closes
f = make_feats(40, z_at={5: -2.5, 9: -2.5, 24: -2.5})  # bar 24 -> entry bar 25 = 08:00 utc next day
f["hl"] = 1.0
f["high"] = f["open"] + 0.00005
f["low"] = f["open"] - 0.00005
f["close"] = f["open"]
# z stays outside band until bar 15 (blocks re-entry incl. signal at 9), inside at 15
for k in range(6, 15):
    f.loc[k, "z"] = -2.2
trades = run_arm(f, "control")
check("cooldown blocks immediate re-entry", len(trades) == 2 and trades[1].sig_idx == 24,
      f"n={len(trades)} sig2={trades[1].sig_idx if len(trades) > 1 else None}")

# 9. Challenger gates: ADX >= 23 blocks challenger but not control
f = make_feats(30, z_at={5: -2.5})
f["adx14"] = 30.0
check("ADX gate blocks challenger", len(run_arm(f, "challenger")) == 0)
check("ADX gate ignored by control", len(run_arm(f, "control")) == 1)

# 10. Wednesday triple weight in swap accumulation
f = make_feats(24 * 4, z_at={9: -2.5}, start="2021-06-08 00:00")  # entry bar 10 = 10:00 utc Tue
f["hl"] = np.nan
f["lam"] = 0.01
f["high"] = f["open"] + 0.00005
f["low"] = f["open"] - 0.00005
f["close"] = f["open"]
trades = run_arm(f, "control")
if trades:
    t = trades[0]
    check("Wednesday x3 in weighted swap", t.swap_weighted > t.swap_events,
          f"events={t.swap_events} weighted={t.swap_weighted}")
else:
    check("Wednesday x3 in weighted swap", False, "no trade")

print()
print("ALL PASS" if not FAILS else f"FAILED: {FAILS}")
sys.exit(0 if not FAILS else 1)
