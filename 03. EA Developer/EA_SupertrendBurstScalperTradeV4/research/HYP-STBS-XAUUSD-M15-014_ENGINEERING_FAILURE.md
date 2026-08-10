# HYP-STBS-XAUUSD-M15-014 engineering failure

Verdict: `KILL_HARNESS_LITERAL_CURRENT_SPREAD_PRECOMPILE_NO_MT5_NO_ECONOMIC_VERDICT`

The sole authorized attempt `STBS014-MODEL0-AUDIT-001` was claimed and is irrevocably consumed. AlphaFactory returned 1 before compile, MT5 launch or run-directory creation because the launcher passed literal `-Spread current`. AlphaFactory accepts current spread only as an omitted/empty request; otherwise `Spread` must be a non-negative numeric value.

Evidence:

- authority row SHA256: `9BCE293542CEBE1183883B94376EFBE3F8AEB5B78174E8FB903C146DC4C0C108`
- attempt start SHA256: `6F53CCD5EC13B6F9BA6DC11C90966BF2862B44235870D61BF5428033BF7ADF13`
- failed terminal SHA256: `7FBE2C2891EE09DF33467EE5397407010AEA7F2BF9B690DD9331601C2E1BC670`
- stdout SHA256: `FD8BCF14AB4701ABAC12BDBC16CA1781CFE4F2B5C82299CF54826D6E3195A319`
- stderr SHA256: `363D65C73F642C7E9154F5EEF128BF1B0526D11EF786A1B456F78F8D61A4F551`
- task packet SHA256: `BB22A617EFACA3A4C6FB8225B5750768090D9741ADAF1D96DD20010A009A9FA9`
- contract receipt SHA256: `E2E65FF3A3569F56063503682C17991758319920836EB65AE5A584FC997D06FE`
- exact run-set delta: before 0, after 0, created none, deleted none
- post-Alpha canonical EX5/log hashes equal the pre-run static hashes, confirming Alpha did not compile this attempt

Failure radius is only the HYP014 outer invocation encoding of current spread. It does not reject the Supertrend signal, margin-candidate logic, lifecycle code, data quality, MT5 runtime, trade economics or market edge because none of those stages opened.

Same-ID retry is forbidden. The exact registry object is killed because its sole attempt is consumed; this says nothing about the mechanism or the active project goal. A fresh child may change only the outer identity/attempt and omit the `-Spread` CLI argument while preserving the current-spread receipt/manifest contract and the frozen zero-trade audit mapping.
