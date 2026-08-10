# HYP-STBS-XAUUSD-M15-021 — Frozen Model-0 baseline preregistration

## Hypothesis and lineage

- Hypothesis: `HYP-STBS-XAUUSD-M15-021`
- EA: `EA_SupertrendBurstScalperTradeV8`
- Parent: terminal `HYP-STBS-XAUUSD-M15-020`
- Parent terminal raw-row SHA-256: `58B6BAD2E3AEA23B9F257A86E813A5341865AEA582ABC8543B76F5E56C61E915`
- Parent verdict: `KILL_ENGINEERING_LIFECYCLE_CLOSE_LOGGING_FAILED_AND_JOURNAL_TRUNCATED_NO_ECONOMIC_VERDICT`
- Source SHA-256: `11E44FF9B51DA50F6DF25C54858BFF492C89A58EED04684C828A70740B37FED9`
- EX5 SHA-256: `E98A3535D4E14081C42E88101A32FB251FC11BA78DE79DEA0C444479AC4FC31B`
- Compile log SHA-256: `C36878CF9950E743A97394E21DD083CD75EFCDD2DFB2F06CAA20DA0208779A20`
- Compile: exactly `0 errors, 0 warnings`
- Bounded diff proof SHA-256: `CDDA40FD7B493BFE77C3290E10007E4AF8ED5628C613F8C8C8D8B1C45DB6274D`.
- Non-repaint manifest SHA-256: `E95C3B3C2D8D47E396218F37F9A64A0529C5E775C6AC59C73EFCAD77FC26DA0E`
- Non-repaint audit SHA-256: `2E1D8FEE3444540792014D124DA40A0264CC744F45EC377BCC4970E88D838012` (`PASS`)
- Focused source test SHA-256: `A0A019EE936CC9C881816E0A65C9A2D681EBCCB5E4FD2F8791D5474F00A58509` (`10 passed`)
- Research cost manifest SHA-256: `0FBFDE0F0BCC4E6F829EAA7812D530AF99106E5641444DF3DD2A390353A06215`

HYP020 never produced admissible economics. HYP021 changes only lifecycle-history stabilization and normal-path journal volume. Signal, entry, exit, risk, account margin decisions, costs and acceptance thresholds are frozen unchanged.

## Market and execution contract

- Platform: MT5/MQL5 through `02. AlphaFactory/alpha.ps1` only.
- Symbol/timeframe: native `XAUUSD`, chart `M15`.
- Tester preload: `2005.01.01` inclusive to `2023.01.01` exclusive, Model `0`.
- Economic TRAIN window: `2018.01.02` through `2022.12.30`, inclusive calendar dates.
- Deposit/leverage/spread: `100000`, `1:100`, current spread semantics with the CLI `-Spread` argument omitted.
- Execution mode/delay/timeout: `0`, `0 ms`, `900 seconds`.
- Run role: `control`.
- Telemetry: tier `trade-only`, profile `lifecycle-v3`.
- Data fingerprint: `B326D511C805C7998DF1C2FC540770B6EC3054D0D4BCBB41A5A4E3C2E4239D25`.
- Account fingerprint: `0A603E7B316F58B39FEA0A1710FE6F250E544909DA2B91967C93AD984317A073`.
- Journal raw-byte cap remains exactly `1,048,576`; `truncated=false` is mandatory. Trade mode emits no per-event `STBS_SIGNAL` rows and no safe per-tick margin rows; lifecycle CSV and the terminal summary remain authoritative. Any cap hit is an engineering failure, never an economic verdict.

Exact overrides:

`InpAuditOnly=false;InpEnableTelemetry=true;InpHypothesisId=HYP-STBS-XAUUSD-M15-021;InpMagic=5604121;InpMaxNewPositionMarginPct=5.0;InpMinProjectedMarginLevelPct=2000.0;InpMoneyFreeEquityFloorPct=1.0;InpMoneyHeadroomReserveFactor=0.20;InpPercentStopoutHeadroomFactor=1.25;InpVariantTag=STBS_H1_FLIP_M15_BURST_TRADE_V8_STABLE_LIFECYCLE`

## Frozen strategy

- Completed native H1 Supertrend 10x3 state flip.
- Decision only at the exact next native H1/M15 open.
- Prior completed M15 ATR14.
- One position, no pyramiding.
- Requested risk: 0.25% equity, downward-only broker volume-step sizing.
- Stop: 1.0 ATR; target: 1.5R; maximum hold: eight completed M15 bars.
- Friday entry cutoff 18:00 UTC; flatten at/after 20:00 UTC and no weekend hold.
- Account-safe margin contract and restart-safe execution/risk state unchanged from V7.
- No direction/session/filter/threshold/SL/TP/sizing/parameter search is allowed.

## Engineering gates before any economic read

All must pass:

1. fresh run compile `0 errors, 0 warnings`, exact source/EX5/config/manifest identity;
2. HQ strictly above 97%, fixed-window/no-skip/series-proof/data/account fingerprints exact;
3. journal `truncated=false`, typed, and contains the terminal summary;
4. `runtime_failed=false`, zero `STBS_FATAL`, zero forced stop-outs and zero margin emergencies;
5. RunMeta identity exact and lifecycle row count equals the CSV data-row count;
6. lifecycle OPEN/CLOSE rows, unique deal IDs, position IDs, volumes and final-close flags reconcile exactly to the tester report;
7. zero orphan positions, pending orders, unmatched closes or unresolved replay tickets;
8. raw/executable/gap/direction/ATR/geometry/margin counts are internally reconciled;
9. no trade outside the frozen economic window;
10. deterministic cost artifact and unified validation rebuild.

Any engineering failure consumes the sole attempt and yields no economic verdict.

## Cost contract

`VERIFIED_RESEARCH_PROXY_NONPROMOTABLE` only:

- historical spread source and coverage exactly as bound in the HYP021 cost manifest;
- commission `4.4` with 335 tester samples;
- direction-aware slippage proxy from 31,176 samples with the frozen x1/x1.5/x2 multipliers;
- this evidence may falsify the candidate but cannot promote or deploy it.

## Economic acceptance

Only after every engineering gate passes:

- completed trades `>= 500`;
- cadence `2–5` trades/week using `((2022-12-30 - 2018-01-02).days + 1) / 7`;
- LONG and SHORT each at least 30%; no calendar year above 30% of trades;
- each calendar year 2018–2022 has positive x1 net R;
- mean x1 net R strictly positive;
- PF after x1 costs strictly greater than `1.30`;
- PF after x1.5 costs at least `1.25`;
- PF after x2 costs at least `1.00`;
- maximum drawdown at most `8%`.

## One-shot authority boundary

- Sole attempt: `STBS021-MODEL0-TRAIN-001`, limit `1`, consumed `0` before execution.
- Durable claim must precede compile, MT5 and bound artifact reads.
- Same-ID retry is forbidden.
- Optimization, WFA, OOS, holdout, Monte Carlo, parameter sensitivity, promotion, paper and live remain unauthorized.
- A clean economic fail opens a materially fresh strategy revision; an engineering fail opens only a bounded implementation/harness child.
