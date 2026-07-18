# GoldMacroPulse Storage Hygiene Receipt — 2026-07-16

- MT5 mode: portable; install, data, common-files and tester roots are physical
  `D:` paths.
- Probe-recorded terminal data path:
  `D:\Trading EA MT5\02. AlphaFactory\runtime\mt5-portable`.
- Workflow terminal processes started by the probe: 2 total across one
  implementation-error attempt and one completed evaluation; both stopped.
- Terminal process count at closeout: 0.
- Protected C roots:
  - `C:\Users\ADMIN\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\Tester`
  - `C:\Users\ADMIN\AppData\Roaming\MetaQuotes\Tester`
  - `C:\ProgramData\MetaQuotes\Tester`
- Before/after file counts, byte totals and metadata SHA256 were identical for
  all three roots. No run-owned C file existed to delete; files deleted: 0;
  bytes reclaimed from C: 0.
- Retained evidence is on D only:
  `20260716_GMP_C_STORAGE_BEFORE.json`,
  `20260716_GMP_C_STORAGE_AFTER.json`, and the hash-bound probe result.

Snapshot SHA256:

- Before: `21E9BD99671074628045B8337AB31D05BC71550C8992D66135FFEB14F64A2325`
- After: `D5FF1B2D06EC89786E5B08692510B28824C5E3637EEDE4E6A0CF0209E49559F1`
