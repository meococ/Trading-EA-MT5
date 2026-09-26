# HYP-RGR-CHF-M1-001 — Governed Kill + hcc_reader fabrication discovery

Run: `EA_RollReversion/20260918_205000` (USDCHF M1, 2010.05.10→2026.09.11, Model 0, HQ 98%, 6.06M bars / 261M ticks)

## Headline

| Metric | Value | Gate |
|---|---|---|
| PF | **0.14** | <1.30 → DEAD |
| Trades | 857 (741L/116S) | cadence ~1.0/wk |
| Win rate | 19.3% | — |
| Net | −$7,026 / DD 70.5% | — |
| Avg pips | −6.3 (L) / −6.9 (S) | — |
| Exit profile | ~80% SL −15p within minutes | — |

Every run-year negative → also trips the "sign-flip" kill clause.

## Root cause (verified, not inferred)

The probe edge (PF 2.0–4.3) was measured on `tools/hcc_reader.py` — a 60-byte
phase-scan that **fabricates records inside the roll-minute tick burst**:

1. 2781/2789 USDCHF days carry an absurd 00:00 bar: range 59–173p,
   tickvol ~50,000 (normal ~50), spread field 0.
2. **86% of tester entry fills fall outside the reader's bar range** for that
   minute. Decisive proof: 2026-04-10 EA filled BUY @0.79050 at 00:04:00 while
   the reader's 00:04 bar tops at 0.78843 — a 20p impossibility.
3. Probe entry at "00:05 open" landed on fabricated prices sitting at the
   post-flush bottom → synthetic +3.8p reversion.
4. Same-day join (513 matched days): probe-bar returns +3.54p (74% win) vs
   real tester PnL −6.0p (21% win). Divergence IS the artifact.

The gap event (open0 − prev_close) was real and the EA detected it correctly
(journal gaps match). What never existed: a monetizable reversion at
executable prices. Real roll minute is a 60–170p whipsaw; a 15p SL sits
inside its noise band → structural ~80% stopout.

## Implications

- Day-boundary family fully closed: fade (continuation), 23h (dead 2016),
  fix-windows, roll-gap — all dead.
- Any prior/future probe using hcc_reader output inside burst windows
  (roll, news spikes) is suspect until re-validated against real fills.
- Nonrepaint audit FAIL recorded (time-range Copy overloads flagged;
  guarded-helper refactor required before any EA rerun — not done, dead hyp).

## Process note

Post-run `data_fingerprint` check failed on packet placeholder — expected on
bootstrap runs; report, journal, and fills are authoritative governed evidence.

## Follow-up (same day) — fabrication structure confirmed

- Phase-19 stream is coherent: the "spike bar" is a REAL packed record in
  the file (marker record for the roll tick-burst, tv~50-57k), not a scan
  artifact. The 00:01-00:10 "bars" around it are also real records — but
  they encode only PART of the burst range.
- Decisive: tester fill BUY 0.79050 @00:04 vs file's only 00:04 record
  [0.78823,0.78843]. The tester reconstructs real ticks from the packed
  burst → its effective bar range is far wider. .hcc M1 bars inside burst
  regions are NOT the tradable envelope.
- `hcc_reader` v2 now flags suspect ctms (~1.1%/yr = roll window);
  `validate_bars_against_fills.py` is the reusable GATE A cross-check.
- USDJPY is 22% suspect — JPY probes need fill-level validation everywhere.
