# HYP-G10-XMOM-W1-002 train forensics

## 1. Executive verdict

- **Run identity [OBSERVED]:** `G10XMOM002-TRAIN-EVAL-001`, challenger = prior completed W1 cross-sectional spot momentum; control = the same four selected legs with all directions flipped.
- **Validity [OBSERVED]:** engineering-valid and sample-valid for the frozen 2018-2021 W1 research proxy. Holdout remained sealed.
- **Economic verdict [OBSERVED]:** killed. Challenger PF x1 `0.814`, net `-0.7334`, expectancy `-0.000886`; reverse control PF `0.902`, net `-0.3671`.
- **Failure 1 — signal sign/decay [HIGH, INFERENCE]:** both long and short selections lost, six of seven symbols lost, and the challenger underperformed its matched reverse-direction control. The exact one-week ranking has no positive train expectancy under this execution identity.
- **Failure 2 — cost-amplified negative edge [HIGH, OBSERVED]:** gross PF `0.950` fell to net PF `0.814`; mean cost drag was `0.000664` per leg. Costs worsen the result but do not alone explain a challenger that also loses relative to control.
- **Failure 3 — broad temporal/tail instability [HIGH, OBSERVED]:** 0/4 positive years, 1/8 positive half-years, and MC P95 DD `11.95%` versus the frozen 8% ceiling.

## 2. Evidence integrity

- **[OBSERVED]** Input hashes were verified before reading: legs `CF105E71DB25`, weeks `6E282704964D`, terminal `F115DFB58BE4`, parquet `2FB4615129D8`, sampling plan `A5014B6EDA61`.
- **[OBSERVED]** Terminal, dataset manifest/parquet, prereg, evaluator, tests and independent review are SHA-bound in registry terminal row 344. Evaluator is disarmed after one use.
- **[OBSERVED]** A four-image Grok ACP review passed structured-output validation, cost USD 0.0698892, accessed no holdout, changed no files, and returned `SUPPORTS_KILL`; receipt SHA `D02B296C3E69`.
- **[LIMIT]** This is an offline W1 research proxy, not an MT5 Strategy Tester report. Cost is a frozen pip proxy; account-currency PnL, real lifecycle fills, spread path, news coverage and execution telemetry are unavailable.
- **[OBSERVED]** Source logic rejects non-train years and holdout access (`evaluate_g10_xmom_002_train.py:267-278`), ranks/selects at `407-437`, constructs legs at `598-780`, and summarizes/gates at `823-1005`.
- **[INFERENCE]** Non-repaint risk is low for this proxy because formation uses only the prior completed W1 bar; no MQL5/tick implementation exists to audit.

## 3. Population decomposition

| arm | legs | win rate | PF gross | PF net x1 | net | expectancy | avg win | avg loss | BE win rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| challenger | 828 | 47.10% | 0.950 | 0.814 | -0.7334 | -0.000886 | 0.008227 | -0.008999 | 52.24% |
| reverse control | 828 | 47.34% | 1.053 | 0.902 | -0.3671 | -0.000443 | 0.008651 | -0.008620 | 49.91% |

- **[OBSERVED]** Cadence is `3.967` legs per elapsed calendar week; sample is 207 complete weeks / 828 legs per arm.
- **[OBSERVED]** Bottom 5% of challenger legs contribute `30.2%` of total gross loss magnitude; this is material tail concentration but does not legalize deleting those outcomes.
- **[UNKNOWN]** Account-currency PnL, true R, session/hour, holding-time variation, stop width, volatility, news and execution buckets are not present in this W1 proxy.
- **[OBSERVED]** Full year/month/symbol/side/formation-quintile tables are in `population_summary.json`; no bucket is a same-sample filter recommendation.

## 4. Winner and loser anatomy

- **[OBSERVED]** Winners and losers are sampled by the frozen plan, including extremes, medians and the nearest same-symbol/same-side contrast.
- **[INFERENCE]** With only one formation bar plus one outcome bar, apparent winner traits cannot be separated reliably from random weekly continuation/reversal. Matching controls symbol, side and calendar distance only; it does not control macro news or intrabar volatility.
- **[OBSERVED]** Winners occur when the selected currency continues in the directed pair over the next W1 bar by more than the cost proxy; this is outcome anatomy, not causal proof.

## 5. Logic and fidelity choke points

- **[OBSERVED, HIGH]** `rank_currencies`/`select_basket` (`407-437`) impose the exact top2/bottom2 decision surface; broad losses on both sides connect directly to a weak/decayed one-week continuation premise. Alternative: W1 open/close proxy may misrepresent implementable weekly timing.
- **[OBSERVED, HIGH]** `cost_return` (`374-396`) applies the frozen spread-floor + commission + slippage + rollover proxy. It materially lowers PF. Alternative: real broker costs may differ, but x1 already fails before any promotion claim.
- **[OBSERVED, MEDIUM]** `evaluate_train_bars` (`598-780`) forces Monday-open/Friday-close, all-or-none four-leg baskets. It removes timing flexibility and may blend reversal/continuation subregimes. Testing a mined clock/filter on this sample is prohibited.
- **[DORMANT]** Stops, targets, trailing exits, intraday sessions, news gates, portfolio margin, order filling and MQL5 execution are absent—not merely bypassed—because no EA/Model 0 was built after the probe kill.

## 6. Case chart manifest

Sampling was frozen in `HYP-G10-XMOM-W1-002_TRAIN_FORENSIC_SAMPLING_PLAN.md` before individual outcomes were read. Decision charts use only the prior W1 OHLC; outcome charts add the current W1 OHLC and frozen open/close markers. Intrabar path is unavailable.

| case_id | stratum | position_id | direction | entry | exit | net_R | context_reason | decision_chart | outcome_chart |
|---|---|---|---|---:|---:|---:|---|---|---|
| G10XMOM002-C01 | largest_loss | CH-2020-03-22-GBPUSD-short | short / pair_direction=-1 | 1.167450 | 1.247440 | unknown | predeclared largest_loss; formation=-0.067640; rank=6 | `03. EA Developer/EA_G10WeeklyXSMomentum/research/evidence/HYP-G10-XMOM-W1-002/G10XMOM002-TRAIN-EVAL-001/forensics/cases/G10XMOM002-C01_decision.png` | `03. EA Developer/EA_G10WeeklyXSMomentum/research/evidence/HYP-G10-XMOM-W1-002/G10XMOM002-TRAIN-EVAL-001/forensics/cases/G10XMOM002-C01_outcome.png` |
| G10XMOM002-C02 | median_loss | CH-2018-07-15-USDJPY-short | short / pair_direction=1 | 112.199000 | 111.444000 | unknown | predeclared median_loss; formation=-0.017583; rank=7 | `03. EA Developer/EA_G10WeeklyXSMomentum/research/evidence/HYP-G10-XMOM-W1-002/G10XMOM002-TRAIN-EVAL-001/forensics/cases/G10XMOM002-C02_decision.png` | `03. EA Developer/EA_G10WeeklyXSMomentum/research/evidence/HYP-G10-XMOM-W1-002/G10XMOM002-TRAIN-EVAL-001/forensics/cases/G10XMOM002-C02_outcome.png` |
| G10XMOM002-C03 | median_win | CH-2019-11-03-USDCAD-short | short / pair_direction=1 | 1.313540 | 1.322550 | unknown | predeclared median_win; formation=-0.006161; rank=7 | `03. EA Developer/EA_G10WeeklyXSMomentum/research/evidence/HYP-G10-XMOM-W1-002/G10XMOM002-TRAIN-EVAL-001/forensics/cases/G10XMOM002-C03_decision.png` | `03. EA Developer/EA_G10WeeklyXSMomentum/research/evidence/HYP-G10-XMOM-W1-002/G10XMOM002-TRAIN-EVAL-001/forensics/cases/G10XMOM002-C03_outcome.png` |
| G10XMOM002-C04 | largest_win | CH-2020-03-15-AUDUSD-short | short / pair_direction=-1 | 0.624100 | 0.580060 | unknown | predeclared largest_win; formation=-0.065414; rank=7 | `03. EA Developer/EA_G10WeeklyXSMomentum/research/evidence/HYP-G10-XMOM-W1-002/G10XMOM002-TRAIN-EVAL-001/forensics/cases/G10XMOM002-C04_decision.png` | `03. EA Developer/EA_G10WeeklyXSMomentum/research/evidence/HYP-G10-XMOM-W1-002/G10XMOM002-TRAIN-EVAL-001/forensics/cases/G10XMOM002-C04_outcome.png` |
| G10XMOM002-C05 | matched_win | CH-2018-11-11-AUDUSD-long | long / pair_direction=1 | 0.721800 | 0.732930 | unknown | predeclared matched_win; formation=0.005161; rank=2 | `03. EA Developer/EA_G10WeeklyXSMomentum/research/evidence/HYP-G10-XMOM-W1-002/G10XMOM002-TRAIN-EVAL-001/forensics/cases/G10XMOM002-C05_decision.png` | `03. EA Developer/EA_G10WeeklyXSMomentum/research/evidence/HYP-G10-XMOM-W1-002/G10XMOM002-TRAIN-EVAL-001/forensics/cases/G10XMOM002-C05_outcome.png` |
| G10XMOM002-C06 | matched_loss | CH-2018-11-18-AUDUSD-long | long / pair_direction=1 | 0.731320 | 0.722570 | unknown | predeclared matched_loss; formation=0.015302; rank=2 | `03. EA Developer/EA_G10WeeklyXSMomentum/research/evidence/HYP-G10-XMOM-W1-002/G10XMOM002-TRAIN-EVAL-001/forensics/cases/G10XMOM002-C06_decision.png` | `03. EA Developer/EA_G10WeeklyXSMomentum/research/evidence/HYP-G10-XMOM-W1-002/G10XMOM002-TRAIN-EVAL-001/forensics/cases/G10XMOM002-C06_outcome.png` |

## 7. Conclusions and legal next work

- **[OBSERVED]** The exact tested rule is negative after cost, fails all PF tiers, fails MC DD, and underperforms its matched reverse control. Its internal holdout must remain sealed.
- **[INFERENCE]** Winning legs are ordinary next-week continuation outcomes large enough to cover cost; the population does not show that the frozen ranking selects them reliably.
- **[LIMIT]** This does not kill other formation horizons, event clocks, futures-based cross-sectional signals, or different mechanisms. It also does not prove a live EA would match the proxy.
- **Fresh idea 1 [HYPOTHESIS]:** cross-sectional *slow* trend with an outcome-blind multi-month formation and fixed rebalancing clock; falsify on a new train contract before holdout.
- **Fresh idea 2 [HYPOTHESIS]:** event-clock currency strength continuation using an independent futures/spot dislocation surface, subject to data/licensing and cost feasibility first.
- **[ADJUDICATION]** Grok's proposed direct reversion and AUD/NZD deletion are rejected: the matched reverse control already lost, while deleting weak symbols is same-sample selection. A different horizon is only conditionally legal under independent research, a fresh ID and a new outcome-blind preregistration.
