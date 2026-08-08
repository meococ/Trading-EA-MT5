# Semantic Contract — Modern_Bollinger_Bands_GBB

Campaign: `FIV2-20260808-ATOMIC`  
Source fork SHA256: `D105F12CEADEC91D7F9A470D8977C28DCAA677C463E2B8282288E24ADA515F09`  
Path: `indicators/Modern_Bollinger_Bands_GBB.mq5`  
Policy: **REUSE_AFTER_REAUDIT**

## 1. Original formula

Adaptive/fixed length → KAMA or SMA basis → robust percentile or stdev bands → KER regime → squeeze score/state/release → S1/S2/S3 signal geometry.

## 2. Recursive / update order

1. Dominant cycle / adaptive length (if enabled)  
2. KER and percentile rank  
3. Regime hysteresis (trend enter/exit thresholds)  
4. Basis (KAMA recursive or SMA window)  
5. Band width (robust window or stdev)  
6. Bandwidth, squeeze score, squeeze state, release  
7. S1/S2/S3 raw flags and priority signal code  
8. Visual markers  

## 3. Warm-up

- Requires max(lookbacks): fixed/adaptive length, robust window, rank length (default 252), KER, squeeze min bars.
- Regime and bands `EMPTY_VALUE` until ready.

## 4. Buffer ABI (public)

| Idx | Meaning |
|---:|---|
| 0–2 | Fill upper/lower/color |
| 3–6 | Upper/lower bands + colors |
| 7–8 | Basis + color |
| 9–14 | Visual S1/S2/S3 marker prices |
| 15–17 | DC period / valid / length used |
| 18–19 | KER / KER percentile |
| 20 | Regime 0 range / 1 trend |
| 21–24 | Bandwidth / squeeze score / state / release |
| 25–30 | Raw S1L S1S S2L S2S S3L S3S flags |
| 31 | Priority signal ±1 S1, ±2 S2, ±3 S3 |

## 5. State vs event

- **State:** basis, bands, regime, squeeze state, bandwidth.  
- **Events (rising-edge):** S1/S2/S3 raw flags 25–30; release 24; priority 31 nonzero on event bars.

## 6. Non-repaint

- Consume `shift >= 1`.  
- Priority and raw flags must be fixed after bar close.

## 7. EA read rules

- ENGINE_R event: S1 (±1) or band reclaim rule using bands 3/5 + close.  
- ENGINE_T event: S2 (±2) / pullback-to-basis geometry.  
- ENGINE_B event: S3 (±3) with release 24.  
- Geometry only; not a majority vote input.
