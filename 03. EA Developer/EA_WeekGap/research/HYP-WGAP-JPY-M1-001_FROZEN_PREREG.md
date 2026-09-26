# HYP-WGAP-JPY-M1-001 — FROZEN 2026-09-19 (GATE B PASS both seats)

Status: **FROZEN.** GATE B round 1: Gatekeeper WARN (10 additions),
Auditor FAIL (11 attacks). Round 2 re-review after all decisive checks
published: **Auditor PASS-with-conditions** (3 mechanical items — ledger
row verified in lab.duckdb, artifact path fixed + gap_pips ctm-aligned,
funded-spread artifact committed); **Gatekeeper PASS** (all 10 additions
verified; artifact path fixed). Frozen with the spec below — no further
edits except verdict/kill annotation after the governed run.
2026-09-19.

## Falsification context

- Full falsification map:
  `04. Memory/research/20260919_LAB_FALSIFICATION_MAP_AND_COST_REFRAME.md`
  (~91k cells, two cost planes — every unconditional class dead).
- HYP-WOPEN-CHF-M1-001 killed at GATE B; its audit discovered the
  Monday-01h edge is a weekend-gap conditional.
- This cell is that conditional on USDJPY — the strongest conditional
  cell measured. **Selection basis (declared):** post-hoc, from the
  ~200-cell gap-conditional family probed during the WOPEN kill; NOT
  pre-declared. Parameters sit at the measured mechanism boundary
  (02:00 entry dead; hold>60 decays) — not tuned past it.
- **Committed reproduction:** `lab/probe_weekgap.py` → ledger row
  `weekgap_fade/USDJPY` (cell_hash via Lab.record, sim_version 4) +
  450-event artifact
  `03. EA Developer/EA_WeekGap/research/evidence/wgap_jpy_events.csv`.

## Hypothesis (spec to freeze)

- **Mechanism (honest label):** weekend gap-down fade at the week-
  reopen's second hour, confined to the post-2016 dispersed-open feed
  regime and the EEST half of the year. The "Tokyo open" label is
  DEMOTED: the edge does not migrate to the 02:00 cell in EET weeks —
  it is a server-clock week-reopen effect, not a verifiable Tokyo-flow
  effect (DST table below).
- **Symbol / timeframe:** USDJPY, M1 closed-bar decisions.
- **Condition:** weekend gap < −2.0 pips; gap = open(week's first M1
  bar) − close(bar immediately before it). Both legs known by ~00:06
  server — ~55 min before the decision; no lookahead. Lab `dow`=pandas
  0=Monday; MQL5 `day_of_week` 1=Monday (one-offset noted).
- **Signal:** bar stamped 01:00 server Monday.
- **Entry:** LONG at open of the 01:01 bar — next-bar-open fill.
- **Exits:** SL 20p fixed. TP none. **Time exit at the CLOSE of the
  bar stamped 02:01** (EA acts on the 02:02 new-bar event) — bit-exact
  with lab `c[entry+60]`. hold59-vs-60 delta measured immaterial
  (+2.34/1.59 vs +2.16/1.54).
- **Missing bars:** if the 01:00 or 01:01 bar is absent (data hole),
  the EA skips — matches lab drop semantics.
- **Per-trade logging:** EA logs measured gap + first-bar identity per
  trade (required for GATE C "gap condition applied" enforcement).
- **Sizing:** 0.25% risk/trade; margin-capped; daily 2% lock; account
  10% DD lock.
- **Cadence — DECLARED SUB-FLOOR:** ~0.51/wk (450/869 weeks). GOAL
  floor 10/wk — calibration run per HYP-RGR precedent, never DONE.
- **News/overnight/weekend:** flat by ~02:02 Monday; blackout retained.

## Probe evidence — committed, all checks published

USDJPY Mon-01h long, gap<−2p, sl=20, tp=0, hold=60 (sim v4):

| Plane | n | net | PF | pos_yr | t |
|---|---|---|---|---|---|
| deploy proxy 1.0p RT | 450 | +3.24 | 1.90 | 0.65 | 3.12 |
| recorded spread+comm | 450 | +2.16 | **1.54** | 0.65 | 3.12 |

- **Cost stress (recorded plane, honest bound):** x1.5 → +1.12/**PF
  1.25**; x2 → +0.07/**PF 1.01** — sits exactly ON both gates. Thin.
- **Tester cost reality (declared):** Model-0 governed run applies
  configured spread (~2pt=0.2p "current") — cost-tier gates are
  vacuous at tester; the recorded-plane stress above is the binding
  one and is evaluated probe-side / via post-hoc re-price of the
  executed trade list (declared, labeled non-governed).
- **Deploy-venue spread measured for THIS window:** FivePercentOnline-
  Real USDJPY ticks, 6 Mondays 01:00–02:00 (2026-06→09): med 0.2–0.3p,
  p90 0.5–0.6p → deploy RT ≈ 1.0p. (Auditor's "unmeasured" concern —
  measured.)
- **Boundary:** hold60 1.54 / hold120 1.16 / hold240 0.87; Mon-02h
  entry −2.68/0.54; gap-up −1.20/0.75; |gap|≤2 +0.36/1.10.
- **Threshold robustness:** gap<−1 1.54 / −2 1.54 / −3 1.61 / −5 1.54 /
  −10 1.68 — smooth, not a spike.
- **Gap-definition robustness:** suspect-inclusive first-bar def
  +2.16/1.54 (n=450) vs first-NON-suspect def +1.93/1.46 (n=381) —
  **18.7% membership flips** between definitions but edge holds under
  both. The EA classifies on raw broker bars; ~1/8 weeks may differ
  from lab membership (feed-boundary noise), declared.
- **Gap legs are open/close only** — the first bar's fabricated `h/l`
  (daily-summary record) is never read. Cross-broker: 8/8 week-first
  opens exact vs Owner GUI; prev-bar (Friday last) closes deviate ≤14p
  on 2/8 weeks including one sign flip (2026-09-14: GUI −1.4 vs lab
  +5.7) — the feed-portability noise behind weakness #5.
- **Funded-venue artifact:** `evidence/USDJPY_funded_spread_mon01h.json`
  (6 Mondays, ticks 6.3k–13.7k each; thin-tail caveat recorded).
- **Suspect-drop counterfactual:** drop disabled → +2.12/1.53 (n=452);
  no inflation. drop_entry=2, drop_path=0, n_gap_path=11.
- **Split-half:** +0.14 / +4.18 — both positive, H1 near-flat.

## Era × record-type — the edge's real habitat (declared, not hidden)

- Conditional per-year (net pips): 2010 +88.7 | 2011 +58.8 | **2012
  −53.5 | 2013 −65.5 | 2014 −38.1 | 2015 −49.8** | 2016 +93.3 | 2017
  −126.9 | 2018 −15.0 | 2019 +59.9 | 2020 +73.9 | 2021 +67.5 | 2022
  +334.3 | 2023 +2.8 | 2024 +121.0 | 2025 +226.3 | 2026 +193.8.
- **has-00:00-record split:** weeks WITH the packed record
  +0.64/1.13 (n=188) vs weeks WITHOUT it **+3.25/1.98** (n=262) — the
  edge lives in the dispersed-open (mostly post-2016) regime, same
  signature as the CHF kill.
- **DST split:** EEST months +3.17/**2.05** vs EET +0.59/1.11; the
  02:00 cell is dead in BOTH halves (−2.37/0.52, −3.14/0.56) — the
  effect does not migrate with the Tokyo clock.

## Declared weaknesses

1. Era concentration — real edge is 2016+/EEST/dispersed-open regime;
   governed full-window run will show the early-era drag.
2. pos_yr 0.65; half1 +0.14.
3. Single-JPY-pair; coherence untestable in-universe.
4. Cadence ~0.51/wk — permanent GOAL miss.
5. Gap membership fragile at boundaries (~1/8 weeks feed-dependent).
6. Recorded-plane stress sits ON the x1.5/x2 boundaries, not above.

## Validation posture — DECLARED

No sealed holdout exists; cell selected on full 2010–2026 window during
kill analysis. The governed run is a transfer-fidelity/calibration
test, NOT OOS. DONE unreachable regardless — cadence miss + no sealed
arm.

## Environment (frozen)

- MetaQuotes-Demo portable isolate, RESEARCH-ONLY.
- Window: USDJPY lab coverage verified 2010.01.04 → 2026.09.18
  (data_plane asserted).
- Model 0. Tester spread: configured "current" (~2pt) — the governed
  run calibrates the **deploy-equivalent plane** (~0.9p RT); recorded-
  plane economics are evaluated on the executed trade list post-hoc.
- Clock: server time throughout.

## Acceptance contract (frozen)

| Gate | Value |
|---|---|
| min_profit_factor | 1.30 |
| min_trades_per_week | DECLARED MISS (~0.5) — calibration run |
| max_trades_per_week | 40 |
| max_drawdown_pct | 20.0 |
| max_monte_carlo_p95_dd_pct | 20.0 |
| min_cost_pf_x1_5 | 1.25 (evaluated on recorded-plane re-price) |
| min_cost_pf_x2 | 1.00 (same) |
| history_quality | >97 |

## Trial budget (frozen)

Baseline + at most 1 market-logic revision, then KILL. No subgroup
salvage, no post-hoc parameter rescue.

## Kill criteria (frozen)

- Governed PF ≤ 1.30 at x1.
- Recorded-plane re-price of executed list fails x1.5 ≥1.25 or
  x2 ≥1.00.
- **Era clause:** PF>1.30 with edge exclusively post-2020 AND pre-2016
  materially negative → classify MARGINAL, not PASS.
- Executed sample ≠ declared mechanism (entry ≠ 01:01 bar open, side ≠
  long, gap condition not applied/mislogged).
- Probe↔governed divergence unexplained by GATE C.

## Falsifier statement

After weekend gap-down ≥2p, USDJPY drifts UP during 01:01–02:01 server
Monday (exit at 02:01 bar close). Falsified if governed net ≤ 0 or
PF ≤ 1.30 on the executed sample.
