# HYP-UO-EURUSD-H1-001 — Frozen Ultimate Oscillator Re-entry Source Screen

## Scope

- One outcome-blind source/cadence attempt: `UO001-SOURCE-ATTEMPT-001`, no retry.
- Native FivePercent EURUSD H1 Bid bars; full source `<2023`; score source bars `[2018-01-01, 2023-01-01)` UTC.
- Data SHA256 `78BF655C67392A23690C80DB127E24997D0CD14264B573A3832D167C9361FCF3`; manifest SHA256 `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`.

This is a fresh finite-window buying-pressure/true-range thesis, not a revision of COP/ERAY/KVO. TradingView documents the canonical 7/14/28 Ultimate Oscillator formula: https://www.tradingview.com/support/solutions/43000502328-ultimate-oscillator-uo/ . Formula provenance is not parity or acceptance. Symmetric 30/70 extreme re-entry is the frozen research event; no divergence logic is used.

## Formula and event

For ordered source rows and `t>=1`:

- `BP_t=Close_t-min(Low_t,Close_(t-1))`.
- `TR_t=max(High_t,Close_(t-1))-min(Low_t,Close_(t-1))`.
- `Avg_p(t)=sum(BP_(t-p+1..t))/sum(TR_(t-p+1..t))`, `p in {7,14,28}`.
- `UO_t=100*(4*Avg_7+2*Avg_14+Avg_28)/7`.
- First BP/TR index 1; first UO index 28; first event index 29; event dependency `t-29..t`.

LONG: prior `UO<=30`, current `UO>30`. SHORT: prior `UO>=70`, current `UO<70`. Current equality emits nothing; prior equality may cross. Conflicts fail closed. No trend/session/direction filter, FSM, debounce, cooldown, divergence or alternative threshold.

Full-history OHLC must be finite, strictly positive and geometrically valid. A required nonfinite/nonpositive TR sum makes only that feature row invalid and non-emitting and counts against coverage; no imputation or global source abortion. Physical gaps create no synthetic bars.

A raw event is executable only if the immediate next physical row is UTC `+1h`, source epoch `+3600`, and the decision is before 2023. Gap events are consumed, not queued. Never read next-row OHLC. Annual gates use decision UTC year.

## Gates

All must pass: design rows >=25,000; feature coverage >=99%; exact-next coverage >=97%; executable events >=500; pooled cadence 2.0–5.0/week; LONG and SHORT each >=30%; max decision-year share <=30%; each 2018–2022 decision-year cadence 1.25–6.50/week; zero conflicts; deterministic replay.

Failure parks the exact UO re-entry mapping without economics and forbids same-ID rescue. Passing authorizes only a separately reviewed MQL5 implementation/parity stage. No MT5, trades, costs, returns, PF, validation, holdout, paper or live authority exists.
