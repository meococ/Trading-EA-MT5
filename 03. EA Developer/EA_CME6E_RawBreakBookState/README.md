# EA_CME6E_RawBreakBookState — research-only external-data lane

Two adjacent objects are now terminal:

- `HYP-CME6E-RAWBREAK-BOOKSTATE-001` killed the exact stale pre-break-bar
  five-level score (N230, PF0.527529, meanR -0.365156). Its clock-forensics
  finding remains valid: the source window normally ended five minutes before
  the actual next-bar decision/entry.
- `HYP-CME6E-RAWBREAK-BOOKTRANSITION-002` then tested that missing clock-correct
  surface on a fresh 2021-2022 DESIGN population. Owner plan
  `C57B0AF9...64A1D1C` acquired 561/561 nonempty windows plus four planned
  metadata-empty identities for a journal estimate of USD0.696219488984.
  Dual clocks and 565 outcomes reconciled. The frozen top-50 transition score
  returned N258, cadence2.477366/week, PF0.782315, meanR -0.155912, net
  -USD382.83 and DSR0.030471; both years and directions lose and only 2/11
  gates pass. It is slightly worse than both the quality control and bottom
  score control.

Frozen post-kill chart forensics then sampled 12 cases before image view and
rendered separate future-hidden decision charts plus outcome anatomy. Direct
lifecycle reconstruction confirms that price profit is already negative before
separable explicit cost (PF0.9353/net -USD101.79); commission/swap/fee adds
-USD281.04. The dominant anatomy is entry failure: 161/258 SL-like trades,
including 74 stops within 15 minutes (-USD823.50). Decision-time winners and
losers overlap, the score has only rho0.0627 versus realized R, and the highest
score quartile is not the best. Extended prior H1/24-hour directional context
is a post-outcome exhaustion lead, not an authorized filter. The chart
postmortem confirms the kill and narrows the likely failure to the immediate
first-close entry/context surface; no HYP-002 management rescue is legal.
An independent one-image-at-a-time Grok audit then accepted 24/24 stateless
vision jobs. Blind decision review was 10/12 ambiguous; the only two
directional continuation calls split one correct/one wrong. Outcome review
classified six clean continuations, three immediate failed breaks and three
favorable-then-giveback losses. Four of six losses were assigned primarily to
setup/entry and two to exit management. All jobs passed exact image SHA,
ACP-image-count-one, EndTurn, schema and `image_opened=true` gates. This
confirms the outcome anatomy but supplies no decision-time rescue rule.

The clock bug was a fidelity defect, not the source of alpha. Do not rescue
either opened object with another percentile, score weight, depth level,
quality exclusion, direction/year/session veto, cost tier or management
overlay. A successor needs a fresh population and materially different
mechanism/decision surface, plus a new Owner-approved source plan if paid data
is required.

Readouts:

- `research/HYP-CME6E-RAWBREAK-BOOKSTATE-001_READOUT.md`;
- `research/HYP-CME6E-RAWBREAK-BOOKSTATE-001_CHART_FORENSICS_READOUT.md`;
- `research/HYP-CME6E-RAWBREAK-BOOKTRANSITION-002_READOUT.md`;
- `research/HYP-CME6E-RAWBREAK-BOOKTRANSITION-002_CHART_FORENSICS_READOUT.md`;
- `research/HYP-CME6E-RAWBREAK-BOOKTRANSITION-002_GROK_EACH_IMAGE_READOUT.md`.

This package remains research-only: no `.mq5`, Model 0, promotion, paper or
live authority.
