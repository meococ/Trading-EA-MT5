# PROBE PLAN — HYP-BR-SESSDRIFT-EURUSD-H1-001 (frozen before any outcome read)

Status: FROZEN 2026-07-18, before any PnL of this object was computed. SHA256
bound into the registry row. Owner explicitly approved this probe by name
("Breedon-Ranaldo session seasonality") on 2026-07-18.

## 1. Identity

- `hypothesis_id`: HYP-BR-SESSDRIFT-EURUSD-H1-001 · `ea_name`: EA_EURSessionDrift
  (research-only; no `.mq5` exists or is authorized)
- Symbol/TF: EURUSD H1. Thesis: Breedon & Ranaldo (2013, JMCB; SNB WP 2011-04)
  intraday FX seasonality — EUR depreciates during the European morning and
  appreciates during the US session. Cited by the Owner MR v3 spec §4.3 as an
  optional overlay with an honest decay warning (source data 1997–2007).
- Object: UNCONDITIONAL time-of-day drift. Daily: SHORT EURUSD from the 07:00
  UTC H1 bar open to the 11:00 UTC bar open; LONG from the 13:00 UTC bar open
  to the 17:00 UTC bar open. No signal, no indicator condition, no overnight.
  Windows are engineering defaults anchored to the paper's session blocks,
  fixed in UTC (declared: no window tuning, no local-time variant, no post-hoc
  shifts — any window change is a new hypothesis).

## 2. De-dup (explicit, including the O-screen seal)

- `cron_20260717_2110` sealed a DESIGN-ONLY screen (`ZERO_KEEP_OHLC_ORTHOGONAL`)
  rejecting "calendar seasonality as primary" as killed-family densify/rebrand.
  That screen produced no probe evidence. This lane proceeds anyway under the
  workspace reopen convention (**Owner-new scope + de-dup clearance**): the
  Owner approved this specific probe by name, and the object is materially
  distinct from every killed session lane:
  - S528/S588 EA_LondonNY EURUSD + S622/S623 EA_SessionDrift: **conditional**
    London→NY momentum continuation (condition on the London move). This
    object has NO conditioning.
  - Greenfield "LNY EUR fade": a **fade of session imbalance** — opposite
    construction, also conditional.
  - "EUR Asian manipulation" / Asia-coil: Asian-session objects, different
    windows and mechanisms.
  - "Calendar seasonality" in the O-screen's usual sense (day-of-week /
    month-of-year): not this object (time-of-day drift with a primary-source
    citation, not a proper-noun rebrand).
  - The just-closed MR family (001/002): different family entirely (no
    detrended-z, no regime gates); nothing here reopens it.
- Honest adverse priors, stated up front: every ADJACENT session object on
  EURUSD was dead/breakeven (S528 PF 1.08, S588 PF 0.99); B-R's sample is
  1997–2007 with documented decay risk (spec §4.3); at ~2 trades/day the 1.5
  pip RT cost proxy is a high bar for a small drift. Expected outcome is
  skewed to KILL; the probe is cheap and terminal in either direction.

## 3. Data

Reuse the SHA-bound FivePercent EURUSD H1 parquet from the MR lane:
`03. EA Developer/EA_HybridRegimeMR/research/evidence/EURUSD_H1_2015_now.parquet`
(SHA recorded in the probe artifact), with the weekly-verified server→UTC
model (EU DST ≤2023, US DST ≥2024). Probe loads bars < 2023-01-01 ONLY
(read-filter); Holdout 2023+ SEALED, 0 bars loaded. Splits: Train 2015–2020,
Validation 2021–2022 (diagnostics); PRIMARY series = pooled 2015–2022
(consistent with the grid-study convention).

## 4. Execution rules (frozen)

- Entry at the OPEN of the window-start bar (07:00 / 13:00 UTC); exit at the
  OPEN of the window-end bar (11:00 / 17:00 UTC). Unconditional — no
  look-ahead exists by construction.
- A trade requires both its start and end bars to exist on the same UTC date
  with the exact hours; otherwise the day is skipped for that window (holiday
  / gap integrity). Skips are counted and reported.
- R unit = 2.0 × ATR14 (Wilder, same formula as the MR lane) of the last
  CLOSED bar before entry; gross_r = signed pips / R_pips. If ATR is NaN
  (warm-up) the day is skipped.
- TWO simulated arms (the full trial universe, N=2):
  - `book_nostop` (PRIMARY candidate): pure session hold, exit only at window
    end. This is the paper's object.
  - `book_sl` (secondary candidate): same entries with an intrabar stop at
    2.0×ATR14 (worst-case SL-first inside each bar); exit at SL price or
    window end. Live trading would need a stop; declared pre-outcome.
  Short-window-only and long-window-only figures are PARTITIONS of each arm
  (diagnostics for attribution), not separate simulations.
- Cost: x1 = 1.5 pips RT per trade (same UNVERIFIED_PROXY as the MR lane);
  no swap (no position crosses server midnight: windows end 19:00/20:00
  server at the latest). Stress ×1.5 / ×2.

## 5. Kill gates (ALL required for SURVIVE, on the primary pooled series of an arm)

| # | Gate | Threshold |
|---|---|---|
| 1 | Sample | n ≥ 1000 pooled (expected ~3600–3900) |
| 2 | Economics | PF@x1 ≥ 1.25 AND expectancy ≥ +0.02R@x1 |
| 3 | Stress | PF@x1.5 ≥ 1.25 AND PF@x2 ≥ 1.00 |
| 4 | Year consistency | ≥ 6 of 8 years positive net R@x1 |
| 5 | Concentration | no positive year > 40% of positive net R |
| 6 | Outliers | top-1 winner ≤ 5% of gross positive sum |
| 7 | Deflation | DSR ≥ 0.95 (N = 2 simulations; V[SR] across both arms) |

Expectancy floor note (declared pre-outcome, not a weakening): the workspace
0.08R floor was calibrated to 2–5 trades/week objects. This object trades
~9–10/week by construction; 0.02R/trade ≈ 0.18–0.20R/week — the same weekly
economic bar. PF and stress gates are unchanged.

Cadence note: ~9–10 trades/week exceeds the GOAL 2–5/week band. A SURVIVE
would be an economics flag only; book integration (sizing/selectivity) is a
separate Owner decision under a fresh prereg. No `.mq5`/Model 0 from this
probe. KILL if gates fail — no PARK (sample is huge by construction).

## 6. Artifacts

Hash-bound probe JSON (`br_sessdrift_offline_probe.v1`,
`promotion_eligible=false`, `cost_status=UNVERIFIED_PROXY`,
`holdout_bars_loaded=0`), trade ledger CSV, trial-log entries (2), readout,
single registry transition, hot.md/do_not_repeat updates at verdict.
