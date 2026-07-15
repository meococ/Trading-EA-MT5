# Probe contract — WTI ToT USDCAD + WALCL QT RR2 gate V1

Status: `JOIN_CONTRACT_FROZEN / OFFLINE_EXECUTED / BOTH_KILL / NO_EA`

## Authority

Post COT size-budget KILL + Wave7 empty. Solo lead memo
`readouts/20260714_POST_SIZEBUDGET_LEAD_MEMO.md`. GPT waived.

## Objects

### O1 `HYP-USDCAD-H1-WTI-TOT-CONT-001`

- Panel: `panels/fred_wti_dcoilwtico_d1_v1.csv` SHA
  `21148C9B8AEC5109814AA292082B608CAA76A5067DB90742061022521BA0E853`
- Lag: observation + 1 calendar day
- Signal: |z|≥0.75 on prior-60 WTI → oil-up short USDCAD / oil-down long;
  H1 displace body≥0.5·ATR ∧ range≥1.0·ATR; SL 1.2·ATR; RR=2; max-hold 12
- Result: **KILL** N=635 PF 0.9494 tpw 2.43 x1.5 0.8906

### O2 `HYP-RR2-WALCL-QT-ALLOW-GATE-001`

- Panel: `panels/fred_walcl_wow_w1_v1.csv` SHA
  `D2D3376916725A703FBF3FDC3BEF13AD1F608F2EB0A3AE3B23AFFA56BD69956F`
- Lag: observation + 2 calendar days
- Gate: allow frozen RR2 `194548` trades only when latest available WALCL
  wow_pct < 0 (QT); fail-closed if missing
- Result: **KILL** N=318 PF 1.2758 tpw 1.22 x1.5 0.9539 lift −0.060

## Explicit non-actions

No T10YIE RR2 z-gate · no HY OAS/MOVE/DTWEX · no COT |z|/size retune ·
no WTI/WALCL threshold mine · no Model 0.
