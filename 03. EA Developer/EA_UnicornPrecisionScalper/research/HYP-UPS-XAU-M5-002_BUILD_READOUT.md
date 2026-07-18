# Build Readout — HYP-UPS-XAU-M5-002

## Bound identity

- Source SHA256: `DEA7C2E3380B04E494DABD8D985C1912DA5E023F76AC277ADD6653453071376E`.
- Frozen prereg SHA256:
  `46CACFC5D191690981C5FD46E0AC93B14D5F2CB2A73C7570A99AF06A8F5237F1`.
- Capability SHA256:
  `82CC9B1BAFB6722F57E1B4BE89D6B18C29FC27C8518AECDD233C4045A9ED61E5`.

## Code gates

- Canonical source is under `03. EA Developer/EA_UnicornPrecisionScalper/`.
- Static non-repaint audit: PASS; no findings. The one `iTime(...,0)` call is
  the documented new-bar gate. All signal `CopyRates` calls begin at shift 1.
- MetaEditor: exit `1` accepted by AlphaFactory because the fresh UTF-16 log
  reports `0 errors, 0 warnings`.
- EX5 (latest verified compile, 2026-07-16): `50,118` bytes, SHA256
  `024E449190765398827833E709DAD46045BFDABC0FACABD6BE6A48C39C7DEBB3`.
- Compile log SHA256:
  `B2496DA6A4857331D41CDDE10F127C8DCC4C21A905825FC5CAB707EA85EF3806`.

## Implemented controls

- Default alert-only; explicit research-auto opt-in.
- Symbol + magic ownership, one owned exposure, restart history lookup for
  entry direction, synchronous retcode handling and broker stop geometry.
- `OrderCalcProfit` fixed-fraction sizing; min/max/step normalization and
  fail-closed min-lot oversizing.
- Hard SL, 2.5R target, 1R break-even, 90-minute timeout, daily/weekly loss,
  consecutive-loss and account-DD gates.
- Lifecycle-v3 per-deal telemetry with deal P&L/commission/swap/fee and
  initial-risk fields needed for report reconciliation.

## Remaining pre-MT5 gate

The current workspace now has full-window FivePercentOnline XAU M1 spread
evidence, but the frozen task packet still carries MetaQuotes identity and no
same-broker evidence exists for at least 30 XAU commission lifecycles or at
least 100 independent bid/ask-referenced slippage samples. A strict dry-run
must therefore remain blocked until one coherent broker-bound cost contract
exists; no missing cost field is being treated as zero.
