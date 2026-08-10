# HYP-ST-XAUUSD-H1-007 — frozen AlphaFactory MT5 full-bar parity audit

Status: `FROZEN_PRE_MT5_DATA_ACQUISITION_ONLY`  
Parent: `HYP-ST-XAUUSD-H1-006` (`KILL_ENGINEERING_INVOCATION_ADAPTER_TELEMETRY_OVERRIDE_NO_MT5`)  
Parity target: `HYP-ST-XAUUSD-H1-003`

## Bounded revision

HYP007 is a fresh outer execution identity. ST006 proved the empty current-spread
token reaches the next AlphaFactory gate, then failed before MT5 because profile
`none` forbids an explicit `InpEnableTelemetry` override. HYP007 removes only
that redundant override. `InpEnableTelemetry` remains frozen false twice: its
MQL5 input default is false and `OnInit` rejects true.

No formula, source byte, EX5, oracle, symbol, H1 window, Model 4 setting, cost
semantics, data-quality gate, output schema, count, comparator tolerance or
zero-trade rule changes. HYP005/ST005 and HYP006/ST006 are terminal and cannot
be retried.

## Frozen execution contract

- Outer ID/attempts: `HYP-ST-XAUUSD-H1-007`; `ST007-MT5-001`,
  `ST007-ARTIFACT-COLLECT-001`, `ST007-COMPARATOR-001`, each once.
- Inner formula/oracle: `HYP-ST-XAUUSD-H1-003`,
  `ST003-MT5-PARITY-001`, `ST003_MQL5_PARITY_001.csv`.
- Source SHA-256: `C8C222487769439DC8FB9272C049BE30928FED5315A64DD1CAD440B500A13D02`.
- EX5 SHA-256: `0C68520D3C3B073939B8A4FF403575687E93739E1A9844B6B051E85011F84982`.
- Oracle SHA-256: `63E93022794C6DD50EBFB4464DD521D4B1757C5797B158121467F18FF2F13096`.
- Exact overrides: `InpAuditOnly=true;InpAuditRunId=ST003-MT5-PARITY-001;InpParityFileName=ST003_MQL5_PARITY_001.csv`.
- XAUUSD H1, `2018.01.01`–`2023.01.01`, Model 4, execution/delay 0,
  timeout 1800, role control, telemetry profile none/tier off, deposit 10000,
  leverage 100, semantic spread current represented by an empty CLI token.
- Authority: `DATA_ACQUISITION_ONLY_NO_PERFORMANCE`; fixed-window HQ `>97`,
  XAUUSD mandatory, no-skip, journal bounds and exact M5/M1 series proof.

The direct Supertrend 10/3 formula and complete H1 prehistory contract remain
unchanged. The EA is audit-only and contains no trade API.

## One-shot acceptance

Seal fresh packet/receipt/snapshot/audit/tests/review before authority; require
the ST007 root and common CSV absent. Every stage claims before execution and
any failure consumes the ID. PASS requires compile 0E/0W, one clean summary
`29460/690/683/7/339/344`, exact full-bar oracle parity and zero orders/deals.

No outcomes, PnL, PF, economics, optimization, validation, holdout, paper or
live authority exists. An economic child may open only after parity PASS.

