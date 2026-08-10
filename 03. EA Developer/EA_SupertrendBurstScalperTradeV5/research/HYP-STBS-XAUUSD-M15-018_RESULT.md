# HYP-STBS-XAUUSD-M15-018 — comparator result

Verdict: `PASS_ENGINEERING_ZERO_TRADE_MODEL0_AUDIT`

This is an engineering-only PASS. It does not measure or authorize PF,
expectancy, drawdown, optimization, OOS, promotion, paper or live trading.

## Immutable chain

- authority row SHA256: `207681CA4ABAE43AAA8569EFA9625621900621F466CF21DAEAAB384D94ECE3ED`;
- attempt start SHA256: `A5C0295370C237FB19F4B4B19B9458E84FDAA1F69BCB9AD07E53139A92A70257`;
- comparison report SHA256: `5AAC843B0C88049952DBC3BF86614928132B3C069DE5258BA5183177251304F3`;
- comparison receipt SHA256: `3465D6C27CFE6A72FA2F00A23E5788135830B7EEE52EF8A2DC8B62B5D85BED0B`;
- attempt terminal SHA256: `294516C757A221AADEF642D549FCF7281517BDA4E11F6B44165CDB20915243C7`.

Receipt evidence rehash: 21/21 matched, zero mismatch. Deterministic replay
matched byte-for-byte.

## Accepted engineering facts

- data fingerprint: `B326D511C805C7998DF1C2FC540770B6EC3054D0D4BCBB41A5A4E3C2E4239D25`;
- raw/executable/gap signals: 690/683/7;
- LONG/SHORT: 339/344;
- ATR-ready/geometry-ready/margin-ready: 683/683/683;
- journal records: 1,380 = 690 unique × 2 identical provenance copies;
- deinitialization reason: 1;
- runtime failure: false;
- orders/trades/returns/economic evaluations: 0/0/0/0.

The imported frozen quant parser produced one Python bytecode cache file at
`captured/__pycache__/quant_analyzer.cpython-312.pyc`, SHA256
`6FB6BB9A0EB1CCBD54E264DBF2A4E25131C070B9E2E0FD837AA00EAB6CE523B3`.
It is a non-authoritative derived cache, is outside the 21 receipt inputs and
does not participate in the result.

## Next decision

Engineering audit is closed. The next hypothesis must be trade-enabled and
economic, with a fresh source identity because V5 intentionally hard-requires
audit-only mode. It must preserve the verified signal/risk mechanics and pass
compile/runtime/lifecycle/deal reconciliation before cost/PF is admissible.
