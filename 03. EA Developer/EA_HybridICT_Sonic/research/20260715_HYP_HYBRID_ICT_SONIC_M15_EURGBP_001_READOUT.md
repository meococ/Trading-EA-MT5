# Hybrid ICT-Sonic Model 0 EURUSD M15 — Session readout

Date: 2026-07-15  
Hypothesis: `HYP-HYBRID-ICT-SONIC-M15-EURGBP-001`  
Role: control (Owner Path-C)  
Cost: **UNVERIFIED** (tester current spread; commission/slip not broker-proven)

## Official window

| Field | Value |
|---|---|
| Symbol / TF | EURUSD M15 |
| From → To | 2020.01.01 → 2026.07.15 |
| Model | 0 (every tick) |
| Deposit / leverage | 100000 / 100 |
| History quality | **100%** |
| Bars / ticks | **162845** / **102936747** |

## Primary result (first clean control)

Run: `02. AlphaFactory/runs/EA_HybridICT_Sonic/20260715_164851`

| Metric | Value |
|---|---|
| Total trades | **0** |
| Total deals | **0** (balance only) |
| Net profit | 0.00 |
| Profit factor | 0.00 / n/a |
| Max DD | 0.00% |

Tester agent: init OK; test passed in ~12–13s wall (no fills).

## Follow-up remints (same hyp, engineering fixes)

BOS rewrite, Dragon mid-reclaim OR outer break, forced TesterInputs overrides  
(spread 4.0, MACD off, vol climax 1.5, wave+PVSRA on).  
**Still 0 trades** (runs through `20260715_165146`+).

## Verdict vs council plan gates

| Gate | Result |
|---|---|
| PF ≥ 1.65 after slip | **FAIL** (no trades; cannot claim) |
| Max DD ≤ 10% | n/a (flat) |
| Expectancy positive | **FAIL** |
| Cadence / sample | **FAIL** (N=0) |

**Decision: `KILL_AT_MODEL0_EMPTY` / no edge evidence under mechanical Hybrid stack.**  
Not promotion. Not live. Prior red-team revive warning remains relevant.

## Likely cause (engineering, not excuse)

Confluence AND-stack (H4 bias + ICT level touch + wave + Dragon trigger + PVSRA
tick climax + session/spread/ATR) produced **zero** closed-bar setups over 6.5y.
Pending path never logged a place/fail print → signal gate never cleared.

## Next (needs Owner)

1. Keep package as research scaffold only, or  
2. Authorize **DIAG ablation** hyp (filters off stepwise) to isolate which gate zeros cadence — new hyp id, not rescue of this readout.
