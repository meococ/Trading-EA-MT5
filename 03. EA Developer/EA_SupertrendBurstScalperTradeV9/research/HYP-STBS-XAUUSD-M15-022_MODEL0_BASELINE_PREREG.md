# HYP-STBS-XAUUSD-M15-022 — Frozen Model-0 baseline preregistration

## Hypothesis and lineage

- Hypothesis: `HYP-STBS-XAUUSD-M15-022`
- EA: `EA_SupertrendBurstScalperTradeV9`
- Parent: terminal `HYP-STBS-XAUUSD-M15-021`
- Parent terminal raw-row SHA-256: `507905ED8C71C4E3DA60853F5A60E7CD44B0A2F56BC06E8EE045FA0102D05C59`
- Parent verdict: `KILL_ENGINEERING_NR_PROVENANCE_PROPAGATION_AND_ACTUAL_MONEY_MARGIN_HALT_NO_ECONOMIC_VERDICT`
- Source SHA-256: `9B82946CF17A876B547E7227F7FA131183C2383D38BF639574001CAB03DF8D82`
- EX5 SHA-256: `5FDB825F8D83EF52F639547CE444C936FD1ED9EE581AD5220EBA0774128A8954`
- Compile log SHA-256: `E605E1BD6095F7E79D44F8397F54A2D02D89F2E191D17DDC6CD7762A92A5DEF9`
- Compile: exactly `0 errors, 0 warnings`
- Bounded diff proof SHA-256: `1CC4B30A4F524A95837DD53AFC76CB2CDDF59619A41A58AB8578FF339FD35B44`
- Non-repaint auditor SHA-256: `366D70F0C6FAF02F85B4819E7305CD1BD271BA6A78B4789CF0DCDF2FB651E360`
- Non-repaint manifest SHA-256: `899E2C031DBC93FD99450990347C3FB1FB412E848964820AD4A0887FAAE3F6F1`
- Non-repaint audit SHA-256: `359E11DC5979E5D0B915A510F0148D3451D11994EDF46ADA1D18F3CF0C238509` (`PASS`)
- Risk/source test SHA-256: `E6F337726E1CC627732C05D194C2C39D43D9ABA5C91401BAAE1BA7074A2AC1A1`
- Runner/adapter test SHA-256: `3A519EE55818800B4DCF2965DCC0B9B42292DE7B3381B3432E84B57B7B039391`
- Focused tests: `15 passed`
- Research cost manifest SHA-256: `F3474E21C48A0DD2F3E8192F252016759EF05FA477B16ABF626EBEB9B8C91BA1`
- HYP022 runner SHA-256: `A01B6D5F3E76C5B6E3B60D82690F6D894E1A9B559A19E107BA475D2ECDAB0F5E`
- Frozen shared Alpha SHA-256: `BC570A1EA7D8788AC9483A7133565893C8B679ADE9A0ED85E2B8AF8B3A0F02FC`
- Frozen base research loop SHA-256: `6E205874477A79EB97EE56967B81FA3675FB25AD784D00D989BBD077DA837550`

HYP021 produced no admissible economics. HYP022 is a bounded risk-consistency and audit-provenance child. It does not use HYP021 PF, session, weekday or hour readouts.

## Exact V9 risk revision

The signal, entry price, SL, TP and exit schedule stay frozen. For each candidate volume, before `OrderSend`:

1. move the requested entry adversely by the full frozen `InpDeviationPoints=20` envelope (BUY higher, SELL lower);
2. calculate P/L from that worst allowed fill to the already-frozen SL with `OrderCalcProfit`, then subtract the full frozen research-proxy round-turn commission reserve of `4.4` account-currency units per lot;
3. calculate required margin at the requested entry, worst allowed fill and SL price with `OrderCalcMargin`;
4. use conservative stressed margin `max(OrderCheck.margin, current_margin + max(entry_margin, worst_fill_margin, stop_margin))` and apply the existing 5%-equity new-margin ceiling to that worst of the three;
5. compute stressed equity/free margin/margin level;
6. apply the same frozen percent or money stop-out headroom formula to the stressed state;
7. if unsafe, move down exactly one broker volume step and repeat; if min lot is unsafe, consume the signal as a margin rejection.

API failure, nonfinite values, nonloss SL geometry or invalid margin values fail closed. The pre-trade claim is limited to the frozen SL under the allowed 20-point fill envelope plus the full 4.4/lot charge reserve; gaps beyond SL remain outside that guarantee. `EvaluateActualMargin` remains unchanged as a permanent runtime backstop. A runtime margin breach still makes the attempt engineering-invalid; it is not converted into a recoverable economic exit.

## Narrow run-time non-repaint adapter

The shared `alpha.ps1` and generic research loop remain byte-frozen. `run_stbs022_model0_baseline.ps1` calls canonical `alpha.ps1` for compile/backtest, validates the original run manifest against the packet, then writes a separate analysis-local `nonrepaint_run_manifest.json`. The adapter does not mutate the original at the audit step; the inherited generic loop may later append its normal research-loop receipt metadata to the original manifest.

The adapter hash-binds the original manifest before, during and after derivation. The derivative may add only:

- `nondecision_provenance_copytime_authorized=true`; and
- the exact static manifest path/SHA and scope string.

It is allowed only when outer identity is HYP022, EA is V9, run source SHA is exact, and the reviewed static manifest authorizes the single exact `DATA_EPOCH_D0` first-date `CopyTime`. No decision, price-outcome or generic collection authority is added.

## Market and execution contract

- Platform: MT5/MQL5; compile/backtest executed by canonical `02. AlphaFactory/alpha.ps1` through the frozen HYP022 runner.
- Symbol/timeframe: native `XAUUSD`, chart `M15`.
- Tester preload: `2005.01.01` inclusive to `2023.01.01` exclusive, Model `0`.
- Economic TRAIN window: `2018.01.02` through `2022.12.30`, inclusive dates.
- Deposit/leverage/spread: `100000`, `1:100`, current spread semantics with CLI `-Spread` omitted.
- Execution mode/delay/timeout: `0`, `0 ms`, `900 seconds`.
- Run role: `control`; telemetry tier `trade-only`, profile `lifecycle-v3`.
- Data fingerprint: `B326D511C805C7998DF1C2FC540770B6EC3054D0D4BCBB41A5A4E3C2E4239D25`.
- Account fingerprint: `0A603E7B316F58B39FEA0A1710FE6F250E544909DA2B91967C93AD984317A073`.
- Journal cap: exactly `1,048,576` raw bytes; `truncated=false` mandatory.

Exact overrides:

`InpAuditOnly=false;InpEnableTelemetry=true;InpHypothesisId=HYP-STBS-XAUUSD-M15-022;InpMagic=5604122;InpMaxNewPositionMarginPct=5.0;InpMinProjectedMarginLevelPct=2000.0;InpMoneyFreeEquityFloorPct=1.0;InpMoneyHeadroomReserveFactor=0.20;InpPercentStopoutHeadroomFactor=1.25;InpVariantTag=STBS_H1_FLIP_M15_BURST_TRADE_V9_SL_STRESSED_MARGIN`

## Frozen strategy

- Completed native H1 Supertrend 10x3 state flip.
- Decision only at exact next native H1/M15 open.
- Prior completed M15 ATR14.
- One position; no pyramiding.
- Requested risk 0.25% equity; downward-only broker-step sizing.
- Stop 1.0 ATR; target 1.5R; maximum hold eight completed M15 bars.
- Friday entry cutoff 18:00 UTC; flatten at/after 20:00 UTC; no weekend hold.
- No direction/session/hour/weekday/filter/threshold/SL/TP/hold/indicator search.

## Engineering gates before economics

All must pass:

1. fresh run compile `0 errors, 0 warnings`; source/EX5/config/original manifest exact;
2. the pre-audit original manifest contains no provenance fields; the derivative differs semantically only by the two frozen provenance fields;
3. run-local non-repaint PASS with exactly one allowed DQ `CopyTime` and zero findings;
4. HQ strictly above 97%, fixed-window/no-skip/series-proof/data/account fingerprints exact;
5. journal `truncated=false`, terminal summary present and `runtime_failed=false`;
6. zero `STBS_FATAL`, forced stop-outs, margin emergencies, orphan inventory and unresolved replay tickets;
7. RunMeta/lifecycle/report reconcile exact unique deal/position volumes and final-close flags;
8. raw/executable/gap/direction/ATR/geometry/margin counts reconcile and no trade lies outside TRAIN;
9. deterministic verified-cost artifact and unified baseline rebuild complete.

Any engineering failure consumes the sole attempt and yields no economic verdict.

## Cost and economic acceptance

Cost tier remains `VERIFIED_RESEARCH_PROXY_NONPROMOTABLE`: frozen historical spread, commission `4.4`, and direction-aware 1,000 ms adverse quote proxy from `31,176` samples.

Only after engineering PASS:

- completed trades `>=500`;
- cadence `2–5` trades/week using `((2022-12-30 - 2018-01-02).days + 1) / 7`;
- LONG/SHORT each `>=30%`; no year above `30%` of trades;
- every calendar year 2018–2022 has positive x1 net R;
- mean x1 net R strictly positive;
- PF x1 strictly `>1.30`; PF x1.5 `>=1.25`; PF x2 `>=1.00`;
- maximum drawdown `<=8%`.

## One-shot authority boundary

- Sole attempt: `STBS022-MODEL0-TRAIN-001`, limit `1`, consumed `0` before execution.
- Durable claim must precede compile, MT5 and bound artifact reads.
- Same-ID retry is forbidden.
- Optimization, WFA, OOS, holdout, Monte Carlo, sensitivity, promotion, paper and live remain unauthorized.
