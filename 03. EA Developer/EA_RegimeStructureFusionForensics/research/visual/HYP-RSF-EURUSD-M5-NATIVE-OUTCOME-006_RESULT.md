# HYP-RSF-EURUSD-M5-NATIVE-OUTCOME-006 — native post-exit chart result

Status: `EVIDENCE_CAPTURE_COMPLETE`

Authority: forensic / engineering only. The seven short replays used Strategy
Tester Model 1 to reproduce frozen historical loser windows and capture the
real portable MT5 Visual Mode window. Their economic summaries are diagnostic
only; economic authority remains with the original Model 0 parent.

## Capture verdict

All seven cases passed the frozen visual acceptance contract:

- no `Skip to` fast-forward was used;
- the EA raised a case-specific flag one completed M5 bar after the frozen exit;
- the complete live `Strategy Tester Visualization` window was captured through
  Windows Graphics Capture while that flag was held;
- the native JPEG frame was losslessly re-containerized to PNG without pixel
  edits, and every file has a valid PNG signature at `1906x1025`;
- AlphaFactory imported the exact PNG, recorded its SHA-256 in the run manifest,
  and preserved the indicator sidecars and report.

| Case | Run | Accepted native PNG | SHA-256 |
|---|---|---|---|
| Breakout long | `20260807_060712` | `native_outcome_006/NATIVE_MT5_OUTCOME006_BREAKOUT_LONG.png` | `C71AF3D8C87B6C041265A0D44667A84E00E89976A21952BB0973D97229C6213C` |
| Trend long | `20260807_060941` | `native_outcome_006/NATIVE_MT5_OUTCOME006_TREND_LONG.png` | `8E25AE6BDA22B67E479C164B3692C1BB03D50E24C5C8EE0507FAB8C7B01E52BD` |
| Range long | `20260807_061214` | `native_outcome_006/NATIVE_MT5_OUTCOME006_RANGE_LONG.png` | `2379DA58942EA2C2F1304B289857E507632DF56297580859A1293A37C9DC6CFE` |
| Trend short | `20260807_061428` | `native_outcome_006/NATIVE_MT5_OUTCOME006_TREND_SHORT.png` | `367FC7D007EBC05653E7020C1E70181B9693B1AE85CEA546204C92F5260469E1` |
| Breakout short | `20260807_061639` | `native_outcome_006/NATIVE_MT5_OUTCOME006_BREAKOUT_SHORT.png` | `5720F0C9B757BFC19CFD2853A6AFB0771828170AACF4CC0E2CDBE52F40E1F00B` |
| Range short | `20260807_061855` | `native_outcome_006/NATIVE_MT5_OUTCOME006_RANGE_SHORT.png` | `3C3EDCA13AD513361BD6E6E72EC9750130FF5F6385A3105F1E5EE00D073318E6` |
| Extreme short loss | `20260807_062127` | `native_outcome_006/NATIVE_MT5_OUTCOME006_EXTREME_LOSS.png` | `D67E1A165D495AE13AE7284C750BA959B4D12B9AAC328587A102FDCAF0E2FDD3` |

The machine-readable entry-state join is
`HYP-RSF-EURUSD-M5-NATIVE-OUTCOME-006_ENTRY_DIAGNOSIS.csv`.

## What the real charts prove

### Trend and breakout entries chase completed movement

- Breakout long entered `+2.193` MBB half-widths from basis on the release bar
  and stopped in 4.98 minutes.
- Trend long entered `+1.634` half-widths from basis after upward displacement.
- Breakout short entered `-1.414` half-widths from basis while AIRD still held
  Range at 86.01% and VRC was Compression with bullish directional lean.
- The extreme short entered `-1.537` half-widths from basis beside a low sweep
  after a multi-session decline and stopped in 42 seconds.

Directional agreement is therefore not a runway test. AIRD, VRC, TB and QQE
can all describe the completed impulse correctly while the executable edge has
already decayed.

### Range entries are not structurally confirmed fades

- Range long was taken while TB bias and structure were down and QQE remained
  negative. A low sweep plus rising oscillator was accepted before bullish
  reclaim.
- Range short was taken while TB bias/structure were up and the AIRD posterior
  was nearly tied Bull 50.79% versus Range 48.95%. The trade had no bearish
  reclaim and stopped in 5.2 minutes.

The current router treats sweep and oscillator turn as votes. A sweep is only a
liquidity event; it is not a reversal until price accepts back through a stored
structure level.

### Temporal SEQUENCE-002 did not fix the causal defect

`HYP-RSF-EURUSD-M5-SEQUENCE-002` delayed entry by one to three bars but still
required four differently lagged indicators to agree on one confirmation bar.
It produced 48 trades, PF `0.5519`, and net `-2531.44`. The successor must give
each engine one non-overlapping role and use stored price events, not add more
same-bar votes.

## Role contract for the successor

1. AIRD supplies the held market state and ambiguity guard; it does not trigger.
2. VRC supplies volatility/compression permissions and risk scaling; its
   directional label does not overrule structure.
3. TB SMC supplies direction, stored reclaim/retest level and structural stop.
4. MBB supplies location and the economic objective (basis/outer band); its
   signal marker only arms a setup.
5. QQE supplies the final transition trigger only after price has reached the
   required location and reclaimed/retested structure.

Verdict: visual pipeline engineering-valid; original signal economic-invalid;
not promotion-ready. Open a fresh role-aware hypothesis. Do not tune the killed
same-bar or `SEQUENCE-002` mechanisms.
