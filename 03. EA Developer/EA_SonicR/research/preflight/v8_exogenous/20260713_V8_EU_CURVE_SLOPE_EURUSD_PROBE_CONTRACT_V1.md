# V8 EU AAA Curve Slope (10Y−2Y) → EURUSD Probe Contract V1 — 2026-07-13

Status: `JOIN_CONTRACT_FROZEN / OFFLINE_PROBE_ONLY / NO_EA_BUILD`

## Authority

Owner autonomous self-research (no GPT). Uses already-frozen US–EU panel
field `eu_curve_10y_minus_2y` only (ECB AAA 10Y−2Y). One cheap offline probe.
No registry/prereg/EA/Model 0 unless survivor.

## De-dup intake (pre-result)

| Closed family | Why independent |
|---|---|
| `V8_USBILL_SLOPE_USD_BASKET` | US **bill** curve → multi-pair USD basket. This is **EU AAA sovereign** 10Y−2Y → EURUSD only. |
| `V8_USEU_10Y_DIFF_EURUSD` | Cross-market US−EU **level** differential. This is **EU domestic** curve shape only (US series unused for signal). |
| `V8_USUK_10Y_DIFF_GBPUSD` | US−UK cross-market → GBPUSD. Different pair + different state. |
| G3 short-rate carry / COT / carry×vol | Different causal surfaces. |
| `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001` | No FX-return factor / pullback-break. |

## Probe identity

- Probe tag: `V8_EU_CURVE_SLOPE_EURUSD_V1`
- Panel: `preflight/v8_exogenous/panels/us_eu_bond_yield_diff_d1_v1.csv`
- Field: `eu_curve_10y_minus_2y`
- Lag: `available_at_utc` (observation + 1 calendar day)

## Signal (frozen a priori — same constants as sibling bond probes)

1. `slope_t` = lagged EU AAA (10Y−2Y) available on decision date `t`.
2. `z_t` over lookback 60 (≥40 obs).
3. `z >= +0.75` → long EURUSD; `z <= −0.75` → short EURUSD; else flat.
4. D1 Mon–Thu entry; Friday flatten; stop 1.5×ATR14; time-stop 5 bars.
5. Stress A/B 1.5/3.0 pip RT. Train 2019–2022; holdout gated.
6. Control: same |z| gate; direction = sign(20d EURUSD return).

Thesis: steeper EA curve (higher term premium / easier relative funding path)
favors EUR vs USD; inverted/flat curve favors USD. A priori sign — not mined.

## Kills

trades&lt;80; tpw&lt;0.5; PF-A&lt;1.05; fail beat control PF-A and expectancy-A;
year concentration of positive net-A &gt; 0.55.

## Non-rescues

No z/tenor/session mining from readout. No garnish onto killed USEU/USUK books.
