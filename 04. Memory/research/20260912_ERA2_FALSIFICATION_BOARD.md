# ERA-2 FALSIFICATION BOARD — 2026-09-12

Governed falsification screen, era-2 rebuild. Every cell ran the full
provenance chain (frozen contract + prereg + registry row + task packet +
verified-M1 data quality + non-repaint audit + lifecycle reconciliation +
research-proxy cost stress). No post-hoc rescue was attempted on any cell.

## Kill board (15 hypotheses, 9+ mechanism families, 2 symbols)

| # | Hypothesis | EA | Symbol/TF | Trades | Cad/wk | Gross PF | Cost PF x1.0 | DD% | Kill driver |
|---|---|---|---|---|---|---|---|---|---|
| 1 | CRSIR2-GB | EA_CrsiR2 | GBPUSD M5 | — | — | 0.75 | — | — | economics |
| 2 | AMA-XAU | EA_AMA | XAUUSD M15 | 22,245 | ~15 | 0.91 | 0.59 | 74.5 | costs |
| 3 | VWF-XAU | EA_VwapFade | XAUUSD M5 | 25,417 | ~17.6 | 0.87 | 0.50 | 76.8 | costs |
| 4 | — | EA_HourDrift | XAUUSD M15 | 34,127 | ~23.6 | 0.94 | 0.52 | 82.5 | costs |
| 5 | GBB-S3-XAU | EA_GbbSqueeze | XAUUSD M15 | 408 | ~0.3 | ~1.00 | — | 2.5 | cadence |
| 6 | IBSC-EU | EA_Ibsc | EURUSD M5 | 33,822 | 23.4 | 0.79 | 0.68 | 88.2 | economics |
| 7 | CAMF-EU | EA_CamarillaFade | EURUSD M15 | 14,755 | 10.2 | 0.76 | 0.70 | 57.1 | economics |
| 8 | H1D-EUR | EA_HtfDisplacement | EURUSD M5 | 6,907 | 4.8 | 0.87 | 0.76 | 27.0 | cadence+econ |
| 9 | LSWEEP-EUR | EA_LiquiditySweep | EURUSD M5 | 172 | 0.12 | 0.68 | 0.68 | 10.0 | cadence+econ |
| 10 | M15BR-EU | EA_M15br | EURUSD M5 | 20,805 | 14.5 | 0.82 | 0.68 | 78.8 | economics |
| 11 | VOL-EU | EA_VolSpike | EURUSD M15 | 14,053 | 9.8 | 0.87 | 0.72 | 69.9 | cadence+econ |
| 12 | RSP-EU | EA_Rsp | EURUSD M5 | 21,940 | 15.2 | 0.81 | 0.69 | 78.6 | economics |
| 13 | HOD-EU | EA_Hod | EURUSD M5 | 13,806 | 9.6 | 0.83 | 0.68 | 64.0 | cadence+econ |
| 14 | H4PB-EU | EA_H4pb | EURUSD M5 | 1,251 | 0.87 | 0.93 | 0.76 | 6.6 | cadence |
| 15 | FVG-EU | EA_FVG | EURUSD M15 | 29,370 | 20.3 | 0.78 | 0.69 | 92.6 | economics |

## Mechanism coverage

Falsified classes on EURUSD M5/M15:
- Mean reversion / fade: IBS continuation, Camarilla H3/L3, liquidity sweep
- Breakout / expansion: M15 range break, H1 displacement, FVG imbalance
- Participation: tick-volume spike
- Cross-symbol: EU-GB RSI spread
- Temporal: hour-open drive, seasonal drift (XAU), session VWAP (XAU)
- Pullback: H4 EMA50 value reclaim
- Trend: AMA cross (XAU), squeeze release (XAU)

## Structural findings

1. **Every tested mechanism is gross-negative** on EURUSD M5/M15 under
   Model 0 + measured MQ-Demo costs. Best gross: H4pb 0.93 (sub-cadence),
   worst: FVG 0.78.
2. **Cost drag is ~30% of PF**: median cost PF x1.0 ≈ 0.68 vs gross ≈ 0.83.
   Even a hypothetically break-even gross signal cannot reach 1.30.
3. **Cadence vs quality anti-correlate**: the two least-bad cells (GbbSqueeze
   ~1.00, H4pb 0.93) are the two sparsest — the more selective the trigger,
   the less negative, but neither reaches the 10/wk floor.
4. **XAU cost structure is strictly worse** (spread p90 ~4.2 pips vs
   EURUSD ~0.1) — all 5 XAU cells died on costs even at 15+/wk cadence.
5. **Overnight/weekend exposure is controllable** — all session-disciplined
   EAs passed it; the failures are purely economic.

## What this does NOT falsify

- Other symbols (GBPUSD/USDJPY sleeves) — untested domain, needs new cost
  evidence; same broker economics make a reversal unlikely.
- Swing/multi-day holding (H1+, multi-day holds) — outside the frozen
  10-40/wk cadence contract; requires Owner renegotiation.
- Non-price information sources (news calendar, macro prints, DOM) — not
  in the current contract space.
- Parameter variants of killed families — out of scope by doctrine
  (no post-hoc salvage).

## Recommendation to Owner

The falsification screen has done its job: **no single-mechanism intraday
scalp sleeve clears the promotion gates at MQ-Demo economics.** Options:

1. **Change the contract space** — allow swing holding (days, not minutes)
   and renegotiate the cadence gate; larger stops make the cost drag small
   enough that an edge could survive. Highest expected value.
2. **Different broker/cost tier** — a raw-spread + commission account
   (e.g. the The5ers server) may have different economics; the screen can
   be re-run there.
3. **Different information source** — news/macro-calendar conditioned
   mechanisms (outside current contract space).
4. **Accept the falsification** — document that this fleet's hypothesis
   space contains no viable scalping edge on this broker.

Do NOT: mint more same-family variants, loosen gates, or salvage — that
would be manufacturing a pass.
