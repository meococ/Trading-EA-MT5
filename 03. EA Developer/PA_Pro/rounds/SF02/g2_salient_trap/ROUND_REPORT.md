# G2 — Salient-zone rejection / trap — DEPRIORITISED (no screen)

Verdict: **NOT RUN** — closed on autopsy evidence before any outcome
(Lead Review 2 allows pre-outcome re-prioritisation; census/outcome
budget for G2 = 0 cells spent).

## Candidate

F1/F3 logic (zone probe + rejection, or failed-breakout trap) restricted
to the single most salient armed zone per side, salience >= declared
threshold.

## Why the autopsy closed it

`rounds/SF02/AUTOPSY.md`, plan T000229:

- A2 exit-free edge: the probe/rejection families F1, F3 (and F2, F4)
  carry **adverse** directional information — edge-ratio delta vs
  matched random -0.26 to -0.68, BH-significant at every horizon
  (6..96 M5 bars). The entry direction itself is wrong, not merely the
  exits. Adding a salience filter keeps the same adverse entry style;
  there is no slice in A4 where a probe entry flips positive.
- A3 perception: salience terciles did not rescue lift for F1/F3 — the
  perception defect was *density* (4.6 armed zones near price for
  line1_cluster), which G1 already fixes by construction (single most
  salient zone) with a different, non-adverse entry style (limit at
  edge on a pullback).
- Remaining revision budget spent where the evidence points: G1
  (pullback-limit at salient zone) and G3 (build-up break at salient
  zone). A probe-entry family would repeat the falsified F1/F3
  mechanism on a smaller sample.

## What would reopen it

A Lead instruction, or new evidence that salient-zone probes behave
differently from the screened F1/F3 populations (none exists in DESIGN).
