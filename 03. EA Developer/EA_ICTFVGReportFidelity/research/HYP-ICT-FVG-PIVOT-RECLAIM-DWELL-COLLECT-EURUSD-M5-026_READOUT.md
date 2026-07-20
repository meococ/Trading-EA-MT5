# HYP-026 swept-pivot reclaim dwell — terminal readout

## Verdict

`KILL_AT_HYP026_COLLECTION_DATA_DENSITY_OR_REDUNDANCY`

HYP-026 is terminal and the EURUSD M5 HYP-012 sweep-confirmation/pivot-dwell
branch is at `FRONTIER_STOP`. HYP-027 is not opened. No measured-level migration,
duration threshold, lag subgroup, label inversion, direction/session/year/HTF
filter, rerun, economics, paper/live or promotion authority follows.

## Exact object and provenance

- Hypothesis:
  `HYP-ICT-FVG-PIVOT-RECLAIM-DWELL-COLLECT-EURUSD-M5-026`.
- Canonical v1.27 source and immutable snapshot SHA-256:
  `227A52E93713731EF639D9484DABC89B85006660F436C0F232117C60F1528127`.
- Frozen plan SHA-256:
  `4F963A8AC579F90828B2A669A08746E7CD9739116F367A68D5FF7FC511C8F059`.
- Frozen preset SHA-256:
  `C34A7FEF4CDDBDF18663DA81E66552B444A85666BC1B41D690289B02B20107D4`.
- Run `20260720_021053`, EURUSD M5, Model 0,
  `2018.01.01` through `2026.07.19`.
- Run-manifest SHA-256:
  `2BEC201A0A387C2E15BE674524DE6363C225DC3212E620D0C1BE7EB221B661A2`.
- Execution-receipt SHA-256:
  `7837739CC7FDED1ECE0C09EB66840466413AFC12C898706217EF4605422BF108`.
- Post-run source/binary/run receipt V31 SHA-256:
  `828C440C4B2765F0227A42D74839A0B1E455D99AC4AFDB280D9CA1B218481BFB`.

The source stores the exact point-in-time pivot used by `DetectSweep`: long
uses the breached/reclaimed pivot low and short uses the corresponding pivot
high. HYP-024's clock, first-favorable anchor, equality/invalid-quote behavior,
last-side carry, decision-tail seal, confirmation and invalidation remain
unchanged. Sweep extremes remain dormant risk/confirmation geometry and are no
longer the measured level.

## Engineering and run validity

- Red-first: five mathematical/geometry fixtures passed and five source-specific
  tests failed on v1.26; after the minimal source delta HYP-026 passed `10/10`.
- Pre-run package regression: `105/105`; post-analyzer regression: `110/110`.
- AlphaFactory compile: `0 errors, 0 warnings`.
- Exact-source non-repaint V23: `PASS`, zero findings.
- Tester history: `99%`; processed ticks: `206,517,809`.
- HumanContext and LevelResilience each sealed 6,401 decisions. LifecycleTrades,
  TickInitiation and LevelPath have zero data rows. RunMeta records zero
  attempted and zero opened entries.
- Defined rows reconcile their millisecond durations exactly; external parser
  replay reproduces the same canonical result hash.
- AlphaFactory ended at `No trades found` only after sealing evidence. That is
  expected for the frozen zero-trade mode and is not an economic result.

## Frozen gate result

| Measurement | Result | Frozen gate | Status |
|---|---:|---:|---|
| Confirmations | 6,401 | nonzero, reconciled | PASS |
| Defined paths | 6,398 / 6,401 = 99.9531% | at least 99% | PASS |
| FAVORABLE_DOMINANT | 6,217 = 97.1710% | at least 20% | PASS |
| ADVERSE_DOMINANT | 181 = 2.8290% | at least 20% | **FAIL** |
| FAVORABLE cadence | 13.9395/week | at least 2.0/week | PASS |
| ADVERSE cadence | 0.40583/week | at least 2.0/week | **FAIL** |
| ADVERSE 2018–2022 | 103 / 3,745 = 2.7503% | at least 20% | **FAIL** |
| ADVERSE 2023–YTD | 78 / 2,653 = 2.9401% | at least 20% | **FAIL** |
| Both directions/London/NY/all years per label | present | required | PASS |
| Exact duration + deterministic replay | exact | required | PASS |

Canonical outcome-blind result:
`research/evidence/HYP-ICT-FVG-PIVOT-RECLAIM-DWELL-COLLECT-EURUSD-M5-026_COLLECTION_RESULT.json`,
SHA-256
`79DFA7D16CC91660D6B33E6BD25FF00B8E9817051ACC44AE1E25B1711ED5076C`.

## Why 6,217 versus 181

Moving from the wick tip to the actual pivot proved that HYP-024's extreme was
the wrong structural level: the adverse state increased from 3 to 181 and now
covers both directions, sessions and all years. It is still far too sparse.

The remaining imbalance is a selection effect of the unchanged scaffold, not a
clock/feed defect. A setup is detected only after its sweep bar has already
closed on the reclaimed side. Measurement then begins at the first favorable
quote. To reach the ledger it must survive close-at-extreme invalidation and
finish with a strong closed candle through the opposite sweep extreme. These
conditions select paths that predominantly preserve the reclaim; sustained
re-acceptance beyond the pivot and a late confirmation is possible, but rare.

The stable 2.75%/2.94% split rules out one isolated era. Confirmation-delay
diagnostics support the mechanism without authorizing a filter:

| Confirmation lag | FAVORABLE | ADVERSE | Undefined |
|---|---:|---:|---:|
| first eligible M5 bar | 2,963 | 27 | 1 |
| second eligible M5 bar | 1,882 | 86 | 2 |
| third eligible M5 bar | 1,372 | 68 | 0 |

Delayed confirmations allow more pivot re-acceptance, but using that observed
stratum as a go/no-go rule would be an explicitly forbidden post-readout
subgroup rescue. Small tick gaps, high defined coverage, exact identities and
both temporal splits reject a clock/carry explanation.

## Outcome-blind chart and HTF casebook

Four adverse cases were selected deterministically as maximum adverse-share
within short/long × London/New-York; each has the nearest same-direction,
same-session, same-year favorable control. Case CSV SHA-256:
`14E3C0325459BC30E0CD3039507E59E9D8A277B76FD9D09927945554D32C89D6`.
The H1-centered as-of manifest SHA-256 is
`97EF3C0A11EA27CDF65D9B77C20E311C5BF3943228C8EA190888B1C6539237EB`;
the disclosed anatomy manifest SHA-256 is
`0D2283B75A61FC3217ADE1F28C34EC38260D49456506D3D8DBCBBB2D2E123997`.

HTF context does not consistently separate the labels:

- short London: adverse H1/H4 structure is bearish/neutral while its match is
  neutral/neutral;
- short New York: adverse is bullish/bullish while its match is neutral/bearish;
- long London: adverse and favorable are both bullish/bullish, only five minutes
  apart and use the same pivot;
- long New York: adverse and favorable are both bullish/bullish, 45 minutes apart.

The strongest visual lesson is not a new feature: very similar H1 context can
carry opposite intrabar dwell labels. Anatomy paths also vary within both labels
and cannot be used to design a successor. The blue chart marker is a measurement
level/time mislabeled by the generic renderer as `entry`; there was no executed
entry, SL, TP or exit.

## Family boundary and independent review

The accepted one-turn Grok adversarial review used only sealed facts and ended
with `EndTurn`, response SHA-256
`0BB8A5FDD7B17722D0D36BFE79D99BAF662172B7DCBF2D4666D4C86B6CA87A1C`.
Two earlier file-reading attempts ended `Cancelled` and are rejected, not
evidence. The accepted review independently returns `FRONTIER_STOP`:

- fast-versus-delayed confirmation is a subgroup of the same killed scaffold;
- disabling break-even is not a HYP-026 child because this run has no orders,
  and the prior motivation is post-outcome with unverified same-broker costs;
- pivot/FVG retracement entry is another entry/level migration from the failed
  readout and overlaps the already tested report-fidelity/retest family.

HYP-012 already tested the economic sweep-confirmation member and was negative
(PF 0.810, -0.098R, all nine years losing); HYP-014 ranking and HYP-017 context
policy also failed. The collection family now either selects an overwhelmingly
common state or lacks enough cadence/materiality for a legal economic child.

## Hard stop

Do not move the measured level again, lower the 20%/2-week gates, filter by
confirmation lag, trade the 2.8% rare class, invert labels, use HTF/session/year/
direction rescue, change management under this ID, rerun HYP-026 or open
HYP-027. A future lane must begin from a fully independent causal mechanism and
fresh outcome-blind feasibility probe; it may not use HYP-026 labels, rare cases
or lag strata as design features. Historical same-broker cost provenance remains
an independent promotion blocker.
