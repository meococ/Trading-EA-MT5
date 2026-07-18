# Readout — HYP-ICTVIS-EURUSD-M5-001 / EA_ICTVisualEdge

**Verdict: KILL_AT_DESIGN_IN_SAMPLE_ECONOMICS** (2026-07-18)

Method = OPEN visual feature-discovery (Owner-directed, seeded by the ICT report).
The method was executed honestly and *worked as a method* — the eye + quantified
feature battery genuinely surfaced discriminating structure. The **object** it was
applied to (generous M5 sweep-reversion) is confirmed dead on economics, from a
direction fully independent of the prior a-priori ICT lanes. Holdout 2023+ never
loaded (sealed); the kill lands at the cheapest possible gate — DESIGN in-sample.

## What was done

- **Stage 0** — froze the de-dup auto-fail predicate + anti-overfit contract
  BEFORE any render (`STAGE0_FREEZE.md`, SHA-bound in registry idea row).
- **Stage 1** — closed-bar M1->M5/M15 resampler + GENEROUS sweep detector
  (high-recall, no session/structure filter) + SEALED forward-R labels (2R,
  stop-first, cost-aware). M5 DESIGN: 39,122 candidates. Contract tests 6/6 PASS.
- **Stage 2 (visual)** — rendered 40 balanced asof (decision-time) charts on
  DESIGN only; the eye proposed 6 declared features (`STAGE2_VISUAL_READOUT.md`).
- **Stage 2-3 (quantify)** — computed each feature decision-time-safe on the full
  DESIGN set; measured separation; then measured the cost-aware economics of the
  best feature selection **in-sample on DESIGN**.

## Evidence (the numbers that decide it)

1. **The generous universe is near-random.** DESIGN base win-rate 34.5% at 2R
   (break-even 33.3%), mean gross R **+0.012**. At **zero cost** the whole
   universe PF is **1.019**.
2. **The method found a real but tiny edge.** Cleanest DESIGN separators:
   `F5 range-position` (enter at range extreme; rho +0.886) and `F4 sweep-wick`
   (smaller rejection wick better; rho -0.915). Top-decile by F5+F4 reaches PF
   **1.12 at zero cost** (win 0.342 -> 0.359). The visual method demonstrably
   discriminates — this is the honest upside it produced.
3. **The edge cannot survive cost.** Median sweep risk is only **4.5 pips**, so
   1.5 pip RT ≈ **0.33R/trade**. Cost-sensitivity of the top-decile selection:

   | cost (pip RT) | PF all | PF top-10% (F5+F4) |
   |---------------|--------|--------------------|
   | 0.00          | 1.019  | 1.12               |
   | 0.25          | 0.934  | 0.995              |
   | 0.50          | 0.858  | 0.887              |
   | 0.75          | 0.790  | 0.793              |
   | 1.50 (frozen) | 0.620  | 0.573              |

   The feature selection *raises win-rate but concentrates into tighter-risk,
   higher-cost trades*, so net PF gets **worse**, not better. Dead by 0.5 pip.

## De-dup adjudication (auto-fail predicate)

**NOT an auto-fail-by-de-dup.** The surviving features — range-position and
sweep-wick morphology — are mean-reversion **context/morphology**, provably not
the killed ICT primitive set `{sweep-as-edge, displacement/MSS/BOS, FVG/OB retest,
killzone, HTF-bias}`. The eye's initial "shorting into momentum is bad" read (a
displacement-grey-zone idea) was **REFUTED by population stats** (F1 rho -0.915,
opposite sign) — a clean instance of the overfit-by-eye trap the quantification
exists to catch. So this is KILL taxonomy **(b)**: a materially-different feature
that fails on economics, NOT (a) a resurrected dead object.

## Why this is stronger than the prior ICT kills

DRAT killed the object by memo-funnel simulation. This kills it by a **data-driven,
visually-seeded OPEN search** that was free to find *any* non-primitive feature and
still could not beat cost even in-sample. The M5 sweep-reversion geometry is
structurally cost-dominated: stops are too tight (4.5 pip median) for realistic
EURUSD cost. No visual feature rescues it.

## Boundary of this verdict (what is NOT concluded)

- This kills the **M5 generous-sweep 2R object on price-only EURUSD**, not "OHLC
  has no edge" and not "visual feature-discovery is a dead method". The method
  found real separation; the object's cost geometry defeats it.
- A genuinely different **object** with wider stops / different entry geometry, or
  a **new information set** (order-flow / options / OI), remains a separate,
  un-probed question — its own hypothesis, not a rescue of this one.

## Artifacts (SHA-bound)

- Freeze: `HYP-ICTVIS-EURUSD-M5-001_STAGE0_FREEZE.md` SHA `4A5D6675…B0A2`
- Stage-1 manifest: `evidence/stage1/stage1_manifest.json` SHA `1B5F6D38…374E`
- Features: `evidence/stage1/candidates_M5_features.parquet` SHA `F1B3DE3B…A27F`
- DESIGN separation: `evidence/stage1/stage2_design_separation.json` SHA `F7EA6B77…485C`
- DESIGN economics: `evidence/stage1/stage23_design_economics.json` SHA `D3514C6D…AB9E`
- Contract tests: `tests/test_ictvis_stage1_contract.py` 6/6 PASS.
- Holdout: 2023+ never loaded (sealed). No .mq5 / compile / Model 0.
