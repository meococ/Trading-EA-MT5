# HYP-STBS-XAUUSD-M15-019 — one untuned Model-0 economic baseline

Status: `FROZEN_PRE_OUTCOME`

## Thesis and revision boundary

A completed native H1 Supertrend-10x3 state flip may retain enough next-open
continuation for one short M15 burst trade. Entry occurs only at the exact next
native M15 open. The prior completed M15 ATR14 supplies a 1.00 ATR stop; target
is 1.50R; requested-price equity risk is 0.25%; maximum hold is eight completed
M15 bars. One owned position only, no pyramid, trailing or breakeven. Friday
entries stop at 18:00 UTC and exposure is flattened by 20:00 UTC/weekend.

HYP019 is a fresh trade-enabled economic child of terminal HYP018, raw row
SHA256 `6DB679E3FDE7D7D0D11A4C942C4E89B986ECAFD96C5877353A367266DA044A41`.
HYP018 passed the complete zero-order Model-0 audit but V5 intentionally
hard-required audit-only mode. V6 changes only package/identity/magic,
telemetry defaults and the frozen OnInit guard from audit-only to trade-enabled.
Every signal, Supertrend, ATR, geometry, lifecycle FSM, stop/target/hold,
session, persistent risk-anchor and account-safe margin function remains exact.

- EA: `EA_SupertrendBurstScalperTradeV6`.
- Source SHA256: `067633008AC0B88E56B15825DFA5226822D25C2B6E49AAC62AFFA6732D89F477`.
- Exact overrides: `InpAuditOnly=false;InpEnableTelemetry=true;InpHypothesisId=HYP-STBS-XAUUSD-M15-019;InpMagic=5604119;InpMaxNewPositionMarginPct=5.0;InpMinProjectedMarginLevelPct=2000.0;InpMoneyFreeEquityFloorPct=1.0;InpMoneyHeadroomReserveFactor=0.20;InpPercentStopoutHeadroomFactor=1.25;InpVariantTag=STBS_H1_FLIP_M15_BURST_TRADE_V6_ACCOUNT_SAFE`.
- No parameter, threshold, session, direction, stop, target, hold or risk search.

## Execution contract

- XAUUSD native M15, FivePercentOnline-Real.
- Model 0, execution mode 0, fixed delay 0, current tester spread.
- Preload/tester window: 2005.01.01–2023.01.01.
- Economic window: inclusive 2018.01.02–2022.12.30; preload advances
  recursive state only. Any trade outside the economic window invalidates the
  baseline instead of being deleted.
- Deposit USD 100000, leverage 1:100, nonvisual, timeout 900 seconds.
- Telemetry profile `lifecycle-v3`, Alpha tier `trade-only`.
- Exactly one baseline attempt. Same-ID retry is forbidden.

Engineering gates precede economics: compile 0 errors/0 warnings; exact source,
EX5, config, manifest, account and B326 data identities; no runtime fatal;
RunMeta audit=false/promotion=false/runtime_failed=false; lifecycle rows match
report deals and positions; every opened position has one final close; zero
orphan/pending exposure, emergency margin exit or broker stop-out. Any failure
is engineering-only and makes PF inadmissible.

## Cost evidence and ceiling

The frozen HYP019 cost manifest reuses pre-outcome HYP013 research sources:
full historical XAUUSD M1 bid/ask coverage, USD 4.40/lot maximum tester
round-turn commission, and direction-aware 1000 ms adverse executable-quote
proxy p90 of 80 XAU pips round trip. It updates only HYP019 identity/magic and
the 100000-account fingerprint.

This is `RESEARCH_PROXY`: it includes spread, commission and dynamic slippage
stress and can economically falsify the baseline, but observed fills are still
missing. Even a PASS is not promotion, paper or live ready.

## Exact baseline gates

- at least 500 completed positions;
- 2.0–5.0 positions/week over the inclusive window;
- BUY and SELL each at least 30%;
- no exit year above 30%, and every year 2018–2022 positive at x1 cost;
- mean x1 net R strictly positive;
- x1 cost PF strictly greater than 1.30;
- x1.5 PF at least 1.25 and x2 PF at least 1.00;
- maximum equity drawdown at most 8%.

PASS may open robustness/OOS. FAIL parks HYP019 and triggers independent
mechanism analysis; no readout-mined rescue is allowed.
