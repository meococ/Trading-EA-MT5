# Local Research Memo — Rates Surface Next Candidate

Date: 2026-07-13  
Status: `VERDICT_D / NO_LEGAL_CANDIDATE_ON_RATES_SURFACE`  
Authority: Owner override — skip ChatGPT; local self-research only (primary papers + workspace evidence).  
Scope: Point-in-time public G3 rates / short-rate differentials only.  
Not authority for: offline probe implementation, registry, prereg, EA, compile, Model 0.

## Binding inputs

| Artifact | Role |
|---|---|
| `readouts/20260713_V8_CARRY_DIFF_OFFLINE_PROBE_READOUT.md` | Weekly Friday long-max-if-positive **KILLED** (0.05 trades/week) — do not rescue |
| `readouts/20260713_V8_CARRY_DAILY_OFFLINE_PROBE_READOUT.md` | Daily long-max/short-min deadband 0.25 **KILLED** (0.261/week) |
| `readouts/20260713_V8_CARRY_RATE_EVENT_OFFLINE_PROBE_READOUT.md` | Rate-event ≥5 bp rebalance **KILLED** (0.092/week) |
| `readouts/20260713_V8_EXOGENOUS_LOCAL_DEDUP_BASELINE.md` | Pre-result family lock (B1 rates bucket ≠ pre-cleared candidate) |
| `preflight/v8_exogenous/` + `exogenous_data/v8_public/rates/` | Lawful rates panel on disk |
| `03. EA Developer/EA_CarryPublicRates/` | Engineering scaffold / compile SUCCESS only — **not** gate pass |
| `01. GOAL/GOAL.md` | North-Star: PF>1.30 after verified cost **and** 2–5 trades per elapsed calendar week |

## Research question

Is there **one** legal **independent** hypothesis that uses point-in-time public rates and is **not** the killed weekly cross-sectional carry-rank book?

---

## Literature anchors (primary, not ChatGPT)

1. **Menkhoff, Sarno, Schmeling, Schrimpf (Journal of Finance, 2012)** — *Carry Trades and Global Foreign Exchange Volatility*  
   Classic carry is a **monthly / low-frequency cross-section** sorted on interest differentials / forward premia. High-carry currencies underperform when global FX volatility innovations spike. The paper explains a **risk premium**, not a retail 2–5 trades/week scalp clock. Sampling the same slow differential on H1/M15 does not create new causal information.

2. **Faust, Rogers, Swanson, Wright (JEEA / Fed IFDP; NBER w9660)** — monetary-policy shocks via **Fed Funds futures surprises** in a narrow announcement window.  
   Identified FX responses require a **reconstructable expectation surface** (futures), not the mere step in the published policy/short-rate level. De-dup baseline B5 / V3 already closes calendar-only or surprise-less event momentum.

Implication for this workspace: the on-disk G3 policy / T-bill / overnight panel supports **level and lagged Δlevel** joins. It does **not** by itself supply a Faust-style surprise series. Treating every ≥5 bp money-market move as a “policy surprise” is a proxy mismatch.

---

## Candidate evaluations (honest kill table)

### A) Policy-rate CHANGE / differential JUMP — event continuation or fade

| Check | Result |
|---|---|
| Independent of weekly rank? | Mechanistically yes (event clock ≠ Friday rank) |
| Already tested locally? | **Yes.** `V8_CARRY_RATE_EVENT_5BP_V1`: same G3 lagged ≥5 bp calendar; long-max/short-min + deadband 0.25; train **24 trades / 0.092 per elapsed week**; `KILL_AT_OFFLINE_PROBE` (sample + cadence floors). Holdout gated shut. |
| Literature-true surprise? | **No** on current panel — needs futures-implied surprise (Faust et al.); de-dup B5 without that surface is fail-closed |
| H4 fixed-hold wrapper (`preregs/20260713_H_CARRY_RATE_CHANGE_EVENT_H4_V1_PROBE_FREEZE.md`)? | Same sparse **information clock**; converting events into overlapping H4 tickets is a timeframe/hold wrapper on the killed event family, not new causal state. Cadence “path” to ≥1.5 trades/week would be **ticket inflation**, not denser exogenous news. |
| Post-hoc threshold mining? | Forbidden (readouts explicitly ban bp/deadband mining from sparse PF) |

**Verdict A: KILL.** Either already falsified as event-rank, or illegal as surprise-proxy mismatch / H4 re-wrap of the same jump calendar. Do not open a fourth rates-event ceremony.

### B) Daily carry differential as FILTER only on an unrelated entry

| Check | Result |
|---|---|
| Independent book? | No — filter is not a stand-alone exogenous mechanism under North-Star |
| Resurrects killed Sonic filters? | Binding reject per Owner brief if attached to Classic/PVSRA/Dragon/Trend/ATR-impulse/session descendants (`20260712_NEW_STRATEGY_DEEP_RESEARCH_PACKET.md`) |
| De-dup risk | Rates garnish on closed price-only families (V7/V8 Section A) = `KILL_AT_INTAKE_DUPLICATE` / proxy mismatch |
| Daily rank already killed? | Yes — using the same differential as a soft gate after seeing daily PF is a rescue path |

**Verdict B: KILL (illegal).** Not a legal independent hypothesis.

### C) Higher-frequency (H1/M15) carry

| Check | Result |
|---|---|
| Mechanism timescale | Carry / policy / T-bill differentials are **slow** (Menkhoff monthly sorts; policy steps sparse; overnight series changes infrequently relative to M15) |
| What H1/M15 would actually do | Re-sample a near-constant state → artificial trade density without new rate information (timescale mismatch; analogous spirit to V6 latency reject) |
| Cadence honesty | Daily D1 already failed structural floor at **0.261**/week with max information use of the panel. Faster bars cannot invent rate innovations. |

**Verdict C: KILL.** Usually illegal; here specifically illegal as cadence theatre on a slow exogenous state.

### D) No legal candidate on the rates surface after the weekly kill

**Verdict D: SELECTED.**

Clarification (important): the **weekly kill alone** does **not** close the entire rates frontier. Independent frozen probes were still legitimate for daily rank and rate-event rebalance. Those were run and also died on **cadence/sample**, not on “weekly name conflict.”

What **does** close the **reconstructable public short-rate differential book** for North-Star is the **joint** evidence:

1. Weekly rank — sparse sleeve (GOAL non-goal: pretty PF, sub-2/week).  
2. Daily rank — denser but still **0.261**/week ≪ 2–5 and below structural probe floor.  
3. Event jump rebalance — **sparser** (0.092/week); high PF is the classic sparse-sleeve trap.  
4. Filter-only and H1/M15 re-sampling — illegal / timescale-invalid.  
5. True surprise continuation — **missing data surface** on the current rates panel (needs futures expectations), not a free B1 candidate.

`EA_CarryPublicRates` remains scaffold only.

---

## Frontier boundary (what weekly kill does / does not close)

| Surface | Closed by weekly kill alone? | Status after this memo |
|---|---|---|
| Friday cross-sectional public-rate rank book | Yes (that book) | Stay killed — no rescue |
| Daily cross-sectional / long-short deadband on same differentials | No | Separately killed offline |
| Rate-change event rebalance / jump continuation on lagged Δrates | No | Separately killed / H4 wrapper rejected |
| Carry as Sonic/price-family filter | No | Illegal de-dup / rescue — reject |
| H1/M15 sampling of same differentials | No | Timescale-illegal — reject |
| Faust-style **surprise** (futures) event FX | No | Outside current rates panel; needs new reconstructable series + de-dup B5 |
| Menkhoff carry×vol **risk** overlay as North-Star book | No | Not evaluated as a survivor here; vol gate **reduces** density and still depends on slow carry. Existing join contract is not a rates-frontier pass. |
| Other V8 exogenous buckets (COT/TFF, equity–bond differentials) | No | **Outside** this rates-surface verdict; may still be investigated under de-dup B3/B4 |

**Bottom line:** Weekly kill does **not** by itself end all rates research. After honest evaluation of A–C against the **already-run** daily/event kills, literature timescale, and missing surprise surface: there is **no remaining legal independent North-Star hypothesis on the point-in-time public rates panel**.

---

## If one candidate had survived (counterfactual — not claimed)

None survived. No exact rules / lag / kill-gate freeze is authorized for a next rates probe.

For audit completeness only, the three killed designs already froze:

| Item | Weekly | Daily | Rate-event |
|---|---|---|---|
| Lag | USD +1d; EUR +1d; GBP +1d; JPY +2d | same | same |
| Cost | Stress A 1.5 / B 3.0 pip RT | same | same |
| Split | Train 2018–2022; holdout 2023–2025 gated | same | same |
| Kill | trades&lt;80; cadence floor; no holdout peek | same | same |

Do not mint a fourth variant by editing deadband, bp threshold, or bar size.

---

## Coordinator return

| Field | Value |
|---|---|
| Memo path | `03. EA Developer/EA_SonicR/research/readouts/20260713_LOCAL_RESEARCH_RATES_NEXT_CANDIDATE_MEMO.md` |
| Verdict | **D — NO LEGAL CANDIDATE** on the public rates surface for North-Star |
| Why weekly kill ≠ full rates closure | Weekly only kills the Friday rank book; daily and event were independent tests |
| Why rates book frontier is still closed now | Triple offline kill + illegal filter/H1 paths + no reconstructable surprise series |
| Suggested next research surface (non-authorizing hint) | Leave rates books; consider de-dup B3 COT/TFF or B4 public equity/bond differentials under separate memos — not rates rescues |

---

## Footer — authority

No probe implementation authority, no registry append, no prereg freeze, no EA/build/compile/Model 0 authority until **coordinator merge** explicitly opens the next surface. This memo is local research intake only.
