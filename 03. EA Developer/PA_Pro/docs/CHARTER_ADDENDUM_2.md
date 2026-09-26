# CHARTER ADDENDUM 2 — control design for the level-physics test (BINDING)

Amends `PA_PRO_CHARTER.md` §4, the clause "K=5 fake zones ... placed at prices with no real zone or
reference level within 2 widths". Issued by the Lead, 2026-09-20 22:15 VN. Dictated by the Lead and
transcribed verbatim by the R01 orchestrator; verified by Lead read-back.

1. MEASUREMENT THAT FORCED IT (outcome-blind; EURUSD, 48 sampled days, line1_cluster): the literal
   exclusion leaves 2.6% of the candidate price space eligible, 85% of real events have essentially zero
   eligible space, and the realized control count is K = 0.08 per event (20 controls for 264 events).
   The charter-literal rule is empirically infeasible and is replaced.

2. REPLACEMENT (primary control). Per real event, K = 5 matched arbitrary bands: same anchor bar t, same
   side, same width w, near edge at least 1.0 x ATR14(H1)(t) from c_{t-1}, centre drawn Uniform over the
   eligible same-side part of the 5-day range R5, the fake event being the first fresh approach under the
   identical event rules, up to 20 redraws, per-event seeded RNG. The ONLY placement exclusion is that the
   fake band may not overlap the triggering zone Z itself. No other zone and no reference level is excluded.

3. ESTIMAND. D = P(bounce | fresh approach to an ARMED zone of generator g) - P(bounce | fresh approach to
   a geometry-matched arbitrary band). D is the incremental value of using this generator's zones instead
   of an arbitrary level of the same geometry. A fake band may coincide with real structure; that
   contamination biases D toward zero, never away from it.

4. REPORTING (descriptive, never gates, never tie-breaks): per generator, the contamination rate of the
   realized controls, the share of control bands containing a reference level, the median coverage of the
   +-2 x ATR14(H1) window by that generator's armed bands, and the sensitivity views S-CLEAN (clean
   controls only) and S-NEAR (control event within 1 day of the anchor).

5. DECLARED INTERPRETATION. A sparser generator is attenuated less by contamination than a denser one.
   Selectivity is part of what the bake-off measures and is not corrected for; it is reported so that the
   reader can see it.

6. UNCHANGED. Everything else in charter §4, all gate thresholds, the power floors, the winner rule of
   `research/zones/SHORTLIST.md` §4, and the ARMED primary population of
   `rounds/R01/00_LEAD_RULINGS_READ_FIRST.md` §1.
