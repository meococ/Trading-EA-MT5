# s1b vs c3 — per-panel object diff

S1-b touches BOX-family only; non-box objects must equal the c3 set — asserted per panel below (PASS/FAIL).

## 9.2b (tau=765)
- added (0): —
- removed (0): —
- changed (2):
  - BOX0002(BOX): t0_min 70->390
  - CON0008(CONTEXT_RANGE): t0_min 40->390
- s1 stats: rows=2 transformed=2 (+1 unlisted) dropped=0; boxes without row: RAN0000
- non-box == c3: PASS

## 9.10c (tau=945)
- added (0): —
- removed (0): —
- changed (1):
  - BOX0001(BOX): t0_min 20->570
- s1 stats: rows=1 transformed=1 (+2 unlisted) dropped=0; boxes without row: CON0006, RAN0000
- non-box == c3: PASS

## 9.11b (tau=840)
- added (0): —
- removed (0): —
- changed (2):
  - BOX0001(BOX): t0_min 20->465
  - CON0007(CONTEXT_RANGE): t0_min 20->465
- s1 stats: rows=2 transformed=2 (+1 unlisted) dropped=0; boxes without row: RAN0000
- non-box == c3: PASS

## 9.17b (tau=730)
- added (0): —
- removed (0): —
- changed (2):
  - BOX0001(BOX): t0_min 40->355
  - CON0007(CONTEXT_RANGE): t0_min 20->355
- s1 stats: rows=2 transformed=2 (+1 unlisted) dropped=0; boxes without row: RAN0000
- non-box == c3: PASS

## 9.25a (tau=300)
- added (0): —
- removed (0): —
- changed (0):
- s1 stats: rows=2 transformed=0 (+0 unlisted) dropped=0; boxes without row: RAN0000
- non-box == c3: PASS

## 9.33c (tau=1055)
- added (0): —
- removed (0): —
- changed (1):
  - BOX0001(BOX): t0_min 35->680
- s1 stats: rows=1 transformed=1 (+2 unlisted) dropped=0; boxes without row: CON0006, RAN0000
- non-box == c3: PASS

## 9.36c (tau=1085)
- added (0): —
- removed (0): —
- changed (2):
  - BOX0001(BOX): t0_min 20->710
  - BOX0014(BOX): t0_min 325->630
- s1 stats: rows=2 transformed=1 (+3 unlisted) dropped=0; boxes without row: BOX0013, BOX0014, RAN0000
- non-box == c3: PASS

## 9.40a (tau=660)
- added (0): —
- removed (0): —
- changed (3):
  - BOX0002(BOX): t0_min 50->285
  - CON0007(CONTEXT_RANGE): t0_min 50->285
  - RAN0000(RANGE_OPEN): t0_min 20->150
- s1 stats: rows=2 transformed=2 (+1 unlisted) dropped=0; boxes without row: RAN0000
- non-box == c3: PASS

## 9.42b (tau=640)
- added (0): —
- removed (0): —
- changed (2):
  - BOX0001(BOX): t0_min 30->265
  - RAN0000(BOX): t0_min 20->265
- s1 stats: rows=5 transformed=2 (+0 unlisted) dropped=0; boxes without row: —
- non-box == c3: PASS

## 9.48b (tau=705)
- added (0): —
- removed (0): —
- changed (2):
  - BOX0001(BOX): t0_min 45->330
  - RAN0000(BOX): t0_min 20->330
- s1 stats: rows=2 transformed=2 (+0 unlisted) dropped=0; boxes without row: —
- non-box == c3: PASS

## 9.52a (tau=350)
- added (0): —
- removed (0): —
- changed (0):
- s1 stats: rows=2 transformed=0 (+0 unlisted) dropped=0; boxes without row: RAN0000
- non-box == c3: PASS

## 9.57b (tau=685)
- added (0): —
- removed (0): —
- changed (2):
  - BOX0005(BOX): t0_min 95->310
  - CON0006(CONTEXT_RANGE): t0_min 35->310
- s1 stats: rows=2 transformed=2 (+1 unlisted) dropped=0; boxes without row: RAN0000
- non-box == c3: PASS
