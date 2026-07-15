# Design memo — Multi-day H4–D1 swing thick book

Date: 2026-07-15
Lane: single; offline-first; `EXO_FRED_DISPLACE_SPAM_PAUSED`
Panel: nested `cursor-grok-4.5-high-fast`

## Problem

Entry-state / exit / FRED / LNY / XS boards exhausted. Need a **new class**:
multi-day swing thick enough that +$12 RT is a small fraction of R, with
2–5/wk from **multi-symbol OR multi-setup portfolio** and frozen overlap
rules — not densify of SB/RR2/entry/exit packs.

## Design 1 — D1 ADX + H4 thrust3 continuation

`HYP-FX3-D1ADX-H4-THRUST3-SWING-001`

**Thesis:** D1 trend strength (ADX≥25 + DI align) plus same-direction H4
three-bar thrust marks multi-day continuation; thick SL (1.75 ATR beyond
leg) + RR=3; FX3 pool with ≤2 open and EUR/GBP same-day ADX arbiter.

**Frozen:** universe EURUSD/GBPUSD/USDJPY; ADX14≥25; thrust step≥0.25 ATR;
SL 1.75 ATR beyond 3-bar extreme (min 1.5 ATR from entry); RR=3; hold≤28 H4;
≤1/symbol; ≤2 book; EUR+GBP same-dir same UTC day → higher D1 ADX only.

## Design 2 — D1 trend-day + ROC persist multi-setup book

`HYP-FX3-D1-TRENDDAY-ROC-BOOK-001`

**Thesis:** Two independent D1 persistence setups (trend-day body dominance
and short/medium ROC agreement) supply cadence; TD beats RP same day;
thick SL 1.60 ATR; RR=2.5; same FX3 portfolio caps.

**Frozen:** TD: range≥1.15 ATR_D1 and body/range≥0.70; RP: sign(ROC3)=sign(ROC10)
and |Δ3|≥1.0 ATR_D1; entry next H4 open after D1 close; hold≤32 H4;
EUR+GBP same-dir → larger range/ATR; TD>RP priority.

## Model 0 policy

Only if offline `PROBE_SURVIVOR`. Else withhold.

## If both fail — next object class

Multi-symbol **D1 volatility-regime breakout** (ATR14/ATR50 expansion
threshold + close beyond prior 8-day extreme) with same frozen portfolio
caps — still not channel/NR7/EMA-PB densify.
