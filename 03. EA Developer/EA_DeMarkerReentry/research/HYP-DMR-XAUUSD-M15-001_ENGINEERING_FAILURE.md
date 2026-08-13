# HYP-DMR-XAUUSD-M15-001 — engineering failure

## Verdict

`KILL_ENGINEERING_ORDER_CHECK_INVALID_STOPS_NO_FULL_WINDOW_ECONOMIC_VERDICT`

The sole Model-0 run `20260810_224300` is not an admissible full-window economic baseline. The tester reached the end of the requested window, but the EA set `runtime_failed=true` after `OrderCheck` returned error `4806`, retcode `10016`, comment `Invalid stops` at `2018-05-10 07:45:00`.

## Bound evidence

- Source SHA256: `6664BA3C441799ED89DB48CAB19126D6012C74F834FAD5DAD0634F65A5B1659E`
- Run manifest SHA256: `A1E888FE8C9F27A38C7A6586A49D38B5488B09580D411AA9D256710C9E69C826`
- Report SHA256: `50C35DBDEEB7F9076230B9DBE2BC361C5BEC8E82135A9767547464CC897CA69A`
- Journal SHA256: `AEB0D15A53216F74B3D4E6002030C0FBCC5FBE44CC8C0CBB9662B15FE9DE6C4E`
- Enhanced summary SHA256: `8C31F104245AA81EA8F291312DCA7391AA4BEDB3052E91F662934A9E33BFAB24`
- Data quality: HQ `99`, fixed-window coverage class `FULL_2018_PLUS`, journal nontruncated, two identical tester/agent summaries.
- Exact journal summary: closed bars `117789`, raw events `8008`, LONG `4055`, SHORT `3953`, entries `91`, clock rejects `98`, runtime failed `true`, reason `1`.

## Non-economic diagnostic only

The 91 positions completed before the fatal event produced PF `0.7086013139695712`, net `-2359.63`, expectancy `-25.93`, 33 wins and 58 losses. All entries were in 2018 and the last exit was `2018-05-09`. These values are diagnostic only; they do not establish a five-year PF or a market-edge verdict.

## Failure radius and lawful next action

The entry preflight compared stop distance to the requested Ask/Bid entry. MT5 validates a BUY protective stop relative to the current Bid and a SELL protective stop relative to the current Ask. Spread can therefore make a nominally acceptable structural stop invalid at `OrderCheck`.

No threshold, DeMarker period, session, direction, stop formula, target multiple, hold period, risk, or daily cap may be changed from this readout. A fresh `HYP-DMR-XAUUSD-M15-002` may only reject a signal once when the unchanged SL/TP do not satisfy the broker reference-quote distance; it must not widen, move, or retry the stop.
