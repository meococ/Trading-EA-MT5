# ALERT_FIRST label gate readout

Date: 2026-07-16  
Verdict: `STOP_BEFORE_NEW_HYPOTHESIS / HUMAN_LABEL_GATE_NOT_CLEARED`  
Authority: pre-outcome taxonomy audit only; no PnL, Model 0, promotion or live

## Outcome first

The full Unicorn memo is still not assured for economic auto-execution. The
zero-trade collector worked, but the missing trader taxonomy did not converge:
the stable parts are displacement/FVG detection; the unstable parts are the
liquidity reference, MSS swing anchor and true-breaker identity. Coding another
filter from this surface would be post-hoc rescue of a terminal OHLC family.

No new hypothesis was registered and no economic backtest was run.

## Sealed collection

AlphaFactory run `20260716_153059` used the exact v1.22 source snapshot SHA256
`A1AD68BC668C277D5EF85E54F61C28F0688D6FF9AC037A43368CECF45383B003`.
It produced exactly 200 unique detector rows, zero prefilled labels and zero
Strategy Tester trades. Casebook SHA256:
`D96F556493DE008C0280907386488411D557451D8C507E1D46B6A05CB48A091E`.
The collection validation artifact SHA256 is
`59A955983A8FBCB291C40E79A266DD98C4565B30870B949835E415FD8F403956`.

All tester/data paths were portable on `D:` and `FILE_COMMON` was disabled.
The four protected C-drive roots were identical before/after by file count,
bytes and metadata hash. No C-side cache, training data or backtest log was
created or deleted by this lane.

## Context integrity

Each alert received 48 M5, 32 M15, 16 H4 and 12 D1 completed bars. No bar close
after the logged decision cutoff is present and no PnL, forward return, fill,
MFE or MAE field exists. Context manifest SHA256:
`1931F3B3193B9BA77422A10C16B7494445A3DAD3AACEF30E798449360A2070C0`.

Two early extractor attempts were invalidated before use. MT5 Python exposes
this broker history on its server-time axis, while the EA logs both server and
UTC decision times; additionally, the logged decision is the final M5 close
cutoff, not its open. The valid extractor queries `decision_time_server`,
subtracts `server_utc_offset_hours`, and proves that the final M5 bar opens five
minutes before `decision_time_utc`. Invalid-attempt evidence is retained under
`.context/unicorn_label_review_20260716/INVALIDATED.md` and contributes no
strategy conclusion.

## Objective exploratory precheck

The frozen rubric deliberately uses stricter memo fidelity than the v1.22
proxy. Results over all 200 rows:

| Component | Yes | No | Ambiguous |
|---|---:|---:|---:|
| True liquidity sweep | 78 | 98 | 24 |
| Displacement >=1.50 ATR and directional outer-quartile close | 79 | 121 | 0 |
| MSS/BOS close beyond a pre-sweep confirmed swing | 89 | 86 | 25 |
| True failed-block breaker | 0 | 11 | 189 |
| Fresh three-candle FVG | 200 | 0 | 0 |
| Post-formation micro-confirmation at decision | 0 | 200 | 0 |

Only 22/200 rows (`11%`) passed sweep + displacement + MSS + FVG before the
unresolved breaker label. Final core labels were 169 `no`, 31 `ambiguous`, zero
`yes`. This is an AI/rule precheck, not an authoritative accepted-density
estimate and not a substitute for human review. Objective summary SHA256:
`C4D58275910811AE1D0F7B71ACCB84D1B5701D0CE5FCF0B8CF8409C83760420C`.

## Grok 4.5 independent calibration

Grok received a sealed, outcome-free, stratified five-case sample with the
objective labels hidden. The file-based runner completed successfully with
`model=grok-4.5`, `stopReason=EndTurn`, and a non-empty response.

Agreement versus the objective precheck was:

| Label | Agreement | Cohen kappa |
|---|---:|---:|
| Sweep | 40% | -0.154 |
| Displacement | 100% | 1.000 |
| MSS/BOS | 60% | 0.412 |
| Breaker | 60% | 0.000 |
| FVG | 100% | 1.000 |
| Micro-confirmation | 100% | 1.000 |
| Final core accept/reject/ambiguous | 60% | 0.286 |

This small, non-random sample cannot estimate population agreement. It is
enough to reject any claim that two AI reviewers cleared the preregistered
`kappa >=0.70` human-label gate. The displayed kappa is three-class
`yes/no/ambiguous`; only one sample row was binary and unambiguous for both
reviewers, so the contract's binary human kappa is not estimable. The material
disagreements are exactly the subjective taxonomy the memo left unresolved.
Calibration analysis SHA256:
`A304BE2E6C2A4FBB225C6E3F2F66613E2C2B51DFB05639C020883D06935F760B`.

## Strategy interpretation

1. The v1.22 detector emits at FVG formation close. Therefore it is a setup
   candidate, not an entry-ready signal: a post-formation retest or rejection
   candle cannot exist at that same decision.
2. The current maximum-overlap opposite candle is not a proven breaker. A true
   failed-order-block sequence needs a frozen origin/invalidation taxonomy.
3. A rolling 12-bar wick reclaim is not consistently the same thing as a
   recognizable liquidity pool. Likewise, different plausible swing anchors
   can flip the MSS label.
4. The strict report prior (`1.50 ATR` plus quality close) rejects 121/200 rows;
   v1.22's `1.20 ATR` detector is intentionally a broad alert proxy.

These findings explain the historical economic failure without inventing a
new rescue: the EA traded broad formation-time proxies before the memo's
structure and zone-response judgment was resolved.

## Decision and next legal action

- Keep the EA alert-only and terminal for economic execution.
- Do not register `HYP-UPS-XAU-M5-009`, change thresholds, add MSS/retest, or
  run another Model 0 from these AI labels.
- The only legal Unicorn continuation is at least 100 sealed labels from two
  independent human reviewers using the frozen rubric, final-core kappa
  `>=0.70`, accepted density `>=25%`, then exactly one de-duplicated feature
  family and a new unopened-window hypothesis.
- If human agreement or density fails, close the detector-to-memo gap. Do not
  tune the taxonomy from outcomes.

The canonical source may receive engineering-only schema/safety hardening after
this collection. That does not retroactively change the bound v1.22 rows or
create performance authority.
