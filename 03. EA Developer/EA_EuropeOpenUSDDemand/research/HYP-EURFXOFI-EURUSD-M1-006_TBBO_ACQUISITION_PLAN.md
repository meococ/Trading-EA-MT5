# TBBO PAID ACQUISITION PLAN - HYP-EURFXOFI-EURUSD-M1-006

Frozen on `2026-07-30` before the first paid HYP006 call.

## Authority and exact source

The Owner's single hard ceiling is `USD 2.25`, originally named against HYP001
in the same message that expanded the horizon to 2016-current. HYP002-HYP005
are immutable contract successors, not separate budgets, and spent USD0. The
exact HYP005 TBBO receipt is SHA256
`CAF5732E1C80EC1E4F0E32DA612C633ED5031D72DEB64342459B36FFDA35C5A7`:
1,359 windows, estimated USD2.117540538299, 81,203,280 billable bytes, 1,356
positive-size and three zero-size windows.

- Dataset/schema/symbol: `GLBX.MDP3` / `tbbo` / continuous `6E.v.0`.
- Windows: exact `[14:14:45,14:15:00) Europe/Berlin` for the hash-bound HYP002
  630/526/203 TRAIN/VALIDATION/HOLDOUT dates through 2026-07-29.
- Information use: source only. TBBO supports future signed aggressive
  trade-flow imbalance with contemporaneous top-of-book context; it is not
  MBP depth or EBS cash-spot dealer flow.

## Fail-closed paid protocol

1. Re-quote every one of the 1,359 exact windows with free metadata calls.
2. Stop before the first paid call if coverage changes, any positive planned
   window becomes invalid, or live total exceeds USD2.25.
3. Download positive-size windows serially with
   `timeseries.get_range(..., stype_out=instrument_id)` to exclusive D-side
   `.partial` files.
4. Before each call, persist an `in_flight` journal. After return, fully decode
   DBN, count records, hash the file, atomically rename and checkpoint.
5. A charged call error or in-flight request with no recoverable complete file
   must stop. It may not be automatically retried.
6. Three live zero-size windows are recorded as source-empty without a paid
   call. Any live classification change is journaled.

The acquisition may resume only by independently revalidating every completed
file and the frozen plan/quote/tool bindings. No destructive cleanup.

Forbidden: window/date/schema fallback, batch download, parallel paid calls,
API-key persistence, target price/return join, OFI result, economics, MQL5,
Model 0, optimization, promotion, paper or live trading. Download completion
only opens an outcome-blind source-quality/decode successor.
