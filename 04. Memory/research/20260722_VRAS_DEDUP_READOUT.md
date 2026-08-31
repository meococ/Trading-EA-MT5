# VRAS Deep-Research Intake — Historical De-dup Readout

Date: 2026-07-22  
Status: `SUPERSEDED_BY_OWNER_BUILD_FIRST_SCOPE_AND_MODEL0_EVIDENCE`  
Historical verdict: `KILL_AT_DEDUP_NO_BUILD`  
Promotion-grade/economic-authoritative run authority: `BLOCKED`  
Diagnostic Model-0 authority: `NOT_OPENED; REQUIRES_FRESH_OWNER_SCOPE_AND_CONTRACT`  
Source/build/compile/Model-0 authority: `SUPERSEDED; see HYP-VRAS-EURUSD-M5-003`

This file is retained as the pre-build adversarial intake. The Owner later
explicitly removed this veto and authorized implementation. The exact seven-gap
object was built and terminally killed by bound Model-0 evidence under
`EA_VRAS_RegimeAdaptiveScalperV3/research/HYP-VRAS-EURUSD-M5-003_READOUT.md`.

## Intake identity

- Owner source: `05. Playbook/Strategy/BaoCao_DeepResearch_VWAP_Regime_Adaptive_Scalper_VRAS_22Jul2026.docx`
- Source commit: `84ce253cae3e812d94fac0317ea67286fa9389f0`
- Source SHA256: `AB57D7D3F8993784C9B0016E4347BB7D093122A539C0A741C0389648AD014F0C`
- Requested object: M5/M15 Session VWAP + SD bands, ADX regime switch,
  swing-anchored VWAP, rejection confirmation, session/news/cost filters.

The document is a design memo, not a frozen strategy contract. It leaves the
VWAP reset clock, weighted-SD definition, swing-anchor replacement rule, entry
event, news data source and asset-specific parameter set materially ambiguous.
Its section 7 fallback also routes to Variant 3, adds M15, or drops mean
reversion after PF is known. Those are separate pre-outcome arms, not legal
post-outcome rescue actions.

## Failure-radius result

The complete VRAS object is not a materially independent candidate. It
densifies or recombines already-tested decision surfaces:

| VRAS component | Existing evidence | Boundary |
|---|---|---|
| Session-VWAP reclaim/continuation | Historical local-run/archive-ledger evidence for `HYP-SESSION-VWAP-RECLAIM-M15-001`: N=1,357, PF=0.9000, without the current lifecycle-grade packet; retained primary readouts for `HYP-FX3-H1-SESSION-VWAP-RECLAIM-CONT-001`: N=1,566, PF=0.9758 and `HYP-GBPUSD-H1-LONDON-VWAP-RECLAIM-CONT-001`: N=1,297, PF=0.8783 | Changing H1/M15 to M5 or adding another confirmation does not create a new causal object. |
| ADX-gated range mean reversion | `HYP-MR-REGIME-EURUSD-H1-001` killed; `HYP-MR-GRID-EURUSD-H1-002` closed the family after 8,100 simulations with zero arms at gross PF >=1.25 | ADX 22 and equal-weight/range-proxy Session-VWAP SD variants remain threshold/filter recombinations without a new information set. Actual broker tick-volume weighting is `UNPROVEN_NEWNESS`, not covered by this sentence until an outcome-blind divergence screen. |
| Trend pullback + pivot/anchor reclaim | `HYP-MZMS-XAU-M5-008` is the same broad pivot-reclaim identity; its only run is engineering-invalid at 98% history and under-cadence, so it is not an economic kill, but it also cannot be patched/rerun under a renamed ID | Adding swing AVWAP and M15 side bias is confluence densification on that event identity. |
| Rejection + ADX exhaustion | `HYP-MZMS-XAU-M5-010` already binds wick rejection and ADX-roll exhaustion; its run is invalid/sparse, not economic evidence | Reusing the same decision fields inside VRAS does not establish independence. |

The report therefore fails the pre-code newness gate. No registry hypothesis was
opened because no meaningful probe or economic run was authorized.

## Independent cost blocker

The best available first asset is FivePercent EURUSD because the D-portable M1
data has 4,293,917 monotonic, non-duplicate rows and supports a clean
2019-2022 window. It still cannot support a promotion-grade or
economic-authoritative Model-0 VRAS run:

- `02. AlphaFactory/data/fivepercent/EURUSD/manifest.json` marks
  `EURUSD_M1_SPREAD_2019_2022.csv` as `FAIL_SPREAD_COST_PROVENANCE`.
- 366,196 / 1,491,312 rows (24.5553%) report zero spread.
- No hash-bound same-symbol commission contract or direction-aware slippage
  sample satisfies the active cost gate.

Historical price quality does not repair missing execution-cost provenance.
An Owner-authorized diagnostic-only control could be opened separately with a
fresh prereg/registry/task packet and `promotion_eligible=false`; no such scope
or contract exists for VRAS in this session.

## Actions deliberately not taken

- No `EA_VRAS_RegimeAdaptiveScalper.mq5` or indicator `.mq5` was created.
- No EX5 was compiled.
- No offline economic probe, Strategy Tester run, run folder, report or metric
  was created.
- No old archive source was compiled and no prior result was relabeled as VRAS.
- No ADX, SD, session, M15, AVWAP, rejection or asset threshold was tuned from
  the prior outcomes above.

This is the required golden-path stop: a de-dup kill must end before code rather
than manufacture activity that cannot produce valid evidence.

## One non-exhaustive potential successor from this report

A future Owner-scoped successor would have to isolate an information-set delta,
not the full VRAS stack. One narrow candidate identified from this report that
may be worth an outcome-blind identity screen is:

`HYP-VRAS-TICKVOL-SDVWAP-REENTRY-EURUSD-M5-001`

Status: `IDEA_ONLY / NOT_AUTHORIZED / UNPROVEN_NEWNESS`.

- actual broker `tick_volume`-weighted Session VWAP and weighted SD;
- fixed 07:00 UTC anchor;
- first closed-bar re-entry after an excursion outside +/-2 weighted SD;
- no ADX, pivot/second AVWAP, M15 bias, RSI, wick/rejection stack, BOS, news
  filter or parameter grid.

Proposed, not-yet-preregistered screen gates are: prove a distinct decision
surface versus equal-weight and archived range-proxy controls (Jaccard <=0.80
against each), pooled cadence 2-5 signals per elapsed week, and at least 1
signal/week in both 2019-2020 and 2021-2022. If Owner opens this idea, the gates
must be frozen before outcome and failure must be terminal with no filter
rescue. Passing that identity screen would only authorize a fresh economic
prereg; verified broker cost evidence would still be required for
economic-authoritative Model 0. Other materially independent mechanisms or data
contracts remain possible after their own failure-radius review.
