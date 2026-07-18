# HYP-GLDFLOW-XAU-M15-001 — Readout

Verdict: **KILL_AT_SCHEMA_CONTRACT**  
Outcome access: **NONE**  
EA/source/compile/Model 0: **NOT AUTHORIZED**

The frozen official workbook hash matched, but its header surface contains
`Date`, `Ounces of Gold per Share`, `Total Ounces of Gold in the Trust`, and
other NAV/price fields; it does not contain the preregistered official
`Total Shares Outstanding` field. The prereg explicitly required that field
and prohibited substitution, so HYP-001 stops before any workbook data row,
XAU bar, signal count, trade outcome, or 2025+ row was read.

This is an operational schema failure, not evidence for or against the primary
creation/redemption thesis. A deterministic derived-shares mapping can only be
tested under a fresh hypothesis frozen before outcome access.

Evidence:

- workbook SHA256:
  `8E7F1DA21C7169D1950F865731817E191E897E650454F9FA37AE5AD1CBD08C38`
- prereg SHA256:
  `69A09943151510A48ABD1FF4F3D8392906E739B7026D3514A57CBDB9CE80B600`
- protected-C/terminal mutation: none; MT5 was not initialized for this check.
