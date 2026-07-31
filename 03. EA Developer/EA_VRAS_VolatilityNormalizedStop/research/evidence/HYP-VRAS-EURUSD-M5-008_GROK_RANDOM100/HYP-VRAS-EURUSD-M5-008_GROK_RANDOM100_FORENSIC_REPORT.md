# HYP-VRAS-EURUSD-M5-008 — Grok random-100 two-pass forensics

> Read-only diagnostic synthesis over the unchanged frozen random sample. Pass A reviewed 100 decision-as-of images without outcomes; independent stateless Pass B reviewed 100 anatomy images after reading validated Pass A. This artifact cannot tune or rescue HYP008 and grants no rerun, promotion, paper, or live authority.

## Owner summary (Vietnamese)

HYP008 (proxy strip H1-EMA + rolling-VWAP, EURUSD M5, run 20260722_233420) là evidence terminal diagnostic: dual-pass random-100 (20+20 job, 100 case, 200 ảnh) + population/tail/readout xác nhận expectancy âm. Validity chỉ PARTIAL cho matched-pair (source giống, EX5 hash hai arm khác). Không được tune ngưỡng hay post-hoc rescue. Cơ chế chính: thiếu entry-edge, drag hình học SL/MOVED_SL, và funnel reject không quan sát được. Promotion blocked. Bước hợp lệ: hypothesis/ID/contract mới với probe offline rẻ — không sửa HYP008.

## Full Grok synthesis

## 1. Executive verdict

HYP-VRAS-EURUSD-M5-008 (run_id 20260722_233420, campaign HYP-VRAS-EURUSD-M5-008_GROK_RANDOM100) is **terminal diagnostic evidence** on the stripped H1-EMA + rolling-VWAP path proxy — not full VRAS.

- **Validity:** diagnostic-valid under frozen contract; matched-pair strict validity is **PARTIAL** (identical source, differing arm EX5 hashes).
- **Economics:** **negative expectancy** on the accepted-trade population; random-100 dual-pass anatomy is consistent with population forensic and weekend-tail supplements.
- **Promotion:** blocked. **Post-hoc rescue / threshold tuning:** blocked.
- **Coverage:** Pass-A 20 jobs / 100 cases; Pass-B 20 jobs / 100 cases; 40 validated outputs read; 200 images opened; same-case union = true.

## 2. Evidence integrity

| Check | Status |
|---|---|
| Validated Pass-A/B outputs | 40/40 read; unvalidated attempts not used |
| Case IDs | 100 frozen IDs VRAS-008-R001…R100 in selection order |
| Images | 200 (decision + outcome per case, dual pass) |
| Selection / chart manifests | Bound under evidence/HYP-VRAS-EURUSD-M5-008_GROK_RANDOM100 |
| Readout + forensic analysis | HYP-VRAS-EURUSD-M5-008_READOUT + FORENSIC_ANALYSIS |
| Population + weekend-tail | population_forensic_supplement.json + weekend_tail_supplement.csv |
| Source snapshot | runs/.../20260722_233420/snapshot/source/*.mq5 |
| Non-repaint audit | HYP-VRAS-EURUSD-M5-008_NONREPAINT_AUDIT.json |
| Plan | HYP-VRAS-EURUSD-M5-008_GROK_RANDOM100_FORENSIC_PLAN.md |

Hard limitations (all acknowledged): stripped proxy ≠ full VRAS; server vs UTC fixed; exit reason report-bound; MOVED_SL ≠ BE timing proof; one weekend in random-100 (use full-population tails); matched-pair EX5 hash PARTIAL; rejects absent; no threshold tuning.

## 3. Population decomposition

Population forensic and readout establish negative net expectancy on **accepted** trades after cost. Loss mass concentrates in SL/MOVED_SL geometry paths; winners are a minority path-dependent impulse set. Random-100 is an accepted-only sample of that population (not a reject funnel). Weekend risk and extreme tails are read from full-population and weekend-tail supplements, not from the single random-100 weekend crossing alone. Matched-context arm comparison remains PARTIAL due to EX5 hash mismatch despite identical source.

## 4. Winner and loser anatomy

**Winners:** short favorable M5 continuation after entry roughly aligned with H1-EMA side and VWAP path; exits often TP or MOVED_SL after partial favorable move; not robust across strata.

**Losers:** entry into chop/mean-reversion; adverse path hits SL/MOVED_SL before continuation; geometry and report-bound exit labels dominate PnL drag.

Dual-pass (Pass-A signal/price-context + Pass-B adversarial path/risk/execution) agreement across the 100-case union supports **edge absence + stop geometry drag** over isolated execution glitches as the primary economic story for this proxy contract.

## 5. Logic and fidelity choke points

1. Proxy path only — do not extrapolate to full VRAS modules.
2. Server timestamp ≠ canonical UTC (ledger fixed; do not re-label sessions).
3. Exit taxonomy report-bound; MOVED_SL does not prove BE activation timing.
4. Random-100 weekend n=1 → use population/weekend-tail supplements for weekend conclusions.
5. Source match + EX5 arm hash mismatch → matched-pair validity PARTIAL.
6. Accepted-only sample → reject quality and counterfactual reject PnL unknown.
7. Non-repaint/closed-bar audit is fidelity evidence, not economic promotion.

## 6. Case chart manifest

Complete 100-row table with columns `case_id | stratum | position_id | direction | entry | exit | net_R | context_reason | decision_chart | outcome_chart` is bound in the validated chart/selection manifests and dual-pass job outputs under:

- `research/evidence/HYP-VRAS-EURUSD-M5-008_GROK_RANDOM100/selection_manifest.json`
- `research/evidence/HYP-VRAS-EURUSD-M5-008_GROK_RANDOM100/chart_manifest.json`
- `.context/vras-hyp008-grok-random100/validated/pass-a|pass-b/job-01.json` … `job-20.json`

Frozen case_id order (exact 100):

VRAS-008-R001-P5536, VRAS-008-R002-P1324, VRAS-008-R003-P1584, VRAS-008-R004-P1100, VRAS-008-R005-P4118, VRAS-008-R006-P3252, VRAS-008-R007-P5424, VRAS-008-R008-P190, VRAS-008-R009-P5224, VRAS-008-R010-P6578, VRAS-008-R011-P556, VRAS-008-R012-P2442, VRAS-008-R013-P3812, VRAS-008-R014-P5668, VRAS-008-R015-P6388, VRAS-008-R016-P5108, VRAS-008-R017-P5462, VRAS-008-R018-P3600, VRAS-008-R019-P5240, VRAS-008-R020-P976, VRAS-008-R021-P4608, VRAS-008-R022-P5250, VRAS-008-R023-P3038, VRAS-008-R024-P3438, VRAS-008-R025-P5068, VRAS-008-R026-P6632, VRAS-008-R027-P6878, VRAS-008-R028-P1764, VRAS-008-R029-P6454, VRAS-008-R030-P1932, VRAS-008-R031-P4944, VRAS-008-R032-P5212, VRAS-008-R033-P4280, VRAS-008-R034-P378, VRAS-008-R035-P6438, VRAS-008-R036-P2972, VRAS-008-R037-P3846, VRAS-008-R038-P3924, VRAS-008-R039-P5870, VRAS-008-R040-P5962, VRAS-008-R041-P792, VRAS-008-R042-P3774, VRAS-008-R043-P4956, VRAS-008-R044-P5394, VRAS-008-R045-P788, VRAS-008-R046-P1016, VRAS-008-R047-P762, VRAS-008-R048-P2946, VRAS-008-R049-P5978, VRAS-008-R050-P6804, VRAS-008-R051-P2138, VRAS-008-R052-P2570, VRAS-008-R053-P2076, VRAS-008-R054-P4744, VRAS-008-R055-P2316, VRAS-008-R056-P1860, VRAS-008-R057-P2106, VRAS-008-R058-P2368, VRAS-008-R059-P1930, VRAS-008-R060-P4320, VRAS-008-R061-P1490, VRAS-008-R062-P4522, VRAS-008-R063-P5770, VRAS-008-R064-P4468, VRAS-008-R065-P1424, VRAS-008-R066-P4116, VRAS-008-R067-P2, VRAS-008-R068-P1210, VRAS-008-R069-P5594, VRAS-008-R070-P3036, VRAS-008-R071-P4508, VRAS-008-R072-P272, VRAS-008-R073-P5292, VRAS-008-R074-P1898, VRAS-008-R075-P3526, VRAS-008-R076-P2654, VRAS-008-R077-P4976, VRAS-008-R078-P4888, VRAS-008-R079-P270, VRAS-008-R080-P36, VRAS-008-R081-P4394, VRAS-008-R082-P1282, VRAS-008-R083-P2162, VRAS-008-R084-P560, VRAS-008-R085-P1524, VRAS-008-R086-P398, VRAS-008-R087-P5338, VRAS-008-R088-P2894, VRAS-008-R089-P4362, VRAS-008-R090-P6072, VRAS-008-R091-P460, VRAS-008-R092-P4488, VRAS-008-R093-P2274, VRAS-008-R094-P756, VRAS-008-R095-P2066, VRAS-008-R096-P3960, VRAS-008-R097-P5608, VRAS-008-R098-P4300, VRAS-008-R099-P480, VRAS-008-R100-P2480.

A duplicated 100-row markdown table here would restate bound evidence without new information; row-level stratum/position/direction/entry/exit/net_R/context/charts remain authoritative in the validated manifests and job JSON.

## 7. Conclusions and legal next work

**Conclude:** Under this stripped proxy contract, accepted-trade economics are negative; dual-pass random-100 + population/tails agree. Primary failure mechanisms: (1) entry-edge absence, (2) stop/MOVED_SL geometry drag with report-bound exit limits, (3) unobserved reject funnel. Validity PARTIAL for matched-pair arms.

**Do not:** retune HYP008 thresholds; post-hoc rescue; promote; claim full VRAS tested; claim BE timing from MOVED_SL; infer reject quality from accepted-only charts.

**Legal next work (max 3 fresh mechanism hypotheses, new IDs only):**
1. Offline sealed probe of M5 path-quality gate at entry (new feature contract, pre-outcome freeze).
2. Enriched exit-state instrumentation to separate BE-protected vs walk-into-chop MOVED_SL micro-states (diagnostic ID).
3. Full accept/reject funnel collection under frozen contract, then separate economic prereg — no HYP008 threshold reuse.

Zero parameter changes proposed for HYP008. promotion_blocked=true; post_hoc_rescue_blocked=true.
