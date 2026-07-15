# Design memo — London–NY overlap EUR/GBP structural board

Date: 2026-07-15
Lane: single; no-Git; offline-first; `EXO_FRED_DISPLACE_SPAM_PAUSED`

## Problem

MFE stall-cut + Asia pctl-coil KILL. Exit-path on RR2 exhausted. Asia nearest
miss cadence-only — no densify. Named next: NY/London-overlap structure on
EUR/GBP not Wave5–7/MULTISYM-exhausted.

## Rejected a priori

- FRED displace/ToT spam.
- RR2 BE@1R / MFE stall-cut densify.
- Asia coil p40/hours densify.
- MULTISYM EUR 07–10 continue-break hour/RR rescue.
- MULTISYM GBP NY-impulse body/ATR densify.
- IB/ORB/NY-IB/LORBA/Spark/ITSM family retune.
- Invent multi-month cost freeze.

## Design 1 — EUR London imbalance → NY fade

`HYP-EURUSD-H1-LONDON-IMBAL-NY-FADE-001`

**Thesis:** One-sided London AM (07–12) mid-displacement leaves inventory that
NY-overlap liquidity mean-reverts toward London mid.

**Frozen:** arm `|Close12−Mid|≥0.75·ATR` and LondonRange≥0.80·ATR; fire first
mid-cross close 13–16; SL beyond London extreme ±0.10·ATR; RR=2; 1/day; EXPIRE 16.

## Design 2 — GBP London coil → NY break

`HYP-GBPUSD-H1-LONDON-COIL-NY-BREAK-001`

**Thesis:** Relative London-AM coil stores energy released on first NY-overlap
range break (state arm → fire → EXPIRE).

**Frozen:** coil LondonRange ≤ p40 of prior 60; fire 13–16 close beyond London
H/L; SL opposite extreme; RR=2.5; 1/day; EXPIRE 16.

## Design 3 — EUR lead → GBP overlap catch-up

`HYP-GBPUSD-H1-EURUSD-LEAD-OVERLAP-CATCHUP-001`

**Thesis:** Late-London EURUSD impulse with quiet GBPUSD implies GBP is the
lagged USD-factor leg; GBP catches up in EUR lead direction in early NY.

**Frozen:** EUR 11 or 12 body≥0.80·ATR + swing break; GBP same-bar body<0.40·ATR;
GBP fire 13–15 close beyond prior H1 extreme in lead dir; SL 1.0·ATR; RR=2;
1/day; no EURGBP; EXPIRE 15.

## Model 0 policy

Only if offline `PROBE_SURVIVOR`. Else withhold. No Real stall required.
