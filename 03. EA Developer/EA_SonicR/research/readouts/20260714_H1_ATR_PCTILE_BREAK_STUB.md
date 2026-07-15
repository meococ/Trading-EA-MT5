# Stub — HYP-H1-ATR-PCTILE-BREAK-001 (next auto)

Date: 2026-07-14 ~22:40 ICT  
State: **`idea / STUB_PREPARED`** — not prereg-frozen; no EA; no Model 0  
Authority: Successor after EQHL intake-kill + Wave4 offline board

## Thesis (draft)

Closed-H1 Donchian(20) break is taken **only** when ATR(14) percentile over
lookback 100 sits in **[40, 70]** — mid-vol regime. Avoids parked
`HYP-H1-ATR-REGIME-MOM` (elevated-vol mom) and killed LowVol Donchian **fade**.
A priori RR=2.5, MaxPerDay=2, Mon–Thu, weekend flat.

## Mandatory de-dup before freeze

| Family | Why must differ |
|---|---|
| `HYP-H1-ATR-REGIME-MOM-001` PARK | Elevated ATR ratio mom RR1.5 — this is mid-pctile gate + Donchian break |
| `HYP-H1-LOWVOL-DONCHIAN-MR-001` KILL | Low-vol fade / MR — opposite action + different vol gate |
| `HYP-H1-RV-COMPRESS-BREAK-001` KILL | RV compress coil — different vol object (range-RV ratio vs ATR%ile) |
| VolExp / Keltner / NR7 | M15 expansion / squeeze families — different TF/object |

## Next step when Owner continues

1. Written de-dup clearance → freeze prereg → closed-bar EA → offline probe
   cost x1/x1.5/x2 → Model 0 only if probe survives.
2. Parallel: if Real closed (`Get-Process terminal64`=0), run queued Model 0
   for IB-Overlap then GBPJPY-Lead first (already probe-survive).
