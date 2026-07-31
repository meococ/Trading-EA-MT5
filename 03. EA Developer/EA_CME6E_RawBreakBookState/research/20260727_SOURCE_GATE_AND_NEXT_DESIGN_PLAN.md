# CME 6E book-state source gate and next DESIGN plan

Date: 2026-07-27

Status: `SUPERSEDED_BY_TERMINAL_HYP-CME6E-RAWBREAK-BOOKSTATE-001_DESIGN_KILL`

This is source-feasibility evidence only. No hypothesis ID, registry row,
outcome join, feature threshold, MQL5 source, compile, Model 0, optimization,
promotion or live action was opened.

## Owner authority used

The Owner approved a maximum USD 1.00 for the exact bounded 261-window CME 6E
MBP-10 acquisition. No continuous dump, EBS data or other paid population was
requested.

## Validated source result

- Dataset/schema/symbol: `GLBX.MDP3` / `mbp-10` / `6E.v.0`.
- Window: `[decision_time_utc-120s, decision_time_utc)`.
- Plan v2 ID:
  `9EB45071C233F31EF8EA348F2DBF8053A62ECF53CBD94D99DE32E51748213D38`.
- Plan SHA256:
  `CD7DA4F331D7A52B0FEE5B7F9E82755FA2D342E8DA2AA055FA8F691B671FD929`.
- Manifest SHA256:
  `2F2018175DE9C3ED9EA18FC8701E2AE3A17E16DBFE66468EFB2F6455E9454B8C`.
- Validation receipt SHA256:
  `CA5EE2198B2F54394656488FF789E4BF7101A744CF6DD690721B0C51C1E00844`.
- Full decode/hash validation: 259/259 response files, 258 nonempty, one
  complete source-empty response at PID42, 257,009 decoded market records,
  7,110,174 compressed bytes.
- Live estimated billable bytes: 546,318,080.
- Live estimated cost: USD 0.254399180414. This is an API estimate, not an
  independently read invoice charge.
- Outcome fields used: false.

The first v1 run stopped after 19 files when PID42 returned a complete 101-byte
DBN stream with zero market-data records despite a positive 368-byte metadata
quote. The original plan, manifest and partial response were preserved under
`02. AlphaFactory/data/databento/cme_6e_mbp10_scc/evidence/blocked_pid42_20260727/`.
The v2 tool checkpoints a fully decoded zero-record response as
`source_empty=true` and never retries it. PID42 was adopted from the existing
file; no second paid request was made. Combined acquisition/planner regression
tests passed 16/16.

## Fatal population gate before outcome join

The acquired population is the 261 HYP004 HOLD-to-retest decision timestamps
over 208.714 elapsed weeks. Its absolute maximum cadence is
`261 / 208.714 = 1.250515059/week`; validated nonempty coverage is
`258 / 208.714 = 1.236141323/week`. The workspace minimum is 2/week, requiring
at least 418 decisions over the same interval.

Therefore no feature gate on this population can satisfy the Owner's cadence
goal: accepting 100% already fails, and filtering can only reduce cadence. The
261 object is parked without reading feature-versus-outcome relationships. Do
not create an EA or tune an acceptance threshold from it.

## Fresh next candidate, still pre-authority

The distinct next decision surface is every frozen raw first-close BREAK plus
causal CME 6E book state. It is not a HYP004 amendment: the price-only raw BREAK
control remains economically killed, while the new candidate adds primary
futures order-book information under a fresh future ID.

The metadata-only DESIGN plan uses only `position_id`, `decision_time` and
`direction` from the 1,112-row control ledger:

- DESIGN 2019-2020: 547 decisions (258 in 2019, 289 in 2020); 541 billable
  windows and six metadata-empty windows.
- Sealed OOS 2021-2022: 565 decisions; not quoted, downloaded or opened.
- Plan ID:
  `1825DC77A35F2794051BD83E5A35ED87C8952049FB08B47BEA1AF34E1802D98F`.
- Plan SHA256:
  `B780B7A4AD0F0C8B7CDF6A109DE41754C5F9CD88856D464085EE69513A1E24D5`.
- Planner tool SHA256:
  `686457183C03BECB92BAEBB7D090C8E7E1EBC4F9196BEC57BC6B83DB9486FAB2`.
- Metadata quotes were reused offline from the complete no-paid/no-outcome
  receipt SHA
  `FF06D9BD348EF4146AFBF84FA1CBED63F8A26F33F53B7B58ECD903F07FA92454`
  after a redundant live re-quote attempt returned HTTP 504. The final plan
  binds both planner and quote-receipt hashes and made zero network calls.
- DESIGN estimate: USD 0.339879676699 / 729,886,048 billable bytes.
- Recommended new-plan ceiling: USD 0.68.
- Paid request made: false; outcome fields used: false; OOS quoted: false.

The next paid action requires explicit Owner approval for plan
`1825DC77...02D98F` up to USD 0.68 while keeping the combined session ceiling at
the already approved USD 1.00. Only after DESIGN source validation may a fresh
hypothesis/registry/prereg freeze feature transforms and falsification gates
before any DESIGN outcome join.

## Executed successor closeout

The Owner subsequently approved exact plan `1825DC77...02D98F` up to USD0.68.
The acquisition full-decode/hash validated 541 responses (529 nonempty and 12
complete source-empty), six metadata-empty windows and 353,598 records. The
live API estimate was USD0.339879676699 for this plan and USD0.594278857113
combined with the prior cell; these estimates are not invoice-verified actual
charges. OOS 2021-2022 remained unquoted and sealed.

After source-only feature extraction, fresh
`HYP-CME6E-RAWBREAK-BOOKSTATE-001` froze the exact score, quality surface,
median threshold, three arms and kill gates before its sole DESIGN outcome
join. The N230 challenger returned PF0.527529, meanR -0.365156 and DSR
0.000001795, worse than both controls; only 2/11 gates passed. Terminal verdict:
`KILL_DESIGN_BOOK_ALIGNMENT_NO_POSITIVE_EXPECTANCY`. The authoritative readout
is `HYP-CME6E-RAWBREAK-BOOKSTATE-001_READOUT.md`; no OOS, MQL5, Model 0,
promotion, paper or live authority remains.
