# LEAD_HANDOFF - SONIC-LAB Round 2 -> next round

## Status

No config passed the preregistered D5 gate -> VALIDATION was never run
-> there is NO MQL5 build spec to hand off this round. HOLDOUT sealed.
This file instead hands the Lead the verified findings, the exact
machinery to reuse, and the cheapest next tests (E5 output).

## What is verified reusable (do NOT re-derive)

1. **Canonical data plane**: `02. AlphaFactory/lab/cache/<SYM>_M1_2010_2026.parquet`
   - M1 bid, UTC-stored as server-naive ctm, `suspect` flags baked in.
   - Server clock = UTC+2/+3 following US DST (verified vs MT5 exports).
   - M15/M5/H1 = causal resample of M1 (`src/data.py::resample`).
   - London sessions: convert ctm -> London wall via US+UK DST tables
     (`src/data.py::server_to_london`); NEVER hand-roll offsets.
2. **TAH-code-exact components** (unit-tested, `src/components/`):
   - Dragon = EMA34(H/C/L), Trend = EMA89(C); J slope = mid[t] vs mid[t-3].
   - PVA: av=mean(vol[i-10..i-1]); climax if vol*rng >= max(prior10)
     OR vol>=2*av; rising if vol>=1.5*av.
   - WHQ grid: pip=Point*10; EUR quarters 0.0025/0.005/0.01;
     XAU 2.5/5/10. **The old EA file SNR_SRLevels.mqh draws a WRONG
     10/5/2.5-pip grid - do not copy it.**
   - Fractal-2 swings (16/08 parser; confirmation lag = 2 bars).
   - ATR-zigzag 1.5xATR14 (variable confirmation lag, stored per swing).
   - Swing-cluster zones (>=2 confirmed extremes within 0.3*ATR,
     pad 0.1*ATR, dies on close-through >0.5*ATR).
   - J wave parser + pending/SL/TP/Friday-flatten semantics (sim.py).
3. **Cost model** (DATA.md): EUR 1.0p RT x1 (spread 0.1 + slip 0.2 +
   comm 0.7); XAU 5.5p RT (2.0 + 2.8 + 0.7). x1.5/x2 scale the whole.

## Which elements moved the needle (ladder anatomy, EURUSD DESIGN)

- W2 wave-origin inside swing-cluster zone: PF 0.90 -> 1.08 (+0.18)
- W3 leg-1 through Dragon required: -> 1.06 (+0.16)
- W4 Dragon angle >=0.05 ATR/bar: -> 1.20 (+0.30) but ~2 sig/yr (dead)
- R1b big-swing stop, R2a zone target: +0.04-0.05
- R2b WHQ target >=1R: -0.11 (hurts)
- PVSRA-agree gate: kills cadence (98% cut) - unevaluable as a gate;
  keep PVSRA as TELEMETRY only (consistent with freeze doctrine).

## The one real family: F2 Nhat Hoai (atlas S6 fam 2)

Exact spec as run (for any future re-test):
- M15, London-ext 07:00-16:00 London.
- After close crosses the Dragon mid (side change), wait for the first
  pullback INTO the band (close inside EMA34L..EMA34H), <=16 bars stale.
- Trigger: bar closes back outside the band on the armed side.
- Pending stop = signal extreme + 2 pips, TTL 4 M15 bars.
- SL variant b (the better one): beyond the largest ATR-zigzag extreme
  of the last 48 bars on the protective side -/+ 0.1*ATR14, cap 120p EUR
  / 212.2p XAU.
- TP: nearest opposing swing-zone near edge at >=1R; none -> no trade.
- One position/pending at a time; Friday flatten 20:00 London.
Numbers: EUR n=1298 PF1=1.147 PF15=1.123 pct=100; XAU n=1448 PF1=1.053
pct=96. Fails D5 on PF<1.20 + pos-years 55% + MC DD P95 196R.

## Cheapest next tests (E5 - need a NEW prereg before running)

1. Exit redesign on F2_NH_b (same signal stream, change exits only):
   BE at +0.5R + TP 1.5-2R; or TP 1.5R fixed; or time-stop 8 bars.
2. Minimal J composite: J + W2swing + W3 (nothing else).
3. F2_NH_b + H1 trend-agreement gate (reuse F3's H1 block) for XAU.

## MT5 parity checklist for any future MQL5 build

- trade-by-trade match vs `out/trades_<sym>_<cfg>.csv` on DESIGN:
  same fill times within 1 M1 bar, same SL/TP prices within 0.2 pip,
  same exit reason mapping (sl/tp/flat).
- WHQ grid must be the 25-pip quarter grid (EUR) / $2.50 (XAU).
- PVA on tick volume with the 10-PRIOR-bar average (not including i).
- All indicators/swings on closed bars only; fractal usable only after
  its 2 confirmation bars.
- Pending fills resolved on M1; SL-first inside ambiguous bars;
  Friday flatten before 20:00 London.

---

# Round-2B + errata addendum (23/09, for round-3 MQL5 spec)

## Harness rules the EA MUST copy (errata E1-E3, verified in lab)

1. **Rollover handling**: the feed fabricates M1 bars inside the roll
   window (EURUSD ~00:00-00:20, XAUUSD ~01:00-01:20 server) - measured
   19x-450x exit concentration, 31-38x daily-max-range vs quiet hours,
   jump-and-revert 26%/18% of days. EA-side equivalent: do not let a
   pending fill or an SL/TP touch execute on tick data inside the
   broker's own rollover spread burst; the lab rule is "skip the bar,
   resolve at the first clean bar's open" - on a live EA the cleanest
   port is to ignore SL/TP trigger checks while the spread exceeds a
   pre-registered cap (round-3 measures the real S_roll from broker
   ticks; lab assumption EUR +2.0p / XAU +20p in window).
2. **E2 executability floor**: never place an order whose
   |pending_px - SL| < max(3 x round-trip cost, 0.15 x ATR14[signal tf]).
   This removed 759-6866 micro-stop orders on XAU in DESIGN - they are
   not executable at a real broker.
3. **Fixed risk-% sizing**: account P/L is in R, not pips - PF_R is the
   promotion metric (pip PF co-reported).
4. **Zone semantics**: a swing-cluster zone exists at decision bar t
   only after its SECOND member is confirmed (avail_idx); death is
   checked from the earliest member pivot (origin_idx). The MQL5 port
   must replicate exactly this causal visibility.
5. **W4 definitions used in 2B**: W4c = dir*(mid[t]-mid[t-20]) > 0;
   W4d = dir*(mid[t]-mid[t-20])/(20*ATR14[t]) >= Q with Q per symbol
   (EUR -0.006340, XAU -0.005364, from census).
6. **PVA definitions**: rising = vol >= 1.5 x mean(vol[i-10..i-1]);
   climax = vol*rng >= max(vol*rng over prior 10) OR vol >= 2 x av.
   pv2a checks the leg2 +/- 1 bar window; pv2b the trigger bar only.
7. **Ticket fields** (every trade row): sig bar ctm, pending_px
   (stop-order price), fill ctm + entry (actual fill), SL, TP, exit
   ctm + px, reason (sl/tp/flat/window_end).
8. **No weekend hold**: Friday flatten at 20:00 London (server-side
   ~21:00-22:00 depending on DST - use the London-clock conversion,
   never a fixed server hour).
9. **sl_big_swing**: most recent CONFIRMED swing extreme strictly
   beyond pending_px on the protective side; None if none within 48
   bars -> no trade. Never a same-side or wrong-side stop.

## Round-3 MQL5 spec for advancing configs

PENDING - see RESULTS_v2.md section 6. (If the dual-harness selection
yields zero, this section stays a placeholder: no MQL5 build is
justified by DESIGN numbers alone.)
