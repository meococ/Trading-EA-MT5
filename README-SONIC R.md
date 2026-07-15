---
title: README-SONIC R
tags:
  - sonic-r
  - mt5
  - pvsra
  - ea-research
status: living-note
updated: 2026-07-11
---

# README-SONIC R

This is the workspace Sonic R knowledge note. It is written as an
Obsidian-compatible Markdown file and should be treated as a living research map,
not a deployment claim.

## Current Truth

- `EA_SonicR` is research-only.
- The code is reconstructed parity research, not confirmed original Sonic R/PVSRA
  source parity.
- Canonical symbols are unsuffixed `XAUUSD`, `EURUSD`, and `GBPUSD`; do not mix
  MetaQuotes-Demo strategy evidence with the current FivePercentOnline cost
  preflight.
- Plus-suffix runs such as `XAUUSD+` are historical/E8 context unless explicitly
  reopened.
- Current target is still unmet. Exact audit across `217` identity-valid
  non-empty runs found zero runs with both PF strictly above `1.30` and `2-5`
  trades per elapsed calendar week. There are `218` physical run directories;
  one cross-EA timestamp collision is excluded because its manifest/config EA
  identities disagree.
- Promotion requires numeric/artifact validation, verified broker costs,
  genuine optimization-aware WFA, multiple-testing controls, execution
  reconciliation, zero overnight/weekend exposure for scalp lanes, and known
  news/risk safety. Historical `validate-full PASS` labels based on tool exit
  codes are not promotion evidence.
- Strict control and challenger evidence must use Model 0. Model 1 may only
  screen, park, or kill.
- MetaEditor CLI exit `1` is compile proof only when a newly created compile log
  reports `0 errors` and a fresh non-empty EX5 is timestamped at or after compile
  start. Exit status alone is never proof.
- Lifecycle evidence now requires `sonic_telemetry.v3`: PX6/Trades entry and
  exit rows carry `initial_risk_account` plus `deal_profit`, `deal_commission`,
  `deal_swap`, `deal_fee`, and `deal_net`. Per deal, `pnl_gross = deal_profit`
  and `pnl_net = deal_net = deal_profit + deal_commission + deal_swap +
  deal_fee`.
- OPEN evidence is written from the actual MT5 history-deal fill (deal ID,
  volume, price, time, position ID, and effective stop), with a separate row
  per netting scale-in. Missing partial/multi-deal fills fail closed.
- `build_verified_cost_artifact.py` requires v3 deal-level reconciliation and
  emits `verified_execution_cost.v1`; its focused suite passes `6/6`. Missing
  same-broker quote/commission/slippage data still blocks usable cost evidence.
  It parses raw spread rows (`timestamp/symbol/bid/ask`), commission lifecycles
  (round-turn account commission per lot), and side-referenced slippage fills,
  or a hash-bound JSON broker contract; declared sample/value/P90 summaries are
  not trusted. Every report deal ID must join to lifecycle evidence, and unified
  validation canonical-rebuilds and compares `trade_repricing` and `scenarios`.
- Current fixed-parameter WFA, realized-P/L robustness, PBO, and White Reality
  Check outputs are diagnostic-only (`promotion_eligible=false`). They cannot
  satisfy a `confirmed` gate.
- Source S/R is a research blocker: `InpUseSourceSrInteractionV1=false` does not
  isolate `source_sr_runway_pips` from Classic decision gates. No telemetry-only
  or behavior-neutral control claim is valid until a code fix or matched
  ablation proves isolation; this note does not authorize an EA logic change.
- The existing Sonic feature frontier remains closed. The only new external
  idea, `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001`, is preregistered but
  `COST-DATA BLOCKED`; no outcome probe or EA patch is authorized.
- Latest failure portfolio audit:
  `03. EA Developer/EA_SonicR/research/20260710_EA_FAILURE_PORTFOLIO_AUDIT.md`.
- Latest broker-cost audit:
  `03. EA Developer/EA_SonicR/research/20260711_BROKER_COST_PROVENANCE_AUDIT.md`.
- Current evidence-gated agent loop:
  `04. Project Control/ai/agent_ea_research_loop.md`.
- **Backup-indexed history below is unavailable in this lean checkout.**
  "Latest" means chronologically latest in the backup index, not locally
  inspectable or current evidence. Restore the exact path and verify its hash
  before using any of these claims for a decision.
- Backup-indexed latest source-parity recovery: `03. EA Developer/EA_SonicR/research/20260509_SONICR_SOURCE_PVA_PARITY_V1_READOUT.md`.
- Backup-indexed latest source S/R probe: `03. EA Developer/EA_SonicR/research/20260509_SONICR_SOURCE_SR_INTERACTION_V1_PROBE_READOUT.md`.
- Backup-indexed latest source Classic Wave/Dragon probe:
  `03. EA Developer/EA_SonicR/research/20260510_SONICR_SOURCE_CLASSIC_WAVE_DRAGON_V1_PROBE_READOUT.md`.
- Backup-indexed latest Trader-State Reader V1 smoke:
  `03. EA Developer/EA_SonicR/research/20260510_SONICR_TRADER_STATE_READER_V1_SMOKE_READOUT.md`.
- Backup-indexed latest Trader-State label loop:
  `03. EA Developer/EA_SonicR/research/20260510_SONICR_TRADER_STATE_LABEL_LOOP_READOUT.md`.
- Backup-indexed latest Trader-State Directional V1 readout:
  `03. EA Developer/EA_SonicR/research/20260510_SONICR_TRADER_STATE_DIRECTIONAL_V1_READOUT.md`.
- Backup-indexed latest Scanner-Candidate Alignment V1 readout:
  `03. EA Developer/EA_SonicR/research/20260510_SONICR_ERROR_ANATOMY_AND_ALIGNMENT_V1_READOUT.md`.
- Backup-indexed latest Candidate-aligned locked-label separation V2:
  `03. EA Developer/EA_SonicR/research/20260510_candidate_aligned_locked_label_separation_v2.md`.
- Backup-indexed latest source-trader research note:
  `03. EA Developer/EA_SonicR/research/20260510_SONICR_SOURCE_TRADER_RESEARCH_NOTE.md`.
- Backup-indexed latest engineering hardening:
  `03. EA Developer/EA_SonicR/research/20260511_SONICR_ENGINEERING_SAFETY_V1_READOUT.md`.
- Backup-indexed latest EUR London Classic probe:
  `03. EA Developer/EA_SonicR/research/20260511_SONICR_EUR_LONDON_CLASSIC_V1_READOUT.md`.
- Backup-indexed latest EUR M15 ClassicTrend true probe:
  `03. EA Developer/EA_SonicR/research/20260511_SONICR_EUR_M15_CLASSICTREND_TRUE_V1_READOUT.md`.
- Backup-indexed latest EUR density recovery batch:
  `03. EA Developer/EA_SonicR/research/20260512_SONICR_EUR_DENSITY_RECOVERY_BATCH_V1_READOUT.md`.
- Backup-indexed blind manual label packet:
  `03. EA Developer/EA_SonicR/research/label_packets/20260510_trader_state_manual_label_packet_v1.csv`.
- Backup-indexed candidate-like label packet:
  `03. EA Developer/EA_SonicR/research/label_packets/20260510_candidate_aligned_label_packet_v2.csv`.
- Backup-indexed candidate-aligned locked labels:
  `03. EA Developer/EA_SonicR/research/label_packets/20260510_candidate_aligned_codex_locked_labels_v2.csv`.
- Backup-indexed EUR source-core label packet:
  `03. EA Developer/EA_SonicR/research/label_packets/20260512_eur_source_core_casebook_packet_v1.csv`.
- Backup-indexed latest consolidated review:
  `03. EA Developer/EA_SonicR/research/20260509_SONICR_RESULTS_AND_WORKFLOW_REVIEW.md`.

## Claim Provenance Tags

Use these tags when adding new claims:

- `public-source`: directly supported by Sonic R/PVSRA public material.
- `reconstructed`: our deterministic mapping of public Sonic R ideas into EA
  fields.
- `local-empirical`: observed in AlphaFactory artifacts/backtests.
- `hypothesis`: plausible idea not yet validated.

Do not mix these in one sentence without making the boundary explicit.

## What Sonic R Is

Sonic R started as an M15 swing/trend method built around:

- price action waves,
- the Dragon,
- the Trend line,
- support/resistance levels,
- volume and later PVSRA context,
- disciplined trade/risk management.

The public Sonic R thread describes the system as a 15-minute method that moved
away from indicator stacking and toward price, volume, and support/resistance
analysis. The important coding lesson is that Sonic R is not simply "EMA cross
equals trade". The trader is reading whether a wave is clean, whether Dragon has
angle, whether the breakout has room to run, and whether PVSRA supports or warns
against the setup.

## Core Components

### Dragon

The Dragon is the dynamic EMA34 band. Public references describe it as EMA 34 on
close, with high/low outer edges used as the Dragon band.

EA mapping:

- EMA34 high,
- EMA34 close,
- EMA34 low,
- slope/angle in ATR terms,
- distance and extension from the band.

### Trend

The Trend line is EMA89 close. It is context, not a complete strategy.

EA mapping:

- EMA89 close,
- slope/angle in ATR terms,
- price side relative to Trend,
- HTF agreement or conflict.

### Classic

Classic is the core Sonic R setup:

- a decently smooth and spaced price-action wave,
- wave crosses or interacts with the Dragon,
- Dragon has good angle in the direction of the crossing,
- breakout/momentum appears on the third leg,
- S/R and session context provide runway.

The EA must not reduce this to "price above Dragon". It needs state quality:
wave clarity, pullback quality, non-chase, Dragon expansion, S/R runway, and
session phase.

### Scout

Scout is historically not a Classic entry. It is a discretionary/high-risk
position taken around extreme highs/lows or stopping volume when PVSRA suggests
position-building or a later Classic may form.

EA rule: Scout-like logic must stay disabled/scanner-only unless independently
proven. Do not let PVSRA alone open a trade.

### Re-entry / Continuation

Re-entry belongs after a valid Classic narrative or strong directional context.
It is not a separate source of truth. For EA work, continuation needs separate
attribution so it is not just a correlated scale-in counted as independent edge.

### PVSRA

PVSRA means Price, Volume, Support and Resistance Analysis. Public Sonic R
guidance says PVSRA is a method of analysis, not an entry method.

EA mapping:

- PVSRA bias,
- PVSRA event,
- PVSRA grade,
- whole/half/quarter level proximity,
- high-volume behavior around S/R,
- sweep/reclaim context.

EA rule: PVSRA may raise/lower quality, veto fragile setups, or label cases. It
must not create standalone trades unless a separate, pre-registered thesis
survives validation.

## Trader Mental Model To Quantify

The gap between a trader and current code is state reading.

Key visual questions:

- Is the PA wave clean, smooth, and spaced, or overlapping/choppy?
- Is Dragon angled and expanding, or flat/compressed?
- Is price just breaking from build to run, or chasing late after the move?
- Is there enough runway before whole/half/quarter levels or prior swing S/R?
- Is volume supporting the third-leg breakout, or warning of trap/build?
- Is the setup in London/NY phase with enough time to run?
- Is XAU in impulse, transition, or sideway-wide behavior?
- Is EUR in real range expansion or just low-volatility noise?

Discipline rules from public Sonic/PVSRA notes should stay explicit in the EA:
quality over frequency, avoid Asian-session overtrading for Classic, do not add
to losing positions, and do not enter while the read is still position-building
instead of run-for-profits.

Quant features to prefer:

- wave smoothness and overlap ratio,
- impulse/pullback ratio,
- Dragon slope persistence,
- Dragon band compression-to-expansion,
- extension from Dragon in ATR,
- S/R runway in pips and ATR,
- sweep/reclaim side and failure behavior,
- PVSRA event/grade near key levels,
- session phase and remaining session runway,
- multi-horizon trend/range/volatility tags.

## Chart-State Vocabulary

Every state-based hypothesis must lock labels before an EA rule patch:

| Field | Allowed labels |
|---|---|
| Wave state | `clean`, `choppy`, `overlap`, `unclear` |
| Dragon state | `flat`, `compressed`, `expanding`, `angled` |
| Trend/HTF state | `aligned`, `soft_conflict`, `hard_conflict`, `unknown` |
| S/R runway | `clear`, `blocked`, `near_whole_half_quarter`, `unknown` |
| Chase risk | `early`, `mature`, `late_chase`, `unknown` |
| MM mode read | `position_building`, `run_for_profits`, `trap_risk`, `unknown` |
| Session phase | `asia`, `london_open`, `london_mid`, `ny_overlap`, `late_ny`, `off_session` |
| Invalidation | explicit price/state condition |

Required negative controls:

- `SIDEWAY_WIDE` losses,
- impulse wins,
- high-MFE missed trades,
- high-MAE false positives,
- adjacent sessions and nearby hours.

No EA rule patch from visual intuition:

```text
chart claim -> locked labels -> offline separation -> matched control -> default-off patch
```

## Variants And EA Status

| Variant | Meaning | EA status | Allowed next action |
|---|---|---|---|
| Classic | Core wave + Dragon angle setup | Active research core | Improve state labels, not blind thresholds |
| Re-entry | Continuation after Classic narrative | Auxiliary, symbol/session-specific | Only after Classic narrative survives |
| Scout | PVSRA/extreme-area discretionary entry | Parked / scanner-only | Requires new prereg and separate validation |
| PVSRA standalone | Volume/S&R as trigger | Not allowed without separate proof | Do not trade |
| Source S/R WHQ V1 | Whole/half/quarter S/R context | Research blocker: the false switch does not isolate `source_sr_runway_pips` from Classic decisions | No evidence/promotion use until a code fix or matched ablation; this note does not authorize logic changes |
| Source Classic Wave/Dragon V1 | Classic wave + Dragon state context | Telemetry-only; decision patch parked | Keep `source_classic_*` as audit context |
| Trader-State Reader V1 | Story-state labels for build/run/trap using Classic + PVSRA + S/R context | Telemetry/label infrastructure only | Use `sonic_*` for locked labels before any qualifier |
| Trader-State Directional V1 | Prevents `direction=NONE` scanner context from masquerading as executable `run_for_profits` | Correctness patch parked; no decision effect | Use source-case examples to rebuild direction semantics |
| Manual Trader-State Label Packet V1 | Blind 89-case pre-entry packet for build/run/trap labeling | Prepared; Codex labels filled but signal join is too sparse | Use as casebook input, not a decision patch |
| Scanner-Candidate Alignment V1 | Offline check whether clean Sonic scanner narrative becomes executable directional candidates | Parked; `262` scanner candidates, `0` directional alignments within 6 bars, locked-label separation failed | Return to source-case examples / MT5 chart casebook for true direction semantics |
| Candidate-like Label Packet V2 | Blind 120-case packet from joined candidate-like rows across EURUSD/GBPUSD/XAUUSD | Filled/frozen by Codex field policy; joined `120/120`; separation failed | Keep as falsification evidence, not a decision patch |
| Opportunity score gate | Existing score-based option gate | Failed XAUUSD M15 option screen | Do not advance; it did not separate trap/run |
| XAU S1 sweep reclaim | XAU M5 sweep/reclaim scalp lane | Cadence driver but fragile | Audit trap/run classifier first |
| XAU R1 range absorption | Sideway/range rotation attempt | Failed current probes | Park unless new state thesis appears |
| XAU long-bias core | Quality sleeve for long-only XAU contexts | Cleaner but too sparse | Feature donor only |
| EUR Sonic Classic/router | EUR M5/H1 Sonic adaptation | Parked until EUR-specific thesis | Build independent London Classic thesis |
| EUR London Classic V1 M15 option | Existing-route M15 Option B screen from 2026-05-11 plan | Killed as configured; `20260511_222011` had `0` trades and all `direction=NONE` | Superseded by direct M15 ClassicTrend true screen |
| EUR M15 ClassicTrend true V1 | Direct legacy ClassicTrend with `InpUseRegimeRouter=0` and `InpUseClassicTrend=1` | Killed as too sparse; `20260511_230302` fired 2 trades over two years | Do not rerun same config; use label/casebook-first blocker anatomy or new M5 EUR_T1 prereg |
| EUR Density Recovery Batch V1 | Three locked screens: actual M5 T1 route, M15 no-PVSRA, and M15 source-core Classic | Killed; best population was source-core with 14 trades, PF 1.2786, still below target | Use source-core only as casebook donor; do not patch `sonic_*` labels because trap/late-chase was net positive in this sample |
| Compression/retest | Breakout from compression then retest | Rejected from current fields | Killed for current fields |

## Backtest Evidence Summary

This is an evidence snapshot, not core doctrine. Do not use a best-seed row as a
reason to mine local filters. The long-window falsification has priority when it
conflicts with a favorable 2024-2025 pocket.

### Baseline And Seeds

| Run | Window | Model | Trades | PF | Net | Decision |
|---|---|---:|---:|---:|---:|---|
| `20260501_000718` | XAUUSD M5 2024-2025 | 0 | 282 | ~1.3202 | ~$296.67 | Research baseline only; `validate-full REVIEW 0/5` |
| `20260501_151422` | XAUUSD M5 2024-2025 | 0 | 237 | 1.3136 | $240.17 | Attribution dataset; weaker than baseline |
| `20260502_220922` | XAUUSD M5 2024-2025 | 0 | 181 | 1.7758 | $496.37 | Best economics seed, still below cadence and `REVIEW 0/5` |
| `20260502_232935` | XAUUSD M5 2019-2025 | 1 | 492 | 0.9520 | -$127.11 | Long-window falsification |
| `20260503_145322` | XAUUSD M5 2019-2025 | 1 | 492 | 0.9520 | -$127.11 | GoldRegime joined; no patch authorized |
| `20260503_185518` | XAUUSD M5 2024-2025 | 1 | 41 | 2.6969 | $217.09 | Quality sleeve only, too sparse |
| `20260503_185600` | XAUUSD M5 2024-2025 | 1 | 181 | 1.8025 | $503.95 | Matched control beat long-bias on net/cadence |
| `20260511_222011` | EURUSD M15 2024-2025 | 1 | 0 | n/a | $0.00 | Killed as mis-scoped M15 Option B; existing `EUR_T1_CLASSIC` route is M5-only and legacy M15 ClassicTrend was disabled |
| `20260511_230302` | EURUSD M15 2024-2025 | 1 | 2 | 1.5938 | $29.64 | Direct M15 ClassicTrend route works but is killed as too sparse; no Model 0 or validation |
| `20260512_215529` | EURUSD M5 2024-2025 | 1 | 4 | 0.5054 | -$14.66 | Actual M5 T1 route; killed as sparse and losing |
| `20260512_221742` | EURUSD M15 2024-2025 | 1 | 2 | 1.5938 | $29.64 | M15 Classic no-PVSRA; killed because PVSRA ablation did not recover density |
| `20260512_222608` | EURUSD M15 2024-2025 | 1 | 14 | 1.2786 | $69.36 | M15 source-core Classic; killed but useful as casebook donor |

### Lessons From The Runs

- The 2024-2025 XAU seed has signal, but not enough robustness.
- Long-window 2019-2025 testing falsified the current stack as a robust edge.
- `SIDEWAY_WIDE` is the major loss pocket; generic range logic did not fix it.
- S1 is the cadence driver but loses badly in wide sideway/trap conditions.
- Profit is concentrated in favorable 2024-2025 gold regimes.
- Price-only multi-day trend proxies did not recreate robust edge.
- Compression breakout and post-impulse retest probes failed.
- XAU long-bias gating improves quality but destroys cadence and loses to
  matched control on net.
- EUR should not be forced into XAU thresholds; it needs a separate market model.
- EUR source-core Classic increases candidate count, but current trader-state
  labels are not decision-safe: in `20260512_222608`, `trap_risk/late_chase`
  held 12 of 14 fired trades and was net positive. Relabel from chart story
  before adding any Sonic state qualifier.

## What Has Not Worked

- Loosening Classic to increase trade count.
- Treating PVSRA or S/R sweep as a standalone entry.
- Generic sideway/range absorption.
- Generic compression-to-impulse breakout.
- Generic breakout-retest after impulse.
- Mined hour/day vetoes without pre-registration and split/cost survival.
- PF-only promotion.
- Relying on 2024-2025 without longer-history falsification.

## Anti-Overfit Checklist

- One hypothesis equals one feature family and one state separation.
- Define maximum tunable thresholds before the run.
- Define holdout windows before the run.
- Do not inspect holdout windows for feature design.
- Post-hoc hour/day/year/session buckets become new `idea` rows, not rules.
- Model 1 can kill or park; it cannot promote.
- Every run must be matched to a control.
- Count failed variants when interpreting PBO/Reality Check.
- Any candidate that depends on one year/month/hour/session is parked or killed.

## Current Bottlenecks

1. The code still detects patterns better than it reads trader state.
2. Current score is pattern-completeness, not trade-quality.
3. Sideway-wide trap versus impulse continuation is not separable yet by simple
   fields.
4. Cost and broker geometry can erase thin M5 XAU edge.
5. Backtest cadence target is not met without adding fragile/noisy trades.
6. Same-broker quote/commission/slippage provenance is incomplete, so the v3
   lifecycle builder cannot yet produce promotion-grade verified cost evidence.
7. Current WFA/robustness/PBO/White Reality Check producers are diagnostic-only;
   `confirmed` remains blocked without promotion-eligible evidence.
8. Source S/R is not behaviorally isolated by its default-off switch, so its
   historical telemetry/control claims are blocked pending a code fix or matched
   ablation.
9. Historical `validate-full REVIEW 0/5` is backup-indexed context, not a current
   validator output.
10. Some MT5-native screenshot batches still need reliability hardening.

## Team Consensus 2026-05-03

Three review roles agreed on the same direction:

- Trader view: the next edge is not "more entries"; it is separating S1
  post-sweep continuation from `SIDEWAY_WIDE` reclaim traps.
- Quant view: current XAU 2024-2025 seeds are research evidence only. Every
  candidate must be tracked in a registry and taxed for data mining; Model 1 can
  reject but cannot promote.
- Engineering view: the workflow is promising but not deploy-ready while source
  contamination, MT5 cache state, broker geometry, telemetry volume, and
  Model-1-overread risk remain active.

Current strategic decision:

- Keep XAU as a feature donor and research baseline.
- Build an audit-first XAU S1 trap/run classifier.
- Build EUR London Classic as an independent cadence sleeve.
- Aim for `>120 trades/year` at portfolio level, not by forcing one XAU lane to
  overtrade.

## Results Review 2026-05-09

The evidence and workflow were reviewed and summarized into:

`03. EA Developer/EA_SonicR/research/20260509_SONICR_RESULTS_AND_WORKFLOW_REVIEW.md`

Current summary:

- The branch is valuable as research infrastructure, not as a deployable EA.
- The best local XAU economics seed remains `20260502_220922`, but it is still
  below cadence target and `validate-full REVIEW 0/5`.
- The long-window XAU test (`20260502_232935` / `20260503_145322`) is the higher
  priority evidence: 2019-2025 PF `0.9520`, net `-$127.11`, so the current stack
  is not a robust long-history edge.
- `SIDEWAY_WIDE` and S1 trap/build behavior remain the main state problem.
- The next useful work is an audit-first XAU S1 trap/run classifier, followed by
  a separate EUR London Classic sleeve.

## Source Parity Recovery 2026-05-09

The source-parity lane recovered canonical public Sonic R `.mq4/.tpl` material
into quarantine:

`03. EA Developer/EA_SonicR/source_quarantine/forexfactory/20260509_232500/`

Current source-authenticated implementation:

- `InpUseSourcePvaParityV1=false` was added as a default-off PVA parity switch.
- Source PVA uses the 2014 SonicR PVA Candles/Volumes logic: previous-10-bar
  average volume, `150%` rising volume, and climax at `200%` volume or highest
  `spread * volume` versus the previous 10 bars.
- `PVSRA_SR_Fields` now exports `source_pva_event` and `source_pva_grade`.
- `InpUseSourceSrInteractionV1=false` was added as an intended default-off S/R
  WHQ telemetry switch, but current code still calculates `source_sr_*`
  unconditionally and uses `source_sr_runway_pips` in Classic decision gates.
  The switch is therefore not a behavior-neutral control.
- Source S/R uses the quarantined Control Panel 00/25/50/75 level grid and logs
  `source_sr_level_kind`, `source_sr_interaction`,
  `source_sr_rejection_side`, `source_sr_runway_pips`, and
  `source_sr_grade`.
- Source Classic Wave/Dragon V1 logs `source_classic_wave_state`,
  `source_classic_wave_smoothness`, `source_classic_dragon_state`,
  `source_classic_dragon_expansion`, `source_classic_trigger_state`,
  `source_classic_chase_risk`, `source_classic_session_runway`, and
  `source_classic_run_mode_proxy`.
- Trader-State Reader V1 logs `sonic_story_state`, `sonic_mm_mode_proxy`,
  `sonic_wave_quality`, `sonic_dragon_momentum`, `sonic_level_story`,
  `sonic_session_momentum`, `sonic_entry_timing_risk`,
  `sonic_trade_management_context`, and 20/60-bar replay metrics.
- No Scout/Reentry/lifecycle/XAU S1 classifier logic was revived.

First-screen result:

- Matched Model 1 M15 screens completed on `EURUSD`, `GBPUSD`, and `XAUUSD`.
- `InpUseSourcePvaParityV1=1` is parked as a decision-path override because it
  reduced cadence on all three symbols and did not create a viable edge.
- Keep the `source_pva_*` fields as source-authenticated audit context.
- Source S/R WHQ V1 probe completed on `EURUSD`, `GBPUSD`, and `XAUUSD` M15
  with zero sidecar join mismatches and all `source_sr_*` headers present.
- S/R V1 is parked as a decision/qualifier patch: `near_whq` was a weak pocket
  in the probe, but `clear_runway` and `body_cross` were too sparse to promote,
  and the proxy did not prove `position_building` versus `run_for_profits`.
- Historical `source_sr_*` rows remain descriptive context only. Do not treat
  them as isolated telemetry or promotion evidence until a code fix or matched
  ablation proves the switch contract.
- Source Classic Wave/Dragon V1 probe completed on `EURUSD`, `GBPUSD`, and
  `XAUUSD` M15 with zero sidecar join mismatches and all `source_classic_*`
  headers present.
- Classic V1 is parked as a decision/qualifier patch: current fired trades were
  mostly `trap_risk` and `clean_classic_run` had zero fired trades. An XAU-only
  trap veto would be local mining, not source-parity proof.
- Keep the `source_classic_*` fields as audit context and casebook-label input.
- Trader-State Reader V1 smoke completed on short EURUSD, GBPUSD, and XAUUSD
  M15 windows with zero sidecar join mismatches and all `sonic_*` headers
  present. This is not a strategy result because no trades fired; it only proves
  the label infrastructure is wired.
- Trader-State Directional V1 fixed a telemetry semantics bug: broad scanner
  rows with `direction=NONE` no longer create false `run_for_profits` context.
  After the fix, full M15 2024-2025 runs produced zero directional
  `run_for_profits` candidates, so the patch is not a qualifier.
- Scanner-Candidate Alignment V1 then tested the gap between scanner narrative
  and executable candidates. It found `262` candidate-like scanner rows across
  EURUSD, GBPUSD, and XAUUSD M15, but `0` aligned to a directional candidate
  within the fixed 6-bar window. The dominant current blocker is
  `LONG_CONTEXT_FAIL`, not a missing PVA/SR/Classic filter. This keeps the EA in
  research-only mode.
- Candidate-like Label Packet V2 was then filled/frozen with a Codex pre-entry
  field policy and joined back `120/120` cases from raw Directional V1 sidecars.
  It still failed separation: `run_for_profits` had only `9` cases with positive
  proxy rate `0.5556`, while `position_building` had `20` cases with positive
  proxy rate `0.6000`. This parks the candidate-alignment hypothesis and blocks
  any context-direction or entry patch from this evidence.

Next source-parity work comes before more local XAU mining:

- locked chart labels/casebooks using `source_classic_*` before any future
  Classic or S/R qualifier patch;
- locked chart labels/casebooks using `sonic_*` to separate
  `position_building`, `run_for_profits`, and `trap_risk`;
- source-case examples and MT5-native chart casebook review for true London
  Classic direction semantics after the Candidate-like Label Packet V2
  separation failure;
- only a survivor may move to a strict Model 0 matched control/challenger,
  `validate-full`, v3 verified-cost reconciliation, candidate compare, and
  casebook review.

## Debug Checklist

When a result looks unexpectedly good:

- Confirm source path: must be `03. EA Developer/EA_SonicR`, not archive.
- Confirm symbol: current lane uses `XAUUSD`/`EURUSD`, not `XAUUSD+` unless
  explicitly reopened.
- Confirm model: Model 1 is fast screen only; strict control and challenger must
  both run Model 0.
- Confirm compile proof: MetaEditor exit `1` is acceptable only with a newly
  created `0 errors` log and a fresh non-empty EX5 timestamped at or after
  compile start.
- Confirm run id, report path, input hash, variant tag, and copied sidecars.
- Confirm `Signals`/`Trades` headers did not change unexpectedly.
- Confirm `sonic_telemetry.v3`, finite positive `initial_risk_account`, entry/exit
  deal fields, and deal-level reconciliation to corrected
  `pnl_gross`/`pnl_net` semantics when lifecycle telemetry is enabled.
- Confirm no bar-zero decision logic was introduced.
- Confirm cost stress and slippage/geometry status.
- Compare against matched control; do not read a candidate alone.

When there are too few trades:

- Do not loosen filters blindly.
- Separate whether the lane is too strict, the symbol thesis is wrong, broker
  geometry rejects trades, or news/session/spread blockers dominate.
- Check whether the target should be portfolio-level instead of one lane.

When sideway hurts:

- Do not assume range rotation is profitable.
- Label sideway-wide losses against impulse wins.
- Look for trap/build versus run-for-profits state, not just range width.

When screenshots disagree with CSV:

- Treat MT5-native screenshots as stronger visual evidence than SVG sketches.
- Check chart time, symbol, timeframe, entry marker, Dragon/Trend overlay,
  candle alignment, and run-local SHA manifest.

## Development Flow

Use this sequence for future Sonic R work:

1. Research and source mapping.
2. Hypothesis registration using
   `03. EA Developer/EA_SonicR/research/PREREG_TEMPLATE.md`.
3. Offline scanner/probe from closed-bar sidecars.
4. Matched Model 1 fast screen only; it may kill or park but cannot promote.
5. Cost stress and baseline comparator.
6. Trade anatomy by lane/direction/session/hour/month/year/phase.
7. MT5-native screenshot casebook for top wins, top losses, high-MFE misses,
   high-MAE false positives, and weak months.
8. One feature patch only if the evidence identifies affected bars before code.
9. Strict Model 0 matched control/challenger confirmation.
10. Build report-bound `verified_execution_cost.v1` from reconciled
    `sonic_telemetry.v3` lifecycles and verified same-broker cost provenance.
11. Run `validate-full` at challenger stage. Treat current WFA/robustness/PBO/
    White Reality Check outputs as diagnostic-only; `confirmed` requires later
    promotion-eligible evidence from a frozen, aligned variant family.
12. Update `hot.md`, `current_state.md`, source registry, and the relevant
    prereg/readout.
13. Archive Common Files telemetry and stale artifacts.
14. Close with `03. EA Developer/EA_SonicR/research/READOUT_TEMPLATE.md` and a
    candidate registry transition.

## Candidate Registry Location

Canonical files:

- `03. EA Developer/EA_SonicR/research/CANDIDATE_REGISTRY.jsonl`
- `03. EA Developer/EA_SonicR/research/CANDIDATE_REGISTRY.schema.json`
- `03. EA Developer/EA_SonicR/research/PREREG_TEMPLATE.md`
- `03. EA Developer/EA_SonicR/research/READOUT_TEMPLATE.md`
- `04. Project Control/ai/sonic_validation_gates.md`

Rule: no meaningful backtest can be used for a decision unless it attaches to a
`hypothesis_id` in the registry.

## Candidate Registry Flow

Each experiment should move through explicit states:

```text
idea -> probe -> screened -> challenger -> confirmed -> portfolio-sleeve
```

Terminal states:

```text
parked
killed
```

Minimum fields to record:

- hypothesis id,
- parent candidate,
- lane and setup type,
- source/provenance,
- symbol/timeframe/window/model,
- exact overrides and variant tag,
- matched control run id,
- PF/net/DD/trade count/year,
- cost PF at base/x1.5/x2,
- positive months/half-years/years,
- WFA/robustness/PBO/Reality Check/Monte Carlo status, including each artifact's
  `analysis_kind` and `promotion_eligible` value,
- execution issues and sidecar completeness,
- casebook/snapshot status,
- verdict and reason.

## Session Close Checklist

- Registry row appended or state transitioned.
- Prereg and readout linked.
- Source identity recorded: source path/hash, compiled artifact timestamp/hash,
  copied tester path, input hash.
- Run-local manifest exists or readout records equivalent fields.
- Telemetry schema is `sonic_telemetry.v3`; `initial_risk_account`, entry/exit
  deal components, gross/net semantics, and reconciliation status are recorded.
- Report-bound `verified_execution_cost.v1` path/hash and same-broker provenance
  are recorded, or the run is explicitly cost-blocked.
- `validate-full`, cost stress, phase/regime attribution, and non-repaint audit
  recorded when applicable.
- Sidecar rows/header/schema checked when telemetry is on.
- Common Files telemetry archived or confirmed clean.
- `hot.md`, `current_state.md`, and `source_of_truth.*` updated if the result is
  authoritative.
- Final verdict is explicit: continue, park, kill, confirm, or portfolio-candidate.

## Next Hypotheses

### H0: Source-Case Direction Semantics

Purpose: explain why current clean scanner narratives become `LONG_CONTEXT_FAIL`
instead of executable Sonic R Classic direction candidates.

Evidence required before EA patch:

- public-source or quarantine-supported Classic examples for wave/Dragon break
  timing and London context,
- MT5-native chart casebook for candidate-like rows from the parked alignment
  probe,
- labels locked before outcome review,
- no XAU-only hour/day/filter mining.

Pass idea: the casebook must show a pre-entry, cross-symbol direction rule that
separates true run-for-profits from position-building/trap before any default-off
qualifier is proposed.

### H1: XAU S1 Trap/Run Classifier

Purpose: separate S1 reclaim that starts an impulse from S1 reclaim that traps in
wide sideway behavior.

Evidence required before EA patch:

- MT5-native snapshots for S1 impulse wins and sideway-wide losses,
- closed-bar StateTelemetry and GoldRegime fields,
- pre-entry features only: Dragon expansion, overlap, SR runway, flow alignment,
  session phase, wick/body, and distance to box mid.

Pass idea:

- long-window cost PF above `1.25`,
- at least `9/14` positive half-years,
- at least `4/7` positive years,
- no sole dependency on 2024-2025.

### H2: EUR London Classic Independent Lane

Purpose: build EUR as its own market model, not a copy of XAU.

Core idea:

- London-first,
- M5 execution with M15/H1 context,
- Asian range as context/retest candidate,
- clean Dragon angle,
- non-chase and S/R runway,
- no PVSRA standalone trigger.

Expected role: add independent portfolio cadence if it survives validation.

### H3: Portfolio Router

Purpose: reach target through independent sleeves.

Only combine lanes after:

- each sleeve survives its own validation,
- overlap/correlation is measured,
- cost stress remains acceptable,
- no overnight/weekend exposure appears,
- no lane depends on one mined hour/day/year.

## MT5 Backtest Notes

- MetaTrader 5 Strategy Tester supports multiple model modes.
- `Every tick` is the most accurate generated mode but slower.
- `Every tick based on real ticks` uses broker real ticks when available.
- `1 minute OHLC` uses only M1 OHLC ticks and is useful for fast screening.
- `Open prices only` runs only at bar open and can distort SL/TP/BE economics;
  do not use it to promote Sonic scalping candidates.
- MQL5 `CopyRates` start position `0` is the current unfinished bar; Sonic
  decisions must use closed bars.
- Strict control and challenger runs use Model 0; Model 1 is screen-only.
- MetaEditor exit `1` counts only with a fresh `0 errors` compile log and a fresh
  non-empty EX5 timestamped at or after compile start.
- Lifecycle telemetry used for evidence must be `sonic_telemetry.v3` and must
  reconcile entry/exit deal components to corrected gross/net totals before the
  verified-cost builder can emit `verified_execution_cost.v1`.
- After any signal/data-access change, run a non-repaint audit for bar-zero
  prices/buffers and hidden current-bar indicator reads.
- Serious readouts must record source path/hash, compiled artifact timestamp/hash,
  copied tester path, run id, input hash, telemetry tier, and final report path.
- Telemetry tiers: `off`, `trade-only`, `state-lite`, `state-full`,
  `snapshot-casebook`. Long-window screens should avoid full telemetry unless
  bounded case sampling is required.

## Obsidian Usage

This file is plain Markdown and can be opened in Obsidian as part of this
workspace folder. Do not create a nested vault inside the workspace; open the
workspace root as the vault if Obsidian is used. Use standard Markdown links for
external sources and keep this note as the main Sonic R map.

Useful note links:

- `04. Project Control/ai/hot.md`
- `04. Project Control/ai/current_state.md`
- `04. Project Control/ai/sonic_tool_runbook.md`
- `03. EA Developer/EA_SonicR/research/SONIC_PARITY_SPEC.md`
- `03. EA Developer/EA_SonicR/research/20260503_SONICR_LONG_WINDOW_PHASE_ATTRIBUTION_011_READOUT.md`
- `03. EA Developer/EA_SonicR/research/20260503_SONICR_COMPRESSION_RETEST_AND_LONG_BIAS_015_READOUT.md`

## External Sources Checked

### Sonic / PVSRA

- [ForexFactory Sonic R thread](https://www.forexfactory.com/thread/114792-sonic-r-system)
- [TAH Classic explanation, post 8127640](https://www.forexfactory.com/thread/post/8127640)
- [ForexFactory Classic and Scout explanation](https://www.forexfactory.com/thread/114792-sonic-r-system?page=2664)
- [ForexFactory run-for-profits / position-building PVSRA discussion](https://www.forexfactory.com/thread/114792-sonic-r-system?page=3368)
- [SonicR999 Sonic R / PVSRA notes](https://sonicr999.blogspot.com/2014/08/sonic-r-system.html)
- [TradingView Dragon and Trend reference](https://www.tradingview.com/script/DWh6PLdY-Dragon-and-Trend/)

### MT5 / MQL5

- [MetaTrader 5 Strategy Testing](https://www.metatrader5.com/en/terminal/help/algotrading/testing)
- [MetaTrader 5 tick generation modes](https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation)
- [MQL5 CopyRates reference](https://www.mql5.com/en/docs/series/copyrates)

### Obsidian / Note Workflow

- [Obsidian data storage](https://obsidian.md/help/data-storage)
- [Obsidian internal links](https://obsidian.md/help/links)
- [Obsidian formatting syntax](https://obsidian.md/help/syntax)
