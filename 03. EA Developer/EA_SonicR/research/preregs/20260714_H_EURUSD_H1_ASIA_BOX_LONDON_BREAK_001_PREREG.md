# Prereg — HYP-EURUSD-H1-ASIA-BOX-LONDON-BREAK-001

Date: 2026-07-14  
State on freeze: `FROZEN / preregistered`  
Authority: Owner Discovery Wave5 — joint thick + cadence (new symbol)  
GPT: waived

## Identity

- Hypothesis ID: `HYP-EURUSD-H1-ASIA-BOX-LONDON-BREAK-001`
- EA: `EA_EURUSD_H1AsiaBoxLondonBreak`
- Path: `03. EA Developer/EA_EURUSD_H1AsiaBoxLondonBreak/EA_EURUSD_H1AsiaBoxLondonBreak.mq5`
- Explicitly **not**: LondonORB USDJPY; IB-overlap densify; AsianSweep reclaim

## Thesis

**EURUSD** Asia H1 box [0,7) locks a session range; London [7,16) closed-bar
break with mid ATR%ile ∈[40,70] and body quality is regime×session
microstructure designed for **joint** cadence (daily London opportunity) and
thick expectancy (mid-vol + RR=2.5 quality). New symbol avoids USDJPY family
contamination.

## Locked Design

| Item | Frozen |
|---|---|
| Symbol/TF | EURUSD H1 |
| Window | 2021.01.01–2025.12.31 |
| Deposit | 100000 |
| Model | 0 |
| Asia box | server hours [0,7) H1 high/low lock |
| Break window | [7,16); close beyond box; body≥0.35 ATR; ATR%ile-100 ∈[40,70] |
| Days | Mon–Thu; Fri off |
| Risk / RR | 0.50% / 2.5 |
| SL | beyond opposite box extreme + 0.10×ATR |
| Max/day | 2 |
| Flat | hour≥22 / weekend; max hold 24 H1 |
| Magic | 880996 |
| Overrides | (none) |

## Kill / Park / HIT

Same Wave5 screen as ATR-pctile sibling.

## Cost honesty

`UNVERIFIED_TESTER_DEFAULT`. Not Real QFSI. Not GOAL.

## Independence

`readouts/20260714_DISCOVERY_WAVE5_DEDUP_CLEARANCE.md`
