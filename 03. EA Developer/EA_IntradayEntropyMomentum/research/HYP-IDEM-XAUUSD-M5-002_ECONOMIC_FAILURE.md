# HYP-IDEM-XAUUSD-M5-002 — terminal untuned baseline

Verdict: `KILL_BASE_PF_AND_EXPECTANCY_FAIL_CADENCE_PASS`

## Engineering reconciliation

The sole AlphaFactory Model-0 run is `20260811_135304` on FivePercent native
XAUUSD M5, `2018.01.01..2023.01.01`, current broker spread, USD100,000 and
1:100 leverage.

- History Quality `99%`; 351,303 bars and 135,208,676 ticks.
- Journal raw delta `4,188,500` bytes, `files_read=3`, `truncated=false`.
- Source/runtime identity: raw 638, LONG 344, SHORT 294, exact executable
  entries 634, broker entry rejects 4, risk-lock skips 0.
- Lifecycle: close attempts 224, close rejects 2, accepted timed closes 222;
  remaining 412 positions closed by their frozen broker SL/TP. Summary reports
  `runtime_failed=false`, clock rejects 0 and the run reached 2022-12-30.
- Compile result was 0 errors/0 warnings and non-repaint audit passed.

The revision therefore fixed only the parent journal-flood defect and did not
alter the 638-event entropy signal.

## Economic result after tester costs

- completed trades: 634 (`343` LONG, `291` SHORT)
- cadence: `634 / (1826/7) = 2.430449/week` — PASS
- profit factor: `0.8146901669` — FAIL versus strict `>1.30`
- net profit: `-$5,656.49`
- expectancy: `-$8.9219/trade` — FAIL
- win/loss: `260 / 374`; win rate `41.0095%`
- commission: `-$926.81`; swap: `-$263.74`
- relative equity drawdown: `6.9349%` — PASS versus `<=8%`
- calendar-year trades: 119/123/135/131/126; maximum share `21.2934%` — PASS

Both sides lose after costs: LONG PF `0.7886`, net `-$3,502.30`; SHORT PF
`0.8457`, net `-$2,154.19`. These direction/year/weekday observations are
diagnostic only and authorize no filter or rescue.

## Decision

This exact entropy-momentum mechanism is terminal. Do not tune the entropy
definition, prior-session median length, threshold, direction, weekday,
session, stop/target, flatten retry, risk, spread, commission or timeframe.
Cost stress, optimization, validation, holdout, paper and live remain closed.
The EA program goal continues with one materially fresh information mechanism.

Evidence SHA256:

- run manifest: `60FF0B6CD2E7027959E25D6F504A53F36356C860453642F2473DF8C51AFE8066`
- MT5 report: `8A5845B679724DE602C4FF834F36644463B43BDBEC470A1BAF2F2B90971D5B66`
- tester journal: `3230F26F49A8414A292D143174A6B69A70896E2251E4ECF2C4B32DDB8539E4DE`
- enhanced summary: `1DDD0F587BA3731655000FAD0511A706A4D37CDC755AEFDF57C3FCDA7ABB33F9`
- analysis report: `3052BAE4CC2C49FE7E5A28E733F42F1E758685B4A18FF60BC4D8E8DF33E3B3A6`
