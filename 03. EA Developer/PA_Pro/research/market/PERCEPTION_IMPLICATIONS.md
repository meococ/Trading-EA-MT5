> **FINAL v2 (REVIEW_3 PASS by Lead Ruling 4)**

# PERCEPTION_IMPLICATIONS — market evidence vs `params_v1.json`

Proposals only — the Lead rules and forwards to the Perception lane.
All numbers are DESIGN 2016–2021, core 4 symbols, prereg `abc8b5ba…`,
**post-REVIEW_2 corrected pipeline** (ledger T000393–396 superseding
T000380–387/T000391; suite `tests/` green, D32).  "Stable" = the
preregistered 4/6-year + 3/4-symbol sign rule.  "Not identified" = the
declared placebo cannot support the contrast — no evidence either way.

| param | spec v1 | market evidence | proposal |
|---|---|---|---|
| `abr_len` | 50 | ABR is the working scale everywhere; all level results are ABR-relative and stable. | Keep 50. |
| `ema_len` | 25 | P(|θ1 counter-pivot − EMA_L| ≤0.5·ABR) is monotone in L — no kink at 25 (M6 F-M). | Keep 25 as *arbitrary smooth guide*; do not treat EMA touches as events.  Any L≈20–50 equivalent. |
| `window_bars` | 84 | Level premium concentrates in the first ~3h (D=**+7.3pt** stable), ≈0 by ~5h; small residual +0.95pt at 8–24h; half-life ≈1h (M3 F-A).  >24h bins unidentified. | Keep 84 for drawing, but **weight/decay objects by age** — a level older than ~48–96 bars should be structurally downgraded. |
| `edge_tol` | max(1p, 0.25·ABR) | Bounce-event overshoot p50≈0, p90≈0.6–0.65 ABR pooled (≈1.4–3.5p); 0.25·ABR sits at ~p75–p90 (M3 F-O). | Keep.  Optionally ~0.35·ABR on GBPUSD. |
| `swing.confirm_pullback` | 4p / 0.8·ABR | θ=1–2.5·ABR DC pivots produced real, stable level premium (**+2.45pt S1 / +1.75pt S2**). | Keep. |
| `swing.min_swing_pips` | 6 | Not isolated; bound with pivot θ scale. | Keep. |
| `box.height_min/max` | 6–34p | Declared detector (1.5–6·ABR, W=30) yields heights p25/50/75 ≈ 12/17/24p EURUSD.  6–34p broadly consistent. | Keep; ABR-scaled bounds more symbol-robust than fixed pips. |
| `box.width_min/max` | 9–100 | Box life median 11–13 bars, p75 26–30 — consistent with span≥9 birth; few reach 100 (M4 F-BX). | Keep. |
| `box.poke_min/max` | 1–3p | Median poke depth ≈ 0.8–1.0p; P(reach opp ≤24b) ≈ 0.21 real vs **0.34–0.38 on equal-distance placebo** (M4b P-SHIFT, prereg T000392): real failed pokes traverse *less* — directionally contradicts Volman's run, sign-unstable → descriptive.  Deep bins thin. | Keep 1–3p; do NOT treat pokes as continuation-to-opposite-side signals; voided +13.8pt stays voided. |
| `box.breakout_edge_min_touches` | 2 | Used as-is at birth. | Keep. |
| `box breakout follow-through` | — | M4b Arm-IN race24: **+1.14pt, q=0.0075, stable** — real edge breaks follow through more than interior crossings at equal traversal distance (addendum result, pending REVIEW_3). | Weak positive: breakouts carry a small genuine follow-through premium vs non-edge crossings. |
| `box.tf_relabel_*`, `right_edge_*`, `reanchor_*` | spec | Not measured (drawing mechanics). | Unchanged. |
| `box.asia` 0–480 CET, h 8–27p, thin 10p | — | Asia range median 22.6p EURUSD / ~31p others; ≤10p ~3–4%; >27p ~35% EURUSD (M2). | Raise `asia.height_max_pips` to ~40p or per-symbol scale; keep thin=10p but expect it rare. |
| `pattern_line.touch_tol` | 1p / 0.25·ABR | Same zone physics as levels (F-O supports ±0.25–0.35 ABR). | Keep. |
| `pattern_line.min_touches` | 2 | Third+ touches on real θ2-pivot lines bounce **+7.2pt (x1) / +8.4pt (x2)** over identical-geometry placebos — stable (M5 F-TL, re-verified post-D26). | Treat the 3rd touch as a *legitimate bounce candidate*, not a breakdown warning. |
| `pattern_line.trigger_bars` | 12 | — | Keep (execution param, untested). |
| `pattern_line.context_*` | 3–8h, ≤4 touches | Level premium ≈0 by ~5h and ~0 at touch 3+ (M3 F-A/F-T); slope class no post-break effect (up p=0.077 just misses FDR). | `context_max_hours` ~4–6h; `context_max_touches` ≤3; drop slope-class conditioning. |
| `squeeze.max_bar_range_abr` | 0.8 | Not isolated as an event study. | No change; flag for future squeeze study. |
| `derived.room_rule_pips` | 14 | Pullback median depth ≈ 4.1·ABR; EURUSD ABR ~2.6p → 14p ≈ 5.4·ABR. | Keep for EURUSD; express as ~5·ABR or per-symbol pips. |
| `derived.low_vol_daily_range_pips` | 60 | Daily range ≤60p: EURUSD 36%, USDJPY 41%, AUDUSD 52%, **GBPUSD 9%**. | Per-symbol or quantile-relative (e.g. ≤p35) — 60p almost never fires on GBPUSD. |
| `derived.news_windows_cet` | 14:25–14:55, 15:55–16:10 | Spike clusters: 08:00 & 09:00 CET (8.9–9.0%), 14:00–15:00 (3.9%), 02:00 small. | Keep both; **add ~07:55–09:30 CET** — the largest un-captured burst. |
| `derived.magnet_*` | 12–30p / 10p | Rounds show no stable bounce (RND D +0.29pt ns; grid tests ns); cascades positive-signed but underpowered (F-C, +0.135 ABR @h12 ns). | Keep magnets as *context*, not reversal levels. |
| `derived.chop_bar_abr_mult`, `chop_overlap_bars` | 2.0 / 6 | M5 mildly mean-reverting everywhere (lag1 −0.03…−0.07; VR12 ≈0.90–0.97, ASIA/EU weakest). | Keep filters; chop is baseline behaviour. |
| `budget.structural_soft/hard` | 5 / 8 | Dense S1 field ~1.05M touches/symbol; age and touch-count are the strongest stable moderators. | Keep budget; selection should prefer **young (<3h), first-touch** objects. |
| Asia H/L as levels | implicit | **Confirmed continuation structure:** −1.43pt, significant + sign-stable — post-Asia the range is a breakout structure, not S/R. | Mark Asia levels as directional-break context, not bounce candidates. |
| PDH/PDL as levels | implicit | **−3.20pt, significant but year-unstable** — prior-day H/L lean toward continuation more than reversal. | Treat PDH/PDL as break/bias context; do not draw them as bounce zones. |

## Big-picture mapping

- **Confirmed (stable):** pivot-level premium ~1.8–2.5pt; first-touch
  and <3h freshness carry it (+7.3pt); zone ±0.25–0.35·ABR; third-touch
  on real pivot lines bounces (+7–8pt); M5 mean reversion everywhere;
  Asia H/L = continuation; M4b race24 +1.14pt (addendum, pending
  REVIEW_3).
- **Contradicted:** EMA25 specialness; slope-class effect on line
  breaks; blanket "retest/role-reversal" after clean breaks.
- **Inconclusive:** round-number cascades; buildup-before-break (ns).
- **Not identified (declared placebo too sparse, D22):** box-breakout
  race24 and failed-poke → opposite-edge on the P-RAND arm.  M4b
  P-SHIFT is the identified arm; its fb(0,1] −7.4pt is unstable →
  descriptive.

## Caveats

- All effects are *descriptive* contrasts on DESIGN; nothing here is a
  tradable signal (no costs, no entries).
- S1 pivot density makes absolute rates field-dependent; matched
  contrasts are valid but absolute probabilities are not portable to
  sparser fields.
- Round-number results cover rounds near the day open only (D5),
  enveloped by causal day-open ABR (D28).
