# HYP-DMR-XAUUSD-M15-002 — economic baseline failure

## Verdict

`KILL_BASE_PF_EXPECTANCY_AND_YEAR_CONCENTRATION_FAIL`

The sole untuned Model-0 run `20260810_225818` is engineering-valid and economically fails the frozen baseline contract.

## Engineering evidence

- Source SHA256: `D9A86E175E29C2A7BC3913588B8E5CC00A26EDA1564487F82B5EA0F8AE8BA970`.
- Manifest SHA256: `359E2DD919538CA47D0F9B686E512E0690D827CF1DBAB9C966B47289663BBB23`.
- Report SHA256: `D14802163D19EBD7706B7CF41432CE8CD4F46366301B3A08AAB31EA3CE8276D6`.
- Journal SHA256: `1678B9A58F7E648BD9BA655FA91693E6CCA93B5A841EDCA69347844E79EAA9F1`.
- HQ `99`, `FULL_2018_PLUS`, exact DQ matches `2`, distinct range `1`, journal nontruncated.
- Two identical summaries: closed bars `117789`, raw `8008`, LONG `4055`, SHORT `3953`, entries `843`, rejects `7067`, broker-geometry rejects `14`, clock rejects `98`, invalid `0`, `runtime_failed=false`.

## Frozen economic gates

- Completed positions: `843` (`320` wins / `523` losses).
- Gross profit/loss: `15106.96` / `22069.30`.
- Profit factor: `0.6845237501869113` — FAIL versus strict `>1.30`.
- Net after tester-report costs: `-6962.34`; expectancy `-8.2590035587` per trade — FAIL.
- Commission: `-669.86`; swap `0`.
- Cadence: `3.2316538883/week` over `260.8571428571` weeks — PASS `2–5/week`.
- Direction shares: BUY `432` (`51.2456%`), SELL `411` (`48.7544%`) — PASS.
- Calendar years: 2018 `258`, 2019 `258`, 2020 `259`, 2021 `68`, 2022 `0`; maximum share `30.7236%` — FAIL strict `<=30%`.
- Max equity drawdown: `7.9518664494%`; the frozen 8% peak-equity latch then prevented later entries. This is part of the preregistered object, not a post-run rescue target.

## Failure radius

Kill the exact XAUUSD M15 native DeMarker14 re-entry through 0.30/0.70 with five-bar extreme plus 0.20 ATR stop, 1.50R target, 12-bar exit and one accepted entry/day. Do not rescue it with session/hour/weekday/direction selection, DeMarker period/threshold changes, stop/target/hold/risk changes, removing the daily cap or disabling the drawdown latch. Validation, WFA, OOS and holdout remain unopened.
