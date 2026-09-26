# 2026-09-12 — CELL 7: EA_CamarillaFade EURUSD M15 kill + mid-run LiveUpdate fingerprint hazard

## Result

| Field | Value |
|---|---|
| Hypothesis | HYP-CAMF-EU-M15-001 (Camarilla H3/L3 reclaim fade, 8-bar / 1.0 ATR) |
| Runs | `20260912_083342` (pass A, provenance fail) + `20260912_083640` (governed, complete loop end-to-end) |
| Window | 1999.01.01 → 2026.09.11 (`verified_m1_asof`) |
| History quality | **99%** (gate >97) |
| Trades | 14,755 — cadence **10.21/wk PASS** |
| Report PF / Net / DD | 0.886 / -5,458 USD / 57.1% |
| Cost PF x1.0 / x1.5 / x2.0 | **0.763** / 0.702 / 0.646 |
| MC p95 DD / Robustness | 57.6% / 14.3% |
| Overnight / weekend | 3 / 0 — FAIL |
| Verdict | REVIEW → **KILLED_AT_MODEL_0** |

## Provenance finding: mid-run LiveUpdate changes the server fingerprint

Pass-A run `083342` completed the full backtest + analysis chain
(economically negative: PF 0.886, -5,458 USD) then died at post-run
manifest identity binding:

    Post-run manifest identity 'server_fingerprint' does not match task packet.

Root cause: the portable isolate **LiveUpdated Build 6191 → 6192 during
the run itself** ("Adopted post-liveupdate tester PID" in the log). The
report/manifest therefore binds `server = MetaQuotes-Demo (Build 6192)`,
while the packet had been built from EURUSD cost evidence measured on
build 6191 → fingerprint mismatch. Not a builder formula bug — a real
environmental drift between evidence capture and execution.

Repair (provenance only, zero strategy change):

1. Re-measured EURUSD cost evidence on build 6192 (spread/slippage/
   commission evidence JSONs now carry `terminal_build: 6192`).
2. Regenerated the commission proxy CSV from pass-A real lifecycles
   (30 EURUSD positions, 7 USD/lot RT bound, observed=0).
3. Rebuilt the task packet with measured M15 data stats
   (quality 99%, bars 686325, ticks 387427329, to=2026.09.11) —
   `data_fingerprint 832AD496…` verified byte-exact against the manifest.
4. Second governed run `083640` passed the entire chain including the
   cost artifact (14,755 positions / 29,510 deals reconciled) and the
   non-repaint audit.

Lesson for the loop: **check terminal build drift when a fingerprint gate
fails before assuming artifact corruption.** The isolate auto-updates;
evidence measured under an older build must be re-measured (or the packet
re-pinned) if a run lands on a newer build.

## Economic reading

Camarilla H3/L3 reclaim fade on EURUSD M15, 1999–2026 verified-M1 window:

- Gross PF 0.886 — already below the 1.30 gate before costs.
- Cost-bound repricing pushes it to 0.763 @x1.0 → the mechanism has no
  edge even at the cheapest measured venue (spread p90 0.1 pips).
- Europe PF 0.88 / New York PF 0.89 — both sessions negative; no
  session-level rescue exists or was attempted.
- WFA diagnostic: avg OOS PF 0.95, 2/5 windows profitable — no signal.

## Cell tally (7 kills, 0 passes)

CRSI-R2 GBPUSD (data) · AMA XAU · VwapFade XAU · HourDrift XAU ·
GBBSqueeze XAU · IBSC EURUSD · **CamarillaFade EURUSD**.

EURUSD (cheapest venue) has now killed 2/2 mechanisms tried. Candidate
selection should prefer mechanisms that are structurally insensitive to
spread (longer holds, wider targets) or exploit EURUSD-specific
microstructure rather than importing XAU scalps.
