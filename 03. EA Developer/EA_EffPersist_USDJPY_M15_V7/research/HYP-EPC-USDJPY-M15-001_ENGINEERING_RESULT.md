# Engineering result - HYP-EPC-USDJPY-M15-001

Verdict: `INVALID_JOURNAL_TRUNCATED_NO_ECONOMIC_READOUT`.

Run `20260812_015341` created an MT5 report, but AlphaFactory rejected the tester journal because its captured delta reached the exact 8 MiB truncation boundary and ended during 2021-05. No performance metrics from that report were used. The immutable run snapshot preserves the source and artifacts.

The same frozen economic logic was reissued under fresh runtime identity `EA_EffPersist_USDJPY_M15_V7R1 / HYP-EPC-USDJPY-M15-002`, with only verbose CTrade/state logging removed. Economic verdict belongs exclusively to the new valid run.
