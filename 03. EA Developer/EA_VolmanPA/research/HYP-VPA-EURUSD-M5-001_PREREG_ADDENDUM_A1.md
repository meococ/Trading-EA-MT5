# PREREG ADDENDUM A1 — registry state clarification

Date: 2026-09-20 · Author: OpenCode worker · Append-only note.

The frozen prereg `HYP-VPA-EURUSD-M5-001_FROZEN_PREREG.md`
(SHA256 `A81F43D735F2139751B50E98F39908D0FF7A889CDAB76FF9DE3F76A46CBDE09C`)
carries the status line `SCREENED`. The live registry row is:

- `04. Memory/research/CANDIDATE_REGISTRY.jsonl`, row 47,
  `HYP-VPA-EURUSD-M5-001`, **state=`probe`**,
  verdict `PROBE_P1_GATE_PASS_PENDING_P2_CENSUS`.

Reason: `validate_candidate_registry.py` requires a hash-bound canonical EA
source (`03. EA Developer/EA_VolmanPA/EA_VolmanPA.mq5`) for every execution
state (`screened`, `challenger`, `confirmed`, `portfolio-sleeve`). That file is
a P4 deliverable and does not exist yet, so a `screened` row would make the
append-only ledger fail validation. `probe -> screened` is a legal transition,
so the row will be advanced to `screened` when the MQL5 package exists (with its
real source hash).

This addendum does not change any frozen content of the prereg: the hypothesis
contract, splits, geometry (S=8, London primary), lift gate and KILL rules stand
exactly as frozen. The word `SCREENED` in the prereg's status line is to be read
as "screened for execution by the P1 gate", not as a claim about the registry
state word.
