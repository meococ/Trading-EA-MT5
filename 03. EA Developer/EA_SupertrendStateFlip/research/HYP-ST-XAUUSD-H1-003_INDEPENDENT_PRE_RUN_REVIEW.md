# HYP-ST-XAUUSD-H1-003 — Independent pre-run review

Status: `PASS_HYP003_ORACLE_AUTHORITY`  
Review scope: static only; no source/oracle/MT5 execution  
Reviewed at: 2026-08-08 UTC

## Bound snapshot

- Preregistration SHA-256: `D82037A5730F0766EE872C3A3D1DB5AAB9DA3BD69BADC08B1323446B1FDF924D`
- Direct MQL5 source SHA-256: `C4C2A0A700434A2C104551D9AD33ECB8893ACB887E25C6E2E045F4A94638A32E`
- Oracle builder SHA-256: `C8358007C1C359CF4FE42650E9EA8683A29A5770FAF7AF3A4AB90D589DC472E4`
- Comparator SHA-256: `4A99D8AD9E2BFBFAF7CA8C6B5A2C2BCF05C0DFE04E53075A0615E463308CBC50`
- Test SHA-256: `22F0F1F25F0886402B2EF098017EFCC1D6C01111C5142E90E5752BDD4B27C590`
- Non-repaint manifest SHA-256: `C176124B1BF10722FDC1369937DBF2314105ACE9E9BA4B1E35231E3CE3904232`
- Non-repaint audit SHA-256: `47809ABA3AB22046053AB4CFD9B1DAEFFCEE3126D272C85E7D9705ECF2E3DCFB`

## Verdict

No fatal blocker remains for the exact HYP003 authority. The oracle uses the primary native `source_epoch` for exact-next classification, claims its single attempt before source access, materializes only `<2023`, replays byte-identically and seals report/receipt/terminal artifacts. The MQL implementation refuses a pre-existing frozen `FILE_COMMON` target, requires telemetry disabled, and preserves the reviewed direct Supertrend recursion.

The current comparator/test snapshot strengthens, without broadening, the HYP003 contract: it verifies oracle receipt/report/terminal identity and attempt, frozen counts and zero-outcome allowlist, and the non-repaint manifest/audit chain.

## Authorized boundary

Authorize exactly one `ST003-ORACLE-001` build, followed by static audit and one AlphaFactory compile. HYP003 does not authorize Strategy Tester, parity comparison, trades, economics, optimization, validation, holdout, paper or live execution.

Before any MT5 parity run, a fresh HYP004 preregistration and registry authority must bind the terminal HYP003 row, exact oracle/report/receipt/terminal, reviewed MQL/comparator/tests/non-repaint artifacts, zero-error/zero-warning compile log and EX5, an exact AlphaFactory execution receipt, a canonical run-local journal/export chain, and one unconsumed MT5 attempt.
