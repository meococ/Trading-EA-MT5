# De-dup Clearance — VIXCLS risk-off → USDJPY — 2026-07-14

Status: `INTAKE_CLEARED / INDEPENDENT` (pre-result; does not grant survivor)

## Proposed probe

| Field | Value |
|---|---|
| Working ID | `HYP-SR-FX-VIX-RISKOFF-USDJPY-001` (mint only if probe survives) |
| Probe tag | `V8_VIX_RISKOFF_USDJPY_V1` |
| Surface | Lagged CBOE VIXCLS level z-gate → USDJPY D1 |

## Closed families checked

| Closed / active family | Why independent |
|---|---|
| `V8_EQUITY_BOND_DIFF_V1` | That book used **SPX−DGS10 excess**; VIX was archived **unused**. This probe uses **VIXCLS alone** as the signal — not an overlay rescue of the killed equity−bond book. |
| V8 carry / OIS SOFR−€STR / US−JP bond | Rates / RFR / sovereign curves. Unused here. |
| COT TFF / USBILL | Positioning / bill slope. Unused here. |
| S559 / EA_VixFixScalp | Williams **VixFix from OHLC** + Stoch on **XAUUSD M15**. This is **CBOE VIXCLS** exogenous → **USDJPY D1**. |
| S682–S685 equity-close hour | Intraday hour drift. Unused here. |
| Price-M15 shelf (SB/Spark/VolExp/Chop/…) | Different timescale and causal surface. |

## Explicit non-claims

- Not a post-hoc VIX gate added to killed equity−bond.
- Not SOFR−SONIA twin rescue.
- Not true FX forwards / licensed vendor VIX futures curve.

## Authority

Clearance authorizes **one** cheap offline probe only. Registry/prereg/EA/Model 0
remain closed unless the probe survives doctrine floors.
