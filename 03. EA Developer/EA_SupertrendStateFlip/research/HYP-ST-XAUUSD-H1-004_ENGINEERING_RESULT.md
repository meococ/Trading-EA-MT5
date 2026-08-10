# HYP-ST-XAUUSD-H1-004 — Engineering result

Verdict: `PARK_ENGINEERING_VALID_STATIC_COMPILE_ONLY_HANDOFF_TO_HYP005_NO_MT5`

HYP004 completed exactly one static compile and no MT5 attempt. The direct MQL5
Supertrend 10/3 source compiled with `0 errors, 0 warnings`; the canonical and
archived source, EX5 and compile log are byte-identical.

Authoritative SHA-256:

- attempt start: `E366CF138994CF1C289EFDC0D55BC6277F637108C9E23CFEBCE415D5BA767578`
- compile receipt: `E45D5459FAF76923D99800A7F1BED4FFDABEAE00ECD6A47C8E26753D82DC4B7A`
- terminal: `A0F7AA7717CCC0EC57E55D6893FEF5331112FDC36314252B8AAD4F8FEAADEEFD`
- source: `C8C222487769439DC8FB9272C049BE30928FED5315A64DD1CAD440B500A13D02`
- EX5: `0C68520D3C3B073939B8A4FF403575687E93739E1A9844B6B051E85011F84982`
- compile log: `3CF9A7A8B8C8CC39709EDFAAF9FEB2F4A8B7AAB1273D5CB7B4547A9D8675AEF6`

The HYP004 V1/V2 packets were prelaunch artifacts only. Neither was supplied to
AlphaFactory. Registry validation exposed that HYP004's initial `probe` row had
frozen `model=null`, so it could not legally become a Model-4 execution state.
No validator exception was added, no model was mutated, and no same-ID retry is
authorized. The frozen FILE_COMMON CSV and HYP004 MT5 marker never existed.

HYP004 makes no parity, order, outcome, cost, return, PF, validation, holdout,
promotion, paper or live claim. A fresh HYP005 correctness-only child may reuse
the exact compile artifacts under a new Model-4 data-acquisition preregistration
and new outer attempt IDs.

