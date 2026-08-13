# HYP-IVRL-XAUUSD-M5-001 — engineering failure

Verdict: `KILL_ENGINEERING_JOURNAL_DELTA_TRUNCATED_NO_ECONOMIC_VERDICT`

The sole Model-0 attempt `20260811_142221` completed MT5 execution and produced
a report, but AlphaFactory correctly rejected the run before economic
acceptance because the frozen 4 MiB raw journal-delta cap was exhausted.

- Manifest journal contract: `bytes_read=4,194,304`, `files_read=3`,
  `truncated=true`.
- Exported journal: `2,097,154` bytes and ends mid-line.
- A terminal summary is observable and mechanically reports
  `runtime_failed=false`, `raw=1196`, `L607/S589`, `entries=670`,
  `rejects=5`, `risk_lock_skips=521`; it does not cure truncation.
- Manifest SHA: `7BE003ED1D42BD38436F4D046B75503E11AC754F510CD04805946F94285E2389`.
- Report SHA: `FA7A72E786C47D33A8906D1C526502E3D5BCB2586A6A4AC35D932E22268EB4A4`.
- Truncated journal SHA: `15B9FE3F89252BBF9B15D96552739B48088CDD0428BC83D815C9E469B9A5DD06`.

PF, expectancy, returns and cost stress are inadmissible for this attempt.
Same-ID retry is forbidden. A fresh identity may change only the evidence cap;
the strategy and execution mapping remain frozen.
