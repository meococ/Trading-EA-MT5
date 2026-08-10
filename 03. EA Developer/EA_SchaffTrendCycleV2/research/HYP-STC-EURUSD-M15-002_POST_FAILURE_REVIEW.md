# HYP-STC-EURUSD-M15-002 independent post-failure review

Verdict: `PASS_KILL_ENGINEERING`.

HYP002 failed inside `OnInit` before any completed bar, signal, order, trade or
return was processed. The immutable failure packet SHA256 is
`F96016C633669BF1699336F1E47BF332D1A6602A6A95B84D567AC44D6129FDA6`.

The exact failure was an off-by-one-bar preload boundary: Strategy Tester
reported the last closed M15 bar as source epoch `1451591100`
(`2015-12-31 19:45:00`), while HYP002 required `1451592000`
(`2015-12-31 20:00:00`). All runtime counters were zero and the run manifest
reported zero bars/ticks, so no PF, cadence, drawdown or market-edge inference
is admissible.

The independent reviewer authorized a fresh engineering revision only after a
same-terminal/profile read-only proof established the exact count, first, last
and timestamp-sequence hash. That proof shows the tester-visible closed subset
contains `24,775` strictly increasing bars from `2015-01-02 09:00` through
`2015-12-31 19:45`, sequence SHA256
`C9006D5C5E0ED8BE72C63BA4F1C0FB1B12AD9DF518F0D7BE68639305EAD114FF`.

HYP003 may change only fresh identity/log prefixes and the preload
count/last-endpoint contract. The recurrence, STC signal, ATR/risk, exits,
costs, DESIGN/validation/holdout windows and economic gates must remain
unchanged. One untuned baseline is allowed after compile, focused tests and
non-repaint review pass.
