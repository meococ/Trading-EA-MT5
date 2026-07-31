# DESIGN ECONOMICS PLAN - HYP-VCEX-EURUSD-M15-002

Status: FROZEN PRE-OUTCOME on 2026-07-29. This is a **fresh pre-outcome DESIGN
economics child** enabled solely by the outcome-blind HYP001 source-feasibility
PASS. It is **not** a post-hoc market rescue of any prior economic object, and it
does **not** reopen, retune, or reinterpret HYP001 source thresholds.

An engineering-valid gate failure under this plan **kills exactly HYP002**. No
same-ID rescue of session, weekday, year, direction, threshold, stop, target,
horizon, cost, symbol, timeframe, source reselection, control arm, or entry delay
is permitted.

## 1. Identity and failure radius

- `hypothesis_id`: `HYP-VCEX-EURUSD-M15-002`
- `parent_candidate`: `HYP-VCEX-EURUSD-M15-001` (PASS source feasibility)
- `ea_name`: `EA_VolumeClockExhaustion`
- `family`: `volume-clock-early-impulse-exhaustion-reversal-design-economics`
- Symbol / decision surface: EURUSD M15 source population; economics on public
  DESIGN M1 BID bars only.
- Attempt: `VCEX002-DESIGN-ECON-001` (limit exactly one).
- Fresh evidence root:
  `03. EA Developer/EA_VolumeClockExhaustion/research/evidence/HYP-VCEX-EURUSD-M15-002_DESIGN_ECONOMICS/VCEX002-DESIGN-ECON-001`.

Parent HYP001 terminal path/SHA:

- `03. EA Developer/EA_VolumeClockExhaustion/research/evidence/HYP-VCEX-EURUSD-M15-001_SOURCE_FEASIBILITY/VCEX001-SOURCE-001/attempt_terminal.json`
- SHA256 `74832896B42BEE53E4375069B56CFDEB5114BCA66A24E068DC7041F5612C1D49`
- Status: `PASS_SOURCE_FEASIBILITY`
- Stage-0 verdict: `SOURCE_PASS_FUTURE_ECONOMICS_PREREG_ONLY` (non-authoritative
  calculation on the non-terminal receipt only)

**Failure radius (exact tested object):**

Child `HYP-VCEX-EURUSD-M15-002` using the fixed HYP001 807-pair population with
`tau0.40 / early0.45ATR / exhaustion0.30 / 07-16UTC / max1day / 8bar / 1R`;
TRUE fade vs FOLLOW_CONTROL; entry/stop/TP/time/gap/adverse-first rules; costs
`1.50 / 2.25 / 3.00` pips; fixed `0.5%` initial-equity risk; DSR with exactly two
trials; all eleven gates on public DESIGN only.

No threshold, session, direction, stop, target, horizon, cost, symbol, TF, source,
or control rescue under the same ID.

## 2. Frozen HYP001 source population (authority before price)

Bind and validate **before any DESIGN price access**:

| Artifact | Relative path under HYP001 evidence root | SHA256 |
|---|---|---|
| Classifications | `vcex_001_source_classifications.jsonl` | `FDD3D608A70D54634511A582E202D431D42F04EEEFBB0239233BB38D32407D06` |
| Source ledger | `vcex_001_source_ledger.jsonl` | `EA608B72DBF146E45FD568BD5A1AA9EC2691D2AE1BF78F244C007F157BDD1978` |
| Report | `vcex_001_source_report.json` | `7911A5C9D0585F7F897BAD3779E67F3EA717754DEBB3DE3EB9EFB18AD5E93845` |
| Non-terminal receipt | `source_feasibility_receipt.json` | `0D1911848896B9E4D30C21A32AF3720A9D4A0C9A2C231DEFAD2DF73F1E191425` |
| Terminal | `attempt_terminal.json` | `74832896B42BEE53E4375069B56CFDEB5114BCA66A24E068DC7041F5612C1D49` |
| Attempt started | `attempt_started.json` | `8D4B7E750448CA3E337A7338C0A27B3A711C47F3B7BA1F304962AB0012658ABF` |

Evidence root:

`03. EA Developer/EA_VolumeClockExhaustion/research/evidence/HYP-VCEX-EURUSD-M15-001_SOURCE_FEASIBILITY/VCEX001-SOURCE-001`

Exact population constants (fatal):

- Classifications: **812** = **807** `SOURCE_EXECUTABLE` + **5** `HORIZON_INCOMPLETE`
- Source ledger: exactly **807 TRUE** + **807 FOLLOW_CONTROL**
- Every executable `source_signal_id` must join **exactly once** to both
  opposite-direction ledger rows
- Excluded / incomplete IDs join **neither** ledger arm
- No drop, reselection, replacement, mutation, fan-out, or silent filter
- Classification digest SHA256 `7FFF418FB2AC78B38651B3A455D69A45333FE1C4EC7CEB1F04FEE7E6F79703F2`
- Canonical digest SHA256 `07006B208371AEAB2CD97C0B44A34E742269AD9C8A155D536966AE31A9B16169`
- Source registry row SHA256 `CD420E208611FE27590903590134A5E434920D3C53B25F4469DE27D2FA02D352`

Paired ledger invariant for each `source_signal_id`:

TRUE and FOLLOW_CONTROL must share `decision_utc`, `entry_open_utc`,
`time_exit_utc`, `stop_distance_pips`, `h`, `tau`, `p_early`, `p_late`, and must
be exact opposite directions (`LONG`/`SHORT`).

Non-terminal receipt **cannot** authorize PASS economics. Terminal is sole
authoritative completion of the source stage. Sealed source counters must show
zero economics / outcome / MT5 / network activity.

## 3. Exact M1 mapping and 1R execution (no delay / no censor drop)

Use only FivePercent `splitvault_002` public DESIGN M1
`2016-01-04` .. `2020-12-31`.

Producer bindings:

- Manifest SHA256 `A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7`
- Receipt SHA256 `8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8`
- Public M1 source SHA256 `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`

Decode **only** `time_utc` / `open` / `high` / `low` / `close` for economics
after full authority. Never request or depend on `spread`, `tick_volume`,
private/validation/holdout paths, network, MT5, or MQL5.

Manifest/producer defenses (fatal): exact ordered public schema; path/date/SHA/
bytes/rows; one row group if producer contract requires it; no aliases/hardlinks/
symlinks; monotonic unique M1; finite valid OHLC.

For each paired source signal:

1. Entry is the BID **open** of the exact M1 bar at `entry_open_utc`. Missing exact
   entry minute is engineering-invalid.
2. Require exactly **120 unique contiguous** M1 timestamps from `entry_open_utc`
   inclusive through `time_exit_utc` exclusive. No fallback, delay, fill, or
   right-censor drop.
3. Stop distance = `stop_distance_pips * 0.0001`. TP distance = same (1R).
4. LONG: stop = entry − distance, TP = entry + distance. SHORT: mirror.
5. Inspect M1 bars chronologically.
6. At any M1 **open** beyond the adverse stop, exit at that open with
   `gross_R <= -1` (realized open slippage allowed worse than −1R).
7. At any M1 **open** beyond the favorable TP, exit at that open and **cap**
   favorable `gross_R` at `+1`.
8. Otherwise, if both stop and TP are touched inside the same M1 bar, **adverse
   stop wins**: stop `gross_R = -1`; TP would have been `+1`.
9. If no barrier hits, exit at the **close** of minute `time_exit_utc - 1m` with
   `gross_R = direction_sign * (exit - entry) / stop_distance`.

All-or-nothing mapping before metrics: every one of the **807 + 807** trades must
map. Re-assert max-one-per-UTC-day and arm-local non-overlap. Any mismatch is
`ENGINEERING_INVALID_NO_MARKET_VERDICT` before gate evaluation, DSR, or success
artifacts.

## 4. Cost, fixed-initial-equity risk, DSR

- Round-trip cost tiers exactly `1.50`, `2.25`, `3.00` pips
  (`UNVERIFIED_PROXY_KILL_ONLY` stresses, **not** extra trials).
- `cost_R = cost_pips / stop_distance_pips`
- `net_R = gross_R - cost_R`
- Drawdown uses chronological TRUE trades at 1.50 pips with **fixed 0.5%
  initial-equity risk and no compounding**:
  - equity starts at `100`
  - `equity_t = 100 + 0.5 * cumulative_net_R`
  - peak = max prior equity including the initial `100`
  - `DD_pct = (peak - equity) / peak * 100`
  - maximum DD must be finite
- DSR uses per-trade 1.50-pip `net_R`; sample Sharpe mean/sample-std; population
  skew; non-excess kurtosis; sample variance across exactly the TRUE and
  FOLLOW_CONTROL arm Sharpes; `n_trials = 2`; TRUE `n_obs = 807`
- Canonical DSR tool:
  `02. AlphaFactory/tools/research/dsr.py`
  SHA256 `A0659CDCDB2EAB4F29F69A1FBF4222FE3EC12467FE4CC664E194173126A4CEEA`

Elapsed calendar weeks (identity denominator, not active weeks):

`ELAPSED_WEEKS = (2020-12-31 - 2016-01-04).days / 7 = 260.42857142857144`

TRUE cadence identity: `807 / 260.42857142857144` must lie in `[2.0, 5.0]`.

## 5. Eleven fatal gates and verdicts

1. TRUE cadence `2.0 <= x <= 5.0` over elapsed calendar weeks
   (`807 / 260.42857142857144`, identity gate).
2. TRUE PF at 1.50 pips `>= 1.30`.
3. TRUE PF at 2.25 pips `>= 1.25`.
4. TRUE PF at 3.00 pips `> 1.00`.
5. TRUE mean net_R at 1.50 pips `> 0`.
6. TRUE total net_R at 1.50 pips `> 0`.
7. TRUE positive DESIGN calendar years at 1.50 pips `>= 3 of 5`
   (fixed years 2016..2020).
8. TRUE fixed-initial-equity max drawdown at 1.50 pips `< 8.0%`.
9. TRUE DSR at 1.50 pips `>= 0.95` with exactly 2 trials.
10. TRUE PF minus FOLLOW_CONTROL PF at 1.50 pips `>= 0.15`
    (infinite PF handled fail-closed / explicitly).
11. TRUE mean net_R minus FOLLOW_CONTROL mean net_R at 1.50 pips `>= 0.05`.

Verdicts:

- Engineering-valid and all 11 pass =>
  `PASS_DESIGN_ECONOMICS_MAY_BUILD_EA`
  (DESIGN survivor only; no validation/live claim).
- Engineering-valid and any gate fails =>
  `KILL_DESIGN_ECONOMICS_NO_EDGE` for exact HYP002; no same-ID rescue.
- Any authority / source / join / data / mapping / durability invalid =>
  `ENGINEERING_INVALID_NO_MARKET_VERDICT` before any economic claim.

## 6. One-use authority, durability, and prohibitions

- Evaluator:
  `03. EA Developer/EA_VolumeClockExhaustion/research/evaluate_vcex_002_design_economics.py`
- Tests:
  `03. EA Developer/EA_VolumeClockExhaustion/research/tests/test_evaluate_vcex_002_design_economics.py`
- Run packet (not created by this implementation task):
  `03. EA Developer/EA_VolumeClockExhaustion/research/HYP-VCEX-EURUSD-M15-002_DESIGN_ECONOMICS_RUN_PACKET.json`
- Review receipt (not created by this implementation task):
  `03. EA Developer/EA_VolumeClockExhaustion/research/HYP-VCEX-EURUSD-M15-002_DESIGN_ECONOMICS_IMPLEMENTATION_REVIEW_RECEIPT.json`

Import-safe and exact sentinel:

`REVIEWED_RUN_PACKET_SHA256: str | None = None`

Production requires explicit CLI switch, exact reviewed packet SHA, exact
evaluator/test/plan/review-receipt/source-artifact/data/DSR hashes, and the
latest canonical registry HYP002 row authorizing exactly one attempt.

Durability rules:

- Create-new evidence root; attempt limit one; no overwrite/reuse/same-ID rerun.
- Terminal is sole durable authoritative completion status.
- Terminal must hash-bind `attempt_started`, trade ledger, arm metrics, yearly,
  drawdown, DSR, gate report, and non-terminal receipt.
- Non-terminal receipt cannot authorize PASS.
- Post-write suspect PASS recovery must become
  `ENGINEERING_INVALID_NO_MARKET_VERDICT` (same spirit as HYP001 source builder).
- No success economics artifacts before all-or-nothing mapping and gate
  evaluation succeed.
- Ship disarmed. Plan alone grants no run authority.

Forbidden throughout HYP002: validation, holdout, private custody, MQL5, MT5,
Model 0/4, optimization, network, paid calls, promotion, paper trading, live
trading, and any production parquet/economic outcome inspection by the builder
task that freezes this plan.

Required success artifacts (production only, not this implementation task):

`attempt_started.json`, `design_economics_trade_ledger.jsonl`,
`design_arm_cost_metrics.json`, `design_yearly_metrics.json`,
`design_drawdown_metrics.json`, `design_dsr_inputs.json`,
`design_gate_report.json`, `design_economics_receipt.json`,
`attempt_terminal.json`.

## 7. Implementation-task boundary

This plan freezes the economics object, fixed HYP001 population join, M1
execution surface, costs, fixed-initial DD, DSR, and eleven gates. The builder
may create only this plan, the disarmed one-shot evaluator, and focused synthetic
tests. It must not create a run packet, review receipt, registry row, evidence
root, arm the sentinel, open production parquet/economic outcomes, execute
production, or touch MT5/MQL5.
