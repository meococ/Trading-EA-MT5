# CLEAN BOOK — Model 0 sleeve authority vs offline +$12 stress

Date: 2026-07-15 ~18:35 ICT  
Hypothesis: `HYP-BOOK-CLEAN-APRIORI-RR2SPARK-001`  
Status: `SLEEVE_MODEL0_AUTHORITY_BOUND__BOOK_STILL_GOAL_SCREEN_FAIL__NOT_CONFIRMED`  
Authority: Owner continue-R&D after W27 ALL_KILL — highest remaining autonomous EV  
Nested: lead self-merge (no densify)

## Contract (frozen a priori; unchanged)

| Item | Binding |
|---|---|
| Freeze memo | `readouts/20260715_CLEAN_BOOK_APRIORI_UNIVERSE_FREEZE.md` |
| Freeze SHA256 | `F18FAB12ECCBD3FF09A4FA03317AB13A59DFCAE00BA9491B640D69D2B728931C` |
| Offline stress JSON | `preflight/20260715_CLEAN_BOOK_APRIORI_RR2SPARK_STRESS.json` |
| Stress JSON SHA256 | `5F41A94BCFC9185C6771E60616FE5A7855C770D795B28AFCC2C2AB36C4DBB28B` |
| PRIMARY | RR2 `20260714_194548` ∪ Spark `20260714_193358` |
| EXTENDED | PRIMARY ∪ ITSM `20260714_003920` (diagnostic only here) |
| Caps | +$12 haircut; weekly corr≤0.35; same-M15 overlap≤0.05; heat=1; A>B>C |

## Model 0 authority decision

**No new AlphaFactory Model 0 burn.** Sleeve Model 0 authority runs already exist under the frozen overrides / shelf IDs:

| Sleeve | hyp_id (book map) | run_id | Model | Role | Overrides | Cost label |
|---|---|---|---:|---|---|---|
| A_RR2 | `HYP-SB-MAXKZ2-RR2-FRICTION-001` | `20260714_194548` | **0** | challenger | `InpFridayFlatHour=21;InpFridayFlatMinute=45;InpMaxTradesPerKZ=2;InpRiskPct=0.5;InpTP_RR_LDN=2.0;InpTP_RR_NY=2.0;InpUseWeekendFlat=1` | `UNVERIFIED_TESTER_CURRENT_SPREAD` (spread=`current`; deposit=100000) |
| B_SPARK | shelf `193358` (mapped in freeze to `HYP-SPARK-CAPACITY-3PD-001`; run manifest hyp=`HYP-SB-SPARK-BOOK-001`) | `20260714_193358` | **0** | control | *(empty — EA defaults; MaxPerDay=2 shelf)* | `UNVERIFIED_TESTER_CURRENT_SPREAD` |

Re-running identical Model 0 configs would only mint duplicate run_ids. Binding here = authority under the clean-book contract, not new evidence creation.

### Artifact hashes (authority)

| Artifact | SHA256 |
|---|---|
| RR2 `run_manifest.json` | `8332E91360DE469C2C5DB180387A34461D9ED3BEECA38EDBB4F534583F466C23` |
| RR2 `report.html` | `49D142CF2B9531AD2F9C338277FD30B00EC74F420B23A7E288687443723397E3` |
| Spark `run_manifest.json` | `21DF7AA410B4FF8A208FD0804C2B051B717033AB429AEAB003F96F8CFABDFF14` |
| Spark `report.html` | `8E655DB0E5537F99CEB9ED7560D472FC8F45E6D862F5495A0B965D82BBDE9357` |

## Honest cost labels (do not invent)

| Label | Meaning | Binding for GOAL? |
|---|---|---|
| `tester_raw` / Model 0 report PF | Tester PnL with `spread=current` (Demo/tester path). Missing commission/slip fields ≠ 0. | **No** — diagnostic only |
| `apriori_+12` | Frozen research screen: subtract $12 RT from every closed trade before pool/PF | **Yes** — research kill/survive screen |
| `real_qfsi_partial_p50` | FivePercentOnline-Real **partial** unit P50 ≈ $2.62/trade (USDJPY) from cost-ladder diagnostic | **No** — DIAGNOSTIC only; freeze still GAP (deals~11; quote-days≪90; slip MISSING≠0) |
| Demo | Same as tester `current` until a verified Demo-account cost freeze exists | **No** — not a QFSI freeze |

Cost freeze remains **GAP**. Do not claim broker-verified cost.

## Sleeve Model 0 (tester raw) vs offline haircut

| Sleeve | N | Model 0 PF (tester raw) | PF @$12 (offline haircut) | tpw | Model 0 net | Net @$12 |
|---|---:|---:|---:|---:|---:|---:|
| A_RR2 `194548` | 524 | **1.378** | **1.120** | 2.010 | 9828.35 | 3540.35 |
| B_SPARK `193358` | 325 | **1.380** | **1.207** | 1.247 | 9350.59 | 5450.59 |

Notes:
- RR2 alone hits research bar under tester (PF>1.30 ∧ tpw∈[2,5]) but **fails** GOAL cost-stress under +$12×1.5 (PF≈1.013) — already parked.
- Spark alone is cadence-thin (tpw≈1.25) under elapsed weeks — book role is cadence complement, not solo GOAL sleeve.

## PRIMARY book: offline stress (binding) vs Model 0 raw pool (diagnostic)

| Metric | Offline PRIMARY (heat +$12) | Model 0 raw pool (no haircut; diagnostic) | RealP50 pool (diagnostic) |
|---|---:|---:|---:|
| N after heat | 845 (drop 4) | 845-equivalent raw trades before haircut | same trade set |
| Pooled PF | **1.184** | **1.409** (tester_only ladder) | **~1.356** |
| Pooled tpw | **3.241** | 3.241 | 3.241 |
| Caps (corr/overlap) | PASS (corr≈0.031; overlap=0) | n/a (caps measured on haircut path) | n/a |
| GOAL screen PF>1.30 @$12 | **FAIL** | not applicable (raw ≠ screen) | not applicable |

Source for ladder rows: `preflight/20260715_COST_LADDER_DIAGNOSTIC_RR2_CLEANBOOK.json` / `.md`  
(RealP50 ≈1.36 is **DIAGNOSTIC** only — do **not** promote to GOAL.)

### Pair caps (offline; unchanged)

| Pair | weekly corr | overlap frac |
|---|---:|---:|
| A_RR2 × B_SPARK | 0.0307 | 0.0000 |

## Book-level Model 0

**Still WITHHELD as a portfolio EA challenger.** No coded dual-instance / portfolio EA exists. Binding sleeve Model 0 ≠ book Model 0. Offline pool remains probe/diagnostic under the freeze.

## Verdict

| Layer | Verdict |
|---|---|
| Sleeve Model 0 authority | **BOUND** to freeze — reuse `194548` + `193358`; no re-burn |
| Offline PRIMARY @$12 | `DIAGNOSTIC_PARTIAL__CAPS_OK__GOAL_SCREEN_FAIL` (PF=1.184 < 1.30) |
| RealP50 diagnostic | ~1.36 PF — **not** GOAL / not confirmed |
| Phase-0 | Still **CONTAMINATED** — not cleared |
| Confirmed / GOAL | **FAIL / unmet** |

## Explicit non-claims / non-actions

- Not GOAL. Not confirmed. Not portfolio-sleeve.
- Not Phase-0 clearance.
- Not densify RR / MaxKZ / Spark MaxPerDay / FVG / exit / exo / W1–W27 / R-series.
- Not invent cost from missing fields or thin Real sample.
- Not promote RealP50 diagnostic over a priori +$12 screen.

## Next legal actions (autonomous / Owner)

1. Keep QFSI alive until cost freeze has real deals + quote-days (Owner export optional).
2. Owner ChatGPT login → failure-packet Deep Research (parallel only).
3. Next independent discovery surface **outside** dollar-TWI / credit-MOVE / commodity ToT / quality-gate densify / W1–W27 / R-series.
4. Do **not** densify clean-book sleeves to chase PF@$12≥1.30.
