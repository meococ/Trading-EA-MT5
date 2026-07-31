# HYP-VCEX-EURUSD-M15-001 — Stage-0 Source Feasibility Plan (Frozen)

## Identity

| Field | Value |
|---|---|
| Hypothesis ID | `HYP-VCEX-EURUSD-M15-001` |
| EA / package | `EA_VolumeClockExhaustion` |
| Family | `volume-clock-early-impulse-exhaustion-reversal` |
| Attempt | `VCEX001-SOURCE-001` (exactly one production attempt) |
| Symbol / TF | EURUSD / M15 (built from public DESIGN M1) |
| Window | `2016-01-04` .. `2020-12-31` (FivePercent splitvault_002 public DESIGN) |
| Purpose | Outcome-blind **source / cadence / geometry falsification only** |
| Builder | `03. EA Developer/EA_VolumeClockExhaustion/research/build_vcex_001_source.py` |
| Tests | `03. EA Developer/EA_VolumeClockExhaustion/research/tests/test_build_vcex_001_source.py` |
| Evidence root (create-new, replay-forbidden) | `03. EA Developer/EA_VolumeClockExhaustion/research/evidence/HYP-VCEX-EURUSD-M15-001_SOURCE_FEASIBILITY/VCEX001-SOURCE-001` |
| Review receipt path | `03. EA Developer/EA_VolumeClockExhaustion/research/HYP-VCEX-EURUSD-M15-001_SOURCE_IMPLEMENTATION_REVIEW_RECEIPT.json` |

**Status:** FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN once registry row + independent review arm the builder. This plan does **not** authorize economics, outcomes, MT5/MQL5, validation/holdout, promotion, or live trading.

Runtime plan binding: the builder constant `PLAN_SHA256` must equal the SHA-256 of this exact file’s bytes. The plan does not embed its own hash (avoids self-referential hashing). Builder and tests recompute and fail-closed on drift.

## Literature (measurement prior only)

These papers motivate volume-clock / activity-time and early-session impulse measurement. **None proves this EURUSD rule profitable.**

1. Clark (1973), *A subordinated stochastic process model with finite variance for speculative prices* — activity time / volume clock foundation.
2. Ane & Geman (2000), *Order flow, transaction clock, and normality of asset returns* — transaction-time versus wall-clock.
3. Easley, López de Prado & O’Hara (2012), *Flow toxicity and liquidity in a high-frequency world* — volume-bucket / VPIN measurement prior only.

## De-dup / failure radius

**Classification:** `MATERIALLY_NEW_WITH_HIGH_ADVERSE_OHLC_PRIOR`.

This object is **not**:

- HYP-DFR-IC diurnal residual impulse continuation
- HYP011 round lattice
- TrendStack clock stack
- ARUC signed tick-volume activity / H1 response
- LVOR low-activity overshoot reversal
- ECRS compression release
- BR / EUR session drift
- MR grid
- SCC pivot cascade
- ICT / FVG / sweep
- raw early-to-late half-hour momentum
- wall-clock fixed-minute `h=7` split (explicitly rejected; must not appear as a trial)

Legality of this ID comes **only** from the frozen conjunction:

1. Intrabar **volume-clock half-mass** location `tau` from M1 tick volumes (not wall-clock minute fixed at 7)
2. Early impulse magnitude vs contemporaneous **price-unit** ATR14 (`abs(P_early) >= 0.45 * ATR14`)
3. Exhaustion of late residual (`P_late` opposite or shrunk vs early)
4. Matched fade-vs-continuation decision object (**TRUE** / **FOLLOW_CONTROL** only)
5. Max-one-per-UTC-day execution surface with eight complete M15 bars / 120 minutes

**If killed:** failure radius closes this exact object  
`VCEX M15 tau0.40/early0.45ATR/exhaustion0.30/07-16UTC/max1day/8bar/1R TRUE-vs-FOLLOW EURUSD DESIGN`.  
No threshold, session, stop, horizon, or control rescue under this ID. No wall-clock `h=7` economic trial.

## Data contract (immutable)

| Binding | Value |
|---|---|
| M1 root | `02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002` |
| Manifest | `public/design_manifest.jsonl` SHA `A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7` |
| Receipt | `public/design_receipt.json` SHA `8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8` |
| Source corpus | SHA `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A` |
| Manifest dates / rows | 1555 dates, 1_859_820 rows, start/end as above |
| Registry validator | `04. Memory/research/validate_candidate_registry.py` SHA `B04B379E11F556A0CF3E6C3264768176310FF01CF360CC3B92464C51A2996DD0` |
| Registry schema | `04. Memory/research/CANDIDATE_REGISTRY.schema.json` SHA `96C80D3C46A105A9754CA1325F3DD6C160D92A9D5800ECBC402DE0F40C612F5C` |

**Decode only** `time_utc`, `open`, `high`, `low`, `close`, `tick_volume` from public DESIGN after full authority.  
**Never** request or depend on `time_server`, `spread`, `real_volume`, private/validation/holdout paths/columns, outcomes, or post-entry prices for source eligibility.

### M15 construction (immutable)

- Construct each UTC M15 from **exactly 15 unique observed M1 offsets** `0..14`.
- Finite OHLC with `O<=H`, `O>=L`, `C<=H`, `C>=L`.
- Nonnegative finite `tick_volume` on every M1 minute.
- Strict monotonic timestamps; reject duplicates; **never fill gaps**.

## Frozen mechanism

### Signal domain (prospective)

- UTC weekdays only (Monday–Friday).
- Signal-bar **start** hours `07..16` inclusive.
- No later hour/day/year rescue.

### Features (closed-bar only)

Signal bar `i` requires ATR14 from the 14 immediately contiguous complete M15 true ranges ending at `i` (gaps reset ATR / unavailable):

- `TR_j = max(H_j-L_j, abs(H_j-C_{j-1}), abs(L_j-C_{j-1}))`
- `ATR14_i` = simple mean of those 14 TR values (closed bars through `i` only).

Within signal bar M1 minutes `j=0..14`:

- `TV_j = tick_volume_j`
- `totalTV = sum_j TV_j` and require `totalTV > 0`
- `h = min { j : cumulative TV through j >= 0.5 * totalTV }`
- `tau = (h + 0.5) / 15`
- `P_early = C_h - O_0`
- `P_late = C_14 - C_h`

### Gates (frozen)

Eligible raw signal iff **all** hold:

1. `tau <= 0.40`
2. `P_early != 0`
3. `abs(P_early) >= 0.45 * ATR14`
4. Exhaustion: `(P_late * P_early) <= 0` **OR** `abs(P_late) < 0.30 * abs(P_early)`

Scan chronological and retain the **first eligible raw signal per UTC date only**.

### Arms (exactly two; matched)

On identical `source_signal_id`, signal/entry timestamps, stop, and horizon:

- **TRUE** direction = `-sign(P_early)` (fade / reverse early impulse)
- **FOLLOW_CONTROL** direction = `+sign(P_early)` (continuation control)

These are the **only** two future economic arms.  
The wall-clock fixed-minute `h=7` proposal is **rejected** and must **not** appear as a trial. No third arm.

### Execution surface (source reservation, no outcomes)

- Planned entry timestamp = signal close / next M15 start (`availability_utc`).
- Horizon executable only if entry **plus** the following **seven** exact complete M15 timestamps exist (**8** entry-period bars / **120** minutes).
- Horizon check uses complete-bar **timestamps only** — zero post-entry OHLC reads for eligibility.
- Planned time exit = `entry + 120` minutes.
- Planned stop distance = `max(ATR14_i, 0.0006)`.
- Future TP geometry intent = **1R** (source plane does not realize outcomes).
- Stage-0 cost tier geometry only: fixed `0.00015` round-turn; `cost_to_stop_ratio = 0.00015 / stop_distance`.

## Stage-0 gates (all fatal)

1. Signal-domain M15 completeness ≥ 0.99  
   - Denominator: all UTC-aligned M15 bins for each public DESIGN **manifest weekday** date, hours `07..16` inclusive (40 bins/day).  
   - Numerator: exact complete M15 bins in that domain. Exclude weekends and hours outside `07..16`.
2. Source-executable horizon ratio ≥ 0.99 among **first-per-day raw** signals.  
   Persisted eligible population = horizon-complete only; report raw + excluded counts.
3. Eligible cadence in `[2.0, 5.0]` per elapsed calendar week;  
   `elapsed_weeks = (2020-12-31 - 2016-01-04).days / 7` (**not** active weeks).
4. FOLLOW_CONTROL matched count/timestamps/`source_signal_id` equals TRUE by construction.
5. TRUE long share ≥ 0.25 and short share ≥ 0.25; max single calendar-year share ≤ 0.35; ≥ 20 eligible TRUE per side.
6. Median planned `cost_to_stop_ratio` ≤ 0.25; median `stop_distance_pips` ≥ 6.0 (boundary-safe comparison includes equality).
7. Exact-once classification, independent replay/digest equality, and all source-only zero counters pass.
8. Zero post-entry OHLC reads; zero outcome fields; returns/trades/economics/performance all zero/false.

**Failure label:** `SOURCE_FAIL_NO_ECONOMICS_AUTHORITY` (engineering / source plane) — **not** market no-edge.  
**PASS alone** may draft a fresh economics prereg; it does **not** run economics.

## Future economics intent (not authority)

Only after a **separate** prereg following source PASS:

- Entry next-M15 open; SL 1R; TP 1R; time exit after 8 M15 bars.
- Adverse-first M1 pathing; cost tiers 1.5 / 2.25 / 3.0 pips.
- Fixed 0.5% initial equity risk/trade, no compounding; one position / max 1 UTC day.
- Gates: base PF ≥ 1.30; PF@2.25 ≥ 1.25; PF@3.0 > 1.0; after-cost meanR > 0; max DD < 8%; ≥ 3/5 positive years; DSR trials = **exactly 2 arms**.

This section is **intent only**. Stage-0 must not execute economics.

## Authority / disarmament

- Python module is **inert on import**.
- Production CLI requires **both**:
  1. `--execute-probe`
  2. `REVIEWED_REGISTRY_ROW_SHA256: str | None = None` replaced by an independently reviewed uppercase 64-hex canonical registry-row SHA
- Ship sentinel **exactly disarmed** (`None`).
- Registry authority requires `source_run_authorized=true`, `source_feasibility_only=true`, attempt limit/id/root, reviewed plan/builder/test/receipt hashes; every economics/outcome/validation/holdout/private/network/paid/MT5/MQL5/promotion/live permission **false**; all counters zero pre-run.
- The canonical independent-review receipt binds this plan under the generic registry key `v1_plan` (not `plan`), so the builder and canonical registry validator enforce the same exact object.
- Evidence: create-new exclusive root; attempt_started → report/classifications/ledger/receipt → attempt_terminal hash chain; replay-forbidden on the same attempt root.
- Independent replay / canonical digest / exact-once identity checks required (semantics below).

## Durability / reconciliation (frozen Stage-0 semantics)

These rules do **not** change market gates, thresholds, arms, horizon, cost geometry, or data window. They only harden identity, replay, and completion authority.

### 1) Exact-once raw-signal classification

- Assign a deterministic `source_signal_id` to every first-per-day raw signal **before** horizon evaluation.
- Persist an outcome-blind classification row for every raw signal, **exactly once**, with:
  - `source_signal_id`
  - decision timestamp and planned entry timestamp
  - `status` ∈ {`SOURCE_EXECUTABLE`, `HORIZON_INCOMPLETE`}
  - `observed_horizon_bars` and `required_horizon_bars`
  - **no** post-entry OHLC and **no** outcome fields
- Mapping rules:
  - each `SOURCE_EXECUTABLE` `source_signal_id` maps to exactly one TRUE and exactly one FOLLOW_CONTROL ledger row
  - each excluded (`HORIZON_INCOMPLETE`) id maps to **neither** arm
  - candidate ids remain unique
- Hard identity: `raw_count == classification_count == executable + excluded` and max one decision per UTC date.
- Persist reconciliation counts/booleans and a canonical `classification_digest_sha256` covering ordered classification rows plus the exact arm-identity projection.

### 2) Independent replay before report persistence

- Before any report / classification / ledger / receipt / terminal persistence, recompute the full pure scan from a **separately reconstructed immutable copy** of decoded M1 rows and decision dates.
- Do **not** reuse or mutate the primary report object for the replay path.
- Re-run aggregation → features → raw signal → horizon/classification → gates and compare canonical projections / digests **byte-for-byte**.
- Fail closed on any mismatch.
- Persist primary and replay canonical digest SHA-256 values (must be equal) and `exact_once_reconciliation=true`.
- Mutation, reordering, or omission of classification/ledger projection must reject under independent replay.
- Implementation must avoid infinite recursion: one-pass pure scan (`scan_source_once`) is separate from the replay wrapper (`independent_replay_scan` / `scan_source`).

### 3) Terminal-sole PASS authority

- A non-terminal receipt must **never** claim `PASS_SOURCE_FEASIBILITY`.
- Receipt status is exactly `NON_TERMINAL_SOURCE_RESULT_AWAITING_ATTEMPT_TERMINAL`.
- Receipt retains computed `stage0_verdict` only as a **non-authoritative calculation** (`stage0_verdict_is_non_authoritative_calculation=true`) and declares `terminal_is_sole_authoritative_completion=true`.
- Receipt must **not** carry an authoritative `terminal_status=PASS_*` field.
- `attempt_terminal.json` is the **only** artifact allowed to authorize `PASS_SOURCE_FEASIBILITY` (or `SOURCE_FAIL_NO_ECONOMICS_AUTHORITY` / `ENGINEERING_INVALID_NO_MARKET_VERDICT`).
- If the final success-terminal write fails after the receipt already exists, `execute_probe` must persist `ENGINEERING_INVALID_NO_MARKET_VERDICT`; the surviving receipt must remain visibly non-terminal / non-PASS.
- Engineering terminal must hash-bind every artifact that existed under the attempt root (excluding the terminal file itself at bind time).

## Deliverables of this coding task

1. This frozen plan
2. Disarmed builder `build_vcex_001_source.py`
3. Focused synthetic test suite `test_build_vcex_001_source.py`

**Out of scope for this coding task:** reading production parquet, creating evidence, mutating the registry, running economics/MT5/MQL5, or claiming edge.
