# HYP-024 time-weighted sweep-extreme resilience — terminal readout

## Verdict

`KILL_AT_HYP024_COLLECTION_DATA_DENSITY_OR_REDUNDANCY`

HYP-024 is terminal. HYP-025 is not opened. No duration, tick-count, gap,
session, year, direction or threshold rescue is allowed. The collection gives
no economic, paper, live or promotion authority.

## Exact object tested

- Hypothesis: `HYP-ICT-FVG-TIME-WEIGHTED-LEVEL-RESILIENCE-COLLECT-EURUSD-M5-024`.
- Canonical v1.26 source SHA-256:
  `3BC2130CE8F84AF44C6D3EFEC0639A7B461907A096A6AE90636479E6BB40E77B`.
- Frozen plan SHA-256:
  `6A80E4C97D19D901F6D96112114B0979F5065323E307D5907620FC77906E8269`.
- Frozen preset SHA-256:
  `7192B0BC4963C8593B7F1C84D5D370EAC5EC45DEB28D7DBCAB4112649297A6BE`.
- Run: `20260720_013805`, EURUSD M5, Model 0,
  `2018.01.01` through `2026.07.19`.
- Run-manifest SHA-256:
  `B060751F6D833FCA949D9EFAF1D65509D00D658B9349E7737B7FFAA51A5ADD76`.
- Post-run source/binary/run receipt V29 SHA-256:
  `6A65AC8706320165603FB3068D5A0A9A4E60388A43BD010774FFBEA829B313AE`.

The immutable source snapshot is
`research/source_snapshots/EA_ICTFVGReportFidelity_HYP-ICT-FVG-TIME-WEIGHTED-LEVEL-RESILIENCE-COLLECT-EURUSD-M5-024.mq5`.

## Engineering and run validity

- Package regression after the analyzer contract: `95 passed`; compile:
  `0 errors, 0 warnings`.
- Exact-source non-repaint V22: `PASS`, zero findings.
- History quality: `99%`; tester ticks: `206,517,809`.
- HumanContext and LevelResilience each sealed 6,401 confirmation rows.
  LifecycleTrades, TickInitiation and LevelPath sealed zero data rows. RunMeta
  records zero attempted and zero opened entries.
- All defined durations reconcile exactly, invalid/equality/carry behavior
  matches the frozen contract, and the external parser reproduces the exact
  canonical result hash.
- AlphaFactory's generic economic analyzer ended with `No trades found` only
  after sealing the report and sidecars. That is expected for this zero-trade
  collection and is not an economic result.

## Frozen gate result

| Measurement | Result | Frozen gate | Status |
|---|---:|---:|---|
| Confirmations | 6,401 | nonzero, reconciled | PASS |
| Defined paths | 6,399 / 6,401 = 99.9688% | at least 99% | PASS |
| FAVORABLE_DOMINANT | 6,396 = 99.9531% | at least 20% | PASS |
| ADVERSE_DOMINANT | 3 = 0.04688% | at least 20% | **FAIL** |
| FAVORABLE cadence | 14.3408/week | at least 2.0/week | PASS |
| ADVERSE cadence | 0.006726/week | at least 2.0/week | **FAIL** |
| ADVERSE 2018–2022 | 2 / 3,745 = 0.0534% | at least 20% | **FAIL** |
| ADVERSE 2023–YTD | 1 / 2,654 = 0.0377% | at least 20% | **FAIL** |
| Both directions/sessions/all years per label | adverse is short-only, no NY, three years | required | **FAIL** |
| Deterministic external replay | identical result SHA-256 | required | PASS |

Canonical result:
`research/evidence/HYP-ICT-FVG-TIME-WEIGHTED-LEVEL-RESILIENCE-COLLECT-EURUSD-M5-024_COLLECTION_RESULT.json`,
SHA-256
`AF55C0C14184120AB60D2F0BBD3A952296E8EB27C8EF79BDCBE2DA8EAFB11F76`.

## Why the mechanism failed

This is not a clock, sparse-feed or reconciliation failure. HYP-024 selected
the sweep wick tip as level `L`. For a short, the sweep has already closed
below the breached pivot and therefore below `sweep_high = L`; later closed
bars at or above `L` invalidate the setup, while confirmation must close below
the opposite sweep extreme. The population that survives to confirmation is
therefore mechanically selected to spend nearly all of its time on the
favorable side of the wick tip. The long case is symmetric.

The label remains formally non-recoverable from OHLC because identical prices
with different tick timestamps can flip duration dominance. That establishes
tick-time information, but it does not establish separability after the
confirmation filter. The 6,396 versus 3 split is a near-tautology created by
the chosen geometry, not evidence of resilience alpha.

The three rare adverse rows have 326–455 valid ticks, maximum tick gaps of only
about 3–6 seconds within 300–600 second windows, and exact duration identities.
They are pathological survivors that spend most of the window beyond the wick
tip and then confirm late; they do not expose a feed defect.

## Chart and higher-timeframe forensics

All three adverse rows and deterministic same-direction/session/year favorable
matches were rendered both as decision-time charts and disclosed anatomy charts.
The case CSV SHA-256 is
`E37F4F503B8F6FC5DCB1A969C4EF1A24F1B2A5A3FEF786FE943FF5966343FF25`.
The as-of manifest SHA-256 is
`1915E8B5E1032A8D989535AC6C9F37C124473E74D0AF9A5644DA53CBAACD5417`;
the anatomy manifest SHA-256 is
`E71E3F7F5EDC155DE1F6173E59219E158F6D0DD04FD0430583F1B407D1A320DF`.

H1/H4 does not distinguish the rare label consistently. One pair is neutral
versus bullish/neutral, one pair has identical bearish/bearish alignment, and
one pair reverses conflict/alignment signs. Range location, liquidity room and
external-sweep context also have no stable polarity in this six-case diagnostic.
The common rare facts are the mechanical dwell arithmetic and short-only/no-NY
coverage, neither of which may be promoted into a post-outcome filter.

The chart marker is the measurement decision/structural level, not an executed
entry. There is no SL, TP or exit because the EA opened zero trades. Post-marker
anatomy bars are visual disclosure only and were not used to create the label
or the next mechanism.

## Independent adversarial review

The local-only Grok forensic response independently classified the imbalance
as the near-tautological consequence of `L = sweep extreme`, rejected clock/feed
artifact as the main cause, found no stable H1/H4 separator and accepted only
one fresh structural successor. Response SHA-256:
`20D8254D63AC0899ECF55DB513DAC7F2FDF42C0B3BB17A54C61C7FB2BAE3D474`.

## Legal successor boundary

A single fresh HYP-026 may store the actual point-in-time pivot high/low that
`DetectSweep` breached and reclaimed, then measure natural time dominance about
that pivot. The pivot lies strictly inside the sweep wick: quote mid can spend
time beyond the pivot but inside the sweep extreme without triggering the
unchanged extreme invalidation. That is materially different structural-level
geometry and asks whether the reclaimed liquidity level held, rather than
whether price stayed inside the wick tip.

HYP-026 must be frozen before source change, use no tuned threshold or subgroup,
open zero trades, and pass the same density/materiality/coverage/replay gates.
If it fails, no further migration of `L`, duration threshold or HYP-027 economic
child is allowed.
