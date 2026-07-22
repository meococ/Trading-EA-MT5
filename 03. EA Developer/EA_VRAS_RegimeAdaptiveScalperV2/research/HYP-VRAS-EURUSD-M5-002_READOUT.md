# HYP-VRAS-EURUSD-M5-002 - invalid initialization readout

`INVALID_ENGINEERING_ONINIT_NO_ECONOMIC_VERDICT`.

Run directory `20260722_103321` contains an MT5 report, but tester stopped at
OnInit because the canonical source defaulted to HYP-002/magic 5600742 while
`ValidateInputs()` still required HYP-001/magic 5600741. No lifecycle, RunMeta,
market-bar evaluation or trade exists. This is a static/test coverage failure,
not a market result. HYP-002 is terminal and remains byte-identical.

- Source SHA256: `424C8AB804EB753B152FA8D39EE63B2FC333A4B1DE385478E69B1D4FF697B9C4`
- Report SHA256: `56E688CB112F023B9AC8098C407F13EF9F7F4543AD2E2E9E28419FD1C19D90C0`
- Failure radius: identity guard only. HYP-003 may correct only that guard and
  add an all-occurrence identity regression test; no trading rule may change.
