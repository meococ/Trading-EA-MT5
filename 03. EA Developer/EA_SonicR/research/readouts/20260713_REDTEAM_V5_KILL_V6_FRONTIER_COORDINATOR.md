# Redteam Coordinator Readout — V5 Kill Affirmation + New-EA Search Boundary

Date: 2026-07-13  
Status: `REDTEAM_CLOSED / NO EA BUILD AUTHORIZED`  
Lane: new-strategy discovery after V5 offline falsification

## Decision

Coordinator merges three independent critic memos and affirms:

1. `Impact-per-Pressure Continuation` remains `KILL_AT_OFFLINE_PROBE`.
2. `Round-Number Release Persistence` remains `KILL_AT_INTAKE_DUPLICATE`.
3. Under the current retail MT5 data contract (OHLC + Bid/Ask quotes + tick
   volume + deterministic calendar), the local redteam finds
   `NO_LEGAL_CANDIDATE_FOR_IMMEDIATE_EA_BUILD`.
4. The only live search channel is Deep Research V6 already submitted from
   `20260713_NEW_STRATEGY_DEEP_RESEARCH_FAILURE_PACKET_V6.md`. Local agents
   must not invent a replacement EA while V6 is incomplete, and must not code
   any candidate until a later coordinator intake authorizes one frozen probe.

This readout authorizes neither registry row, preregistration, MQL5 source,
compile, Strategy Tester, nor demo/prop/live deployment.

## Critic panel

| Role | Agent | Local verdict |
|---|---|---|
| Sonic / FX trader critic | [trader critic](c8d64802-dd2d-4239-a349-cf665ab252cc) | Affirm kill; `NO_LEGAL_TRADER_CANDIDATE` under current contract |
| Quant validation critic | [quant critic](c9968413-00b9-4c6f-803c-32ca828a4591) | Process-correct kill; `NO_LEGAL_QUANT_DESIGN` without new external data |
| MQL5/MT5 systems critic | [systems critic](4096686b-d4de-44ef-8924-58f58f7750de) | Probe systems-safe; build authority = NO until probe+prereg gates open |

Coordinator owns the merge. Critic memos are advisory input only.

## Evidence base reviewed

- Goal: `01. GOAL/GOAL.md`
- V5 intake:
  `readouts/20260713_DEEP_RESEARCH_V5_COORDINATOR_INTAKE.md`
- V5 probe kill:
  `readouts/20260713_IMPACT_PRESSURE_PROXY_PROBE_READOUT.md`
- Probe artifacts: `preflight/v5_ipp/20260713_IPP_PROXY_PROBE_V1/`
- Locked families: `20260713_NEW_STRATEGY_DEEP_RESEARCH_FAILURE_PACKET_V3.md`
- Active search packet:
  `20260713_NEW_STRATEGY_DEEP_RESEARCH_FAILURE_PACKET_V6.md`
- V6 submission receipt:
  `preflight/20260713_NEW_STRATEGY_DEEP_RESEARCH_SUBMISSION_V6.json`
- Portfolio frontier:
  `20260710_EA_FAILURE_PORTFOLIO_AUDIT.md` (`0/217` joint PF+cadence survivors)

## Merge findings

### Trader

The academic order-flow mechanism does not transfer to retail Bid/Ask quote
ticks. `q=sign(Δmid)` is the same price path being predicted. Gross expectancy
was already negative before cost stress, so this is not a friction near-miss.
Any rename into imbalance / CVD / toxicity / tick-direction is the same dead
family. No additional local trader mechanism was proposed without requiring
external surprise, futures basis, or true trade-flow data.

### Quant

The frozen probe process passed: one contract, train/holdout split, elapsed-
calendar cadence, train-matched return-z control (`50,058` = `50,058`), and no
post-hoc threshold mining. Six performance/identity gates failed by large
margins (pooled cadence `177.70`/week vs `2–5.5`; holdout stress-B PF `0.340`
vs GOAL `>1.30`; candidate lost to control holdout PF `0.404`). Reparameterizing
IPP, hour/day vetoes from this readout, or Model-1 screens are forbidden.

### Systems

The probe was read-only, issued zero orders, created no MQL5, and did not call
MetaEditor or Strategy Tester. Hash-bound artifacts are sufficient to close the
candidate at the probe stage. They are not sufficient to authorize compile.
Any later EA, if ever earned, still requires closed-bar decisions, Model 0,
`sonic_telemetry.v3`, non-repaint audit, and same-broker cost provenance before
the first meaningful Tester run.

## New-EA search disposition

| Path | Disposition |
|---|---|
| Rescue / tune V5 IPP or Round-Number | Banned |
| Immediate MQL5 EA from local ideation | Banned |
| Local “new idea” without de-dup + frozen probe | Banned |
| Deep Research V6 (already submitted) | Allowed search channel only |
| V6 result extraction + local source audit + de-dup | Next coordinator work when V6 completes |
| One frozen offline probe for a V6 survivor | Conditional, only after intake pass |
| Registry / prereg / EA code / compile / Tester | Still unauthorized |

Required external-state reopeners if V6 returns `NO LEGAL CANDIDATE`:

1. Reconstructable real-time macro expectations + audited release timestamps; or
2. Lawful synchronized COMEX GC L1/trades + roll metadata; or
3. True signed trade / participant flow not derived from `sign(Δmid)`; and
4. Same-broker executable cost/slippage provenance before Model 0 promotion claims.

## Authority after this readout

Allowed now:

- wait for / extract Deep Research V6 result;
- local source audit and family de-duplication of any V6 proposal;
- update `hot.md` when V6 completes.

Not allowed now:

- invent a parallel local EA candidate to bypass V6;
- append registry rows;
- freeze a prereg;
- write or edit strategy MQL5;
- compile, backtest, optimize, or deploy.

## Next move

1. When conversation
   `https://chatgpt.com/c/6a54f339-93c0-83ec-b966-d022564ca116`
   completes, extract the exact V6 verdict (`ONE LEGAL CANDIDATE` or
   `NO LEGAL CANDIDATE`) into a hash-bound result receipt.
2. Run coordinator intake with fresh de-dup against V2–V5 locks and the
   portfolio audit boundary.
3. Only a de-dup-surviving candidate may receive exactly one frozen offline
   probe. Fail closes the family. Pass still does not auto-authorize EA code.
