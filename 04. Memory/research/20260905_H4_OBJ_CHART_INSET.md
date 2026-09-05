# H4 OBJ_CHART inset on M5/M15 (2026-09-05)

Owner: M15/M5 must show a **large H4 frame, bottom-left**, with SMC attached.

TV Pine `IM2GxnOK` has **no** LTF H4 overlay. This is an MT5 affordance, not TV parity.

## Reuse (do not mint)

- Pattern: `ChartInChart.mq5` raw `ObjectCreate(..., OBJ_CHART)` + `OBJPROP_PERIOD/CORNER/XSIZE`.
- Not: spark `OBJ_RECTANGLE_LABEL` panel, not a second HUD, not `CChartObjectSubChart`.

## Contract

- Name: `g_prefix+"INSET_CHART"` (not under `HTF_` — RebuildVisuals used to wipe that prefix).
- Place with `CORNER_LEFT_UPPER` and `Y = chartH - height - pad`. `OBJ_CHART` has no ANCHOR; `LEFT_LOWER` pushes the box off the pane.
- Size: 42% × 36% parent, floor ~380×220, pad X=10 Y=24.
- Nested: `_Symbol`, `PERIOD_H4`, date+price scale on, B&W copied from parent. `ChartApplyTemplate(tb_smc_inset.tpl)` after save-before-create (`ChartIndicatorAdd` of this EX5 returns 4114).
- Nested HUD off: skip `UpdateHud` only when `_Period == InpHtfPeriod` AND `CHART_IS_OBJECT`. Do not gate the host on `CHART_IS_OBJECT` alone.
- Skip inset when chart TF == H4. MCP `chart_add_indicator` must pass `InpShowHud=1,InpDrawObjects=1,InpShowHtfInset=1` (bare add zeros bools).
- New inputs appended after the 46-slot contract (`InpShowHtfInset` default true).

Visual 2.40. Buffer contract stays 2.3.
