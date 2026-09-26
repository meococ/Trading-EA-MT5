# Roll-Reopen Reversion — deep-history verification (2010→2025, M1 .hcc)

**Status: first verified real mechanism of the campaign. Supersedes the fade claims
in `20260918_DAY_BOUNDARY_MARKET_PHYSICS.md` (see corrections below).**

Method: `.hcc_reader.py` parses `bases/MetaQuotes-Demo/history/<SYM>/YYYY.hcc`
directly — the same data plane the governed Strategy Tester uses (~370k validated
M1 bars/yr/symbol, 2010→2025; the `copy_rates` research window covered only
2025-05→2026-09 ≈ 16 months). Event-level accounting (one event per day),
server-time minutes (00:00 server = 5pm ET roll, both DST regimes).

## The mechanism

At server 00:00 the FX trading day reopens after the 5pm-ET roll pause. The reopen
systematically prints BELOW fair value (tom-next/carry repricing overshoots inside
the post-roll liquidity vacuum). Buy the reopen → ride the ~1–2h reversion.

Evidence it is real, not artifact:
- Effect only fires conditioned on the gap SIZE (Q1 gap-downs +2.4–4.4p, t 6–18,
  win 68–83%; flat/gap-up days ≈ 0 or negative) — a clock artifact would fire
  unconditionally.
- Present in BOTH US-DST and winter regimes at server-00:00 (CHF +3.53 vs +4.35) —
  anchored to the ET-anchored roll, which the server clock tracks by construction.
- Generalizes across asset class: XAUUSD at its own 01:00-server boundary
  (gap≤-3 → +4.58p, PF 2.01, n=723).
- Stable post-2016 on 6/7 majors (EURUSD positive 10/10 years 2016–2025).
  Pre-2016 the pattern is absent — consistent with modern rollover liquidity
  structure, and warns: era is a real conditioning variable.

## Event-level results (2016→2025 unless noted)

LONG at ~00:05 server (5min after reopen — overshoot peaks ~5min in), gap vs
prior close ≤ −1.5p, exit +60–120m:

| Symbol | +60m mean | t | win% | PF@120m | n/16y |
|---|---|---|---|---|---|
| USDCHF | +2.64p | +14.6 | 73% | **5.22** | ~971 |
| USDCAD | +2.63p | +13.3 | 73% | **3.62** | ~1030 |
| EURUSD | +2.22p | +8.9 | 75% | **2.86** | ~716 |
| GBPUSD | +2.48p | +8.6 | 72% | **3.49** | ~1051 |
| NZDUSD | +2.06p | +7.7 | 68% | **2.69** | ~1011 |
| AUDUSD | +1.62p | +8.1 | 70% | **2.79** | ~1036 |
| USDJPY | +1.99p | +6.3 | 65% | **1.49** | ~994 |

Horizon: PF peaks ~120m hold (240m decays — reversion completes ~2h).
Entry timing: 00:05 > 00:00 (gap overshoot extends ~5min after reopen).
MAE: median −2.6~−4.8p, p25 −6.3~−8.9p → SL ~10–12p required.
Gap threshold: ≤−3.0p → PF 2.5–10.8 but ~0.5–0.7 events/wk (rarer, stronger).

SHORT side exists ONLY on USDCHF (gap ≥ +2p → +4.02p, PF 6.69, n=102 ≈ 6/yr).
Other symbols' gap-ups ≈ PF 1.1–1.5 — too thin.

Week-open (Mon 00:00, weekend gap): conditional reversion real on CHF/CAD/GBP
(gap≤−5 → +5.9–12.3p, PF 3.1–8.2) — EUR/AUD dead. +~0.3–0.5 events/wk.

## Falsified in the same deep-history pass

- **Pierce-fade (the 2026-09-18 "flagship")**: event-level M1 says up-pierces
  CONTINUE (fade loses −2 to −7.7p, win 15–35%, all symbols all years). The M5
  probe's "+5–7.5p signed fade" is an artifact — likely a sign-inversion inside
  that probe chain (auditor flagged one sign fix already) plus per-tranche
  oversampling of continuation days. Claim withdrawn.
- **23h pre-roll short**: real 2010–15 (+1.9–3.6p), dead post-2016 (~0).
- **WMR/ECB/Tokyo-fix reversion at correct server clocks** (18:00 / 15:15 /
  03:00): PF 0.85–1.15 everywhere — published fix effects absent at 30/60m
  granularity on this feed.
- **Post-reversion giveback** (fade the completed 2h reversion): PF ~0.9–1.2.
- **Boundary gap itself** (−1.2 to −4.1p at 23:55→00:00): carry/tom-next
  repricing — untradeable by CIP construction (offsets swap).

## Cadence — honest accounting

Per symbol per year: ~60 conditional events (gap≤−1.5) + ~5–10 week-open +
(CHF) ~6 short-side ≈ **1.2–1.5/wk**. Trading the boundary unconditionally
(5/wk) dilutes to +0.5–0.9p/day. GOAL floor 10–40/wk/symbol is NOT met by this
family alone — declared constraint, not hidden. This run tests governed
economics; cadence feasibility is a separate contract question.

## Corrections required by adversarial audit (done / pending)

1. BEDGE/SMOM governed "kills" ran GMT-shifted windows disjoint from the probed
   server-time cells → those kills did NOT test the day-boundary mechanism.
   (Registry annotation pending; new EA must gate on SERVER time.)
2. Sample window: copy_rates probes saw ~16mo, not 2022→2026 — now fixed via
   direct .hcc reads (2010→2025 asserted).
3. Spread-contradiction resolved by clock arithmetic: COST_PLANE_AUDIT's
   p90-5.4p hour is 00:00 UTC (=02:00–03:00 server) — NOT the 21:00–22:00 UTC
   entry window (measured p90 0.2–0.3p flat on ~4wk real ticks).
4. Cost model for prereg must add commission ≈0.7p RT + adverse-fill discount
   on top of spread — net margin ~0.5–1.5p against 2–3.5p gross.
5. All future probes: assert times[0]/times[-1] coverage, event-level (not
   tranche) accounting, server-time labels, pip sanity clip |ret|<150p.
