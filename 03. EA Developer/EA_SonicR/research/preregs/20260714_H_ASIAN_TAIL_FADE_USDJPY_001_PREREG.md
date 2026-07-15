# Prereg — HYP-ASIAN-TAIL-FADE-USDJPY-001

Date: 2026-07-14  
State on freeze: `preregistered`  
Authority: Owner rebuke — continue R&D; systems #1 AsianTailFade port

## Identity

- Hypothesis ID: `HYP-ASIAN-TAIL-FADE-USDJPY-001`
- EA: `EA_M15AsianTailFade`
- Path: `03. EA Developer/EA_M15AsianTailFade/EA_M15AsianTailFade.mq5`
- Parent scaffold: `EA_AsianTailFade` (XAU-oriented) — **USDJPY ATR port**, not gold pts

## Thesis

Early Asia (h0–h3) directional accumulation; late Asia (h4–h8) fade toward
partial reversion before London handoff. Mechanical inventory-flattening
proxy. Independent of Spark Asian range-break continuation and killed ASR
London reclaim.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | USDJPY M15 |
| Window | 2021.01.01–2025.12.31 |
| Deposit | 100000 |
| Model | 0 |
| Early / fade / close | 0–3 / 4–8 / force 9 |
| Move gate | 0.60–4.0 ATR (not fixed gold points) |
| Days | Mon–Thu; Fri off |
| Risk | 0.50%; max 2/day; SL 1.5 ATR; TP 0.50·early-move (floor 1.0R) |
| Magic | 880973 |
| Overrides | (none) |

## De-dup

- Not `EA_M15SparkAsian` (continuation / Asian range)
- Not `HYP-ASIAN-SWEEP-RECLAIM-M15-001` (killed N=0 London reclaim)
- Not FailedORB / EMAStretch / ADRExhaust
- Not XAU `EA_AsianTailFade` gold-point thresholds

## Kill / Park / HIT

Standard Model 0 research bar.

## Cost honesty

Tester `current` only. Not confirmed.

## Banned

- Mining early/fade hours from readout
- Restoring gold MinMovePts as USDJPY rescue
- Trading Fri after freeze
