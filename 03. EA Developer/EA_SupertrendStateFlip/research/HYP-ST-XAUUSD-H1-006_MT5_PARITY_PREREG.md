# HYP-ST-XAUUSD-H1-006 — frozen AlphaFactory MT5 full-bar parity audit

Status: `FROZEN_PRE_MT5_DATA_ACQUISITION_ONLY`  
Parent: `HYP-ST-XAUUSD-H1-005` (`KILL_ENGINEERING_INVOCATION_ADAPTER_SPREAD_TOKEN_NO_MT5`)  
Parity target: `HYP-ST-XAUUSD-H1-003`

## Thesis and bounded revision

HYP006 is a fresh execution/provenance child created because the sole ST005
launcher attempt was consumed by AlphaFactory argument validation before MT5
started. The only behavior change is the AlphaFactory adapter token:

- ST005 passed `-Spread current` and failed before any run directory existed;
- ST006 passes `-Spread ''`, the documented AlphaFactory current-spread request;
- the task packet, execution receipt and expected run manifest continue to bind
  semantic spread `current`.

No formula, MQL5 source, EX5, symbol, timeframe, window, Model, data-quality
gate, event count, oracle, output schema, or comparator tolerance changes.
HYP005 is terminal and must never be retried.

## Frozen identities and implementation

- Outer authority: `HYP-ST-XAUUSD-H1-006`.
- Outer attempts: `ST006-MT5-001`, `ST006-ARTIFACT-COLLECT-001`,
  `ST006-COMPARATOR-001`, each limit one.
- Inner parity identity: `HYP-ST-XAUUSD-H1-003`, run
  `ST003-MT5-PARITY-001`, common CSV `ST003_MQL5_PARITY_001.csv`.
- Direct MQL5 source SHA-256:
  `C8C222487769439DC8FB9272C049BE30928FED5315A64DD1CAD440B500A13D02`.
- Inherited HYP004 EX5 SHA-256:
  `0C68520D3C3B073939B8A4FF403575687E93739E1A9844B6B051E85011F84982`.
- Inherited HYP004 compile log SHA-256:
  `3CF9A7A8B8C8CC39709EDFAAF9FEB2F4A8B7AAB1273D5CB7B4547A9D8675AEF6`
  (`0 errors, 0 warnings`).
- HYP003 oracle SHA-256:
  `63E93022794C6DD50EBFB4464DD521D4B1757C5797B158121467F18FF2F13096`.

The formula remains exact Supertrend 10/3: full native H1 chronology from
2004-06-11 04:00Z, TR0, SMA10 seed, Wilder RMA, initial DOWN state, strict
band/state comparisons, upper-first coincident-band identity, flat-bar
acceptance, no rounding, chronological gaps, completed bars only. There are no
trade APIs or native Supertrend/ATR parity assumptions.

## Exact AlphaFactory contract

- EA / symbol / timeframe: `EA_SupertrendStateFlip` / `XAUUSD` / `H1`.
- Window: `2018.01.01` through `2023.01.01`.
- Model / execution / delay / timeout: `4 / 0 / 0 / 1800`.
- Role / telemetry: `control / none / off`.
- Deposit / leverage / semantic spread: `10000 / 100 / current`.
- Launcher representation of semantic current spread: empty `-Spread` value.
- Overrides: `InpAuditOnly=true;InpAuditRunId=ST003-MT5-PARITY-001;InpEnableTelemetry=false;InpParityFileName=ST003_MQL5_PARITY_001.csv`.
- Authority: `DATA_ACQUISITION_ONLY_NO_PERFORMANCE`.
- Data acceptance: fixed window, History Quality `>97`, XAUUSD mandatory,
  no-skip, tester-journal bounds and exact M5/M1 D0 series proof required.

## One-shot workflow and acceptance

Before authority, seal a fresh HYP006 packet, receipt, registry snapshot,
collection-aware non-repaint audit, tests and independent review. The exact
HYP006/ST006 attempt path and common CSV must be absent. Each outer stage is
durably claimed before execution. Any crash or failure consumes its ID.

Correctness PASS requires compile `0E/0W`, no fatal journal line, exactly one
summary with `rows=29460`, `raw=690`, `executable=683`, `gaps=7`, `long=339`,
`short=344`, full-bar oracle parity and zero orders/deals.

This hypothesis authorizes no post-event prices, PnL, PF, performance metric,
economic claim, optimization, validation, holdout, paper or live trading. Only
a fresh child after parity PASS may preregister entry/exit/risk/cost economics.

