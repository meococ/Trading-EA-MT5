# Session Closeout — OIS/RFR + US−JP Non-US Yield Probes — 2026-07-13

Status: `BOTH_KILLED_AT_OFFLINE_PROBE / USBILL_STILL_COST_BLOCKED / NO_REGISTRY / NO_MODEL_0`

Authority: Owner mandate — self-research only; no GPT; no wait on Real login;
execute next legal exogenous panel with new lag/hash contract.

## What was executed

### 1) OIS / overnight RFR panel (true public proxy; not vendor forwards)

| Artifact | Path / hash |
|---|---|
| Acquisition | `preflight/v8_exogenous/acquire_v8_ois_rfr_panel_v1.py` |
| Manifest | `manifests/20260713_V8_OIS_RFR_PANEL_ACQUISITION_V1.json` |
| Lag contract | `contracts/20260713_V8_OIS_RFR_AVAILABLE_AT_UTC_CONTRACT_V1.json` SHA256 `CE21E7A0…BF28631` |
| Panel SOFR−€STR | `panels/us_eu_ois_rfr_diff_d1_v1.csv` **1674** days SHA256 `0EFEF0C0…496600` |
| Companion SOFR−SONIA | `panels/us_uk_ois_rfr_diff_d1_v1.csv` **2025** days (not probed this session) |
| De-dup | `readouts/20260713_OIS_SOFR_ESTR_VS_CARRY_DEDUP_CLEARANCE.md` = `INTAKE_CLEARED` |
| Probe | `V8_OIS_SOFR_ESTR_DIFF_EURUSD_V1` |

**Verdict:** `KILL_AT_OFFLINE_PROBE`

| Train | Trades | /week | PF-A | vs control |
|---|---:|---:|---:|---:|
| Candidate | 159 | 0.76 | **1.003** | beats 0.795 |
| Kill | | | `pf_stress_a<1.05` | holdout gated |

Result SHA256 `9B77DE7B…C66BDDB`. Beat momentum but failed absolute PF floor.
Do **not** retune z; do **not** auto-probe SOFR−SONIA as rescue.

### 2) Non-US yields — MoF JGB 10Y (new lag contract)

| Artifact | Path / hash |
|---|---|
| Raw | `raw/ois_rfr/mof_jgb_historical.csv` (cp932 Japanese-era dates) |
| Lag contract | `contracts/20260713_V8_USJP_BOND_YIELD_AVAILABLE_AT_UTC_CONTRACT_V1.json` SHA256 `0C911404…7FEAAD` |
| Panel US−JP 10Y | `panels/us_jp_bond_yield_diff_d1_v1.csv` **1992** days SHA256 `3FD76068…E04625` |
| De-dup | `readouts/20260713_USJP_10Y_VS_USEU_USUK_DEDUP_CLEARANCE.md` = `INTAKE_CLEARED` |
| Probe | `V8_USJP_10Y_DIFF_USDJPY_V1` |

**Verdict:** `KILL_AT_OFFLINE_PROBE`

| Train | Trades | /week | PF-A | vs control |
|---|---:|---:|---:|---:|
| Candidate | 215 | 1.03 | **0.977** | beats 0.927 |
| Kill | | | `pf_stress_a<1.05` | holdout gated |

Result SHA256 `F4DDA767…56DA13D`. Cadence OK; edge fails. Not a USEU/USUK retune.

## Registry / prereg / Model 0

**None minted.** Working IDs stay unregistered.

## USBILL / QFSI (unchanged blocker)

`HYP-SR-FX-USBILL-SLOPE-USD-BASKET-001` remains sole offline `PROBE_SURVIVOR`.
**Model 0 still blocked** by `COST_PROVENANCE_GAP` — needs Owner login
`FivePercentOnline-Real` + QFSI capture. Agents cannot invent credentials.
Cadence ~1/wk still below North-Star 2–5.

## GOAL distance

Still **far from GOAL**: no book with verified-cost PF>1.30 and 2–5/week.
Public overnight RFR + sovereign yield differentials (US−EU, US−UK, US−JP,
EU slope, SOFR−€STR) are now empirically dead under the frozen z-gate
template. Remaining Owner-independent surfaces are thin (true FX forwards
vendor, licensed equities, signed flow). Primary unlock is Real cost for
USBILL Model 0 — still insufficient alone for North-Star cadence.

## Explicit non-rescues

- No z/tenor/session mining on OIS or USJP.
- No SOFR−SONIA probe as post-hoc twin of killed SOFR−€STR.
- No reopen of carry / COT / equity-bond / cadence-book / USBILL z-retune.
- No GPT Deep Research (Owner waived).

## Next

1. **Owner:** login `FivePercentOnline-Real` + authorize QFSI (USBILL Model 0).
2. Optional new independent surface only if lawful free archive appears
   (true forward points) or price-M15 **new** hypothesis ID (not cadence-book
   rescue).
3. Companion SOFR−SONIA panel frozen on disk but **not authorized** as automatic
   next probe without fresh de-dup + Owner/coordinator decision (risk of
   correlated kill to SOFR−€STR).
