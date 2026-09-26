# LEAD NOTE 4 - answer to "ESCALATE: NEED_DRIVE TAH_03-17-2014_Revised.zip" (Lead, 23/09 ~10:05Z)

The Owner's Drive holds that zip already EXTRACTED (members renamed 0001-0014 in archive order). The Lead
delivered the one member that decides the PVA question, and read it:

## primary/drive/Sonic_2_PVA_Candles_White_20140317.mq4  (= zip member "White Chart/Sonic_2 PVA Candles (White).mq4")
- 11672 bytes (matches the zip listing), SHA256 4ef2dcb1223c3a43b70dfd02739966c73b9669e8931fdea27aaacce6f03f4a71
- Header: "Copyright 2014 traderathome and qFish", MT4 build 600, release 03-17-2014 (changes from 05-25-2012).
- User notes: Climax = volume >= 200% of the average of the 10 most recent PREVIOUS bars, OR candle spread x volume
  >= the highest of the 10 previous bars; Rising = volume >= 150% of that average.
- Code: line 201 `for(j = i+1; j <= i+10; j++)` (average of the 10 previous bars, current excluded),
  line 203 `Volume[i] >= av * 1.5` -> rising, lines 208-213 spread x volume max of prior 10 OR `Volume[i] >= av * 2` -> climax.
- Line 41 acknowledgement: the climax definition comes from BetterVolume.mq4 (BetterVolume_v1.4). Add this lineage
  fact (PVA climax rule = BetterVolume/VSA heritage) to S1/S4 and INDICATORS section 3.
=> The canonical 03-17-2014 PVA logic is IDENTICAL to the 2015 Suite you read. The PVA verdict is now closed on
   the canonical file itself, not only on TAH's succession statement. Update PRIMARY_INDEX, INDICATORS section 3,
   REVIEW.md "remaining limitations", and close the escalation in the log.

## Other members - not delivered (not needed), available on request
0002/0009 Sonic_1 Solid Dragon (Black/White, ~11.1 KB) - same EMA34 H/C/L + EMA89 object as the Feb Filled Dragon.
0004/0011 Sonic_3 Trade Levels (Black/White, ~57 KB - twice the Feb 27 KB file: likely the version that starts
reading real orders, cf. the St3ve credit you found in post 7348659). 0005/0012 Sonic_4 Access Panel (~170 KB).
0006/0013 Sonic_5 FFCal (~54 KB). 0007/0014 Sonic_6 PVA Volumes (~11.3 KB). 0001/0008 templates (.tpl).
If one of these would change a conclusion, write "ESCALATE: NEED_DRIVE <member>" and say why.

## Clock
Your NOTEBOOK.md/REVIEW.md times (13:05Z, 13:35Z ...) are about 3.5 hours ahead of true UTC (the Lead's
09:10Z note arrived before your "13:05Z" auth check). Get UTC with
`python -c "import datetime;print(datetime.datetime.now(datetime.timezone.utc).isoformat())"` and fix the stamps.
