# PROBE PLAN — HYP-TRENDSTACK-EURUSD-H1-003

Status: **FROZEN before HYP-003 source access, price-row read, outcome, PnL, or
economic metric** on 2026-07-28.

This is a fresh source-contract successor to HYP-002. HYP-001 and HYP-002 were
parked for engineering/data-access failures with no authorized market verdict.
The market mechanism, indicator definitions, clocks, arms, trial budget,
execution proxy, costs, and economic gates remain unchanged. HYP-003 changes
only the M1 source plane and capability boundary.

## 1. Identity, de-duplication, and parent evidence

- Hypothesis ID: `HYP-TRENDSTACK-EURUSD-H1-003`
- EA identity: `EA_TrendStackContinuation`
- Symbol / decision timeframe: `EURUSD / H1`
- Mechanism: long-horizon M252 time-series trend context multiplied by same-day
  06:00-12:00 six-H1 alignment. Agreement is the challenger; disagreement is a
  negative control.
- Parent HYP-002 terminal verdict:
  `PARK_ENGINEERING_INVALID_DESIGN_M1_PATH_GAP_NO_MARKET_VERDICT`.
- HYP-002 M1 run packet, failure manifest, 49 quarantine shards, and any
  HYP-002 M1 artifact are forbidden inputs.

Accepted parent feature evidence reused without recomputation:

- Stage-0 ledger:
  `03. EA Developer/EA_TrendStackContinuation/research/evidence/HYP-TRENDSTACK-EURUSD-H1-002_STAGE0/stage0_eligibility_ledger.jsonl`
- Ledger SHA256:
  `3092A6FCFADE0DA23E4470C4BF3B1D7750190358CF6ED09A2BB942937A7CD3C7`
- Stage-0 receipt SHA256:
  `5AEA570736361EF22BF2F090A5C05EF2974F482B5CB34A1186F27D9B43AAF5CE`
- Decision manifest SHA256:
  `D199E105CF6B51E0516D4FB57FFCB0D9AF63A72D8084B04BE6D73892ED7EA9DA`
- Decision receipt SHA256:
  `DA113E80157FFF69DBD11BB478637DC2DA3B9FD829102763250DA55D07773320`
- Decision packet-set SHA256:
  `22B0F111DCA293C0234C4C1D88F5A6E4CEABC7E7EE071466E310C9D0079F6E3E`
- Frozen DESIGN date-set SHA256:
  `4F30B5E09C8C21C3FCB63F4D5A016EB514D689710589077427464B92CD99A06A`
- Exact DESIGN opportunities: `1,297`, from `2016-01-04` through
  `2020-12-31`, requiring `466,920` exact M1 rows.

The mixed parent Stage-0 ledger is not a DESIGN evaluator capability. A trusted
ledger projector must create a physical DESIGN-only projection, preserve every
DESIGN row and field byte-for-byte under a new canonical wrapper, bind the
parent ledger/tool/receipt hashes, and emit no VALIDATION row, identity, count,
direction, exclusion, hash, path, or statistic. The evaluator receives only
that accepted DESIGN projection.

## 2. Source contract

Raw source identity:

- `02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_M1_2015_now.parquet`
- Bytes `104965845`
- SHA256
  `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`
- Root manifest SHA256
  `2CD996FD4416B1E888BF1C9D272BF49056DB3A4CE477CF74FA4E31D474A41B54`
- Clock tool SHA256
  `A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52`

The raw monolith is never a HYP-003 evaluator input. It may be decoded only by
the separately frozen mechanism-free data custodian:

`DATASET-FIVEPERCENT-EURUSD-M1-SPLITVAULT-001_PLAN.md`.

The custodian may decode the whole corpus once. Research validation and holdout
remain unopened because only the physical DESIGN capability is released. The
HYP-003 source gate may read only:

- the accepted custodian public DESIGN root/manifest/receipt;
- the accepted DESIGN-only parent Stage-0 projection;
- the frozen DESIGN date-set authority;
- the bound clock tool.

It may not read or enumerate the original monolith, source parent, HYP-002 M1
artifacts, custodian private/quarantine paths, VALIDATION, or HOLDOUT.

## 3. Frozen indicators and opportunities

- `M252 = sign(last valid daily close / close 252 valid UTC dates prior)`.
- `M6 = sign(close of the closed 11:00 H1 bar / open of the closed 06:00 H1
  bar)`.
- Decision time: `12:00 UTC`, using closed bars only.
- `ATR20`: MT5 simple average of the prior 20 closed H1 true ranges, shift 1.
- Arms: `CONTROL_M252_ONLY`, `CONTROL_M6_ONLY`, `CHALLENGER_STACK`, and
  `NEGATIVE_DISAGREE`.
- Frozen trials: `4`. Source preparation and engineering failures do not add an
  economic trial.
- Parent Stage-0 counts remain evidence only: DESIGN STACK `661` (`263` LONG,
  `398` SHORT); VALIDATION_FEATURE_ONLY STACK `267` (`82` LONG, `185` SHORT).

No threshold, direction, date, arm, hour, ATR, stop, cost, or gate may be
changed from HYP-002.

## 4. HYP-003 DESIGN source gate

The source gate writes create-new output only:

```text
02. AlphaFactory/data/fivepercent/EURUSD/trendstack_003_design_m1/
  design_request_plan.jsonl
  design_request_plan_receipt.json
  design_stage0_projection.jsonl
  design_stage0_projection_receipt.json
  raw_m1/DESIGN/YYYY-MM-DD/1201_1800.parquet
  design_m1_manifest.jsonl
  design_m1_source_receipt.json
  design_source_access_trace.jsonl
  design_source_reconciliation.json
  quarantine/<attempt_id>/...
```

For every one of the exact `1,297` frozen dates:

- require exactly `360` unique chronological UTC M1 opens from `12:01` through
  `18:00` inclusive;
- require exactly `466,920` rows in total;
- require exact M1 grid, server/UTC/offset round-trip, finite positive OHLC,
  and `low <= open/close <= high`;
- write one regular physical file with one row group per date/window;
- hash-bind bytes, canonical content, file set, request plan, projection, source
  access trace, reconciliation, and receipt;
- reject any missing/duplicate/outside-window minute or date;
- reject symlink, hardlink, junction, reparse, alias, path escape, identity swap,
  output overlap, overwrite, or partial publication.

The known `2016-03-11` gap is not special-cased. There is no fill, retry
widening, merge with quarantine, alternate source, interpolation, resample,
drop, dedupe, or date substitution. One missing minute invalidates the entire
source attempt before economics.

An independent validator must reopen and rehash every public DESIGN shard and
projection and recompute the exact full date-set before a source PASS. The
source receipt must distinguish:

- `custodian_full_corpus_decoded=true`;
- `research_validation_opened=false`;
- `research_holdout_opened=false`;
- `economics_opened=false`;
- `performance_trials_executed=0`.

Source PASS yields only
`SOURCE_READY_FOR_SEPARATE_DESIGN_ECONOMIC_RUN_PACKET`; it does not authorize
economic evaluation by itself.

## 5. Frozen sequential DESIGN economics — conditional and unchanged

Only a later create-new run packet, made after independent source acceptance,
may bind the final reviewed tool/test/source/projection hashes and authorize one
DESIGN evaluation.

- Entry: `12:01 UTC` M1 bid open.
- Stop: entry minus/plus `1.0 * ATR20` for LONG/SHORT.
- No take profit.
- Scan stops through `17:59`; if not stopped, exit at `18:00` M1 bid open.
- One opportunity per UTC date; no overlapping position.
- Round-trip proxy cost tiers: `1.50`, `2.25`, `3.00` pips, explicitly
  unverified and kill-only.
- Tie policy and gap policy remain exactly those frozen in HYP-002 Design plan.
- No spread column may be treated as verified cost truth.

All gates apply to `CHALLENGER_STACK` on DESIGN:

1. Cadence between `2.0` and `5.0` trades per elapsed calendar week.
2. Profit factor at 1.50 pips `> 1.30`.
3. Profit factor at 2.25 pips `>= 1.25`.
4. Profit factor at 3.00 pips `>= 1.00`.
5. Mean net R at 1.50 pips `>= 0.08` and total net R positive.
6. At least `4/5` DESIGN years have positive net R at 1.50 pips.
7. DSR `>= 0.95` across all four frozen arms.
8. Versus the better standalone control: PF delta `>= 0.15` and mean-net-R
   delta `>= 0.05` at 1.50 pips.
9. Versus `NEGATIVE_DISAGREE`: PF delta `>= 0.15` and mean-net-R delta
   `>= 0.05` at 1.50 pips.
10. Peak-to-trough drawdown proxy `<= 6%` under the frozen risk normalization.

No optimization, threshold rescue, subgroup, year/day/session veto, source
substitution, SL/TP/BE change, or post-outcome rule change is allowed.

## 6. Evaluator identity and capability

The HYP-003 evaluator may receive only the accepted HYP-003 DESIGN M1 shards,
DESIGN-only Stage-0 projection, frozen request plan, and frozen research tools.
It may not import MT5 or access the raw source, any HYP-002 M1 artifact, mixed
Stage-0 ledger, validation feature rows, validation/holdout vaults, source
parent, quarantine, or network.

Every output row must use:

- `hypothesis_id = HYP-TRENDSTACK-EURUSD-H1-003`;
- `parent_decision_contract = HYP-TRENDSTACK-EURUSD-H1-002`;
- `parent_stage0_ledger_sha256 =
  3092A6FCFADE0DA23E4470C4BF3B1D7750190358CF6ED09A2BB942937A7CD3C7`;
- stable `parent_opportunity_id`;
- `evaluation_id = HYP003::<parent_opportunity_id>::<arm>`.

## 7. Failure and continuation routing

- Custodian/source identity, capability, projection, physical partition,
  completeness, clock, schema, or reconciliation failure:
  `PARK_ENGINEERING_INVALID_SOURCE_OR_SEAL_NO_MARKET_VERDICT`; no economics.
- Any DESIGN economic, relative, year, cost, drawdown, or DSR gate failure:
  `KILL_DESIGN_NO_POSITIVE_EXPECTANCY`; no validation M1 and no rescue.
- All DESIGN gates pass: `PROBE_SURVIVOR_DESIGN_ONLY`; validation remains
  unauthorized until a separate frozen phase and registry transition.
- Any source hash/contract replacement after this freeze requires a fresh
  hypothesis ID. If local completeness fails, a separately preregistered
  external source such as Dukascopy is a new source-contract cell, not HYP-003
  substitution.
- No result from this plan authorizes MQL5, Model 0, promotion, paper, live, or
  deployment.

