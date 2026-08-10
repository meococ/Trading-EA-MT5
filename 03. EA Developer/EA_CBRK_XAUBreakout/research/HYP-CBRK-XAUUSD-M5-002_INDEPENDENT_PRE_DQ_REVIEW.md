# HYP-CBRK-XAUUSD-M5-002 — Independent pre-DQ review

Verdict: `PASS_PRE_DQ`

Scope: static/source review only. No MT5 run, market outcome, cost, PF, validation or holdout was opened.

## Frozen evidence

- Source: `03. EA Developer/EA_CBRK_XAUBreakout/EA_CBRK_XAUBreakout.mq5`
  - SHA256: `24C6B88BECF2A6F762C204B8DFD861CDA2A9E186C2EF1C55EA00A2A0C22F38F8`
- Preregistration: `03. EA Developer/EA_LOMX_MultiAssetMomentum/research/HYP-CBRK-XAUUSD-M5-002_FROZEN_PREREG.md`
  - SHA256: `064BCFB8F1BDD7B781ACCAF53098339D5DB7A64A97E0C22DDC92639D9BC5A924`
- EA contract SHA256: `DB4E8764DBEBA7EA99E3FE3D50E8D53723A9B451AE946E806D9000EE2BF919D1`
- EX5 SHA256: `AE4C9A4FBD9889CF93CD2E699C6E1E7AA355B5894716198AFDA481FA394C0BBA`
- Compile log SHA256: `5E209AD5D978470225A69B3138AADB1E37A9FAEE2735FAA5651B58D89850D1D5`
  - Result: exactly `0 errors, 0 warnings`.
- Non-repaint manifest SHA256: `FA288D9D5A9654F685E66D40C966CE0D1E89907CED1502AE68F66D9170182EFB`
- Non-repaint audit SHA256: `812929E64176FC4C8FE29C29497E3AE17DA50F3766AFF757D963B794031D09D8`
  - Result: `PASS`, zero findings.
- Focused tests: `16/16 PASS`.

## Review findings

1. The historical LOMX source remains unchanged at SHA256 `D363121DC7FFCB128A67C796B76F8B86C8AB2262FF045EAC62B49FE19FB3298B`.
2. The fresh source differs from that historical source only in package identity and the authorized clock correction.
3. The signal session now uses `ServerToUtc(rates[0].time)` after loading the completed signal bar.
4. The frozen signal-bar window is exactly `[07:00,16:00)` UTC: 06:55 reject, 07:00 accept, 15:55 accept, 16:00 reject.
5. Signal construction, ATR14, volume participation, stop/target geometry, risk, order, exit and lifecycle rules did not drift.

## Authority boundary

Authorize only the standard AlphaFactory zero-trade DQ child needed to prove exact native XAUUSD M5 population `351303`, history quality `>97%`, journal bounds and D0 series proof. No direct economic authority is granted by this review.
