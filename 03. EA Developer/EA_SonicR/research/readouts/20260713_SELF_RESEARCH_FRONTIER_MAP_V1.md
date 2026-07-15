# Frontier Map — Self-Research Lane (no GPT) — 2026-07-13

Status: `LOCAL_EVIDENCE_ONLY / GPT_DEEP_RESEARCH_WAIVED / USBILL_OFFLINE_SURVIVOR_COST_BLOCKED`

## Owner instruction (binding)

Skip Browser → ChatGPT → GPT-5.6 Sol → Pro → Nghiên cứu sâu. Discovery authority
is workspace truth + offline probes only.

## Killed / closed families (do not revive)

| Surface | Evidence | Blocker |
|---|---|---|
| Price-only H4/D1 multi-pair | V7 coordinator audit | No legal candidate without exogenous state |
| Fix/benchmark / round-number / IPP proxy / tick-flow | V2–V6 + STRATEGY_LOG | Duplicate or causal mismatch |
| Public-rates carry weekly | `V8_CARRY_DIFF` result | Cadence 0.05/wk; sample fail |
| Public-rates carry daily rank | `V8_CARRY_DAILY_RANK` | Cadence 0.26/wk; sample fail |
| Public-rates carry rate-event ≥5bp | `V8_CARRY_RATE_EVENT` | Cadence 0.09/wk; sample fail |
| COT TFF spec-net change | `V8_COT_TFF_SPEC_NET_CHG` | Cadence OK (~1.95–2.16/wk) but loses control and/or year concentration 1.0 |
| COT TFF lev-money level H4 | `V8_COT_TFF_LEVMONEY_H4` | Cadence 2.51/wk; PF-A 1.019 < 1.10 (beats mom) |
| Carry×vol H4 regime | `V8_CARRY_VOL_REGIME` (see result JSON) | Cadence 2.71/wk; PF-A 0.947; negative expectancy |
| Cadence-book M15 hour-open | `HYP-CADENCE-BOOK-M15-001` Model 0 | Cadence OK (~3.18/wk); PF 0.94 |
| US−EU 10Y bond-diff EURUSD | `V8_USEU_10Y_DIFF_EURUSD_V1` | Cadence OK; PF-A 0.579 lose to mom |
| US−UK 10Y / EU curve slope | USUK + EU_CURVE results | PF-A 0.834 / 0.773 kill |
| OIS SOFR−€STR → EURUSD | `V8_OIS_SOFR_ESTR_DIFF_EURUSD_V1` | PF-A 1.003 < 1.05 (beats mom) |
| US−JP 10Y JGB → USDJPY | `V8_USJP_10Y_DIFF_USDJPY_V1` | PF-A 0.977 < 1.05 |
| Flow / equity-close / COMEX CFD proxies | S624/S625/S682/S683/S621 | Already dead in STRATEGY_LOG |

## Active offline survivor (cost-blocked)

| Surface | Evidence | Status |
|---|---|---|
| US bill-slope → USD basket | `V8_USBILL_SLOPE_USD_BASKET_V1` result SHA256 `BE93F528…3BA8EC` | **`PROBE_SURVIVOR`**; registry `probe`; prereg frozen; **no Model 0** until Real cost |

Stale concurrent notes claiming bill-slope KILL (year-conc 0.78 / 233 trades)
are superseded by the hash-bound result JSON above. Do not retune from either
narrative.

## Available lawful local data (on disk)

| Surface | Path | Probe status |
|---|---|---|
| G3 short rates (ECB/BoE/BoJ/Treasury/FRED) | `preflight/v8_exogenous/raw/`, `data/exogenous/` | Carry variants killed |
| CFTC TFF COT 2022–2025 | `preflight/v8_exogenous/raw/cot_tff_extracted/` | Spec-net + lev-money killed |
| US Treasury yield curve / bills | `exogenous_data/v8_public/rates/`, `v8_exogenous/raw/us_treasury_bill_rates_*.csv` | Bill-slope **offline survivor** |
| MT5 D1/H4 OHLC (Demo) | Terminal tick/history cache | Falsification only |
| FivePercentOnline-Real tick cache | Local monthly `.tkc` present | **Not** QFSI cost provenance; live probe still Demo≠Real |

## Unexplored / blocked sleeves

1. **Model 0 for USBILL survivor** — blocked on Real broker cost provenance.
2. **`HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001`** — idea remains
   `COST-DATA BLOCKED`; needs same Real QFSI bundles.
3. **Signed dealer flow / COMEX L1 / ALFRED vintages / true FX forwards /
   licensed equity closes** — still missing or incomplete. Non-US sovereign
   yields (UK BoE GLC + JP MoF JGB) are now on disk and probed/killed.

## Exact missing data

| Missing | Why it blocks GOAL |
|---|---|
| Target-broker QFSI capture manifests on FivePercentOnline-Real | True-cost Model 0 / promotion for USBILL + USD-factor |
| True FX forward points (vendor) | Overnight RFR proxies acquired+killed; forwards still missing |
| Licensed equity-index closes with session lag | Independent risk-on proxy |
| Lawful signed flow or futures L1 with sync rules | V7 primary-source families |

## Acquired this session (now probed/killed)

| Surface | Path | Probe status |
|---|---|---|
| SOFR−€STR / SOFR−SONIA RFR panels | `panels/us_eu_ois_rfr_diff_d1_v1.csv` (+ UK companion) | SOFR−€STR **KILL**; SONIA companion frozen not auto-probed |
| MoF JGB 10Y + US−JP panel | `panels/us_jp_bond_yield_diff_d1_v1.csv` | **KILL** `V8_USJP_10Y_DIFF_USDJPY_V1` |

## Next auto move (no GPT)

1. **Owner:** login `FivePercentOnline-Real` + authorize QFSI read-only cost
   capture (agents do not invent credentials).
2. After Real cost bundles exist: reopen Model 0 path for USBILL under frozen
   prereg (still no post-hoc z/tenor tune).
3. Do **not** auto-probe SOFR−SONIA as twin of killed SOFR−€STR without fresh
   independent mechanism. True FX forwards still missing if a lawful free
   archive appears.
4. Do not ChatGPT Deep Research unless Owner reverses the waiver.
5. Do not Model 0 `EA_CarryPublicRates` from killed carry probes.
