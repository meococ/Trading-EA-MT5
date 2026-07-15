# Discovery Wave5 closeout — ATR%ile / EURUSD Asia-box / NY-IB (2026-07-14)

Status: `WAVE5_EXECUTED_EMPTY / GOAL_STILL_UNMET`  
Authority: Owner mandate — R&D without Real/QFSI stall; joint thick post-cost $/trade **and** cadence 2–5/wk  
GPT: waived

## De-dup / ceremony

| Step | Artifact |
|---|---|
| De-dup | `readouts/20260714_DISCOVERY_WAVE5_DEDUP_CLEARANCE.md` |
| Phase-0 freeze (optional) | `readouts/20260714_PHASE0_RR2_SPARK_UNIVERSE_FREEZE.md` — universe frozen a priori; **compose ceremony not run** |
| Registry boot | `preflight/20260714_DISCOVERY_WAVE5_BOOT_RECEIPT.json` |
| Contracts | `preflight/20260714_DISCOVERY_WAVE5_CONTRACTS.json` |
| Compile | All three EX5 OK (0 errors) |
| Metrics | `preflight/20260714_WAVE5_MODEL0_METRICS.json` |

## Board (Model 0)

| ID | Run | Verdict | PF | N | tpw | Exp $/t | +$12 stress |
|---|---|---:|---:|---:|---:|---:|---|
| `HYP-H1-ATR-PCTILE-BREAK-001` | auth `20260714_224917` (twin `225208`) | **PARK** weak | 1.10 | 445 (twin 452) | ~**1.71** | +~11 | x1 **~0.99 FAIL** / x1.5 **~0.94** / x2 **~0.89** |
| `HYP-EURUSD-H1-ASIA-BOX-LONDON-BREAK-001` | auth `20260714_225314` (alt `225610` same report SHA) | **KILL** PF | **0.90** | 500 | ~**1.92** | −13.01 | x1 **0.81** / x1.5 **0.77** / x2 **0.74** (diag) |
| `HYP-M15-NY-IB-DRIVE-BREAK-001` | `20260714_225340` | **PARK** weak | 1.02 | 983 | ~**3.77** | +1.74 | x1 **0.90 FAIL** / x1.5 **0.85** / x2 **0.80** (diag) |

No research HIT (none clears PF>1.30 ∧ tpw∈[2,5]).

Report SHA map: `preflight/20260714_WAVE5_REPORT_SHA.json`.

## Integrity

- ATR%ile authoritative run is `20260714_224917` (parallel lane closeout +
  `readouts/20260714_HYP_H1_ATR_PCTILE_BREAK_001_READOUT.md`). Twin
  `20260714_225208` from Wave5 batch confirms same PARK shape; do not treat
  twin as a second research hit attempt.
- Alpha finalize threw known empty `required_sidecars` null-coercion after report ready; metrics from report + `sonic_cost_stress` (base+$12).
- Autoretry waited for free lock/`terminal64=0` then launched batch — mechanical slot, not a QFSI/login research gate.
- `HYP-PORTFOLIO-SB-SPARK-RUNNER-001` `20260714_224302` KILL (PF 1.219) —
  scaffold portfolio is **not** a GOAL book; Phase-0 compose remains freeze-only.
- Do **not** densify ATR%ile bands, Asia/London/NY hours, Donchian, RR, or Mon/day from these readouts.
- Phase-0 RR2 `194548` + Spark100k `193358` universe is frozen a priori; prior offline compose remains diagnostic only — **no combo PF claimed this wave**.

## Best GOAL distance (shelf unchanged)

| Book | Tester | Stress | Notes |
|---|---|---|---|
| RR2 `20260714_194548` | PF **1.378** / ~**2.01**/wk | a priori +$12 x1.5 **FAIL** | Still closest joint PF+cadence |
| ATR%ile `225208` | PF 1.10 / ~1.73/wk | +$12 x1 FAIL | Mid-vol gate ≠ thick edge |
| NY-IB `225340` | PF 1.02 / ~3.77/wk | +$12 x1 FAIL | Cadence-band twin of London-IB weak |

## Structural lesson

Wave5 again failed the joint GOAL design target:

1. **Mid-vol ATR%ile Donchian** cleared cadence-ish (~1.73/wk) but expectancy too thin for +$12 (exp +$11 → stress FAIL).
2. **New-symbol EURUSD Asia-box→London** had cadence (~1.9/wk) but **negative edge** (PF 0.90) — session box alone is not a transferable edge.
3. **NY-IB** mirrored London-IB Wave4: cadence OK (~3.8/wk), PF≈1.0, dies under +$12.

Split lesson from Wave4 **reconfirmed**: cadence sleeves ≠ thick sleeves. Mid-vol / session-microstructure filters without a stronger structural edge do not create joint books.

## Next R&D (no Owner login dependency)

1. Prefer **structural rebuilds with a priori thick edge objects** (multi-bar acceptance after stop-run, cross-asset lag with quality impulse already proven offline, or frozen multi-sleeve compose ceremony after contamination clear) — not more single-signal session/vol gate spam.
2. Phase-0 RR2+Spark compose ceremony only after contamination contracts clear; universe already frozen in `20260714_PHASE0_RR2_SPARK_UNIVERSE_FREEZE.md`.
3. `DEMO_DISCOVERY_DIMINISHING_RETURNS = true` remains — cheap offline probe / failure-packet Deep Research before next Model 0 batch when possible.
4. Real/QFSI accumulate in parallel only — never lane stop / never headline.
5. Banned densify: MaxKZ/RR, ATR%ile bands, Asia/London/NY IB hours, Wave1–5 killed/parked families.
