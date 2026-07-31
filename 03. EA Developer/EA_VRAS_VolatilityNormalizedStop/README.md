# EA_VRAS_VolatilityNormalizedStop

Canonical HYP006 matched-pair package testing whether ATR-normalized structural stops fix HYP005's premature fixed-clamp stop-outs. Research-only; not authorized for live use.

The entry is intentionally the actual HYP005 closed-bar H1 EMA200 plus 48-bar rolling M5 VWAP reclaim/path condition. The only arm-level change is stop geometry. Shared telemetry and guard repairs are mandatory validity infrastructure, not challenger alpha.

HYP007 is a separate, non-promotable full-horizon diagnostic requested after the 6% account-DD latch censored both HYP006 arms in March 2019. It disables only the account-DD **entry halt** in Strategy Tester, keeps measuring the 6% threshold and realized DD, and uses 0.05% fixed-fraction risk to avoid broker stop-out over 2019–2022. Default and non-tester behavior remains fail-closed with the DD halt enabled.

HYP007 still hit the FivePercent tester/account stop-out at about 10% loss and 44% of the chart, so it is terminal invalid. HYP008 is the frozen tester-survival successor: deposit USD 500,000 and risk 0.01% preserve the same approximate USD 50 initial cash-risk budget while lifting the account-level stop-out floor. This scaling is diagnostic infrastructure, not a strategy improvement.

HYP008 completed both full-window Model-0 arms and is terminal `FULL_HORIZON_CONFIRMS_NO_EDGE_BOTH_ARMS_NEGATIVE`. Control: N4,841/PF0.7736/gross price PF0.8803/meanR-0.1096/DD5.31%. ATR-structural challenger: N3,611/PF0.7722/gross price PF0.8870/meanR-0.1184/DD4.28%. The nominal 1.5R target realizes only payoff1.0586 and needs WR48.58% versus 42.20% observed. The 24-bar hold rule also pauses over market closure, producing Friday-Monday gap tails. These are terminal diagnostic findings, not authority to retune or deploy.
