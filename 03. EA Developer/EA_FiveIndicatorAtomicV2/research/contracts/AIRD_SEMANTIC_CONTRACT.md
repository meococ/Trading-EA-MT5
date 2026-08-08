# Semantic Contract — AI_Regime_Detection

Campaign: `FIV2-20260808-ATOMIC`  
Source fork SHA256: `26132998349052C66098FE94119C801D6F6E7F11E08FB1FB27C358672F20B17A`  
Path: `indicators/AI_Regime_Detection.mq5`  
Policy: **REUSE_AFTER_REAUDIT**

## 1. Original formula

Four-state (Bull/Bear/Range/HighVol) online Hamilton-style filter with feature vector (trend corr, RSI momentum, vol percentile, drift), tempered likelihoods, transition matrix online EM, jump-penalty held-regime decoding.

## 2. Update order

1. Features from closed OHLC/returns  
2. Emission likelihoods per state  
3. Forward filter / alpha recursion  
4. Online EM updates of A and μ (causal)  
5. Raw argmax regime  
6. Jump-penalty confirmation → held regime, confidence, change flag  

## 3. Warm-up

- Correlation/RSI/vol/drift lengths + EM burn-in.  
- `valid` buffer must be 1 before EA use.

## 4. Buffer ABI (public subset for EA)

| Idx | Meaning |
|---:|---|
| 5 | Confidence |
| 7–10 | P(Bull/Bear/Range/HighVol) % |
| 11 | valid 0/1 |
| 12 | held regime 0..3 |
| 13 | confirmed change event |
| 14–15 | raw regime / raw prob |
| 16–21 | features / vol diagnostics |
| 22–25 | age / switches / next regime |

Regimes: 0 Bull, 1 Bear, 2 Ranging, 3 HighVol.

## 5. State vs event

- **State:** held regime, probabilities, confidence, valid.  
- **Event:** confirmed change (13); not an entry trigger alone.

## 6. Non-repaint

- Closed-bar features only; `shift >= 1`.  
- Online EM is causal left-to-right; no smoothing with future bars.

## 7. EA read rules

- **Context only.** Never direct buy/sell.  
- ENGINE_R: held=2 Ranging + confidence floor.  
- ENGINE_T: held=0/1 matching direction + confidence.  
- ENGINE_B: transition/change or rising confidence with structure; block pure HighVol shock without TB displacement.
