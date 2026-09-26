# SONICR_ATLAS.md — the complete, source-verified picture of the Sonic R. System

Lane: SONIC-ATLAS, 2026-09-23. Claim tags: `source-primary` (Kyaw/sonicdeejay or TAH own text/code), `source-secondary` (faithful mirrors), `community` (later practitioners incl. VN), `reconstructed` (deterministic mappings of vague rules), `local-empirical` (our repo evidence), `hypothesis` (untested inference). Every rule carries one tag; sources by id (SOURCES.csv).

---

## S1. Lineage

- 2008 — Kyaw Trader ("sonicdeejay", Singapore) opens FF thread 114792. Self-description: a "simple, profitable 15M swing system inspired from Raghee's book", tuned with wave analysis, S&R and volume after watching blind MA systems die in ranges. (source-primary, S07/S18)
- 2008-2011 — early stack: TRO_Tunnel_Dragon (3×EMA34 H/C/L) + EMA89 + QQE + CCI(63) + NVO + ZZ-Fractal + SHI_Channel; wave-and-level trading, Rules 1-3 already present (≤5 trades/week, no averaging, wide SL). (source-secondary, S27; manifest S38)
- 2011-07 — first-gen "SonicR PV Histogram" (Climax 20-bar incl. current, Rising 1.38× incl. current bar). (source-primary code, S39)
- 2012-04/05 — TAH's first integrated release: Control Panel (Chart Panel + Clock Panel merge), Line & Solid Dragon-Trend (05-01-2012 per Filled Dragon change-log line 56), VSA Candlesticks, VSA Histogram. (source-primary, S10 + code)
- 2012 — Scout trade introduced by sonicdeejay. (source-primary, S18)
- 2013 — VSA renamed PVA (Price-Volume Analysis) → PVA Candles/Volumes; PVSRA (Price, Volume, S&R Analysis) formalised as the qualification lens. 05-25-2013 Filled Dragon released (recovered, hash-verified); Feb-2014 build-600 set: Filled Dragon, PVA Candles/Volumes, Trade Levels, Control Panel, FFCal Panel. (source-primary, S10/S18/S19 + drive file)
- 2014-03 — canonical `TAH 03-17-2014 Revised` set: Sonic_1 Solid Dragon, Sonic_2 PVA Candles, Sonic_3 Trade Levels, Sonic_4 Access Panel, Sonic_5 FFCal Panel, Sonic_6 PVA Volumes + black/white templates. (source-primary, S06/S19/S38)
- 2014-05 — TAH announces the Candles/Volumes "Suite" as the direct Sonic_2/6 successor (S16, post ~72,242); our recovered Suite files are the 05-30-2015 revision (header line 79) — one generation, announced 2014, revised 2015. Access Panel + FFCal Panel continued in parallel. (source-primary code, S01-S04; succession stated by TAH, S16)
- Lineage footnote: the PVA **climax** definition itself is acknowledged by TAH as coming from **BetterVolume_v1.4** (canonical `Sonic_2_PVA_Candles_White_20140317.mq4` line 41 — recovered and hash-verified this lane) — i.e., the rule is VSA/BetterVolume heritage, which explains why identical thresholds appear in Traders Reality's port. (source-primary code)
- 2016+ — Traders Reality ports the PVSRA stack to TradingView and extends it (vector-candle zones, session boxes, EMA cloud) — the main living lineage today. (community, S21-S23)
- 2013+ — Vietnamese community adopts the system widely: faithful translations (tamnhindautu, traderviet/Nhật Hoài) plus local variants adding EMA200/EMA610 and Wyckoff overlays. (community, S31-S37, S25)
- What each layer added: Kyaw = philosophy + wave/dragon/trend core; TAH = professional-grade indicators, PVSRA essay, discipline codification; Traders Reality = platform port + liquidity-zone concept; VN community = translations + hybridisation. (hypothesis — synthesis)

## S2. Components

| component | definition | parameters | how the trader reads it | role | sources/tag |
|---|---|---|---|---|---|
| WAVE | price swing structure L-H-HL (longs) or H-L-LH (shorts) starting at/through the Dragon | qualitative | leg-1 ideally pierces the Dragon; leg-3 candle breaking back out of the Dragon = the actionable moment | validates the setup at S&R | S10/S11, source-primary |
| DRAGON | EMA34 of High, Close, Low (band) | period 34, EMA, H/C/L | must be "angled up with PA above" for longs, "angled down with PA below" for shorts | picks the entry | S13/S24/S26, source-primary |
| TREND | EMA89 of close | period 89 | bias: best longs above, shorts below; Dragon-vs-Trend position reads trend quality | confirms direction | S10/S26, source-primary |
| S&R — WHQ grid | horizontal levels at 00/25/50/75 within each 100-pip span | 25-pip spacing default, density ±, per-TF caps (quarter ≤M30) | whole>half>quarter significance; "runway" = clear space to next strong level | entry filter + TP reference | S03 code, source-primary |
| S&R — swing/consolidation | historic swing H/L, middle of consolidation areas, day/week average-range marks | qualitative; RDH/RDL = session-avg range projection | where MMs do business; TP goes to the next historic level | TP + context | S12/S17, source-primary |
| PVA/PVSRA | candle+volume colour code: climax (vol≥2×avg10 OR sv≥max10) & rising (vol≥1.5×avg10) | 10 prior bars excl. current | where volume spikes relative to key S&R tells what MMs are doing | analysis lens, NOT an entry | S01/S02/S18, source-primary |
| sessions | vLines: Asia, Frankfurt, London, NY opens; London close | broker-TZ+DST resolved | trade at/after London open; avoid Asia | timing permission | S03/S10/S15, source-primary |
| FFCal | next ≤4 FF releases w/ impact colours | minutes-before alert | timing of news = MM volatility event | awareness, not hard block | S04, source-primary |
| Trade Levels | EP_1..20, avg-EP, TP_1..3, SL_1..3 lines + labels | trader-typed inputs (Feb-2014 build); real-orders migration just started | posted-trade clarity + management; up to 20 entries = scaling-in tool | management display | S06/S17 + Lead decode, source-primary |
| range marks | RDH/RDL (day), RWH/RWL (week) | day avg 15 days, week 13 weeks | expected daily/weekly reach from session extremes | TP context, MM targets | S03/S17, source-primary |
| pivots/fibos | daily/fibonacci pivots + mid-pivots; natural fibos on prev-day range | PivotsTz default Frankfurt | secondary S/R | optional context | S03, source-primary |

## S3. Setups

### 3.1 Classic (the core — source-primary, S10/S11/S18)

Context: price at an S&R area (WHQ level, historic level, or consolidation zone). Wave: L-H-HL from below the Dragon (long) or H-L-LH from above (short), ideally leg-1 piercing the Dragon. Dragon angled with PA on the correct side; Trend confirms direction. Volume: doctrine adds "a bit of Volume to validate a setup" — Kyaw's seminar form: "High Volume at the recent low" for longs (S13; the PVSRA doc compiles the same phrase). Session: **London — TAH's own words: "Classic entries are only recommend during the London session"** because that is when setups "more accurately reflect the trend and run further, usually" (S08 page-3756 capture — TAH post immediately above #7679382, verbatim, source-primary). The earlier phrasing "ENTRY SHOULD BE WITHIN LONDON SESSION" is a community restatement of the same rule (S15). Note TAH himself took a nice Classic in the Asian session once (S08 AUDJPY narrative) — the rule is a strong preference, not an absolute veto in his practice.
- Trigger: a leg-3 candle closes back outside the Dragon.
- Entry order: stop order "at least several pips beyond" that candle's extreme (S10/S11). **The sources never specify a number** — "several pips" is a discretionary buffer against spread-wick fills (verified: NLM-p2 NUM query vs post#1 text). Our 3-pip freeze is reconstructed. No strong S&R just beyond the entry ("runway").
- SL: beyond the far side of the **recent large-scale price swing** — i.e., the structural H/L of the whole wave move, not a single candle wick (post#1 SL rules verbatim, S11); ≤100-120 pips from EP on EURUSD (manual; Sonic M doc adds SL≥50 for sizing — S09). Kyaw's own rule: wide enough "for the price to breathe" (S13). VN sources add ≥80 pips for JPY pairs (S31 translation of the same doctrine).
- TP: a historic S&R level — whole/half numbers and mid-consolidation areas named explicitly (S10); TAH's practice adds RDH/RWH/range marks (S17).
- Management: trail behind structure; close any time; never average losers (Rules). Kyaw's claimed per-trade outcome range: "50 to 400+ pips on a trade" (post#1 verbatim — preserved via NLM cited_text of the S10 sonicr999 mirror; the saved S18 post#1 file no longer carries the rules list).

### 3.2 Re-entry (source-primary)

After a Classic is running, a pullback that does NOT kill the structure offers a new entry when "PA clears the most recent high or low" with no strong S&R just beyond (S10/S11). Seminar notes: re-enter after a confirming candle of the intended direction (S13). It is trade management/adding-to-winners — discretionary in size and timing.

### 3.3 Scout (source-primary, S08)

- Introduced 2012. TAH's updated definition (post 7679382, Aug-16-2014, full text recovered round 1B — `primary/ff_page3756_post7679382_scout_m5_20140816.txt`):
  - **Scout Before Classic**: PA ending a very strong directional run, or repeatedly bumping at S/R, **plus very high current volume** → raised odds of a reversal (or at least a nice pullback). Counter-trend entry amid momentum — "very much perception oriented"; the Dragon is NOT used to locate the EP (PA may already be through it). **Very high risk vs Classic**; wait for additional PA/confirmation.
  - **Scout During Classic** (≈ what was earlier called "re-entry"): adding to a running Classic during a retrace — optimum near the pullback's top/bottom; with PVSRA one may add during the retrace instead of waiting for PA to clear the previous high/low. **Adding while the Classic is red is NOT recommended** (that red spell may be an MM Stop Hunt — a separate Scout situation, still high risk). Safest form: Scout during a Classic that is in retrace **but remains green**.
  - sonicr999's own text gives the two accepted PA triggers: "(1) a suitable pattern of H/Ls, and (2) a break out from a consolidation area" (S10). TAH warns repeatedly: careful with scouts; the temptation to average losers via "PVSRA" is a trap (S10 rule 2, S17 Gupito).
  - **M5** (exact TAH wording, verified): "For scalping, or as an alternative for getting an earlier entry, you can try the M5 TF. Just remember that Classic entries are only recommend during the London session... And by dropping to the M5 and looking for setups, you won't be allowing the same time to see whether or not PA is actually transitioning from the MMs building to the MMs beginning a trend move." → **M5 is sanctioned for scalping/earlier entry, with an explicit confirmation-time caveat. It is NOT a sanctioned timeframe for the Classic setup itself** — "The M15 Classic setup in the London Session is the core of the Sonic R. System." (S08 verbatim)
- Seminar notes give a minimal form: high stopping volume + a strong candle of the intended direction (S13) — but this is a summary, not a full spec.

### 3.4 "Sonic entry" (seminar-era, source-primary S13)

Kyaw's Singapore seminars describe an aggressive variant: (1) high "stopping volume", (2) enter on a strong candle of the intended direction — essentially what became the Scout. Listed for completeness; the canonical trio is Classic / Re-entry / Scout.

### Cancel/invalidation conditions (source-primary + reconstructed)

- Strong S&R directly ahead of entry → stand aside (S15).
- Wrong session (Asia) → no Classic (S10/S15).
- Counter-trend Classic against an established trend → TAH's critique says wait for the retrace instead (S15).
- News imminent → not a formal veto in doctrine; treated as MM-volatility context (S04/S17). (reconstructed: the repo GOAL's hard news-avoid is stricter than source doctrine.)

### 3.5 Worked examples (chart narratives; attachments blocked → text only, no images)

**EX-1 Classic short, canonical manual example (source-primary, S11 post#1).** Pair unstated, M15 London. Price sat at an S&R area above the Dragon; wave formed H→L→LH with the start above the band; leg-1 pierced the Dragon downward (the "best if" case); a leg-3 candle closed back below the Dragon's lower edge. Entry: sell-stop "at least several pips" below that candle's low, checked for no strong S&R just beyond. SL: above the High of the recent large-scale swing, capped ≤100-120 pips from EP. TP: next historic S&R (whole/half number or mid-consolidation). Outcome: the manual uses it to illustrate SL placement rules; the trade "runs for profits" with the MM direction.

**EX-2 Classic short, TAH's own AUDJPY trade, 17 Aug 2014 (source-primary, S08 page-3756 post).** M15, opened in the ASIAN session — TAH explicitly: "The setup is nice, so I took it even though in the Asian session." Context read: Friday had strong shorting; the reset (pullback) came on declining volume = PVSRA sign the MMs remain bears; the day's high printed on the highest volume; then "a nice bear PA wave with the Dragon angled down and also below the Trend." Management plan stated live: target might not be reached before the London session; the LS might reset price higher as "the big Robber Banks look to add more shorts" → possibly remove SL and add a Scout later; possibly lower the target and hold for a bigger multi-day swing. Lesson: even TAH treats session as preference not veto; PVSRA supplies the direction/mode story; management is dynamic and discretionary.

**EX-3 Classic invalid — TAH coaching a student, page ~3387 (source-primary, S15).** EURUSD M15: the student's wave+session were correct but TAH rejected the trade because a resistance area sat "right in your lap" ahead of the entry and the higher trend was down — runway check failed. Lesson: "no strong S&R just beyond" is a hard practical veto, applied visually.

**EX-4 Re-entry / Scout-during-Classic (source-primary, S08/S10).** A running Classic in retrace that remains green: PA pulls back to/into the Dragon, a new minor 3-leg wave forms, and the add is placed near the pullback's top/bottom (or as PA clears the recent high/low with runway). With PVSRA one may add during the retrace rather than waiting for the breakout. Adding while the Classic is red = not recommended (possible Stop Hunt). Gupito's "Sneak Into Classic" pdf (S17, 21k downloads) walks this checklist stepwise.

**EX-5 Real outcomes posted by practitioners (source-primary, S08 page-3756).** Catcher777: "E/U trade closed 2.800 pips × 2 accounts" on an M15 Classic (15.08.14 chart). Patron: GBPAUD M15 long opened targeting 20-40 pips, closed early on resistance + double-bottom + weekend gap — discretionary management. santos23: "Classic short for Monday" chart. Lesson: real posted trades show both the swing targets (hundreds of pips) and discretionary early closes.

**EX-6 Scout Before Classic (source-primary, S08).** PA ending a strong run or repeatedly bumping at S/R with very high current volume → counter-trend Scout: entry on perception + confirmation PA, NOT on the Dragon (PA may already be through it). High risk; TAH's ordering: Scout-during-green-Classic < Scout-during-red-Classic < Scout-before-Classic in safety.

**EX-7 VN Classic narrative (community, S31/S33).** tamnhindautu's translated mechanics match the original exactly (leg-3 candle breaks the Dragon → entry vài pips outside, SL beyond nearest swing ≤100-120 pips, TP at historic S&R incl. mid-consolidation; JPY pairs SL ≥80 pips). VN worked example GBPJPY +140 pips (S33). The VN "rainbow-EMA" example (EURUSD H4: EMAs 6/12/18/24/30/36 + RSI14; entry 1.1225, SL 1.1200, TP 1.1300) is a **different system wearing the Sonic name** — see S6.

**EX-8 VN scalping worked trade — Lucy XAU (community, S53 video transcript via NLM-p3e).** XAUUSD; trend read H4/H1 up (price above the EMAs); execution M15/M5/M1. Price pulled back to retest the Dragon band; a rejection candle (pin/rút chân) printed at the band → Buy ~1933, SL 1930 just under the rejection wick, TP proactive before the local Elliott-5 completes. Outcome: price bounced hard off the band — won. Note this is the *rejection-scalp* variant (S6 family 3), NOT the canonical leg-3-close trigger — SL wick-based contradicts the TAH swing SL.

**EX-9 VN contamination example — "rainbow" EURUSD (community, flagged, S32 article §5.6; S59 = same article via dup URL).** EURUSD H4: 6 rainbow EMAs 6/12/18/24/30/36 + RSI14; day-1 EMA6/12 crossed up with RSI 55 → day-2 pullback to EMA18 → Buy 1.1225, SL 1.1200 under EMA36, TP 1.1300 (R:R 1:3), SL moved to breakeven at 1.1275. Outcome: TP hit +75 pips. **This recipe is not Sonic R** — no Dragon band, no wave, no S&R doctrine — it ships inside the same tamnhindautu article as an auxiliary method.

**EX-10 VN teacher mechanics — Nhật Hoài (community, S52 video transcript via NLM-p3c).** M15 (optimal; M10/M5 allowed, never below M5): wait for the FIRST pullback back to the Dragon band → enter when a candle closes fully outside the band. Two SL doctrines offered: tight beyond the pullback extreme (RR) or wide beyond the whole accumulation swing (winrate — ≈ TAH's rule). TP nearest S/R or trail behind new swings/pivots. This is the closest VN teacher form to canonical Classic minus PVSRA/WHQ.

Not recoverable: the attached chart images (FF attachment CDN is TLS-blocked for us); Kyaw's own earliest trade posts beyond post#1; the Mar-2014 Trade Levels revision. Say "not recoverable" rather than invent.

## S4. PVSRA deep-dive

- Definition (source-primary, S12/S18): joint analysis of Price, Volume, S&R. Premise: price movers ("MMs") habitually buy below key S&R (bulls) and sell above it (bears). Find WHERE they trade → infer whether they are bulls or bears; then infer whether they are position-building or running for profit. Trade only with the run-for-profit direction.
- Mode clues (source-primary, S12): bulls + price generally falling + most volume below key S&R/lows → position building; bulls + price rising + volume below key S&R on pullbacks → running for profit. Mirror for bears (selling above key S&R/highs). Swing amplitude context: price tends to move in 100+/150+/200+/250+ pip swings (VN translation of TAH text, S31).
- Exact PVA colouring (source-primary code, verified on BOTH the canonical `Sonic_2_PVA_Candles_White_20140317.mq4` lines 201-213 and the Suite Candles 509-529 / Volumes 313-332): climax = vol ≥ 2× mean(vol of prior 10 bars, excl. current) OR spread×vol ≥ max of prior 10; rising = vol ≥ 1.5× that mean. Climax rule heritage: BetterVolume_v1.4 (file line 41). 2011-gen differed (climax 20-bar incl. current; rising 1.38× incl. current — S39).
- Tick-volume caveat: MT4/5 FX volume = broker quote-tick activity, not traded volume; thread itself acknowledges every broker shows different volume (S16). TAH's workaround: relative spikes only, M1 for fine timing (S06). (source-primary + community)
- Position-building vs run-for-profits → the actual edge claim (source-primary, S06/S18): entering with the MM profit-run direction is "the secret" behind Classic profitability; entering during their building phase = trapped in chop. This is exactly where our deterministic reimplementations fell down (see S8).

## S5. Discipline & risk doctrine

- Rule 1 (source-primary): don't overtrade, don't trade Asian session; best setups at/after London open; **≤5 trades/week — stated as a general account-level recommendation in post#1's rules list, NOT scoped per-pair** (verbatim "You shouldn't trade more than 5 trades a week." — post#1 rules via NLM cited_text of S10 mirror; the saved S18 file lacks the rules list). Kyaw traded one primary pair (EURUSD preferred), so per-account ≈ per-pair in his practice; the multi-symbol era is later community habit.
- Rule 2 (source-primary): never add to a losing position — explicitly warned that Scout+PVSRA tempts averaging; don't (S10/S18).
- Rule 3 (source-primary): SL wide enough for price to breathe; ~100 pips on EURUSD, 100-120 manual cap; EURJPY variant notes "no SL but not more than 250" + strong opposite candle on weekly TE as exit (S13 seminar notes — treat the 250/no-SL as seminar shorthand, risky).
- Sonic M (source-primary, S09/S42): fixed-fractional sizing off SL≥50 pips; pip-value privacy convention (count pips, not lots).
- Trade posting discipline = teaching tool (post#1 rules, S18).
- News: panel = awareness; doctrine expects MM games around releases; not a hard avoid (S04/S17). GOAL conflict → S9.
- Weekend/overnight: source doctrine is silent on weekend-holding (swing system — examples hold multi-day); GOAL bans it → S9.

## S6. Variant & contamination map

| rule/element | TAH original | Traders Reality | VN community | our code | verdict |
|---|---|---|---|---|---|
| Dragon = EMA34 H/C/L | yes | yes (band) | yes (all recaps) | yes | agree |
| Trend = EMA89 close | yes | yes | yes | yes | agree |
| PVA 150%/200%/10-prior/sv-max | yes (code) | yes (identical) | mostly cited w/o numbers | yes | agree |
| Wave L-H-HL / H-L-LH + leg-3 break | yes | implicit | yes | reconstructed swing parser | mechanical mapping differs |
| London-session entry | yes (core) | session boxes | yes | session inputs | agree |
| ≤5 trades/wk; no averaging; wide SL | yes | not emphasised | yes | weekly cap implemented | agree |
| PVSRA = analysis not entry | yes | yes | yes | violated in some dead EAs | — |
| extra EMAs (200/610) | no | 5/13/50/200/800 set | yes (tamnhindautu/topsanfx) | no | community extension |
| Wyckoff phase colouring | no | vector zones adjacent | yes (CRTT) | no | community extension |
| QQE/CCI63/50SMA/Stealth LCD | pre-TAH era only (QQE/CCI/NVO were 2008-2011 stack) | no | rare | no | FSR "full version" = contamination (S30) |
| Elliott-wave justification | no (Kyaw credits Raghee) | no | claimed by topsanfx | no | contamination |

### Vietnamese variants concretely (community, verified vs VN sources — upgraded round 1C with teacher-video transcripts)

Round 1C added 6 captioned VN lesson videos + 2 pages to the notebook and queried them source-scoped (`nlm_raw/VN_p3_*.md`, citations with timestamps). Five distinct teacher families emerge — listed from most-faithful to least-faithful:

1. **tamnhindautu.org / Đăng Quang (S31/S32/S58/S59)** — still the closest written reference to TAH. Same wave counting (L-H-HL→HH / H-L-LH→LL), leg-3 candle breaking the Dragon band as trigger, re-entry at the "rào cản thứ 3" of the next pullback at the Dragon, M15 execution + H1/H4/D1 trend, PVSRA + WHQ kept as the advanced core ("PVSRA là một phương pháp phân tích, không phải là một phương pháp giao dịch" — same doctrine as TAH). Adds: EMA200/EMA610 as optional dynamic S/R context, an Elliott linkage for the 34/89 periods, SL ≥80 pips JPY, TP M30-prior-wave/mid-consolidation — AND its own extra recipe: a "chỉ báo cầu vồng" multi-TF method (6 EMAs 6-36 + RSI14, H4) embedded in the same article — i.e., the contamination example lives inside the faithful translation. Fidelity: **high on the Sonic core; the article also teaches non-Sonic recipes — separate them**.
2. **Nhật Hoài Trader (S52 — the traderviet translator's own lesson, "Scalping Khung 15 Phút")** — closest VN *teacher* to TAH mechanics: first pullback back to the Dragon band → entry when a candle **closes fully outside** the band (= leg-3 trigger, faithful). Two documented SL styles: tight beyond the pullback extreme (for RR) vs wide beyond the whole accumulation swing (for winrate) — the wide style ≈ TAH's large-swing SL. TP at nearest S/R or trail behind new swings + **Pivot Points** (red dots — his addition). TF: M15 optimal, M10/M5 acceptable, *"không có nên đi xuống thấp hơn khung M5"* — matches the TAH M5 boundary. Fidelity: **high-medium; scalping flavour, pivot overlay, no PVSRA/WHQ in the video**.
3. **Lucy / Học Đầu Tư Forex (S53/S54)** — HTF-trend + LTF rejection scalping: trend from H4/H1; entries on **M15/M5/M1** (M5 "hiệu quả và an toàn nhất", M1 = "say sóng"). Entry trigger = **rejection candle (Pin/Doji/engulfing) at the Dragon band or EMA89** — replaces the leg-3 close. SL under the rejection-candle wick (far tighter than TAH's swing SL). TP proactive at nearest old high/low or before Elliott wave-5 completes (Elliott overlay). Worked XAU scalp: buy ~1933 at Dragon retest, SL 1930, won (S53). Fidelity: **medium-low — same ingredients, different trigger/SL/exit doctrine; no PVSRA/WHQ**.
4. **TRADERPTKT / Bài 14 (S55)** — EMA-bounce system wearing Sonic clothes: adds EMA200 (pink) + EMA610 (silver) as moving S/R, compares the EMA34 band to the Ichimoku Kumo, mixes SMC/BOS vocabulary, allows counter-trend entries at strong resistance, entry on band touch/breakout ± engulfing confirm. **SL beyond the band (not the swing); TP = fixed 2R** — both directly contradict TAH (SL beyond large swing, TP at historic S/R). Fidelity: **low — recognisably a different method with the same indicator**.
5. **Chỉ Báo SONIC R channel + Stoch/BB teacher (S56 Sell-thuận / S57 StochRSI-BB — two different videos, keep separate)** — S56 teaches EMA200+610 stacking for "rất mạnh" trends AND **averaging sells into MA touches** (normalized transcript quote: *"giá kéo lên chạm vào các đường này thì bạn cứ thế mà nhồi lệnh Sell"* — auto-caption garbled, meaning verified across citations 10/29/31 in `nlm_raw/VN_p3_b/e`) — directly violating TAH rule 2 (never add to losers). S57 adds Stoch RSI + Bollinger Bands + EMA200/610 stack, SL at old highs + partial TP — no averaging shown. Fidelity: **contamination — flag, do not port**.
- Older written references: **topsanfx (S35)** — same EMA200/610 stacking + Elliott justification + pullback-to-EMA entries (medium fidelity). **giaodichtaichinh (S36)** — EMA200 + pin/engulfing + ADX/BB + top-down D/H4→M15 + the same rainbow recipe (low-medium). **traderviet forum (S33)** — practitioner mechanics, GBPJPY +140p example, closest textual usage.
- Not usable: zoom "Buổi 1 Sonic R nâng cao" and "Sonic R + Elliott ứng dụng" videos are login-walled; "Team hv Sonic R + Elliott + Fibo + Pitago" failed NLM ingest ×2 — Elliott-heavy VN variant exists but is only thinly documented here.
- **Which variant is the Owner most likely using? (hypothesis, updated)** Same answer as round 1B — repo code matches the **TAH-canonical line** (no EMA200/610/RSI anywhere), i.e., families 1-2 (tamnhindautu / Nhật Hoài). If the Owner learned from videos, families 3-4 (Lucy rejection-scalp / TRADERPTKT EMA-bounce) are the likely alternatives — concrete menu in S11.

## S7. Machine-readiness matrix

| rule | mechanical? | causal definition available | source-given vs reconstructed |
|---|---|---|---|
| Dragon/Trend values | yes | EMA34 H/C/L, EMA89 C — closed bars | source-given |
| PVA classification | yes | §3 code — closed bars causal | source-given (Suite gen) |
| WHQ grid | yes | code — fixed levels | source-given |
| session permission | yes | clock vLines; broker-TZ | source-given times, reconstructed in our code |
| wave shape L-H-HL | **partly** | needs a swing parser (fractal/ZZ/ATR legs) — no source spec for leg sizes | reconstructed |
| "leg-1 crosses Dragon" | yes once wave parsed | swing high/low vs band | reconstructed via parser |
| "leg-3 candle breaks out" | yes | close beyond EMA34 edge | near-mechanical |
| S&R "at an area" | partly | distance-to-level in pips/ATR | reconstructed threshold |
| "no strong S&R just beyond" (runway) | partly | distance to next grid/swing level | reconstructed threshold |
| volume validation ("a bit of Volume") | partly | climax/rising flag at or near the wave low/high (PVA code exists; the "where it matters" mapping is ours) | PVA classification source-given; its role in Classic validation reconstructed |
| trend confirmation | yes | price vs EMA89 | source-given |
| SL beyond large swing + cap | partly | swing identification + 100-120 cap | cap source-given, swing reconstructed |
| TP at historic S&R | partly | next WHQ/swing/consolidation level | reconstructed selection |
| PVSRA bull/bear mode | **discretionary** | "most of their trading above/below key S&R" over N bars — needs a statistical mapping | reconstructed (unproven) |
| position-build vs profit-run | **discretionary** | trend state × volume-side — no mechanical spec | reconstructed (unproven) |
| ≤5 trades/week, no averaging | yes | counters | source-given |
| Scout entry | **discretionary** | "PA hints" — no spec | not codable faithfully |
| news handling | doctrine = context, not gate | GOAL = gate | policy decision, not source |

## S8. Reconciliation with our history — the attempts × Classic-elements matrix

The original Classic elements (columns) are the source-verified rules from S3: **W1** wave shape L-H-HL / H-L-LH; **W2** wave starts at an S&R area; **W3** leg-1 pierces the Dragon; **W4** Dragon angle (visual); **W5** Trend side; **W6** leg-3 close beyond the Dragon; **E1** stop order several pips beyond signal candle; **R1** SL beyond the large swing with ~100-120 pip cap; **R2** TP at historic S&R; **S1** London session; **D1** ≤5 trades/week + no averaging to losers. Cell: `P` present / `~` approximated / `-` missing / `X` contradicted.

### The attempts (all numbers local-empirical with file cites)

| # | attempt (window) | object actually tested | result | fate |
|---|---|---|---|---|
| A | S360 Dragon bounce/breakout (`EA_SonicR` v1.1, 2026-07) | M15 Dragon-channel touch/break entries + Trend filter, London/NY | EURUSD bounce PF 0.98, breakout 0.58, USDJPY 0.27, GBPUSD 0.45; XAU ~no trades (`20260816_SONICR_PVSRA_RESEARCH_PACKET.md` §7.1, STRATEGY_LOG S360) | killed — Dragon proximity alone has no next-bar edge |
| B | ITSM 5-13-34-89 EMA-stack pullback (S506-S702) | EMA-zone pullback family, per-symbol sweeps | S506-S508 GBP/EUR/XAU PF 0.62-0.99; USDJPY children = `KILL_NO_REVIVAL` (`20260812_ITSM_SONIC_USDJPY_REVIVAL_AUDIT.md`); S701 EUR PF 0.895, S702 XAU 0.84 (packet §7.2) | killed — pair-specific curve-fit, not Sonic |
| C | archive `EA_SonicR` XAU + AutoSleeve (runs `20260701_*`, `20260705_*`) | ~50-input regime-router EA: Dragon-touch CLASSIC / CLASSIC_ARM / DRAGON_PB / REVERSAL routes + XAU sleeves + news-CSV hard-bind (`Include/SNR_Signals.mqh` touch_idx logic; `SNR_Opportunity.mqh` HTF score) | XAU 2024-25 PF **1.41** (127 trades), 2021-25 PF **1.16** (335), all `InpUseAutoSleeveConfig=true` (`20260813_..._FRONTIER.md` lines 43-46); XAU M5 2024-25 seeds PF 1.32-1.78 but 2019-25 PF **0.952** on 492 trades, SIDEWAY_WIDE = main loss pocket (Owner Drive README-SONIC R via Lead — Lead-brief class, not locally archived) | **parked to `00. Old File` 31/08, not killed**; exact re-run blocked — `SNR_FX_EVENTS.csv` (hash b62eab34…) absent (frontier lines 76-86) |
| D | Grok SonicR v10 (delegated, 2026-08-04→12) | H1 yfinance EA, fail-open HTF read, Dragon buffer OOB, unscoped deals | audit verdict `NOT_A_CANDIDATE_ENGINEERING_DONOR_ONLY` (`20260812_GROK_SONICR_V10_LOCAL_AUDIT.md`); recovery `ORIGINAL_EVIDENCE_INCOMPLETE` — walk-forward fold assignments + OOS ledgers don't exist (`20260813_GROK_SONICR_V10_ORIGINAL_EVIDENCE_RECOVERY.md`) | rejected as candidate; donor-only plumbing |
| E | May-2026 Scanner-Candidate Alignment | archive scanner candidates vs subsequent direction | **262 scanner candidates → 0 directional alignments within 6 bars; LONG_CONTEXT_FAIL dominant** (Lead brief; ledger itself lost in 31/08 cleanup — unverifiable-first-party) | scanner labels carried no forward information |
| F | EUR London Classic V1 | first direct Classic route attempt | 49,558 signals / **0 trades** (route-scope bug); fixed → **2 trades / 2 years** — killed by prereg as too sparse (packet §7.3; PF figure not preserved in packet) | killed — cadence ~0 |
| G | EUR density batch | three screens, not "level density": actual M5 T1 route / M15 no-PVSRA / M15 source-core Classic | M5 T1 **PF 0.505** (4 trades per Lead brief — packet records PF only); M15 no-PVSRA **2 trades**; M15 source-core **14 trades PF 1.28**; `trap_risk` + `late_chase` labels net **positive** → cannot be vetoes (packet §7.3) | killed — cadence/edge fail |
| H | Hybrid ICT-Sonic (`EA_HybridICT_Sonic`) | AND-stack: H4 BOS/FVG/liq + M15 wave + Dragon + tick climax + session | **N=0 for years**; diagnostic with Dragon ±40 floor OFF still **1505/1508 SL-cap fails**; terminal `HYP-HIS-SL-SIGATR-M15-EUR-001` PF 0.98 at ~0.22 trades/wk (packet §7.4) | killed — AND-stacking suffocates the signal |
| I | 12/08 Classic-wave PVA-pullback draft | PVA-gated pullback design (never ran) | `REJECT_PRE_SOURCE_DEDUP_FAIL` — same Dragon/Trend/PVA family, tick_volume≠volume, ambiguous indexing (`20260812_SONICR_CLASSIC_WAVE_PRE_SOURCE_DESIGN.md`) | rejected pre-registration — PVA as entry gate is a doctrinal error |
| J | 16/08 Classic geometry `20260816_205426` | `ClassicWaveLeg3DragonBreak` Model-0 — the most faithful mechanical Classic ever run here (spec: packet §6.1-6.5) | EURUSD M15 London: **N=307, PF 0.94** → `KILL hẹp` (`20260816_SONICR_CONTEXT_QUANT_TEAM_FREEZE.md` lines 9,41: no context gates on this object) | narrowly killed — faithful geometry still failed PF |

### Fidelity matrix (file:line = the packet spec where coded)

| attempt | W1 | W2 | W3 | W4 | W5 | W6 | E1 | R1 | R2 | S1 | D1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A S360 bounce/break | - | - | - | - | P | - | - | - | - | P | - |
| B ITSM 5-13-34-89 | - | - | - | - | P | - | - | ~ | - | ~ | - |
| C archive EA_SonicR | ~ (touch, not 3-leg parser — `SNR_Signals.mqh` 254/334) | ~ (SMC/static swing) | - | ~ | P | ~ (touch/break routes) | - | ~ | ~ (targets per route) | P | ~ (sleeve caps) |
| D Grok v10 | - | - | - | - | ~ (fail-open HTF) | ~ | - | - | - | - | - |
| F EUR London V1 | ~ | ~ | ~ | ~ | P | P | ~ | ~ | ~ | P | ~ |
| G density source-core | ~ | ~ | - | - | P | P | ~ | ~ | ~ | P | ~ |
| H Hybrid ICT-Sonic | ~ | ~ | ~ | ~ | P | P | ~ | X (SL-cap floor ±40 contradicts wide swing SL) | - | P | - |
| J 16/08 Model-0 | P (fractal-2 parser, §6.3 L390-391) | ~ (within w pips of WHQ/swing, w=0.25·ATR recon, L405) | ~ (flag only, not a gate, L392) | ~ (`dragon_mid` slope over 3 bars, L397) | P (soft bias, L396-398) | P (L393-395) | P (3 pips recon, L414) | ~ (beyond leg-1 extreme +0.10·ATR, cap 120, L416) | ~ (next WHQ ≥15 pips or 1.5R, L417 — WHQ ≠ historic S/R) | P (London 08-16, L419) | P (cap 5, no adds, L418/420/447) |

(E scanner-alignment and I draft had no tradeable object → not matrixed.)

Answer plainly: **No — the original Classic has never been tested faithfully, and the closest attempt failed.** Run J coded W1/W5/W6/E1/S1/D1 faithfully but still approximated W2 (zone → pip distance to a reconstructed 25-pip WHQ grid, not "an S&R area"), W3 (quality flag, not required), W4 (3-bar slope proxy, not the visual angle), R1 (leg-1 extreme, not "the large-scale swing"), R2 (WHQ grid, not historic S/R). J reached PF 0.94 on N=307 — so either (a) the missing discretionary elements (wave quality judgment, PVSRA mode, runway feel) carry the edge, or (b) the mechanical core has no edge at all. Every earlier attempt removed strictly more elements AND added non-source gates. Distinguishing (a) vs (b) is THE open question for any future Sonic lane — and it can only be answered by testing the missing elements one at a time on a scanner, never by re-running J with more gates (J is `KILL hẹp`). (local-empirical + hypothesis)

## S9. Conflict with GOAL

GOAL: 10-40 trades/week/symbol, PF>1.30 after costs, scalping, no weekend, news-avoid, limited overnight.
Doctrine: M15 swing entries in London session, ≤5 trades/week total (not per symbol), 100-pip-scale SLs, 50-400+ pip targets, multi-hour-to-multi-day holds; news = watched MM event, not a ban. (source-primary, S10/S13)
Quantified: doctrine cadence ≈1 trade/day max across the board vs GOAL 2-8/day/symbol — **a 10-50× cadence gap**; typical Sonic trade duration ≫ intraday scalping; Sonic explicitly tolerates overnight holds (examples S16/S17 show multi-day); weekend silence in sources.
Options (no decision — for Lead/Owner):
1. Multi-symbol sleeves — keep M15 London Classic per-symbol; cadence per symbol stays ≤~2-3/wk even across 5+ symbols. Fails per-symbol GOAL cadence but preserves fidelity. (hypothesis)
2. Lower-TF execution — TAH: "For scalping, or as an alternative for getting an earlier entry, you can try the M5 TF" with the caveat that M5 forfeits the time to see the MM build→run transition (S08 verbatim). An M5 London-session variant could reach ~5-10/wk/symbol; it is source-sanctioned for scalping/earlier entry but NOT for the Classic setup itself, whose stated core is M15. (source-primary + hypothesis)
3. Classic + Re-entry + Scout — bundling all three setups raises count; Scouts are explicitly higher-risk/discretionary. (source-primary + hypothesis)
4. Sonic as context/scanner layer for another trigger — e.g., Dragon-trend+PVSRA regime label feeding a different entry mechanism. Diverges from "trade the Classic" but uses the stack causally. (hypothesis)
5. Alert/assistant mode — EA detects Classic candidates + PVSRA state and alerts a human; zero-automation doctrine risk, full fidelity. Matches Owner's possible actual need. (hypothesis)
6. Abandon Sonic as the GOAL vehicle; keep it as research. (option of last resort)

## S10. New angles not yet tried — ranked by expected value × fidelity

1. **Volman-style S&R ZONES for the "wave at S&R" + runway checks** — replace hard-line WHQ/swing levels with zone objects (our price-action perception engine). Why: sources themselves say "areas of S&R", significance-ordered; zones match doctrine better than lines and fix the "resistance in your lap" veto mechanically. Causal def: zone = recent N-swing overlap region; event = leg-3 Dragon break within x·ATR of zone edge; runway = distance to next opposing zone ≥ k·ATR. Sources: S10/S12/S15. Cheapest falsification: outcome-blind event study — count setups/week/symbol, both directions; kill if <2 events/wk EURUSD M15 London or runway distribution degenerate. (hypothesis)
2. **A proper wave parser for leg-1/leg-3 geometry** — fractal or ATR-scaled zigzag on closed bars; encode L-H-HL + leg-1-pierce + leg-3-close-beyond-Dragon exactly. Why: the ONLY mechanical piece of Classic we never coded faithfully; every prior attempt substituted EMA logic. Falsification: replay parser on 2014-2016 EURUSD, count qualifying waves/session; kill if <3/wk or if triggered bars don't visually match manual wave reads on a 100-chart sample. (reconstructed)
3. **HTF context + LTF execution** — H1 PVSRA regime (MM direction/build-vs-run proxy: where volume clusters vs key S&R over rolling N) gates M5/M15 Dragon-break entries in London. Why: TAH explicitly pairs H1 bias with M15 entry (S15 "look at the H1 chart, then the PVSRA chart"), and M5 entries are sanctioned (S08); cadence rises without new indicators. Falsification: label-only probe — measure agreement between the H1 proxy and subsequent M15 Classic outcomes; kill if direction-agreement <55% or regime labels unstable intraday. (hypothesis)
4. **Symbol-specific level grids (XAU first)** — the WHQ grid is pip-defined via `Poin = Point*10` (Access-Panel.mq4 line 713). **Code-derived XAU behaviour, no longer a guess:** on a 2-digit gold quote (Digits=2, Point=0.01) the SAME indicator draws quarter levels **$2.50** apart (half $5.00, whole $10.00) — i.e., the earlier "$2.50/$5 zones" suggestion is exactly what TAH's own code paints on standard gold feeds. On a 3-digit feed (Point=0.001) it draws $0.25 apart unless `__Incr_Decr_Levels_Density` is raised (density=9 reproduces the 2-digit grid). Open design question remaining: whether gold's *psychological* grid should follow $10 wholes at all — XAU swing amplitudes dwarf FX (source swings were quoted for EURUSD); candidates: keep code-exact $2.50/$5/$10, or scale to ATR. Falsification: map XAU swing H/L to the code-exact grid; kill if <60% of significant swings terminate within ±0.3 ATR of a grid line. (hypothesis; derivation source-primary code)
5. **PVSRA regime label as a *filter-state*, not a gate** — compute a closed-bar scalar "MM direction confidence" (fraction of recent climax/rising volume occurring below-vs-above nearest key S&R) and test whether conditioning the 16/08 Classic geometry on regime≥threshold recovers PF>1. Why: it's the missing discretionary layer, made measurable without changing entries. Falsification: distribution test — does regime score separate subsequent +50pip vs −50pip moves? kill if KS test p>0.05 or monotone lift absent. (reconstructed)
6. **Traders Reality vector-candle "unrecovered liquidity" zones** — mark last climax-candle origin zones; test price-return probability. Why: TR's main claimed edge-extension; gives a concrete TP/magnet object our stack lacks. Falsification: fill-rate of zones within N bars vs random baseline; kill if lift <10%. (community + hypothesis)
7. **Alert/assistant EA (human-in-loop)** — full faithful detection, Telegram/chart alert, human executes. Not a PF play — a fidelity play that produces labeled data for later automation. Falsification: N/A for edge; kill if alert precision <50% on manual review of 50 alerts. (hypothesis)

Rank order rationale: 1+2 are the missing mechanical fidelity; 5 converts the discretionary edge claim into a falsifiable scalar; 3 raises cadence within doctrine; 4 unblocks XAU; 6-7 are cheaper side-quests. (hypothesis)

## S11. Open questions for the Owner (≤5)

1. Anh học Sonic R từ nguồn nào? Menu cụ thể sau round 1C (anh chỉ cần chọn một dòng): (a) thread FF gốc/tamnhindautu — chuẩn TAH; (b) Nhật Hoài scalping M15 — chuẩn cơ chế, thêm pivot, không PVSRA; (c) Lucy rejection-scalp H4→M5/M1 — entry bằng nến từ chối, SL dưới râu nến; (d) TRADERPTKT/Bài-14 EMA-bounce + EMA200/610, SL qua band, TP 2R; (e) kênh Chỉ-Báo-SONIC-R StochRSI/BB + nhồi lệnh (nhiễm). Evidence: repo mình khớp (a)/(b); nếu anh quen (c)/(d) em sẽ map trigger/SL/TP khác hẳn — quan trọng để hỏi trước khi build.
2. Anh kỳ vọng EA trade symbol/timeframe nào — chỉ XAUUSD M15, hay cả FX majors, và có chấp nhận M5 scalping entries (TAH-allowed, cảnh báo mất thời gian xác nhận)?
3. Cadence: chấp nhận ~2-5 lệnh/tuần/symbol đúng-chuẩn Sonic (post#1 cap = per-account, Kyaw chủ yếu trade 1 pair), hay bắt buộc 10-40 như GOAL hiện tại (→ buộc phải biến thể)?
4. News: giữ hard-avoid của GOAL, hay theo doctrine gốc (TAH chỉ theo dõi MM-games quanh news, không cấm)?
5. Nếu mechanical Classic thật sự không có edge, anh muốn: Sonic-as-scanner cảnh báo cho người trade, hay đóng hẳn lane Sonic?

## S12. Tóm tắt cho anh (10 dòng)

1. Sonic R là hệ swing M15 của Kyaw Trader (2008), được TAH phát triển thành bộ indicator + giáo lý PVSRA — trade sóng giá tại vùng hỗ trợ/kháng cự, vào lệnh theo Dragon (EMA34 high/close/low), xác nhận bằng Trend (EMA89).
2. Setup chính là "Classic": sóng L-H-HL (mua) hoặc H-L-LH (bán) ở vùng S&R, nến chân-sóng-3 đóng cửa thoát khỏi Dragon, đặt stop-order vài pip ngoài nến đó; SL ngoài swing lớn (≤100-120 pip EURUSD), TP về S&R lịch sử.
3. PVA/PVSRA không phải tín hiệu vào lệnh — nó là cách "đọc" market maker: nến climax (vol≥2× trung bình 10 nến hoặc spread×vol lớn nhất 10 nến) và rising (≥1.5×) cho biết cá mập đang mua/bán ở đâu so với S&R.
4. Con số PVA 150%/200%/10-nến/spread×volume là chính xác từ code TAH (đã đọc file gốc) — packet cũ ghi "reconstructed" là sai; bản 2011 cũ hơn dùng tham số khác (20-nến, hệ số 1.38).
5. Lưới whole/half/quarter trong Access Panel vẽ mức 00/25/50/75 cách nhau 25 pip (có chỉnh density; quarter chỉ hiện ≤M30) — code mình đang vẽ lưới 10/5/2.5 pip, tức là KHÔNG giống bản gốc.
6. Ba quy tắc kỷ luật gốc: ≤5 lệnh/tuần (không trade phiên Á), không nhồi lệnh lỗ, SL phải đủ rộng — nghĩa là Sonic gốc không thể đạt mục tiêu 10-40 lệnh/tuần/symbol của GOAL.
7. News: hệ gốc chỉ "theo dõi" tin để đọc ý đồ cá mập (panel FFCal), không cấm trade quanh tin — khác với hard-avoid của GOAL mình.
8. Mười lần thử trước đây đều chưa test đúng bản gốc — ma trận S8 (10 attempts × 11 yếu-tố-Classic) cho thấy run 16/08 (N=307, PF 0.94) là gần nhất: đúng 6/11 yếu tố, 5/11 còn xấp xỉ (sóng-tại-S&R, chân-1-xuyên-Dragon, góc Dragon, SL-swing-lớn, TP-S&R-lịch-sử); archive EA_SonicR XAU (PF 1.41/127 lệnh 2024-25) bị PARK vào kho 31/08 chứ không bị kill — chạy lại đúng-object bị chặn vì thiếu file SNR_FX_EVENTS.csv.
9. Hướng mới đáng thử nhất: S&R-zone kiểu Volman cho "wave at S&R" + parser sóng chuẩn cho leg-1/leg-3 + nhãn regime PVSRA đo được (không phải cổng) — cả ba đều falsification-test được trước khi build.
10. Notebook "Sonic R System" (8490421d): 31 source entries (20 READY/usable, gồm 6 video VN round 1C), 17 câu hỏi đã dùng (6 nhóm round 1 + 6 gap-queries round 1B + 5 pass-3 VN, raw trong nlm_raw/); briefing report + data table + audio tiếng Việt đã render xong — anh mở notebook xem được ngay; mind map lỗi INVALID_ARGUMENT đã bỏ. 5 câu hỏi S11 chờ anh chốt hướng lane build.
