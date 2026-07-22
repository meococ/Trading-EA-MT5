# HYP-ECRS-EURUSD-M5-001 — Stage-0 Readout (TERMINAL: PARK, no outcome read)

Date: 2026-07-22 (UTC)
Lane: `EA_ECRS_CompressionReleaseScalper` — EURUSD M5, Efficiency Compression
Release Scalper (Kaufman ER regime-shift + ATR compression + tick-volume surge
+ 12-bar range breakout).
Thesis source: Owner deep-research report
`05. Playbook/Strategy/BaoCao_DeepResearch_ECRS_Efficiency_Compression_Release_Scalper_22Jul2026.docx`
(research input only).
De-dup: `04. Memory/research/20260722_ECRS_DEDUP_READOUT.md`
(`DEDUP_PASS_MATERIALLY_NEW`).

## Verdict

`PARK_STAGE0_CADENCE_INFEASIBLE_NO_OUTCOME_READ`

The report-default ECRS object on EURUSD M5 (FivePercent feed) produces
**8 eligible entries in 208.71 elapsed weeks (2019-2022) = 0.0383 trades/week**
— 26x below the pre-declared hard-KILL cadence floor (tpw >= 1.0), 52-130x
below the GOAL band (2-5/week), and 8 << 300 minimum probe sample. No frozen
probe was run; **no trade outcome, PnL, forward return, or excursion was ever
computed** (outcome-blind attestation inside the funnel JSON; scanner code
greps clean — the only forward reads are entry-bar time/open/spread).

The deep-research report's frequency claim ("2-5 quality setups/day on major
pairs") is falsified by ~3 orders of magnitude for its own recommended default
configuration on EURUSD.

## Evidence (hash-bound)

| Artifact | Path (relative to package `research/`) | SHA256 |
|---|---|---|
| Stage-0 scanner (outcome-blind) | `preflight/stage0_scan.py` | `BA15FA9E42B8015CBA148906794580137516F2F09831477335C1612CC7068228` |
| Funnel + preflight JSON | `preflight/stage0_funnel.json` | `DAF08FEF22A9574F8FC503D5A1635411E29A0522E48699A458FEE1B24915F072` |
| Candidate cases CSV (8) | `preflight/stage0_candidate_cases.csv` | `44C953D576DCD4B619E90D3C3295780E5D813D2204B3C1A7295753718028998D` |
| Rendered asof cases manifest (8 PNG, cutoff enforced) | `preflight/cases_asof/cases_manifest.json` | `3FBD4258DA667F930D5D05F5359E61F6EC0E08BCFDA24A81D283B9F858478711` |
| Input M1 parquet | `02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_M1_2015_now.parquet` | `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A` (manifest match) |
| News CSV (FF high-impact 2019-2022) | `02. AlphaFactory/data/forexfactory/EURUSD/news_events/...csv` | `80B9DE46517B42F8B1D9A3ACCEFA6CC6D3DCB4DD06CAE357F16DE46228C64307` (manifest match) |

Seal receipt: holdout 2023-01-01+ enforced at read time, `holdout_bars_loaded=0`,
last bar loaded 2022-12-30 21:59 UTC.

## Funnel (pooled 2019-2022, mainline compression variant_pre)

```
n_bars 298,483
G1  ER shift (prior<0.28, now>=0.38)          15,780
G2  + ATR compression (atr<=0.70xSMA20, t-1)   1,092
G3  + 12-bar range breakout                      462
G4  + tick-volume surge >=1.7xSMA20               75   <- biggest in-session cut
G5  + EMA20 slope bias alignment                  73
G6  + session 07:00-16:30 UTC entry                8   <- dominant constraint
G7  + news blackout +/-45min                       8
G8  + spread 0<sp<=0.8 pip                         8   (2 long / 6 short)
```

Per-year finals: 2019:4, 2020:2, 2021:1, 2022:1 (2015-2018 diagnostic,
news-ungated: 0/1/0/0). Compression variant_at (ATR at signal bar t) final = 1
— near-degenerate because the release bar itself inflates ATR(14).

## Mechanism findings (frequency-plane only, still outcome-blind)

1. **Joint rarity is intrinsic**: ER-rising-while-ATR-compressed (G1∧G2) is
   only 1,092 bars in 4 years (~0.37% of bars); the volume surge then removes
   84% of breakouts. The report's core conjunction is self-throttling.
2. **The mechanism fires off-session**: pre-session-gate survivors cluster at
   22:00-00:00 UTC (47 of 73) — rollover hours where the trailing tick-volume
   baseline is thinnest (surge trivially satisfied) and spread is widest. The
   frozen London-NY window fights the phenomenon's natural habitat; what
   remains in-session is 8 events in 4 years.
3. Even with session, news, and spread gates all removed, the ceiling is 73
   candidates / 208.71 weeks = **0.35/week** — still below the tpw>=1.0
   hard-KILL floor and below any GOAL-compatible cadence. No legal single-knob
   change reaches 2-5/week; reaching it requires a materially different object
   (e.g. removing/weakening the volume-surge gate or redefining the release
   trigger), which is a NEW hypothesis, not this one.

## Radius (what this park closes, and does not)

- CLOSES: the report-default ECRS object (ER10 0.28->0.38 + ATR14<=0.70xSMA20
  + 12-bar breakout + 1.7x tickvol surge + EMA20 bias + London-NY session) as
  a *cadence-feasible* candidate on EURUSD M5 / FivePercent feed. Terminal for
  `HYP-ECRS-EURUSD-M5-001`; the ID is never revived.
- DOES NOT CLOSE: economic edge of the entry object (never measured — no
  outcome was read); materially re-scoped ECRS variants (different gate set /
  frequency surface) under a NEW ID with fresh de-dup + prereg; other symbols
  (GBPUSD/USDJPY/XAU never tested — though the same joint-rarity logic likely
  applies); the off-session 22:00-00:00 UTC release phenomenon (untested,
  adverse cost prior at rollover).
- Forbidden as rescue framing: re-running this exact object with loosened
  thresholds purely to manufacture cadence, then citing this readout's
  frequency data as design authority without declaring it (any successor
  prereg MUST cite this readout as pre-outcome frequency input).

## Session provenance

Stage-0 scan built and executed by an Opus 4.8 sub-agent under parent
orchestration; parent independently verified: manifest SHA match, seal
receipt, gate formulas line-by-line, outcome-blindness grep (only
`shift(-1)` reads are entry time/open/spread), funnel monotonicity, and
visual inspection of rendered asof cases (breakout bars are genuine range
exits; no post-entry bars rendered).
