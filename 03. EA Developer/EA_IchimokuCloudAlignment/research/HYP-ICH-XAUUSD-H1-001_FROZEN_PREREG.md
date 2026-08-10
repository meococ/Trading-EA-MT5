# HYP-ICH-XAUUSD-H1-001 — Frozen Native-H1 Ichimoku Full-alignment Source Preregistration

Status: `FROZEN_PRE_OUTCOME_SOURCE_ONLY`  
Informing result: terminal M5 source over-frequency object `HYP-ICH-XAUUSD-M5-001` only.

## Identity and horizon thesis

- Hypothesis: `HYP-ICH-XAUUSD-H1-001`
- Family: `native-h1-ichimoku-9-26-52-full-alignment`
- Symbol/timeframe: FivePercent XAUUSD native H1 Bid bars
- Design: `[2018-01-01T00:00:00Z, 2023-01-01T00:00:00Z)`
- Validation 2023–2024 and holdout 2025+ remain sealed
- Sole attempt: `ICHH1001-SOURCE-ATTEMPT-001`

M5 full alignment was frozen before source access and terminally parked only because it emitted about 20 events/week. Native H1 is not a filtered or downsampled set of those M5 events: H1 OHLC aggregation nonlinearly changes every high/low midpoint and cross. The unchanged 9/26/52 definition now represents approximately 9h/26h/52h trend structure rather than 45m/130m/260m microstructure. No M15/M30/H4 tournament is authorized.

## Bound indicator dependency and exact rules

- Formula dependency: `research/analyze_ichimoku_source.py`
- Dependency SHA256: `F9BAF1626EF05A623C49B16B817D405AE1C9689845E5E5E8F8E5E23F937C8114`
- Tenkan 9, Kijun 26, Span B 52 and displacement 26 are unchanged.
- Displayed Span A/B at completed H1 bar `t` are raw spans from `t-26`.
- raw LONG: prior Tenkan `<=` prior Kijun, current Tenkan `>` current Kijun, current close strictly above both displayed spans, Span A strictly above Span B.
- raw SHORT: exact inverse.
- Complete dependency is `t-77..t`; first usable row is index 77. All 78 H1 source rows must be finite and geometrically valid. Bar-count windows span normal market closures.
- Executable event requires the immediately following native H1 timestamp to equal `t+1 hour`. A raw gap event is consumed, with no next-row price read. Decision timestamp is `t+1 hour`.

Forbidden: period/displacement changes, M5-event reuse, alternative timeframe scan, Chikou, other indicators, filters, sessions, cooldown/debounce, optimization and outcome fields.

## Frozen source

- Manifest SHA256: `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`
- native XAUUSD H1 Parquet: `XAUUSD_H1_ALL_AVAILABLE_20260801.parquet`
- H1 data SHA256: `B85006E201DA7B359E9F25290C81C72A6092CFA08AEDFFE05E693E17A005ACC3`
- Only symbol/timeframe/source epoch/time/UTC ambiguity/high/low/close may be read.
- PyArrow must materialize only `2018 <= time_utc < 2023`, followed by a fail-closed post-read assertion.
- M5 evidence cannot be used as H1 source rows or H1 economic evidence.

## Source gates

All must pass:

1. all hash/registry/dependency/one-shot bindings and byte-identical replay;
2. at least 25,000 design H1 rows, a pre-access calendar-derived completeness floor;
3. feature coverage at least 99.0% after exactly 77 warmup rows;
4. exact-next H1 timestamp coverage at least 97.0% of raw events;
5. at least 500 executable events;
6. pooled cadence 2.0–5.0/week;
7. LONG and SHORT share each at least 30%;
8. no year above 30%;
9. every design year cadence 1.25–6.50/week;
10. zero direction conflicts;
11. exact source-only ledger allowlist.

Any failure gives `PARK_SOURCE_FEASIBILITY_EXACT_NATIVE_H1_ICHIMOKU_FULL_ALIGNMENT`. All pass gives `SCREENED_SOURCE_PASS_NATIVE_H1_MQL5_IICHIMOKU_BUILD_AUTHORIZED`, allowing only native H1 `iIchimoku(9,26,52)` parity/correctness and collector work. Economics remains unauthorized.

## Authority boundary

No H1 scan is authorized until analyzer/tests/hashes receive independent static review and a matching registry row. No MQL5, MT5 tester, outcome, validation, holdout, paper, promotion or live authority is granted here.
