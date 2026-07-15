# Correction — USBILL slope status vs stale NO_LEGAL closeouts — 2026-07-13

## Fact

Hash-bound offline probe result
`preflight/v8_probe/20260713_V8_USBILL_SLOPE_USD_BASKET_PROBE_RESULT_V1.json`
(SHA256 `BE93F528537609E62C345E855E80EFB715CD88D88972535701C1444DA73BA8EC`)
status = **`PROBE_SURVIVOR`**.

## Supersedes

Concurrent/stale text in:

- `readouts/20260713_NO_LEGAL_LOCAL_CANDIDATE_READOUT.md` (bill-slope row)
- `readouts/20260713_V8_AUTONOMOUS_CAMPAIGN_CLOSEOUT.md` (bill-slope kill row)
- earlier `hot.md` / frontier bullets citing year-conc 0.78 / 233 trades

Those claim `KILL_AT_OFFLINE_PROBE` with metrics that are **not** present in the
current result JSON. Living authority is the result JSON +
`readouts/20260713_V8_USBILL_SLOPE_USD_BASKET_OFFLINE_PROBE_READOUT.md` +
registry row `HYP-SR-FX-USBILL-SLOPE-USD-BASKET-001` (`probe`) +
`preregs/20260713_H_FX_USBILL_SLOPE_USD_BASKET_001_PREREG.md`.

## Unchanged

- Carry / COT / carry×vol / US−EU bond-diff / cadence-book M15 kills stand.
- USBILL remains **cost-blocked** for EA / Model 0 / GOAL.
- No post-hoc z/tenor rescue.
