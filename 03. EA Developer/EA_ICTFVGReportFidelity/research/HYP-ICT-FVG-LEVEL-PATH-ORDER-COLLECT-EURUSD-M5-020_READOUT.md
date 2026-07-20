# HYP-020 pre-source de-dup readout — terminal kill

## Verdict

`KILL_AT_HYP020_PRE_SOURCE_OHLC_REDUNDANT_BINARY_RECROSS`

HYP-020 is terminated before source modification, compile or tester execution.
No price outcome or tester economics were read.

## Why the frozen binary is not a new information set

For a long setup, the closed sweep bar satisfies `close > pivot_low > sweep_low`.
The proposed path interval starts at that sweep-bar close, so its first valid mid
is normally already favorable relative to `L=sweep_low`. Therefore:

- `CLEAN` (`adverse_reentry_count=0`) means no later mid is below `L`;
- `CHURN` (`adverse_reentry_count>=1`) means at least one later mid is below `L`.

Under a continuous intrabar path this is equivalent to asking whether any
post-sweep M5 low is below `L` (or high above `L` for a short). The existing
post-sweep OHLC extrema can recover that bit. The label therefore does not prove
event-order information beyond OHLC, despite being computed online from ticks.

The first Grok review selected this binary. Codex challenged it before code; the
second adversarial Grok review accepted the flaw and recommended the same
terminal pre-source kill. The corrected review lives at
`.context/grok_ictfvg_hyp020_path_order_20260719/run2/grok-response.json`.

## Formal distinction required for a successor

With long level `L=100`, these paths share `O=101, H=110, L=99, C=109`:

- `101 -> 110 -> 99 -> 109`: one favorable-to-adverse re-entry.
- `101 -> 99 -> 105 -> 99 -> 109`: two favorable-to-adverse re-entries.

OHLC cannot recover the multiplicity. A fresh HYP-022 may therefore test the
pre-outcome binary `ORDERLY <=1` versus `REPEATED_CHURN >=2`. The integer cut is
semantic (a repeat requires a second completed probe), not selected from any
price outcome. HYP-022 requires a new plan, matrix, preset, registry row,
red-first identical-OHLC fixtures and a zero-trade materiality collection.

## Stop rule

- Do not implement or run HYP-020.
- Do not amend HYP-020 in place or create `HYP020_V2`.
- Do not defend it using rare gaps or bid-versus-mid edge cases.
- HYP-018 and HYP-020 remain terminal; HYP-019 remains unopened.

