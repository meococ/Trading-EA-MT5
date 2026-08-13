# HYP008 pre-Model-0 review

Review scope: frozen source/table binding, executable timing, audit coverage and
economic acceptance only. No EURUSD outcome, report or return was inspected.

## Result

- Engineering gate: PASS. `EA_EventDepthTransfer.mq5` compiles through
  AlphaFactory with 0 errors and 0 warnings.
- Source identity: PASS. The EA binds the independently reconciled HYP007 ledger
  SHA-256 `3B3B0F4CF85FD733B26DE0CA84F890265C94693DC7A58170507491985B2687B8`
  and canonical 329-clock table SHA-256
  `BD2D3F6CF9C048F606F822EF2BEDF0C6DCA4CE6C25673A5235D70F8AC096A3DD`.
- Timing/no-lookahead gate: PASS. The EA does not call bar/indicator copy APIs;
  decisions use the frozen source table and `MqlTick.time_msc`. Entry and exit
  are fail-closed at the first tick on or after T+60 and T+120 respectively.
- Accounting gate: PASS by source inspection. Every event is written exactly once
  to the audit ledger, including the eleven frozen zero-direction events.
- Comparator gate: PASS by construction. PRIMARY follows the frozen sign and
  REVERSE changes only `InpReverseComparator`.
- Cost gate: PASS by specification. Base, 1.5x and 2x arms include the same frozen
  commission, observed spread/fill and adverse entry-spread formula.

## Authorization boundary

Exactly one PRIMARY Model-0 and one REVERSE Model-0 are authorized on FivePercent
EURUSD M1 for `[2019.01.01, 2021.01.01)`. No optimization, parameter variation,
same-ID retry, validation, holdout, paper/live execution or promotion is authorized.
If any frozen DESIGN gate fails, this exact direction/T+60/T+120 mapping is terminal.

