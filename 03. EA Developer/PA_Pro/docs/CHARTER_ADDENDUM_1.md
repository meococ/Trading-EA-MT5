# Charter addendum 1 (Lead, binding) - 2026-09-20 19:20 VN

Owner direction (2026-09-20 19:18): a pro does not draw a perfect line. Support/resistance is a small AREA that price can
overshoot a little; lines may shift. A precise single line makes the chart hard and is not how a pro trader works. Have
DeepSeek research whether a good existing indicator does this well and apply it; if none is good enough, build one.

Binding changes:
1. PERCEPTION IS ZONE-FIRST. Horizontal structure is represented as ZONES [low, high] (width scaled by ATR, typically
   0.2-0.6 x ATR14(H1)), never as exact prices. Touch/respect/break are defined against the zone, with tolerance for
   small overshoots (a wick through the zone that closes back inside is a TEST, not a break).
2. Trendlines become BANDS (a channel of tolerance around the fitted line), are secondary to horizontal zones, and are
   not required in the first physics run.
3. Chart hygiene: at most ~4-6 zones armed near price (within +-2 x ATR14(H1)); merged, labelled, never duplicated.
4. ZONE GENERATOR BAKE-OFF replaces the single-generator physics test: every candidate zone generator (our LINE-1
   clusters, the best existing indicators found by the ZONE-1 survey, and any we build) is frozen and run through the SAME
   preregistered level-physics test (charter section 4). The winner is chosen by a pre-declared criterion (top-tercile
   bounce or break-continuation lift vs fake zones, CI lower bound > 0, monotone in strength, consistent across symbols
   and years), with multiplicity correction across candidates. Every candidate run is a ledger trial.
5. Existing indicators may be ported only if non-repainting (causal) or made causal, and only with license-compliant
   attribution. Describe algorithms in our own words; do not paste code from restrictive licenses.
