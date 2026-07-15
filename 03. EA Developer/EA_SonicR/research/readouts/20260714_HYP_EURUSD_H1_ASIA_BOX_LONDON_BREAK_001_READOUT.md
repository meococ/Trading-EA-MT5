# Readout — HYP-EURUSD-H1-ASIA-BOX-LONDON-BREAK-001

Date: 2026-07-14  
State: `KILLED_AT_MODEL_0`  
Authority: Owner Wave5 iterate; EURUSD Asia-box preferred over NY-IB  
(new-symbol independence vs parked London-IB family)  
GPT: waived

## Slot choice

| Option | Readiness | Choice |
|---|---|---|
| `HYP-EURUSD-H1-ASIA-BOX-LONDON-BREAK-001` | EA+prereg+receipt ready | **Selected** — new symbol, clearer independence |
| `HYP-M15-NY-IB-DRIVE-BREAK-001` | EA+prereg+receipt ready | Deferred — nearer parked London-IB `223618` |

Probe waived per Wave5 de-dup (no cheap offline series). Lane waited for
sibling ATR%ile re-run lock then exclusive Model0.

## Run

| Item | Value |
|---|---|
| `run_id` | **`20260714_225610`** |
| EA | `EA_EURUSD_H1AsiaBoxLondonBreak` magic 880996 |
| Binding | EURUSD H1 2021–2025 deposit 100000 overrides empty Model 0 |
| Receipt SHA | `E234B6FFB13FE5B290A407543C9604AF3E71AEA2154BF28A8455B2287CE79308` |
| Report SHA | `FCF42B4287019AB203F3C1229C66CA282A326912FCF90BDFCA66A7912C3C7958` |
| Closeout | empty required_sidecars throw after report; metrics via analyze |

## Metrics vs GOAL / Wave5 gates

| Metric | Value |
|---|---:|
| Trades | 500 |
| PF | **0.897** |
| Net | **−$6504** |
| tpw (elapsed 260.714) | **~1.92** |
| Expectancy | −$13.01 |
| Max DD | 9.37% |

| Gate | Result |
|---|---|
| KILL (PF&lt;1.00) | **HIT → KILL** |
| Research HIT | FAIL |
| GOAL | unmet |
| Cost stress +$12 | Skipped (PF&lt;1.20 kill-fast) |

## Banned (honored)

Do **not** densify Asia/London hours, ATR%ile, RR, Tue/Wed cut, or NY-session
filter from this readout. Not LondonORB / IB-overlap rescue.

## Next Wave5 remaining

1. `HYP-M15-NY-IB-DRIVE-BREAK-001` — only Wave5 slot left (EA ready).  
2. Best shelf unchanged: RR2 `194548`.  
3. No portfolio / SB / ATR%ile / Donchian reopen.
