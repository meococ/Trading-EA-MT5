# FivePercent prospective DOM source capability and quality verdict

Date: 2026-08-13

Lead verdict: `KILL_FIVEPERCENT_DOM_LADDER__NO_HYPOTHESIS_AUTHORITY`

Engineering verdict: `SOURCE_CAPABILITY_PASS`

Economic/hypothesis verdict: `NOT_OPENED`

## Build and runtime identity

- Package: `EA_ProspectiveDOMTape`, implementation `1.1.1`, schema `1.1`.
- Frozen symbols: `XAUUSD`, `EURUSD`, `GBPUSD`, `USDJPY`.
- Terminal/server: MT5 build 6090, `FivePercentOnline-Real`.
- AlphaFactory compile: `0 errors, 0 warnings`, EX5 71,556 bytes.
- Static tests: `10 passed`.
- MQ5 SHA-256:
  `6C4AA0312E73DA9A2BACAA7C6A3D293E11EFE6AD2FED8FD102B8491A8AE0C30A`
- EX5 SHA-256:
  `CBBA0CED2AC30D586CE1FF47DFF7E090EAC220B7C7ACE637AF9A3B66FE52051E`
- Terminal deployment hashes matched the package hashes.
- Algo Trading permission remained unchecked. The collector contains no order,
  position, chart bar, indicator, Calendar, WebRequest or outcome API.

The v1.0 stopped smoke and the v1.1.0 pre-subscription initialization failure
remain separate failed receipts. Neither was overwritten or promoted.

## Source and restart proof

Two stopped v1.1.1 sessions passed the independent JSON/CSV/state auditor:

- `5,172` JSON snapshots exactly matched `5,172` CSV snapshot keys and
  `70,579` individual CSV level rows;
- snapshot counts by symbol: XAUUSD `4,107`, EURUSD `148`, GBPUSD `440`,
  USDJPY `477`;
- `2` writer receipts, `8` ordered subscription receipts, `2` init receipts,
  `4` all-subscribed heartbeats and `2` clean shutdown receipts;
- zero empty books, book/timer API errors, I/O errors or tick regressions;
- first session stopped at snapshot ID `2,716`; restart loaded the validated
  state, jumped the reserved floor to `10,000`, and first used ID `10,001`.
  Per-symbol event IDs also first used `10,001`. No ID was reused or moved
  backward.

Final stopped artifacts:

- JSON SHA-256:
  `D9D2B3C8B4F726C5EA7D7D59D95EFF18E249A9F5C59F6543574931B1D4B25903`
- CSV SHA-256:
  `21C2BEB69F99D85AB6EA9FAF772FCD0384DAD856CA3CC282CA2E6647007B9D41`
- State SHA-256:
  `1E922768D9EB6FB598D88AAD7CFB82AA1E5F20FAE86E343C80AA93D9A1E0F77F`
- First stopped audit: `research/DOM_SMOKE_V1_1_1_AUDIT.json`.
- Restart audit: `research/DOM_RESTART_V1_1_1_AUDIT.json`.

This proves only that current terminal DOM arrays can be collected faithfully.

## Outcome-blind information-quality audit

The broker payload does not expose a defensible new size/flow object:

- every EURUSD, GBPUSD and USDJPY level had both `volume` and `volume_real`
  equal to `100,000,000`;
- XAUUSD had `56,054 / 56,070` levels exactly equal to `100,000,000`; the other
  16 were integer `99,999,999` with only sub-unit floating representation
  differences. Aggregate modal-volume share was `99.977330%`;
- constant-volume snapshot share was 100% for EURUSD/GBPUSD/USDJPY and
  `99.610421%` for XAUUSD. Any apparent size imbalance is only a count of
  displayed levels, not queue-size imbalance or OFI;
- the outer ladder was almost fixed and symmetric: EURUSD/GBPUSD about
  `+/-0.00811`, USDJPY mostly `+/-1.012`, and XAUUSD median about `+/-1.63`;
- only 4/9/10/13 type-volume shapes appeared on EURUSD/GBPUSD/USDJPY/XAUUSD;
  XAUUSD retained the same type-volume shape across `80.9547%` of consecutive
  snapshots;
- combined JSON+CSV occupied `26,102,049` bytes across `143.391` observed
  seconds, projecting to roughly `15.73 GB/day` uncompressed at the smoke rate.

These observations are consistent with a dealer-rendered fixed-size quote
ladder, not proof of an executable exchange queue. On this exact source:

- volume imbalance and OFI have no varying size input;
- depth-count imbalance is the finite ladder shape and is not independent size;
- ladder spacing is a transform of displayed quote geometry;
- update intensity is quote refresh/tick activity, not identified add/cancel or
  trade flow, and de-duplicates to previously closed quote-activity families.

There is no residual signed object known on a closed M5/M15 bar that is both
non-price and defensible before outcomes. Mining shape IDs, count imbalance or
event rate would be post-source feature search without a causal sign.

Machine quality readout:
`research/DOM_TAPE_V1_1_1_QUALITY.json`.

## Grok Build review and Lead decision

Grok Build independently returned
`KILL_FIVEPERCENT_DOM_LADDER - NO_HYPOTHESIS_AUTHORITY` after reviewing the
hash-bound local metrics. It separately preserved `SOURCE_CAPABILITY_PASS`.
Lead concurs based on the local artifacts; Grok remains advisory.

## Process failure and correction

This source attempt should have been stopped before build. The existing local
failure catalog already contained `FivePercent live-DOM size-identity guard
(2026-08-13)`: 160 polls over XAUUSD and seven major-FX symbols had found the
same `100000000` volume on every level, and the guard explicitly prohibited a
prospective collector merely because `MarketBookAdd` succeeds.

Lead performed run-catalog and EA-lineage de-dup but missed the API + payload
field signature in `04. Memory/do_not_repeat_failures.md`. The new work adds a
verified single-writer/restart collector and stronger hash-bound evidence, but
it does not count as a new discovery frontier. Corrective gate: before any new
prospective source build, search the failure catalog by source API, venue,
symbol set, payload fields and intended mechanism in addition to querying the
runs database and candidate lineage.

## Failure radius

Closed:

- current `FivePercentOnline-Real` `MarketBookAdd`/`OnBookEvent`/
  `MarketBookGet` payloads for the four frozen symbols;
- volume imbalance, OFI, level-count imbalance, fixed ladder spacing,
  shape-transition rate and book-update intensity derived from this tape;
- any EA, hypothesis ID, AlphaFactory backtest or economic claim minted from
  this exact payload.

Not claimed:

- this is not a verdict on true exchange MBO/MBP data, another executable venue
  with variable restable size, or all MT5 brokers;
- this does not establish that the displayed ladder is fraudulent or unusable
  for manual visualization; it establishes that it lacks the required new
  causal information for this EA research contract.

No continuous collector is left running. No data/service purchase, hypothesis,
target-price read, backtest, paper trade or live trade was opened.
