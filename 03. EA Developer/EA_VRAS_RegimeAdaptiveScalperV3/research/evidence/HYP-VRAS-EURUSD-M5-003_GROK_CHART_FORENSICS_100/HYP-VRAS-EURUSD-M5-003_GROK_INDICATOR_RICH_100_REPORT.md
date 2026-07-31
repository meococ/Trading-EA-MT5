# HYP-VRAS-EURUSD-M5-003 — Grok indicator-rich forensics (100 images)

> Grok-authored synthesis. Corpus: the complete 93-trade Model-0 census plus seven explicitly non-economic COST_DISTANCE_REJECT diagnostics. This report does not authorize tuning, rerun, rescue, promotion, or live use.

## Owner summary (Vietnamese)

Tổng hợp forensics 100 chart (93 trade census + 7 reject diagnostic) xác nhận HYP-VRAS-EURUSD-M5-003 vẫn KILL và không đủ điều kiện promote. Coverage 20/20 batch: EndTurn success, 5/5 image mở, ID khớp một lần, entry-parity 9/9. Dân số 93 lệnh: PF 0.59, WR 34.4%, expectancy −$56.4/lệnh, cadence 0.45 lệnh/tuần (dưới 2–5), net −$5,243; chỉ max DD 5.67% đạt trần. Trend 83 / Range 10 đều âm; stop 55 lần (−$12.2k) lấn target 13 lần. Edge thực tế phụ thuộc path sau entry, không phải fingerprint gate riêng. ADX hysteresis code-consistent nhưng lag; cost-distance K=8 chặn 455 candidate (7 chart reject chỉ diagnostic). Không retune, không veto session/năm, không rescue hậu nghiệm.

## Full Grok report

# VRAS Indicator-Rich 100-Chart Forensic Synthesis

**Object:** HYP-VRAS-EURUSD-M5-003 / EA_VRAS_RegimeAdaptiveScalperV3  
**Run:** `20260722_103759` (EURUSD M5 Model 0, 2019.01.03–2022.12.31)  
**Source SHA256:** `EAFB0A5962E79D7543CA7039F3C4B8597644D591CBFD08C9B19BD93B19FCD3B7`  
**Authority:** Advisory chart synthesis only — terminal readout remains decisive  
**Verdict:** **TERMINAL KILL / PROMOTION-INELIGIBLE** (no post-hoc rescue)

---

## 1. Coverage gate (fail-closed)

| Check | Result |
|---|---|
| Runner summaries (20) | All `success=true`, `stop_reason=EndTurn`, `response_useful=true` |
| Batch analyses (20) | Each `coverage` 5/5 `images_opened`, `all_cases_reported=true`, `entry_parity_manifests_checked=5` |
| `image_opened` | True on all 100 cases |
| Case IDs | Exactly the 100 casebook IDs once, batches B01–B20 in casebook order |
| Trade vs reject | 93 TRADE census + 7 REJECTED_CANDIDATE diagnostics |
| Entry parity | Casebook `all_entry_parity_pass_9_of_9=true`; batches reconfirm PASS |

Coverage is **CLOSED**. Synthesis proceeds.

Anti-inflation rule (binding): the seven rejected candidates are **not trades** and never enter WR, PF, expectancy, cadence, or outcome frequencies. Economic sample size remains **n=93**.

---

## 2. Terminal population economics (authoritative frequencies)

From `HYP-VRAS-EURUSD-M5-003_READOUT.md` / lifecycle reconcile:

| Metric | Value | Frozen bar |
|---|---:|---|
| Trades | 93 | ≥350 |
| Trades / elapsed week | 0.4465 | 2–5 |
| Net profit | −$5,243.22 | >0 |
| Profit factor | 0.591354 | ≥1.30 diagnostic |
| Win rate | 34.4% | info |
| Expectancy | −$56.38 / trade | >0 |
| Avg realized R | −0.230972R | >0 |
| Max DD | 5.6684% | ≤6% (only pass) |

**Branch / direction (population):**

- Trend: 83 trades, 28 wins, PF 0.6412, net −$4,152.31  
- Range: 10 trades, 4 wins, PF 0.1331, net −$1,090.91  
- Long: 51, PF 0.5607, net −$3,153.00  
- Short: 42, PF 0.6302, net −$2,090.22  

**Exit anatomy (population):**

- 13 TARGET_LEVEL → +$4,962.74  
- 55 STOP_LEVEL → −$12,213.14  
- 25 safety/time (NON_LEVEL) → +$2,007.18  

**Funnel:** 2,546 attempts → 1,998 ENTRY_GUARD_REJECT + 455 COST_DISTANCE_REJECT + 93 accepted.  
**Regime switches:** 10,090 ≈ 6.92 / elapsed day (whipsaw red flag >4/day).  
**Activity window:** first trade 2019-01-03, last OPEN 2020-06-04; 31/48 months inactive; 2019 net −$441 (PF 0.84), 2020 net −$4,802 (PF 0.52).  
**Robustness:** 0/7 PASS; bootstrap PF 95% CI 0.352–0.930; MC 1000: P(below start)=100%, p95 DD 6.8% > 6% ceiling.

Only the drawdown ceiling passed. Sample size, cadence, PF, expectancy, robustness, equity audit, and cost truth all fail or block promotion.

---

## 3. EA behavioral identity (what it actually does)

### 3.1 Core design (prereg + logic matrix + source)

Closed-bar dual-branch scalper on EURUSD M5:

1. Rebuild session clock (London anchor, server→UTC DST) and session VWAP/SD (tick-volume Welford).  
2. Update ADX14 regime with **25 enter / 19 exit / 6-bar dwell**.  
3. Evaluate **exactly one** branch:  
   - **RANGE:** ±2SD location + RSI soft floor/ceiling (25/75); AVWAP/M15 dormant. Target = session VWAP.  
   - **TREND:** multi-VWAP stack (session + confirmed 5-bar AVWAP) + pullback/reclaim + M15 bias; target 1.80R.  
4. Guards (spread, news ±45m, daily loss 1.5%, account DD 6%, max 3 trades/day, warmup 15, SD≥0.30 ATR).  
5. **G11 cost-distance:** target pips ≥ 8 × estimated round-trip cost.  
6. Risk 0.25%, OrderCheck, market entry next bar; MaxHold 20 M5 bars; open trade plan frozen (regime flip does not retarget live SL/TP).

HYP-003 changes only OrderCheck boolean acceptance and identity/magic vs HYP-001/002 — **no threshold rescue surface**.

### 3.2 Regime state machine

Charts repeatedly show **label lag** consistent with G01:

- TREND while ADX ∈ (19,25): e.g. T003 (24.32), T009 (23.24), T093 (20.80), P102 (19.10).  
- RANGE while ADX >25: e.g. T002 (26.43), T013/T014 (~27–28), R04 (38.82).  

This is **not** a render bug. Instantaneous ADX is not a win/loss discriminator: strong-ADX stopouts and soft-ADX winners both appear. At population scale the machine still switches too often (6.92/day).

### 3.3 Entry selectivity

Extreme pre-trade filtration yields only 93 fills across four calendar years of elapsed time. Cost-distance alone rejects 455 candidates; entry guards reject 1,998. Accepted trades still lose money — selectivity did not buy positive expectancy; it bought **sample starvation**.

### 3.4 Risk / exit anatomy

- Stops realize ~−0.86R to −0.95R after commission (dominant mass).  
- Targets ~+1.5R to +1.7R when full continuation holds (rare).  
- NON_LEVEL exits monetize incomplete paths both positively (partial winners) and as near-stop scratches.  
- Chart loser archetypes: (1) zero-MFE reverse-to-stop, (2) MFE-without-target giveback, (3) failed range reversion / breakout through extreme, (4) sticky-hysteresis TREND on soft ADX reverse-spike.  
- Chart winner archetype: same decision-time stack as losers, **plus** post-entry continuity on the correct side of VWAP/AVWAP into target or strong partial.

### 3.5 Winner vs loser profiles

**Winners** need path continuity after entry — expanding favorable bias distances, price remaining beyond the mean stack, ADX often re-expanding after entry.  
**Losers** clear the same gates then reverse through ATR-scaled stops; many holds last minutes to ~30–40 minutes. Same-day opposite TREND legs both stopping illustrate path dependence under continuous labels (e.g. P68/P70, P122/P124, P134/P136, P116/P118).

### 3.6 Execution and cost

Assumed cost components + G11 dominate pre-trade economics. Cost truth is blocked (24.55% zero spreads). Strict TCA blocked. Even the observed negative PF cannot be promoted.

---

## 4. Indicator roles and trajectories

| Indicator | Role | Trajectory observation |
|---|---|---|
| Session VWAP | Primary mean surface | Winners stay trade-correct side; losers reverse through |
| Session SD | Range location ±2SD; context dispersion | Often >> ATR/stop; co-factor for full-R noise stops |
| Shadow VWAP | Tick-volume uncertainty arm | Parity field; not alternate live decision |
| Confirmed AVWAP | TREND confluence only | Live in TREND; zero in RANGE by contract |
| ADX14 + hysteresis | Regime root | Sticky labels lag; not standalone edge |
| RSI14 | RANGE soft gates; TREND telemetry | No TREND fingerprint separation |
| ATR14 | Stop/risk scaling | Thin stops vs wide SD days |
| M15 close vs M15 VWAP | TREND HTF bias | Necessary, not sufficient |

Continuous series after entry are **diagnostic and outcome-aware**; decision rights remain the closed-bar snapshot with 9/9 parity.

---

## 5. Rejected-candidate diagnostics (n=7, non-economic)

| ID | Event | Blocking gate | Note |
|---|---|---|---|
| R01 | TREND_LONG | COST_DISTANCE | Tight ~5.3p risk vs ~2.4p est cost |
| R02 | TREND_SHORT | COST_DISTANCE | Sub-4p risk; later path with short (non-economic) |
| R03 | RANGE_LONG | COST_DISTANCE | −2SD geometry; target << 8×cost |
| R04 | RANGE_SHORT | COST_DISTANCE | +2SD; ADX 38.8 with regime RANGE (hysteresis) |
| R05 | TREND_LONG | COST_DISTANCE | Global min cost/risk; fails K=8 by a hair at ~1.8R |
| R06 | TREND_SHORT | COST_DISTANCE | Global median; strong ADX still blocked |
| R07 | TREND_SHORT | COST_DISTANCE | Global max; est cost > risk and target |

All seven: entry-parity PASS; post-reject paths descriptive only; **excluded from all economic tallies**.

---

## 6. Ranked strengths (evidence-bound)

1. **Fidelity / engineering integrity** — parity, non-repaint, lifecycle reconcile.  
2. **Minority TREND continuation works as designed** when path holds to TARGET.  
3. **G11 blocks cost-dominated micro-geometries** (reject funnel).  
4. **DD ceiling and 0.25% risk prevented blow-up**.  
5. **MaxHold/non-level can salvage partial R** on incomplete favorable paths.

---

## 7. Ranked weaknesses (evidence-bound)

1. **Stop-frequency payoff dominance** (−$12.2k stops vs +$5.0k targets).  
2. **Gates necessary not sufficient** — shared entry fingerprint, path decides.  
3. **Regime whipsaw + hysteresis lag**.  
4. **RANGE branch weak** (PF 0.13 on 10 trades).  
5. **Cadence/sample starvation** and post-2020-06 silence.  
6. **SD>>stop residual envelope** as stop co-factor (inference).  
7. **MFE-without-target givebacks** under fixed SL/MaxHold.

---

## 8. Source and fidelity choke points

1. Cost provenance blocked (zero-spread rows; assumed commission/slippage).  
2. Aggregated ENTRY_GUARD counters — post-June-2020 guard mix not separable.  
3. Strict execution/TCA reconciliation blocked.  
4. Server-time vs parquet UTC clock risk (mitigated in these charts).  
5. Outcome-aware continuous series must not be abused for feature rescue.  
6. Tick-volume-only VWAP without second real-volume broker feed.

---

## 9. What cannot be concluded

- Post-hoc session/hour/day/year filters restoring edge.  
- Threshold retunes of ADX/K/RSI/stops on this killed object.  
- Counterfactual economics for rejects.  
- Promotion/live/delivery under blocked cost truth.  
- WFO for this object (n too small).  
- That *all* VWAP/AVWAP/regime strategies lack edge — only this exact object is killed.  
- Separable account-DD vs other guards after mid-2020.  
- True independent slippage distribution.  
- M15 path continuity as a validated production filter.

---

## 10. Legal next hypotheses (max 3; new IDs only)

1. **Continuation-conditioned TREND** — predeclared path-quality confirmation after reclaim; independent prereg; not HYP-003 threshold nudging.  
2. **Regime switch-budget redesign** — attack 6.92 switches/day with a new state machine contract.  
3. **Cost-true microstructure entry** — verified spread feed + separable guard telemetry; falsify if cost truth still blocked or economics still negative.

Each requires a **new hypothesis_id**, frozen PROBE_PLAN pre-outcome, and forbids amendment/rescue of HYP-VRAS-EURUSD-M5-003.

---

## 11. Terminal conclusion

The indicator-rich 100-chart review is **coverage-complete and fidelity-intact**. It **confirms** the terminal Model-0 readout mechanisms and **does not** rehabilitate economics.

**HYP-VRAS-EURUSD-M5-003 remains TERMINAL KILL and promotion-ineligible.**  
No threshold tuning, session/year veto, rerun, source edit, or post-hoc rescue is authorized.
