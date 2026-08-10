# HYP009 Model-0 audit failure

Verdict: `KILL_EXACT_RUNNER_COMPILE_LOG_SUFFIX_FALSE_REJECT_AFTER_MT5_NO_PARITY_NO_ECONOMICS`

## Exact failure

The sole `STBS009-MODEL0-AUDIT-001` attempt is consumed and cannot retry. AlphaFactory compiled the frozen source, launched MT5, produced a report and returned a canonical run directory. The outer runner then stopped before manifest/report/journal parity because its compile-log regex required the complete result line to end immediately after `0 warnings`.

Actual frozen MetaEditor line:

`Result: 0 errors, 0 warnings, 722 ms elapsed, cpu='X64 Regular'`

This is a harness false reject. It does not reject the EA source, signal mapping, MT5 run, parity or economics. The runner decoded the run manifest and exactly parsed the snapshot/live configs before reaching the compile-log check, but it did not complete the manifest field/hash gates and did not semantically open the report, journal or enhanced summary. Those bytes are recorded below only as immutable recovery candidates for a fresh comparator-only child.

## Consumed-attempt evidence

- screened authority raw row: `1C485E174B1600AF227CEC104D85387F125F01993D228BC088C5BD858E1E4301`;
- attempt start: `07B3F4EA4A33577B58A3AFC528F4FD56D4D9DC35512F244FCFA7EF403EAB0F4E`;
- failed terminal: `9EDFC70DDAD82B0B446678AB6A135573DC2D9CA1919BE7F8F0ED14FFDE11A565`;
- Alpha stdout: `F75363F2EC88587E79958371308C778A96AC55B7645F79AB039CECC83F96F29F`;
- empty Alpha stderr: `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`;
- immutable run compile log: `7DCEC7E9B9D8CFDD19CE507CF1D49258F91AA17B200475404A58E9922C9A070E`;
- reviewed runner: `AFFD1823BBEA9833C6C7D4844A829135277E808A2114142BBA28BE4AA0100E42`;
- frozen source: `D950ED04F6940F82354D0D5AF2A2E59C270A71FDFE0A96873C3781849AD959BB`.

The attempt root contains exactly five files: start, failed terminal, stdout, empty stderr and the run compile-log archive. No HYP009 audit receipt was emitted.

## Run artifacts and semantic boundary

Alpha run: `02. AlphaFactory/runs/EA_SupertrendBurstScalperTradeV2/20260809_181119`

- manifest: `8837FB5635865AA5791181D22E7F16418C63A5D39A5F235D59539E38B2F3C5E5`;
- report: `9B4872DEEBB9B4D41284EF010ED68E5DC5FB13F5A19490DE0A50573737C46E8E`;
- tester journal: `D7851DB3E53515E063C79854841D62D5A7E91D1BD8A75B2DD64849689F3CBDA0`;
- enhanced summary: `E546E60F4587CE4572AE7526BAABC737F8A65FAF7542A96359A092E893C8DA47`;
- source snapshot: `D950ED04F6940F82354D0D5AF2A2E59C270A71FDFE0A96873C3781849AD959BB`;
- EX5 snapshot: `3E71B8B74E18F407FFA645118D6ED10FFBC040B7F5044E53C3F28A3C5E7883C9`;
- config snapshot/live config: `CCCDB49CA74BB216EAB05F11A105629E1ADE1BFAC101C54CFF1D64E22BCC3A27`.

Only manifest JSON decoding and the two exact config parses occurred. Manifest acceptance, DQ, report, funding, journal, Oracle, UTC/server and geometry parity were not executed.

No PF, expectancy, drawdown, cadence, return, cost or market-edge claim is authorized.

## Legal next lane

After independent failure review and a terminal HYP009 registry row, a fresh comparator-only child may bind this exact already-produced run and change only compile-log acceptance from whole-line equality to a unique structured prefix with zero errors and zero warnings plus a strictly parsed timing/CPU suffix. It must use a fresh hypothesis/attempt ID, claim before opening the run artifacts, retain every no-trade/parity/economic boundary, and must not launch MT5 again.
