# INDICATORS.md — Sonic R indicator catalogue, code-verified

Scope: every indicator in the TAH Sonic R template lineage (2011 → Feb-2014 build-600 set → Mar-2014 `Sonic_1..6` set → 2015 "Suite" generation), plus the most-used later ports and our own MT5 `SNR_*` port fidelity.

Sources cited by id per `SOURCES.csv`. File:line references point to files in `primary/` (this folder) unless noted.

---

## 0. Template inventory (what actually loads on the chart)

From the 2014 release post (S06/S41) and the canonical Mar-2014 zip manifest (S38):

| slot | 2013 name (post 7281738, Feb-2014) | 2014 name (`TAH 03-17-2014 Revised`) | 2015 successor |
|---|---|---|---|
| 1 | SonicR_Filled_Dragon_White.mq4 | Sonic_1 Solid Dragon (White|Black).mq4 | — (Solid Dragon-Trend lineage) |
| 2 | SonicR_PVA_Candles_White.mq4 | Sonic_2 PVA Candles | Candles Suite.mq4 |
| 3 | SonicR_Trade_Levels_White.mq4 | Sonic_3 Trade Levels | Trade Levels (revised) |
| 4 | SonicR_Control_Panel_White.mq4 | Sonic_4 Access Panel | Access Panel.mq4 |
| 5 | SonicR_FFCal_Panel_White.mq4 | Sonic_5 FFCal Panel | FFCal Panel.mq4 |
| 6 | SonicR_PVA_Volumes_White.mq4 | Sonic_6 PVA Volumes | Volumes Suite.mq4 |
| tpl | sonicr_2013_white.tpl | 2014 sonicr (white|black).tpl | — |

Earlier lineage (source-primary, TAH post history via S10): Chart Panel + Clock Panel → Control Panel (2012) → Access Panel (2014); TRO_Tunnel_Dragon (Kyaw era) → Line Dragon-Trend + Solid Dragon-Trend (2012) → Filled Dragon (2013) → Solid Dragon (2014); VSA Candlesticks (2012) → PVA Candles (2013) → Candles Suite (2015); VSA Histogram → PVA Volumes → Volumes Suite. FFCal Panel derives from derkwehler's FFCal_v20 (FFCal-Panel.mq4 lines 72-85). The pre-TAH Kyaw stack also used QQE_Alert_MTF_v5, Sonic CCI 63, Normalized_Volume_Oscillator, PivotsDWM, SpudFibo, ZZ-Fractal, TRO_Tunnel_Dragon (S27, ymcn SonicRV3 manifest via S38) — this is a legitimately older Sonic R variant, not contamination.

---

## 1. Sonic_1 Solid Dragon / Filled Dragon / "Dragon-Trend"

- Author/version: traderathome (with "Fish"/qFish), 2012-2014, MT4. **Recovered and hash-verified this lane**: `primary/drive/SonicR_Filled_Dragon_White.mq4` (272 lines, release 05-25-2013, SHA256 prefix `fbb09c411f0841e5` = matches the May quarantine manifest for FF attachment 1369134, the Feb-2014 build-600 set). The Mar-2014 `Sonic_1 Solid Dragon` file itself still not recovered, but it is the same Dragon-Trend lineage.
- Role (source-primary): "draws the Sonic R. System Dragon on the chart. It includes the option to show our Trend line" (S06, release post). Kyaw's own seminar definition: "Using EMA 34 high low close as dragon" (S13).
- Exact definition (source-primary, `SonicR_Filled_Dragon_White.mq4` code, lines 251-262): three EMA34s — `iMA(NULL,NULL,34,0,EMA,PRICE_HIGH)`, `…PRICE_LOW`, `…PRICE_CLOSE` — forming a filled band plus a center line; plus `iMA(NULL,NULL,89,0,EMA,PRICE_CLOSE)` as the Trend. Buffer layout in THIS file (lines 173-195): 0=DragonHigh histo fill, 1=DragonLow histo fill, 2=DragonTop line (EMA34H), 3=DragonBot line (EMA34L), 4=DragonCntrArea (EMA34C, wide backdrop), 5=DragonCntrLine (EMA34C), **6=Trend1 (EMA89C), 7=Trend2 (EMA89C)**.
- Periods are HARDCODED, not inputs: `Dragon_Period=34`, `Dragon_Type=1` (EMA), `Trend_Period=89`, `Trend_Type=1` (lines 129-138). Only externs: `Indicator_On`, `Chart_Zoom_123456` (default 3), `Trend_On`, `Display_Max_TF=43200` (lines 115-119).
- NO slope/angle is computed anywhere in the file — the Dragon "angle" traders quote is purely a visual read (confirmed by code inspection; Lead note 2 concurs).
- Cross-TF display was REMOVED in this version (change log line 61: "Removed ability to show M15 Dragon-Trend configurations on other TF charts") — it computes on the chart's own TF only.
- Zoom slave system (source-primary, lines 36-44, 156-169): `Chart_Zoom_123456`→`Bar_Width`/`Bands` tables drive the fill widths and are broadcast via GlobalVariables `Zoom_Setting`/`Bar_Setting` so PVA Candles, PVA Volumes, and the Control Panel's special Bid Line/Dot all follow the one setting.
- Colours (defaults white chart, lines 67-74 + properties): H/L histo fill `C'221,238,255'`; H/L MA fill `C'210,233,255'`; center highlighter `C'240,249,255'` width 5; center line `C'032,143,255'`; Trend highlighter CLR_NONE; Trend line Black (MediumVioletRed on black chart).
- "Solid" vs "Filled" vs "Line": Solid Dragon-Trend was released 05-01-2012 (line 56) → Filled Dragon 05-25-2013 (this file) → Sonic_1 Solid Dragon in the Mar-2014 set. Line Dragon-Trend draws the same lines unfilled.
- Third-party buffer-map caveat: the iCustom map reported in S26 (buf 0=high, 1=low, 4=mid, 5=trend) came from an EA calling `SonicR Solid Dragon-Trend (White)` — a DIFFERENT file than this Filled Dragon (where Trend sits on buffers 6/7). Treat the S26 map as Solid-Dragon-specific and unverified; do not mix the two layouts.
- Trader use (source-primary): Dragon = "used for picking the trade entry" — its angle (up/down) and position vs price define direction permission; a wave leg-3 candle breaking out of the Dragon is the Classic trigger (S10/S11). Trend = "market bias indicator... best if PA is above it for longs and below it for shorts" (S10/S11).
- Local fidelity — `Indicators/SNR_Dragon.mq5`: EMA34 H/C/L via iMA handles, 3 line plots (SeaGreen/Goldenrod/IndianRed) — formula MATCH; presentation DIVERGES (no filled band, no embedded Trend — split into SNR_Trend.mq5). `SNR_Trend.mq5`: EMA89 close, slope-colored over `InpSlopeBars=3` — formula MATCH; the slope-colouring lookback is a local choice (TAH's exact slope rule unrecovered — mark reconstructed).

## 2. Trend (EMA89)

- Same indicator family as above (buffer 5 in Solid Dragon-Trend); the VN community and ports treat it standalone. Definition: EMA89 of close (S13/S24/S26).
- Reading: bias line. Post-2013 doctrine adds the Dragon-vs-Trend relative position (89EMA above/below/inside the Dragon band) as a trend-quality read (S29 recap; TAH chart comments S15).
- Local fidelity — `SNR_Trend.mq5`: MATCH on formula; slope colour 3-bar lookback reconstructed.

## 3. Sonic_2 PVA Candles / Candles Suite — **the PVA verdict**

- Author/version: traderathome + qFish; PVA Candles (2013) → Sonic_2 PVA Candles (2014) → Candles Suite. Dating reconciliation: TAH personally announced the Candles/Volumes "Suite" as the direct replacement for Sonic_2/Sonic_6 in **May-2014** (S16, post 72,242, thread page 3613); the recovered file's header is dated 05-30-**2015** (line 79) — i.e., our copy is a 2015 revision of the 2014-announced Suite, not a separate generation.
- Exact algorithm (source-primary, `primary/Candles-Suite.mq4`):
  - For each bar `i`: `av = mean(Volume[i+1..i+10])` — the 10 bars BEFORE bar i, excluding bar i (lines 509-510).
  - `Value2 = Volume[i] * (High[i]-Low[i])` — spread×volume of bar i (line 514).
  - `HiValue2 = max over j=i+1..i+10 of Volume[j]*(High[j]-Low[j])` (lines 516-520).
  - **Climax** if `Value2 >= HiValue2` OR `Volume[i] >= av*2` (line 521).
  - **Rising** (only when not climax and rising display enabled) if `Volume[i] >= av*1.5` (lines 524-529).
  - User notes restate the same in prose: climax = "volume >= 200% of the average volume of the 10 previous chart TFs" OR spread×vol highest of the 10 previous; rising = ">= 150%" (lines 21-29).
- Colours (defaults, file lines 85-96 + externs): Bull Climax green `C'000,166,100'` (white chart) / `C'031,192,071'` (black); Bear Climax red `C'214,012,083'` / `C'224,001,006'`; Bull Rising blue `C'067,100,214'` / `C'017,136,255'`; Bear Rising blue-violet `C'154,038,232'` / `C'173,051,255'`. Normal candles keep standard bull/bear greys. Three colour schemes (Simple 2-colour climax-only, Standard 4-colour, Default hardcoded traditional) via `__PVA_Color_Simple_Standard_Default_123` (lines 121-140).
- Inputs: `__PVA_BAR_STD_HA_1234` (1=PVA,2=bars,3=candles,4=Heikin-Ashi modified to show gaps), `__PVA_Bars_Candles_Bodies_123` (PVA display style), `__PVA_Color_Simple_Standard_Default_123`, `__Include_Rising_Volume`, `__Simple_*`/`__Standard_*` colour externs, alert inputs `Show_Alert_Label`, `Alert_On`, `Broker_Name_In_Alert`, `Non_PVA_*` for non-PVA styles (lines 116-168).
- Alert: fires once per TF at the first moment the live bar qualifies as Climax (`i==0`, lines 538-542) — i.e., the alert can trigger intra-bar before close.
- Repaint behaviour: the PVA classification of a CLOSED bar never changes (all inputs are that bar's own volume/range vs prior 10 closed bars — causal, zero lookahead). The live bar 0 can flip in/out of climax as its volume accrues — same as any volume indicator.
- What it is FOR (source-primary): colours flag "notable volume" events so the trader can do PVSRA — judge whether MMs are buying below key S&R or selling above it, position-building vs running for profit (S06, S12). It is an analysis aid, NOT an entry trigger (S18: "PVSRA is a method of analysis, not a trade entry method").
- **PVA threshold contradiction — SETTLED ON THE CANONICAL FILE**: the 16/08 packet called 150%/200%/10-bar/spread×vol "reconstructed, not TAH". Now proven TAH-authentic on the canonical `TAH_03-17-2014_Revised` member itself — `primary/drive/Sonic_2_PVA_Candles_White_20140317.mq4` (hash-verified): `for(j = i+1; j <= i+10; j++)` prior-10 average excluding bar i (line 201); rising `Volume[i] >= av * 1.5` (line 203); climax `Value2 >= HiValue2 || Volume[i] >= av * 2` over the prior 10 (lines 208-213) — identical logic to the 2015 Suite (only the evaluation ORDER differs: the 2014 file sets rising first then lets climax overwrite, the Suite gates rising on `va==0`; same net classification). TAH's own acknowledgement at file line 41: the climax definition comes from **BetterVolume.mq4 (BetterVolume_v1.4)** — i.e., the PVA climax rule is VSA/BetterVolume heritage, which is why the same thresholds appear in Traders Reality's port (S21). Verdict: **source-primary, no caveat**. Historical note: the 2011 first-generation `SonicR_PV_Histogram` used DIFFERENT parameters — `Climax_Period=20` INCLUDING bar i, `Rising_Period=10` INCLUDING bar i, `Rising_Factor=1.38` (S39 lines 105-108, 222, 255, 286).
- Local fidelity — `SNR_PVA_Candles.mq5` + `Include/SNR_PVSRA.mqh`: prior-10 average excluding current bar (`SnrVolumeAveragePrior` lines 28-35) MATCH; spread×vol max prior 10 (lines 45-52) MATCH; climax = vol≥2×avg OR sv≥max_sv (`SnrClassifyPvaBar` lines 60-66) MATCH; rising 1.5× subordinate to climax MATCH; inputs `InpVolRisingMult=1.5`, `InpVolClimaxMult=2.0` MATCH the source values. Extra local classes LOW/NORMAL and the `support`/`veto` semantics in `SnrPvsraReadClosed` (lines 86-97) are local-empirical additions — TAH code only colours bars.

## 4. Sonic_6 PVA Volumes / Volumes Suite

- Author/version: traderathome + qFish; same generations as #3. Sub-window histogram.
- Exact algorithm (source-primary, `primary/Volumes-Suite.mq4`): identical thresholds to Candles — `av` over `j=i+1..i+10` (lines 313-314), `Value2`/`HiValue2` same loop (318-323), climax `Value2>=HiValue2 || Volume[i]>=av*2` (325), rising `Volume[i]>=av*1.5` gated by `va==0 && Volume_PVA_vs_STD` (328-332). Bars coloured by bar direction (Close>Open → bull colour).
- Extra feature: `Phantom[i]=Volume[i]/0.75` (line 297) — a taller uncoloured "phantom" bar drawn behind the volume bar for visual contrast on black charts.
- Colours (file lines ~62-72 + externs 92-113): Normal `C'102,099,163'` (black) / `C'119,146,179'` (white); Bull Rising `C'017,136,255'`; Bear Rising `C'173,051,255'`; Bull Climax `C'031,192,071'`; Bear Climax `C'224,001,006'`; Standard mono `C'102,099,163'`.
- Alert: same once-per-TF climax alert; TAH says use THIS indicator's alert (not the Candles one) when both loaded (Candles notes line 61-62).
- Repaint: same as #3 — closed bars fixed; bar 0 live.
- Local fidelity — `SNR_PVSRA.mq5`: same SnrClassifyVolume path, MATCH on logic; colours/labels are local reconstructions of the palette.

## 5. Sonic_3 Trade Levels

- Author/version: traderathome (qFish recode, "St3ve" real-orders feature), MT4. File not copied locally, but the Lead decoded the actual Feb-2014 file in full (SonicR_Trade_Levels_White.mq4, 27,652 bytes, FF attachment 1369140 — `primary/drive/LEAD_NOTE_2.md` §2).
- CORRECTION to earlier claims (incl. the May retrieval_readout label "sr_whole_half_quarter_interaction" — that label was WRONG): Trade Levels is a **manual trade-plan utility**, not an S/R grid and not (yet) a real-orders reader in the recovered build. It draws labelled lines for `EP_1..EP_20` (entries), `TP_1..TP_3`, `SL_1..SL_3` that the trader TYPES into inputs, plus an average-EP line (plain arithmetic mean of the non-zero EPs, filled sequentially) and an optional bid-price alert. Right-shift of the avg-EP/TP labels depends on chart zoom read from the Filled Dragon global variable (the same Zoom_Setting GV family as #1).
- The release post's "St3ve — for getting us started on the road away from manual inputs towards using real orders data" (S06, post line 399) frames real-orders as a migration only just STARTED. So: Feb-2014 build = manual inputs; later Mar-2014 57KB revision unread.
- Doctrine hint (Lead note 2 §2): TAH's own tool supports up to 20 entries with an average price — scaling into a position was part of how the method was traded by some users; reconcile with the "never add to a loser" rule (adding to winners/re-entries vs averaging down — see ATLAS S5).
- Role: trade-management display for posted charts — shows EP / average EP / TP / SL + P/L. The whole/half/quarter grid lives in the Control/Access Panel, #6. TAH: "Use our Trade Levels indicator. It gives you more information about your trade" (S17).
- Local fidelity — no SNR port; closest function is inside the archive EA's own level drawing (S45). Our `SNR_SRLevels` is a different thing (it draws the WHQ grid — see #6).

## 6. Sonic_4 Access Panel (ex Control Panel) — **the WHQ grid verdict**

- Author/version: traderathome (CaveMan TzPivots, Kent/Pips4Life clock), 2012→2015, MT4. Recovered: `primary/Access-Panel.mq4` (2015, 3906 lines).
- Function inventory (source-primary user notes, lines 51-88): Market Panel (symbol&TF, spread, weekly/daily average ranges, long/short swaps, candle time-remaining, bid price with shrinking fractional pip and up/down colour, logo); Clock Panel (7 selectable zones; B/L/G/P markers for broker/local/GMT/pivot zones; Preface broker-TZ setup, default proxy "Helsinki"); special Ask/Bid rays + bid dot; **background level lines**; Natural Fibos on previous-day range (internal 23.6/38.2/50/61.8/76.4 + extensions to 638.2); Daily or Fibonacci pivots incl. mid-pivots (PVT optional); Average Range H/L lines for day and week (RDH/RDL/RWH/RWL — "computed average range distance above/below the session low/high", lines 170-172; averages: `Days_In_Range_Day_Avg=15`, `Weeks_In_Week_ATR=13`); day separators; vLines at Asia/Frankfurt/London/NY opens + London close.
- **Whole/half/quarter grid — SETTLED** (source-primary): draws lines at `00, 25, 50, 75` within each 100-pip span (notes lines 101-115; level-class constants declared `int u1=00,u2=50,u3=25,u4=75;` at line 568, consumed by the draw code at lines 953-980: `ssp=int(Bid/Poin)` at 953-961, `v1=ssp%100` classified against u1..u4 at 962/968/974). Base spacing = **25 pips** between adjacent lines; `Poin=Point*10` (line 713 — unconditional; on a 4-digit broker feed the grid would land 10× off, a real caveat for exotics). `__Incr_Decr_Levels_Density` (default 0): +1→50-pip, +2→75-pip, +3→100-pip spacing; −1→12.5, −2→6.25 pips (notes 108-115, code 714-715). Number of line "sets" per TF is hardcoded per timeframe (range counts lines 718-726: M1=4 … W1=70). Per-class visibility caps: `__Levels_Whole_Max_TF=1440`, `__Levels_Half_Max_TF=1440`, `__Levels_Quarter_Max_TF=30` (externs 335-337) — **quarter levels only shown ≤M30 by default**. Half and quarter levels independently toggleable.
- Significance order (source-primary, PVSRA essay S12): "whole numbers, half numbers and finally the 1/4 and 3/4 numbers being important in that order."
- Repaint: none — levels are price-fixed; sets re-anchor only on new highs/lows of the session range lines (by design).
- Local fidelity — `Include/SNR_SRLevels.mqh` + `Indicators/SNR_SRLevels.mq5`: **DIVERGES**. Local input `InpRoundWhole=10.0` (pips) with half=×0.5, quarter=×0.25 → draws a 10/5/2.5-pip grid, whereas TAH draws a fixed 25-pip-spaced 00/25/50/75 grid with density multiplier and TF caps. Local is a simplified reconstruction — usable, but NOT source parity; XAU needs its own scaling decision (TAH's grid is pip-based; gold's "pip" is broker-defined).

## 7. Sonic_5 FFCal Panel

- Author/version: traderathome + deVries + qFish + atstrader, from derkwehler FFCal_v20 (2009) (file lines 72-85). Recovered `primary/FFCal-Panel.mq4` (2015).
- Function (source-primary notes): displays up to 4 upcoming ForexFactory-calendar releases — time, title, impact colour. Prioritisation: simultaneous events collapse to highest impact unless multiple high-impact; current-day Bank Holiday pinned to first label; optional per-currency filter independent of chart pair; option to show only High impact. Alert `Alert_Minutes_Before_Event_1` triggers once. TF display range selectable.
- Deliberately NOT shown: Previous/Forecast numbers — "it is the timing of news that is important, as a market volatility event" (line 34).
- Doctrine baked into the notes (lines 19-29): MMs/banks know news essence in advance, place orders early, and use the intervening time to move price to fill them, "saving the move that will make profits" for release time. → **The panel exists to WATCH MM positioning around releases, not to enforce flat avoidance.** TAH's own commentary treats news as a catalyst MMs exploit ("Whip n' Whack", S17). This is a doctrine conflict with the repo GOAL's hard news-avoidance — flagged for S9 of the atlas.
- Repaint: none (schedule data; requires FFCal .csv file feed in MQL4/Files).
- Local fidelity — no SNR port; the archive EA uses `SNR_FX_EVENTS.csv` gating (S45) — a stricter avoid-news implementation than Sonic doctrine itself.

## 8. Older/other indicators in the lineage

- **SonicR PV Histogram (2011, first PVA generation)** — `primary/SonicR_PV_Histogram_Black_2011.mq4`: externs `Climax_Period=20`, `Climax_Factor=1.0` (≤1; bar must be ≥ factor×max of last 20 incl. itself), `Rising_Period=10`, `Rising_Factor=1.38` (notes recommend 1.38-1.62); average INCLUDES bar i (`for j=i; j<i+Rising_Period`, line 222). So 2011-era PVA ≠ 2013+ PVA parameters — important for audit claims about "the original thresholds" (there are two generations).
- **TRO_Tunnel_Dragon** (Kyaw era): the original 3×EMA34 tunnel + EMA89 (S27) — the Dragon's direct ancestor.
- **QQE_Alert_MTF_v5, Sonic CCI(63), Normalized_Volume_Oscillator, PivotsDWM, SpudFibo, ZZ-Fractal, SHI_Channel_MTF, "time to next bar"** (S27 + SonicRV3 manifest): the pre-PVSRA confirmation stack — QQE>50 rising, CCI>0 rising, NVO volume charge, ZZ for wave visualization, SHI channel for HTF trend. Retired when TAH consolidated PVA in 2013.
- **Multi-Stoch** (Spud's stochastic thread, S34): used by some community members for wave reading — community add-on, not core.

## 9. Later ports

- **Traders Reality Main (TradingView)** (S21): PVSRA candles with IDENTICAL definitions (climax ≥200% avg10 OR sv-max10; rising ≥150%); market session boxes; 5/13/50/200/800 EMAs; pivots; yesterday/last-week range; ADR; daily open; PVSRA datafeed override; psychological H/L; vector-candle zones; alerts. Confirms the PVA spec independently. Vector Candle Zones (S23) mark "unrecovered liquidity" areas — TR's own extension beyond TAH.
- **Dragon and Trend (ForexPipCheats, TV)** (S24): clean EMA34 h/l/c + EMA89 port; credits "traderathome and Fish".
- **CRTT Dragon Trend (VN, TV)** (S25): Wyckoff-phase colouring on the Dragon bands; retest-of-band entries — a VN/community hybrid (community tag).
- **MT5 availability**: no official TAH MT5 port exists; an MQL5 freelance job request (S-category) shows demand but our SNR_* set is effectively the reference port for this repo.

## 10. Fidelity summary — our `SNR_*` port vs TAH original

| our file | original | logic | verdict |
|---|---|---|---|
| SNR_Dragon.mq5 | Solid Dragon-Trend | EMA34 H/C/L | formula MATCH; no fill/trend-embed (split) |
| SNR_Trend.mq5 | Trend (in Dragon-Trend) | EMA89 close | MATCH; slope-colour lookback reconstructed |
| SNR_PVA_Candles.mq5 | Sonic_2 PVA Candles | 150%/200%/sv-max/10-prior | MATCH (source-primary values) |
| SNR_PVSRA.mq5 | Sonic_6 PVA Volumes | same | MATCH |
| SNR_SRLevels.mq5 | Access Panel WHQ | 00/25/50/75, 25-pip, density, TF caps | DIVERGES (10/5/2.5-pip input grid) |
| SNR_Session.mqh | vLines/session marks | Ao/Fo/Lo/NYo/London close | reconstructed (times are local inputs; TAH derives from broker-TZ + DST table) |
| SNR_Wave/ClassicWave | no indicator | manual wave reading | reconstructed (no source code exists — waves were eye-read) |
| SNR_Discipline | 3 Sonic Rules + Sonic M | ≤5 trades/wk, no averaging, wide SL | reconstructed (rule text exists; numeric caps are local) |
| (none) | Trade Levels | EP/avgEP/TP/SL display | MISSING (order-level display, not signal) |
| (none) | FFCal Panel | calendar panel | MISSING (EA-side csv gate instead) |
| (none) | RDH/RDL/RWH/RWL range lines | avg-range projection | MISSING |
| (none) | PivotsTz/NaturalFibos/separators | S/R context | MISSING |
