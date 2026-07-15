# De-dup clearance — Discovery Wave6 (joint thick + cadence)

Date: 2026-07-14  
Authority: Owner CONTINUE Wave6 — Hunt thick expectancy AND 2–5/wk  
GPT: waived · Grok · no-Git · cost honesty  
Status: `A_PRIORI_CLEARANCE_BEFORE_PROBE`

## Joint screen (intake)

HIT only if: PF>1.30 ∧ tpw∈[2,5] ∧ +$12 x1.5≥1.25 ∧ x2≥1.00.  
Offline kill-fast if: N<80 OR tpw∉[1,6] OR PF<1 OR +$12×1.5 PF<1.25.

## Forbidden densify / reopen (do not retune)

MaxKZ / RR2 / SB-Spark book filters · USBILL · PIN / ThreeBar / Outside /
Engulf / EQHL / PDH / H4-struct / LNY DualWin · IB / GBPJPY-lead / ATR%ile
(just PARK) · Asia-box · NY-IB Drive · RV-compress · Donchian MR ·
impulse-halfback · double-inside · gap-fade · FVG · OB · PWHL · H4-balance ·
NR7 densify · D1→H1 PB · V1–V6 / V6-multisym full board.

## H1 — `HYP-H1-MONO-CONTRACT-BREAK-001`

| Prior | Why distinct |
|---|---|
| NR7 **PARK** | Not “narrowest of N”; **3 consecutive shrinking ranges** |
| Double-inside **KILL** | No nested-inside; envelope = minH/maxL of coil |
| RV-compress Donchian **PARK** | No Donchian; no RV ratio |
| Halfback **KILL** | No impulse→50% PB; entry = coil H/L break+close |

Independence: H1 r[i]<r[i-1]<r[i-2] → break+close of coil → continuation.

## H2 — `HYP-M15-BROKEN-LEVEL-RETEST-001`

| Prior | Why distinct |
|---|---|
| H1-BOS + M15 EMA-PB **KILL** | No H1 BOS; no EMA; M15 swing break→retest |
| H4-struct M15 accept **KILL** | No H4 swing; pure M15 pivot L=3 |
| PDH retest **PARK** | Swing pivot, not prior-day H/L |
| Stop-run accept **KILL** | Cont after accepted break+retest, not PD sweep |

Independence: M15 pivot break → retest within 8 bars → close hold → cont.

## H3 — `HYP-H1-FORMING-DAY-EXT-FADE-001`

| Prior | Why distinct |
|---|---|
| D1→H1 PB cont **KILL** | Fade of late day extension, not trend PB |
| Gap fade **KILL** | No open-gap vs prior close |
| Asian/London fail-fade **KILL** | No session box; forming day range progress |
| Donchian / ATR%ile MR **KILL/PARK** | Day-envelope extreme, not Donchian/ATR%ile |

Independence: ≥10 H1 of day + forming range ≥0.80×ATR14 → fade pierce beyond
0.90 of forming day range toward day mid.

## H4 — `HYP-FX3-H1-BODYATR-CONT-PORTFOLIO-001`

| Prior | Why distinct |
|---|---|
| ATR%ile Donchian **PARK** | Gate = **body/ATR of signal bar**, not hist %ile band |
| VolExp / TickVol **KILL** | H1 body-ATR impulse cont; no M15 RV / tick-vol |
| Halfback **KILL** | No pullback; next-bar open continuation |
| GBPJPY-lead **PARK** | Equal-weight **EURUSD+USDJPY+GBPUSD** same rule a priori; not lead pair |
| SB/Spark book **forbidden** | New price-lawful portfolio rule, not densify parked sleeves |

Independence: closed H1 body≥1.0×ATR14 + close in extreme quartile → next open
cont; RR=2.5; pool 3 majors a priori (portfolio cadence lift, not post-hoc pick).

## Probe / Model 0 policy

- Model 0 **only** if `PROBE_SURVIVOR` (or near-pass with explicit promote path).
- No densify from readout. Kill/park fast.
- Cost grade offline: `UNVERIFIED_OFFLINE_PROXY` (+$12 cash stress baked).
