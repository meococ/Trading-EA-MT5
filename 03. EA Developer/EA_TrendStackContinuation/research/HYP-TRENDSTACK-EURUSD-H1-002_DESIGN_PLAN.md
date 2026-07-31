# DESIGN OUTCOME PLAN — HYP-TRENDSTACK-EURUSD-H1-002

Status: FROZEN 2026-07-28 after independent Stage-0 evidence acceptance and
before any DESIGN M1 request, outcome, PnL, economic metric, or validation
outcome. This phase plan does not change the mechanism, indicators, clocks,
splits, costs, controls, or gates in the frozen SOURCE_PLAN. It only defines the
sequential DESIGN outcome data and evaluation contract. The active HYP-002
registry row and SOURCE_PLAN already freeze the sequential probe and condition
DESIGN outcome access on an independently accepted Stage-0 PASS. Registry
doctrine requires a surviving probe to remain a single `probe` row; it forbids
an additional `probe -> probe` row or a prereg-path change. Therefore this file
is a subordinate immutable phase/task contract: its SHA256 must be pinned in
the request-plan builder, acquisition tool, evaluator, receipts, and the
create-new run packet before any M1 request. It does not replace or amend the
registry-bound SOURCE_PLAN.

## 1. Authority and immutable upstream evidence

- Hypothesis: `HYP-TRENDSTACK-EURUSD-H1-002`.
- Package: `EA_TrendStackContinuation`; research-only. No MQL5, Model 0,
  promotion, paper, live, or deploy authority exists.
- SOURCE_PLAN SHA256:
  `3A6137ACEA37D1CC6BEE1700A561873AF8278AC524973054A82F92C70ED95EAF`.
- Accepted Stage-0 eligibility ledger SHA256:
  `3092A6FCFADE0DA23E4470C4BF3B1D7750190358CF6ED09A2BB942937A7CD3C7`.
- Stage-0 receipt file SHA256:
  `5AEA570736361EF22BF2F090A5C05EF2974F482B5CB34A1186F27D9B43AAF5CE`.
- Stage-0 access trace SHA256:
  `6C292ECA2A8332CAD1872F5C78843C5B80BE81A6B865C88AF3FB75C6678E4F15`.
- Stage-0 reconciliation SHA256:
  `7C59560205B0C43DE6C4E26AA7BD266FD45261DC6CEC3BFFB3681EB625E4B56F`.
- Decision packet manifest SHA256:
  `D199E105CF6B51E0516D4FB57FFCB0D9AF63A72D8084B04BE6D73892ED7EA9DA`.
- Decision packet receipt SHA256:
  `DA113E80157FFF69DBD11BB478637DC2DA3B9FD829102763250DA55D07773320`.
- Decision packet set SHA256:
  `22B0F111DCA293C0234C4C1D88F5A6E4CEABC7E7EE071466E310C9D0079F6E3E`.
- Independent audit recomputed all 1,817 packet/worker/ledger/trace mappings
  with zero errors. Stage-0 DESIGN STACK count is 661 (263 LONG / 398 SHORT)
  and VALIDATION_FEATURE_ONLY count is 267 (82 LONG / 185 SHORT); both gates
  passed. This is engineering evidence only, not economic evidence.

The current Owner scope plus the original HYP-002 `probe` row/SOURCE_PLAN
authorize source-tool/test construction after accepted Stage-0 evidence. No
DESIGN M1 request may occur until the acquisition and evaluator tools, their
tests, the deterministic request plan, and their hashes pass independent review
and a create-new `HYP-TRENDSTACK-EURUSD-H1-002_DESIGN_RUN_PACKET.json` binds
those exact hashes with verdict
`FROZEN_DESIGN_M1_PROXY_ONE_RUN_AUTHORIZED`. The next registry append is only a
legal terminal/progression transition (`killed`, `parked`, or `screened`) after
the DESIGN result; no duplicate `probe` row is permitted.

## 2. Unchanged mechanism and frozen populations

- Instrument: FivePercent `EURUSD`.
- Decision features: H1 `M252`, H1 06:00-11:00 `M6`, and MT5-compatible
  `ATR20` through the closed 11:00 H1 bar.
- Entry: 12:01 UTC M1 bid open.
- Stop: exactly `1.0 * ATR20`; no TP.
- Exit: stop or 18:00 UTC M1 bid open, same UTC date.
- Arms/trials remain exactly four:
  `CONTROL_M252_ONLY`, `CONTROL_M6_ONLY`, `CHALLENGER_STACK`, and
  `NEGATIVE_DISAGREE`.
- DESIGN remains `[2016-01-04, 2021-01-01)` with 1,824 elapsed calendar days /
  260.571428571 weeks.
- Frozen DESIGN opportunity dates: 1,297.
- Frozen DESIGN arm rows: M252 1,297; M6 1,292; STACK 661; DISAGREE 631;
  total evaluated arm rows 3,881.
- VALIDATION dates, validation M1, and all timestamps on/after 2021-01-01 are
  forbidden in this phase. HOLDOUT 2023+ remains sealed.

## 3. Deterministic DESIGN request plan

`build_trendstack_002_design_request_plan.py` may read only the accepted
Stage-0 ledger/receipt and the bound DESIGN decision packets. It emits one
request row per unique DESIGN opportunity date, independent of arm count.

- Request count: exactly 1,297.
- Request ID: `M1-DESIGN-{sequence:04d}-{YYYYMMDD}`.
- Canonical window: `[d 12:01:00Z, d 18:00:00Z]`, inclusive M1 opens.
- Expected rows: exactly 360 per date; total 466,920.
- First/last dates: 2016-01-04 / 2020-12-31.
- Clock mapping uses the SHA-bound `fivepercent_server_clock.py`. Convert each
  UTC boundary separately to the unique FivePercent server-wall time and
  round-trip it back to UTC before freezing the row.
- Any validation/holdout date, duplicate ID/date, non-monotonic row, path
  escape, count drift, ledger/packet hash drift, or clock ambiguity is
  `INVALID_ENGINEERING`.

The request plan is canonical JSONL, create-new, byte deterministic, and
hash-bound into the run-authorizing registry row. It contains no price,
direction, ATR, arm, return, outcome, or metric.

## 4. Source-only M1 acquisition

`acquire_trendstack_002_design_m1.py` may import MetaTrader5 and may read only
the frozen request plan. It must not read the Stage-0 ledger, decision packet
features, arm/direction/ATR fields, evaluator, or economic artifacts.

- Explicit portable terminal path; `portable=True`.
- Require terminal-side trading disabled, demo mode, exact FivePercent
  server/company, and EURUSD digits/point.
- Use one bounded `copy_rates_range` request for each frozen request row.
- Never silently retry, widen, clip, filter, or skip an illegal response.
- Every response must contain exactly the 360 unique chronological UTC M1 opens
  12:01 through 18:00, valid OHLC, and no timestamp outside the request.
- Any missing minute, duplicate, out-of-window row, invalid geometry, clock
  drift, runtime/provenance mismatch, or shutdown failure invalidates the whole
  acquisition. It is not a market verdict.
- `mt5.shutdown()` is mandatory in `finally`; the parent stops the exact spawned
  portable terminal process after capture and verifies no residual process.

All data persists on D under:

```text
02. AlphaFactory/data/fivepercent/EURUSD/trendstack_002_design_m1/
  design_request_plan.jsonl
  raw_m1/DESIGN/YYYY-MM-DD/1201_1800.parquet
  design_m1_manifest.jsonl
  design_m1_source_receipt.json
```

Each shard is one file with one row group and explicit server/UTC clock,
bid-OHLC, volume, spread-points, and request identity fields. Writes use a
create-new attempt root. Failure is quarantined with a manifest; no overwrite
or destructive cleanup. Before this 1,297-run batch, record storage inventory
and cleanup dry-run. The source receipt must bind every request/shard/runtime/
tool/plan hash and attest:

- `design_m1_opened=true`;
- `validation_m1_opened=false`;
- `holdout_opened=false`;
- `economics_computed=false`;
- `physical_partition_status=PASS`.

## 5. Frozen evaluator and one-day execution model

`evaluate_trendstack_002_design.py` is offline-only. It cannot import MT5 or
network packages and cannot read raw H1. Inputs are the accepted Stage-0 ledger,
the bound DESIGN decision packets, the frozen request plan, and the validated
DESIGN M1 manifest/receipt/shards.

- Eligibility, direction, opportunity ID, and ATR20 come unchanged from the
  accepted Stage-0/decision packet chain. The evaluator cannot recompute M252,
  M6, eligibility, direction, or ATR.
- Entry price is the 12:01 `bid_open`.
- LONG stop = entry - ATR20; SHORT stop = entry + ATR20.
- The stop is active on bars 12:01 through 17:59.
- On the entry bar, low/high touching the stop exits at the exact stop.
- On later bars, an adverse open at/beyond the stop exits at that bar open;
  otherwise a high/low touch exits at the exact stop.
- If untouched, exit at the 18:00 `bid_open`. Do not use 18:00 high/low. An
  18:00 open beyond the stop is still `TIME_EXIT_1800` at that open.
- There is one barrier and no TP, so no SL-vs-TP intrabar tie exists.
- Missing any required minute or join identity is `INVALID_ENGINEERING`; never
  drop the opportunity.

For direction `+1/-1`:

```text
gross_R = direction * (exit_bid - entry_bid) / ATR20
stop_pips = ATR20 / 0.0001
net_R = gross_R - round_trip_cost_pips / stop_pips
```

Fixed unverified round-trip proxy tiers are 1.50, 2.25, and 3.00 pips. They are
kill-only proxies, not verified broker cost and not separate trials. JSON must
not contain NaN/Infinity; PF with zero loss uses an explicit status, and a
zero-win/zero-loss sample cannot pass.

## 6. Frozen DESIGN gates

All gates apply to `CHALLENGER_STACK` on DESIGN. No threshold may change after
opening outcomes.

1. Completed cadence is 2.0..5.0 per 260.571428571 elapsed weeks.
2. PF at 1.50 pips is `>1.30`.
3. PF at 2.25 pips is `>=1.25`.
4. PF at 3.00 pips is `>=1.00`.
5. Mean net R at 1.50 pips is `>=0.08`.
6. Total net R at 1.50 pips is `>0`.
7. At least 4 of 5 DESIGN years have positive net R at 1.50 pips.
8. DSR at 1.50 pips is `>=0.95` across exactly four arm trials.
9. STACK PF delta versus the better standalone PF is `>=0.15`.
10. STACK mean-R delta versus the better standalone mean-R is `>=0.05`.
11. STACK PF delta versus DISAGREE is `>=0.15`.
12. STACK mean-R delta versus DISAGREE is `>=0.05`.

For each relative metric, the better standalone control is the separate maximum
of M252 and M6 for that metric. DSR uses canonical `dsr.py`, per-trade 1.50-pip
returns, sample variance across four arm Sharpe ratios, `n_trials=4`, challenger
skew, and non-excess kurtosis. Also emit a common 1,824-day UTC book with
no-trade days as zero. DD and Monte Carlo are diagnostics only in this proxy
phase and cannot promote.

## 7. Artifacts, tests, and verdict routing

Evaluation output is create-new under:

```text
research/evidence/HYP-TRENDSTACK-EURUSD-H1-002_DESIGN/
  design_trade_ledger.jsonl
  design_daily_book.jsonl
  design_economic_result.json
  design_evaluation_receipt.json
```

The receipt binds every upstream plan/source/ledger/packet/request/M1/evaluator
hash, exactly 3,881 evaluated arm rows, four trial rows, all output hashes, and
false validation/holdout attestations.

Red-first tests must cover exact request/date/row counts and clock round-trip;
validation/holdout/path/reparse rejection; mandatory shutdown; missing,
duplicate, or malformed minutes; deterministic create-new receipts; exact arm
joins; all long/short entry-bar, gap, equality-touch, and 18:00 exits; cost
arithmetic; every strict/inclusive gate boundary; DSR sample variance with four
trials; the 1,824-day common book; and invalid inputs producing no economic
verdict.

- Data/hash/path/clock/minute/join/reconciliation failure:
  `INVALID_ENGINEERING`; repair the same contract, no market verdict.
- Any DESIGN economic, relative, yearly, or DSR gate failure: `KILL`; do not
  acquire validation M1 and do not rescue this ID post hoc.
- All DESIGN gates pass: `PROBE_SURVIVOR_DESIGN_ONLY`; validation remains
  unauthorized until a separate frozen validation phase plan and registry row.
- No DESIGN result authorizes MQL5, Model 0, promotion, paper, live, or deploy.
