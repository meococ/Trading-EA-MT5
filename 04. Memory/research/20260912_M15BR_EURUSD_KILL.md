# M15BR EURUSD — KILL (2026-09-12)

Cell 10 of the era-2 governed screen. `HYP-M15BR-EU-M5-001` / `EA_M15br`.

## Run

- **Run ID:** `20260912_091049` (control, challenger, research-proxy cost tier)
- **Window:** 1999.01.01 → 2026.09.11, `verified_m1_asof`, coverage class
  `VERIFIED_M1_START` (actual journal depth 1998.01.02 warmup ≤ requested
  1999.01.01; server M1 real from 1999)
- **Quality:** 99%
- **Data fingerprint:** `43E5D70D...`, server fingerprint `212F73C6...` (Build 6192)
- **Model:** 0 — every tick from M1 bars

## Result

| Metric | Value | Gate | Verdict |
|---|---|---|---|
| Trades | 20,805 | — | — |
| Cadence | 14.45/wk | 10–40 | PASS |
| Profit factor | 0.815 | >1.30 | FAIL |
| Net | −$7,842.02 | — | FAIL |
| Max DD | 78.8% | ≤20% | FAIL |
| Win rate | 40.45% | — | — |
| Cost PF x1.0 | 0.681 | — | FAIL |
| Cost PF x1.5 | 0.616 | ≥1.25 | FAIL |
| Cost PF x2.0 | 0.559 | ≥1.00 | FAIL |
| Non-repaint audit | PASS | PASS | PASS |

## Analysis

Second momentum/continuation candidate after H1 displacement — same fate.
M15-bar range expansion (M5 close breaking last-completed M15 high/low with
H4 EMA50 agreement) produced plenty of trades but negative expectancy
(−0.38/trade, avg win 4.12 vs avg loss 3.45 at 40% hit rate). Breakout
entries on EURUSD intraday systematically buy local tops / sell local
bottoms — the fade candidates that profit from the opposite side also lost
to costs, meaning neither side of the M5/M15 microstructure has harvestable
edge at this cost tier.

## Verdict: KILL

All provenance, data-quality, and non-repaint gates passed; economics and
drawdown failed decisively. No rescue attempted (frozen contract). Registry
row appended (`killed`, run_ids=[20260912_091049]).

## Board state (era-2 screen)

9 governed candidates killed, 0 passes:
- XAUUSD: CRSI-R2, AMA, VwapFade, HourDrift, GbbSqueeze — all cost-dead
- EURUSD: Ibsc (MR 0.68), CamarillaFade (MR 0.70), HtfDisplacement (mom 0.76),
  LiquiditySweep (microstructure, 0.12/wk), M15br (breakout 0.68)

## Implication for next cell

Six distinct mechanism families now killed on EURUSD M5/M15. Remaining
untested classes in fleet: session-open drive (London/NY open momentum),
ORFade (opening-range fade — but fades all died), volatility-regime filters.
If next candidate also dies, the honest conclusion approaches "no M5-scalp
edge exists on EURUSD at MQ-Demo cost structure" — document rather than
manufacture.
