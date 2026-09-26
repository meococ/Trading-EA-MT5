# LEAD NOTE - primary sources for SONIC-ATLAS (Lead, 23/09 08:50Z)

The backup zip has no source_quarantine (you already found that). Do not wait for a Drive copy - use these.
The Lead read the Owner's Google Drive copy of the May-2026 quarantine and recovered the ORIGINAL public
Forex Factory attachment URLs (they returned HTTP 200 without login on 2026-05-09). Fetch them directly as
text (they are .mq4 / .tpl source text; zips = list first, extract only .mq4/.tpl/.txt/.pdf/.htm members).
Save into 04. Memory/research/sonicr_atlas/primary/ff/ and hash them into PRIMARY_INDEX.md.

## FF post 7281738 - TAH build-600 indicator set (Feb 2014)
| File | URL | Size (May) | SHA256 prefix (May) |
|---|---|---:|---|
| SonicR_Filled_Dragon_White.mq4 | https://www.forexfactory.com/attachment/file/1369134?d=1392363519 | 13581 | FBB09C411F0841E5 |
| SonicR_PVA_Candles_White.mq4 | https://www.forexfactory.com/attachment/file/1369136?d=1392363543 | 15419 | 60BF70CCEE39B5A4 |
| SonicR_PVA_Volumes_White.mq4 | https://www.forexfactory.com/attachment/file/1369138?d=1392363573 | 14357 | 9246D60C570CC0BD |
| SonicR_Trade_Levels_White.mq4 | https://www.forexfactory.com/attachment/file/1369140?d=1392363601 | 27652 | 59E67740200D73B7 |
| sonicr_2013_white.tpl | https://www.forexfactory.com/attachment/file/1369142?d=1392363669 | 53604 | C0DC968342C79ABB |
| SonicR_FFCal_Panel_White.mq4 | https://www.forexfactory.com/attachment/file/1369192?d=1392367369 | 53817 | 3759DAB5B6C5018B |
| SonicR_Control_Panel_White.mq4 | https://www.forexfactory.com/attachment/file/1369247?d=1392372153 | 136402 | EC19344658640CD0 |

## Zips (list first; extract only source/text members)
- 2014_SonicR_Indys_Tmpls.zip (post 7348659): https://www.forexfactory.com/attachment/file/1388804?d=1395172347  (155274 bytes, SHA256 prefix A52CE2608BEE79E6)
- TAH_03-17-2014_Revised.zip (post #1, the latest TAH set): https://www.forexfactory.com/attachment/file/1572569?d=1418607844  (155139 bytes, SHA256 prefix DB2F0FD60BE6647E)
  Known listing: "TAH 03-17-2014 Revised/{Black Chart,White Chart}/" with "2014 sonicr (black|white).tpl",
  "Sonic_1 Solid Dragon", "Sonic_2 PVA Candles", "Sonic_3 Trade Levels", "Sonic_4 Access Panel" (~170 KB),
  "Sonic_5 FFCal Panel", "Sonic_6 PVA Volumes". This 03-17-2014 set is NEWER than the Feb-2014 build-600 set:
  treat it as the canonical TAH version and diff it against the Feb set (what changed in PVA thresholds, levels, panel).

## Post HTML (tried in May with HTTP 200)
- Post #1 (TAH 2014 revised), 7348659 (PVSRA run-for-profits vs position-building), 6707153 (PVA thresholds),
  7281738 (build-600 set): use https://www.forexfactory.com/thread/post/<id>. Also the sonicr999 mirror (public).

## If FF now blocks these URLs
Write "ESCALATE: FF_ATTACHMENTS_BLOCKED <which>" in the log and keep going; the Lead will copy the Drive
copies of the MQ4 files into primary/drive/. Do not bypass Cloudflare, do not log in.
