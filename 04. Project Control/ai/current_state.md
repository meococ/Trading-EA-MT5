# Current State

- Updated: 2026-07-11
- Active lanes: **EA_SonicR research-only** plus Owner-approved
  **fx_portfolio_silverbullet Phase 0 only**
- Canonical sources: `03. EA Developer/EA_SonicR/EA_SonicR.mq5` and pinned
  `03. EA Developer/EA_SilverBullet/EA_SilverBullet_v2.mq5` for the new lane
- Canonical test symbols for Sonic R: unsuffixed `XAUUSD`, `EURUSD`, `GBPUSD`.
  Historical Sonic evidence is mainly MetaQuotes-Demo; current cost preflight
  is FivePercentOnline and is a separate broker-data lane.

## Active Truth

- Sonic R remains the only active strategy-development lane. The separate
  `fx_portfolio_silverbullet` lane is open only for governance, exact source and
  runner contracts, and metadata-only artifact sufficiency; it does not yet
  authorize strategy development or execution.
- Active source contracts are fail-closed. SilverBullet resolves only to
  `EA_SilverBullet_v2.mq5`; `_v2_Index.mq5`, backups, and archives cannot be
  selected as fallbacks.
- Retired/legacy EA source and runtime EA caches are archived under `00. Old File/EA_Archive/`.
- Root guidance is consolidated into `AGENTS.md`.
- `README-SONIC R.md` is the active Obsidian-compatible Sonic R knowledge map.
- Stale Claude/doc/root guidance was archived under `00. Old File/agent_guidance_archive/20260503_1916_sonic_readme_cleanup/`.
- `02. AlphaFactory/` remains the compile/backtest/analyze platform.

## 2026-07-11 Goal Review

- The exact elapsed-calendar audit covers `217` identity-valid non-empty runs
  across `34` EAs. There are `218` physical directories; one cross-EA
  run-id/config collision is excluded. No valid run currently meets both PF
  strictly above `1.30` and `2-5` trades/week.
- Historical validation was materially fail-open: missing cost proof, false
  exit-code PASS states, fixed-parameter pseudo-WFA, duplicate runs, stale run
  binding, weak manifests, and mostly rejected equity curves.
- AlphaFactory runner and validator now implement a fail-closed,
  task-packet workflow with strict control bootstrap, matched challengers,
  exact physical artifacts, producer-attributed freshness, and numeric gates.
  A passing child process is not a strategy verdict.
- Strict control/challenger execution requires Model 0. MetaEditor exit `1` is
  accepted only when a fresh compile log proves `0 errors` and a fresh
  non-empty EX5 is newer than compile start.
- Lifecycle telemetry is now `sonic_telemetry.v3`; PX6/Trades rows carry
  `initial_risk_account` computed with `OrderCalcProfit` plus `deal_profit`,
  `deal_commission`, `deal_swap`, `deal_fee`, and `deal_net` for entry and exit
  lifecycles. Per deal, `pnl_gross = deal_profit` and `pnl_net = deal_net =
  deal_profit + deal_commission + deal_swap + deal_fee`. The report-bound
  `build_verified_cost_artifact.py` producer requires v3, performs deal-level
  reconciliation, and its focused tests pass `6/6`, but no verified cost
  artifact can be produced from the currently incomplete same-broker data.
- The verified-cost path reads raw `timestamp/symbol/bid/ask` spread rows,
  commission lifecycles for P90 round-turn account commission per lot, and
  side/reference/fill/pip slippage rows, or a hash-bound JSON broker contract.
  Self-declared sample/value/P90 summaries are rejected. Every report deal ID
  must join to v3 lifecycle evidence, and unified validation canonical-rebuilds
  and compares `trade_repricing` and `scenarios`.
- Fixed-parameter WFA, realized-P/L robustness, and the current PBO/White
  Reality Check producers are diagnostic-only. Their outputs set
  `promotion_eligible=false`, so `confirmed` remains blocked.
- The doctrine-canonical registry was restored, preserved append-only, and now
  has `54` rows at its compatibility path. It is the workspace FX research
  ledger. `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001`,
  `HYP-SB-WEEKEND-FLAT-001`, and `HYP-PORTFOLIO-COMPOSE-001` are schema-valid
  state `idea`; the latter two remain draft/not-frozen with empty run IDs and
  null outcome metrics.
- The idea is a synchronous common-USD regime plus strongest-aligned-pair
  pullback-break. S555 lead-lag, S618 fixed-target consensus, and S670 laggard
  divergence are locked negative controls; failure to beat any one kills it.
- Current disposition is `IDEA / COST-DATA BLOCKED`. Historical M15 spread is
  mostly missing, commission has only two EURUSD lifecycle samples, and usable
  side-referenced slippage samples are zero for all three symbols. Historical
  quote ticks needed for executable ask barriers are also unavailable.
- No controlled offline outcome analysis, EA strategy patch, compile, MT5
  backtest, demo, prop, or live action is authorized from this state. The
  approved Phase 0 work is limited to governance, source/runner contract tests,
  and artifact-sufficiency metadata checks; the accidental display event below
  is contamination, not authorized evidence.
- All 2026-05/06 Sonic claims below are backup-indexed narrative whose registered
  artifacts are absent from this lean checkout. They are not current evidence;
  any exact run/count claim must be restored at its registered path and
  hash-verified before use.

## 2026-07-11 FX Portfolio / SilverBullet Phase 0

- `20260711_CODEX_EXECUTION_PLAN_V2.md` supersedes V1. Owner approval opens
  Phase 0 only; Phase 1+ remains blocked.
- Shared runner contract pins SilverBullet to `EA_SilverBullet_v2.mq5`, keeps
  the Index variant out of fallback selection, permits non-Sonic telemetry only
  at tier `off`, and binds both execution receipts and post-run manifests to the
  exact resolved main source. Runner contract tests pass `338/338` without
  MetaEditor or Strategy Tester execution.
- `HYP-SB-WEEKEND-FLAT-001` covers weekend-flat A1 only. The V1 combined
  max-hold rule is split out as a future A2 child and is not registered/frozen.
- `HYP-PORTFOLIO-COMPOSE-001` may use only an exact preregistered universe and
  non-outcome eligibility. PF-ranked/per-EA-best selection is forbidden.
- The Phase 0 sufficiency report is the only legal preflight for these drafts.
  A blocked report is not a strategy verdict; `READY_FOR_PREREG_FREEZE` would
  still require a separate freeze/authorization before any outcome probe.
- The checked-in deterministic report currently returns `BLOCKED` for both
  probes: the portfolio candidate universe is empty/not frozen, and the
  SilverBullet donor is missing seven required hash bindings for price-path,
  side-aware bid/ask, timezone, session, symbol, and cost provenance.
- The controlled producer reports
  `producer_semantic_outcome_accessed=false`. Separately, one sub-agent
  accidentally displayed a donor `RunMeta` file containing summary
  fields before the access contract was finalized. No displayed value was used
  in a threshold, registry metric, decision, or report. This contamination is
  recorded and forces `BLOCKED_REQUIRES_CLEAN_FUTURE_FREEZE_REVIEW`.
- Current hard blockers are hash-bound donor-aligned bid/ask price paths,
  server-time/DST/session-close and next-executable-quote semantics, symbol and
  account-currency conversion contracts, verified USDJPY cost provenance, and
  a frozen portfolio universe with explicit family/risk-weight bindings.

## Sonic R Status

- `EA_SonicR` is research-only.
- Backup-indexed history describes the implementation as research-only and says
  public Sonic R `.mq4/.tpl` source was recovered into quarantine on 2026-05-09;
  the quarantine artifact is not locally available here.
- Backup-indexed source telemetry patches include `source_pva_*`, `source_sr_*`,
  `source_classic_*`, and `sonic_*` trader-state fields.
- M15 Model 1 source-PVA screen is complete: the decision override is parked, but telemetry/context fields remain useful.
- M15 source-S/R WHQ history says `source_sr_*` headers/joins passed and the
  qualifier was parked. Current code nevertheless calculates Source S/R
  unconditionally and uses `source_sr_runway_pips` in Classic decision gates;
  `InpUseSourceSrInteractionV1=false` is therefore not a behavior-neutral
  telemetry-only control. Source S/R evidence is blocked pending a code fix or
  matched ablation. This document does not authorize the logic change.
- M15 source-Classic Wave/Dragon probe is complete: `source_classic_*` telemetry passed header/join checks, but the probe is parked as a decision/qualifier patch.
- Trader-State Reader V1 smoke is complete: `sonic_*` telemetry and replay fields passed header/join checks on short EURUSD/GBPUSD/XAUUSD M15 smoke runs; it is label infrastructure only, not a strategy edge.
- Trader-State label loop is complete for EURUSD/GBPUSD/XAUUSD M15 2024-2025.
  Follow-up Directional V1 fixed the false `run_for_profits` population on
  `direction=NONE` rows, but then found zero directional `run_for_profits`
  candidates. The loop is research evidence, not a decision patch.
- Scanner-Candidate Alignment V1 is complete as an offline probe over
  Directional V1 runs `20260510_093925`, `20260510_094543`, and
  `20260510_095129`. It found `262` candidate-like scanner rows but `0`
  rows aligned to a directional candidate within 6 bars. It produced a
  120-case blind label packet V2 and a source-trader research note.
  Candidate-aligned locked-label separation V2 then joined `120/120` cases,
  but `run_for_profits` had only `9` cases and did not outperform
  `position_building` (`0.5556` vs `0.6000` positive proxy rate). Verdict:
  park; do not patch entry or context-direction semantics.
- Engineering Safety V1 is complete as execution hardening only. It added a
  fail-closed margin precheck, minimal live-position state rebuild on `OnInit()`,
  validation-safe retry default `InpRetryCount=0`, and derived warmup bars.
  Compile passed and smoke runs `20260511_221429`, `20260511_221505`, and
  `20260511_221531` produced clean telemetry headers with no margin/order reject
  hits. It is not strategy evidence.
- EUR London Classic V1 Option B M15 run `20260511_222011` is killed as
  configured: `49,558` signals, `0` trades, and all `direction=NONE`. Code scope
  review shows the existing `EUR_T1_CLASSIC` route requires `PERIOD_M5`, while
  the prereg override disabled legacy M15 `InpUseClassicTrend`, so the run did
  not exercise an executable EUR route.
- EUR M15 ClassicTrend true V1 run `20260511_230302` corrected that scope by
  using `InpUseRegimeRouter=0` and `InpUseClassicTrend=1`. It fired 2 London
  `ClassicTrend` trades, PF `1.59375`, net `$29.64`, max DD `0.4953%`, but is
  killed by prereg because `2` trades over two years is not usable evidence.
- EUR Density Recovery Batch V1 is complete and killed. Runs:
  `20260512_215529` M5 T1 route, 4 trades, PF `0.5054`, net `-$14.66`;
  `20260512_221742` M15 Classic no-PVSRA, 2 trades, PF `1.5938`, net `$29.64`;
  `20260512_222608` M15 Classic source-core, 14 trades, PF `1.2786`, net
  `$69.36`. Source-core is a casebook donor only. It improved density but still
  failed cadence/PF gates, and its fired sample shows current `sonic_*`
  semantics are unsafe for decisions because `trap_risk/late_chase` rows were
  net positive.
- Follow-up label infrastructure for `20260512_222608` is prepared: lightweight
  casebook HTML, casebook index, and blind source-core packet V1 with `60` rows
  (`14` fired, `46` blocked), SHA256
  `5f5dc452645946c60757f503703f6ca53d3d3567a5b0a6d27e5ea5ae2e5fe4e4`, and
  no exported outcome/PnL/MFE/MAE fields.
- PVSRA is context/qualification only, not a standalone trigger.
- **EURUSD Sleeve 2 Restoration (2026-06-05):** Patched static variables to runtime variables (`g_...`) across include files (`SNR_Context.mqh`, `SNR_Signals.mqh`, `SNR_Opportunity.mqh`, `SNR_GoldRegime.mqh`, `SNR_Telemetry.mqh`) to eliminate multi-sleeve configuration leakages. Configured Sleeve 2 to use SMC Structure and Liquidity Sweep. Backup-indexed Q1-2021 Model 1 runs recorded 6 trades (Win Rate 83.3%, PF 2.31) in both Auto-Sleeve and static-control modes. That is observed output parity for one historical window, not proof of complete logic equivalence; the attributed MetaQuotes-Demo data drift is not current evidence until its artifacts are restored and hash-verified.
- **XAU S1 M15 ATR Impulse Filter V1 (2026-06-08):** Killed as a decision filter. Gemini proposed a closed-M15 ATR(14) >= 1.20 * EMA100 gate for executed XAU S1 sweep/reclaim. After correcting the control-plane deposit mismatch (`alpha.ps1` default 10000 vs 20260603 baseline 100000), matched Model 0 D100K control `20260608_002730` produced 326 trades, PF 1.2976, net $1079.76, DD 0.3996%; challenger `20260608_010650` produced 32 trades, PF 1.5460, net $139.65, DD 0.1677%. Higher PF came from deleting most S1 trades, not from reaching the target. No validate-full, WFA, MC, or promotion is authorized.
- **XAU S1 M5 Dragon Anchor Compression V1 (2026-06-08):** Killed as a decision filter. Gemini proposed blocking executed XAU S1 when `abs(Dragon EMA34 close - Trend EMA89 close) / ATR(M5) > 2.20`. Same-source Model 0 D100K control `20260608_024033` produced 326 trades, PF 1.2976, net $1079.76, DD 0.3996%; challenger `20260608_020110` produced 317 trades, PF 1.0307, net $110.25, DD 0.6880%. The filter kept cadence but removed high-value impulse winners: S1 net collapsed from $1043.21 to $47.75. No validate-full, WFA, MC, or promotion is authorized.
- **XAU S1 Micro-Structure Casebook V1 (2026-06-08):** Killed as an offline probe. Gemini proposed body ratio, prior-5 micro clearance, and prior-10 Dragon congestion proxy over control `20260608_024033`. Analyzer joined 321/321 final S1 trades, but impulse winners and loss/flat trades did not separate: approximate Mann-Whitney p-values were 0.5596, 0.6263, 0.7834, and 0.6837. Best exploratory rule kept 179 trades, PF 1.1836, net $371.56, and only 48.93% of impulse-winner net. No EA patch is authorized.
- **XAU S1 H1 Structural Sweep V1 (2026-06-08):** Killed as an offline probe. Gemini proposed H1 structural sweep context rebuilt from closed M5 PVSRA/SR sidecars over control `20260608_024033`. Analyzer joined 321/321 final S1 trades and rebuilt 29,526 H1 bars from 353,023 unique closed M5 bars. `h1_sweep_depth_atr` separated impulse winners from loss/flat trades (`p` approx 0.0128), but no boundary met the locked gates: the cadence-safe best rule kept 287 trades, PF 1.3563, net $1166.32, and all impulse-winner net, but removed only 10.45% of loss/flat trades; the more selective rule kept 224 trades, PF 1.6134, net $1535.32, 95.43% impulse-winner net, and removed only 31.34% of loss/flat trades. Treat as casebook context only. No EA patch is authorized.
- **EUR London Asian Manipulation V1 (2026-06-08):** Killed as an offline probe. After Gemini's first EUR Classic suggestion was rejected as a duplicate of killed EUR Classic/Density runs, the corrected hypothesis rebuilt EURUSD M15 UTC bars from donor `20260601_090150` M5 sidecar and tested Asian-range stop hunt plus London Dragon reclaim candidates. Analyzer rebuilt 372,331 unique M5 bars into 124,214 M15 bars and generated 573 candidates (2.21/week), so cadence exists. Expectancy failed: synthetic PF 1.1014, 0.20-pip cost PF 1.0781, and year concentration failed with max positive-year share 45.7% from 2025. `ema89_aligned=False` showed post-hoc cost PF 1.3098 on 182 candidates, but it is not preregistered and cannot authorize a patch.
- **EUR London Counter Extension V1 (2026-06-08):** Killed as an offline holdout probe. This preregistered the post-hoc EUR counter-EMA high-sweep anomaly from V1 with fixed `H4_Extension_Z > 1.50` and 2024-2025 holdout. Base counter pool was only 88 candidates over five years (0.35/week); holdout base had only 31 candidates; H4-extension holdout had only 14 candidates. H4-extension holdout cost PF was 1.8113, but sample, separation (`p` approx 0.8698), and concentration failed (2025 share 62.46%). High PF on 14 trades is not evidence. No EA patch is authorized.
- **GBP London Value Drift V1 (2026-06-08):** Killed as an offline probe. Gemini pivoted to untouched GBPUSD donor `20260531_144616` with a London M15 Dragon breakout / EMA89 value-drift thesis. Analyzer rebuilt 372,370 unique M5 bars into 124,218 M15 bars and found 258 candidates. It failed train and holdout gates: train cost PF 0.6554, mean anchor distance 7.74 pips below the 12-pip gate, holdout 106 candidates below the 110 gate, holdout cost PF 0.8166, PVSRA drive separation `p` approx 0.7572, and 2024 cost R -9.6079. EMA89 target runway is too narrow relative to Dragon-edge stop and 1.5-pip friction. No EA patch is authorized.
- **Sonic R Frontier Teardown Audit (2026-06-08):** Registry-by-hypothesis audit found no latest `confirmed` or `portfolio-sleeve` strategy. Append-only cleanup closed stale non-terminal rows: old EUR London sleeve is now `killed`; S1 sideway classifier is `parked` until a new evidence class exists; Engineering Safety V1 is `parked` as non-strategy infrastructure; and a follow-up registry verification parked old Source S/R, Source Classic Wave/Dragon, and Trader-State Reader telemetry probes so they are not mistaken for active strategy backlog. Gemini Flash Extended also recommended `PARK / TEARDOWN`, but local registry/readouts remain authority. This does not complete the user target; it prevents another overfit rescue loop on killed route families.
- **XAU S1 Locked Casebook Packet V1 (2026-06-08):** New evidence-class probe created from existing XAU S1 artifacts, not a strategy patch. Builder `03. EA Developer/EA_SonicR/research/analyzers/build_xau_s1_locked_casebook_packet_v1.py` produced blind packet `03. EA Developer/EA_SonicR/research/label_packets/20260608_xau_s1_locked_casebook_packet_v1.csv`, private key `03. EA Developer/EA_SonicR/research/data/20260608_xau_s1_locked_casebook_packet_v1_key.json`, and readout `03. EA Developer/EA_SonicR/research/readouts/20260608_XAU_S1_LOCKED_CASEBOOK_PACKET_V1.md`. Blind CSV has 60 cases and hides outcome/PnL/R/exit fields. Hidden balance is 12 impulse winners, 24 loss/flat, and 24 small winners; the donor has only 12 impulse winners, so it cannot meet the ideal 25/25 balance. Gemini Flash Extended labels are now frozen in four 15-case batches and merged into one 60-row CSV. No EA patch/backtest is authorized.
- **XAU S1 Locked Label Separator V1 (2026-06-08):** Analyzer `03. EA Developer/EA_SonicR/research/analyzers/analyze_xau_s1_locked_casebook_labels_v1.py` is prepared for the post-label gate. It validates returned labels, blocks missing/duplicate/invalid labels or outcome-like free text, joins to the private key, and reports hidden-outcome separation. Smoke against the unlabeled blind CSV produced 420 validation errors and failed closed as expected. Chrome fallback was checked: Chrome is installed/running, Codex Chrome Extension is installed/enabled, and native host is correct, but the extension backend remains unavailable; opening a Chrome window for retry requires explicit user approval. Labels are still not frozen and no EA patch/backtest is authorized.
- **XAU S1 Gemini Batch Merge Gate (2026-06-08):** Merge tool `03. EA Developer/EA_SonicR/research/analyzers/merge_xau_s1_gemini_label_batches_v1.py` and batch README are prepared. Gemini CSV answers must be saved under `03. EA Developer/EA_SonicR/research/label_packets/gemini_batches/xau_s1_lb_v1/outputs/` as `batch_01_001_015_labels.csv` through `batch_04_046_060_labels.csv`. The merge tool reads only `batch_*_labels.csv`, verifies all 60 expected case IDs against the blind packet, and writes a frozen label CSV only when complete. Smoke with no real batch outputs failed closed and did not create a frozen label file.
- **XAU S1 Proxy Label Baseline V1 (2026-06-08):** Deterministic proxy labels were generated from visible blind-packet fields only and separated against the private key as a benchmark, not as Gemini/human labels. Artifacts: `03. EA Developer/EA_SonicR/research/analyzers/build_xau_s1_proxy_labels_v1.py`, `03. EA Developer/EA_SonicR/research/label_packets/20260608_xau_s1_proxy_labels_v1.csv`, `03. EA Developer/EA_SonicR/research/data/20260608_xau_s1_proxy_label_separation_v1.json`, and `03. EA Developer/EA_SonicR/research/readouts/20260608_XAU_S1_PROXY_LABEL_SEPARATION_V1.md`. `label_sr_runway=near_whole_half_quarter` was the strongest negative clue (39 cases, impulse rate 0.102564, Fisher p 0.016872), while `label_sr_runway=clear` was directionally better (15 cases, impulse rate 0.4, Fisher p 0.056041). `label_mm_mode=run` had only 1 case. This is analysis-only and does not authorize an EA patch/backtest.
- **XAU S1 Gemini Locked Label Separation V1 (2026-06-08):** Four Gemini Flash Extended batches were saved under `03. EA Developer/EA_SonicR/research/label_packets/gemini_batches/xau_s1_lb_v1/outputs/` and merged into `03. EA Developer/EA_SonicR/research/label_packets/20260608_xau_s1_gemini_locked_labels_v1.csv` (SHA256 `6755FAA5DC5D60320F0C7127EBCF075CA2B3B56218A25F0CA08155A16F6BEF42`). Private-key analyzer passed with 0 errors and wrote `03. EA Developer/EA_SonicR/research/readouts/20260608_XAU_S1_GEMINI_LOCKED_LABEL_SEPARATION_V1.md` plus separation JSON SHA256 `E5138F34B87926A9DEDD40A86FFC4E248491B9E23D6E921D893EF25272056D48`. Result mirrors proxy: `label_sr_runway=near_whole_half_quarter` has 39 cases, impulse rate 0.102564, Fisher p 0.016872; `clear` has 15 cases, impulse rate 0.4, p 0.056041; `label_mm_mode=run` has only 1 case. This authorizes only a full-321 offline S/R runway audit, not an EA patch/backtest.
- **XAU S1 S/R Runway Full Donor V1 (2026-06-08):** Killed offline. Analyzer `03. EA Developer/EA_SonicR/research/analyzers/analyze_xau_s1_sr_runway_full_donor_v1.py` applied the label-supported S/R runway clue to all 321 joined XAU S1 trades from donor `20260608_024033` and wrote `03. EA Developer/EA_SonicR/research/readouts/20260608_XAU_S1_SR_RUNWAY_FULL_DONOR_V1.md`. Baseline was 321 trades, 1.2346 trades/week, net 1043.21, PF 1.288648. `RUNWAY` alone looked high-PF (98 trades, PF 2.27276, net 1045.0) but kept only 0.3858 trades/week and 53.5% of impulse-winner net. `keep_not_NEAR` improved PF to 1.736432 but cut to 124 trades and reduced net to 964.91. `keep_RUNWAY_REJECTION` net was only +18.8 versus all S1 with 117 trades. No EA patch/backtest is authorized; the locked-label probe is parked as evidence.
- **XAU S1 HTF Velocity Coordination V1 (2026-06-08):** Killed offline after Gemini proposed a signed H1 EMA34 slope coordination thesis. Prereg `03. EA Developer/EA_SonicR/research/preregs/20260608_H_XAU_S1_HTF_VELOCITY_COORD_V1_PREREG.md` froze four rule screens over the same 321-trade donor. Analyzer `03. EA Developer/EA_SonicR/research/analyzers/analyze_xau_s1_htf_velocity_coord_v1.py` wrote `03. EA Developer/EA_SonicR/research/readouts/20260608_XAU_S1_HTF_VELOCITY_COORD_V1.md`. No rule passed gates: `keep_positive_velocity` kept 118 trades, PF 1.191458, net 267.76; `keep_positive_velocity_young` kept 85 trades, PF 1.170725; `keep_transition_positive_velocity` kept 69 trades, PF 1.152346; `avoid_old_negative_velocity` kept 257 trades but PF only 1.234162 and net 705.24. No EA patch/backtest is authorized.
- **FX Context Anatomy Gemini Intake V1 (2026-06-08):** Killed at intake before prereg/donor. Gemini proposed `HYP-SR-FX-CONTEXT-ANATOMY-001`: EURUSD/GBPUSD London Classic `CONTEXT_FAIL` rows as mean-reversion candidates outside Asian range with flat/compressed HTF Dragon. Local de-dup readout `03. EA Developer/EA_SonicR/research/readouts/20260608_FX_CONTEXT_ANATOMY_GEMINI_INTAKE_DEDUP_V1.md` rejects it as duplicate of killed London/Asian range reversal, `CONTEXT_FAIL` near-miss, and Dragon/Trend-state locked-label families. No donor run, EA patch, or backtest is authorized.
- **Gemini Post-De-Dup Frontier Reply V1 (2026-06-08):** After the intake kill above, Gemini was asked for another thesis while excluding all currently killed/banned route families. It returned `FRONTIER_REACHED_NO_LEGAL_ACTION_REMAINS`. Local readout `03. EA Developer/EA_SonicR/research/readouts/20260608_GEMINI_POST_DEDUP_FRONTIER_REPLY_V1.md` records this as reviewer input only. It matches the verified registry shape: no latest active strategy candidate and no confirmed/portfolio sleeve. No prereg, donor run, EA patch, backtest, or validate-full is authorized from this reply.
- **Management MFE Invariant Gemini Intake V1 (2026-06-08):** Killed at intake before prereg/replay. Gemini proposed `HYP-SR-MGMT-MFE-INVARIANT-001`: replay the existing XAUUSD M5 donor `20260608_024033` with MFE >= 1.0R move-to-+0.2R and fixed +1.5R TP. Local readout `03. EA Developer/EA_SonicR/research/readouts/20260608_MGMT_MFE_INVARIANT_GEMINI_INTAKE_DEDUP_V1.md` rejects it as duplicate Source Trade Management / XAU Trap Management territory, not a pre-entry Sonic R predicate. No analyzer, replay script, EA patch, or backtest is authorized.
- **Gemini Post-Management Frontier Recheck V1 (2026-06-08):** After banning management/SL/TP/BE/MFE replay as well, Gemini was asked for exactly one remaining legal pre-entry predicate, one independent locked chart-state dataset plan, or a frontier-reached reply. It returned `FRONTIER_REACHED_NO_LEGAL_ACTION_REMAINS`. Local readout `03. EA Developer/EA_SonicR/research/readouts/20260608_GEMINI_POST_MANAGEMENT_FRONTIER_RECHECK_V1.md` records this as reviewer input only. Registry parse remains `51` rows, `23` hypotheses, `0` active, latest states killed=15/parked=8. This is a repeated direct-goal blocker; no prereg, donor, EA patch, backtest, or `validate-full` is authorized without new source/data input, independent locked labels, or explicit pivot approval.
- No demo, prop, or live promotion is allowed from the current artifact set.
- PF alone is never enough; `validate-full`, execution safety, tester fidelity,
  artifact traceability, WFA/robustness/Monte Carlo, and cost stress are required.

## Key Results So Far

- `20260501_000718`: XAUUSD M5 2024-2025 Model 0 research baseline, 282 trades,
  PF about `1.32`; `validate-full REVIEW 0/5`.
- `20260501_151422`: attribution dataset, 237 trades, PF `1.3136`, net
  `$240.17`; weaker than baseline and cost-fragile.
- `20260502_220922`: best local economics seed, 181 trades, PF `1.7758`, net
  `$496.37`, DD `0.8203%`, cost x2 PF `1.4321`; still `REVIEW 0/5` and below
  cadence target.
- `20260502_232935` / `20260503_145322`: XAUUSD M5 2019-2025 long-window Model 1,
  492 trades, PF `0.9520`, net `-$127.11`, DD `6.2248%`; falsifies current
  stack as robust long-history edge.
- `20260503_185518`: XAU long-bias quality gate, 41 trades, PF `2.6969`, net
  `$217.09`; too sparse and loses to matched control on net/cadence.
- `20260503_185600`: matched long-bias control, 181 trades, PF `1.8025`, net
  `$503.95`; confirms quality sleeve is not the target solution.
- `20260608_010650`: XAU S1 M15 ATR impulse filter V1, 32 trades over five years,
  PF `1.5460`, net `$139.65`; killed because cadence collapsed from matched
  control `20260608_002730` with 326 trades.
- `20260608_020110`: XAU S1 M5 Dragon anchor compression V1, 317 trades over
  five years, PF `1.0307`, net `$110.25`; killed because matched same-source
  control `20260608_024033` had 326 trades, PF `1.2976`, net `$1079.76`.
- `OFF_SR_XAU_S1_MICRO_STRUCTURAL_CASEBOOK_V1`: offline probe on
  `20260608_024033`, joined `321/321` S1 trades and killed body-ratio /
  micro-clearance / Dragon-congestion proxy because best rule preserved only
  `48.93%` of impulse-winner net.
- `OFF_SR_XAU_S1_H1_STRUCTURAL_SWEEP_V1`: offline probe on `20260608_024033`,
  joined `321/321` S1 trades and rebuilt H1 context from closed M5 sidecars.
  H1 sweep depth showed partial separation (`p` approx `0.0128`), but the
  best cadence-safe rule removed only `10.45%` of loss/flat trades and the
  more selective rule fell below sample/removal gates. Killed; no patch.
- `OFF_SR_EUR_LND_ASIAN_MANIP_V1`: offline probe on donor `20260601_090150`,
  rebuilt `372331` unique EURUSD M5 bars into `124214` M15 UTC bars and found
  `573` Asian-range sweep/reclaim candidates. Cadence passed, but PF `1.1014`,
  cost PF `1.0781`, and year concentration failed. Killed; post-hoc
  counter-EMA89 subgroup is idea-only.
- `OFF_SR_EUR_LND_COUNTER_EXT_V1`: offline holdout probe on the same donor,
  testing high-sweep counter-EMA shorts with fixed `H4_Extension_Z > 1.50`.
  Base pool was `88` candidates, holdout base `31`, and holdout H4-extension
  subset `14`. Despite cost PF `1.8113` on that tiny subset, separation and
  concentration failed. Killed; no patch.
- `OFF_SR_GBP_LND_VALUE_DRIFT_V1`: offline probe on donor `20260531_144616`,
  rebuilt `372370` GBPUSD M5 bars into `124218` M15 bars and found `258`
  London Dragon value-drift candidates. Train cost PF `0.6554`, holdout cost
  PF `0.8166`, and mean anchor distance was too small. Killed; no patch.

## Main Lessons

- The EA reads setup shape better than trader state.
- `SIDEWAY_WIDE` is the main long-window loss pocket.
- S1 sweep/reclaim is a cadence source but fragile; in sideway-wide it often
  behaves like a trap/build setup rather than run-for-profits.
- Generic range rotation, compression breakout, micro breakout, and post-impulse
  retest did not show stable edge from current fields.
- XAU overextension alone is not a veto; it only matters with weak runway,
  session/chop context, or bad structure.
- H1 sweep depth is a useful casebook clue for XAU S1, but not a standalone
  executable filter from the current probe.
- EUR Asian-range manipulation V1 has cadence, but the all-candidate reversal
  vector is not strong enough after costs and is year-concentrated.
- EUR counter-EMA/H4-extension is too sparse for the target cadence; H4
  extension did not explain the post-hoc anomaly.
- GBP London value drift to EMA89 is not viable as defined; the target is too
  near to pay for friction.
- EUR must be rebuilt as its own London/HTF/range thesis; do not copy XAU
  thresholds.

## Tooling And Workflow Delivered

- `AGENTS.md`: cross-agent operating doctrine.
- `README-SONIC R.md`: Sonic R knowledge map and debug guide.
- `04. Project Control/ai/sonic_validation_gates.md`: staged validation gates.
- `03. EA Developer/EA_SonicR/research/CANDIDATE_REGISTRY.jsonl`: candidate ledger.
- `CANDIDATE_REGISTRY.schema.json`, `PREREG_TEMPLATE.md`, `READOUT_TEMPLATE.md`:
  enforce hypothesis/readout discipline.
- `sonic_telemetry.v3` adds `initial_risk_account` and entry/exit
  `deal_profit`/`deal_commission`/`deal_swap`/`deal_fee`/`deal_net` to
  PX6/Trades lifecycle rows. Per deal it defines `pnl_gross = deal_profit` and
  `pnl_net = deal_net = deal_profit + deal_commission + deal_swap + deal_fee`.
  `build_verified_cost_artifact.py` requires v3 and converts reconciled,
  manifest-bound complete lifecycles plus verified cost provenance into
  `verified_execution_cost.v1`. Its focused unit suite passes `6/6`; the
  validator independently rebuilds the artifact from raw inputs before using
  its repriced trades or scenarios.
- Compile proof accepts MetaEditor exit `0` or `1` only after a fresh log proves
  `0 errors` and a fresh non-empty EX5 passes timestamp checks.
- StateTelemetry and GoldRegimeContext were added as default-off research tools.
- Analyzer/tooling now includes candidate compare, cost stress, evidence audit,
  casebook indexing, MT5 snapshot flow, market phase attribution, market regime
  atlas, S1 phase audit, compression/retest probes, trade-state anatomy, pair
  compare, source-parity quarantine retrieval, source PVA telemetry, and a
  guarded manual research loop.
- Source PVA screen readout captured six matched Model 1 M15 runs and sidecar
  checks for `source_pva_*` telemetry.
- Source S/R WHQ probe captured three Model 1 M15 runs and a source_sr analyzer:
  `near_whq` was weak, but no class had enough stable cross-symbol evidence for
  a decision patch.
- Source Classic Wave/Dragon probe captured three Model 1 M15 runs and a
  source_classic analyzer: current fired trades were mostly `trap_risk`, but
  cross-symbol separation did not justify a default-off qualifier.
- Trader-State Reader V1 added `sonic_story_state`, `sonic_mm_mode_proxy`,
  wave/Dragon/level/session/timing/management labels, and 20/60-bar replay
  metrics to PVSRA/SR sidecars. Smoke runs `20260510_002720`,
  `20260510_002751`, and `20260510_002822` passed with zero join mismatches.
- Trader-State label loop runs `20260510_005641`, `20260510_010229`, and
  `20260510_010813` passed sidecar checks with zero join mismatches. Analyzer v2
  joined `67121` opportunity forward labels. Codex locked-label V1 later filled
  `89` labels, but only `2` signal rows joined, so it is not decision-ready.
  `InpUseOpportunityScoreGate=1` XAUUSD M15 run `20260510_011506` failed with
  2 trades, PF `0.0030`, net `-$292.59`.
- Trader-State Directional V1 patched telemetry semantics only:
  non-directional rows now log `unknown/observe/no-management-edge`. Full M15
  runs `20260510_093925`, `20260510_094543`, and `20260510_095129` had
  `146312` PVSRA/SR rows, `21` directional candidate rows,
  `run_for_profits=0`, and total trade result `18` trades net `-$897.10`.
  Verdict: park; do not add a qualifier or Model 0 screen from this patch.
- Scanner-Candidate Alignment V1 added
  `03. EA Developer/EA_SonicR/research/analyze_sonic_error_alignment_v1.py`.
  It joined Signals, PVSRA/SR, StateTelemetry, and Trades with zero mismatches,
  reported scanner blockers (`LONG_CONTEXT_FAIL 219`, `WEAK_BODY 20`,
  `NO_SWING_BREAK 9`), and exported
  `03. EA Developer/EA_SonicR/research/label_packets/20260510_candidate_aligned_label_packet_v2.csv`
  with outcome/PnL/MFE/MAE hidden.
- Candidate-aligned locked-label separation V2 added
  `03. EA Developer/EA_SonicR/research/label_and_separate_candidate_aligned_v2.py`.
  The locked labels SHA256 is
  `27FBF7FBA020977D1EA84829FFFEE79EFD1B5321728BF8C63C3419593FE374A0`.
  Separation reconstructed hidden outcomes from raw run sidecars instead of the
  scanner-only alignment CSV, joined `120/120` cases, and parked the hypothesis.
- Manual label packet V1 is prepared:
  `03. EA Developer/EA_SonicR/research/label_packets/20260510_trader_state_manual_label_packet_v1.csv`.
  It has 89 blind pre-entry cases and hides outcome/PnL/MFE/MAE plus target
  proxy fields. Codex locked-label V1 was filled, but signal-row join is too
  sparse to authorize any trader-state decision patch.
- Cleanup helpers archive MT5 Common Files telemetry to Google Drive with
  manifests after meaningful runs.
- Backup-indexed cleanup history says 225 stale `Terminal/Common/Files`
  telemetry/cache items, total 439.72 MB, were archived under
  `MT5_Backtest_Cleanup_20260608_054307`. Cited 2026-05/06 run directories such
  as `20260608_024033` are absent from this lean checkout and are not current
  local evidence.

## Known Blockers

- No current candidate passes deploy-readiness.
- No current execution-eligible registry challenger exists; the only new idea
  is offline and cost-data blocked.
- Missing same-broker historical bid/ask ticks, complete commission provenance,
  and side-referenced slippage prevent a real `verified_execution_cost.v1`
  artifact even though the builder now exists.
- `confirmed` is blocked because current robustness/PBO/White Reality Check
  producers are diagnostic-only and no promotion-eligible optimization-aware
  WFA/full aligned variant family exists.
- Source S/R is not isolated by `InpUseSourceSrInteractionV1=false`; no
  no-decision-effect control claim is valid until fixed or ablated.
- Legacy `validate-full REVIEW 0/5` and baseline drift `282 / 237 / 95` are
  backup-indexed historical warnings, not current validator outputs.
- Broker geometry risk remains; historical telemetry showed invalid stop/modify
  failures before execution hygiene improved.
- MT5-native screenshot flow is useful but broad batch reliability still needs
  hardening.
- `20260501_221111` is invalid because it compiled from archived source.

## Next Actions

1. Use the registry/prereg/readout workflow for every meaningful experiment.
2. Do not patch strategy logic from `20260501_151422`; keep it as attribution data.
3. Do not mine more XAU hour/day/filter rules.
4. Do not advance `InpUseSourcePvaParityV1=1` to Model 0 or `validate-full`; it
   is parked as a decision-path override.
5. Keep `source_pva_*`, `source_sr_*`, and `source_classic_*` as source-authenticated audit context.
6. Do not add `InpUseSourceClassicWaveV1` from this probe; use locked chart
   labels/casebooks before any future Classic qualifier.
7. Use `sonic_*` trader-state fields for scanner-to-directional-candidate
   alignment and locked-label casebooks before any future decision qualifier.
   No `sonic_*` field may affect `should_trade` without a new prereg and
   matched control/challenger screen.
8. Candidate-like Label Packet V2 has been filled/frozen and failed offline
   separation. Keep the artifacts as falsification evidence; do not add
   `InpUseSonicCandidateAlignmentV1` or any context-direction qualifier from
   this hypothesis.
9. Treat the prepared manual label packet V1 as useful but insufficient by
   itself: the strict labels joined too sparsely to signal rows, and the current
   next target is source-case / MT5-native chart review of true London Classic
   direction semantics.
10. Keep XAU S1 trap/run classifier paused until the next work explicitly reopens
    it with a fresh prereg, matched `Deposit=100000` controls, and cadence-safe
    evidence. Do not reuse the killed M15 ATR >= 1.20 * EMA100 hard veto, and do
    not threshold-mine Dragon/Trend distance at `2.20` as a hard entry veto.
    Do not patch from the killed body-ratio / prior-5 clearance /
    Dragon-congestion proxy micro-structure probe or H1 sweep-depth structural
    probe, S/R runway audit, or signed H1 EMA34 velocity/age audit.
11. Do not rerun the same EUR M15 ClassicTrend true, no-PVSRA, source-core,
    M5 T1 density configs, EUR Asian Manip V1 all-candidate setup, EUR Counter
    Extension V1, or GBP London Value Drift V1 without a genuinely new
    hypothesis. GBP value drift to EMA89 is parked because target runway and
    cost gates failed; EUR counter-EMA/H4-extension is parked because holdout
    sample, separation, and concentration gates failed.
12. Do not run Gemini's `HYP-SR-FX-CONTEXT-ANATOMY-001` donor request. The
    outside-Asian-range + `CONTEXT_FAIL` + flat/compressed-Dragon formulation
    failed intake de-dup against killed London/Asian range and FX M15
    Dragon/Trend-state families.
13. Do not run Gemini's `HYP-SR-MGMT-MFE-INVARIANT-001` replay request. The
    MFE >= 1.0R move-to-+0.2R plus fixed +1.5R TP contract failed intake de-dup
    against Source Trade Management V1 and XAU Trap Management 003. It is
    trade-management/SL/TP/BE/risk geometry, not a new pre-entry Sonic R
    predicate.
14. Gemini's post-de-dup reply found no legal Sonic R thesis left under current
    exclusions. Treat that as reviewer input, not proof of impossibility. The
    Owner has now opened a separate FX portfolio/SilverBullet Phase 0 lane, but
    this does not reopen or override the parked Sonic feature frontier and does
    not authorize outcome analysis, EA strategy changes, compile, or backtest.
15. The user-authorized strategy-agnostic pivot is now preregistered, but its
    cost gate failed. Do not impute zero spreads, reuse the two EURUSD commission
    samples, infer zero slippage, or synthesize ask barriers from one M15 spread.
    Reopen only with complete tick/cost provenance and the immutable task-packet
    path.
16. Keep Source S/R blocked. Do not claim telemetry-only parity or matched
    control neutrality from `InpUseSourceSrInteractionV1=0` until a separate
    code fix or matched ablation proves the switch contract.

## Evidence Anchors

- EA failure portfolio audit: `03. EA Developer/EA_SonicR/research/20260710_EA_FAILURE_PORTFOLIO_AUDIT.md`
- Evidence-gated agent loop: `04. Project Control/ai/agent_ea_research_loop.md`
- Common-USD prereg: `03. EA Developer/EA_SonicR/research/preregs/20260711_H_FX_CROSS_SECTIONAL_USD_FACTOR_001_PREREG.md`
- Broker-cost provenance audit: `03. EA Developer/EA_SonicR/research/20260711_BROKER_COST_PROVENANCE_AUDIT.md`
- Gemini FX context intake de-dup: `03. EA Developer/EA_SonicR/research/readouts/20260608_FX_CONTEXT_ANATOMY_GEMINI_INTAKE_DEDUP_V1.md`
- Gemini post-de-dup frontier reply: `03. EA Developer/EA_SonicR/research/readouts/20260608_GEMINI_POST_DEDUP_FRONTIER_REPLY_V1.md`
- Gemini management MFE intake de-dup: `03. EA Developer/EA_SonicR/research/readouts/20260608_MGMT_MFE_INVARIANT_GEMINI_INTAKE_DEDUP_V1.md`
- Gemini post-management frontier recheck: `03. EA Developer/EA_SonicR/research/readouts/20260608_GEMINI_POST_MANAGEMENT_FRONTIER_RECHECK_V1.md`
- Review/handoff: `03. EA Developer/EA_SonicR/research/20260509_SONICR_RESULTS_AND_WORKFLOW_REVIEW.md`
- Source-parity readout: `03. EA Developer/EA_SonicR/research/20260509_SONICR_SOURCE_PVA_PARITY_V1_READOUT.md`
- Source-parity screen readout: `03. EA Developer/EA_SonicR/research/20260509_SONICR_SOURCE_PVA_PARITY_V1_SCREEN_READOUT.md`
- Source S/R probe readout: `03. EA Developer/EA_SonicR/research/20260509_SONICR_SOURCE_SR_INTERACTION_V1_PROBE_READOUT.md`
- Source Classic Wave/Dragon probe readout: `03. EA Developer/EA_SonicR/research/20260510_SONICR_SOURCE_CLASSIC_WAVE_DRAGON_V1_PROBE_READOUT.md`
- Trader-State Reader V1 smoke readout: `03. EA Developer/EA_SonicR/research/20260510_SONICR_TRADER_STATE_READER_V1_SMOKE_READOUT.md`
- Trader-State label loop readout: `03. EA Developer/EA_SonicR/research/20260510_SONICR_TRADER_STATE_LABEL_LOOP_READOUT.md`
- Trader-State label loop analyzer v2: `03. EA Developer/EA_SonicR/research/20260510_sonic_trader_state_label_v1_joined_loop_v2.md`
- Trader-State Directional V1 readout: `03. EA Developer/EA_SonicR/research/20260510_SONICR_TRADER_STATE_DIRECTIONAL_V1_READOUT.md`
- Trader-State Directional V1 sidecar audit: `03. EA Developer/EA_SonicR/research/20260510_sonic_trader_state_directional_v1_sidecar_audit.md`
- Scanner-Candidate Alignment V1 readout: `03. EA Developer/EA_SonicR/research/20260510_SONICR_ERROR_ANATOMY_AND_ALIGNMENT_V1_READOUT.md`
- Scanner-Candidate Alignment V1 report: `03. EA Developer/EA_SonicR/research/20260510_sonic_error_alignment_v1_scanner_candidate_alignment.md`
- Candidate-like label packet V2 readout: `03. EA Developer/EA_SonicR/research/label_packets/20260510_candidate_aligned_label_packet_v2_READOUT.md`
- Candidate-aligned locked labels V2: `03. EA Developer/EA_SonicR/research/label_packets/20260510_candidate_aligned_codex_locked_labels_v2_READOUT.md`
- Candidate-aligned locked-label separation V2: `03. EA Developer/EA_SonicR/research/20260510_candidate_aligned_locked_label_separation_v2.md`
- Source-trader research note: `03. EA Developer/EA_SonicR/research/20260510_SONICR_SOURCE_TRADER_RESEARCH_NOTE.md`
- Manual label packet V1: `03. EA Developer/EA_SonicR/research/label_packets/20260510_trader_state_manual_label_packet_v1_READOUT.md`
- Engineering Safety V1: `03. EA Developer/EA_SonicR/research/20260511_SONICR_ENGINEERING_SAFETY_V1_READOUT.md`
- EUR London Classic V1 killed readout: `03. EA Developer/EA_SonicR/research/20260511_SONICR_EUR_LONDON_CLASSIC_V1_READOUT.md`
- EUR M15 ClassicTrend true V1 killed readout: `03. EA Developer/EA_SonicR/research/20260511_SONICR_EUR_M15_CLASSICTREND_TRUE_V1_READOUT.md`
- EUR density recovery batch readout: `03. EA Developer/EA_SonicR/research/20260512_SONICR_EUR_DENSITY_RECOVERY_BATCH_V1_READOUT.md`
- EUR source-core casebook packet V1: `03. EA Developer/EA_SonicR/research/label_packets/20260512_eur_source_core_casebook_packet_v1_READOUT.md`
- Source quarantine: `03. EA Developer/EA_SonicR/source_quarantine/forexfactory/20260509_232500/`
- Sonic map: `README-SONIC R.md`
- Tool runbook: `04. Project Control/ai/sonic_tool_runbook.md`
- Validation gates: `04. Project Control/ai/sonic_validation_gates.md`
- Long-window phase readout: `03. EA Developer/EA_SonicR/research/20260503_SONICR_LONG_WINDOW_PHASE_ATTRIBUTION_011_READOUT.md`
- GoldRegime readout: `03. EA Developer/EA_SonicR/research/20260503_SONICR_GOLD_REGIME_CONTEXT_014_READOUT.md`
- Compression/retest/long-bias readout: `03. EA Developer/EA_SonicR/research/20260503_SONICR_COMPRESSION_RETEST_AND_LONG_BIAS_015_READOUT.md`
