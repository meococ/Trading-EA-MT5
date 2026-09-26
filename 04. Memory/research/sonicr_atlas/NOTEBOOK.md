# NOTEBOOK.md — NotebookLM usage log (lane SONIC-ATLAS)

## Status timeline

- ~09:00Z (step 0c): `nlm login --check` → expired (both CLI and MCP). Logged `ESCALATE: NotebookLM not authenticated`. Proceeded with direct reading per lane rules; no login attempted.
- 09:10Z Lead note (`primary/drive/LEAD_NOTE_3_NLM.md`): Owner re-authenticated; Lead verified auth valid; instruction to run STEP 2 in full.
- ~09:42Z: `nlm login --check` → **Authentication valid** (profile default, 19 notebooks, account toilatruc999@gmail.com). Escalation cleared.

## Usage / budget

`nlm usage` at ~09:42Z (clock corrected — earlier stamps read ~3.5h high): rolling window 13.7% used / 86.3% remaining (reset 19:15 SEA), weekly 1.3% used / 98.7% remaining (reset 27/09). Plan: NOTEBOOKLM_TIER_PRO_CONSUMER.
Budget = min(30, remaining-10). With ~86% of the rolling window free the effective budget was the full 30; **queries actually used: 6** (A, B, C, D, E, F consolidated group queries — one per group instead of Q1-Q7×6, prioritising completeness per call).

## Notebook

- Name: **Sonic R System** (created this lane — checked `nlm list notebooks` first: no pre-existing notebook with that name)
- id: `8490421d-f2b6-45f1-9e34-ddb898e5034c`
- URL: https://notebooklm.google.com/notebook/8490421d-f2b6-45f1-9e34-ddb898e5034c
- CLI alias set: `sonicr`
- Kept private; nothing shared, renamed or deleted.

## Sources added (15 rows flagged `added_to_notebook=y` in SOURCES.csv)

Text/file uploads (Tier 0, from `nlm_src/`):
1. Candles-Suite.txt (S01) 2. Volumes-Suite.txt (S02) 3. Access-Panel.txt (S03) 4. FFCal-Panel.txt (S04) 5. SonicR_PV_Histogram_Black_2011.txt (S05/S39) 6. SonicR_Filled_Dragon_White.txt (S49) 7. ff_post1_thread114792_20141222.txt (S07) 8. ff_post1_thread114792_20200812.txt (S18) 9. ff_post7348659_2014release_page3376.txt (S06)

URL sources: 10. sonicr999 (S10) 11. th3-pro-forex (S11) 12. tamnhindautu PVSRA (S31) 13. tamnhindautu sonic-r-la-gi (S32) 14. traderviet 49803 (S48 — note: the PVSRA thread URL redirected to the Toptal-translation article; the content ingested is S48, not S33).

URL ingest failures (recorded, not retried beyond one attempt): sgtradingcourses (S13), toptal (S26), topsanfx (S35), tradingview TR Main (S21), fortraders candles_suite html — NotebookLM could not fetch them; the same material is covered by the uploaded primary files and the successful mirrors.

## Queries run (6 of ≤30 budget)

| file | group | focus |
|---|---|---|
| nlm_raw/A_dragon_trend.md | A | Dragon/Trend exact code, slope question, buffer layout, doctrine use |
| nlm_raw/B_setups.md | B | Classic full rules, Re-entry, Scout definition+evidence+warnings, invalidation |
| nlm_raw/C_pvsra.md | C | PVA code thresholds, position-building vs run-for-profits, above/below S&R, entry-vs-analysis |
| nlm_raw/D_sr.md | D | WHQ grid code, significance order, other S/R, runway, VN zone views |
| nlm_raw/E_discipline.md | E | numbered rules, Sonic M sizing, news doctrine, weekend/overnight |
| nlm_raw/F_lineage.md | F | source disagreements, timeline, TR/VN variants, mechanical-vs-discretionary |

Each raw answer with its citation objects is saved verbatim in `nlm_raw/`. NotebookLM claims were cross-checked against the primary passages before any "verified" tag — its answers confirmed (not originated) the conclusions: e.g., Trade Levels "based on manually input values" (sonicr999, double-confirms the Lead decode), SL beyond recent large-scale swing H/L ≤100-120 pips (sonicr999 manual verbatim), Scout = early reversal entry on H/L pattern or consolidation break (sonicr999).

## Studio artifacts

| artifact | id | status |
|---|---|---|
| Briefing Doc (report) | 34d84012-6b8a-4eec-bb42-fbfa87cf84b3 | completed (~09:55Z) |
| Data table "component x rule x source" | e3560264-6cc2-4e33-a042-b38293b74af7 | completed (~09:55Z) |
| Audio overview (Vietnamese, `--language vi`, deep_dive, default) | 3091328e-cf76-4a34-bf06-711f8a303507 | started ~09:44Z — final status checked in round 1B below |
| Mind map | — | INVALID_ARGUMENT twice (same failure as the other lane today; skipped per lane rules, logged; no further retry) |

Owner opens the notebook himself; ids above are for reference. Raw answers are in `nlm_raw/`, not in the notebook.

---

## ROUND 1B (depth pass, ~10:00-10:30Z)

### Second-pass budget

`nlm usage` at ~09:59Z: rolling window ~30% used / ~70% remaining → pass-2 budget = min(20, remaining-10) = 20. **Queries actually used this pass: 6** (EX1, EX2, NUM, VN, RUN, M5). Lane cumulative: 12 of 30.

### Sources added this pass

- `Sonic_2_PVA_Candles_White_20140317.txt` (canonical TAH 03-17-2014 PVA file, S51) — status READY.
- YouTube attempts (per Lead: VN lessons + accessible video): **all failed or wrong** —
  - Sonic's own video `HCEm9rRr9Lw` (linked from FF page 2873): ingested but resolved to an unrelated AR-15 review (dead/mis-ID'd video) → deleted by me this lane.
  - banteka Sonic R series `hZZ_dPhYb5o`, `NBlB8RaNI4k`, TradingUnited webinar `BTun1dW51SE`: "not accessible" (dead/private 2012-13 era videos) — status FAILED, left in list as tombstones.
  - **VN Sonic R YouTube lessons: none findable.** Three bounded searches surfaced only VN *blog/forum* teaching (tamnhindautu/traderviet/topsanfx/giaodichtaichinh — already sources) and the Sega game. VN Sonic R teaching is text-based; recorded as a finding, not retried further.
- Notebook total now: 23 source entries; ~14 status-READY (the 3 ff_post*.txt uploads show status-3 failed, but their content is covered by the sonicr999 post#1 mirror which NLM did cite).

### Gap queries (all saved verbatim with citations in `nlm_raw/*_p2.md`)

| file | question focus | verified? |
|---|---|---|
| EX1_classic_examples_p2.md | Classic chart narratives, wave legs vs Dragon, EP/SL/TP | yes — citations = post#1 text via mirror source 158fb243 (= S10 sonicr999; local S18 file lacks the rules list) + PVSRA doc + VN source |
| EX2_scout_reentry_p2.md | Scout/Re-entry narratives, differences | yes — sonicr999 Scout text + post#1 EP/TP rules + VN translation |
| NUM_numbers_p2.md | "several pips" number? "large-scale swing"? ≤5/wk per acct or pair? | yes — post#1 verbatim: no number given (discretionary buffer); SL beyond large-scale swing H/L, cap 100-120p EURUSD, ≥80p JPY; ≤5/wk is a general account-level rule, not scoped per pair |
| VN_variants_p2.md | VN wave counting, extra EMAs/TFs, entry/exit differences | yes — topsanfx EMA200+EMA610, giaodichtaichinh rainbow-EMA+RSI (contamination), pullback-to-EMA entry style |
| RUN_build_vs_run_p2.md | how build-vs-run is read on a chart in practice | yes — TAH PVSRA text verbatim (bulls buy below key S&R / bears sell above it; build = price moving against position side, run = with it) |
| M5_timeframe_p2.md | does TAH/manual sanction M5? | **NLM answer said "no sanction" — WRONG.** Verified directly against the page-3756 capture (saved `primary/ff_page3756_*.txt`) — the M5/London wording sits in the TAH post immediately ABOVE #7679382 on the same page: TAH's own words DO sanction M5 "for scalping, or as an alternative for getting an earlier entry", with the caveat it forfeits build→run transition-confirmation time; Classic core remains M15 London. Lesson: this is why cited passages must be read, not trusted. |

### Studio artifacts — final status

| artifact | id | status |
|---|---|---|
| Briefing Doc | 34d84012-6b8a-4eec-bb42-fbfa87cf84b3 | **completed** |
| Data table | e3560264-6cc2-4e33-a042-b38293b74af7 | **completed** |
| Audio overview (vi) | 3091328e-cf76-4a34-bf06-711f8a303507 | **completed** (checked ~10:00Z) |
| Mind map | — | INVALID_ARGUMENT ×2 — skipped per rules (not retried this pass) |

---

## ROUND 1C (Vietnamese pass, ~11:20-12:00Z)

### Sources added (6 videos + 2 pages)

YouTube (captions verified on the watch page before adding):
- `2o9DQQ8yXX0` Nhật Hoài Trader — "Sonic R Scalping Khung 15 Phút" → src `6dda4081` (S52)
- `hwbi_-3DFys` Lucy — "Hướng dẫn chi tiết Hệ thống Sonic R" → src `72b9da59` (S53)
- `1OGTB-I36vs` Lucy — "Sonic R (Thực hành)" → src `e9226f6e` (S54)
- `lbkMihV7nUM` TRADERPTKT — "Bài 14 Sonic R Chuyên Sâu" → src `41e704d4` (S55)
- `2zwASKYFifE` — "SONIC R vào lệnh Sell thuận xu hướng" → src `e827dabb` (S56)
- `3dH14nhVjO0` — "Sonic R + Stoch RSI Bollinger Bands" (contamination class) → src `65cf6571` (S57)

Pages:
- tamnhindautu "tiếp cận thiết lập Cổ điển" → src `6cb007c8` (S58)
- tamnhindautu "PVSRA khai thác khối lượng" → src `92b945ad` (S59) — **resolved to the same article as S32** (possible canonicalization dup; flagged in SOURCES.csv)

### Skipped (logged reasons)

- `QeMOELmb0d4` (zoom Buổi 1), `oAhsx5brL_Y` (Elliott ứng dụng) — login wall, no captions.
- `jmwGfu9Q2kY` (Team hv Elliott+Fibo+Pitago) — public captions exist but NLM ingest failed ×2.
- forexvietnam + hocdautu pages — HTTP timeout via curl AND webfetch ×2.
- Scribd "Co Ban Ve He Thong Sonic R" — per Lead: read-only reference, not uploaded.
- `@chibaosonicr` channel — not sampled inside timebox (Bài 14 already covers the deep lesson).

### Pass-3 queries (5 of budget; all `--source-ids` restricted to the 11 VN sources)

| file | focus | verified? |
|---|---|---|
| VN_p3_a_waves.md | wave counting per teacher | yes — TNDT: L-H-HL→HH / H-L-LH→LL, leg-3 candle breaks Dragon, re-entry "rào cản thứ 3", M15 + H1/H4/D1. **CAVEAT (reviewer r3)**: this file's citation objects mis-map — all [n] resolve to TRADERPTKT transcript (41e704d4); verbatim backing for the TNDT claims lives in `VN_variants_p2.md` (src 6c5ed85f) |
| VN_p3_b_extras.md | extra EMAs/indicators | yes — EMA200/610 as dynamic S/R (Bài14 ~[01:00], Stoch-vid ~[01:30], TNDT); rainbow 6-EMA+RSI recipe; StochRSI/BB; Pivot (Nhật Hoài); Elliott linkage |
| VN_p3_c_rules.md | entry/SL/TP/TF per teacher | yes — Nhật Hoài (M15 opt, ≥M5, close-outside-band, 2 SL styles, pivot trail); Lucy (H4/H1→M15/M5/M1, rejection candle, wick SL); TRADERPTKT (D1/H4→M15/H1, band touch/engulfing, band SL, 2R TP). **CAVEAT**: citation objects again all resolve to 41e704d4; Nhật Hoài verbatim is in `VN_p3_e_examples.md` cits 19/22 (src 6dda4081) |
| VN_p3_d_pvsra.md | PVSRA/WHQ usage | yes (thin file — answer text cites TNDT keeping PVSRA+WHQ as advanced core vs video teachers ignoring both; citations block empty → treat prose as lower-confidence, core split confirmed by c/e answers) |
| VN_p3_e_examples.md | worked trades | yes — Lucy XAU buy 1933/SL1930 Dragon-retest win; TNDT rainbow EURUSD 1.1225/1.1200/1.1300 +75p (contamination); Nhật Hoài rules-level mechanics |

### Notebook totals after pass 3

31 source entries; **20 status-2 READY** (verified by counting `nlm source list` status field — the earlier "~14 of 23" was an underestimate; 11 entries are status-3 failed incl. dead videos/URLs); +8 new this pass (6 videos + 2 pages). Cumulative queries: 17 (6 + 6 + 5). Mind map still abandoned.

**NLM citation-mapping defect noted (reviewer r3)**: in `VN_p3_a/c` all citation objects resolve to source `41e704d4` regardless of which teacher the prose describes — treat those files' `[n]` markers as unreliable; verbatim backing was cross-located in `VN_p3_e_examples.md` and `VN_variants_p2.md`. `VN_p3_d` returned zero citations — its two-group split is corroborated by the c/e answers and by S31 material, not by its own file.
