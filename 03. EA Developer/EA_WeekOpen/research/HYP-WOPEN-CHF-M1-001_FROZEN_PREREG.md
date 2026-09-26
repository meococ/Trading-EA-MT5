# KILLED AT GATE B — HYP-WOPEN-CHF-M1-001 (never frozen)

Status: **KILLED 2026-09-19 before freeze.** The GATE B review pair
(Adversarial Auditor: FAIL; GOAL Gatekeeper: WARN-with-gaps) plus the
auditor's decisive checks killed the hypothesis before any EA code or
governed run. This file preserves the full evidence trail — the draft
prereg content is kept below the kill record for auditability.

## GATE B verdicts

- **Adversarial Auditor: FAIL** — seven attacks; decisive items:
  (1) mechanism text described the wrong hour (weekly open is the 00:00
  bar = 17:00 ET roll, not the 01:00 bar); (2) RGR-class fill validation
  never run on this window; (3) cross-symbol coherence claim contradicted
  by the ledger (EURUSD Mon-1h long is flat −0.82/PF0.80, not "risk-on");
  (4) short-side asymmetry is implied arithmetic, not evidence;
  (5) selection/survival stats weaker than campaign rules; (6) n_gap_path
  discarded before ledger; (7) **recorded spread at window never checked
  vs the 1.0p cost assumption.**
- **GOAL Gatekeeper: WARN** — freeze was contract-legal as a declared
  calibration run (RGR precedent verified), but no outcome could produce
  DONE (cadence ~1.01/wk vs floor 10); required acceptance-table additions
  (applied to draft below before kill), validation-posture declaration,
  and hour-wording fix (applied).

## Decisive checks run (parent, on lab parquet + Owner-GUI bars)

1. **Bar-envelope / fabrication check — PASSED.** 360/360 Owner-GUI
   (FivePercentOnline-Real) M1 bars match lab .hcc bars at identical
   stamps for the last 6 Mondays 01:00–01:59. Close deviation: median
   0.20p, p90 0.80p, max 3.8p — bars envelope real tradable prices,
   NOT an RGR-class fabrication. 0% suspect flags in window. Week opens
   at 00:00 server on both feeds (Gatekeeper watch-item answered).
2. **First-bar-of-week census.** First decodeable Monday bar is 00:00
   in only ~416/869 weeks; ~half of weeks start at 00:01–00:05 (open
   burst spread over minutes, era-dependent: pre-2016 mostly 00:00,
   post-2016 dispersed). The hour-0 cell is ~100% event-killed by
   suspect rules — unmeasurable; hour-1 is the first complete hour.
3. **Era split — edge is a post-2016, mostly post-2020 phenomenon:**
   2010–15 +0.35p/PF1.11 | 2016–19 +0.66/1.33 | 2020–23 +2.28/2.22 |
   2024–26 +3.91/3.48. Fails the campaign's stability standard; the
   "13/17 positive years" claim was aggregation-masking.
4. **Weekend-gap conditioning — mechanism mislabeled.** Split by gap
   sign: gap-down weeks +2.82p/PF2.51 (n=407) | gap-up +0.12/PF1.04
   (n=404) | flat +1.24/1.57. The edge is a **weekend-gap fade**, not
   unconditional weekly-open drift — a different (conditional)
   hypothesis than preregistered.
5. **has-00:00-bar split:** weeks missing the 00:00 bar +2.02/PF2.00
   vs weeks with it +0.87/PF1.32 — correlates with the era pattern.
6. **Sister cells (dow0/hour1, all symbols):** EURUSD long flat
   (−0.82/PF0.80), GBPUSD/AUDUSD/NZDUSD no coherent risk-on pattern —
   mechanism relabeled to haven-selloff at best.
7. **Recorded spread at window — the kill shot.** Feed `sp` (points):
   Mon 01h median 15pt = **1.5p**, p90 33pt = 3.3p (midday baseline
   7pt = 0.7p; Mon 00h median 41pt = 4.1p, correctly excluded).
   At cost = entry-recorded-spread + 0.7p commission:
   **net −1.11p, PF 0.69** (n=761). Even the gap-down subset:
   **−0.09p, PF 0.97** (n=372). The +1.46p edge was entirely a
   flat-cost-proxy artifact.
8. **All four grid survivors die at honest cost:**
   USDCHF Mon1h −1.11/0.69; USDJPY Mon1h +0.62/1.15 (sp 1.2p);
   XAUUSD Fri9h −6.41/0.62 (sp 1.4p+p90 5.3p); EURUSD Wed1h −0.77/0.73.

## Structural finding (campaign-level)

The flat 1.0p round-trip cost proxy is falsified for boundary-adjacent
windows: recorded spread is 0.7p midday → 1.2–1.5p at the exact hours
where anomalies appeared → 4.1p at the roll. **Edges and recorded
spread are anti-correlated by microstructure** — cells show gross edge
precisely where liquidity is thin and cost is highest. The corrected
grid's surviving cells were all cost-understatement artifacts.

Consequence: `sweep`/eval must price cost as per-event recorded spread
(+ commission) — `sp` column exists in the data plane; the flat proxy
is deprecated for cell economics. Cells whose edge survives ONLY at
tight-spread brokers are broker-transfer hypotheses, not feed
hypotheses, and must be declared as such (USDCHF Mon-01h at a ~0.2p
spread broker would still be ~+1.5p net — but the era concentration
and gap-conditioning remain).

## Kill classification

- **Cost-model failure** (primary): edge evaporates at the feed's own
  recorded spread.
- **Mechanism-label failure** (secondary): edge is weekend-gap-fade
  conditional, not unconditional weekly-open drift; the conditional
  variant also dies at honest cost (PF 0.97).
- **Stability failure** (tertiary): post-2020 era concentration.
- NOT a data-fabrication kill — bar layer verified real (0.20p
  cross-broker median deviation).

## What remains legally open from this attack surface

- A gap-fade hypothesis (fade weekend-gap direction, conditioned on
  gap size) at a tighter-spread venue would need its own prereg and a
  declared broker-transfer cost model — the demo feed's recorded
  spread kills it here.
- H1/H4/D1 timeframes where gross edges are 10–50p and the 1–2p cost
  floor is negligible — the GOAL explicitly permits these "according
  to mechanism"; nothing from this kill blocks them.

---
---

## (Archive) Draft prereg as it stood when killed

Status: DRAFT awaiting GATE B review (Adversarial Auditor + GOAL
Gatekeeper). Frozen only after both PASS. Written before any governed
outcome for this hypothesis. 2026-09-19.

## Falsification context (why this hypothesis now)

- The corrected lab campaign (sim v3, 35.5k cells, 8 symbols) falsified
  the M1 event-driven class entirely: max |raw edge| ~1.27p < ~1.0p RT
  cost floor. Impulse/breakout/pullback continuation: dead both sides.
- EURUSD European-USD-bid short (HYP-EUSBID-EUR-M1-001) was killed
  in-probe after GATE A caught the simulator's short-side SL/TP field
  swap — corrected PF 1.15-1.25 < 1.30.
- **Four cells survive the whole corrected grid.** This is the
  strongest: USDCHF Monday 01:00 LONG, discovered systematically by the
  drift_mow family, not hand-picked.
- Post-hoc basis declared: the cell comes from a 240-cell/symbol
  dow×hour grid; it was not pre-declared. Multiple-testing handled via
  ledger-wide FDR (t=5.01 -> p~3e-7, q<<0.01 at m~35k).

## Hypothesis (frozen spec)

- **Mechanism:** weekly-open repositioning. The broker week opens at
  server 00:00 Monday (verified: M1 bars exist from 00:00 onward; the
  00:00-00:15 roll burst is suspect-flagged ~27% and dropped). The bar
  stamped 01:00 is therefore hour-index-1 — the **first trusted hour of
  the trading week**, one hour after the untradeable reopen burst.
  Haven currencies CHF/JPY are sold while risk FX is bought; USDCHF
  drifts UP during this window. Cross-symbol coherence: USDJPY Mon-1h
  long +1.49/PF1.38 (same driver); EURUSD/GBPUSD Mon-1h shorts lose
  (EUR/GBP also bid) — a risk-on open, not a USD quirk.
- **Symbol / timeframe:** USDCHF, M1 closed-bar decisions.
- **Signal:** bar stamped 01:00 server on Monday (dow=0, mod=60) —
  explicitly NOT the weekly-open bar (00:00), avoiding RGR-class
  reopen-burst adjacency.
- **Entry:** LONG at OPEN of the next M1 bar (~01:01) — next-bar-open
  fill, same convention as the lab simulator and the governed tester.
- **Exits:** SL = 20 pips fixed (broker side). TP = none. Time exit at
  close of the M1 bar stamped 02:01 (i.e., entry bar 01:01 + 60 bars;
  the EA acts on the new-bar event at ~02:02). Hard flats retained.
- **Sizing:** 0.25% equity risk per trade (DD-bounded); margin-capped;
  daily loss lock 2%; account DD lock 10%.
- **Cadence — DECLARED SUB-FLOOR:** ~1.01 trades/week. The GOAL floor is
  10/wk. Per the HYP-RGR precedent this run is a **calibration and
  economics validation**: it tests whether a real, integrity-clean
  anomaly reproduces under governed fills — not cadence compliance.
- **News:** keep the substrate's ±20min blackout (safety layer stays;
  Sunday-open high-impact events are rare but the layer costs nothing).
- **Weekend/overnight:** none — position always flat by ~02:02 Monday.
- **Validation posture — DECLARED:** no sealed holdout exists. The cell
  was selected on the full 2010-2026 window; the governed run is a
  transfer-fidelity test (does the lab plane reproduce under governed
  fills), NOT an out-of-sample test. Any future DONE claim on this
  mechanism would additionally require a sealed-window re-validation;
  that is out of scope for this calibration run and blocks DONE
  regardless of outcome.

## Evidence (sim v3 — post GATE A fix)

USDCHF Mon 1h long, sl=20, tp=0, hold=60, cost_rt=1.0p, 2010-2026:

- n=860 events (all kept; 0% suspect in Mon 1h window; the roll-burst
  contamination is confined to hour 0, ~27% flagged, fully dropped)
- net **+1.46 pips/trade**, t=5.01, **PF 1.62**, pos_year 0.76 (13/17)
- hold=240 variant: +1.87, PF 1.42, pos_year 0.82
- Asymmetry check: same cell SHORT = -3.59/PF 0.29 — directional flow,
  not noise harvesting.
- Split-half and per-year: positive both halves; positive years spread
  across 2010-2026 (13/17 at h60, 14/17 at h240).
- h60 chosen over h240 as primary (higher PF + cleaner exits); h240 is
  the fallback revision arm inside the same hypothesis.
- Tick spot-check (EURUSD midday, cross-broker): .hcc bars envelope
  real ticks at 0.30p median — the midday-liquidity window is trusted;
  the 01:00 Monday window passed the same flagging regime.
- USDJPY Mon-1h suspect caveat: JPY data has 22% suspect share
  historically, but Mon 1h shows 0% — still treated as secondary
  confirmation, not primary evidence.

## Environment (frozen)

- Broker/server: MetaQuotes Ltd. / MetaQuotes-Demo (AlphaFactory
  portable isolate). RESEARCH-ONLY, non-promotable.
- Coverage: all_available_asof — verified USDCHF coverage window from
  the prior discovery run; bind --from-date/--to-date to that identity.
- Model: 0 (every tick from M1 bars). Cost tier: research_proxy
  (tester-current spread + $7.00/lot RT + measured slippage proxy).
- Clock: server time throughout; no GMT conversion needed (the signal
  is server-clock anchored — 01:00 Monday server).

## Acceptance contract (frozen)

| Gate | Value |
|---|---|
| min_profit_factor | 1.30 |
| min_trades_per_week | DECLARED MISS (~1.0) — calibration run |
| max_trades_per_week | 40 |
| max_drawdown_pct | 20.0 |
| max_monte_carlo_p95_dd_pct | 20.0 |
| min_cost_pf_x1_5 | 1.25 |
| min_cost_pf_x2 | 1.00 |
| history_quality | >97 |

Verdict semantics: economics PASS = PF>1.30 x1 AND cost tiers hold —
that is a positive probe↔governed calibration point, not GOAL DONE.
Cadence remains a declared miss; a GOAL-compliant campaign still needs
a frequency solution (multi-cell stack or Owner contract amendment).

## Trial budget (frozen)

Baseline + at most 2 market-logic revisions (e.g., h240 arm), then
KILL. No subgroup salvage, no post-hoc parameter rescue.

## Kill criteria (frozen)

- Governed PF ≤ 1.30 at x1, or cost-tier breach.
- Executed sample not matching the declared mechanism (wrong entry
  window, wrong side, extra filters).
- Probe↔governed divergence unexplained by GATE C review.

## Falsifier statement

The hypothesis predicts: USDCHF drifts UP in the first trusted hour of
the trading week (01:00-02:01 server Monday window). It is falsified if
the governed run shows non-positive net expectancy or PF ≤ 1.30 — the
lab sim then overestimates the capture even on a clean-data,
real-mechanism cell, and the probe↔governed parity question stays open
negative.
