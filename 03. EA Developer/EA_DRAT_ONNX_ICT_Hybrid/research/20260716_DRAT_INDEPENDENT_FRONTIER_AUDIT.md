# DRAT Independent Frontier Audit

Date: 2026-07-16

Verdict: `NO_LEGAL_LOCAL_CANDIDATE`

This audit was performed after the terminal result of
`HYP-DRAT-ONNX-ICT-M15-EUR-001`. It does not open a new hypothesis and does
not authorize model export, EA source, compilation, or Strategy Tester work.

## Why the current brief cannot produce DRAT-002

The DRAT document supplies a useful software architecture, but its only
quantified decision object in the current package is the causal
sweep -> MSS/CHOCH -> FVG/OB retest mechanism with regime and breakout gates.
The frozen OOS probe already falsified that object:

| Route | N | Trades/week | PF | Net |
|---|---:|---:|---:|---:|
| Rules-only control | 402 | 3.0855 | 0.7642 | -67.752R |
| ONNX-gated challenger | 287 | 2.2029 | 0.7488 | -52.824R |

The challenger was negative in 2024, 2025, and partial 2026. Changing model
type, labels, probability threshold, session, RR, hold time, or ICT thresholds
would consume the just-read result and is therefore a post-hoc rescue.

## Independent local-family cross-check

The only plausible omitted local family was Gold -> USDJPY inverse lead.
Historical log entry S673 reported PF 1.26 with 456 trades, but it selected only
Monday and Thursday in the 15:00-18:00 server window. S676 and S699 narrowed
the calendar further. These variants do not satisfy the no-calendar-mining
standard for a new DRAT decision object.

A later closed-bar implementation explicitly removed the Mon/Thu-only filter
while retaining its preregistered 15:00-18:00 session and weekend-flat rule:

- source snapshot:
  `02. AlphaFactory/runs/EA_M15GoldJPYLead/20260714_001343/snapshot/source/EA_M15GoldJPYLead.mq5`;
- Model 0 window: USDJPY M15, 2021-01-01 through 2025-12-31;
- report: 99% history quality, 931 trades, PF 0.97, net -$710.49, balance DD
  16.48%;
- cadence: approximately 3.57 trades per elapsed calendar week.

The unmined transfer therefore had enough cadence but no edge. Adding an ONNX
or ICT gate after reading that result would be another same-family rescue.

The portfolio audit also found zero of 217 identity-valid historical runs met
both PF and elapsed-week cadence conditions. The canonical pointer to that
audit is stale on disk, but the original file remains recoverable read-only
from Git blob:

```powershell
git show 'b709309:03. EA Developer/EA_SonicR/research/20260710_EA_FAILURE_PORTFOLIO_AUDIT.md'
```

## The remaining genuinely independent information sets

No matching files for options-implied state, open interest by strike, signed
exchange trades, market depth, MBO, or L2 were found in the workspace.

Two information sets remain scientifically open:

1. FX options-implied state: EUR/USD risk reversal, implied-volatility skew and
   term structure, or real options open interest/dealer positioning.
2. Primary-market order flow: CME 6E or EBS point-in-time trades and order-book
   state, with signed aggressor flow or enough trades/quotes to infer it without
   future information.

CME documents that historical settlements, trades, top-of-book, market depth,
and MBO are distributed through DataMine. The public Daily Bulletin exposes
current/previous-trade-date volume and open interest, but it is not a complete
historical point-in-time surface for a 2020-2026 train/OOS study.

Official references:

- https://www.cmegroup.com/market-data/real-time-and-historical-data.html
- https://www.cmegroup.com/datamine.html
- https://www.cmegroup.com/market-data/daily-bulletin.html
- https://www.cmegroup.com/market-data/browse-data/catalog/ebs-spot-fx-and-ndf-ultra-binary.html

## Minimum reopen contract

Open a fresh hypothesis only after an Owner-approved dataset is present on
`D:` and passes provenance checks.

For the options lane, require at minimum:

- point-in-time EUR/USD or CME 6E option settlement/quote, implied volatility,
  strike, expiry, put/call, volume, and open interest;
- contract/expiry metadata and a deterministic continuous-underlying mapping;
- observation and availability timestamps that prevent same-day lookahead;
- coverage sufficient to freeze train and untouched OOS across 2020-01-01
  through 2026-06-30;
- license/source manifest and file hashes.

For the order-flow lane, require at minimum:

- CME 6E or primary EBS best bid/ask plus trades, preferably MBO/depth;
- exchange timestamps, price, size, quote condition, and aggressor side or a
  frozen causal inference rule;
- roll/calendar metadata and auditable missing-session handling;
- the same 2020-01-01 through 2026-06-30 coverage and provenance controls.

The target-broker execution cost gate remains independent: at least 90 elapsed
quote days, 30 commission lifecycles per symbol, and 100 side-aware fills per
symbol under the current QFSI contract. External signal data cannot mint or
replace broker cost evidence.

## Storage contract

- Persist acquired raw data, frozen features, ONNX files, and AlphaFactory
  evidence on `D:` only.
- Training may use memory or `D:` scratch; no retained training corpus is
  permitted on `C:`.
- After any future Strategy Tester run, copy and hash the complete run evidence
  to `02. AlphaFactory/runs/` first, stop the runner-owned terminal, then delete
  only the reproducible tester cache/train/log files created by that run.
- Account, profile, broker configuration, shared chart history, and unrelated
  terminal data remain protected.

Until this contract is met, the honest output is a terminal research record,
not an EA binary with unsupported performance claims.

## Blocked audit 3

Rechecked on 2026-07-16 after two earlier goal turns reached the same stop:

- the active registry still records
  `HYP-DRAT-ONNX-ICT-M15-EUR-001` as `KILL_AT_OFFLINE_PROBE`;
- `alpha.ps1 status` and `alpha.ps1 list` still reject the DRAT package because
  `EA_DRAT_ONNX_ICT_Hybrid.mq5` does not exist;
- the package contains only the preregistration, probe/trade evidence, readout,
  audit, and README;
- no `.onnx` file exists anywhere in the workspace;
- no workspace filename matches an options risk-reversal/implied-volatility/
  open-interest surface or primary-market MBO/L2/order-flow dataset;
- the latest QFSI execution capture remains dated 2026-07-15 and live truth
  remains 2/90 quote days with commission/slippage gaps;
- MT5 was stopped and no DRAT Strategy Tester run or disposable `C:` artifact
  was created during this audit.

The same blocking condition has therefore repeated for three consecutive goal
turns. Progress now requires an external-state change: an Owner-supplied or
Owner-approved point-in-time dataset satisfying the minimum reopen contract.

## Owner resume decision

Later on 2026-07-16 the Owner selected external-data option 1 and directed that
all files remain inside this `D:` workspace. Acquisition is reopened under
`20260716_CME_EURUSD_OPTIONS_ACQUISITION_CONTRACT.md` for CME EUR/USD CVOL plus
the full daily option chain. The strategy hypothesis remains closed until the
licensed files are delivered and the fail-closed inventory reports
`CONTRACT_READY`.
