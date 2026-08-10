# HYP-DCX-XAUUSD-M15-001 — Sole TRAIN Baseline Result

## Verdict

`KILL_BASE_PF_EXPECTANCY_AND_CADENCE_FAIL`

This verdict applies only to the frozen XAUUSD M15 Donchian-20 transition entry with Chandelier-22x3 initial/trailing stop, one entry per broker-server day, 0.25% equity risk, and the exact 2010-01-04 through 2018-01-01 Model-0 mapping.

## Artifact identity

- Alpha run: `02. AlphaFactory/runs/EA_DonchianChandelierBreakout/20260810_181302`
- Source snapshot SHA256: `A4BE71F1A1F98DCDE3C181C8BDF60017CA981816F0871D5CAC281565132FB94F`
- Run manifest SHA256: `00C3D4B421B5C0E7EBFBEFE09B960EF020BD497DFB4441964E2EE4B61BD03460`
- Tester report SHA256: `88DF63F15BA26E72F1110607F2C09C5BCA934EB9E6D7D6C086A2E008F497A38D`
- Enhanced summary SHA256: `80AE2254AA026615EE6F0521F53AECECAE56F33781A0DD75CBEAB8570B9E1E89`
- Analysis report SHA256: `ACF890A52E0CE8A0DF464ABC5C5036053EB98D82C41EC3691DCF626BB6970236`
- Contract receipt SHA256: `EB9CA882F605155E31EA1925ECFFB5D7C22F2390B7018429369C636AB55D509C`
- Run data fingerprint: `0B4CCBFF3EC8C457FA6BC4EE4946BA0D628F6078D66F8F1F0BC9E068049F5829`
- Tester fingerprint: History Quality 97%, 183,719 bars, 190,128,095 ticks.

## Frozen gate readout

| Gate | Result | Verdict |
|---|---:|---|
| Closed positions | 267 | Evidence available |
| Profit factor | 0.7272293276 | FAIL, required > 1.30 |
| Net profit | -7,473.54 USD | FAIL |
| Expectancy | -27.9908 USD/trade | FAIL, required > 0 |
| Cadence | 0.640288/week over exactly 417 weeks | FAIL, required 2–5/week |
| Max drawdown | 7.73897% | PASS the isolated <=8% ceiling |
| Win rate | 31.0861% | Descriptive only |

The tester baseline is already materially negative before adding the research slippage stress. Non-negative additional costs cannot rescue this mapping. The cost-source manifest remains explicitly blocked for TRAIN-window economic acceptance, so this result is an exact baseline falsification, not an `economic-valid` or promotion-ready artifact.

## Failure radius and prohibited rescue

- Do not keep only Tuesday, remove Asia/Europe, remove specific hours/weekdays, change direction, adjust the Donchian/ATR periods, change the Chandelier multiple, add a target, or change risk based on this readout.
- Do not open validation, holdout, optimization, Monte Carlo, WFA, paper, or live stages.
- A later strategy may reuse the general concepts only under a fresh hypothesis whose market mechanism is materially different and preregistered before outcomes.

## Next action

Independent post-result review must confirm the KILL and de-duplicate the next mechanism against the registry/failure catalog. The active goal continues with a fresh strategy rather than a DCX revision.
