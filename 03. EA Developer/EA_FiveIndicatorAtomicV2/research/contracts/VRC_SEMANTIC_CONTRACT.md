# Semantic Contract — Volatility_Regime_Classifier_QuantRegime

Campaign: `FIV2-20260808-ATOMIC`  
Source fork SHA256: `400AA62B6FD00A35F711D15F61075CED86D6D5571EF0B22932B0915BB93AD8BC`  
Path: `indicators/Volatility_Regime_Classifier_QuantRegime.mq5`  
Policy: **REUSE_AFTER_REAUDIT**  
License: MPL-2.0 (Ac wernert95; MQL5 port) — attribution retained.

## 1. Original formula

Composite of smoothed Hurst, ADX/DI, Choppiness, ATR percentile → nine regimes (−1..7) plus compression; direction and component scores.

## 2. Update order

1. ATR / ATR percentile  
2. ADX family (DI+, DI−, ADX)  
3. Choppiness  
4. Hurst estimate + smooth  
5. Component scores trend/chop/Hurst  
6. Composite score → regime map  
7. Change / previous regime / high-low vol flags  

## 3. Warm-up

- Max of Hurst (100), vol rank (100), ADX, chop, ATR lengths.  
- Buffer 31 stable/full-lookback valid must be 1.

## 4. Buffer ABI (EA-critical)

| Idx | Meaning |
|---:|---|
| 14–18 | Hurst / ADX / DI+ / DI− / CHOP |
| 19–21 | ATR pct / ATR / composite |
| 22–25 | direction / regime / changed / previous |
| 26–27 | high-vol / low-vol flags |
| 31 | stable valid |
| 32–35 | component / raw Hurst |

Regimes: −1 strong bear … 2 mean-rev, 3 ranging, … 6 strong bull, 7 compression.

## 5. State vs event

- **State:** regime, direction, vol flags, scores.  
- **Event:** regime changed (24).

## 6. Non-repaint

- `shift >= 1`; no future windows.

## 7. EA read rules

- Cost/risk/vol context, not bullish/bearish vote.  
- ENGINE_R: mean-rev/ranging/compression-compatible.  
- ENGINE_T: trend-compatible; block compression + high-cost shock.  
- ENGINE_B: compression→expansion path; spread/ATR gate with ATR buffers.
