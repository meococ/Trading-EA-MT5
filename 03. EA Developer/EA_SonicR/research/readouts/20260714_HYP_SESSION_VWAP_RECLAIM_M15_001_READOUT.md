# Readout — HYP-SESSION-VWAP-RECLAIM-M15-001

**Date:** 2026-07-14  
**Run:** `EA_M15SessionVWAPReclaim/20260714_195418` (authoritative)  
**Twin:** `20260714_195550` — same metrics after re-bind + analyze; keep both.  
**Role:** Model 0 control | USDJPY M15 | 2021.01.01–2025.12.31 | Deposit 100000 | spread current  
**Contract receipt SHA256:** `C0CFE9B5F7DB556CD3C221E9C537EFB093D4028E4DCBA5B20C71D2B283990DAD`  
**Non-repaint:** closed-bar[1] PASS.  
**Note:** `includes_sha256` flake after report ready; artifacts kept; `alpha.ps1 analyze -Report` used.  
**Cost-stress:** `preflight/20260714_COSTSTRESS_SVR_195418.json` — x1.5 PF **0.690**.

## Metrics (tester current)
| Metric | Value |
|--------|------:|
| Trades | 1357 |
| PF | 0.900 |
| Net | -9391.24 |
| tpw (N/261) | 5.20 |
| Max DD % | 10.44 |
| Win rate | 38.4% |

## Verdict
**KILLED** — PF 0.90 < 1.00 kill floor; negative expectancy. Report-only x1.5 also FAIL (0.690). Do not densify / retune stretch/hour from this readout.

## Ceremony receipt rebuild
Rebuilt contract receipt SHA256: `AF91FF60B0A37C1A8D8F40B3D3FBD69D8F5E0B2A5CC49A45C3D418DC502E757A` (Model 0 artifacts reused; not re-tester while Owner Real terminal64 held).
