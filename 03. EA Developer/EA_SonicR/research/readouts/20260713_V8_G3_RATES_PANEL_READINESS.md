# V8 G3 Rates Panel Readiness — 2026-07-13 (night autonomy)

Status: `RATES_PANEL_MOSTLY_READY / LAG_CONTRACT_DRAFT / BLOCKED_BY_CHATGPT_AUTH / NO_PROBE / NO_EA`

## Purpose

Close the highest-leverage **legal** unblock under Owner 1A fail-closed after
V7 `NO_LEGAL_H4_D1_CANDIDATE`: finish a reconstructable public short-rate panel
for the V8 data-contract packet **without** submitting Deep Research, without
an offline strategy probe, and without EA compile.

## What changed this session

| Action | Result |
|---|---|
| Verified prior `v8_exogenous/raw` hashes vs manifests | All expected rate CSVs `HASH_OK` (ECB DFR, BoE Bank Rate, Treasury bills 2018–2025) |
| Parsed BoJ overnight call from official HTML mirror | `jpy_boj_uncollateralized_overnight_call_daily.csv` — 10,413 data rows; SHA256 `9e1d2a2e1ca1a9e16e86090d3ee2c8927a05f6660bbb0b3b849cd1b16aef4482` |
| Froze BoJ Basic Discount / Loan Rate effective-date steps | `jpy_boj_basic_discount_loan_rate_steps.csv` — 12 steps; SHA256 `9084f1f93907beb4adb9ac3939f8859921611210737697ed714dcb4416892e5e` |
| Drafted `available_at_utc` lag contract | `preflight/v8_exogenous/contracts/20260713_V8_RATES_AVAILABLE_AT_UTC_CONTRACT_V1.json` — `DRAFT_CONTRACT / NO_JOIN / NO_PROBE` |
| Machine readiness receipt | `preflight/v8_exogenous/manifests/20260713_V8_G3_RATES_PANEL_READINESS_V1.json` |

Script: `preflight/v8_data/complete_v8_rates_panel_v1.py`

## Local rates surface (V8 packet scope = rates only)

### Canonical acquisition tree — `preflight/v8_exogenous/raw/`

| File | Role |
|---|---|
| `ecb_dfr_daily.csv` | EUR policy / deposit facility daily level (ECB SDMX) |
| `boe_bank_rate.csv` | GBP Bank Rate daily export (IUDBEDR) |
| `us_treasury_bill_rates_2018.csv` … `_2025.csv` | USD bill rates (Treasury.gov) |
| `jpy_boj_uncollateralized_overnight_call_daily.csv` | JPY money-market call ON (BoJ) |
| `jpy_boj_basic_discount_loan_rate_steps.csv` | JPY sparse policy steps |

### FRED mirrors — `research/data/exogenous/`

Present and previously hash-bound: `DFF`, `SOFR`, `ECBDFR`, `ESTR`, `SONIA`,
monthly JPY call (`IRSTCI01JPM156N`). Monthly JPY is **inferior** to the new
daily BoJ call series for point-in-time H4/D1 joins.

## Integrity note (out of V8 packet)

Older acquisition manifest claimed `cot_tff_202{2-4}.zip` as `OK`, but those
binaries are **missing** under `v8_exogenous/raw`. V8 packet **forbids COT**.
Do not treat missing COT as a V8 rates blocker; do not invent COT joins.

## Still missing / soft gaps

1. ALFRED vintages not archived (revision risk on some FRED series).
2. Separate EFFR / DTB3 pulls not required if Deep Research accepts DFF/SOFR +
   Treasury bills with an explicit mapping table.
3. Same-broker QFSI cost provenance still `STOP_DATA_FRONTIER` (Demo ≠ Real).
4. No Deep Research V8 result yet — packet remains draft / not submitted.

## Authority boundary (unchanged)

This readiness work authorizes **only** continued lawful rates acquisition and
contract prep. It does **not** authorize:

- Browser Deep Research V8 submission (needs Owner confirm + UI readback);
- offline strategy probe / analyzer;
- registry row / frozen prereg;
- MQL5 EA / MetaEditor compile / Strategy Tester / Model 0.

## Exact Owner decision needed

Unlimited-GOAL authority already allows V8 submit. Remaining blocker is
**ChatGPT Browser login**. Restore an authenticated session, then resume submit
with UI readback of `GPT-5.6 Sol` + `Pro` + `+ → Nghiên cứu sâu`.

Attempt receipt:
`preflight/20260713_NEW_STRATEGY_DEEP_RESEARCH_SUBMISSION_V8.json`
(`BLOCKED_BY_BROWSER_AUTH`).

## Controlling status

`RATES_PANEL_MOSTLY_READY / BLOCKED_BY_CHATGPT_AUTH / NO_EA_BUILD`
