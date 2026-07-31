# HYP-001 chart clock-semantics erratum

Date: 2026-07-27  
Status: `OLD CHART LABELS INVALID / CLOCK V2 AUTHORITATIVE`

The frozen sample and raw data are valid, but the first chart renderer repeated
the probe's semantic mistake by labeling the control ledger's `decision_time`
as the raw BREAK decision. In the parent EA, that timestamp is `bars[0].time`:
the **open** of the M5 bar that is recognized as a break only after it closes.
The EA evaluates `CopyRates(..., shift=1, ...)` and enters on the next-bar tick.

Observed reconciliation over the 230-trade challenger population:

- 229 rows: feature cutoff to actual closed-bar decision/entry = 300 seconds.
- one row: 330 seconds due observed entry latency.
- The CME window `[ledger decision_time-120s, ledger decision_time)` therefore
  ends before the M5 break bar starts and does not cover the actual decision.

Invalidated chart manifest only:

- `chart_manifest.json` SHA
  `5FB608CA480182B49CD914A0B44DC9CA5F770368DB14F08C87B4924143F2C3C0`.
- Its images must not be cited because their blue `BREAK decision` label is
  semantically false. Their pixels are retained for audit, not deleted.

Authoritative replacement:

- `chart_manifest_clock_v2.json` SHA
  `D64554DDF3AB0CC33C6F75AB0BA652E279190F027B921E3CF128C0F12FC3810A`.
- Clock V2 explicitly marks `feature cutoff / break-bar open` separately from
  `actual closed-bar decision / entry` and states that the actual decision is
  outside the CME window.
- The frozen 12-case IDs, sampling strata, price bars, book traces and outcomes
  are unchanged; only clock semantics and chart labels are corrected.

Impact on truth:

- The terminal economic KILL remains valid for the **exact frozen stale
  pre-break-bar feature object**.
- The intended causal claim, "CME book state immediately before the actual
  closed-bar decision," was not implemented/tested and cannot be inferred from
  HYP-001.
- This does not authorize shifting the old windows by five minutes and joining
  the already-opened DESIGN outcomes. A correctly aligned successor needs a
  fresh population, ID, source plan and pre-outcome contract.
