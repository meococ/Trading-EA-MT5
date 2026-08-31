# FivePercent broker and external source-shelf frontier

Date: 2026-08-13

Verdicts: `NO_BROKER_OBJECT` and `NO_EXTERNAL_SHELF_CANDIDATE`.

Authority: source capability, physical inventory and successor-lineage audit
only. No target-price outcome, hypothesis, MQL5, compile, backtest, validation,
holdout, paper/live trade, download or purchase was authorized by this work.

## Scope

- Target universe remains XAUUSD and the seven active FX majors.
- BTC/crypto is excluded even when the broker inventory lists those symbols.
- M5, M15, H1, H4 and D1 remain possible only for a materially distinct
  mechanism frozen before source/outcome access.
- Grok Build is advisory. Local MT5 metadata, manifests, receipts and terminal
  successor lineages are the decision authority.

## AlphaFactory and FivePercent runtime

`alpha.ps1 status` confirmed that the portable FivePercent terminal is running
and remains the canonical AlphaFactory runtime. The read-only context capsule
confirmed a dirty concurrent worktree; no Git operation or unrelated cleanup
was performed.

The broker exposes 64 non-custom symbols:

| Group | Count |
|---|---:|
| Forex | 35 |
| Indices | 11 |
| Precious metals | 7 |
| Energy | 3 |
| Crypto, excluded | 8 |

Every non-custom contract has `expiration_time=0`; none is an option, dated
future or maturity-bearing instrument. All are rolling spot/CFD objects using
market execution. Therefore the broker has no native spot-future, calendar
spread or option-surface object to gate.

The remaining structural fields also fail:

- current swaps on every active FX major are negative in both directions, so
  the already-closed carry lineage cannot be reopened;
- broker-native cross prices reduce to the already-terminal triangular,
  residual, cross-asset lead-lag, price-transform or fixing/session families;
  and
- tester history contains the same CFD price tape, not a second information
  source.

## DOM volume-only probes

Read-only subscriptions inspected only book type and volume, not prices:

| Symbol | Levels | Levels at exactly 100,000,000 |
|---|---:|---:|
| EURUSD | 15 | 15 |
| XAUUSD | 14 | 14 |
| US30 | 10 | 10 |
| XTIUSD | 9 | 9 |
| XAUEUR | 14 | 14 |

The energy and hidden-metal symbols were temporarily selected for the probe and
restored afterward. Every sampled venue segment exposes the same fixed
100,000,000 sentinel ladder. This is not objective depth, and MT5 provides no
historical DOM replay for a history-equals-live validation path.

Grok independently returned `NO_BROKER_OBJECT`, `OBJECT: NONE`,
`HISTORY_LIVE_IDENTITY: FAIL` and `FIRST_GATE: NONE`. Lead accepts the verdict
because it matches the local metadata and volume-only probes.

## External physical source shelf

The previous local inventory covered `02. AlphaFactory/data`. This pass also
enumerated `02. AlphaFactory/external`:

| Shelf | Files | Bytes | Controlling boundary |
|---|---:|---:|---|
| `cboe_fx_vol` | 1 | 79,073 | EVZ history ends 2025-03-11; no matching current live serve. |
| `cftc_fx_options_tff` | 15 | 6,459,650 | Exact HYP-CFTC-FX-H1-001 is terminal at PF x1 0.812/0.766 train/validation and lacks a complete first-public vintage contract. |
| `cme_daily_volume` | 1,769 | 123,346,242 | Exact daily OI participation child is terminal at PF x1 0.878/0.924 and failed its matched-control margin. |
| `cme_fx_options_euro` | 4 | 11,307 | Manifest status is `MISSING_RAW_DATA`; zero raw files and profiles. |
| `cme_sdr_fx` | 272 | 4,060,540 | Official archive ends 2023; 2022-2023 validation density is 1.944 active days/week and sampled 2023 has zero major-FX new-option days. |
| `dtcc_fx_options_sdr` | 3 | 2,827,819 | Dense current files, but pre-mid-2024 history is deep-archived/unrestored; no 2018-live identity. |
| `sge_shau_auction` | 1,698 | 96,458,272 | 10,617 rounds and valid density, but date-only pages have no immutable `published_at`, ETag or revision lineage; source feasibility is terminal. |
| `dukascopy_tsmom_v4_jobs` / `v5_jobs` | 40 | 853,871 | Consumed job packets for terminal/superseded Dukascopy successors. |
| `bitmex_xbtusd` | 3,322 | 107,220,106,010 | Excluded crypto/BTC source; not inspected for strategy discovery. |

The empty pytest directories are not data. `.context/external` contains only
the already-rejected SonicR QUALITY v10 package. `02. AlphaFactory/evidence`
contains execution/cost evidence, not another market source, and
`02. AlphaFactory/tmp` contains no source shelf. The prior `.context/cron_*`
official/free discovery waves are terminal in the failure catalog.

Grok independently returned `NO_EXTERNAL_SHELF_CANDIDATE`, `OBJECT: NONE`,
`MECHANICAL_SIGN: NONE` and `FIRST_GATE: NONE`. Lead accepts this advisory
verdict because each shelf is locally bound to a terminal, empty, excluded or
history/live-broken object.

## Anti-rescue boundary

- No triangular/XAU residual/cross-asset retime, price-only indicator, session,
  fixing, swap, spread or sentinel-DOM reuse.
- No stitching CME SDR history to current DTCC, treating EVZ as live, inventing
  SGE publication clocks, reversing or retuning TFF/OI participation, or
  reviving Dukascopy/Jetta.
- No column remix, threshold change, symbol deletion, clock move or old-catalog
  selection can create a fresh information object.

## Authority boundary

The zero-spend local, broker-native and already-acquired external source
frontiers are exhausted under the current scope. Further market progress now
requires an explicit Owner expansion to either:

1. a new executable venue/feed that supplies a distinct replayable information
   object with historical/live identity; or
2. one precisely defined paid research-grade historical and live data contract
   with a frozen maximum spend.

No such expansion or purchase is authorized by this receipt.

