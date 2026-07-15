# HYP-SR-FX-USBILL-SLOPE-USD-BASKET-001 Model 0 Readout

Date: 2026-07-14  
Hypothesis: `HYP-SR-FX-USBILL-SLOPE-USD-BASKET-001`  
EA: `EA_UsBillSlopeBasket`  
Probe: `V8_USBILL_SLOPE_USD_BASKET_V1` (`PROBE_SURVIVOR` offline)  
Authority: Owner free-MT + self-direct (2026-07-14)

## Verdict

**`KILLED_AT_MODEL_0`**

Challenger does **not** beat matched control on tester PF / net / expectancy.
Neither run approaches North-Star PF>1.30 after verified true cost. Cost grade
remains `UNVERIFIED_TESTER_DEFAULT` (MetaQuotes-Demo / spread=`current`) —
honest research-pass screen only; **not** confirmed / GOAL.

Do **not** retune z / tenor / ATR / time-stop / session from this readout.

## Runs (Model 0, EURUSD D1 host, basket legs EURUSD+GBPUSD+USDJPY)

| Role | Run ID | Overrides | PF | Net $ | Trades | Exp. $ | Equity DD max | Bars |
|---|---|---|---:|---:|---:|---:|---|---:|
| Control | `20260714_013628` | `InpMode=0` | **1.05** | 586.28 | 1124 | 0.52 | 13.59% | 1818 |
| Challenger | `20260714_014003` | `InpMode=1` | **1.03** | 383.49 | 989 | 0.39 | 10.63% | 1818 |

- Window: 2019.01.01 – 2025.12.31, Deposit=10000, Leverage=100, Model=0
- Symbols in tester: **3** (basket legs active)
- History quality: 99%
- Cadence (leg-level, elapsed ~364 calendar weeks): challenger ≈ **2.72**/week;
  basket-equivalent ≈ trades/3 ≈ **0.9**/week (aligned with offline ~1/week;
  below North-Star 2–5)
- Alpha closeout threw known `includes_sha256` mismatch after report ready;
  `report.html` + `run_manifest.json` retained under run folders

## Cost provenance

- Grade: `RESEARCH_PROXY_TESTER_SPREAD_ONLY`
- Observed server: MetaQuotes-Demo (Real/`FivePercentOnline` not reachable)
- Missing broker bid/ask/commission/slippage — **must not** be treated as zero
- Stress x1.5/x2 / QFSI not run; irrelevant after edge fails vs control at x1 tester

## Non-repaint / closed-bar

- Decisions on D1 `bar[1]` / `CopyBuffer(..., shift=1)`
- `iTime(..., 0)` used only for new-bar detect
- CSV z already lagged (`obs_date+1d`); as-of lookup with max gap 3d
- Audit: **PASS** for closed-bar decision path

## Gate check vs GOAL

| Gate | Result |
|---|---|
| Beat matched control PF + expectancy | **FAIL** (1.03 < 1.05; 0.39 < 0.52) |
| PF > 1.30 after verified true cost x1 | **FAIL** (1.03; cost unverified) |
| Cadence 2–5/week elapsed (basket book) | **FAIL** (~0.9 basket/week) |
| x1.5 PF≥1.25 / x2 PF≥1.00 | Not promoted (edge already fails) |
| Confirmed / 84m promotion | **Blocked** |

## Artifacts

- EA: `03. EA Developer/EA_UsBillSlopeBasket/EA_UsBillSlopeBasket.mq5`
- CSV: `usbill_slope_z_d1.csv` (2090 rows; build manifest beside EA)
- Control run: `02. AlphaFactory/runs/EA_UsBillSlopeBasket/20260714_013628/`
- Challenger run: `02. AlphaFactory/runs/EA_UsBillSlopeBasket/20260714_014003/`
- Receipts: `preflight/usbill_slope_basket/contracts/`
- Offline survivor JSON (unchanged): `preflight/v8_probe/20260713_V8_USBILL_SLOPE_USD_BASKET_PROBE_RESULT_V1.json`

## Next move (lawful)

1. Close this hypothesis version as **killed** (preserve evidence).
2. Do not post-hoc filter / retune from this readout.
3. Self-research next independent ID (GPT waived). Price-M15 shelf:
   `HYP-CHOP-TREND-M15-001`. Real QFSI still needed before any confirmed claim
   on remaining cost-sensitive books (e.g. USD-factor).
