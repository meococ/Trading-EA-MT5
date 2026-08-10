# HYP-ST-XAUUSD-H1-004 — Independent initial compile-authority review

Verdict: `PASS_INITIAL_COMPILE_ONLY`  
Reviewer: independent campaign audit sub-agent  
Scope: static read-only review; source data, compiler and MT5 were not executed by the reviewer

The read-only D0 series witness is a legally bounded engineering revision of HYP003. It does not change the H1 Supertrend formula, recursion, state transitions, parity CSV or order behavior. The one-shot compile runner durably claims before calling the hash-bound AlphaFactory runner and terminally consumes success/failure.

Current reviewed SHA-256 identities:

- prereg: `D900315D656319690DEDDAF9B1242C42C2F8B65A94EE0977586E411FF09623CB`
- MQL source: `C8C222487769439DC8FB9272C049BE30928FED5315A64DD1CAD440B500A13D02`
- static compile runner: `7274527DEF9A1F082558959FEEF2BC6B5DDB06B182340EA0FDF8C815CE84152F`
- claim-before-MT5 launcher: `0B3DDBF7E03C2CF5B76CF6290620E9CFA0963564F8429EE2C7527A7E918D0090`
- comparator: `1D1D52C739B563981B252A7E659D9251BC4A90036BA7B4F290FD29AB73FA9772`
- post-run collector: `C84724BA660AA17836FC5267BD3BE531516E7C21BD6A05ADE1D52BE780534B8F`
- HYP003 parity tests: `22F0F1F25F0886402B2EF098017EFCC1D6C01111C5142E90E5752BDD4B27C590`
- HYP004 harness tests: `AB4C0BF0464C704AFB91F0EEEC5D42C1CCDF13BA5DA7C774097F37D964B2C606`
- AlphaFactory runner / quant parser / non-repaint tool: `758D0185A862E023309F7D1A9DFF5970072D71F310975AFCE526CD6E5965F93F` / `A7F93E8DC35A2FC7A273419500E7B41DF742F828613C48EDA3D5C766C042616B` / `366D70F0C6FAF02F85B4819E7305CD1BD271BA6A78B4789CF0DCDF2FB651E360`

The package's reported test result is 48 passing tests. The reviewer did not rerun them under the static-only instruction.

Authority granted by this review is exactly one `ST004-COMPILE-001` static compile/archive. MT5, artifact collection, comparator, outcome/economic analysis, validation, holdout, optimization, paper and live operation remain unauthorized until a separately reviewed second `state=probe` authority row.
