# HYP-RSF-EURUSD-M5-NATIVE-OUTCOME-002 — visual failure packet

Status: `KILLED_EVIDENCE_ACCEPTANCE_FAILURE`

This diagnostic replay did not produce admissible post-exit evidence.

## Observed failure

1. The external Windows Graphics Capture payload was JPEG even though the
   destination contract required PNG. The first file therefore failed the PNG
   signature gate.
2. The 12-second wall-clock pause was too short to reliably detect the flag,
   attach to the portable tester window and capture before the replay resumed.
3. `CHART_SHIFT=true` left excessive blank space at the right edge, reducing the
   usable price/indicator area.
4. The rejected file did not satisfy the frozen June 4 outcome timestamp and is
   excluded from AlphaFactory import and all chart conclusions.

## Failure radius

The failure is confined to external visual evidence transport and chart layout.
It changes no entry, exit, indicator buffer, risk or economic metric. The run was
aborted and consumed zero economic trials because Model 1 visual output has no
economic authority.

## Successor boundary

A fresh ID must freeze: a 30-second hold, `CHART_SHIFT=false`, `CHART_END` with
zero shift, and lossless image-container normalization from the genuine native
window capture into verified PNG bytes. No crop, repaint, redraw simulation or
pixel editing is allowed.
