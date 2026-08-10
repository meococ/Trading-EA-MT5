# HYP-STBS-XAUUSD-M15-011 — Exact summary-BOM comparator preregistration

Status: `FROZEN_PRE_EXECUTION`

## Exact thesis

HYP011 is a comparator-only engineering child of terminal HYP010. HYP010 corrected the frozen compile-result suffix parser and validated authority, source/run bindings, compile, config, manifest and data-quality/M5-series proof, but its sole attempt stopped because the unchanged parent validator decoded an exact UTF-8-BOM summary with `encoding="utf-8"`.

HYP011 changes only decoding of the exact frozen zero-trade summary. It does not modify the EA, rerun AlphaFactory, launch MT5, compile, inspect trade outcomes, calculate performance or open economics.

## Frozen lineage

- Terminal HYP010 row raw SHA256: `D951D4D552BD8BFE4CE197047647FCDD99DA825FA605001B81727634EF26AD74`.
- Terminal HYP010 verdict: `KILL_EXACT_ZERO_TRADE_SUMMARY_UTF8_BOM_DECODER_NO_PARITY_NO_ECONOMICS`.
- Frozen HYP010 comparator SHA256: `6B5357466E5EC6D17375C6F6D8D5BE2B421CC2B70E1EB223226CD15A7EAD564A`.
- Frozen HYP009 runner SHA256: `AFFD1823BBEA9833C6C7D4844A829135277E808A2114142BBA28BE4AA0100E42`.
- Exact run: `02. AlphaFactory/runs/EA_SupertrendBurstScalperTradeV2/20260809_181119`.
- Exact summary SHA256: `E546E60F4587CE4572AE7526BAABC737F8A65FAF7542A96359A092E893C8DA47`.
- Exact ST003 oracle SHA256: `63E93022794C6DD50EBFB4464DD521D4B1757C5797B158121467F18FF2F13096`.

## Exact decoder revision

Only the canonical hash-bound `analysis/enhanced_summary.json` may use the recovery decoder. Its bytes must:

1. begin with exactly one `EF BB BF` sequence;
2. contain no second or interior UTF-8 BOM;
3. decode strictly as UTF-8 after removal of that one prefix;
4. parse as exactly one JSON document with no trailing second document or non-whitespace junk;
5. retain the unchanged HYP009 zero-trade summary schema, `n_trades=0`, and `performance_metrics_authorized=false` gates.

The decoder must not affect any other path. Absent/double/interior BOM, invalid UTF-8, wrong path/hash, malformed JSON or trailing JSON fails the sole attempt.

## Unchanged full acceptance

After the exact BOM recovery, execute every unchanged HYP010/HYP009 gate: structured compile result; manifest/config/path/hash/sidecar/geometry identity; HQ >97 and fixed history/M5 series proof; zero-trade summary; exact empty Orders section and sole funding balance row; no forbidden runtime/trade records; normalized duplicate journal multiplicity; exact counts 690 raw, 683 executable, 7 gaps, 339 LONG, 344 SHORT, 683 ATR-ready and 683 geometry-ready; exact ST003 UTC/server-axis, direction, exact-next and geometry parity.

Run the complete analysis twice from unchanged inputs, require byte-identical output/bindings, and rehash all bound inputs immediately before sealing the receipt.

## One-shot and authority boundary

- Sole attempt ID: `STBS011-COMPARATOR-001`, limit 1.
- The exact evidence root has one `.gitignore` rule and must be absent at authority time.
- Create and fsync the exclusive attempt marker before reading registry, HYP010/HYP009 code/evidence, run files, summary, oracle or review artifacts.
- Success emits report, receipt and terminal; failure emits start plus failure terminal and consumes the attempt. Same-ID retry is forbidden.
- Only artifact collection and comparator execution may be true. MT5, source-run, compile, run-compile, trade/outcomes/post-event OHLC, performance, economics, optimization, validation, holdout, falsification, promotion, paper/live, network/paid, retry and registry mutation remain false.

Pass verdict: `ENGINEERING_VALID_STBS009_MODEL0_SIGNAL_ATR_GEOMETRY_PARITY_RECOVERED_NO_TRADES`.

That verdict is engineering parity only. It does not establish PF, expectancy, transaction-cost validity, robustness, OOS validity or deploy readiness.
