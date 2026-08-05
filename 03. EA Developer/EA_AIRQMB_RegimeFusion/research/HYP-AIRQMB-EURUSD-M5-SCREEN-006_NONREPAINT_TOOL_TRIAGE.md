# AIRQMB SCREEN-006 Non-Repaint Tool Triage

The conservative AlphaFactory scanner returned `FAIL`; that raw result is
retained in `HYP-AIRQMB-EURUSD-M5-SCREEN-006_NONREPAINT_TOOL_AUDIT.json` and is
not relabelled as a tool pass.

## Findings reviewed

1. `CopyBuffer(..., shift, ...)` at source line 255 is a generic helper. Every
   call site in `ReadSnapshot()` passes literal shift `1` or `2` (source lines
   270–286). No signal buffer is read at shift zero.
2. `iTime(..., 0)` at source line 774 is the new-M5-bar clock. It only compares
   the current bar's opening timestamp with `g_last_bar_time`; signal evaluation
   then reads the completed bar through shifts 1/2.
3. `iTime(..., 0)` at source line 823 seeds that clock during `OnInit()` and is
   not used as price, feature or signal data.
4. `collection_authority_verified=false` remains an unresolved metadata result
   from the scanner. The run itself is bound to the SCREEN-006 preregistration,
   receipt, source snapshot and registry terminal row, but this note does not
   reinterpret the scanner field as verified.

## Disposition

Manual call-site review finds no current-bar price/signal dependency in the EA.
The source-bound manual audit remains a separate `PASS`; the automated scanner
remains `FAIL` with the three conservative findings above. This disagreement
does not affect promotion because SCREEN-006 is already an economic kill and
has no optimization, validation, paper or live authority.
