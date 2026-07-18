# Operational closure — HYP-UPS-XAU-M5-005

## Verdict

**PARK WITHOUT MODEL 0. No performance evidence exists for HYP-005.**

The event-anchored sweep mechanism passed its frozen no-outcome probe, compiled
with zero errors/warnings, passed eight contract tests and passed the exact
source-bound non-repaint audit. The frozen Model-0 role, however, is
`challenger`, while the only available cost evidence is explicitly
`RESEARCH_PROXY`. AlphaFactory correctly rejects that combination: research
proxy evidence may falsify a `control` but may never authorize a challenger or
promotion comparison.

No threshold, signal rule, date/hour filter or risk rule is changed. HYP-005 is
parked before execution rather than being relabelled after the valid four-bar
control outcome was read.

## Preserved evidence

- Frozen preregistration: `HYP-UPS-XAU-M5-005_FROZEN_PREREG.md`.
- No-outcome probe: `evidence/20260716_HYP_UPS_XAU_M5_005_PROBE.json`.
- Static audit: `evidence/HYP-UPS-XAU-M5-005_STATIC_AUDIT/`.
- Exact source SHA256:
  `D7698C250906A48B750351C70ACBA84B5ED7E4DC9CE51EA74967EECBEC999011`.

The same already-frozen mechanism may only continue through a separately
registered operational successor whose sole changes are hypothesis identity
and research-control role. That successor cannot claim a matched challenger
win and remains non-promotable under every result.
