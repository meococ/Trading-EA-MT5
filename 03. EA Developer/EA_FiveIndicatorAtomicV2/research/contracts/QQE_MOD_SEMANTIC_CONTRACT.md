# Semantic Contract — QQE_MOD

Campaign: `FIV2-20260808-ATOMIC`  
Source fork SHA256: `0CD4381B49B49E7B41D0DB99281158FCB03A2AC79FABC492AB8921F2A4BE2F78`  
Path: `indicators/QQE_MOD.mq5`  
Policy: **REUSE_AFTER_REAUDIT** (not economic evidence)

## 1. Original formula (closed-bar)

Dual QQE lanes (primary + secondary), each:

1. RSI on applied price (default close), length `RSILength`.
2. Wilder-style avg gain/loss recursion → RSI.
3. RSI smoothed (EMA-like of length `RSISmoothing`) → centered at 0 (`RSI-50`).
4. ATR-of-RSI style absolute change smoothed → QQE bands with factor.
5. Trend line follows long/short band state machine.
6. Secondary histogram vs threshold; primary has Bollinger on primary QQE.
7. Composite state: +1 up / −1 down / 0 neutral from dual-lane agreement rules.
8. Primary zero-cross event: rising-edge of centered primary RSI through 0.

Primary and secondary are **one momentum family**. EA must not treat them as independent votes.

## 2. Recursive state update order

Per bar index ascending (time series, non-series buffers):

1. Source price  
2. Avg gain/loss → RSI  
3. Smoothed RSI centered  
4. Smoothed ATR-RSI  
5. Long/short bands from previous band + trend state  
6. QQE trend line  
7. Bollinger on primary QQE (secondary path: histogram/threshold)  
8. Composite state + primary cross event  

## 3. Initialization / warm-up

- Until RSI and smoothing lengths are satisfied → public values `EMPTY_VALUE` / neutral 0 where defined.
- Fail-closed: EA requires finite buffers and no reliance on forming bar.

## 4. Buffer ABI (public iCustom)

| Idx | Meaning | Type |
|---:|---|---|
| 0 | Secondary RSI histogram (0 inside neutral) | state/plot |
| 1 | Histogram color 0/1/2 | visual |
| 2 | Secondary QQE trend line (centered) | state |
| 3 | Primary smoothed RSI centered | state |
| 4 | Secondary smoothed RSI centered | state |
| 5 | Primary QQE trend line centered | state |
| 6/7 | Primary QQE Bollinger upper/lower | state |
| 8 | Composite state +1/−1/0 | **state** |
| 9 | Primary zero-cross +1/−1/0 | **event / rising-edge** |
| 10..12 | Visual mirrors only | not EA signals |

## 5. State vs event

- **State:** buffers 0–8 (continuous or held).  
- **Event:** buffer 9 (primary zero-cross); composite transitions must be detected by EA as edge if used.

## 6. Non-repaint conditions

- Alerts and EA reads only on **closed bar**, `shift >= 1`.
- No future bar peek; recursion uses `index-1` only.
- Forming bar may paint but is not decision-legal.

## 7. EA read rules

- `CopyBuffer(..., shift>=1)`.
- Timing confirmation only; never sole regime vote.
- ENGINE_R: extreme loss / cross-back.  
- ENGINE_T/B: same-direction re-acceleration / impulse using composite state edges + optional buffer 9.
