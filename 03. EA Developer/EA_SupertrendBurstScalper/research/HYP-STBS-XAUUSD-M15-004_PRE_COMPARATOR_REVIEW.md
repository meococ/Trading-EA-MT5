# HYP-STBS-XAUUSD-M15-004 — Independent pre-comparator review

Status: `PASS_PRE_COMPARATOR`

Reviewed at: `2026-08-09T06:08:56Z`

## Frozen package

- Preregistration SHA256: `6DC4A6E70E33C330C735B3995D3212C204F498AC4840DC50498A2A53AC384CD3`.
- Comparator SHA256: `00D140BEBAB567678F96E4C581C6871D410C18C488BF1330FDEFC2EBEC44677B`.
- Comparator tests SHA256: `32C6603BE818A48B230FBDAA9850A8ACE186C008218891DF2847B5831322F028`.
- `.gitignore` SHA256: `77A411DA69B2EE690EFB948EC3D00C13A56C3FA0563BC6DEEC1EE577A450D836`.
- The HYP004 evidence root was absent throughout this static review.
- The HYP004 comparator test suite passed `13/13` before authority.

## Independent verdict

`PASS`: no fatal pre-comparator blocker remains. The exact full path and SHA256 bindings, canonical duplicate-run bindings, leading-BOM and duplicate-key rules, dual UTC/server-axis clock mapping through the referenced next oracle row, physical-journal multiplicity, report/data-quality/summary checks, deterministic replay, authority boundary and durable one-shot claim are internally coherent.

The three earlier blockers are closed: abbreviated artifact hashes were replaced with full hashes; all dynamic artifact paths are constrained to the exact frozen roots and kept disjoint from static inputs; executable stop and target geometry is reconstructed from the inherited direct-MQL5 formula rather than checked only for direction. Tests include right-sided but wrong-distance stop/target mutations.

## Authority boundary

This review permits only one `STBS004-COMPARATOR-001` execution against the already completed and hash-locked HYP003 audit run. It authorizes no AlphaFactory invocation, compile, MT5 launch, source-data acquisition, order, trade, outcome, performance, economic analysis, optimization, validation, holdout, promotion, paper trading or live deployment.

Any successful comparator verdict can establish engineering correctness only; it cannot establish PF, expectancy, cost realism, robustness or deploy readiness.
