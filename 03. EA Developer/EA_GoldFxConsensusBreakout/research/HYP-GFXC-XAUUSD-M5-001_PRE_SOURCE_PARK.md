# HYP-GFXC-XAUUSD-M5-001 — Pre-source PARK

Verdict: `PARK_PRE_SOURCE_DEDUP_SAME_BAR_CONSENSUS_FAMILY`

- No Parquet row was opened and `GFXC-SOURCE-001` was never claimed.
- No signal count, post-decision price, trade, PF, expectancy, cost, MT5 run,
  optimization, validation or holdout was opened.
- The proposed rule combined an XAU M5 breakout with same-bar EURUSD,
  GBPUSD and USDJPY direction consensus.
- Independent read-only review identified this as the already-closed
  same-bar-consensus / lead-lag / laggard-catch-up information family
  (S555/S618/S670 class). Adding breakout context did not establish a new
  information set, and the three FX legs are largely the same USD factor.
- Threshold/window/leg/cooldown edits are not authorized under this ID.

Process correction: de-dup future ideas by information family before writing
an analyzer, not merely by strategy name or indicator. The unused source
harness remains a code template only and is not evidence.
