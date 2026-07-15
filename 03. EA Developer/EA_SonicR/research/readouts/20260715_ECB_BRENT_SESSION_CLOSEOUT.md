# Session closeout — ECB BS + Brent importer ToT

Date: 2026-07-15  
Status: `OFFLINE_ALL_KILL / NO_MODEL0`  
Lane: single checkout; no-Git

## Acquisition

FRED `ECBASSETSW` (lag +5d) + `DCOILBRENTEU` (lag +1d).  
JPNASSETS monthly kept **RAW_ONLY** (too coarse; not probed).  
Manifest: `v8_exogenous/manifests/20260715_ECB_BRENT_ACQUISITION_V1.json`

## Probes

| ID | Verdict |
|---|---|
| `HYP-EURUSD-H1-ECB-BS-EXPAND-DISPLACE-001` | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-EURUSD-H1-ECB-BS-CONTRACT-DISPLACE-001` | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-EURUSD-H1-BRENT-IMPORTER-TOT-001` | **KILLED_AT_OFFLINE_PROBE** |

Receipt: `3A0DA01E6F71EFCA298FE9073F5827B27C0F870F2BE9DDF07ECD93B13099289C`  
Artifacts: `preflight/20260715_ECB_BRENT_OFFLINE_PROBES.json`

## Model 0

Withheld (no PROBE_SURVIVOR).

## Next autonomous EV

1. Do **not** densify ECB wow sign / Brent z / displace ATR/RR.
2. Keep Real QFSI accumulate for cost frontier (still GAP).
3. Next object outside Wave1–9 / dichotomy / COT / WTI / WALCL / PD-MMF-6J /
   PD-primary / ECB-Brent killboard — or Owner PIT/vendor surface.

Best shelf unchanged: RR2 `20260714_194548`. Phase-0 still BLOCKED. GOAL unmet.
