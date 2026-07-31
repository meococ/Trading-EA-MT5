# CME 6E break-bar transition source plan

Date: 2026-07-27  
Status: `METADATA QUOTED / OWNER SPEND APPROVAL REQUIRED / NO PAID REQUEST / NO OUTCOME`

## Decision

Proceed with a materially new, clock-correct source cell before opening a new
hypothesis. The candidate measures direction-aligned CME 6E MBP-10 transition
through the full closed M5 break bar and ends strictly at the actual next-bar
decision/entry. It does not shift HYP-001's opened 2019-2020 DESIGN windows and
does not change entry, stop, target or management.

Proposed future ID after source validation:
`HYP-CME6E-RAWBREAK-BOOKTRANSITION-002`. It is not yet in the registry and has
no preregistration or outcome authority.

## Frozen source surface

- Population: 565 raw first-close BREAK identities in UTC years 2021-2022
  (2021=278, 2022=287; BUY=274, SELL=291).
- Input fields read: `position_id`, `decision_time`, `open_time`, `direction`.
  No close time, price, stop, target, net, realized R or other outcome field was
  read by the planner.
- Window start: `decision_time`, semantically the M5 break-bar open.
- Window end: `open_time`, semantically the actual next-bar decision/entry.
- Duration: 564 windows of 300 seconds and one of 330 seconds.
- Dataset/schema/symbol: `GLBX.MDP3 / mbp-10 / 6E.v.0`.
- Four windows are metadata-empty; 561 are billable. Metadata-empty is source
  planning evidence only, not proof about decoded record contents.

This population was the sealed calendar slice under HYP-001. HYP-001 did not
quote, download, extract or join it. Opening it under a future HYP-002 still
requires a fresh source acquisition, source-only transform, registry row and
SHA-bound preregistration before any outcome join.

## Bound packet

- Plan ID:
  `C57B0AF9CAAB52095629C4D6F3BE449EA23629E02F9FA30C4F54C5CC164A1D1C`.
- Plan path:
  `02. AlphaFactory/data/databento/cme_6e_breakbar_transition_design/source_plan.json`.
- Plan SHA256:
  `BF478C4FF9B181E0BC7C38E55C9613D69B44DBF348CBC351EC0909583E25D7F6`.
- Planner SHA256:
  `95AC16109B8F73261CB549155F65FB2543A933CEB1EB4BFD43410101FC515406`.
- Planner test SHA256:
  `DFD70B90238C80FC77E8EDAA6E0E47AE63CAB3B5A40F60C2A7E21EBBA95B6642`.
- Parent control ledger SHA256:
  `07CDBD82D9BE6B9745484E5312F534B72C883AF8B61D8FB240D28EEE72FDC0D9`.
- Clock module SHA256:
  `A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52`.
- HYP-001 clock-forensics readout SHA256:
  `562A87F6FBD46E1F8C7EA5874E017A79193C8B9ECD16553F388CD9C2486EAFD8`.

## Cost and authority gate

- Live metadata estimate: USD `0.696219488984`.
- Estimated billable bytes: `1,495,119,968`.
- Planner's conservative two-times drift ceiling and recommended Owner ceiling:
  USD `1.40`.
- Metadata calls: 1,130; timeseries calls: zero.
- Paid request made: false.
- Outcomes opened: false.

The next action is blocked on explicit Owner approval of this exact plan ID and
a maximum USD ceiling. Acquisition must re-quote immediately before the first
paid call and fail closed if the live estimate exceeds the Owner ceiling. A
lower ceiling than USD1.40 is legal but may stop the lane if the quote drifts;
it may never be silently raised.

## Post-approval sequence

1. Build/hash-bind an acquisition authorization to the exact plan and Owner
   ceiling; download only the 561 billable windows with an in-flight journal.
2. Full-decode/hash validate every response; checkpoint complete zero-record
   responses as source-empty and never auto-retry them.
3. Freeze a source-only five-level transition transform and quality surface
   without outcomes. The mechanism compares early versus late break-bar depth,
   final alignment and persistence; no threshold is selected from PnL.
4. Only after source validation append the fresh HYP-002 registry/prereg packet,
   then perform one DESIGN outcome join with preregistered control/challenger,
   cadence, cost and futility gates.

No acquisition, outcome join, MQL5, Model 0, promotion, paper or live action is
authorized by this plan alone.
