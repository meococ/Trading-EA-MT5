# 2026-09-12 — HYP-CRSIR2-GB-M5-001 control screen: KILL + data-quality finding

## Verdict

`HYP-CRSIR2-GB-M5-001` (EA_CrsiR2, GBPUSD M5, Connors RSI 50-cross + H4 EMA50)
→ **killed** at Model 0, registry row updated (screened→killed, validator green).

Run `20260912_002912` (governed, portable isolate, MetaQuotes-Demo):

| Metric | Value |
|---|---|
| Window | all-available; journal sync 1993.05.12 → 2026.09.10 (~33y) |
| Trades | 29,943 (~17.4/week — cadence band satisfied) |
| Profit Factor | **0.75** |
| Net | **-9,155.12 USD** (10k → 841) |
| Gross / Loss | 27,791.66 / -36,946.78 → frozen kill rule `gross ≤ loss` fired |
| Max DD | 91.59% |
| Sharpe | -5.00 |
| History Quality | **82%** (gate requires >97) |

Kill direction is economics-safe: 18% degraded tick modeling cannot plausibly
hide PF≥1.30 inside an observed 0.75 over 30k trades. No post-hoc rescue.

## Pipeline repairs landed this iteration

1. `research_loop_engine.ps1` — isolate-aware process guard (Owner GUI no
   longer falsely blocks governed runs).
2. `alpha.ps1` + engine — `max_journal_delta_bytes` 1MB → 256MB. A 33y
   M5 all-available run legitimately emits ~67MB of tester-agent journal
   (≈10 lines/trade × 60k fills). Gate semantics unchanged: still
   fail-closed on truncation, hash-bound, bounds-required.
3. `EA_CrsiR2.mq5` — wired lifecycle-v3 telemetry AND the canonical
   `EmitD0SeriesProof()` block (fails INIT on unsynchronized series). Any EA
   entering the governed path needs BOTH; the fleet template lacks the D0
   proof block — required for every future cell.
4. Packet `requested_to`/`availability_asof` must bind the **last closed
   server day** (UTC yesterday), not today — synced history ends at the last
   completed daily bar.

## Structural finding: MetaQuotes-Demo history depth per symbol

`bases/MetaQuotes-Demo/history/<SYM>/YYYY.hcc` sizes reveal real M1 coverage:

| Symbol | Full-M1 years | Stub years (~60–80KB = daily-level) |
|---|---|---|
| GBPUSD | 1999–2026 | **1993–1998** → quality 82% on all-available |
| EURUSD | local cache 2022+ only (server depth unprobed) | — |
| USDJPY | local cache 2022+ only | — |
| USDCAD | local cache 2022+ only | — |
| XAUUSD | 2016–2026 full | none observed |

Implication: GBPUSD all-available M5 on this broker can likely never clear
the >97 quality gate (6 stub years / 33y ≈ 18% loss ≈ observed 82%). Before
running a governed screen on any symbol, check `.hcc` year files for stubs.
Symbols whose server history begins at full M1 (XAUUSD 2016+) are the best
quality-gate candidates. EURUSD server depth unknown until first sync.

## Cost evidence

Spread/slippage measured on isolate (400 samples): p90 spread 0.1 pip,
p90 RT slippage proxy 0.1 pip/side @250ms. Cost manifest =
`RESEARCH_PROXY` tier, non-promotable. MetaQuotes-Demo ≠ FivePercentOnline —
results are research screens only, never broker-verified economics.

## Next

Pick cells on symbols with stub-free server history (XAUUSD first — GOAL
wants XAU+FX anyway; EURUSD needs first-sync depth check). GBPUSD cells are
data-blocked at the quality gate until/unless broker data improves.
