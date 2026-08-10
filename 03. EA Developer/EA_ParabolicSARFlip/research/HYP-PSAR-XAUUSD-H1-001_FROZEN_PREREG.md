# HYP-PSAR-XAUUSD-H1-001 - Frozen Standard Parabolic SAR Flip Source Preregistration

Status: `FROZEN_PRE_OUTCOME_SOURCE_ONLY`

Informing evidence: standard AO(5,34) Twin Peaks on M5 was parked only for 43.09 events/week. No PSAR count, price outcome or economic metric informed this object.

## Identity and thesis

- Hypothesis: `HYP-PSAR-XAUUSD-H1-001`
- Family: `wilder-parabolic-sar-002-020-stop-and-reverse`
- Symbol/timeframe: native FivePercent XAUUSD H1 Bid bars
- Source state: exact inception `2004-06-11T04:00:00Z` through `<2023`
- Design: `[2018-01-01T00:00:00Z, 2023-01-01T00:00:00Z)`
- Validation 2023-2024 and holdout 2025+ remain sealed
- Sole attempt: `PSAR001-SOURCE-ATTEMPT-001`

TradingView documents the original Wilder Parabolic SAR recurrence, strict penetration reversal test, two-prior-bar clamp, and start/increment/max defaults `0.02/0.02/0.20`. MetaQuotes exposes the same standard family through one-buffer `iSAR(step=0.02, maximum=0.20)`.

Repository de-dup found no canonical Parabolic SAR, PSAR or `iSAR` object in the registry or failure catalog. PSAR is materially distinct from ATR-band Supertrend: it evolves from trend extreme points and an accelerating factor rather than ATR distance.

## Exact direct-formula state machine

Use full native-H1 history from inception. All rows must have finite `high>=low`, `low<=close<=high`; flat bars are valid.

- Bar 0: SAR and direction unavailable.
- Bar 1 initialization: UP iff `close[1] > close[0]`; equality initializes DOWN. UP uses `SAR[1]=low[0]`, `EP=high[1]`; DOWN uses `SAR[1]=high[0]`, `EP=low[1]`. `AF=0.02`. Initialization never emits.
- For every bar `t>=2`, first compute `candidate = SAR[t-1] + AF[t-1] * (EP[t-1] - SAR[t-1])`.
- Prior UP reverses to DOWN iff `candidate > low[t]` (strict). On reversal: `SAR[t]=EP[t-1]`, `EP[t]=low[t]`, `AF[t]=0.02`, emit SHORT.
- Prior UP without reversal: `SAR[t]=min(candidate, low[t-1], low[t-2])`; if `high[t] > EP[t-1]`, set `EP[t]=high[t]` and `AF[t]=min(0.20,AF[t-1]+0.02)`, else preserve both.
- Prior DOWN reverses to UP iff `candidate < high[t]` (strict). On reversal: `SAR[t]=EP[t-1]`, `EP[t]=high[t]`, `AF[t]=0.02`, emit LONG.
- Prior DOWN without reversal: `SAR[t]=max(candidate, high[t-1], high[t-2])`; if `low[t] < EP[t-1]`, set `EP[t]=low[t]` and increment capped AF, else preserve both.
- Equality in penetration, EP update or clamp comparison never triggers the strict branch.

This TradingView-provenance direct formula controls source acceptance. It makes no pre-run claim of byte parity with MetaQuotes initialization. If source gates pass, a fresh child must compare every bar's SAR and every reversal against native `iSAR`; if parity fails, only the exact direct formula may be built unless a separately frozen explanation is accepted.

## Execution mapping

- signal only on a completed H1 state reversal;
- decision only at exact next physical H1 row, both `source_epoch+3600` and UTC `+1 hour`;
- a raw gap event is consumed, never queued;
- next price is never read.

Forbidden: trend-strength/session/news/ATR/ADX/volume filters, alternate step/max, delayed confirmation, cooldown/debounce, sibling timeframe tournament, stops/targets, outcomes and optimization.

## Frozen source and gates

- Manifest SHA256: `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`
- XAUUSD H1 SHA256: `B85006E201DA7B359E9F25290C81C72A6092CFA08AEDFFE05E693E17A005ACC3`
- PyArrow materializes only `time_utc<2023`; scoring uses `[2018,2023)`.

All gates must pass: hashes/one-shot/replay; design rows >=25,000; feature coverage >=99%; exact-next >=97%; executable N>=500; cadence 2-5/week; each direction >=30%; max year <=30%; every year 1.25-6.50/week; zero conflicts; exact outcome-blind ledger.

Any failure gives `PARK_SOURCE_FEASIBILITY_EXACT_STANDARD_PSAR_FLIP`. All pass gives `SCREENED_SOURCE_PASS_DIRECT_MQL5_PARITY_CHILD_AUTHORIZED`, permitting only a fresh direct-formula/native-`iSAR` correctness child.

No source access may occur before preregistration, analyzer, tests and independent review are registry-bound. No MT5, MQL5, economics, validation, holdout, paper, promotion or live authority is granted.

References:

- https://www.tradingview.com/support/solutions/43000502597-parabolic-sar-sar/
- https://www.tradingview.com/support/solutions/43000645065-parabolic-sar-strategy/
- https://www.mql5.com/en/docs/indicators/isar
