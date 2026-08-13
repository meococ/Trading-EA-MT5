# HYP-ISDS-XAUUSD-M5-001 — economic baseline failure

Verdict: `KILL_BASE_PF_EXPECTANCY_AND_CADENCE_FAIL`

The source-passed intraday serial-dependence switch completed its sole untuned
FivePercent XAUUSD M5 Model-0 baseline. Source parity, closed-bar causality,
history quality and runtime integrity passed. The economic mapping failed
materially after tester spread and commission.

## Verified result

- run: `20260811_132554`
- history quality: `99%`; journal truncation: `false`
- source/runtime identity: raw `1275`, LONG `626`, SHORT `649`
- runtime: `runtime_failed=false`, `clock_rejects=0`
- completed trades: `386` (`195` LONG, `191` SHORT); entry rejects: `8`
- elapsed cadence: `1.479737/week` — FAIL `2..5`
- PF: `0.6569217522` — FAIL `>1.30`
- expectancy: `-$20.117513/trade` — FAIL `>0`
- net profit: `-$7,765.36`
- win rate: `34.7150%`
- analyzer trade-path drawdown: `7.9322%`; native report equity DD reached the
  frozen `8.00%` lock boundary — risk gate behaved as designed.

The frozen 8% peak-equity entry lock suppressed later entries after the losing
book approached its risk ceiling. Removing or loosening that lock after seeing
the run would be an outcome-informed execution rescue and is prohibited.

## Evidence

- run manifest SHA256:
  `537FD37BDE9C65A84DB6281427CB565C96930DD5933C2FB02130BA8BC8B635F1`
- report SHA256:
  `5D15256EBAF89AFED3924A1CBB3692071395758A73158C81147876494E1E0C48`
- journal SHA256:
  `D6CD16A9BB5EEE0680F6E3C5A0791DDD5752A5D12A40E61DB8EC7BE9B871EDD6`
- enhanced summary SHA256:
  `7338F6BED1AA82E668BB10F8623AD4BCD13398058F2DC6928C84460A1FBB0D18`
- non-repaint audit: PASS, zero findings.

Before the economic run, the manual reviewer found TP tick rounding toward the
entry, which violated the frozen 1.50R mapping. That implementation defect was
fixed to round the target outward, covered by a focused test, recompiled at
0 errors/0 warnings and re-audited before MT5 outcomes were opened. Two Alpha
invocations then failed before compile/backtest because of a truncated receipt
SHA and an incorrectly reproduced Git-status hash; neither produced a run or
informed strategy logic.

## Failure radius and prohibition

This kills the exact complete-session lag-1 return-correlation regime switch,
six-interval recent-return direction, 12-bar structural stop, 0.20 ATR buffer,
1.5R target, 20:00 UTC flatten and frozen risk locks on XAUUSD M5, 2018–2022.

No rho threshold, recent-window change, persistent/anti-persistent deletion,
weekday/session/direction filter, stop/target/hold/risk-lock change or subgroup
rescue is allowed under this ID. Cost stress, optimization, validation,
holdout, paper and live remain closed. The overall EA goal remains active; the
next lane must use a materially fresh information mechanism.
