# Intake kill — HYP-H1-EQHL-SWEEP-RECLAIM-001

Date: 2026-07-14 ~22:35 ICT  
Verdict: **`KILL_AT_INTAKE_DUPLICATE`**  
Authority: Owner CONTINUE post PIN/THREEBAR — mandatory de-dup vs AsianSweep / TailFade / SFP / AsianTail before code  
GPT: waived

## Claimed candidate

`HYP-H1-EQHL-SWEEP-RECLAIM-001` — equal-high/low liquidity pool → closed-bar
sweep beyond EQH/EQL → reclaim continuity (a priori RR≈3).

## Contrast table

| Prior ID / family | Mechanism | Relation to EQHL |
|---|---|---|
| `HYP-ASIAN-SWEEP-RECLAIM-M15-001` **KILL** N=0 | Asia H/L lock → London pierce+close-inside → mid reclaim continuity | **Same archetype**: horizontal H/L liquidity grab then reclaim. EQHL only swaps level constructor (equal HL cluster vs Asia session range). |
| `HYP-H1-SWING-FAILURE-001` / SFP **KILL** PF 0.97 | H1 pivot L=2 pierce → close back inside → fade | **Same liquidity-grab object family**: equal highs/lows are a pivot-cluster constructor for SFP. Sweep+close-back is textbook SFP. |
| `HYP-ASIAN-TAIL-FADE-USDJPY-001` **KILL** | Early-Asia ATR move fade late Asia | **Independent** (inventory fade, not level sweep-reclaim) — not the kill axis |
| VWAP reclaim / PDH / FailedORB | Session/PDH/OR objects | Different objects; still do not rescue EQHL |

## Independence claim rejected

Changing the **level constructor** after ASR N=0 and SFP PF-kill is densify /
near-clone of the sweep-reclaim + SFP family — not a new thick edge. No
prereg freeze, no EA, no Model 0.

## Action

1. Registry: `killed` at intake (`KILL_AT_INTAKE_DUPLICATE`).
2. Same-run successor (already Wave4-cleared, not EQHL retune):
   `HYP-M15-IB-OVERLAP-BREAK-001` → offline probe then Model 0 if survives.
3. Backup stubs already frozen: `HYP-H1-RV-COMPRESS-BREAK-001`,
   `HYP-GBPJPY-LEAD-USDJPY-H1-001`.

## Explicit bans

No EQHL tolerance / lookback / RR retune; no AsianSweep hour rescue; no SFP
PivotL mine; no PIN/ThreeBar/Outside/Engulf/MaxKZ/RR densify; no USBILL.
