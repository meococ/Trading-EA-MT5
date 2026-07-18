# C-root storage delta note — Stage B0 data pull (2026-07-17)

Context: read-only EURUSD H1/H4/M1 history pull through the installed C
terminal (`C:\Program Files\MetaTrader 5\terminal64.exe`, FivePercentOnline-Real
demo, AutoTrading off, no orders, no Strategy Tester run). Terminal was
launched 4x by `mr_pull_bars.py` / identity checks and shut down after each.

Snapshot comparison (`20260717_MR_C_STORAGE_BEFORE.json` vs `_AFTER.json`):

| Root | Before | After | Verdict |
|---|---|---|---|
| Terminal\Common\Files | 137 / 20,008,308 B | 137 / 20,008,308 B | **IDENTICAL** (hash match) |
| Terminal\D0E8...\Tester | 120 / 1,260,063,754 B | 119 / 1,260,063,646 B | −1 file / −108 B |
| Roaming\MetaQuotes\Tester | 882 / 6,847,158,854 B | 881 / 6,729,439,454 B | −1 file / −117,719,400 B |
| ProgramData\MetaQuotes\Tester | absent | absent | IDENTICAL |

Assessment: the two Tester-root deltas are **file removals, not additions**,
performed by MT5's own startup housekeeping (tester journal/cache pruning).
No workspace command wrote to or deleted from any protected root; the data
pull touches only `bases\FivePercentOnline-Real\history\` and the D-side
evidence folder. Nothing referenced by hot.md/registry lives in the pruned
files (no run evidence is stored under C Tester roots per D-portable policy).

Additional documented C-side change (outside the 4 protected roots):
`bases\FivePercentOnline-Real\history\EURUSD\2026.hcc` grew +124,038 bytes
(live-bar append during the pull; appended proprietary records cannot be
separated from shared history → protected, not deleted, per hot.md C-drive
tester hygiene precedent). No new `.hcc` files were created
(`20260717_C_EURUSD_HCC_BEFORE.txt` vs `_AFTER.txt`: 56 files before/after).

Limitation: the `alphafactory_mt5_storage_snapshot.v1` receipts store
aggregate metadata only, so the identity of the two pruned Tester files is
not recoverable from the BEFORE receipt. The snapshot script has been
upgraded to embed per-file metadata for all future receipts.
