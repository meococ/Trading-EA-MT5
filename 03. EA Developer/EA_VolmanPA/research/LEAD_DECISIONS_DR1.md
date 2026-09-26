# LEAD DECISIONS — DR1 (T-VPA-DR1), saved verbatim

- **D1 — DR1 spec approved with these changes.**
  - **(a) Signal-bar direction.** The signal bar must close in the trade direction: a bearish close for shorts, a bullish close for longs. A neutral doji (|close−open| ≤ 0.1×range) is allowed (book p.95 GHI CHÚ).
  - **(b) Combi placement.** Combi is an entry-timing variant only inside a valid Pattern-Break context: the same barrier, buildup, trend, room, anti-chase, chop and session gates apply. It is never a standalone trigger (book p.125). Entry is a stop order 1 pip beyond the inside bar. The "wait for the strong-bar break" alternative is out of DR1.
  - **(c) Trend grid.** θ_slope grid = {0.0, 0.10}, replacing {0.05, 0.10}. θ=0.0 is the book-literal rule: never trade against a still-trending EMA25 (p.227). Keep frac_side ≥ 0.6. The DR1 baseline run uses the defaults only: θ=0.10, band 0.5, overlap 0.45, expiry 20. **No grid runs in this task.**
  - **(d) Room.** room_r ≥ 2.0 from entry stays the default. The book-literal equivalent (p.167: skip if the obstacle leaves <14/20 = 0.7×target profit) is 1.4R, but only with a manual exit. DR1 has none, so 2.0R is the justified substitute. Record this rationale in the prereg.
  - **(e) Geometry.** Fixed S=8 / TP=16, EURUSD M5, London primary plus US window per the spec. The low-vol profiles stay out.
- **D2 — Cadence rule (DESIGN census, executable/week).**
  - ≥10/week: normal.
  - 3 to <10/week: flag LOW_CADENCE and continue to fidelity grading. No economic or outcome run; the Lead escalates to the Owner.
  - <3/week: STOP after the census, report the rejection funnel and a recommendation.
- **D3 — Registry.** The hypothesis stays in state `probe` until the MQL5 build. If repo doctrine says DR1 needs a new frozen prereg id or row, follow the doctrine (research it first: `04. Memory`, `AGENTS.md`, the existing prereg/addendum pattern) and state what you did.
- **D4 — The 60 Lead-labelled cases** are reserved as a fixed grader-drift check set. Never use them to tune or select the detector.
- **D5 — Grading protocol at scale.**
  - Two blind graders (G1, G2) with GRADING_RUBRIC_V2, unchanged. When they agree, that grade stands. When they disagree, a third blind grader G3 decides by majority.
  - Report A/B precision both as the dual-agreement count and as the majority count, each with a Wilson 95% CI.
  - Note: the graders are more lenient than the Lead (A+B 33–42% vs the Lead's 27%), so report that inflation caveat.
  - The Lead blind-grades a spot-check of 20: 10 agreed-A/B, 5 disagreements, 5 agreed-C. Prepare `PLAN/grading_dr1/LEAD_SPOTCHECK_INDEX.csv` with case ids and snapshot paths only, with no grades or keys anywhere the Lead would see them first.
- **D6 — Stay outcome-blind.** Compute NO outcomes in this task: no fills-to-exit, no PnL, no win rate, no MFE/MAE, on any split. Snapshots show nothing after the decision bar.
