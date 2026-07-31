# HYP-004 GFI integrated readout

> **ERRATUM:** The five-case chart observations below were rendered on an
> uncorrected chart clock and are invalid as visual evidence. They do not
> change the MT5 economics or terminal kill. Use
> `HYP004_RANDOM100_TIMEBASE_ERRATUM.md` and
> `HYP004_RANDOM100_GFI_CLOCK_V2_READOUT.md` for the corrected 100-case,
> 200-image chart-forensics record.

Reviewer role: read-only/advisory. Parent Codex owns reconciliation and verdict.

## Runner acceptance

- Attempt 1 is rejected: Grok exited with stop reason `Cancelled`, produced no
  useful final answer and tried to create an unapproved helper script.
- Retry is accepted: model `grok-4.5`, reasoning `high`, exit code 0, stop
  reason `EndTurn`, useful response true, nine turns.
- Accepted response:
  `.context/scc-hyp004-gfi-review/run2/grok-response.json`
  SHA256
  `5E456722B1A5FDF9851597820BA3F7CF32208549A3C17F05D7F8C35401140E28`.
- Accepted runner summary:
  `.context/scc-hyp004-gfi-review/run2/summary.json`
  SHA256
  `069315014A76F4DB90D9D791B69698ADDD0F0617E28E713B5DA0AAFE0487AC21`.

## Coverage validation

The reviewer opened all five requested anatomy PNGs and returned each exact
case ID:

1. `CHALLENGER_SELL_TP_20200318`
2. `CHALLENGER_BUY_TIMEOUT_20200610`
3. `CHALLENGER_BUY_TP_20201117`
4. `CHALLENGER_SELL_SL_20211124`
5. `CHALLENGER_BUY_SL_20220111`

Coverage verdict: `5/5 IMAGE_OPENED`.

## Accepted findings

1. **Negative payoff geometry is the dominant failure (HIGH).** Control and
   challenger both have PF near 0.69 and mean realized R near `-0.22R`.
   Observed win rates remain materially below the breakeven rate implied by
   realized average win/loss.
2. **HOLD to RETEST destroys sample without discrimination (HIGH).** The
   challenger converts only 261 of 1,240 BREAK arms into fills and falls to
   1.251 trades per elapsed week, but PF and mean R do not improve versus
   control.
3. **Tight invalidation plus cost amplifies the loss (MEDIUM-HIGH).** Open
   commission averages about `-$1.23` per challenger trade against roughly
   `$10` planned risk. Fixed additional 1.5-pip stress reduces challenger PF
   to 0.354.

The reviewer independently accepted the recovery of four control rows whose
lifecycle risk fields were zero. Each row has a unique ORDER_ACCEPTED decision
match on direction, entry, time and stop. The correction changes only the R
denominator; deal P/L, native PF and the kill verdict are unchanged. The
underlying single-global telemetry binding remains an engineering defect.

## Parent reconciliation

The reviewer output is accepted after these boundaries:

- Chart observations illustrate path anatomy and are not population proof.
- The five cases do not authorize an H1, session, weekday, hour or year filter.
- The generic session analyzer calling all trades `Asia` is a clock bucket,
  not evidence that another session works.
- The accepted review grants no patch, rerun, promotion or live authority.
- Suggested future work is idea-level only. Any continuation needs a new
  mechanism, hypothesis ID, preregistration and fresh evidence.

Integrated verdict:
`GFI_ACCEPTS_KILL_VALID_MATCHED_PAIR_NO_POSITIVE_EXPECTANCY`.
