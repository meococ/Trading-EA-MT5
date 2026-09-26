# INDICATOR_LAYER_SPEC — drawing the armed pro lines in VPA_Vision (T-VPA-LINE-1)

Scope: **spec only**. `03. EA Developer/VPA_Vision/VPA_Vision.mq5` and
`VPA_Core.mqh` are owned by VIS-1; this task edits neither. Everything below is
the contract VIS-1 needs to add a "prepared lines" layer on top of the frozen
DR3 forensic view. Source of truth for the geometry = `research/lines/vpa_lines.py`
(module docstring carries the book pages); where this spec and the Python
disagree, **the Python wins** and the difference must be listed in
`PLAN/vis1/GATE_MAP.md` or the parity report.

## 1. Why this layer exists

The DR3 barrier layer draws a micro-line: two nearby lag-2 pivots within
0.10xATR, horizontal, alive 20 bars (tr. 87-110 read narrowly). The Owner's
question ("why is there no line drawn in advance?") is answered by a second
layer that shows the lines a Volman trader prepares *before* price arrives:

| line type | book | what it is |
|---|---|---|
| `level` | tr. 39-41, 90, 94, 99 | ceiling/floor that held several times (touch cluster from lag-3 swings, zone 0.35xATR) |
| `box_top` / `box_bottom` | tr. 156 | boundary of a tight range (height <= 5xATR, width:height >= 3:1) |
| `trendline` | tr. 95, 109 | line through the important swing highs/lows, adjusted on later touches |
| `flag_upper` / `flag_lower` | tr. 113 | boundary of a consolidation hanging on a pole (flag <= 0.5x pole) |
| `tri_upper` / `tri_lower` | tr. 101, 105 | converging boundaries (triangle) |
| `round` | tr. 43, 45 | 00/50 grid level once price comes within 8xATR |
| `pdh` / `pdl` | tr. 42/44, 98-99, 234/244 | prior UTC-day high/low, known at the first closed bar of the day |
| `sess_hi` / `sess_lo` | tr. 355, 362 | running high/low of the EU (05:00-11:00 UTC) / US (11:30-17:30 UTC) session |

Each armed line carries: kind, side (ceiling/floor), anchors, slope, touches
(count + bar times), age in bars, integrity (no close through it since
formation), visibility in ATR, HTF-swing alignment (lags 3/6/12 = M15/H1
proxy), and the significance score.

## 2. Object contract (reuse, do not mint)

One object type per role, all under a new prefix `VPA_LN_` (the existing
`VPA_VIS_` prefix and `ObjectsDeleteAll(0,VPA_VIS_)` stay untouched):

| role | object | notes |
|---|---|---|
| line body | `OBJ_TREND` | `RAY_RIGHT=false`, two anchors: horizontal = `(t_born, level)` to `(t_now + InpLineExtendBars, level)`; diagonal = the fitted line evaluated at `t_born` and `t_now + InpLineExtendBars` |
| touch marker | `OBJ_ARROW` code 159 | at the touch bar, price = high (ceiling) / low (floor) |
| score label | `OBJ_TEXT` | `"LEVEL 0.71"` / `"TREND 0.80"` ... right of the line end, offset `InpLineLabelOffsetPoints` (default 30), anchor `ANCHOR_LEFT` |
| broken marker | same `OBJ_TREND`, `STYLE_DASH` + `InpColorLineBroken` | a broken line stays for the role-reversal window (48 bars; 24 for trendlines) |

No `OBJ_HLINE` (it cannot carry a start time), no new object type, no
`OBJ_RECTANGLE` for boxes (the two boundaries are enough, as in the Python
snapshots).

## 3. Inputs (append after the existing VIS-1 inputs)

```
input group "--- Prepared lines (LINE-1) ---"
input bool   InpShowLines          = true;   // draw the armed pro lines
input bool   InpShowLineTouches    = true;   // dots on every counted touch
input bool   InpShowLineLabels     = true;   // "TYPE score" at the line end
input int    InpMaxLines           = 8;      // chart-hygiene cap (Python: max_lines)
input double InpMinLineScore       = 0.50;   // armed = score >= threshold
input int    InpLineDrawBars       = 2000;   // newest N bars drawn (0 = whole depth)
input int    InpLineExtendBars     = 2;      // projection beyond the last closed bar
input int    InpLineLabelOffsetPoints = 30;
input bool   InpLineShowLevel      = true;   // per-type toggles
input bool   InpLineShowBox        = true;
input bool   InpLineShowTrendline  = true;
input bool   InpLineShowFlag       = true;
input bool   InpLineShowTriangle   = true;
input bool   InpLineShowRound      = true;
input bool   InpLineShowPd         = true;
input bool   InpLineShowSession    = true;

input group "--- Prepared line colors ---"
input color  InpColorLineLevel     = C'15,118,110';   // #0F766E teal
input color  InpColorLineBox       = C'124,58,237';   // #7C3AED violet
input color  InpColorLineTrend     = C'37,99,235';    // #2563EB blue
input color  InpColorLineFlag      = C'219,39,119';   // #DB2777 pink
input color  InpColorLineTriangle  = C'234,88,12';    // #EA580C orange
input color  InpColorLineRound     = C'107,114,128';  // #6B7280 grey
input color  InpColorLinePd        = C'202,138,4';    // #CA8A04 gold
input color  InpColorLineSession   = C'8,145,178';    // #0891B2 cyan
input color  InpColorLineBroken    = C'120,120,120';  // dashed role reversal
```

The same palette is used by the Python snapshots
(`research/lines/lines1_common.py:KIND_COLOR`), so a screenshot and a chart
screenshot can be compared side by side.

## 4. Port checklist (what VIS-1 must implement)

All constants live in `vpa_lines.DEFAULTS`; the values below are the ones that
change behaviour (copy them verbatim, do not "improve"):

| constant | value | meaning |
|---|---|---|
| `level_pivot_lag` | 3 | swings that stand out over +-3 bars seed levels/trendlines |
| `level_eps_atr` / `level_min_touches` | 0.35 / 2 | touch zone / minimum touches |
| `level_max_age` / `level_seed_ttl` | 288 / 96 | 1-touch seeds die after 96 bars, levels after 24h |
| `level_break_atr` / `level_break_keep` | 0.25 / 48 | close through = broken; role reversal for 48 bars |
| `level_max_per_side` | 5 | chart hygiene at seed time (tr. 87/88) |
| `box_min_bars` / `box_max_height_atr` / `box_min_aspect` | 12 / 5.0 / 3.0 | box window + tr. 156 aspect |
| `tl_lookback` / `tl_max_pivots` / `tl_max_per_side` | 160 / 8 / 2 | trendline candidates + hygiene |
| `tl_slope_min_atr` / `tl_slope_max_atr` | 0.02 / 0.40 | tr. 122 slope bounds |
| `tl_break_atr` / `tl_break_keep` | 0.25 / 24 | close through kills a trendline |
| `pole_min_atr` / `pole_max_bars` / `flag_pole_frac` | 2.5 / 60 / 0.5 | flag = tight consolidation on a pole (tr. 113) |
| `tri_slope_eps_atr` | 0.02 | converging boundaries = triangle |
| `round_grid_pips` / `round_near_atr` | 50.0 / 8.0 | 00/50 grid (tr. 43); low-vol grid 20 = tr. 417 |
| `sess_windows` | eu (300,660), us (690,1050) | UTC minutes, same as the frozen DR3 |
| `htf_lags` / `htf_tol_atr` / `htf_weights` | (3,6,12) / 0.60 / 0.5,0.8,1.0 | M15/H1 swing alignment |
| score weights | 0.35 touch, 0.20 age, 0.25 visibility, 0.20 HTF | `touch/4`, `age/96`, `vis/3` saturate |
| `score_threshold` | 0.50 | armed |
| pruning | max 8 lines, max 2 per kind, merge 0.15xATR | chart hygiene |
| `stale_bars` | 192 | no touch for 16h -> the line is redrawn (tr. 148) |

Causality (same contract as the Python): pivots are confirmed `lag` bars late;
the rolling window is `[s..t]`; a line exists only from `created_idx`; the
forming bar is never fed; one redraw per closed bar. The port must reproduce
`armed_at(t)` exactly: same touches (min separation 2 bars), same visibility
(max excursion between consecutive touches, normalised by the ATR at the
excursion bar), same integrity (a close through the line by more than
`break_atr`, evaluated against the side at the previous close), same score.

MQL5 notes:
- `_fit_line` (least squares) is a 6-line helper; `statistics.median` is not
  needed anywhere in the line engine.
- the rolling window is two monotonic deques in Python; in MQL5 a bounded array
  scan over `[s..t]` (t-s <= the box window) is enough at 5-minute cadence.
- `VpaUtcMinute()` already exists in `VPA_Core.mqh:266` and is the only clock
  the session/pd lines may use.
- the day change uses `(long)bar.t/86400`, as `CVpaDr3` already does.

## 5. Drawing rules

1. Draw only lines with `score >= InpMinLineScore`, after the same pruning
   (sort by score, cap 8, cap 2 per kind, merge same-price within 0.15xATR).
2. Draw from `max(created_idx, t - InpLineDrawBars)`; never draw a line before
   the bar at which it became knowable.
3. Intact = solid, width 1; broken = dashed grey (role reversal); the label
   shows the type + score to 2 decimals, e.g. `FLAG+ 0.83`.
4. Touch markers only for touches inside the drawn window.
5. `ObjectsDeleteAll(0,"VPA_LN_")` once per rebuild, then draw; keep the
   existing single-redraw-per-closed-bar pattern (`VPA_Vision.mq5:121`).
6. Object budget: 8 lines x (1 body + up to 32 touches + 1 label) <= ~272
   objects, drawn over the newest `InpLineDrawBars` bars. No panel, no HUD
   (the DR3 ATR panel stays bottom-left as shipped; the line labels live at the
   right edge of the chart, so the AGENTS.md "HUD must not cover the price
   column" rule is respected by construction).
7. Weekend/session gaps: horizontal lines simply span them; no gap arithmetic.

## 6. Parity / acceptance for VIS-1

- Add an export mode next to `InpExportCsv` that writes one CSV row per
  `(bar_time, kind, side, level, slope, touches, age, integrity, score)` for a
  window, from the MQL5 port.
- Compare with `research/lines/vpa_lines.py` on the same window (same server
  timestamps -> UTC like `VPA_Vision_Parity` does). PASS = identical armed sets
  per bar (kind + level within 0.01 pip + score within 0.005) and 0 repaints.
- Snapshot requirement (INDICATOR_WORKFLOW §5): real MT5 window screenshot on
  EURUSD M5 with the line layer on, reviewed PASS before "done".
- Until that parity exists, this layer is a **design**, not a shipped feature.
