# HYP-RSF-EURUSD-M5-VISUAL-007 — Failure Packet

Status: `KILLED_ENGINEERING_DIAGNOSTIC`

## What was proven

- AlphaFactory imported the genuine native MT5 Visual Mode PNG into the run
  chart bundle before finalization.
- The imported image is `NATIVE_MT5_VISUAL007_EURUSD_M5.png`, `506378` bytes,
  SHA-256 `D7D2D7D8F0DFDDD1125E6995637CD26FB10B6EA94184AFB55B38627C681C4FC4`.
- The frame is a capture of the Strategy Tester Visualization window, not a
  Python or synthetic reconstruction.
- Price, MBB and the reduced-retention TB overlay were visible.  QQE's white
  trend line rendered, but the histogram remained absent.

## Why this ID is killed

1. The lifecycle RunMeta emitted `EA_RegimeStructureFusion` while the manifest
   correctly bound `EA_RegimeStructureFusionForensics`.  This wrapper/parent
   identity mismatch made run completion fail closed.
2. The native frame still did not show the QQE histogram.  A visual crop alone
   cannot distinguish a zero-valued display buffer from a ChartIndicatorAdd
   rendering defect, and the tester `.set` files contain the expected QQE
   defaults.  The earlier stale-parameter inference is therefore rejected.

No economic conclusion is authorized.  The follow-up must derive RunMeta EA
identity from `MQL_PROGRAM_NAME` and record the display handle's closed-bar QQE
buffers `0`, `2`, `3`, `4`, `8`, `10`, `11`, and `12` beside the native image.
Those changes require a fresh diagnostic hypothesis ID.
