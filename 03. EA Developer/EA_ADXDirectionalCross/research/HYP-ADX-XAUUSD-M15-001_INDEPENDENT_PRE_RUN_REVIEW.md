# Independent pre-run review — HYP-ADX-XAUUSD-M15-001

Verdict: `PASS_BUILD` / baseline permitted after compile and nonrepaint evidence.

- Native `iADX(14)` buffer mapping is `0=ADX`, `1=+DI`, `2=-DI`.
- `CopyBuffer(start_pos=1,count=2)` maps oldest shift 2 to array index 0 and newest shift 1 to index 1.
- The DI crossover with `ADX>=25` and rising ADX is causal on completed bars; decision is exact next M15 open.
- The atomic DI-cross event is materially different from the ATR impulse/pullback/release object where ADX was only a confirmation.
- Novelty is moderate because ADX and the adjacent Vortex polarity family exist. One untuned baseline only; no period/threshold/rising-lag/timeframe/session/direction/exit rescue.

Reviewer made no edits and opened no outcomes.
