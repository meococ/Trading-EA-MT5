# V8 US−JP 10Y Yield Differential → USDJPY Probe Contract V1 — 2026-07-13

Status: `JOIN_CONTRACT_FROZEN / OFFLINE_PROBE_ONLY / NO_EA_BUILD`

## Authority

Owner self-research (GPT waived; no Real login). Uses newly frozen US−JP
bond-yield panel (MoF JGB historical + US Treasury 10Y). One cheap offline
probe. No registry/prereg/EA/Model 0 unless survivor.

De-dup: `readouts/20260713_USJP_10Y_VS_USEU_USUK_DEDUP_CLEARANCE.md`.

## Probe identity

- Working ID: `HYP-SR-FX-USJP-10Y-DIFF-USDJPY-001` (mint only if registered)
- Probe tag: `V8_USJP_10Y_DIFF_USDJPY_V1`

## Data

- Frozen panel: `preflight/v8_exogenous/panels/us_jp_bond_yield_diff_d1_v1.csv`
- Field: `diff_us_jp_10y` = US Treasury 10Y − MoF JGB 10Y
- Lag: `available_at_utc` = observation_date + 1 calendar day 00:00Z
- Fail closed if gap > 3 calendar days
- FX: MetaQuotes-Demo USDJPY D1 falsification only

## Signal (frozen a priori — mirror USEU/USUK constants)

1. `z_t` of lagged diff over lookback 60 (≥40 obs).
2. `z >= +0.75` → long USDJPY (USD premium → JPY weak); `z <= −0.75` → short USDJPY; else flat.
3. D1 Mon–Thu entry; Friday flatten; stop 1.5×ATR14; time-stop 5 bars.
4. Stress A/B 1.5/3.0 pip RT. Train 2019–2022; holdout gated.
5. Control: same |z| gate; direction = sign(20d USDJPY return).

Note on sign: for USDJPY, higher US−JP yield premium favors long USDJPY
(USD strength), opposite of the EURUSD/GBPUSD short-when-premium convention
used on those quotes. Frozen a priori; do not flip from readout.

## Kills

trades&lt;80; tpw&lt;0.5; PF-A&lt;1.05; fail beat control PF-A and expectancy-A;
year concentration of positive net-A &gt; 0.55.

## Non-rescues

No z/tenor/session mining. No garnish onto killed USEU/USUK/OIS books.
