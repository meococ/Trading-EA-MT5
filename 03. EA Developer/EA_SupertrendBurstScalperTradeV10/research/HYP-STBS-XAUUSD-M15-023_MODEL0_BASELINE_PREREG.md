# HYP-STBS-XAUUSD-M15-023 — Frozen Model-0 baseline preregistration

## Hypothesis and lineage

- Hypothesis: `HYP-STBS-XAUUSD-M15-023`
- EA: `EA_SupertrendBurstScalperTradeV10`
- Parent: terminal `HYP-STBS-XAUUSD-M15-022`
- Parent terminal raw-row SHA-256: `91A68A5C36EA19F62F12896C4F96A05426D62C13DBCD8EF3F4F8DBB34F56409E`
- Parent verdict: `KILL_GOVERNANCE_PRE_PACKET_BUILDER_SELF_HASH_AUTHORITY_CYCLE_NO_ATTEMPT_NO_ECONOMIC_VERDICT`
- Source SHA-256: `4B481CE867DB8A9F9E02AB218FEA50C88FD37A48B8ECB92E2048418DB7F7769B`
- EX5 SHA-256: `4A1639156AB77A8A82CF59A5A65693BFBA751AB9574E6BC4981E70E0BB10AD64`
- Compile log SHA-256: `7A42C5F208DCDD3481009D78ECB34BA34A4C54C032D86A8C02FA98495BB92692`, exactly one `0 errors, 0 warnings`
- Identity-only diff proof SHA-256: `80B199795BA970CA651789532C4158BF0498FEE8B00F238437F6019754333BCE`
- Non-repaint auditor SHA-256: `366D70F0C6FAF02F85B4819E7305CD1BD271BA6A78B4789CF0DCDF2FB651E360`
- Non-repaint manifest SHA-256: `2FD0CB06E4273671994A7D6B105701FC78AFAC37536E111D791519D99CF2086D`
- Non-repaint audit SHA-256: `7E281A579EB6DE5E90C5263BA6E5E064015A96231753C217DE592CA6AE641053` (`PASS`)
- Identity/risk test SHA-256: `0AD401B327A7D454FFA4CA59B2AA06F8545F39F198EB19D7BF2156637776F63E`
- Runner/adapter/builder test SHA-256: `0083D488D0E86177BAAC3B430BB0C9034CD5A395EA4AEA7C4790C55BB0DA6EC6`
- Packet-attempt ignore contract SHA-256: `AB52FF98D7479D29EFA5C324622C77E9929E42939B5C3738C8FFDBB6B6C0B85C`
- Focused tests: `45 passed`
- Research cost manifest SHA-256: `9EE403BA01896DBC94EA271B2E2FE6EF9BB96E3D8EA1D21E510C2D504F137A97`
- HYP023 runner SHA-256: `95D211A6CEC5915C3B47B304B932C4F3665F0ECC5048C8A92ED15C10D41FABA5`
- Frozen shared Alpha SHA-256: `BC570A1EA7D8788AC9483A7133565893C8B679ADE9A0ED85E2B8AF8B3A0F02FC`

HYP022 opened no packet, MT5, market data or economics. HYP023 is an identity-only governance child. It preserves the reviewed V9 strategy and risk bytes and corrects only the pre-packet builder authority construction.

## Frozen strategy and risk

- Completed native H1 Supertrend 10x3 state flip; decision only at the exact next native H1/M15 open.
- Prior completed M15 ATR14; one position; no pyramiding.
- Requested risk 0.25% equity; downward-only broker-step sizing.
- Stop 1.0 ATR; target 1.5R; maximum hold eight completed M15 bars.
- Friday entry cutoff 18:00 UTC; flatten at/after 20:00 UTC; no weekend hold.
- Candidate admission uses BUY requested entry plus 20 points or SELL requested entry minus 20 points, full 4.4/lot round-turn charge reserve, and the maximum required margin at requested entry/worst fill/SL.
- Existing 5%-equity new-position margin ceiling and frozen percent/money headroom formulas apply to the stressed state.
- Gaps outside the frozen fill/SL/charge envelope remain engineering-fatal through unchanged `EvaluateActualMargin`.
- No signal, direction, session, hour, weekday, filter, SL, TP, hold or indicator search.

## Run-local non-repaint adapter

The shared `alpha.ps1` is byte-frozen. The HYP023 runner calls it for compile/backtest, preserves the original run manifest, and writes only an analysis-local derivative that adds the exact nondecision `DATA_EPOCH_D0` CopyTime authority. Runtime acceptance requires the frozen auditor and derivative manifest path/SHA, `collection_authority_verified=false`, one exact V10 source, zero findings and one exact line-678 `collection_first_date_copytime` allowance, followed by final rehash.

## Market and execution contract

- Native `XAUUSD`, chart `M15`; tester preload `2005.01.01` inclusive to `2023.01.01` exclusive; Model `0`.
- Economic TRAIN window: `2018.01.02` through `2022.12.30`, inclusive dates.
- Deposit/leverage/spread: `100000`, `1:100`, current-spread semantics with CLI `-Spread` omitted.
- Execution mode/delay/timeout: `0`, `0 ms`, `900 seconds`.
- Run role `control`; telemetry tier `trade-only`, profile `lifecycle-v3`.
- Data fingerprint `B326D511C805C7998DF1C2FC540770B6EC3054D0D4BCBB41A5A4E3C2E4239D25`.
- Account fingerprint `0A603E7B316F58B39FEA0A1710FE6F250E544909DA2B91967C93AD984317A073`.
- Journal cap exactly `1,048,576` raw bytes; `truncated=false` mandatory.

Exact overrides:

`InpAuditOnly=false;InpEnableTelemetry=true;InpHypothesisId=HYP-STBS-XAUUSD-M15-023;InpMagic=5604123;InpMaxNewPositionMarginPct=5.0;InpMinProjectedMarginLevelPct=2000.0;InpMoneyFreeEquityFloorPct=1.0;InpMoneyHeadroomReserveFactor=0.20;InpPercentStopoutHeadroomFactor=1.25;InpVariantTag=STBS_H1_FLIP_M15_BURST_TRADE_V10_SL_STRESSED_MARGIN`

## Engineering gates before economics

All must pass: fresh run compile 0E/0W and exact snapshots; exact runtime non-repaint contract; HQ >97 with full series proof and fingerprints; nontruncated terminal journal with runtime_failed=false; zero fatal/stopout/margin emergency/orphan/unresolved replay; RunMeta/lifecycle/report reconciliation; all trades inside TRAIN; deterministic verified-cost and unified rebuild.

Any engineering failure consumes the sole attempt and yields no economic verdict.

## Economic acceptance

Cost tier remains `VERIFIED_RESEARCH_PROXY_NONPROMOTABLE`: frozen historical spread, commission `4.4`, and direction-aware 1,000 ms adverse quote proxy.

Only after engineering PASS:

- completed trades `>=500`;
- cadence `2–5` trades/week using `((2022-12-30 - 2018-01-02).days + 1) / 7`;
- LONG/SHORT each `>=30%`; no year above `30%` of trades;
- every calendar year 2018–2022 positive at x1 cost and mean x1 net R strictly positive;
- PF x1 strictly `>1.30`; PF x1.5 `>=1.25`; PF x2 `>=1.00`;
- maximum drawdown `<=8%`.

## One-shot authority boundary

- The first `probe` is packet-build-only authority: `PACKET_BUILD_ONLY_NO_EXECUTION_NO_ECONOMICS`. It must set `packet_build_authorized=true`, bind `STBS023-PACKET-BUILD-001` with limit one/consumed zero, keep `run_ids=[]`, and keep every MT5, compile, trading, artifact/comparator, outcome, performance, economics, optimization, validation, holdout, paper, promotion, live, retry and registry-mutation permission explicitly false.
- The packet builder must create and fsync its exclusive `attempt_started.json` before reading any frozen artifact or registry bytes. The task packet itself is opened once with `xb`; success or failure writes an exclusive terminal, and any crash residue or existing packet permanently blocks the same attempt ID.
- The screened successor must set packet-build attempts consumed to one and bind the exact start and COMPLETE terminal paths/SHAs. After the separate Model0 claim, the runner locks and verifies terminal-to-start, terminal-to-packet, packet-to-start, `.gitignore`, exact IDs/root, no-error status and `packet start <= packet terminal <= screened authority <= Model0 claim` chronology before AlphaFactory execution.
- Sole attempt: `STBS023-MODEL0-TRAIN-001`, limit one, consumed zero before execution.
- The packet builder must validate a packet-only `probe` authority semantically and require that row to bind the builder's exact current SHA. It must not pre-know or inject a raw-row hash. Only after the packet is sealed may a normal `probe→screened` successor bind the packet and authorize execution.
- Durable claim precedes compile, MT5 and bound artifact reads; same-ID retry is forbidden.
- Optimization, WFA, OOS, holdout, Monte Carlo, sensitivity, promotion, paper and live remain unauthorized.
