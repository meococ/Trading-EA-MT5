# HYP-CFTC-FX-H1-001 — Storage Closeout

- Before snapshot SHA256:
  `F1D3B95C3FDBBC18BA11193796A0B77B7F46C4E283DAC71AD63CB0B845BEACBF`.
- After snapshot SHA256:
  `DC4FA3379B685BCE8C6FFEF6B49D5594618221C11FB70522763FBDB5CAD290E0`.
- The snapshot-file hashes differ only because `generated_at_utc` differs.
- All four root records are identical before/after by root, existence,
  file count, total bytes, latest write UTC and metadata SHA256.
- Portable MT5 terminal/data path in the probe artifact is on `D:`.
- `commondata_path` reports the MT5-designed C Common root, but the probe uses no
  `FILE_COMMON` and that root remained identical.
- MT5 was stopped after evidence capture. Zero C-drive files were deleted.

Verdict: `PASS_D_PORTABLE_ALL_FOUR_C_ROOTS_IDENTICAL_ZERO_DELETE`.
