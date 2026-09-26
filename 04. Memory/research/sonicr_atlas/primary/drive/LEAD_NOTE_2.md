# LEAD NOTE 2 - Drive copies delivered (Lead, 23/09 09:12Z)

FF attachments are Cloudflare-blocked now (you logged it). The Lead pulled the Owner's Drive copy instead.

## 1. SonicR_Filled_Dragon_White.mq4 - delivered in this folder
- File: primary/drive/SonicR_Filled_Dragon_White.mq4 (13581 bytes, SHA256 prefix FBB09C411F0841E5 = matches the May manifest).
- Source: FF attachment 1369134 (post 7281738, Feb 2014 build-600 set), TAH, release 05-25-2013.
- Hash it into PRIMARY_INDEX.md as "drive copy, hash-verified vs retrieval_manifest".

## 2. SonicR_Trade_Levels_White.mq4 - read by the Lead, NOT copied (not needed)
The Lead decoded and read the whole file (27652 bytes, FF attachment 1369140). IMPORTANT CORRECTION:
- It is NOT a whole/half/quarter S/R grid. It is a manual trade-plan utility: it draws labelled lines for
  EP_1..EP_20 (entries), TP_1..TP_3, SL_1..SL_3 that the trader TYPES into inputs, plus an average-EP line
  (plain arithmetic mean of the non-zero EPs, filled sequentially) and an optional bid-price alert.
  Right-shift of the avg-EP/TP labels depends on the chart zoom read from the Filled Dragon global variable.
- So the May retrieval_readout label "sr_whole_half_quarter_interaction" for this file was WRONG.
- The whole/half/quarter level drawing must therefore come from the Control Panel / Access Panel
  (your Access-Panel.mq4). Settle the WHQ grid from THAT code (pip step, Digits handling, gold vs FX)
  and say explicitly in INDICATORS.md that Trade Levels is a manual EP/TP/SL plotter.
- Useful doctrine hint from it: TAH's own tool supports up to 20 entries with an average price -> scaling
  into a position was part of how the method was traded by some users; check this against the
  "never add to a loser" rule in the manuals (adding to winners / re-entries vs averaging down).

## 3. Filled Dragon facts the Lead verified in the code (you still own the INDICATORS.md write-up)
- Dragon = EMA(34) of PRICE_HIGH (outer top) and PRICE_LOW (outer bottom), EMA(34) of PRICE_CLOSE (centre line
  + centre highlight band). Trend = EMA(89) of PRICE_CLOSE. MA type EMA (Dragon_Type = Trend_Type = 1).
- Computed on the chart's own timeframe only (release notes: the ability to show the M15 Dragon-Trend on
  other TF charts was REMOVED in 05-2013). No slope/angle is computed anywhere - "angle" is purely visual.
- Standard IndicatorCounted loop; bar 0 updates intrabar (normal EMA behaviour, not a repaint of history).
- Most of the file is cosmetics: histogram fill widths tied to a Chart_Zoom_123456 input, shared with
  PVA Candles / PVA Volumes / Control Panel via GlobalVariables "Zoom_Setting" / "Bar_Setting".

## 4. Still available on request (Owner Drive) if you need them
TAH_03-17-2014_Revised.zip (Sonic_1 Solid Dragon, Sonic_2 PVA Candles, Sonic_3 Trade Levels,
Sonic_4 Access Panel, Sonic_5 FFCal Panel, Sonic_6 PVA Volumes; Black and White chart versions + tpl),
2014_SonicR_Indys_Tmpls.zip, sonicr_2013_white.tpl, FF post HTML (#1, 7348659, 6707153, 7281738),
sonicr999 HTML mirror. Write "ESCALATE: NEED_DRIVE <file>" in the log and the Lead will drop it here.
If your web copies (Candles-Suite / Volumes-Suite / Access-Panel / FFCal-Panel) are a later "Suite" release,
say which version/date each one is in PRIMARY_INDEX.md.
