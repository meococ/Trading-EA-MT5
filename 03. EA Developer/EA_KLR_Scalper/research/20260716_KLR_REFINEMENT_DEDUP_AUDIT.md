# KLR Refinement and Re-test De-dup Audit

Status: **FRONTIER_REACHED_NO_LEGAL_REFINEMENT** on 2026-07-16.

This audit responds to the Owner request to refine and test KLR again. It is
not a new hypothesis, preregistration, Strategy Tester run, or permission to
modify the killed `HYP-KLR-USD-PDLRAID-M5-XAU-001` decision surface.

## Inputs inspected

- Original four-page report:
  `05. Playbook/Strategy/KLR_Scalper_Deep_Research_Report_v1.pdf`, SHA-256
  `29D60B7A75C68C34F0C675383DFD31EC8705DC29C1DF12C9A2CBE0624FFD972F`.
  All four pages were rendered and visually inspected; page 3 contains the
  fallback list.
- Quant engineering report:
  `05. Playbook/Strategy/KLR_Scalper_Deep_Research_Report.md`, SHA-256
  `DD1D252BE0588012A652623059A622590EC4AD068961A425A3366AE48344C57E`.
- Frozen KLR prereg, probe, readout and evidence artifact.
- `04. Memory/do_not_repeat_failures.md`, the active candidate registry and
  `02. AlphaFactory/STRATEGY_LOG.md`.

The PDF exposes four explicit fallback routes: pure NY, majors-only, add
order flow, or research mean reversion. It does not contain a hidden numeric
rule set beyond the already reviewed parameter ranges.

## De-dup result

| Proposed refinement | Existing falsification | Decision |
|---|---|---|
| Tune session, RR, stop, FVG fill or ATR threshold | KLR HYP-001 and PO3 HYP-001/002/003 froze these families before outcome; KLR core produced only 2 trades and the USD challenger 0 | Forbidden post-hoc rescue; no run |
| Pure NY | PO3 NY HYP-003: sweep control N=37, PF 0.674, -5.42R; full challenger N=0. XAU London-to-NY session drift S622: N=720, PF 0.95 | Duplicate killed session/sweep family |
| Majors-only | PDH/PDL sweep S161 on GBPUSD: N=53, PF 0.77. London-to-NY S587 GBPUSD PF 1.11 and S588 EURUSD PF 0.99 | Cross-symbol transfer already failed; changing symbol is not a new mechanism |
| Order Block instead of FVG | XAU zone/OB-style retest S282: N=1306, PF 0.91, DD 90.9%. XAU sweep plus displacement S283/S284 remained 15 trades and degraded from PF 1.10 to 0.48 when relaxed | Duplicate killed zone-retest and sweep-displacement families |
| Round-number confluence | XAU GoldRound S558 rejection PF 0.94; breakout PF 1.20 with unacceptable DD. A filter cannot increase KLR sweep-control cadence above 0.639/week | Cannot repair cadence and has no standalone edge |
| Broker-bar/tick proxy order flow | XAU proxy CVD S617 PF 0.93 on N=882; M1 flow proxy S624 PF 0.94 on N=2070 | CFD proxy flow is already falsified; true exchange order flow is not locally available |
| Mean reversion fallback | XAU COMEX reversion S620 PF 0.87, displacement-to-VWAP fade S561 PF 0.64 and zone reversion S282 PF 0.91 | Broad XAU intraday mean-reversion surface already failed |

## Frozen probe implementation audit

No implementation defect was found that would justify correcting and rerunning
the killed hypothesis:

- M15 pivots become visible only after the two required confirmation bars;
  the M5 merge uses completed-bar timestamps.
- Session mapping uses `America/New_York`, including DST.
- Previous-day levels are completed ET-day levels; entries occur at the next
  M5 open.
- The FRED USD observation uses a two-U.S.-business-day lag.
- Same-bar ambiguity is conservative: stop is evaluated before target.
- One trade per ET day and session-end/day-end flattening are enforced.
- The terminal/data-path contract is D-only and `FILE_COMMON` is forbidden.

The main differences versus the PDF are deliberate frozen choices, not bugs,
and are generally *less* selective: `1.0 * ATR` displacement versus the
report's `>1.5 * ATR`, and any directional FVG overlap versus a preferred 50%
fill. Tightening them to the report would only reduce the already terminal
sample. Expanding the NY window from the preregistered 08:30 ET to the PDF's
07:00 ET after reading the result would be session mining, while the
independently frozen PO3 NY branch has already failed.

## Decision

No `.mq5`, compile, Model 0 run, parameter sensitivity, or 2025+ holdout access
is authorized. Repeating the same probe would be a reproducibility duplicate,
not new strategy evidence.

A fresh KLR-adjacent hypothesis becomes legal only with a materially different
point-in-time information set, such as auditable CME COMEX signed trades/order
book data plus a frozen cost and storage contract. The Owner must separately
authorize any paid-data ceiling. Otherwise the valid next action is a new
independent strategy thesis, not another KLR parameter variant.
