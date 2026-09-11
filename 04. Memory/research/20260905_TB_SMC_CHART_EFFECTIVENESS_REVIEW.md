# TB SMC 2026 visual 2.45 — independent chart effectiveness review

Date: 2026-09-05
Reviewer: independent (did not implement this indicator)
Scope: live-chart visual tool on EURUSD M5/M15 with nested H4 `OBJ_CHART`. Not a git-diff review. Not a trading-edge claim.
Evidence: `02. AlphaFactory/tmp/smc_M5_v245.png`, `smc_M15_v245.png`, optional `smc_M5_v244.png`; `TB_Smart_Money_Concept_2026.mq5` visual 2.45; `04. Memory/research/20260905_H4_OBJ_CHART_INSET.md`.

## Summary

As a *visual SMC context tool*, visual 2.45 is effective on these M5 and M15 snapshots: a trader can read LTF BOS/MSS/CELL/void/sweep/trail on the parent and a real H4 SMC map in the bottom-left inset, with TV teal/pink on B&W candles and no LTF labels painting through the H4 interior. That is not a trading edge — one EURUSD screenshot does not show expectancy, and “looks like SMC” is not a signal. The remaining cost is density: the H4 child is internally crowded at scale 1, the inset hides a large slice of LTF history, and removing the navy HUD (Owner request) makes LTF bias implicit in Protected/Soft trail labels instead of a written BEAR/BULL.

## Chart read (from the snapshots)

**What a trader can actually see**

- Parent: EURUSD M5 (`smc_M5_v245.png`) and M15 (`smc_M15_v245.png`), last print 1.16132 on 4 Sep 2026. Candles are B&W (`default.tpl`). Overlay is teal `#2DD4BF` / pink `#FB7185` — not a greyscale SMC.
- LTF map is readable on the *right* of both charts: recent BOS/MSS, a CELL box, CE, dashed/solid void edges, `Protected H` (pink) and `Soft L` (teal). Sweep markers are the blue `x` plots, not chart objects.
- Nested pane is a real `OBJ_CHART` H4 (`EURUSD, H4` in the child OHLC header, comment `H4`), scale 1, no chart-shift gap, date+price scales on. History is ~6 Jul–3 Sep 2026, range ~1.139–1.171. That is HTF overview, not an 8-bar spark pretending to be H4.
- H4 child has its own SMC: BOS/MSS along the July–August rally, CELL, `SwpH`, `Protected L`. Nested HUD is off. Nested candles match parent B&W.
- LTF vs HTF trails disagree in a coherent way: LTF `Protected H` + `Soft L` ⇒ host bias bearish; H4 `Protected L` ⇒ nested bias bullish (`RebuildVisuals` trail labels). That is the HTF+LTF sentence the inset is for.
- v244 → v245: same drawings and inset; only the navy `TB SMC 2026 / Bias BEAR / Swing 5 / Edge FOCUS` box is gone.

**What is noise**

- M5 left of the weekend gap (4 Sep 04:25–15:05): Focus-mode last-N=10 BOS/MSS labels stacked on one session (`BOS`/`MSS`/`CELL`/`CE`). Usable if you already know the grammar; noisy if you want a clean tape.
- H4 child, last two weeks of the rally (mid-inset to right): `MSS`/`BOS`/`CELL`/`SwpH`/`Protected L` occupy the same few bars. This is the worst read on the screen.
- Parent grid copied into the child (`ApplyHtfInsetTheme`) adds extra lines inside an already small pane.
- The tall black M5 gap around 15:05 is the FX weekend, not an indicator smear.

**H4 inset usability**

- Usable as HTF *context*: uptrend from July, late-August high, pullback toward ~1.160–1.161, live H4 close aligned with LTF 1.16132. Size (~52%×46%, min 460×260) is large enough to see structure, not a postage stamp.
- Not usable as a precision H4 execution pad: scale 1 packs months into ~half the parent; labels collide on the recent swing. A trader cannot reliably pick which H4 BOS is “the” level without reading color+price scale.
- Inset does **not** sit on the parent price axis (right). Volume gutter under the box is padded (`TB_HTF_INSET_PAD_Y=24`).

**Do LTF labels smear the H4 interior?**

- On both v245 shots: no. Host `DRAW_` texts/rays that would sit in the box are gone; the interior is H4 candles + H4 SMC. `CHART_FOREGROUND=false` plus `ClipDrawObjectsUnderInset()` (`OBJ_NO_PERIODS`) is doing the job on this layout (live LTF trails sit *above* the inset, so they survive on the right).
- Clip is hide-whole-object, not a scissor. These two shots do not show live levels vanishing; that failure mode is layout-dependent (see Issue 2).

**HUD removal: help or hide?**

- Helps: v244’s 200×88 navy box covered the first M5 hour (top-left). v245 shows those candles. It was never colliding with the bottom-left inset.
- Hides: explicit `Bias BEAR`, `Swing 5`, `FOCUS`. Bias is still encoded (`Protected H`/`Soft L` vs `Soft H`/`Protected L`) if the trader knows the legend. Swing length and Focus/Full are not on the chart at all when the inset is on (`UpdateHud` returns early whenever `InpShowHtfInset` and `_Period != H4`).

## Effectiveness

- Useful:
  - Dual-TF SMC *map* on one screen: real H4 child with the same EX5, not a spark and not a second HUD.
  - LTF live edges (nearest BOS/MSS ray, CELL, void/CE, trail) stay on the right-hand working area.
  - Color contract matches Pine IM2GxnOK; B&W candles stay Owner `default.tpl`.
  - Clip + no nested HUD: H4 interior is not a sandwich of LTF text + navy panel.
  - M15 is the cleaner LTF of the two (same H4 child, less Focus-label spam).
- Not useful / harmful:
  - H4-child label pile-up at the August high — HTF *detail* is partly unreadable.
  - Inset footprint (~quarter of the pane plus 80px clip pad) deletes a large block of LTF history (M5 Asia/London morning sits under the box).
  - Without HUD, a trader who does not know Protected/Soft cannot read LTF bias at a glance.
  - FocusLastN=10 copied onto the nested H4 via host template is the wrong density for a scale-1 overview.
- Unknown without more evidence:
  - Live-ray survival when the working price sits inside the inset’s vertical band (clip AABB).
  - Cold-start if the first `ChartApplyTemplate` fails (`g_htfInsetApplyTried` never retries). These shots already have nested SMC, so this did not fire here.
  - Any other symbol/TF, replay, or live session besides this EURUSD 4 Sep 2026 window.
  - **Profitability / edge.** Do not infer one from these pictures.

**Owner question:** effective as a *chart* for HTF+LTF Smart Money *context* on M5/M15 with nested H4 — **yes, with the density and HUD-legend caveats above.** Not effective as proof the tool makes money.

## Issues

### Issue 1 -- Severity: suggestion
- File: `TB_Smart_Money_Concept_2026.mq5:2044-2071` (Focus cap + unoffset `OBJ_TEXT`); Snapshot: `smc_M5_v245.png` and `smc_M15_v245.png` H4 child, right half
- Description: Nested H4 inherits host `InpFocusMode=true` / `InpFocusLastN=10`. Ten BOS/MSS labels plus CELL / `SwpH` / `Protected L` land on the same August swing. No collision offset. The HTF map is visible as a *shape* (rally then pullback) but individual labels overwrite each other.
- Suggestion: When `CHART_IS_OBJECT` (or `_Period == InpHtfPeriod` inside the inset), cap structure labels harder (e.g. last 3–4), drop `CELL`/`Protected` if they share an anchor bar, or raise nested scale only for the last swing — do not copy LTF FocusLastN onto a months-long scale-1 pane.
- Status: open

### Issue 2 -- Severity: suggestion
- File: `TB_Smart_Money_Concept_2026.mq5:1460-1517` (`ClipDrawObjectsUnderInset`, especially `OBJPROP_RAY_RIGHT` → `x2=chartW` then hide whole object); `pad=80`
- Description: Clip is an AABB hit-test that sets `OBJ_NO_PERIODS` on the entire object. Any live `RAY_RIGHT` whose Y overlaps the inset band (bottom ~46% + 80px) disappears from the *right* side too, not only under the box. These snapshots do not show that (Protected H / Soft L sit above the box). It is a real failure mode if the trader zooms so working price is in the lower half.
- Suggestion: Do not hide the nearest live trail/void/BOS rays; or clip only objects whose *visible* segment is mostly inside the inset; shrink pad from 80 toward the border.
- Status: open

### Issue 3 -- Severity: suggestion
- File: `TB_Smart_Money_Concept_2026.mq5:1082-1100` (`UpdateHud` early-return when inset on); Snapshot: `smc_M5_v244.png` vs `smc_M5_v245.png`
- Description: Owner asked to delete the blue box; that is honored and it frees top-left candles. Cost: Swing=5 and FOCUS/FULL are gone, and LTF bias is only in trail wording. A reader who treats `Protected H` as a TV “protected high” without the bias rule will misread.
- Suggestion: Keep HUD off. Optional: one short `CHART_COMMENT` or inset-header fragment (`M5 BEAR · H4 BULL`) that does not cover candles or the price axis.
- Status: open

### Issue 4 -- Severity: nit
- File: `TB_Smart_Money_Concept_2026.mq5:175-177,187-192,1327-1353`; Snapshot: both v245 parents, left-bottom
- Description: Default 52%×46% (clamped 45–58 / 40–52), floor 460×260, pad 10/24, plus clip pad 80. On M5 this covers almost the entire pre-gap session. Correct HTF affordance; heavy LTF occlusion. Research note `20260905_H4_OBJ_CHART_INSET.md` still documents visual 2.40 / 42%×36% / ~380×220 and is stale versus 2.45.
- Suggestion: If LTF tape matters more than HTF overview, drop toward the clamp floor (45×40) or make scale/size a chart-profile instead of one global default. Update the research note so the next reviewer does not grade 2.40 geometry.
- Status: open

### Issue 5 -- Severity: nit
- File: `TB_Smart_Money_Concept_2026.mq5:1585-1588` (`g_htfInsetApplyTried` one-shot)
- Description: First `ChartApplyTemplate` is never retried if it fails before `HtfInsetHasSmc`. These shots already show nested SMC, so this is not a live visual defect here — only a cold-start footgun.
- Suggestion: Retry on timer while `!g_htfInsetAttached`, then give up with a Print; do not latch failure on the first tick.
- Status: open

No snapshot bug was found for: LTF text inside the H4 child, HUD-on-price-axis, B&W SMC overlay, spark-as-H4, or HtfCountdown weekend `gap` (HTF panel is deleted while the inset is on). Compile was not re-run; claimed 0 errors / 0 warnings is trusted per product facts.

## Constraints honored

No MT5 start, no `mt5.initialize(path=...)`, no `trade_*`, no source edits, no commit/push, no worktree. Review file only.
