<!--
Grok synthesis provenance:
- aggregate_request_sha256: C9608191BECBBCA63DC9994DBFC01FBA927CDD7D7799BFA94BDE219F2C7D2117
- aggregate_response_sha256: 1F57A6D0AE5862AF478A58B73CA2BCE82D7582A8914C394946BB57A1B37F38EA
- aggregate_summary_sha256: 03E667CDB5EC26B92CA9457560AE01353F752E5A985085B50C24996EEADBE109
- batch_qc_sha256: 8D728D21D931323D0C3F1BA87F0D38E576970F22CEAF7B9B5889F4688592D4C7
- coverage: 100 frozen random trades; 100 decision + 100 anatomy images
- batch04 transport note: one substantive Grok EndTurn response emitted the
  same schema-valid JSON twice; caller normalized one exact instance without
  editing content and hash-bound the source candidate.
-->

# HYP-SCC-MT5-REPLICATION-EURUSD-M5-004 — Final Random100 Visual Forensic Synthesis

> **TIMEBASE ERRATUM — 2026-07-25:** the original 200-image campaign is
> coverage-valid but not price-path-valid. MT5 lifecycle `event_time` came from
> broker-server `DEAL_TIME`; `prepare_hyp004_random100.py` relabeled those raw
> values as UTC, while `chart_case_render.py` read `time_utc`. Parent spot-check
> found median entry marker-to-bar distance 54 points on the old clock versus
> 0 points after correct server→UTC conversion (p90 180.2 versus 2.0 points).
> Therefore all Grok visual mechanism counts and path-shape claims below are
> **PROVISIONAL / NOT ACCEPTED AS VISUAL EVIDENCE** pending review of the
> corrected V2 casebook. Report/lifecycle economics, matched-pair validity and
> the terminal `KILL_VALID_MATCHED_PAIR_NO_POSITIVE_EXPECTANCY` verdict remain
> unchanged.

Lead Quant / GFI integrator readout. Image coverage is verified from batch QC artifacts (20 accepted batches opened 100 decision + 100 anatomy PNGs = 200). This integrator did **not** reopen the 200 images; synthesis reconciles numeric population truth, random100 metrics, case-review labels, source fidelity, and frozen gates.

---

## 1. Executive verdict

| Item | Value |
|---|---|
| Hypothesis | `HYP-SCC-MT5-REPLICATION-EURUSD-M5-004` |
| Active signal mode | **Challenger** `CHALLENGER_HOLD_RETEST` (`InpUseHoldRetest=true`) |
| Challenger run | `20260725_210811` |
| Matched control | `20260725_210715` `CONTROL_FIRST_CLOSE_BREAK` |
| Contract | EURUSD M5, Model 0, 2019-01-01..2022-12-31, micro-risk 0.01%, target 2.00R, max hold 24 M5 bars |
| Source SHA256 | `9C03F4CB913E18B6CF660E48E7ADBD86034B1352A80167C32CC238BA7F7817B3` |

**Validity (run pair + forensic sample):** `VALID_RANDOM100_VISUAL_FORENSIC_SAMPLE`  
**OBSERVED** — pair_analysis marks both arms `valid=true`; random100 casebook QC PASS; grok batch QC PASS with `unique_cases=100`, `decision_images_opened=100`, `anatomy_images_opened=100`, `errors=[]`.

**Economics:** `CONFIRMS_TERMINAL_KILL_NO_POSITIVE_EXPECTANCY`  
**OBSERVED** — challenger population PF 0.6913, mean realized R −0.2318, net −$587.30 (scale-diagnostic), cadence 1.251/week, gates 3/12. Random100 is slightly worse (PF 0.604, meanR −0.311, WR 28%, net −$305.60) but **directionally identical**. Terminal readout verdict `KILL_VALID_MATCHED_PAIR_NO_POSITIVE_EXPECTANCY` is confirmed, not softened.

**Three dominant failure mechanisms (ranked):**
1. **Tight microstructure stop failure** — HIGH — primary economic damage path.  
2. **No durable post-entry follow-through / timeout** — HIGH — second realized-path mass.  
3. **HOLD/RETEST fails as edge discriminator** — HIGH — hypothesis-level mechanism failure vs control.

**Hard boundary:** mechanism labels use outcome-disclosing anatomy images. They describe **realized paths**, not decision-time predictors, and **do not authorize** disabling buckets or same-ID threshold/ATR/retest/session/direction/year/stop/target/timeout tuning.

---

## 2. Evidence integrity

### Artifacts inspected

| Artifact | Integrity note |
|---|---|
| `random100_grok_batch_qc.json` | status PASS; 20 accepted batches; 100 unique cases; 200 images opened; cost ≈ $1.823; errors [] |
| `random100_grok_descriptive_stats.json` | coverage matches batch QC; interpretation_boundary present |
| `random100_grok_case_reviews.jsonl` | 100 rows; SHA in batch_qc outputs |
| `random100_sample_manifest.json` | seed 20260725; `Python random.Random(seed).sample(sorted(position_ids), 100)`; outcome-agnostic; no replacement |
| `random100_casebook_qc.json` | PASS; 100 decision PNGs + 100 anatomy PNGs |
| `pair_analysis.json` | control+challenger validity, economics, funnel, gates, verdict |
| `HYP-...-004_READOUT.md` | terminal kill preserved |
| `HYP-...-004_FROZEN_PREREG.md` | pre-outcome contract; promotion_eligible=false |
| `EA_SweepCascadeContinuation.mq5` | fidelity choke points mapped to functions/lines |

### Manifest / lifecycle / report reconciliation (**OBSERVED**)

- Challenger: 261 OPEN = 261 CLOSE; RunMeta bars 298,483; last close 2022.12.29; report trade count / net / PF reconciled.  
- Control: 1,112 OPEN = 1,112 CLOSE; same bars; reconciled.  
- History quality 100%; no stop-out / fatal termination on either arm.  
- Non-repaint: PASS (readout).  
- Costs: `UNVERIFIED_DIAGNOSTIC_ONLY` (zero-spread rows possible; independent slippage unavailable; news disabled matched).  
- Control had 4 risk-geometry rows recovered from decision telemetry; **challenger recovered 0** (cleaner R denominators).

### Sampling integrity (**OBSERVED**)

- Population = all unique challenger `position_id` (261).  
- Sample size 100, seed `20260725`, order preserved.  
- Sample metrics after selection match descriptive_stats and case_reviews aggregates.

### Visual-label QC challenges (**OBSERVED** contradictions vs numeric truth)

Lifecycle/report numbers are authority when anatomy prose disagrees:

1. **9 cases** labeled `IMMEDIATE_CONTINUATION_EXPANSION` but `outcome=LOSS` and `exit_class=SL_LIKE` with net_R ≈ −1.04..−1.21 (e.g. R100_001, R100_004, R100_011, R100_041, R100_061, R100_065, R100_066, R100_070, R100_083).  
2. Several of those anatomy texts narrate TP / “winning continuation” while **net_account is negative** (clear label/prose contamination). **Rejected as win narratives.**  
3. **7 cases** labeled `TIGHT_STOP_MICROSTRUCTURE_FAILURE` but finished **WIN** (including TP_LIKE). Label is a realized-path bucket with noise, not a pure loser class.  
4. Evidence-class mix: OBSERVED 64 / STRONG_INFERENCE 35 / HYPOTHESIS 1 — labels remain post-outcome descriptive.

**No derived analyzer result is promoted above lifecycle economics.** Sample being modestly worse than population is sampling variance, not a new edge story.

---

## 3. Population decomposition

### Challenger full population (N=261) — **OBSERVED** (`pair_analysis` + `challenger_trades.csv`)

| Metric | Value |
|---|---|
| Trades | 261 |
| Net (account, micro-risk) | −$587.30 |
| Profit factor | 0.6913 |
| Win rate | 31.42% (82W / 179L) |
| Mean trade $ | −$2.25 |
| Mean realized R | −0.2318 |
| Median realized R | −1.0806 |
| Avg win / avg loss $ | +$16.04 / −$10.63 |
| Avg win / avg loss R | +1.638 / −1.088 |
| **Breakeven WR (from mean R)** | **≈39.9%** |
| Cadence | 1.251 / elapsed week (208.57 weeks) |
| Max DD | 0.748% at 0.01% risk (scale artifact) |

**Exit geometry (numeric R thresholds used in readout: TP-like ≥1.5R, SL-like ≤−0.8R):**  
TP_LIKE 67 · SL_LIKE 167 · MID/other 27 (includes the 30 timeout closes counted in RunMeta).

**Payoff implication (**OBSERVED**):** realized WR 31.4% is ~8.5 pp below the ~39.9% breakeven implied by average win/loss R. Mean winner is **not** full +2R after costs (~+1.64R); mean loser is slightly worse than −1R (~−1.09R).

**Cost / stress (**OBSERVED**):** mean planned risk ≈ $9.76; commission is material vs that scale (readout ≈ −$1.23/trade). Fixed round-trip stress PF: 0.5pip 0.549 · 1.5pip 0.354 · 2.25pip 0.255 · 3pip 0.184 — cost deepens an already negative native result; cost is not the sole cause.

### Control comparison (**OBSERVED**)

| | Control | Challenger | Δ |
|---|---:|---:|---:|
| N | 1112 | 261 | −851 |
| PF | 0.6981 | 0.6913 | −0.0068 |
| Mean R | −0.2156 | −0.2318 | −0.0162 |
| WR | 34.08% | 31.42% | −2.66 pp |

Challenger **does not beat** control on PF or mean R. The HOLD/RETEST path only thins the trade set.

### Funnel (**OBSERVED**, RunMeta)

`1240 BREAK_ARMED → 875 HOLD_PASS → 284 ACCEPT_RETEST → 261 fills`  
Rejects: HOLD 364 · close-inside 330 · expire retest 245 · day boundary 16 · gap 1 · spread 11 · broker distance 4 · order check 7 · exposure 1.

### Calendar / direction buckets (**OBSERVED**, descriptive only — **not** rescue licenses)

**By year (challenger PF):** 2019 0.387 · 2020 0.781 · 2021 0.605 · 2022 1.148 — only 1/4 years PF>1 (gate fail).  
**By direction:** BUY n=133 PF 0.690 · SELL n=128 PF 0.693 — both lose.  
**Holding time:** mean hold ~41 min; wins ~54 min vs losses ~35 min; **80/179 losses close within 15 minutes**; 28 losses within 5 minutes.  
**Stop width (risk_points):** median 35; Q1≤25 meanR −0.611 WR 21.1%; Q3≥52 meanR −0.064 WR 37.3% — tight stops look worse in-sample; **this is not authorization to widen the ATR buffer on this ID**.  
**Hour / weekday:** activity concentrated hours 02–04 server; all populated hours/weekdays meanR ≤0 or near-zero with negative mass; **no post-hoc session mask**.

### Tail / concentration (**OBSERVED**)

Gross wins sum ≈ +$1,315; gross losses ≈ −$1,902; top-10 wins ≈ +$192 (~15% of gross win mass). No right-tail concentration rescues expectancy.

### Random100 vs population (**OBSERVED**)

| | Population 261 | Random100 |
|---|---:|---:|
| WR | 31.42% | 28% |
| PF | 0.691 | 0.604 |
| Mean R | −0.232 | −0.311 |
| Net $ | −587.3 | −305.6 |
| SL/TP/other mix | 167/67/27 | 66/23/11 |

Sample is a valid adverse draw of the same failing distribution — **confirms**, does not overturn, the kill.

---

## 4. Winner and loser anatomy

### Numeric winner/loser contrast — population (**OBSERVED**)

| Trait | Winners (82) | Losers (179) |
|---|---:|---:|
| Mean R | +1.638 | −1.088 |
| Mean hold (min) | ~54.3 | ~35.1 |
| Mean risk_pts | 45.0 | 42.2 |

Winners require **reaching near-target expansion** (67 TP-like ≥1.5R). Losers are dominated by **fast SL-like** paths; many die inside one to three M5 bars after fill.

### Random100 mechanism cross-tabs (**OBSERVED** counts; **STRONG INFERENCE** on economic weight; **not predictive**)

| Mechanism | n | W/L | meanR | sumR | net $ |
|---|---:|---:|---:|---:|---:|
| TIGHT_STOP_MICROSTRUCTURE_FAILURE | 43 | 7/36 | −0.679 | −29.20 | −287.68 |
| IMMEDIATE_CONTINUATION_EXPANSION | 21 | 12/9 | +0.608 | +12.76 | +124.28 |
| NO_FOLLOWTHROUGH_TIMEOUT | 21 | 6/15 | −0.272 | −5.72 | −55.33 |
| MIXED_OR_OTHER | 15 | 3/12 | −0.597 | −8.96 | −86.87 |

**Interpretation boundary:** ICE is the only net-positive *labeled* path bucket, but (a) it is only 21% of the sample, (b) 9 ICE rows are **numeric SL losses** with contaminated win prose, and (c) anatomy discloses outcomes — so ICE is **not** a decision-time filter and **cannot** be mined into a same-ID rule.

### Matched structural reading (**STRONG INFERENCE**)

- **Structural winner condition:** post-fill immediate directional expansion that reaches the 2R geometry before the complex-extreme stop is tagged.  
- **Structural loser condition:** compressed microstructure / two-way trade around the retest level with stop placed at three-bar complex extreme ± 0.25 ATR — noise tags stop.  
- **Timeout losers:** retest was “valid” under code rules but displacement never matures within 24 bars.  
- Apparent “winner traits” on decision-asof charts (impulse, range location) **do not cleanly separate** winners from losers once labels are challenged against net_R — H1 context remains mixed (**UNKNOWN** as discriminator).

---

## 5. Logic and fidelity choke points

Source: `03. EA Developer/EA_SweepCascadeContinuation/EA_SweepCascadeContinuation.mq5`  
Active mode: challenger HOLD/RETEST. Closed-bar gate: `OnTick` uses `CopyRates(...,1,6,...)` (lines 960–995).

### Choke A — First-close N=2 pivot BREAK is the only signal surface

- **File/function/lines:** `DetectBreak` L470–495; `ArmBreak` L530–553; `OnTick` L988–995.  
- **Artifact:** 1,240 break arms → only 261 fills after challenger filters; both arms still PF≈0.69.  
- **Mechanism:** entry universe is first confirmed close break per UTC day; no regime/displacement state beyond pivot cross.  
- **Confidence:** HIGH.  
- **Alt:** data/cost artifact — rejected as sole cause (native PF already <1; stress worse).

### Choke B — HOLD bar is a weak continuation proxy

- **File/function/lines:** `ResolveHold` L555–598 (outside-close check L575–586).  
- **Artifact:** 875 HOLD pass vs 364 REJECT_HOLD; still no expectancy lift.  
- **Mechanism:** one closed bar beyond break level is necessary under contract but insufficient for edge.  
- **Confidence:** HIGH.

### Choke C — First-passage RETEST accepts shallow touch with tight complex stop

- **File/function/lines:** `ResolveRetest` L600–678; complex extreme + stop L650–653; open L654–663.  
- **Stop:** `complex_extreme - direction * InpStopAtrBuffer * atr` with `InpStopAtrBuffer=0.25` (inputs L62–64).  
- **Artifact:** 284 accepts / 245 expires / 330 close-inside rejects; random100 TSMF 43/100 with meanR −0.68; pop 167 SL-like.  
- **Mechanism:** stop hugs three-bar extreme; microstructure routinely stops out before 2R can realize.  
- **Confidence:** HIGH.  
- **Alt:** “just widen buffer” — **illegal same-ID rescue**; would be a new invalidation-object hypothesis under a new ID only.

### Choke D — Fixed 2R target + 24-bar wall-clock timeout

- **File/function/lines:** target in `TryOpenTrade` L373–377 (`InpTargetR`); timeout `ManageOwnedPosition` L806–816 (`InpMaxHoldBars=24`).  
- **Artifact:** avg win R 1.64 < 2.0; 30 timeout closes; sample TIMEOUT_OR_OTHER 11.  
- **Mechanism:** incomplete capture of extension + forced flat on non-trending paths.  
- **Confidence:** HIGH for contribution; **not** a license to retune R:R or timeout on this ID.

### Choke E — Control path dormant under active mode

- **File/function/lines:** `ArmBreak` L548–552 branches to HOLD vs `ResolveControlBreak` L514–528.  
- **Dormant when challenger active:** immediate control break entry.  
- **Still relevant:** matched control run shows nearly identical negative expectancy — HOLD/RETEST is not the unique failure; it fails to **repair** the break-continuation idea.

### Choke F — Lifecycle risk binding (control-only residue)

- **File/function/lines:** `LogLifecycleDeal` L714–770 uses globals `g_initial_entry` / `g_initial_stop` / `g_planned_risk_account`.  
- **Artifact:** control recovered 4 zero-risk rows; challenger 0.  
- **Impact:** diagnostic R only; cannot change native PF/P/L or reverse the kill.  
- **Confidence:** MEDIUM as engineering smell; LOW as economic driver for HYP-004 challenger.

### Requirements dormant / bypassed by active signal mode

Active `InpUseHoldRetest=true` **bypasses** control-style immediate next-bar break entry. Session, weekday, ADX, volume, news, HTF, VWAP, FVG, score filters remain **contract-dormant** (prereg §3). No break-even / trail / partials. Promotion and cost verification remain blocked by design.

---

## 6. Case chart manifest

**Sampling rule (**OBSERVED**):** outcome-agnostic simple random sample without replacement of 100 position_ids from 261, seed `20260725`, draw order frozen in `random100_sample_manifest.json`.

**Chart data source:** AlphaFactory chart_case_render layers under  
`.../random100_forensics/decision_asof/` (`*_asof_h1.png`, outcome-blind decision set) and  
`.../random100_forensics/anatomy/` (`*_anatomy_h1.png`, outcome-disclosing path).  
Casebook QC: 100+100 PNGs, status PASS.  
Batch reviewers: 20 accepted batches opened **all** 100 decision + 100 anatomy images (batch_qc).

**Stratum:** single stratum `RANDOM100_OUTCOME_AGNOSTIC` (no winner/loser stratified draw).

**Coverage:** reviewed_cases=100; decision_images_opened_by_batches=100; anatomy_images_opened_by_batches=100; total=200.

### Compact case table (all 100)

`case_id | stratum | position_id | direction | entry | exit | net_R | context_reason | decision_chart | outcome_chart`

| case_id | stratum | position_id | direction | entry | exit | net_R | context_reason | decision_chart | outcome_chart |
|---|---|---:|---|---|---|---:|---|---|---|
| R100_001_PID000000268 | RANDOM100 | 268 | BUY | 2020-12-23 04:05 | 2020-12-23 04:21 | −1.140 | ICE label but SL loss — visual win text **rejected** | decision_asof/..._asof_h1.png | anatomy/..._anatomy_h1.png |
| R100_002_PID000000140 | RANDOM100 | 140 | SELL | 2020-03-10 03:15 | 2020-03-10 03:41 | −1.041 | TSMF / SL | same pattern | same pattern |
| R100_003_PID000000010 | RANDOM100 | 10 | BUY | 2019-02-01 02:30 | 2019-02-01 03:06 | −1.200 | TSMF / SL | … | … |
| R100_004_PID000000304 | RANDOM100 | 304 | SELL | 2021-03-11 03:30 | 2021-03-11 04:05 | −1.073 | ICE+SL mismatch | … | … |
| R100_005_PID000000476 | RANDOM100 | 476 | SELL | 2022-07-01 03:55 | 2022-07-01 05:55 | +0.950 | NFT timeout-like mid win | … | … |
| R100_006–R100_100 | RANDOM100 | (see `random100_grok_case_reviews.jsonl`) | BUY/SELL | (frozen times) | (frozen times) | (net_R) | mechanism∈{TSMF,ICE,NFT,MIXED}; exit∈{SL,TP,TIMEOUT} | `decision_asof/{case_id}_asof_h1.png` | `anatomy/{case_id}_anatomy_h1.png` |

Full per-row fields (direction, timestamps, net_R, exit_class, mechanism, evidence_class, net_account) are hash-bound in `random100_grok_case_reviews.jsonl` (100/100). Chart paths follow `{case_id}_asof_h1.png` / `{case_id}_anatomy_h1.png` for every ID R100_001…R100_100. No bars were reconstructed; charts are pre-rendered PNGs.

**Mechanism count check vs stats:** TSMF 43 · ICE 21 · NFT 21 · MIXED 15 = 100.

---

## 7. Conclusions and legal next work

### Evidence-backed failure causes (**OBSERVED** / **STRONG INFERENCE**)

1. **No positive expectancy** on the frozen EURUSD M5 SCC contract after a fully valid micro-risk matched pair.  
2. **Primary realized path:** tight complex-extreme stops absorb microstructure noise; SL-like exits dominate (167/261; 66/100 sample).  
3. **Secondary path:** accepted retests often lack durable displacement → timeout/mid exits.  
4. **Hypothesis-level failure:** HOLD→12-bar first-passage RETEST collapses cadence below gate (1.25 vs 2–5) and **does not** improve PF/meanR vs control.  
5. **Geometry:** WR shortfall vs payoff-implied breakeven (~31% vs ~40%) with avg win <2R after costs.

### Why some trades win (**OBSERVED**)

A minority catch immediate post-fill expansion to near-2R before the structure stop is tagged. That is **path luck under a negative system**, not a separable decision-time rule validated here. Visual ICE wins must be discounted wherever anatomy prose conflicts with negative net_R.

### Unknowns / invalidity boundaries (**UNKNOWN** / contract limits)

- True live spread/slippage distribution (cost_status unverified).  
- Decision-time chart features that **predict** expansion without outcome leakage — not established.  
- Whether a **different** structural surface works on EURUSD M5 — untested; requires new ID + cheap probe.  
- HYP-004 remains **scale-diagnostic child** of prior survival issues; promotion was never eligible.

### Terminal decision (preserved)

- **KILL** the exact SCC control/challenger mechanism on this frozen EURUSD M5 contract.  
- **`same_id_tuning_authorized = false`**.  
- No retest-bar, ATR-buffer, R:R, session, weekday, year, direction, stop, target, or timeout rescue from this outcome sample.

### Legal next work — zero to three fresh hypothesis ideas (new IDs only; falsifiable; no mined thresholds)

1. **Displacement-gated structure break (new ID):** require a predeclared multi-timeframe closed-bar displacement/state object *before* any entry attempt — not first-close N=2 break alone, and not an hour/year mask from HYP-004.  
2. **Invalidation-object redesign (new ID):** replace three-bar complex extreme ± fixed ATR buffer with a different structural invalidation definition (e.g., closed swing envelope / event-defined invalidation), preregistered without using this run’s stop-width quantiles as parameters.  
3. **Retest quality as first-class state (new ID):** redefine continuation acceptance around a pre-specified value-zone reclaim/reject process rather than first passage of the same break level within 12 bars.

These are **idea-level only**. Each needs de-dup against `do_not_repeat_failures.md`, cheap outcome-blind probe, and independent prereg before any Model 0 ceremony.

**Final line:** Random100 visual forensics are **valid** and **confirm** the terminal economic kill. No same-ID tuning is authorized.
