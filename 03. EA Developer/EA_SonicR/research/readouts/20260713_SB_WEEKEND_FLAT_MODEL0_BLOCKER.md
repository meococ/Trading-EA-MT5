# HYP-SB-WEEKEND-FLAT-001 Model 0 Blocker — 2026-07-13

Status: RESEARCH_FROZEN / COMPILE_OK / MODEL0_BLOCKED_UNRELATED_TERMINAL

## Authority

Owner self-research (no ChatGPT) + unlimited-GOAL. Public exogenous campaign
is NO_LEGAL_LOCAL_CANDIDATE. This lane is a **management-only** A1 weekend-flat
challenger on the historical SilverBullet USDJPY cadence seed — not a carry/COT
rescue and not an open-range rename of S678.

## Done

- Research freeze: preregs/20260713_H_SB_WEEKEND_FLAT_001_RESEARCH_FREEZE.md
- Control ContractReceipt (spread=current; NOGIT includes active
  EA_M15HourOpenBreak.mq5 per lpha.ps1):
  preflight/sb_weekend_flat/20260713_HYP_SB_WEEKEND_FLAT_001_CONTROL_RECEIPT.json
- Compile: EA_SilverBullet SUCCESS (MetaEditor 0 errors; EX5 produced)

## Blocker

Assert-NoUnrelatedTerminal fail-closed:
	erminal64.exe PID **53760** at C:\Program Files\MetaTrader 5\terminal64.exe
is running and is **not** runner-owned. AlphaFactory will not stop it.

## Needs Owner (hard)

Close that MetaTrader 5 instance (or explicitly authorize stopping PID 53760),
then re-run Model 0 control:

`	ext
alpha.ps1 backtest EA_SilverBullet -Symbol USDJPY -Period M15
  -From 2021.01.01 -To 2025.12.31 -Model 0 -Deposit 100000
  -HypothesisId HYP-SB-WEEKEND-FLAT-001 -RunRole control
  -Overrides InpUseWeekendFlat=0
  -ContractReceipt <receipt> -ContractReceiptSha256 <hash>
`

Then build challenger receipt (InpUseWeekendFlat=1;InpFridayFlatHour=21;InpFridayFlatMinute=45)
and matched Model 0 challenger.

## Explicit non-claims

- No run_id yet; GOAL unmet.
- Cost manifest remains research-proxy; promotion still needs FivePercentOnline-Real.
- EA_M15HourOpenBreak is a parallel scaffold near S678; treat as de-dup risk
  until a separate offline probe survives — not this lane's authority.
