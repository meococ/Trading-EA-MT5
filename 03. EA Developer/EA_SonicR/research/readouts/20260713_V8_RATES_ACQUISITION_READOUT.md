# V8 Exogenous Rates Acquisition Readout — 2026-07-13

Status: `ACQUISITION_EXECUTED / NO_PROBE / NO_EA / NO_BACKTEST`

## Authority boundary

Owner autonomous mandate + V8 rates-only data-contract expansion allow
**lawful public short-rate acquisition and hashing only**. This readout does
**not** authorize Deep Research V8 ChatGPT submission, offline probe, registry
row, prereg freeze, EA source, MetaEditor compile, or Strategy Tester / Model 0.

Deep Research V8 remains `DRAFT / NOT SUBMITTED` until Owner confirms submit.

## What was acquired

### A. Official / key-free archives
(`03. EA Developer/EA_SonicR/research/preflight/v8_exogenous/`)

| Series | Path | Role |
|---|---|---|
| ECB Deposit Facility Rate (daily SDMX CSV) | `raw/ecb_dfr_daily.csv` | EUR policy / short-rate leg |
| US Treasury bill rates 2018–2026 | `raw/us_treasury_bill_rates_YYYY.csv` | USD money-market proxy covering V8 2018–2025 window |
| BoE Bank Rate history page snapshot | `raw/boe_bank_rate_page.html` | GBP policy event source (HTML; parser not frozen) |

Manifest V2 (authoritative for this acquisition wave):

`preflight/v8_exogenous/manifests/20260713_V8_EXOGENOUS_ACQUISITION_MANIFEST_V2.json`

`status=ACQUISITION_EXECUTED`, `errors=[]`, `files_ok=11`.

### B. Prior FRED mirrors already on disk
(`03. EA Developer/EA_SonicR/research/data/exogenous/`)

| Series | File |
|---|---|
| USD Fed Funds (DFF) | `us_fed_funds_DFF.csv` |
| EUR ECB deposit (ECBDFR) | `eur_ecb_deposit_ECBDFR.csv` |
| GBP SONIA (IUDSOIA) | `gbp_sonia_IUDSOIA.csv` |
| EUR €STR | `eur_estr_ECBESTRVOLWGTTRMDMNRT.csv` |
| USD SOFR | `us_sofr_SOFR.csv` |
| JPY call money monthly | `jpy_call_money_monthly_IRSTCI01JPM156N.csv` |

FRED receipt:

`preflight/v8_data/20260713_FRED_SERIES_MANIFEST_V1.json`

## Explicit non-claims

- No `available_at_utc` join keys are frozen.
- No carry differential formula is frozen.
- No offline probe was run.
- COT bulk files are **out of V8 packet scope** (positioning not authorized in
  the rates-only expansion). Earlier inventory ranked COT for a broader
  exogenous reopen; it is not part of this V8 rates wave.
- Broker QFSI cost provenance remains `DATA_NOT_READY` (Demo ≠ Real).
- Same-broker commission / side-referenced slippage still blocks meaningful
  Model 0 outcome runs even after a future probe survivor.

## Parallel Phase 0 identity draft (not clearance)

Built outcome-blind universe draft from `run_manifest.json` identity fields
only (UTF-8 BOM-safe; skipped `_` archive namespaces):

`preflight/20260713_PHASE0_UNIVERSE_IDENTITY_INVENTORY_DRAFT_V1.json`

- `member_count=225`
- `error_count=4`
- `draft_universe_sha256=b169f9a68f84956b7fba49ebe7f5415aa0547c047a5c8f20cc2430975734c326`
- `status=DRAFT_NOT_FROZEN`
- Does **not** rewrite Phase 0 sufficiency spec `candidate_runs`
- Does **not** clear `BLOCKED_REQUIRES_CLEAN_FUTURE_FREEZE_REVIEW`

Builder:

`analyzers/build_phase0_universe_identity_inventory_draft_v1.py`

## Next legal moves

1. **needs-owner**: confirm Browser submit of
   `20260713_NEW_STRATEGY_DEEP_RESEARCH_DATA_CONTRACT_V8.md` with UI readback
   `GPT-5.6 Sol` + `Pro` + `Nghiên cứu sâu`.
2. After V8 result + local audit: freeze point-in-time lag/join contract, then
   at most one cheap offline probe if a legal candidate survives de-dup.
3. Phase 0: Owner clean freeze review before any sufficiency-spec rewrite;
   SilverBullet A1 still needs the seven hash-bound contracts on a present donor.
4. QFSI: Owner re-login to `FivePercentOnline-Real` before execution-cost
   promotion evidence.
