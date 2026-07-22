# Grok Indicator Chart Forensics — 200 XAUUSD M5 Losing Trades

## Verdict boundary

Both Grok workers visually inspected exactly 100 unique indicator-rich PNGs (200 total, zero overlap). This is descriptive loser anatomy only. The parent tester run remains `INVALID_ENGINEERING_RUN` because history quality was 98%, below the frozen 99% gate. No finding here authorizes a filter, threshold tune, BE change, timeout change, promotion, or live use.

## Validated coverage

| Worker | Images opened | Valid chunks | Grok turns | Grok elapsed |
|---|---:|---:|---:|---:|
| worker_a | 100 | 10 | 42 | 30.0 min |
| worker_b | 100 | 10 | 49 | 34.9 min |

Each chart contains M5 candles, EMA200, MACD 12/26/9 main/signal/hist with s3/s2/s1 markers, RSI14 with the 42–58 band, ADX14 with the 18 gate, ATR14, entry, SL, TP, exit, hold time, and net R.

## Direct sample anatomy

- Positions: 200 (126 BUY, 74 SELL).
- Median defined net R: -0.866; one case has undefined R because initial account risk was zero.
- Median hold: 28.6 minutes; 53 closed within 15 minutes and 103 within 30 minutes.
- 124 cases lost at least 0.8R; 41 exited at the exact 75-minute / 15-bar hold limit.
- Post-run recomputation matched all source direction conditions in 107/200 cases. Non-parity is a visualization/data-formula boundary, not proof of an EA logic breach.

## Worker-level exact path metrics

These counts come from the frozen lifecycle/case CSV, not text classification.

| Metric | Worker A | Worker B | Combined |
|---|---:|---:|---:|
| BUY / SELL | 61 / 39 | 65 / 35 | 126 / 74 |
| Median defined net R | -0.866 | -0.872 | -0.866 |
| Net R ≤ -0.8 | 56 | 68 | 124 |
| Hold ≤ 15 min | 27 | 26 | 53 |
| Hold ≤ 30 min | 44 | 59 | 103 |
| Exact 75-min timeout | 24 | 17 | 41 |
| Post-run NON-PARITY | 51 | 42 | 93 |

## Grok synthesis

The two reviewers independently converged on the same main mechanism family: the indicator cluster often recognizes a micro-turn after the directional impulse is already mature or exhausted. Worker A tagged 57/100 cases in this family; Worker B's normalized chunk synthesis tagged 52/100. These are non-exclusive reviewer labels, not population failure rates.

Worker A additionally tagged 39 bounce/mean-reversion, 30 range/chop, and 27 timeout/no-follow-through descriptions. Worker B tagged roughly 46 rapid/full adverse-SL paths. Lifecycle truth supersedes text tags: exact 75-minute timeouts were 24 for A and 17 for B, not any broader text-tag count.

## Strategy-indicator linkage recorded by Grok

The counts are non-exclusive unions of case IDs cited by the 16 structured chunks (160 cases). The 40 plain-text recovery cases remain in the validated per-case packet but do not contribute to this structured-surface table.

| Strategy surface | Cited cases |
|---|---:|
| ADX trend-strength gate | 87 |
| EMA200 side filter | 107 |
| Exit geometry and max hold | 98 |
| MACD histogram extremum and delta | 113 |
| Post-run recomputation fidelity boundary | 22 |
| RSI band and slope | 101 |

Cross-chunk reading: Grok repeatedly described the MACD-histogram extremum as occurring after an already-developed impulse, while RSI mid-band slope, ADX≥18, and the EMA200 side filter often remained compatible with both follow-through and reversal paths. The charts also separate rapid near-full-R stop paths from 75-minute timeout paths. These are mechanisms to test prospectively, not post-hoc rules.

## Evidence map

- [Worker A — 100 indicator charts](<D:/Trading EA MT5/03. EA Developer/EA_MZMS_Scalper/research/evidence/HYP-MZMS-MACD-HIST-SLOPE-XAUUSD-M5-006_GROK_INDICATOR_FORENSICS_200/charts/worker_a>)
- [Worker B — 100 indicator charts](<D:/Trading EA MT5/03. EA Developer/EA_MZMS_Scalper/research/evidence/HYP-MZMS-MACD-HIST-SLOPE-XAUUSD-M5-006_GROK_INDICATOR_FORENSICS_200/charts/worker_b>)
- [Validated Grok results packet](<D:/Trading EA MT5/03. EA Developer/EA_MZMS_Scalper/research/evidence/HYP-MZMS-MACD-HIST-SLOPE-XAUUSD-M5-006_GROK_INDICATOR_FORENSICS_200/GROK_VALIDATED_RESULTS_200.json>)
- [Frozen selection manifest](<D:/Trading EA MT5/03. EA Developer/EA_MZMS_Scalper/research/evidence/HYP-MZMS-MACD-HIST-SLOPE-XAUUSD-M5-006_GROK_INDICATOR_FORENSICS_200/selection_manifest.json>)
- [Recomputed entry indicator features](<D:/Trading EA MT5/03. EA Developer/EA_MZMS_Scalper/research/evidence/HYP-MZMS-MACD-HIST-SLOPE-XAUUSD-M5-006_GROK_INDICATOR_FORENSICS_200/entry_indicator_features.csv>)

Raw runner evidence is retained under `.context/mzms-xau-indicator-*-s10-c*` and `.context/mzms-xau-indicator-*-plain-*`. Only runner-useful, image-open, manifest-matching evidence is included in the packet.
