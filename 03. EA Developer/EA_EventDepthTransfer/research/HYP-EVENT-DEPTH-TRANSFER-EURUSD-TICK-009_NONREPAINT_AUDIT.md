# HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-009 - non-repaint audit

Verdict: `PASS` for the frozen tick-exact event contract.

The only bar-series access is the canonical AlphaFactory D0 provenance probe in
`OnInit`: series metadata plus `CopyTime(PERIOD_M5, m5_first_epoch, 1, ...)`. That
timestamp is printed and validated, then discarded. It cannot alter event direction,
entry, exit, size, cost or accounting. There is no bar-zero read, indicator buffer,
current/future target-market price in the source table, or price-derived signal.

The source direction was calculated only from CME 6E records with `ts_recv < T+60`.
Entry requires `tick.time_msc >= event_server_msc + 60000`; exit requires
`tick.time_msc >= event_server_msc + 120000`. The reverse comparator changes direction
only. No threshold, session, SL/TP, trailing or alternate-horizon input exists.

PASS is engineering evidence only. It does not establish profitability or promotion.

