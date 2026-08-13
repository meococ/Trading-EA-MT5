# Baseline result — HYP-TPR-EURUSD-M5-001

Verdict: `KILL_NEGATIVE_EDGE_OVERTRADING_ACCOUNT_STOP_OUT_NO_OOS`.

Authority: AlphaFactory run `EA_TPR_EUR_M5_V3/20260812_011405`, EURUSD M5 Model 0, History Quality 100%, data coverage `FULL_2018_PLUS`.

## Engineering

- Fresh compile `0 errors, 0 warnings`; EX5 nonempty; static contract `15/15`; non-repaint audit `PASS`.
- Telemetry before termination: 6,995 closed bars; 637 trend definitions; 486 pullbacks; 346 resumptions; 218 entries; no entry/close reject and no runtime failure.
- Entry margin usage was about 1.89%..4.50%, well below the 12% frozen cap. The three-way volume topology therefore worked; it did not cause termination.

## Economic and risk failure

- Only 2018-01-01 through 2018-02-12 executed before the account/terminal stop-out threshold ended the test at 2% of the requested interval.
- 218 trades; net `-$10,012.43`; PF `0.6783`; win rate `31.65%`; expectancy `-$45.93/trade`; max DD `10.9534%`; max losing streak `13`.
- The chart shows an almost monotonic equity decline after a brief early fluctuation. Asia PF 0.45, Europe 0.72 and New York 0.98 all fail; these buckets are diagnostics only and cannot authorize a time filter.
- Cadence is also terminal: 218 trades in roughly six weeks implies massive overtrading and would exceed the frozen 600-trade four-year ceiling even if the account had survived.

## Decision

Kill the exact EMA8/EMA21 trend-body + five-bar expansion → seven-bar pullback → nine-bar resumption state machine. No parameter/session/direction/stop/exit rescue, matched control, OOS, holdout, cross-symbol transfer, validation or optimization is authorized.

Evidence: source SHA `39CAD397B794E48C42A20BD867CFF36A6197742F48949306DCB208C1952A2A4F`; EX5 SHA `B34EF03EBC1D92E7BED7E04102037AF539A961F463144790F2B0F3FA4BE12527`; report SHA `0713526DC6AD8FF9C2A63EA539E8ADE713CA9DB80C1CDC02A536564BDDE71060`; journal SHA `84490EA4C47775344C70D37C744601D208AEC86FB302FAE135264838DAB92530`.
