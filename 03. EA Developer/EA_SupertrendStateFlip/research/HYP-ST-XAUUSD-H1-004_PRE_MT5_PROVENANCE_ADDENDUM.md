# HYP-ST-XAUUSD-H1-004 — Pre-MT5 provenance addendum

Status: `FROZEN_V2_BEFORE_MODEL4_PACKET_REBUILD`

This addendum does not alter the H1 Supertrend formula, source, compiled EX5,
test window, oracle, expected counts, or any economic permission. It closes one
operational contradiction discovered after the sole static compile and before
any MT5 attempt.

`AlphaFactory` validates the execution receipt against
`git status --short --untracked-files=all` at process entry. The HYP004 launcher
must first create and fsync `ST004-MT5-001/attempt_started.json`; without a
narrow ignore rule, that mandatory one-shot marker would change the signed Git
snapshot and make every otherwise-valid receipt fail deterministically.

The repository `.gitignore` therefore excludes only:

`03. EA Developer/EA_SupertrendStateFlip/research/evidence/HYP-ST-XAUUSD-H1-004/ST004-MT5-001/`

The exclusion is provenance-neutral:

- it does not exclude the EA source, preregistration, packet, receipt, compile
  archive, non-repaint audit, tests, launcher, collector, or comparator;
- the launch marker, stdout/stderr, receipt and terminal remain exclusive,
  fsynced and mutually hash-bound by `run_st004_mt5_parity.py`;
- the exact attempt directory will be force-added when the terminal evidence
  packet is committed;
- no file may be deleted or overwritten to obtain a retry.

The sealed `ST004-COMPILE-001` result remains the only HYP004 compile attempt:
source `C8C222487769439DC8FB9272C049BE30928FED5315A64DD1CAD440B500A13D02`,
EX5 `0C68520D3C3B073939B8A4FF403575687E93739E1A9844B6B051E85011F84982`,
log `3CF9A7A8B8C8CC39709EDFAAF9FEB2F4A8B7AAB1273D5CB7B4547A9D8675AEF6`,
receipt `E45D5459FAF76923D99800A7F1BED4FFDABEAE00ECD6A47C8E26753D82DC4B7A`,
terminal `A0F7AA7717CCC0EC57E55D6893FEF5331112FDC36314252B8AAD4F8FEAADEEFD`.

## V2 registry-state correction

The first sealed packet was never presented to AlphaFactory and no MT5 marker
was created. Prelaunch validation exposed a second contract contradiction: the
original prereg text and three run harnesses expected a second `state=probe`
row, while the canonical append-only registry permits ordinary progression only
from `probe` to `screened`. Its specialized `probe`-to-`probe` exception is
reserved for a different source-only workflow and is inapplicable to MQL5
correctness parity.

The unexecuted invalid draft row was removed before it became authority. V2
changes only the registry-state assertion in the launcher, collector and
comparator from `probe` to `screened`, updates their tests, and rebuilds the
unused packet/receipt under a distinct `preflight/.../V2/` path. The final row's
registry authority label is `MT5_PARITY_CORRECTNESS_ONLY`; the hash-bound Alpha
execution receipt independently retains
`DATA_ACQUISITION_ONLY_NO_PERFORMANCE`, which is the exact authority required
by AlphaFactory and the collection-aware non-repaint auditor.

No compile, source, EX5, Supertrend rule, test window, CSV schema, expected
counter, order boundary, or economic permission changes. The V1 packet and
receipt are retained as superseded prelaunch evidence and must never be used.
