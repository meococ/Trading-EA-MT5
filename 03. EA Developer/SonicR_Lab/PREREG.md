# PREREG — SONIC-LAB Round 2 (frozen before any P/L)

Frozen: 2026-09-23 ~16:20Z. This document is hashed (sha256) and the hash
logged in LAB_LOG.md BEFORE any profit/loss is computed. Nothing below may
change afterwards; any discovered error is documented as an erratum in
RESULTS.md, not edited here.

## 1. Question

Which Sonic R variant, if any, produces an economically viable edge on
EURUSD and XAUUSD M15 (M5/H1 only where a variant requires them), measured
against costs, negative controls and a single read of VALIDATION.
Reference: SONICR_ATLAS S2-S10; the 16/08 run (object J,
`ClassicWaveLeg3DragonBreak`, EURUSD M15 London, N=307, PF=0.94).

## 2. Data and time windows

Source (both symbols): `02. AlphaFactory/lab/cache/<SYM>_M1_2010_2026.parquet`
(canonical research plane; lab etl suspect flags carried through). J parity
extends EURUSD with MQ-Demo `.hcc` M1 via `hcc_reader.py` flagged mode.
M15/M5/H1 derived by causal resample of M1 (src/data.py::resample).
Broker clock: MQ-Demo server = UTC+2/+3 on US DST (verified in DATA.md);
sessions evaluated on London wall time.

Windows (server-naive ctm):

| window     | start            | end              |
|------------|------------------|------------------|
| DESIGN     | 2010-01-04 00:00 | 2020-01-13 04:47 |
| VALIDATION | 2020-01-13 04:47 | 2023-05-17 14:23 |
| HOLDOUT    | 2023-05-17 14:23 | 2026-09-18 23:59 | (sealed — never loaded)
| J-PARITY   | 2000-01-03 00:00 | 2023-05-17 14:23 |

HOLDOUT seal: `src/data.py::_check_holdout` raises PermissionError on any
read ending after 2023-05-17 14:23 unless `allow_holdout=True`; that flag
is passed NOWHERE in this round (grep-verifiable).

## 3. Cost model (x1 / x1.5 / x2)

Per-trade cost deducted in price units: `cost = spread + 2*slip + comm`.
Fills/exits use raw price levels (one fill path for all tiers).

| symbol | spread | slip/side | commission | cost x1 (RT) | x1.5 | x2 |
|--------|--------|-----------|------------|--------------|------|----|
| EURUSD | 0.1 pip | 0.1 pip | 0.7 pip | 1.0 pip | 1.5 | 2.0 |
| XAUUSD | 2.0 pip | 1.4 pip | 0.7 pip | 5.5 pip | 8.25 | 11.0 |

Sources: cost-plane audit (EURUSD spread ~0.1p measured, slip ~0.1p/side,
commission $7/lot bound ≈0.7p; XAU spread 2.0p fixed evidence, slip p90
1.4p/side, same commission bound).

Suspect bars (etl suspect / hcc burst): trades filling or exiting on a
suspect M1 bar are flagged, never deleted; headline metrics report both
all-trades and clean-only PF.

## 4. Execution model (fixed)

- Decision bar = CLOSED tf bar t (shift>=1 semantics throughout).
- Pending stop at signal-bar extreme ± offset; fills from first M1 bar
  after t's close; expiry = ttl tf bars (unfilled pendings cancel).
- Gap fill: long entry = max(stop, m1.open); short = min(stop, m1.open).
- SL/TP on M1 bars from the fill bar; both inside one M1 bar -> SL first.
- Friday flatten: forced exit at open of first M1 >= Friday 20:00 London.
- One pending + one position per (symbol, config); signals while busy
  skipped.
- Weekly cap (J family only): max 5 new pendings per ISO week.
- No BE/trail/partial/pyramid/add-to-loser anywhere.

## 5. Config table (17 <= 22 per symbol; identical set both symbols)

Shared J base: fractal-2 swings, London 08-16 (J), leg-3 close beyond
Dragon + candle direction + trend side + dragon slope (mid vs mid-3),
prior-break veto, entry offset 3 pips, ttl 4 bars, SL = leg-0 extreme
∓ 0.1*ATR14 capped 120 pips (EURUSD), TP = first WHQ half-step >=15 pips
else 1.5R fallback, weekly cap 5. XAUUSD SL cap = 212.2 pips (formula:
120 * mdr_xau / mdr_eur on DESIGN; mdr_eur=119.9p, mdr_xau=212.0p
measured pre-freeze — derived constant, not tuned).

| id | change vs J | tag |
|----|-------------|-----|
| F0_J | — (control, never a candidate) | source-primary |
| F1_W2whq | +W2: wave origin within 0.25*ATR of WHQ level | source-primary |
| F1_W2swing | +W2: origin inside swing-cluster zone | community |
| F1_W3 | +leg-1 through Dragon required | source-primary |
| F1_W4a | +Dragon angle >=0.05 ATR/bar (N=5) | reconstructed |
| F1_W4b | +Dragon angle >=0.10 ATR/bar | reconstructed |
| F1_R1b | SL = big zigzag swing 48b ∓0.1ATR | reconstructed |
| F1_R2a | TP = nearest opposing zone edge >=1R | reconstructed |
| F1_R2b | TP = next WHQ whole/half >=1R | source-primary |
| F1_PV | +PVSRA agree (bias=side, mode=run) | reconstructed |
| F1_FULL | W2swing+W3+W4a+R1b+R2a+PV | composite (fixed) |
| F1_FULL_RE | F1_FULL + re-entry (S3.2) | composite |
| F2_NH_a | pullback-into-Dragon, SL pullback extreme | source-primary |
| F2_NH_b | same, SL big swing | source-primary |
| F3_LUCY_a | H1 trend -> M5 rejection touch, TP 1.5R | source-primary |
| F3_LUCY_b | same, TP nearest zone | source-primary |
| F4_BAI14 | EMA34-band bounce w/ EMA200/610, TP 2R | community |

Non-J family constants (fixed): pending offset 2 pips; F2/F4 ttl 4 M15
bars, F3 ttl 6 M5 bars; sessions: F2/F4 London-ext 07-16, F3 NY overlap
12-16 London; F3 H1 trend = last CLOSED H1 (open+3600 <= m5 open), close
vs H1 EMA89 and H1 dragon mid; F3 rejection = pin (wick>=2x body and
>=60% range) or engulfing, touching M5 dragon band or EMA89.
F1_FULL_RE re-entry: same wave key, close beyond outer band again within
20 bars of leg-2, one re-entry per wave.

## 6. J-parity protocol (harness validation, control only)

Run F0_J on J-PARITY window. Acceptance vs the 16/08 run (N=307, PF=0.94
on ~2000-01-03..2026-08-14): compare N against window-scaled expectation
N_exp = 307 * (23.4/26.6) = 270; PASS iff |N-270| <= 20% AND |PF-0.94|
<= 0.15. If N overshoots materially, evaluate the documented alternative
interpretation F0_J with w2='whq' gate (same config slot, noted in
PARITY_J) before concluding. Any other gap -> STOP the ladder, write
PARITY_J with the cause (data/spec/cost) and fix the harness first.
J parity uses M1 fills identical to the DESIGN sim — no separate engine.

## 7. Census (outcome-blind, DESIGN only)

Signals/week/symbol, long/short split, session split, pairwise overlap,
per-element removal counts vs F0_J. Configs <0.5 trades/week/symbol are
flagged sparse, kept in the table.

## 8. Selection rule (D5, fixed)

Advance to VALIDATION iff on DESIGN: PF x1 >= 1.20 AND PF x1.5 >= 1.05
AND >=1 trade/week/symbol AND positive P/L in >=60% of years AND real PF
beats the random-entry control at the 95th percentile. At most 3 configs
advance, ranked by expectancy * sqrt(trades). VALIDATION read ONCE;
pass = PF x1 >= 1.15 AND expectancy > 0. HOLDOUT stays sealed.

## 9. Controls (per config per symbol)

(a) Random entries, 100 seeds: same time-of-day and weekday distribution
    as the config's signals, same SL/TP geometry (risk in pips resampled
    from the config's own distribution, TP at the same R distance);
    report the percentile of the real PF.
(b) Direction flip: same signals, dir inverted.
(c) Time shift: signal bar +20 tf bars, same geometry.
Multiple testing: bootstrap the MAX PF across configs under control (a)
null (10,000 draws) -> best-of-N inflation; deflated Sharpe for top
configs = (E[R]-E[R_null])/sd * sqrt(N) correction reported.
MC: P95 max drawdown in R across 200 bootstrap orderings of each
advancing config's trade sequence (preregistered budget: DD P95 <= 30R
per symbol for promotion consideration).

## 10. Kill / reporting rules

- No new configs after this hash. No threshold tuning after D1.
- Sparse configs reported, not silently dropped.
- A result living in one year/hour/direction is reported as such.
- If nothing passes D5: do NOT recommend abandoning Sonic; write the 2-3
  cheapest next approaches from ladder anatomy + MFE/MAE evidence.
- Errors found after freeze -> erratum section in RESULTS.md.
