"""Sanity tests cho indicators + gates + signal (chạy: python3 validation/test_indicators.py)"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from features.indicators import wilder_rma, atr_wilder, adx_wilder, detrend, rolling_half_life, atr_percentile
from features.gates import compute_features, evaluate_gates
from core.signal import evaluate_signal
from data.loader import load_bars
import yaml

ROOT = Path(__file__).resolve().parents[1]
PARAMS = yaml.safe_load(open(ROOT / "config/params.yml", encoding="utf-8"))
COSTS = yaml.safe_load(open(ROOT / "config/costs.yml", encoding="utf-8"))
FAILS = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'}  {name}  {detail}")
    if not cond:
        FAILS.append(name)


# 1) Wilder RMA: giá trị đầu = SMA(period), sau đó công thức đệ quy
s = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=float)
r = wilder_rma(s, 3)
check("wilder_rma init = SMA(3)", abs(r.iloc[2] - 2.0) < 1e-12, f"{r.iloc[2]}")
check("wilder_rma recursion", abs(r.iloc[3] - (2.0 + (4 - 2.0) / 3)) < 1e-12, f"{r.iloc[3]}")

# 2) Half-life trên OU giả lập biết đáp án: theta=0.05 -> HL_true = ln2/0.05 ≈ 13.86
rng = np.random.default_rng(0)
n, theta = 4000, 0.05
x = np.zeros(n)
for i in range(1, n):
    x[i] = x[i-1] + theta * (0.0 - x[i-1]) + rng.normal(0, 1.0)
D = pd.Series(x)
lam, hl = rolling_half_life(D, 300)
med = np.nanmedian(hl.iloc[500:])
check("half-life OU ~ 13.86 (±30%)", 0.7 * 13.86 < med < 1.3 * 13.86, f"median={med:.2f}")

# 3) Không có HL âm (lambda >= 0 -> NaN)
trend = pd.Series(np.arange(500, dtype=float))
_, hl_t = rolling_half_life(trend - trend.rolling(100).mean(), 100)
check("không có HL âm", not (hl_t.dropna() < 0).any())

# 4) z-score: demo mode phải có |z| vượt 2 tại đâu đó (setup tồn tại)
df = load_bars("EURUSD", "H1", 1500, source="demo")
feats = compute_features(df, 100)
check("demo có |z|>=2", (feats["z"].abs() >= 2).sum() > 5, f"count={(feats['z'].abs()>=2).sum()}")

# 5) ATR percentile trong [0,100]
ap = feats["atr_pctile"].dropna()
check("ATR pctile in [0,100]", bool(((ap >= 0) & (ap <= 100)).all()))

# 6) Session gate: EURUSD [7,16) UTC — nửa mở
df4 = load_bars("EURUSD", "H4", 300, source="demo")
g_in = evaluate_gates("EURUSD", feats, df4, PARAMS, COSTS,
                      now_utc=pd.Timestamp("2026-07-17 10:00", tz="UTC"))
g_out = evaluate_gates("EURUSD", feats, df4, PARAMS, COSTS,
                       now_utc=pd.Timestamp("2026-07-17 16:00", tz="UTC"))
sess_in = [g for g in g_in.gates if g.name == "Session UTC"][0]
sess_out = [g for g in g_out.gates if g.name == "Session UTC"][0]
check("session 10:00 UTC pass", sess_in.passed)
check("session 16:00 UTC fail (nửa mở)", not sess_out.passed)

# 7) Signal plan: sizing khớp §8, time-stop bị chặn night-cap
dfx = load_bars("XAUUSD", "H1", 1500, source="demo")
fx = compute_features(dfx, 100)
gx = evaluate_gates("XAUUSD", fx, load_bars("XAUUSD", "H4", 300, source="demo"), PARAMS, COSTS)
plan = evaluate_signal("XAUUSD", fx, gx, PARAMS, COSTS, account_equity=10_000)
R_exp = 2.0 * fx["atr14"].iloc[-1]
lots_exp = np.floor(50.0 / (R_exp * 100) * 100) / 100
check("sizing formula khớp §8", abs(plan.lots - lots_exp) < 0.011, f"{plan.lots} vs {lots_exp:.2f}")
check("time-stop <= night-cap bars", plan.effective_time_stop_bars <= 2 * 24, f"{plan.effective_time_stop_bars}")

# 8) TP validity: tp phải ở phía có lợi so với entry_ref khi có hướng
if plan.direction.startswith("LONG"):
    check("TP > entry (long)", plan.tp > plan.entry_ref)
elif plan.direction.startswith("SHORT"):
    check("TP < entry (short)", plan.tp < plan.entry_ref)
else:
    check("TP side (no signal -> skip)", True)

print("\n" + ("ALL PASS" if not FAILS else f"FAILED: {FAILS}"))
sys.exit(0 if not FAILS else 1)
