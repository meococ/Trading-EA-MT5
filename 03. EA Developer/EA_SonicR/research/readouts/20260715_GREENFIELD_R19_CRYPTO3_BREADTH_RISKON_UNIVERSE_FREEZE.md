# Universe + rules freeze — Round 19 CRYPTO3 breadth / CADJPY risk-on / EURCHF sentiment

Date: 2026-07-15
Status: **FROZEN BEFORE METRICS** (a priori). Do not retune from readout.

Hard constraint: NON-FADE; outside R10–R18 densify; **FORBIDDEN** ETH H4 VR densify
(VR-k / hold / multi-sym rescue of that exact object); FORBIDDEN BTC/XAG ROC-k
thick clones; residual/corr/Parkinson/ON-ratio; fade/MR; unpark/exit/FRED.

Cost: +$12 / trade a priori. Window: 2021-01-01 → 2025-12-31. Gates: N≥80,
PF≥1.30, tpw≥2.0, PF@x1.5≥1.25. Model 0 only if PROBE_SURVIVOR.

---

## Book A — `HYP-CRYPTO3-H1-BREADTH-IMPULSE-CONT-BOOK-001`

| Field | Frozen value |
|---|---|
| Universe U | `{BTCUSD, ETHUSD, LTCUSD}` — fixed; no post-hoc add of SOL/XRP |
| TF | H1 closed-bar |
| Impulse | \|body\| ≥ **0.50** × ATR14 on signal bar |
| Breadth | ≥ **2** members same-sign impulse |
| Entry | next H1 open on each breadth member that fired (per-symbol heat) |
| Cap | ≤1 new entry / symbol / UTC day; no stack if already open on that symbol |
| SL / RR / hold | **1.50** ATR / **2.0** / ≤ **10** bars |
| Thesis | Crypto beta breadth continuation — multi-asset thick book by construction |
| Explicitly NOT | ETH variance-ratio mom; BTC D1 ROC TSMOM; UTC0 open-drive; VR-k/hold rescue |

## Object B — `HYP-CADJPY-H1-XTI-NAS-RISKON-CONT-001`

| Field | Frozen value |
|---|---|
| Trade symbol | CADJPY |
| Leads | XTIUSD + NAS100 H1 closed bars (same timestamp as-of) |
| Oil impulse | \|body_XTI\| ≥ **0.55** × ATR |
| Equity impulse | \|body_NAS\| ≥ **0.45** × ATR, **same sign** as oil |
| Entry | CADJPY next open, side = sign(oil) (risk-on co-impulse) |
| Cap | ≤1 / UTC day |
| SL / RR / hold | **1.45** / **2.0** / ≤ **10** |
| Explicitly NOT | WTI→USDCAD ToT densify; EURJPY←US30 lead; GBPJPY×EURJPY co-mom; yen-β resid |

## Object C — `HYP-EURCHF-H1-NAS-SENTIMENT-CONT-001`

| Field | Frozen value |
|---|---|
| Trade symbol | EURCHF |
| Lead | NAS100 H1 \|body\| ≥ **0.70** × ATR |
| Entry | EURCHF next open, side = sign(NAS) (risk sentiment → CHF cross) |
| Cap | ≤1 / UTC day |
| SL / RR / hold | **1.40** / **2.0** / ≤ **10** |
| Explicitly NOT | USDCHF FX-risk basket resid fade; US30 lead FX; session-edge densify |

Freeze SHA: `D6AB4A0BFCA24C58B659C2BCC6BC7C9698A088BD9B7946B3364C6035EB653062`
