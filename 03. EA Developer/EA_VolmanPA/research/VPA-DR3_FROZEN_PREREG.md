# VPA-DR3_FROZEN_PREREG — trend-primary detector with barrier integrity

Task: T-VPA-DR3. Authority: `research/LEAD_DECISIONS_DR3.md` (F1–F7, binding) →
this prereg → code. Frozen BEFORE the census: the SHA256 of this file and its
mtime must precede every `PLAN/census_dr3/*` and `PLAN/grading_dr3/*` output.
No outcomes anywhere (F7/E4). Set 60 case đã burned (E3): chỉ dùng làm chẩn đoán.

## 1. Scope (F1)

DR3 is the LAST detector revision. Lane continues with option (B). If DR3 fails
its gates (F6 cadence or F5 fidelity), the Lead escalates to the Owner.

## 2. Hard gates (F2) — the only gates that decide

Order (first fail wins, `DR3_HARD_GATES`):

| # | gate | definition |
|---|---|---|
| 1 | warmup | `t >= 50` (signal-bar index) |
| 2 | session | v1 windows, UTC minutes: `eu = [300, 660)`, `us = [690, 1050)`; measured at the **trigger bar** (the bar that fires the entry), not at the signal bar |
| 3 | direction | D1a (tr.95): long → `close > open` or doji (`|body| <= 0.10 * range`); short → mirror |
| 4 | trend | DR1 parameters: `slope = d*(EMA25[t] - EMA25[t-6])/ATR >= 0.10` AND `frac_side >= 0.6` over the last 10 bars |
| 5 | **integrity** (new, tr.39–41) | let `eps = 0.10 * ATR[t]`; let `first_touch = min(touch indices <= signal bar)`; for every bar `i in [first_touch, signal_bar]`: `d * (close[i] - B) <= eps`. If the barrier has no touches ≤ signal bar → not evaluable (skipped, as a `None` gate). A level crossed by closes is not a barrier |
| 6 | cost | `rho = cost_pips / stop_pips = 1.0/8.0 = 0.125 <= rho_max = 0.20` |

Signal/entry mechanics (F2a, unchanged from DR2c):
- signal bar = the **last touch bar** before the breakout when the bar closes
  beyond `B + 0.25*ATR`; otherwise the bar itself when it closes inside
  `[B - 0.50*ATR, B + 0.25*ATR]` (long; mirror for short);
- entry = stop order 1 pip beyond the signal bar's extreme (`entry_buffer_pips
  = 1.0`), valid V = 3 bars, invalidation = `min(low[buildup_start..signal]) -
  0.10*ATR` (long; mirror);
- barrier expiry 20 bars; breakout beyond `B + 0.25*ATR` with no touch bar →
  consumed as a missed break.

## 3. Logged features (F3) — computed for every candidate, never decisive

Written per candidate into the census/trace output:

- **buildup**: chosen `n` (largest, `buildup_min..buildup_max` = 3..10),
  `start`, `band_closes` (closes in `[B-0.5A, B+0.1A]`), `touches`
  (extreme within `0.10A` of B), `overlap` (mean consecutive overlap),
  `contraction` (`median(TR window)/median(TR prior 12)`), `conditions_passed`
  (0–4: band_closes≥2, touches≥1, overlap≥0.45, contraction≤0.85), `cond_flags`,
  `squeeze` (|EMA−B| ≤ 0.6A and ≥2 bars containing EMA);
  variants: `v2of4` = largest n with ≥2 conditions; `vtight` = largest n with
  `band_closes >= 3` and `touches >= 2` and `contraction <= 0.85` (F3: the real
  tight buildup under the ceiling).
- **chop**: `chop` = legacy DR1 (4 bars before the signal bar: overlap ≥ 0.65
  and falling-lows frac ≤ 1/3 and (doji ≤ 0.35 body or long bar > 1.5A));
  `chop_window` = same metrics computed **only inside the buildup window
  `[start, signal]`** (F3: the impulse leg must not veto).
- **room**: nearest significant obstacle ahead of the entry, `room_r` in R
  (R = 8 pips); obstacles **inside the barrier zone are ignored** (F3):
  zone = `max(touch_extreme + eps, entry + max(eps, 0.5*R))` for long
  (mirror short); sources: ±5-bar pivots, active barriers, PDH/PDL, 00/50
  round grid; obstacle `{price, type, zone_price}` logged.
- **adverse magnet**: DR1 rule (pivots older than buildup_start, 0.5R band,
  skip within 0.10S) — boolean + info.
- **anti-chase**: `entry_b_atr`, `range_atr`, `ema_dist_atr` (DR1 thresholds,
  logged only).
- **EMA squeeze**: in the buildup dict.
- **pressure**: v1 `pressure[t]` boolean + `bars_since_pressure` (from the base
  detector).
- **lunch**: `utc_min in [660, 780) or [1020, 1140)` (tr.227/273 dead zones).
- **rho**: cost ratio.

## 4. Config (frozen)

`DR3_CFG` in `research/lab/vpa_dr1.py` = DR1 defaults +:

```
signal_atr = 0.50; signal_prev_bar = True
eu = (300, 660); us = (690, 1050)
hard_gates = ("warmup","session","direction","trend","integrity","cost")
integrity_eps_atr = 0.10
room_significant_only = True; room_include_pdh = True
room_zone_touch = True; room_zone_r = 0.5
chop_in_buildup = True; buildup_variants = True
round_grid_price = 50 pips   # book tr.43, as in the DR1 census
```

All DR1/DR2 knobs not listed keep their defaults (`stop_pips 8`, `entry_buffer
1 pip`, `V=3`, `theta_slope 0.10`, `frac_side_min 0.6`, `rho_max 0.20`, expiry
20, cost 1 pip).

## 5. Census (deliverable 3)

- cadence: accepted (executable) count; per week (span/7 days), per year
  (2016–2021), per session (eu/us);
- funnel: first-fail over the 6 hard gates + counters;
- feature distributions (median/IQR) for accepted vs rejected (rejected =
  evaluated in session with direction passing);
- burned-set recall diagnostic (A/B=16 vs C=44 accepted, **DIAGNOSTIC-ONLY**,
  E3), plus the F2c diagnostic "how many A/B vs C the integrity gate removes";
- no outcome columns.

**D2 verdict (F6):** `>= 10/week` NORMAL, `3 to <10` LOW_CADENCE, `<3` STOP.

## 6. Fidelity (deliverable 4, only if cadence >= 3/week) — F5

- Sample **120 accepted** + **60 rejected** candidates; rejected = evaluated in
  session with direction passing, then rejected by trend or integrity;
- stratified random by year (2016–2021), **excluding every bar within ±50 bars
  of the 60 burned cases**;
- shuffled into one blind set of 180 → `PLAN/grading_dr3/` with `INDEX_BLIND.csv`
  (case_id, symbol, decision_utc, side, entry, stop) and a hidden key
  (`KEY_HIDDEN_DR3.csv`, not opened by the graders); snapshots show **no bars
  after the decision bar**; DRAW_QA row per case;
- G1 and G2 grade blind with the unchanged `GRADING_RUBRIC_V2.md`; both files
  hashed BEFORE any unblinding; G3 grades the disagreements only; the majority
  decides;
- metric: `A/B share(accepted) - A/B share(rejected)`, 95% CI (Newcombe
  difference or bootstrap), reported for the dual-agreement count AND the
  majority count;
- **FIDELITY GATE PASS** = (difference >= +15pp) AND (CI lower bound > 0) AND
  (A/B share(accepted, majority) >= 40%);
- `LEAD_SPOTCHECK_INDEX.csv`: 20 blind cases (12 accepted, 8 rejected), no
  labels anywhere.

## 7. Evidence chain

Time fix (F4): `PLAN/dr3/TIME_SANITY.md` (before this prereg). Code: same
detector path as DR1/DR2 (`_dr1_gates` + `verdict_from_gates`), trace equality
test re-run. Tests: `test_vpa_dr1.py` (integrity +/-, room-zone, chop-window,
buildup variants, DR3 config, trace == detector, full suite).
