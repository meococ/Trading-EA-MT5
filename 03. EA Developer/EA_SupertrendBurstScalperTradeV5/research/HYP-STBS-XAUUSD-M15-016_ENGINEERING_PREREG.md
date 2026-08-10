# HYP-STBS-XAUUSD-M15-016 — account-compatible bounded-journal audit

Frozen before compile, MT5 launch, report parsing or economic outcome for this identity.

## Identity and parent

- Hypothesis: `HYP-STBS-XAUUSD-M15-016`
- EA: `EA_SupertrendBurstScalperTradeV5`
- Parent: terminal HYP015 raw row `E611136E39A8BC6336DFC06995458239EB231BBE5456C1B9B4E685404658E472`
- Source SHA-256: `3822EED82C8D484CE8010A496767271DED20528158D68509B46EF934B043D918`
- EA contract SHA-256: `E15F88FB996D995D34A912714BBDAA4452893C705CE2B1096E6FCC38D96C3980`
- V4/V5 bounded-diff proof SHA-256: `9516B9587F0EA8AA01DDC78E8F4C7F671A8CECB777C64E8F4A3CE3C60158F55C`
- Expected USD 100,000 account fingerprint: `0A603E7B316F58B39FEA0A1710FE6F250E544909DA2B91967C93AD984317A073`
- Fresh magic: `5604116`
- Variant: `STBS_H1_FLIP_M15_BURST_AUDIT_V5_ACCOUNT_SAFE`

HYP015 was not an economic trial. Its zero-send audit was rejected because the two-root tester journal was truncated, and every captured exact signal was margin-unready under a USD 10,000 deposit below the FivePercent USD 92,000 / USD 90,000 money thresholds.

## Only authorized source changes

Signal, state and trade geometry are unchanged from V4: completed H1 Supertrend 10x3 flip, exact next native M15 decision open, prior completed M15 ATR14, 1.00 ATR stop, 1.50R target, 0.25% maximum requested risk, eight completed M15 bars, Friday rules, lifecycle FSM and order gateways.

V5 changes only the account-risk and audit-evidence boundary:

1. The tester uses USD 100,000 / 1:100, matching the established account class.
2. In money stop-out mode, `protected=max(SO_CALL,SO_STOP)`, `reserve=max(0.20*(equity-protected),0.01*equity)`, and `required_free=protected+reserve`. Candidate projected free margin and projected equity-minus-margin must both meet `required_free`. Volume is reduced by broker step only and remains capped by 5% of equity; the minimum volume is rejected.
3. The identical money-mode formula is used after a visible fill. Percent-mode retains V4's `max(2000%,1.25*declared)` rule.
4. Audit-only suppresses per-candidate margin/reject prints and emits one compact deterministic signal record containing source/decision epochs, direction, exact-next/readiness, final volume, projected free margin and required free margin. Trade-mode diagnostics remain unchanged.

At USD 100,000 equity with call/stop USD 92,000/USD 90,000, reserve is USD 1,600, required free margin is USD 93,600, gross margin capacity is USD 6,400, and the existing 5% cap limits a new position to USD 5,000 margin.

## Sole engineering run

After compile 0 errors / 0 warnings, tests, non-repaint PASS and independent review, authorize exactly one `STBS016-MODEL0-AUDIT-001` run:

- XAUUSD M15; `2005.01.01` through `2023.01.01`; Model 0;
- execution mode 0, fixed delay 0, timeout 900 seconds;
- deposit USD 100,000, leverage 1:100, current spread by omitting `-Spread`;
- control role, telemetry profile none/off;
- exact override: `InpAuditOnly=true;InpHypothesisId=HYP-STBS-XAUUSD-M15-016;InpMagic=5604116;InpMaxNewPositionMarginPct=5.0;InpMinProjectedMarginLevelPct=2000.0;InpPercentStopoutHeadroomFactor=1.25;InpMoneyHeadroomReserveFactor=0.20;InpMoneyFreeEquityFloorPct=1.0;InpVariantTag=STBS_H1_FLIP_M15_BURST_AUDIT_V5_ACCOUNT_SAFE`.

## Fatal acceptance gates

- History quality strictly above 97%, exact frozen XAUUSD population fingerprint and complete series proof.
- Journal `truncated=false`, exactly two identical summaries and uniform duplicate multiplicity across the two captured journal roots.
- Raw/executable/gap/LONG/SHORT counts exactly `690/683/7/339/344`.
- ATR-ready, geometry-ready and margin-ready each exactly `683`.
- For every exact event: positive final volume, `projected_free >= required_free`, required-free formula consistent with the account contract; zero margin rejects, emergencies, forced stop-outs or runtime failure.
- Zero market orders and trades; report contains only the exact tester-start funding balance deal; no lifecycle or RunMeta sidecar.
- Any failure consumes this ID and creates a terminal engineering verdict. Same-ID retry is forbidden.

No PF, return, optimization, validation, holdout, paper, live, deployment or market-edge authority is granted. A clean audit permits only a fresh trade-enabled economic child.
