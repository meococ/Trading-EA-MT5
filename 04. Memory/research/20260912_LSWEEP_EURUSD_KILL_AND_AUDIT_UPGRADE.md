# 2026-09-12 — CELL 9: EA_LiquiditySweep EURUSD M5 kill + non-repaint audit upgrade

## Result

| Field | Value |
|---|---|
| Hypothesis | HYP-LSWEEP-EUR-M5-001 (stop-sweep reversion, Osler 2003) |
| Runs | `20260912_085649` (journal-truncation fail) + `20260912_085955` (audit fail) + `20260912_090700` (complete loop end-to-end) |
| Window | 1999.01.01 → 2026.09.11 (`verified_m1_asof`) |
| History quality | **99%** |
| Trades | **172 — cadence 0.12/wk, FAIL outright** |
| Report PF / Net / DD | 0.68 / -887 USD / 10.0% |
| Cost PF x1.0 / x1.5 / x2.0 | **0.620** / 0.592 / 0.566 |
| MC p95 DD / Robustness | 19.9% PASS / 14.3% FAIL |
| Overnight / weekend | 0 / 0 PASS |
| Verdict | REVIEW → **KILLED_AT_MODEL_0** |

## Reading

The mechanism is real but unusable at the required cadence: true
bounded-penetration sweeps that close back inside salient levels printed
only 172 qualifying events across 27 years of EURUSD — 0.12 trades/week
against a 10–40/week band. Economics were also negative (PF 0.62 at
measured cost, WR 28.5%), so even a relaxed cadence gate would not save
the sleeve. No post-hoc rescue.

## Pipeline findings fixed this cell

1. **Journal-delta completeness gate vs verbose logging.** The EA's
   `InpVerboseLog` emits a reject line per non-qualifying bar — 491MB of
   tester journal, overflowing the 128MiB delta cap → `truncated=true` →
   fail. Fixed by pinning `InpVerboseLog=false` in the frozen overrides
   (log verbosity is not market logic).

2. **Non-repaint audit learned three provably-safe patterns:**
   - `iTime(sym,tf,0)` → `allowed_timestamp_only_read`: returns the
     forming bar's open *time* only; structurally cannot leak price. The
     canonical new-bar edge idiom.
   - Identifier shift arg with a dominating `if(param<1) return` guard
     earlier in the same function → `allowed_guarded_shift_param`.
   - Five-arg datetime-range `CopyRates/CopyTime` where both range args
     are `datetime`-typed and the stop arg is clamped to `iTime(>=1)`
     inside the callee → `allowed_bounded_datetime_range`.
   Regression tests: +5 cases in `test_nonrepaint_collection_probe.py`
   (13/13 pass).

3. **EA hardened to be provably closed-bar** (semantics-identical):
   - `LswClosedRangeHighLow` clamps `to` to `iTime(M5,1)` inside the
     callee — closed-only for any caller, not just today's guarded ones.
   - `LswPrevDayLevels` reads only shift-1 D1 with the equivalent
     close-time guard (`d1[0].time + PeriodSeconds(D1) > sweep_time`),
     replacing the forming-bar read whose only use was `.time`.
   - `LswAtrAt` guard `shift<0` → `shift<1` (callers pass 1/2 only).
   - Added standard lifecycle telemetry + D0 series proof; `InpRoundStep`
     pinned 0.0050 for EURUSD per the contract table; `InpMagic` rebound.

4. **Packet builder:** new `--extra-overrides` arg so frozen EA inputs
   beyond telemetry/magic (e.g. `InpRoundStep`, `InpVerboseLog`) are
   bound into the task packet's `overrides` field instead of silently
   diverging from the CLI.

## Cell tally (9 kills, 0 passes)

CRSI-R2 GBPUSD (data) · AMA XAU · VwapFade XAU · HourDrift XAU ·
GBBSqueeze XAU · IBSC EURUSD · CamarillaFade EURUSD · H1D EURUSD ·
**LiquiditySweep EURUSD**.

Pattern: 4/4 EURUSD mechanisms dead on economics regardless of the
cheapest spread venue; rare-event microstructure edges (sweeps) cannot
meet the scalping cadence band on M5. Remaining untested classes on
EURUSD: session opening-range fade (ORFade), inside-bar break (IB_M15),
higher-frequency level fades (Woodie/Piv3/Pdc), or a different symbol
with real tick economics.
