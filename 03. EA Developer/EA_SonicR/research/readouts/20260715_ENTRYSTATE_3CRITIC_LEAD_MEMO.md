# Lead memo (3-critic) — next path after ATR-trail Model0 double KILL

Date: 2026-07-15
Panel: Sonic trader / quant validation / MQL5 systems (lead merge)
Authority: Owner R&D continue; exit family exhausted; QFSI parallel only
Receipt: `85C53902CAC674BFE11369CF080BCFC8670668C5A71A310CE614B3D7CD8A246D`

## Situation (evidence)

- ARM075 `20260715_081213` PF 1.100 / ×1.5 **0.666** → KILL
- ARM100 `20260715_082030` PF 1.086 / ×1.5 **0.715** → KILL
- Offline MFE-envelope invalidated as deploy evidence
- RR2 exit family (BE@1R / MFE stall / ATR-trail) **exhausted** on Model 0
- Best shelf still RR2 `194548`; cost freeze GAP; GOAL unmet

## Critic theses (a priori — chosen path)

| Critic | Highest-EV class now | Why |
|---|---|---|
| Sonic trader | **Entry-state rebuild** (impulse confirm on SB) | Edge death is selection quality, not exit plumbing; limp FVGs bleed under +$12 |
| Quant validation | **Book rule** drop thin-risk legs | Post-friction EV is size×edge − cost; cut cost-dominated quartile without exit spam |
| MQL5/MT5 systems | **Independent Asia PD-close magnet sleeve** | Executable closed-bar H1; no trail tick path; de-dup vs coil/LNY/PDH |

## Rejected a priori

- Densify trail arm/k or reopen BE@1R / MFE stall / scaleout / timebox
- FRED displace/ToT · LNY fade/coil/catchup · XS residual/mom · AUDNZD z
- Asia pctl coil densify · MaxKZ/RR · H4 regime · vol-target rescale
- Invent research-grade cost freeze from shallow QFSI
- Login / Real stall as headline (QFSI accumulate stays parallel)

## Offline joint screen

| ID | N | PF | tpw | x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
| `HYP-RR2-ENTRY-IMPULSE-BODYATR-GATE-001` | 167 | 1.0613 | 0.6405 | 0.8213 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-RR2-BOOK-DROP-THINRISK-P25-001` | 393 | 1.3316 | 1.5074 | 1.0219 | **KILLED_AT_OFFLINE_PROBE** |
| `HYP-USDJPY-H1-ASIA-PDCLOSE-MAGNET-FADE-001` | 766 | 0.8953 | 2.9381 | 0.8228 | **KILLED_AT_OFFLINE_PROBE** |

## Coordinator decision

- Survivors: **0** / 3
- Model 0: **WITHHELD_ZERO_SURVIVOR**
- `EXO_FRED_DISPLACE_SPAM_PAUSED` remains
- Do not densify impulse body_atr / thinrisk pctl / magnet ATR from readout
- Best shelf: RR2 `20260714_194548` — GOAL unmet

## Highest-EV next if all kill

1. Keep QFSI accumulate toward research-grade cost (parallel, not blocker headline)
2. Next board: new independent signal architecture **outside** this entry/book/magnet pack (not exit, not FRED/LNY/XS densify)
