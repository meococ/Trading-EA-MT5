# Deep Research V2 Coordinator Audit — 2026-07-13

Status: `KILL_AT_INTAKE_DUPLICATE / NO PREREG / NO CODE`

## Binding

- ChatGPT conversation:
  `https://chatgpt.com/c/6a53c72a-8ed8-83ec-b1d8-88af38ec4ee6`
- Input packet:
  `03. EA Developer/EA_SonicR/research/20260712_NEW_STRATEGY_DEEP_RESEARCH_PACKET_V2.md`
- Submission receipt:
  `03. EA Developer/EA_SonicR/research/preflight/20260712_NEW_STRATEGY_DEEP_RESEARCH_SUBMISSION_V2.json`
- UI contract was valid: `GPT-5.6 Sol`, `Pro`, and `Nghiên cứu sâu` were
  read back before submission.
- Research completed in approximately nine minutes.

## Model result

The report rejected option-cut gamma unwind for missing historical strike/OI
data and rejected macro-announcement drift for missing consensus-surprise data.
It retained one Phase-A idea:

`EURUSD Europe benchmark-fix dealer-hedging reversal`

The proposed fixed rule was long EURUSD after the London WMR window when the
pre-ECB EUR move was negative, entering at 16:05 Europe/London and forcing an
exit at 16:55 America/New_York. The report marked the candidate
`SURVIVES_PHASE_A / BLOCKED_BY_COST_DATA`, issued no MQL5 build contract, and
requested complete same-broker bid/ask, commission, slippage, swap/fee, symbol
specification, timezone, benchmark calendar, and input hashes.

## Primary-source audit

The economic mechanism is real but does not establish a new retail edge:

- Krohn, Mueller, and Whelan, *Foreign Exchange Fixings and Returns Around the
  Clock* (Bank of Canada Staff Working Paper 2021-48), documents systematic USD
  appreciation before major fixes and depreciation afterward, with a dealer
  pre-hedging/inventory explanation:
  `https://publications.gc.ca/collections/collection_2021/banque-bank-canada/FB3-5-2021-48-eng.pdf`.
- The same paper states that most trading profits disappear when transaction
  costs are incorporated. Full indicative-spread results are generally
  negative; better-than-indicative execution is required for positive results.
- LSEG WMR methodology confirms a five-minute benchmark window from 2m30s
  before to 2m30s after calculation time using sampled trades and order rates:
  `https://www.lseg.com/content/dam/ftse-russell/en_us/documents/ground-rules/wmr-fx-methodology.pdf`.
- FCA Occasional Paper 46 is relevant regulatory evidence for the 4pm fix, but
  it does not validate the exact model-proposed filter, 16:05 entry, or 16:55
  New York exit:
  `https://www.fca.org.uk/publication/occasional-papers/occasional-paper-46.pdf`.

The exact `preE < 0`, long-only, M5, 16:05/16:55, no-SL/no-TP rule is a model
suggestion. No cited primary source directly validates that implementation.

## Canonical local de-duplication

The Phase-A survivor is not new. The broader local catalog contains direct
falsification of the same WMR/post-fix mechanism:

| Evidence | Symbol/period/window | Trades | PF | Net | DD | Verdict |
|---|---|---:|---:|---:|---:|---|
| `S532 / EA_FixFade / 20260331_003352` | EURUSD M15, 2018-01-01..2026-03-29 | 965 | 0.870869 | -2553.65 | 32.61% | `FAILED` |
| `S216 / EA_LondonFix / 20260325_044706` | EURUSD M5, 2019-01-01..2025-12-31 | 38 | 0.635137 | -862.57 | 9.27% | `FAILED` |
| `S217 / EA_LondonFix / 20260325_044717` | GBPUSD M5, 2019-01-01..2025-12-31 | 110 | 1.018369 | 117.98 | 10.18% | `BREAKEVEN / NO EDGE` |
| `S214 / EA_LondonFix / 20260325_044650` | USDJPY M5, 2019-01-01..2025-12-31 | 20 | 0.193689 | -971.29 | 9.24% | `FAILED` |
| `S564 / EA_PostFixRevert / 20260412_194519` | XAUUSD M15, 2018-01-01..2025-12-25 | 1905 | 0.851529 | -3577.23 | 36.91% | `FAILED` |

`02. AlphaFactory/STRATEGY_LOG.md` explicitly records S532 as “London WMR Fix
post-reversal fade” and concludes that fix reversal has no retail-accessible
edge. The same log records the S214-S217 London-fix family and S564 post-fix
reversal failure. The candidate therefore duplicates a closed mechanism,
irrespective of its additional `preE < 0` condition. That condition is an
unverified post-hoc filter suggestion, not new causal evidence.

## Coordinator verdict

`KILL_AT_INTAKE_DUPLICATE`

- Do not append a candidate registry row.
- Do not create or freeze a preregistration.
- Do not acquire cost data specifically to rescue this fix family.
- Do not write an analyzer, MQL5 source, compile, or backtest this candidate.
- Feed this failure into the next Deep Research cycle and require hard de-dup
  against S214-S217, S532, S564, TokyoFix/TokyoFixV2, Gold/LBMA fix families,
  and all generic session/time reversal or drift strategies.

