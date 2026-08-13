# HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-009 - frozen engineering successor

Status: `TERMINAL_KILL_FROZEN_MAPPING`; all rerun, validation, optimization,
paper, promotion and live authority is revoked.

Timestamp reconciliation disproved the original pre-outcome sentence below:
the HYP008 PRIMARY report existed before this HYP009 preregistration was written.
HYP009 therefore cannot be treated as a fresh outcome-blind successor. Its
completed PRIMARY/REVERSE runs are retained only as a same-mapping engineering
confirmation of the already terminal economic failure.

Frozen after HYP008 failed the mandatory AlphaFactory D0-series proof and before any
HYP008 report, ledger PnL, return or economic metric was opened. HYP009 changes only
data provenance instrumentation: it emits the canonical read-only M5/M1 series proof
in `OnInit`. Signal, event table, timing, sizing, costs and economic gates are byte-for-
byte conceptually unchanged. The source-only `CopyTime` call cannot enter a decision.

## Hypothesis and population

- Source parent: `HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-007` reconciled source ledger, SHA-256
  `3B3B0F4CF85FD733B26DE0CA84F890265C94693DC7A58170507491985B2687B8`.
- Compile table: 329 clocks, 318 non-FLAT directions (162 BUY, 156 SELL), one
  source-invalid FLAT, eight ambiguous FLAT and two unavailable FLAT. Canonical table
  SHA-256 `BD2D3F6CF9C048F606F822EF2BEDF0C6DCA4CE6C25673A5235D70F8AC096A3DD`.
- Broker/tester: FivePercentOnline-Real EURUSD, M1 host, Model 0 every tick.
- DESIGN: exact 329 clocks in `[2019.01.01, 2021.01.01)`.
- Validation, holdout and later clocks remain sealed.

The thesis remains post-wave liquidity transfer: CME 6E levels 2-10 depth migration
after the first 15 seconds determines continuation versus reversal of the initial
aggressive flow over the following minute. No target-market price informed direction.

## Immutable execution

1. Use the exact HYP007 direction; zero means no trade. Score magnitude is unavailable.
2. Convert UTC using the frozen EU last-Sunday UTC+2/UTC+3 server-clock table.
3. Enter on the first valid EURUSD tick at or after T+60 seconds.
4. Exit on the first valid tick at or after T+120 seconds.
5. PRIMARY follows source sign; REVERSE changes only the sign.
6. One position maximum; missed boundary is a miss and rejection is never retried.
7. No filters, threshold, session, SL/TP, trailing, alternate hold or optimization.
8. Size `equity * 0.25% / (15 pips * pip value per lot)`, floor to broker step,
   cap at 1.00 lot. The 15-pip denominator is sizing only; there is no stop.

The canonical D0 proof reads only series metadata and one M5 timestamp at the first
available epoch during `OnInit`; failure aborts initialization. It is not referenced
by the signal, entry, exit, sizing or cost path.

## Frozen costs and gates

Complete cost is observed entry/exit spread and fill, USD 4.00 per lot round-trip
commission, plus adverse entry spread above the prior ten accepted-event median.
Report base, 1.5x and 2x complete-cost arms. The five known reduced-quality source
cells are diagnostic only and cannot rescue the primary verdict.

PRIMARY passes only if all gates hold: at least 300 completed trades; cadence 2.5-5.0
per week; base PF >=1.30 and expectancy >0; 1.5x PF >=1.25; 2x PF >=1.00 and
expectancy >=0; both 2019 and 2020 positive; max equity drawdown <=8%; REVERSE base PF
lower; and top 5% profit contribution <=30%.

Exactly one PRIMARY and one REVERSE attempt are authorized. Any failed engineering or
economic gate terminally kills this exact direction/T+60/T+120 mapping. No same-ID
retry, optimization, validation, paper/live execution or promotion is authorized.
