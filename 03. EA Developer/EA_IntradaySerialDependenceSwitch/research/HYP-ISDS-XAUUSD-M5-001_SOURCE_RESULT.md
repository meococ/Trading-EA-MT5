# HYP-ISDS-XAUUSD-M5-001 — source result

Verdict: `PASS_SOURCE_FEASIBILITY_UNTUNED_MQL5_BASELINE_AUTHORIZED`

- DESIGN rows: `351,303`; complete sessions `1,276/1,305 = 97.7778%`.
- Valid serial-dependence measurements: `1,276/1,276 = 100%`.
- Raw/executable events: `1,275/1,275`; exact-next `100%`.
- Cadence: `4.887733/week`.
- LONG/SHORT: `626/649`; persistent/anti-persistent regimes `439/836`.
- Year counts: `255/255/257/252/256`; yearly cadence
  `4.8329–4.9153/week`; max-year share `20.1569%`.
- All frozen gates and deterministic replay passed.
- No post-16:00 price, trade, return, cost, PF, validation or holdout was
  opened.

Evidence hashes:

- report `F4706B9D62DCB250F35EF1C4ACE4E912646ED568CC94577F1D54EAABEFC5ED90`;
- ledger `107AA05FF35AABAACA97EA81DD366AB0522CD6788ACE723DABA4CC67686A5236`;
- receipt `0F020559163D3D68F22D1560D129CC42464783DF8B8A11478D34D30526A692AA`;
- terminal `EDA46B38A869940A4BAED6AC4CD8EF4100278AC1A6042BCDF1C418FB4678EA24`.

PASS authorizes only direct MQL5 parity, focused tests, compile/non-repaint and
one untuned Model-0 baseline with the unchanged source mapping. It does not
establish economic edge or promotion readiness.
