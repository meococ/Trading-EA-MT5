# HYP-ICT-FVG-FIDEXEC-EURUSD-M5-003 - engineering readout

Verdict: **PARKED_PRE_MODEL0_COST_PROVENANCE_FAILED**

## What changed

The ordered report-fidelity signal, every threshold, news guard, sessions,
entry, SL, TP and management geometry are unchanged from the outcome-free
parent `HYP-ICT-FVG-FIDNEWS-EURUSD-M5-002`.

The execution layer now:

- preserves the consecutive-loss streak and cooldown across UTC day rollover;
- persists position-bound initial risk, planned money risk, lifecycle net and
  emergency-close state with a lossless two-word position identifier;
- rebuilds lifecycle net P&L from all deals sharing the exact position ID after
  restart and before final loss classification;
- counts an opened lifecycle and daily trade only on its first actual entry
  deal, validates the server retcode and blocks duplicate sends while an owned
  pending order exists;
- calculates fill risk from the position's volume-weighted entry price;
- retries an excess-fill-risk close on every tick and after restart; and
- closes fail-safe when the original risk geometry cannot be reconstructed.

## Evidence

- Source SHA-256:
  `75EA4B7D8394CCEC6BA5E13643A4340CFAA594BA7934250EC7C5C6D92B3D6541`.
- AlphaFactory compile: **0 errors / 0 warnings**, EX5 76,640 bytes, SHA-256
  `8AEAF0B79313D8E6EEAC1487C494B47DAEC499929C8F935A348C1F498854E72E`.
- Package tests: **19/19 PASS**, including complete receipt hash validation.
- AlphaFactory non-repaint audit V6: **PASS**, zero findings; bar zero is used
  only as the explicit new-M5-bar clock.
- Source/binary receipt V4 SHA-256:
  `6EEBC97733E99B242C74FD7E9E0673326B4C8E097EFF189ACB9DBBA8255E687C`.
- The failed V4 static-audit iteration is retained. Its only finding was the
  auditor-unrecognized combined new-bar guard; the semantically equivalent
  split guard passed V5 and the final V6 exact-source audit.

## Economic boundary

No Strategy Tester outcome, trade ledger, PF, expectancy, cadence, drawdown or
holdout data was opened for this child. The FivePercent spread export still has
366,196 zero-spread rows out of 1,491,312, while verified commission and
direction-aware slippage remain absent. Therefore `model0_authorized=false`,
`promotion_eligible=false`, and the strategy's economic verdict remains
**UNTESTED** rather than superior or inferior.

Unlocking economics requires verified same-broker historical spread, at least
30 commission-bearing completed lifecycles and at least 100 direction-aware
fill/slippage observations. The next legal economic attempt must use a fresh
child ID because this record is terminal parked.
