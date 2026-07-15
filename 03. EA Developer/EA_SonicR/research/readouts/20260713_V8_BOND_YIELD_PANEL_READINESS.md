# V8 Bond-Yield Differential Panel Readiness — 2026-07-13

Status: `PANEL_FROZEN / LAG_CONTRACT_FROZEN / PROBE_KILLED / NO_EA / NO_MODEL_0`

## Purpose

Execute the Owner-authorized **data-state change** after the V8 autonomous
self-research fail-closed (five prior offline kills). Acquire and freeze a
lawful public **US–EU sovereign bond-yield differential** panel with an
explicit `available_at_utc` lag contract, then run one de-dup-clear offline
probe. QFSI Real remains a separate Owner broker-login action and did not
block this public-panel work.

## What was acquired

| Artifact | Source | Role |
|---|---|---|
| `raw/bond_yields/us_treasury_yield_curve_2018.csv` … `_2026.csv` | Treasury.gov daily par yield curve CSV (key-free) | USD 10Y leg |
| `raw/bond_yields/ecb_yc_aaa_gov_sr_10y.csv` | ECB SDMX `YC/.../SR_10Y` | EUR AAA gov spot 10Y |
| `raw/bond_yields/ecb_yc_aaa_gov_sr_2y.csv` | ECB SDMX `YC/.../SR_2Y` | EUR curve companion (2Y) |
| `panels/us_eu_bond_yield_diff_d1_v1.csv` | Joined intersection | Frozen research panel |

Panel stats:

- Joined observation days: **2098**
- Panel SHA256: `27D4BE9BAEBDE5062813D98869C886DC2E0E0CDA5E8B6967D723085308E7D18D`
- Acquisition manifest:
  `preflight/v8_exogenous/manifests/20260713_V8_BOND_YIELD_PANEL_ACQUISITION_V1.json`
- Lag contract:
  `preflight/v8_exogenous/contracts/20260713_V8_BOND_YIELD_AVAILABLE_AT_UTC_CONTRACT_V1.json`
  (SHA256 `15D8636BC2EAB33D77B9375BCA31329D7140E4C9ECC962B7640B523517C37987`)

## Lag / `available_at` contract (frozen)

- `available_at_utc = observation_date + 1 calendar day 00:00Z` (conservative).
- FX closed bar may use a row only if `bar_close_utc >= available_at_utc`.
- Fail closed if gap from last available observation > 3 calendar days.
- No silent forward-fill across missing US/EU intersection days.

## Explicit non-claims

- Not true FX forwards / OIS (still vendor-heavy).
- Not UK gilt / JGB histories (BoE CSV export returned HTML; not frozen).
- Not equity-index closes (Stooq JS-blocked this session; FRED needs API key).
- Not QFSI Real cost provenance (`FivePercentOnline-Real` still Owner login).

## Probe executed on this panel

| Probe ID | Verdict | Train |
|---|---|---|
| `V8_USEU_10Y_DIFF_EURUSD_V1` | `KILL_AT_OFFLINE_PROBE` | 224 trades / **1.07**/week; PF stress-A **0.579**; lost to momentum control (PF-A 0.834) |

Result:
`preflight/v8_probe/20260713_V8_USEU_10Y_DIFF_EURUSD_PROBE_RESULT_V1.json`

Readout:
`readouts/20260713_V8_USEU_10Y_DIFF_EURUSD_OFFLINE_PROBE_READOUT.md`

Do **not** retune z-threshold / tenor / sleeve from the kill.

## Authority boundary

Panel freeze + one offline probe completed. **No** registry row, frozen
prereg, MQL5 build, MetaEditor compile, or AlphaFactory Model 0.

## Next legal reopen

1. Another **genuinely new** exogenous surface with lag contract (e.g. true
   forwards/OIS if a lawful free archive appears; UK/JP yields if official CSV
   works; equity panel only after license-clean download); or
2. Owner QFSI login to `FivePercentOnline-Real` for cost provenance (necessary
   later, insufficient alone to create a survivor).

USBILL-slope probe remains optional and separately de-dup-gated vs
`HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001`; this bond-diff kill does not
authorize retuning that book either.
