# HYP-STBS-XAUUSD-M15-010 — Existing-run comparator recovery preregistration

Status: `FROZEN_PRE_EXECUTION`

## Thesis and exact scope

HYP010 is a comparator-only engineering child of terminal `HYP-STBS-XAUUSD-M15-009`. HYP009 completed exactly one no-trade AlphaFactory Model-0 run (`20260809_181119`) but consumed its sole outer attempt when a frozen regex rejected the valid MetaEditor timing/CPU suffix before full manifest, data-quality, report, journal and ST003-oracle parity validation.

This child does not modify the EA, compile it, launch MT5, rerun AlphaFactory, inspect post-trade outcomes or estimate economics. It may only re-open the exact hash-bound HYP009 run and complete the previously frozen correctness checks.

## Frozen dependency and failure radius

- Parent terminal row: `HYP-STBS-XAUUSD-M15-009`, raw SHA256 `100610B9EC9D4383E9EEA892AC7254EF43DAD2015BE51AA0764465B4837508A3`.
- Parent terminal verdict: `KILL_EXACT_RUNNER_COMPILE_LOG_SUFFIX_FALSE_REJECT_AFTER_MT5_NO_PARITY_NO_ECONOMICS`.
- Frozen parent runner SHA256: `AFFD1823BBEA9833C6C7D4844A829135277E808A2114142BBA28BE4AA0100E42`.
- Frozen ST003 oracle SHA256: `63E93022794C6DD50EBFB4464DD521D4B1757C5797B158121467F18FF2F13096`.
- Exact run directory: `02. AlphaFactory/runs/EA_SupertrendBurstScalperTradeV2/20260809_181119`.
- No parent file may be amended. No HYP009 attempt may be retried.

## Exact compile-result recovery rule

Decode the immutable HYP009 run compile-log archive. It must contain exactly one line beginning `Result:` and that whole line must match:

`Result: <errors> errors, <warnings> warnings, <elapsed_ms> ms elapsed, cpu='<cpu>'`

Acceptance requires `errors=0`, `warnings=0`, `elapsed_ms` a positive base-10 integer and `cpu` exactly `X64 Regular`. A bare legacy line, duplicate `Result:` line, suffix junk, missing/zero/negative/noninteger elapsed time, changed CPU, nonzero errors or warnings fails the sole HYP010 attempt.

After that narrow recovery predicate passes, the comparator must run every unchanged HYP009 run gate: exact manifest schema/identity/window/Model0/control role/deposit/leverage/current spread/nonvisual/no indicators/no required sidecars; canonical snapshot/staged EX5/config paths and hashes; exact config semantics; source and receipt identity; HQ >97, fixed-window bounds, journal binding and M5 series proof; exact zero-trade summary; exact empty Orders HTML shape; exactly one tester-start funding Deal; no trade/runtime records; normalized identical journal multiplicity; 690 raw, 683 executable, 7 gaps, 339 LONG, 344 SHORT, 683 ATR-ready and 683 geometry-ready events; exact ST003 UTC/server-axis/direction/exact-next identity.

## One-shot and read-order contract

- Sole attempt ID: `STBS010-COMPARATOR-001`, limit 1.
- Canonical evidence root must not exist before authorization.
- The canonical evidence root has exactly one repository `.gitignore` rule; the authority and receipt bind the exact `.gitignore` path and SHA so start/report/receipt/terminal artifacts do not create unreviewed worktree path drift.
- The comparator must create and fsync `attempt_started.json` exclusively before reading the registry, parent runner, oracle, run manifest, report, journal, summary, config, EX5, source, failure documents or review artifacts.
- Success writes an immutable report, receipt and terminal. Failure writes only the durable start plus a failure terminal and consumes the attempt. Same-ID retry is forbidden.
- Deterministic replay must execute the complete recovered validation twice and produce byte-identical report payloads while all bound input hashes remain unchanged.

## Authority boundary

The screened row may authorize only artifact collection and comparator execution. MT5, source run, compile, run-compile, trade API, outcomes, post-event OHLC, performance metrics, economics, optimization, validation, holdout, falsification, promotion, paper and live trading, network/paid access, same-ID retry and registry mutation all remain false.

Pass verdict: `ENGINEERING_VALID_STBS009_MODEL0_SIGNAL_ATR_GEOMETRY_PARITY_RECOVERED_NO_TRADES`.

A pass proves only engineering parity for the exact no-trade HYP009 run. It does not establish expectancy, PF, cost realism, risk robustness, OOS validity or deploy readiness. Any economic child requires a fresh ID, preregistration and authority after terminal closeout of HYP010.
