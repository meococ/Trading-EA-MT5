# REVIEW.md — neutral review pass (Step 6)

Reviewer: fresh-context read-only subagent (spawned ~13:0xZ), checklist per lane spec: (a) 15 file:line claims vs primary code, (b) contradictions vs MQ4, (c) 10 sampled `ok` URLs, (d) VN report accuracy.

## Results

- Claims checked ≈ 39. **PASS 18 / WARN 14 / FAIL 3.**
- Every file:line code claim verified (PVA math, WHQ grid, FFCal, 2011 histogram, externs, colours, alerts); all 10 sampled URLs real & on-topic; VN report fluent with full diacritics, consistent numbers, source ids present.

## FAIL findings → fixes applied

1. **Filled Dragon delivered but not integrated** (`primary/drive/SonicR_Filled_Dragon_White.mq4`, Lead drop 09:12Z).
   → FIXED: SHA256 computed `fbb09c411f0841e566c6b1ef612e7307f242744165b746cf5257e808f30dd35e` — prefix matches May manifest `FBB09C411F0841E5`. Added to PRIMARY_INDEX (verified-hash) + SOURCES S49; INDICATORS §1 rewritten from actual code (buffers 0-5 = EMA34 H/L/C fills+lines, 6-7 = EMA89; periods hardcoded; no slope code; cross-TF removed 05-2013; zoom GV slave; colour table); BAO §2 updated; gap closed in PRIMARY_INDEX.
2. **NotebookLM stale** (Lead re-auth 09:10Z not actioned).
   → FIXED: auth verified, notebook "Sonic R System" created (8490421d-...), 14 sources ingested (9 primary files + 5 URLs), 6 group queries run into `nlm_raw/`, studio artifacts triggered (report 34d84012, data-table e3560264, audio-vi 3091328e); mind map failed INVALID_ARGUMENT ×2 → skipped per rules. NOTEBOOK.md fully rewritten with real data; ATLAS S12.10 updated.
3. **Trade Levels overstated** ("reads REAL order data").
   → FIXED everywhere (INDICATORS §5, ATLAS S2 row, BAO §2): Feb-2014 build = manual EP_1..20/TP_1..3/SL_1..3 + avg-EP + bid alert; real-orders migration only STARTED (St3ve credit, post 7348659:399); sonicr999 itself states "based on manually input values" — double confirmation. May retrieval_readout label "sr_whole_half_quarter_interaction" flagged wrong; WHQ grid confirmed living in Access Panel only.

## WARN findings → fixes applied

- u1-u4 declaration cite → moved to line 568 with consumption at 953-980 (INDICATORS §6). FIXED.
- `Poin=Point*10` unconditional → 4-digit-broker caveat added (INDICATORS §6). FIXED.
- Suite generation dated 2015 vs announced May-2014 → reconciliation written (INDICATORS §3, ATLAS S1). FIXED.
- "Sonic entry" S&R embellishment → removed; now matches seminar text (ATLAS S3.4). FIXED.
- Classic volume element missing → added "a bit of Volume to validate"/"High Volume at the recent low" to ATLAS S3.1 + new S7 row. FIXED.
- 2012-04 dragon date → corrected to 05-01-2012 per change-log (ATLAS S1). FIXED.
- Toptal buffer-5 map → marked Solid-Dragon-Trend-specific/unverified vs Filled layout (INDICATORS §1, S2, BAO §2). FIXED.
- S38 two-manifests-one-URL → annotated (2762835 vs 3562296). FIXED.
- SOURCES duplicates → malformed S44 row removed; S05≡S39 cross-annotated; S41/S42/S43 already self-annotated (kept for citation stability). FIXED.
- S36 missing contamination flag → Elliott justification flagged. FIXED.
- Unverifiable-locally claims (S08/S43 Scout, S09/S42 Sonic M, S15/S16 quotes) → kept with source tags; medium verify-confidence noted here.

## Remaining known limitations (not fixable in-lane)

- ~~The literal Feb/Mar-2014 Sonic_2/6 PVA files unread~~ — **CLOSED round 1B**: `drive/Sonic_2_PVA_Candles_White_20140317.mq4` hash-verified, logic identical to Suite; climax = BetterVolume_v1.4 heritage (line 41). `ESCALATE: NEED_DRIVE` closed.
- Mar-2014 `Sonic_3 Trade Levels` 57KB revision (likely the real-orders version) unread — available via Drive on request.
- sgtradingcourses/toptal/topsanfx/tradingview URLs ingest-failed in NotebookLM (fetch ok in-lane earlier; content covered by uploaded primaries + mirrors).
- traderviet 49803 ingested article ≠ S33 thread (redirect) — noted in NOTEBOOK.md.

Reviewer verdict after fixes: no remaining code-level contradictions; all FAILs resolved.

---

# REVIEW.md — round 2 (depth pass, neutral reviewer, ~10:50Z)

Reviewer: fresh-context read-only subagent, instructed to check 15 named claims (≥5 from S8, ≥3 NotebookLM-derived, plus code/source claims) against primary evidence with file:line, plus consistency sweep ATLAS↔BAO↔SOURCES↔nlm_raw.

## Verdict: PASS-WITH-WARNS

All 15 required claim checks **PASS** with verbatim/line evidence:

- S8 numbers verified: archive PF 1.41/127 & 1.16/335 (`20260813_...FRONTIER.md:43-46`), Grok v10 split + verdict (`20260812_...AUDIT.md:70`), run 205426 N=307 PF 0.94 (`20260816_...FREEZE.md:9,41`), density batch (`packet:493`), Hybrid 1505/1508 + PF 0.98 @0.22/wk (`packet:500-503`).
- London/M5 TAH wording verbatim (`primary/ff_page3756_*.txt:226-234`); ≤5/week account-level via NLM cited_text (`NUM_numbers_p2.md:67,72`); NLM M5 answer confirmed WRONG vs primary (`M5_timeframe_p2.md:2`).
- Code verified: PVA prior-10 loop `j=i+1..i+10`, rising 1.5×, climax 2×/sv-max (`Sonic_2_PVA_Candles_White_20140317.mq4:201-213`, BetterVolume ack :41); Access Panel `Poin2=Point`, `Poin=Point*10` (:712-713), quarter ≤M30 (:337); Dragon EMA34 H/L/C + EMA89, hardcoded, no slope (:251-262, :130/137, :173-195); S51 hash `4ef2dcb1…f4a71` (`PRIMARY_INDEX.md:21`).
- No source id out of range; S43 dup + S44 contaminated correctly flagged; all 6 `nlm_raw/*_p2.md` non-empty (RUN populated on re-run).

## WARN findings → fixes applied (all 7)

1. ATLAS:190 enumerated 5 elements but matrix row J shows 6×P → enumeration fixed to `W1/W5/W6/E1/S1/D1`; same fix BAO:188. FIXED.
2. London/M5 quote attributed to post 7679382 → actually sits in the TAH post immediately above #7679382 on page 3756 (Scout-Updated IS 7679382). Re-attributed at ATLAS:42, BAO:56/209, NOTEBOOK:81, BAO appendix; page-level S08 cite unchanged. FIXED.
3. "Post#1 verbatim" quotes ("≤5 trades a week", "50 to 400+ pips") only preserved via NLM cited_text of S10 mirror — saved S18 file lacks the rules list. Provenance corrected at ATLAS:47, ATLAS:101, BAO:13/128/217, NOTEBOOK:76. FIXED.
4. PF 1.59 (EUR London V1) not in packet → number dropped; "2 trades/2 years, PF not preserved" at ATLAS:169, BAO:182/212. FIXED.
5. Scanner-262 → tagged `unverifiable-first-party` (Lead brief, ledger lost 31/08) at ATLAS:168, BAO:181. FIXED.
6. "4 trades" (M5 T1) and M5-seeds numbers (1.32-1.78 / 0.952 / 492) → tagged Lead-brief class at ATLAS:166/170, BAO:179/183/213. FIXED.
7. NOTEBOOK:76 "post#1 text (158fb243)" → clarified 158fb243 = S10 mirror source, not local post#1 file. FIXED.

## Remaining known limitations (not fixable in-lane)

- Two figure classes rest on Lead briefs without local artifacts (scanner-262, M5-seeds numbers) — disclosed inline.
- May quarantine files still unrecovered beyond the two Drive drops; FF attachment images TLS-blocked; Trade Levels Mar-2014 build unread; mind map INVALID_ARGUMENT.

Round-2 verdict after fixes: PASS — no open issues.

---

# REVIEW.md — round 3 (Vietnamese pass, neutral reviewer, ~12:25Z)

Reviewer: fresh-context read-only subagent; 8 claims from the new VN material checked against `nlm_raw/VN_p3_*.md` (answer text AND citations/references arrays), SOURCES.csv, NOTEBOOK.md.

## Verdict: PASS-WITH-WARNS — all 8 claims substantively true

- Nhật Hoài M5-boundary verbatim found (`VN_p3_e_examples.md:145` cit 19); trigger verbatim ("nến thoát khỏi Dragon đóng cửa bên ngoài", `:160` cit 22).
- TRADERPTKT EMA200/610 (`b_extras:46`), band-SL + 2R-TP (`c_rules:53`) verbatim.
- Lucy rejection-scalp + wick-SL + XAU 33/30 fragments (`e_examples:80-90`); "1933/1930" rests on NLM prose + ASR fragments.
- TNDT wave defs verbatim in `VN_variants_p2.md:29-44` (src 6c5ed85f).
- SOURCES.csv S52-S59 correct; NOTEBOOK lists all adds/skips.

## WARN findings → fixes applied

1. NLM citation-mapping defect in `VN_p3_a/c/d` (all cites resolve to 41e704d4 or empty) → caveat lines added to NOTEBOOK.md pass-3 table + totals section. FIXED.
2. EX-9/VD9 source tag `S32/S58` → `S32` (S59 flagged as the dup) — ATLAS:91, BAO:124. FIXED.
3. "nhồi lệnh" quote was a normalized reconstruction and merged S56+S57 → re-labelled "normalized transcript", tagged S56 specifically; family 5 split into S56 (averaging) / S57 (StochRSI+BB, no averaging). ATLAS:139, BAO:189. FIXED.
4. ATLAS S12 parenthetical omitted pass-3 → "(6 + 6 + 5)". FIXED.
5. Nhật Hoài quote normalized "không nên" → verbatim "không có nên" restored (ATLAS:136, BAO:129). FIXED.
6. BAO header still said "(round 1B)" → "(round 1C)"; added §9c round-1C changelog + corrected stale "VN YouTube không tồn tại" line. FIXED.
7. NOTEBOOK READY count "~20" → verified actual count = 20 status-2 (earlier "~14/23" was an underestimate). FIXED.

## Remaining limitations

- `VN_p3_d` two-group PVSRA/WHQ split rests on corroboration (c/e answers + S31), not its own citations — flagged inline.
- Lucy XAU "1933/1930" figures = NLM prose + ASR fragments, not clean verbatim — tagged accordingly in EX-8.
- Read-only reviewer could not re-verify live notebook state; READY count verified from our own `nlm source list` output.

Round-3 verdict after fixes: PASS — no open issues.
