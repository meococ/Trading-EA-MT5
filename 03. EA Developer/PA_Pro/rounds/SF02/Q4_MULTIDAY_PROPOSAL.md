# Q4 — Multi-day referee proposal (proposal only; NO lib/ code)

## Why it is warranted

A1 (referee, ledgered) shows intraday flats are the binding constraint
on the exit axis for the matched-random baseline itself:

| S | tp | PF | exp_r | TP share | DAILY+FRIDAY share |
|---|---|---|---|---|---|
| 55 | 2.0 | 0.940 | -0.0156 | 2.5% | 82.7% |
| 55 | 3.0 | 0.940 | -0.0157 | 0.6% | 84.3% |
| 75 | 2.0 | 0.939 | -0.0119 | 1.0% | 91.7% |
| 75 | 3.0 | 0.935 | -0.0127 | 0.2% | 92.3% |

Once S >= ~55 pips, the fixed-R target essentially never reaches before
22:00-UTC daily flat — the trade is killed by the calendar, not by the
market. A2 showed momentum entries (F5/F6) carry positive exit-free
edge (+0.15..+0.42 edge-ratio delta) that the flats destroy. A
multi-day referee is the only honest way to separate "no entry edge"
from "edge eaten by forced flats".

## Proposed referee changes (new module or flag, never edited mid-round)

`pa_fill.simulate` gains an opt-in `multiday` spec flag:

- `daily_flat` disabled; `friday_flat` kept but moved to a configurable
  `weekly_flat_hour` (default Friday 20:00 UTC — still needed: holding
  over the weekend is a different risk, see gaps below).
- Positions may span multiple sessions; `max_hold` cap in bars or days
  (e.g. 5 trading days) replaces the day-flat as the time-stop.
- Determinism unchanged: same M1 fill path, same seed handling.

## Swap / rollover cost model

Flat-to-flat holding overnight incurs swap (tom-next). Proposal: apply a
per-overnight charge in pips at 22:00 UTC (broker rollover time) per
symbol per direction, sourced from a conservative static table the Lead
supplies (design box must not fetch live swap). Charging a fixed
pessimistic swap (e.g. 0.3-1.0 pip/night, signed by direction) keeps the
test honest: a strategy that only survives with zero swap was never
real. Report `swap_paid_total` per run so the drag is visible.

## Weekend gaps

Two honest choices, both to be reported:

1. `weekly_flat` (default): flat by Friday 20:00 UTC — no gap exposure,
   but the week-end chop still truncates wide-S trades.
2. `allow_weekend`: position held over the weekend; M1 resumes Monday
   — the gap is real data in the series and the fill model already
   handles jumps at the Monday open. The proposal recommends reporting
   variant 1 as primary and 2 as a sensitivity, NOT trading variant 2
   by default (gap slippage on a fixed-R stop can exceed 1R and is
   unmodelled in this simulator — first gap bar fills at open, SL
   distance honoured only approximately).

## Tests against ECON-1

ECON-1 = the frozen random-baseline economics test the referee must
keep passing. Required assertions before any multiday run is accepted:

1. Matched-random entries under `multiday` show exp_r ~ -(costs +
   swap), i.e. the baseline stays honest-negative, never positive.
2. Determinism: same spec + seed reproduces identical trades
   (replay test as in the A1 patch: PF equal to >=7 decimals).
3. A1 drag curve re-run under multiday: PF(S, tp) with flats removed
   must still be < 1.0 at all rungs — if random reaches PF >= 1.0
   under multiday the exit model is broken, not generous.
4. The intraday A1 numbers must remain reproducible with `multiday`
   off (regression: existing ledger rows unchanged).

## What it would buy SF02-style families

- G4's tp_mult sweep at S>=40 currently measures "did the calendar let
  the TP exist" more than "did the entry have edge".
- F5/F6-type momentum entries showed real exit-free edge; under
  multiday, TP at 2-3R becomes reachable — the only honest test of
  whether that edge survives exits.
- Nothing in this proposal touches entries, zones, or salience — it is
  purely the exit referee.
