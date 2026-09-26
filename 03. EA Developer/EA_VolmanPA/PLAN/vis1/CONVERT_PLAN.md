# CONVERT_PLAN — T-VPA-VIS-1 / VPA_Vision (DR3 forensic indicator)

Task: T-VPA-VIS-1 (LANE VPA, PHASE VIS-1). Source of truth = the frozen Python
code path, not the prose:

- `research/lab/vpa_dr1.py` — `Dr1Detector`, `DR1_DEFAULTS`, `DR3_CFG`,
  `DR3_HARD_GATES`, `GATE_ORDER`, `verdict_from_gates`, `full_fail_set`.
- `research/lab/vpa_core.py` — `Detector` engine (ATR/EMA/CLV/pressure/bias,
  pivots, touch-cluster barriers).
- `research/lab/vpa_data.py` + `vpa_random_baseline.eu_server_offset_hours` —
  server→UTC conversion incl. the modulo fix (`PLAN/dr3/TIME_SANITY.md`).
- `research/VPA-DR3_FROZEN_PREREG.md` — DR3 config (SHA A61F06BA…).

Nothing is invented. Where the prereg prose and the code disagree, **the code
wins** and the difference is flagged in `GATE_MAP.md`.

## Write root (research result, deviation from the packet default)

`02. AlphaFactory/alpha.ps1` resolves a compile target through
`tools/ea_contract.ps1:Resolve-EaSourceContract`. For a non-`EA_*` name the
canonical source is, in order: `<repo>/<Name>.mq5`, `<repo>/Indicator/<Name>.mq5`,
`<repo>/Indicator/<Name>/<Name>.mq5`, else `03. EA Developer/<Name>/<Name>.mq5`.
There is **no** contract path that reaches `03. EA Developer/EA_VolmanPA/mql5/`,
so the packet default would be uncompilable. Existing indicator packages
(`SMC_Order_Block_Detector`, `QQE_MOD`, `Modern_Bollinger_Bands_GBB`, …) live at
`03. EA Developer/<Name>/` (`03. EA Developer/README.md:15`). Therefore:

| artifact | path |
|---|---|
| indicator | `03. EA Developer/VPA_Vision/VPA_Vision.mq5` |
| shared engine (single logic path) | `03. EA Developer/VPA_Vision/VPA_Core.mqh` |
| parity harness (script) | `03. EA Developer/VPA_Vision_Parity/VPA_Vision_Parity.mq5` |
| plan / parity / guide | `03. EA Developer/EA_VolmanPA/PLAN/vis1/` |
| review | `03. EA Developer/EA_VolmanPA/research/REVIEW_VIS1.md` |

Compile: `& "./02. AlphaFactory/alpha.ps1" compile "VPA_Vision"` and
`compile "VPA_Vision_Parity"`. The harness reaches the engine with a
`../VPA_Vision/VPA_Core.mqh` include (same convention as
`EA_BoundaryEdge.mq5:29-30`).

## Layer map (task item → MQL5 surface)

| # | requirement | MQL5 surface |
|---|---|---|
| 1 | barrier lines + touch markers, dashed grey + `integrity` label when the integrity gate fails | `OBJ_TREND` per locked barrier (lock bar → end bar), `OBJ_ARROW`/tick per touch bar, `OBJ_TEXT` `integrity` |
| 2 | EMA25 + ATR exactly as Python | plot 0 `DRAW_LINE` from the ported `ema[]`; ATR panel (text + spark) from the ported `atr[]` |
| 3 | signal bar highlighted, entry/stop(S=8)/target(16) lines, ACCEPT/SKIP label with failed hard gates | `OBJ_RECTANGLE` on the signal bar, 3 `OBJ_TREND` from `sig` to `sig+V`, `OBJ_TEXT` |
| 4 | label features: `room_r`, blocked obstacle as a short orange line, `ema_dist_atr`, squeeze, lunch | label text + `OBJ_TREND` obstacle line |
| 5 | toggles / depth / colors | `InpShow*`, `InpHistoryBars`, `InpColor*` (list frozen below) |
| 6 | server→UTC like `vpa_data.py` incl. modulo fix | `VpaUtcMinute()` in `VPA_Core.mqh` (EU DST = last Sunday Mar/Oct + 1h server) |

## Frozen input list (contract for code + HOW_TO_USE.md)

```
InpShowBarriers=true, InpShowTouchMarkers=true, InpShowEma=true,
InpShowAtrPanel=true, InpShowEvents=true, InpShowObstacle=true,
InpShowAccepted=true, InpShowRejected=true,
InpHistoryBars=20000, InpMaxEvents=300, InpLabelFontSize=8,
InpLabelOffsetPoints=40, InpAtrPanelBars=60,
InpColorBarrierUp=clrDeepSkyBlue, InpColorBarrierDn=clrOrangeRed,
InpColorBarrierBad=clrDimGray, InpColorTouch=clrSilver, InpColorEma=clrGoldenrod,
InpColorAccept=clrLimeGreen, InpColorSkip=clrTomato, InpColorEntry=clrRoyalBlue,
InpColorStop=clrCrimson, InpColorTarget=clrMediumSeaGreen,
InpColorObstacle=clrDarkOrange, InpColorLabel=clrWhiteSmoke,
InpColorAtrPanel=clrSlateGray
```

## Non-port decisions (documented, not silent)

1. **Closed bars only.** The detector runs over `[0, rates_total-2]`; the
   forming bar is never fed to it, so nothing repaints (Python's decision time =
   close of a completed M5 bar).
2. **Slice start aligned to a UTC-day boundary** so the day H/L tracker
   (`_update_bar`) sees full days inside `InpHistoryBars`.
3. **ATR is not a second window.** One MQL5 file = one window; ATR is shown as a
   panel (numeric + spark) plus `ATR`/`ema_dist_atr` on every event label.
   Values come from the same ported `atr[]`/`ema[]` arrays the gates use.
4. **`integrity` barrier marking** = the integrity gate failed on at least one
   evaluation of that barrier (the level was crossed by closes). Per-evaluation
   integrity is on each label's fail set.
5. **`room`/`stop` lines are only drawn when Python has `entry != None`** (i.e.
   a buildup was found); otherwise the label states the missing prerequisite.
6. **M5 only** unless `InpAllowNonM5=true` (params are M5-tuned and the UTC
   session clock is expressed in M5 close times).
