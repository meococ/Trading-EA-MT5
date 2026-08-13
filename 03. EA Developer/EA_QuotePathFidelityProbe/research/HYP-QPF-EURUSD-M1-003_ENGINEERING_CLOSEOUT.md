# HYP-QPF-EURUSD-M1-003 engineering closeout

Verdict: `ENGINEERING_INVALID_MISSING_D0_PROOF_NO_SOURCE_VERDICT`

The one authorized launch used the exact explicit input bindings and processed
the frozen FivePercent Real EURUSD M1 window. MT5 reported 99% History Quality,
207,698,274 ticks, 3,194,620 bars, 639,403 completed M5 buckets, zero
out-of-order buckets and zero trades.

AlphaFactory nevertheless rejected the evidence before completing the manifest:
the journal contained no `DATA_EPOCH_D0_SERIES_PROOF`. Consequently the copied
178,932,288-byte required CSV was not bound into `manifest.sidecars`, and the
frozen analyzer correctly returned `ENGINEERING_INVALID_NO_SOURCE_VERDICT` for
missing exact-one sidecar identity.

Diagnostic-only readout, never a source or economic verdict:

- pooled one-sided quote-update share was `0.0019210883561223745` against the
  frozen `0.05` minimum;
- every year 2018-2026 failed that same gate (maximum about `0.0090`);
- all other frozen pooled/per-year source gates passed;
- no outcome price, future return, trade result or economics was present.

Governance:

- HYP003 is terminal and must not be rerun under the same identity.
- The diagnostic gate failure may not be rescued by lowering the threshold,
  shortening years, changing symbol or changing the denominator.
- The immutable terminal source snapshot is
  `research/source_snapshots/EA_QuotePathFidelityProbe_HYP-QPF-EURUSD-M1-003.mq5`
  with SHA256 `3CA6544A650149411316C3F14FC0D7410EA84C395E1444A61AB7AA2F9CD76ACD`.
- A fresh identity may add only the missing fail-closed D0 series proof while
  preserving the complete source object and all gates to obtain one official
  PASS/KILL verdict.
