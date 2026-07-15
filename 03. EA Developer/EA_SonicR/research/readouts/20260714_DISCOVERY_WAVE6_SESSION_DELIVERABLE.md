# Deliverable — Discovery Wave6 (joint thick + cadence hunt)

Date: 2026-07-14 ~23:50 ICT  
Authority: Owner CONTINUE Wave6  
GPT: waived · Grok · free MT · no-Git · cost honesty

## Verdict

**`WAVE6_EXECUTED_EMPTY` / zero Model 0.** Không ID nào đạt joint screen
PF>1.30 ∧ tpw∈[2,5] ∧ x1.5≥1.25 ∧ x2≥1.00. GOAL unmet.

## Board

### Pack A (SHA `AB9ED62F…BE9176`)

| ID | N | PF | tpw | x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-H1-MONO-CONTRACT-BREAK-001` | 740 | 1.13 | 2.84 | 1.07 | **KILL** stress *(V7/V8 collision confirm)* |
| `HYP-M15-BROKEN-LEVEL-RETEST-001` | 1464 | 1.09 | 5.61 | 1.05 | **KILL** stress *(V7/V8 collision confirm)* |
| `HYP-H1-FORMING-DAY-EXT-FADE-001` | 670 | 0.89 | 2.57 | 0.84 | **KILL** pf+stress |
| `HYP-FX3-H1-BODYATR-CONT-PORTFOLIO-001` | 2814 | 1.07 | 10.79 | 1.01 | **KILL** cadence overload+stress |

### Pack B (SHA `B38AE9E3…B04902DFF`)

| ID | N | PF | tpw | x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-H1-MOTHER-BAR-BREAK-001` | 377 | **1.33** | 1.45 | **1.23** | **KILL** stress (near) |
| `HYP-H1-THREE-DAY-HIGHLOW-BREAK-001` | 265 | **1.69** | **1.02** | **1.41** | **PARK** thick; cadence starve |
| `HYP-USDCHF-H1-LONDON-RANGE-BREAK-001` | 692 | 0.99 | 2.65 | 0.91 | **KILL** pf+stress |

### Pack C promote-path (SHA `F2AB710B…D843A3`)

| ID | N | PF | tpw | x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-FX3-H1-THREE-DAY-HL-BREAK-PORTFOLIO-001` | 1079 | 1.05 | **4.14** | **0.85** | **KILL** stress |

Cadence lift a priori trên 3 majors **phá** thickness của USDJPY-only PARK —
không densify; confirm tradeoff cứng.

## HARD_EMPTY property

Thiếu **đồng thời** trên mọi object Wave6 (+ V7/V8 confirm):

1. Expectancy dày sau +$12 (x1.5≥1.25), **và**
2. Cadence 2–5/wk elapsed, **và**
3. PF>1.30 raw.

Tách rời vẫn thấy: (A) thick+stress / starve cadence = 3-day PARK;
(B) cadence OK / thin stress = coil/retest/bodyATR; (C) pool→cadence↑ / PF↓.

## Best candidate (unchanged shelf)

- Historical RR2 `194548` PF~1.38 / ~2.01/wk — friction fragile; current
  Model 0 `231750` weaker PF 1.16 (parallel lane).
- Wave6 diagnostic park: `HYP-H1-THREE-DAY-HIGHLOW-BREAK-001` — **do not densify**
  lookback/body/RR; FX3 child already KILL.

## Next auto (lawful, no stall)

1. **Local price tiếp:** object mới ngoài mother/3-day/USDCHF/FX3/V1–V8
   (ví dụ NZD/CAD session-structure độc lập) — offline first.
2. **Account/data:** Real QFSI hygiene song song cho shelf RR2/SB/Spark
   (không headline stop; không densify).
3. **Blocked data-gate:** `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001` cần
   tick sync — không fake bằng bar-only.

## Files

- Dedup A/B: `readouts/20260714_DISCOVERY_WAVE6_DEDUP_CLEARANCE.md`,
  `…WAVE6B_DEDUP_CLEARANCE.md`
- Probes: `preflight/20260714_DISCOVERY_WAVE6_OFFLINE_PROBES.json` (+B/C)
- Readouts: `readouts/20260714_DISCOVERY_WAVE6_OFFLINE_PROBES.md` (+B/C)
- Preregs under `preregs/20260714_H_*` for each ID
- Registry appends: lane `discovery_wave6_20260714`
