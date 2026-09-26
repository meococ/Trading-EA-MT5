# G4 status — HALTED by LEAD_RULINGS Review 1

SPEC + prereg T000346 exist (sha c62fd290). A 24-cell screen was
launched at ~07:12Z and killed at 5/24 cells when the Review-1 pause
(06:01Z) was discovered on re-read — Q2 screens require P-FREEZE first.

The 5 evaluated cells are ledgered (family `g4_g1_exit_axis` +
`g4_g1_exit_axis_rand`) but are EXPLORATORY on unfrozen perception and
must not feed promotion. Partial console results (S18 rows): tp1 PF
0.913 > tp2 0.869 > tp3 0.781 — direction suggests the exit axis
matters, but nothing here is a verdict.

When P-v1 freezes: re-spec on the Snapshot API, re-prereg, re-run.
This folder keeps SPEC.md/QA_CHECKLIST.md/CENSUS.json/snapshots as
historical record of the unfrozen-perception draft.
