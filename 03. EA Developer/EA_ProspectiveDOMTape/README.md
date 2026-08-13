# EA_ProspectiveDOMTape

Prospective, no-trade MT5 Depth-of-Market collector for XAUUSD and the primary
Forex symbols. The package creates a hashable local source database for future
research; it is not a strategy and carries no edge or deployment authority.

The original collection contract is frozen in
`research/DOM_COLLECTION_PREREG.md` before implementation.

## Current status

- v1.0 compiled cleanly and proved that the current broker exposes nonempty DOM
  for all four frozen symbols, but the stopped runtime audit failed on I/O,
  sequence and JSON/CSV integrity. It has no source-pass authority. See
  `research/DOM_SMOKE_V1_0_RECEIPT.md`.
- v1.1 was frozen before its build in
  `research/DOM_COLLECTION_PREREG_V1_1.md`. Implementation v1.1.1 compiled
  `0E/0W`; two stopped sessions and an actual restart passed JSON/CSV/state and
  high-water audits. This grants `SOURCE_CAPABILITY_PASS` only.
- The outcome-blind payload-quality audit then closed the source as
  `KILL_FIVEPERCENT_DOM_LADDER__NO_HYPOTHESIS_AUTHORITY`: displayed size was a
  near-constant 100,000,000 sentinel and the outer ladder was fixed/symmetric.
  See `research/DOM_SOURCE_CAPABILITY_AND_QUALITY_VERDICT.md`.
- No hypothesis, signal mapping, EA economics, paper trade or live trade is
  authorized by this package. The collector is stopped.
