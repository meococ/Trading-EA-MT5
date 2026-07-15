# De-dup clearance — Dichotomy-break offline probes

Date: 2026-07-14  
Authority: Owner dichotomy-break mandate; GPT waived  
Status: `A_PRIORI_CLEARANCE_BEFORE_PROBE`

## Kill / park shelf (do not retune)

V1-V7 structural · PWHL/H4BAL · Path-B D1-H1-PB · Wave3-5 session/IB/ATR%ile/Asia-box/NY-IB · stop-run/LNY/FVG/OB · MaxKZ/RR densify · T1 cost-arm · AUDJPY-lead standalone · bond/OIS/VIX directional signals · SBSparkBook scaffold · Phase-0 compose without contamination clear.

## D1 — `HYP-RR2-EXIT-BE1R-M15PATH-001`

| Prior | Why distinct |
|---|---|
| T1 cost-arm KILL | T1 filtered entries by min risk_$; this changes exit path (BE@1.0R) on same entries |
| MaxKZ/RR densify | RR and MaxKZ frozen; exit architecture only |
| ATR-stop PARK | Not ATR-stop replace; BE then original TP |

Independence: frozen RR2 trade opens → M15 path BE@1R → joint screen.

## D2 — `HYP-RR2-USJP-YIELD-ZGATE-001`

| Prior | Why distinct |
|---|---|
| USEU/USUK/EU-curve bond signal KILL | Those were exo→direction entries; this is allow gate on frozen RR2 |
| VIX risk-off USDJPY signal KILL | VIX unused; US-JP yield z gate only |
| USBILL Model0 KILL | Different series + gate semantics on SB RR2 |

Independence: lagged us_jp_bond_yield_diff_d1_v1 |z|>=0.75 allow; else skip.

## D3 — `HYP-BOOK-CORRCAP-RR2-SPARK-001`

| Prior | Why distinct |
|---|---|
| Phase-0 equal-join | Equal-join keeps overlaps; this rejects overlapping opens (max concurrent=1) |
| SBSparkBook 224302 KILL | Scaffold portfolio EA; this is offline CorrCap on frozen run IDs |
| V6/V7 multi-symbol price clones | No new EUR/GBP/XAU entry geometry |

Independence: a priori overlap contract on 194548+193358.

## Probe gate (a priori)

KILL if N<80 OR tpw not in [1.0,6.5] OR PF<1.05 OR +$12 x1.5 PF<1.10.
PROBE_SURVIVOR only if PF>1.20 AND tpw in [1.5,6] AND x1.5 PF>=1.15.
No post-readout param mine.
