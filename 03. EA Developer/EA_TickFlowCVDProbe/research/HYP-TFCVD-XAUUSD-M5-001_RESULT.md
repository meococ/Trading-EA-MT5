# HYP-TFCVD-XAUUSD-M5-001 — terminal source-feasibility result

Verdict: `KILL_SOURCE_FEASIBILITY_EXACT_TICK_DELTA_MAPPING` on 2026-08-09
(Vietnam time). This closes only the frozen XAUUSD M5 2018–2022 broker
quote-tick-delta mapping. It is not an economic verdict and does not close the
EA goal.

## What ran

- AlphaFactory run: `20260809_011952`.
- Exact identity: XAUUSD M5, 2018-01-01 through 2022-12-31, Model 4 request,
  collection-only, current spread, no required sidecar or trading permission.
- Source SHA256: `BCEA09D5AAC388224FD469D9C5EBF989D03E97C41EA889146FC50161A24DFCC8`.
- MT5 generated 135,208,676 ticks and 351,303 bars; the collector emitted
  351,302 completed-bar rows with zero out-of-order ticks.
- Report and journal both prove zero orders/trades and an unchanged USD10,000
  balance.

Three earlier invocations stopped in AlphaFactory receipt/scalar preflight
before MT5 launch. They consumed no data attempt and opened no source result.
The run above is the only terminal launch.

## Why the source gate failed

The failure is simultaneous and decisive:

1. Strategy Tester report History Quality is `0%`, below the frozen `>97%`
   gate.
2. AlphaFactory rejected the run because the journal contained no required D0
   series proof.
3. The journal states XAUUSD real ticks begin only at `2026.06.01`; the frozen
   2018–2022 window was therefore generated rather than broker-native real-tick
   history.
4. Outcome-blind analysis found 351,302 bars and 99.814689% with at least 20
   unique quote updates, but exactly zero frozen absorption candidates. The
   candidate-count, 2–8/week cadence, direction-balance and concentration gates
   all failed.

Generated tester ticks mechanically couple the tick-rule delta to generated
price movement. They cannot validate a broker-native quote-flow absorption
thesis. Relaxing the delta threshold, close-efficiency threshold, window or
source-quality gate after seeing this readout would be a prohibited rescue.

## Evidence

- Run manifest SHA256: `5F1B1BD473549BB729B50D2F4D2BA5AC87AE9F8C78D559FED736F9EA300B967F`.
- MT5 report SHA256: `2746B5FD44F88B07226965D7B167BA512AA0D2CA5DCFBD6D6AED3495226A1AFE`.
- Tester journal delta SHA256: `21B1AD46464F1F05C6C5B302671FE9BD8F7E2E93462C8E225C906464F98EC4DE`.
- Raw source telemetry SHA256:
  `27CF2199841619F419BAD8DD290B101EDD36A7F71BE4D6A7B06AD7FFB66016F7`
  (98,445,632 bytes).
- Source analysis SHA256: `B30E2F0CDE01AE495E9F106CAB04427736A69486608D264B253894B6B39327B8`.
- Exact source snapshot SHA256:
  `BCEA09D5AAC388224FD469D9C5EBF989D03E97C41EA889146FC50161A24DFCC8`.
- Compiled run EX5 SHA256:
  `D3086F4764B295CA1A38D9F14F740C7655058E1069B1B3FFE2CCDD05AC99C587`.

All paths are rooted at
`02. AlphaFactory/runs/EA_TickFlowCVDProbe/20260809_011952/`.

## Authority after close

- No same-ID rerun, threshold repair, economics, optimization, validation,
  holdout, promotion, paper or live authority.
- Historical quote-tick/CVD research may reopen only with a materially new data
  source that proves real historical quote/tick provenance under a fresh ID.
- The main research loop continues with a fresh mechanism that uses data
  actually available and auditable in MT5.
