# Readout — HYP-ASIAN-TAIL-FADE-USDJPY-001

**Date:** 2026-07-14  
**Run:** `EA_M15AsianTailFade/20260714_195640`  
**Role:** Model 0 control | USDJPY M15 | 2021.01.01–2025.12.31 | Deposit 100000 | spread current  
**Contract receipt SHA256:** `EA03C72B7A263EFDCAD4CA4761D1028641D2048EB3177F227857E795431EA583`  
**Note:** Concurrent sibling started this run while VWAP closeout held context; report kept; `alpha.ps1 analyze -Report` used.

## Metrics (tester current)
| Metric | Value |
|--------|------:|
| Trades | 1079 |
| PF | 0.908 |
| Net | -5545.51 |
| tpw (N/261) | 4.13 |
| Max DD % | 8.90 |

## Verdict
**KILLED** — PF 0.908 < research bar; negative expectancy. No cost-stress (PF < 1.20).

## Ceremony receipt rebuild
Rebuilt contract receipt SHA256: `B28B0DA70400F3EE26E85DFFB5537F3C0F6981464DEA3DCD052AB755651C666C` (Model 0 artifacts reused; not re-tester while Owner Real terminal64 held).
