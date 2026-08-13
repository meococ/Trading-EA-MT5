# Grok SonicR v10 local audit - 2026-08-12

## Purpose and evidence boundary

The active Grok Build conversation supplied `SonicR_MT5_QUALITY_v10.zip` as a
possible implementation package. This audit answers only whether that package
is a lawful active candidate for the current closed-M5/M15, 2018-latest MT5
goal. It does not judge the profitability of an untested repaired strategy.

No supplied script was executed. The EA was not installed, compiled or
backtested. Source and package metadata were inspected before execution, as
required for externally supplied code.

## Acquisition identity

- Downloaded artifact SHA-256:
  `77709C82212FACD6DF4F74C31A6EBD1581DEB033DECF60C03EC5C3494EA921DA`.
- Downloaded size: `158,707` bytes.
- Local inspection root:
  `02. AlphaFactory/scratch/grok/sonicr_quality_v10_77709c82_20260812`.
- EA source:
  `sonicr/mql5/SonicR_Enhanced.mq5`.
- EA source SHA-256:
  `421E7C58CE8279E1D135459AFE5B9AC777F38D38EF64C4F048A438192B72EA30`.
- The ZIP contains 76 entries but has a Windows case-insensitive collision:
  `sonicr/OPERATOR_HANDOFF.md` and `sonicr/operator_handoff.md`. Standard
  extraction therefore materialized 75 of 76 entries. This is a packaging
  defect; it does not change the source verdict.

## Goal and evidence mismatch

1. The EA describes itself as `H1 QUALITY` and all supplied symbol presets are
   H1 presets. The current goal requires decisions and management on closed M5
   or M15.
2. `PRODUCTION_FREEZE_v10.md` explicitly limits the free yfinance H1 history to
   about 2.5-2.8 years and says it is not a ten-year claim. This cannot satisfy
   the current broker-native 2018-latest evidence contract.
3. The freeze document names `pair_configs.py`, `engine_enhanced.py`,
   `walk_forward.py`, `run_all.py` and `summary.json` as the reproducible
   pipeline, but none is present in the delivered ZIP. The included
   `reproduce_wf_v10.json` has an empty `oos_pfs` array for every symbol and no
   trade ledger. Narrative/JSON metrics are not locally reproducible economic
   evidence.
4. The presets encode selected session/hour blocks, ADX, chase and cooldown
   settings. Those are not transferable proof of a new mechanism and overlap
   already terminal Sonic/Dragon/context/filter rescue families.

## Source-critical defects

The following defects are sufficient to stop before compile/backtest:

- `TryEntry` copies four Dragon values but default/preset
  `InpSlopeBars=3` then accesses `mid[1 + InpSlopeBars]`, i.e. `mid[4]` in an
  array whose valid indexes are 0-3.
- `HTFAllows` reads the current unfinished higher-timeframe value `mid[0]` and
  returns `true` when `CopyBuffer` fails. This is both a lookahead/repaint risk
  and fail-open behavior.
- `OnTradeTransaction` does not bind the received deal to this EA's symbol,
  magic number, position ID or exit role. An unrelated account deal can reset
  the state/cooldown.
- Position close, partial-close and modify calls are made by `_Symbol` rather
  than the exact owned ticket. This is unsafe with hedging or multiple EAs on
  the same symbol.
- The package has no required frozen hypothesis ID, AlphaFactory EA contract,
  Friday/overnight lifecycle gate, state reconciliation or complete execution
  telemetry.

## Verdict

`NOT_A_CANDIDATE_ENGINEERING_DONOR_ONLY`

Grok accepted this corrected verdict in the active conversation. The package
must not be installed under the EA shelf and must not consume a Model-0 run.

Potentially reusable only after independent repair and review:

- the general EA host layout;
- the deal-CSV and parity-kit concepts;
- the operator/freeze document structure;
- a neutral `.set` key layout for a genuinely fresh hypothesis.

Not reusable as edge evidence:

- the Dragon/session/hour/ADX/chase/cooldown recipe;
- free-H1 yfinance WFA numbers;
- the incomplete reproducibility bundle;
- any H1 result transferred to M5/M15.

