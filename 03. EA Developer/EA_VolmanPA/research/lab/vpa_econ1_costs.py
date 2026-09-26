"""VPA-ECON-1 cost scenarios — read-only reuse of the repo evidence.

Sources (verbatim):
  - PLAN/COST_FEASIBILITY.md:61-62   c_rt = spread(session) + commission_price +
    slippage_p90_rt ; k = c_rt / S
  - PLAN/COST_FEASIBILITY.md:75      EURUSD row: c_rt p90 = **1.0 pips**
    (spread p90 0.1 + slip p90 RT 0.2 + comm 0.7)
  - PLAN/COST_FEASIBILITY.md:118     "rồi dịch bất lợi đúng bằng c_rt (x1/x1.5/x2)"
  - research/lab/vpa_random_baseline.py:41  C_RT_P90 = {"EURUSD": 1.0, ...}
  - HYP-VPA-EURUSD-M5-001_FROZEN_PREREG.md:83-85  required lift x1 +14.1pp,
    x2 +18.2pp (EURUSD London S=8, from the frozen RANDOM_BASELINE.csv)

Application: the all-in round-turn cost is applied ONCE per trade as an adverse
shift of the fill price by `c_rt * mult` (exactly the frozen baseline semantics).
Scenarios: x1 = 1.0 (primary), x1.5 = 1.5, x2 = 2.0; gross = 0.0 (sanity only).
"""

C_RT_P90_PIPS = {"EURUSD": 1.0}   # COST_FEASIBILITY.md:75
COST_SCENARIOS = {"gross": 0.0, "x1": 1.0, "x1.5": 1.5, "x2": 2.0}


def cost_pips(symbol, mult):
    """All-in round-turn cost in pips for a cost multiplier (x1/x1.5/x2)."""
    return C_RT_P90_PIPS[symbol] * mult


def cost_price(symbol, pip, mult):
    return cost_pips(symbol, mult) * pip
