# G4 QA checklist

Entry logic is `g1_htf_pullback.detect` imported verbatim — G1's
adversarial tests (prefix invariance, future mutation, warm-up, touch
tolerance, inv semantics) cover the detector; `python -m pytest
families/test_g1_htf_pullback.py` is the suite (10 tests, green
2026-09-21).

Visual QA: G1 snapshots validate entry/inv placement
(`rounds/SF02/g1_htf_pullback/snapshots/`). G4 snapshots re-render the
same signals to check the EXIT side changed only:

- [ ] not a chase — limit order sits AT the proximal zone edge
- [ ] zone is salient — at most 1-2 armed bands near price
- [ ] stop at real structure — SL beyond deeper of far edge / pullback extreme
- [ ] S=55 cells: SL/TP visibly wide (rung-2 geometry exercised)
- [ ] tp_mult axis: TP distance scales 1x/2x/3x for identical entries
- [ ] box visibly tight — N/A (no box in this family)
