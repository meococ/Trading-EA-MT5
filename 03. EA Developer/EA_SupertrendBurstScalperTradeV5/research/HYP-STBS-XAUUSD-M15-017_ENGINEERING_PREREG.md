# HYP-STBS-XAUUSD-M15-017 — canonical-override outer audit

Frozen before the fresh outer receipt, AlphaFactory compile, MT5 launch, report parsing or any economic outcome.

## Identity and failure-informed boundary

- Outer hypothesis: `HYP-STBS-XAUUSD-M15-017`
- Inner MQL identity: `HYP-STBS-XAUUSD-M15-016`
- EA/source: unchanged `EA_SupertrendBurstScalperTradeV5`, SHA-256 `3822EED82C8D484CE8010A496767271DED20528158D68509B46EF934B043D918`
- Magic: unchanged `5604116`
- Parent: terminal HYP016 raw row `3CED3A5D29DEE9A5DC424C104DCBC92DC06F2D6CC0CDEE845E3643E581DFCCCC`
- Parent failure: receipt/invocation override ordering mismatch before compile or MT5; no source, market-data, report, order, outcome or economic result was opened.

This is an outer harness revision only. It does not change signal logic, margin formula, account capital, execution geometry, thresholds or acceptance gates.

## Frozen override mapping

The CLI declaration preserves HYP016's human-authored order:

`InpAuditOnly=true;InpHypothesisId=HYP-STBS-XAUUSD-M15-016;InpMagic=5604116;InpMaxNewPositionMarginPct=5.0;InpMinProjectedMarginLevelPct=2000.0;InpPercentStopoutHeadroomFactor=1.25;InpMoneyHeadroomReserveFactor=0.20;InpMoneyFreeEquityFloorPct=1.0;InpVariantTag=STBS_H1_FLIP_M15_BURST_AUDIT_V5_ACCOUNT_SAFE`

AlphaFactory telemetry profile `none` parses the map and emits the exact sorted effective string below. The receipt, authority and manifest must bind this canonical value:

`InpAuditOnly=true;InpHypothesisId=HYP-STBS-XAUUSD-M15-016;InpMagic=5604116;InpMaxNewPositionMarginPct=5.0;InpMinProjectedMarginLevelPct=2000.0;InpMoneyFreeEquityFloorPct=1.0;InpMoneyHeadroomReserveFactor=0.20;InpPercentStopoutHeadroomFactor=1.25;InpVariantTag=STBS_H1_FLIP_M15_BURST_AUDIT_V5_ACCOUNT_SAFE`

A focused regression must reproduce AlphaFactory's parse/duplicate-reject/sorted serialization and prove the two frozen strings map to the same exact key/value set.

## Sole engineering run

Authorize exactly one `STBS017-MODEL0-AUDIT-001` attempt:

- XAUUSD M15, `2005.01.01` through `2023.01.01`, Model 0;
- execution mode 0, fixed delay 0, timeout 900 seconds;
- deposit USD 100,000, leverage 1:100, current spread by omitting `-Spread`;
- outer Alpha/receipt/manifest identity HYP017; inner journal identity HYP016;
- control role, telemetry profile none/off, audit-only true.

## Acceptance and kill gates

All HYP016 engineering gates remain exact:

- history quality strictly above 97%, exact frozen data/broker/server/account fingerprints and series proof;
- journal `truncated=false`; exactly two identical summaries and uniform duplicate multiplicity;
- raw/executable/gap/LONG/SHORT `690/683/7/339/344`;
- ATR-ready, geometry-ready and margin-ready each `683`;
- every exact event has positive volume and `projected_free >= required_free`; zero rejects/emergencies/stop-outs/runtime failures;
- zero orders and trades; report contains only the exact initial funding balance row; no LifecycleTrades or RunMeta sidecar;
- any failure consumes HYP017; same-ID retry is forbidden.

No PF, return, outcome price, optimization, validation, holdout, paper/live, deployment or market-edge authority is granted. A clean audit authorizes only a fresh trade-enabled economic child.
