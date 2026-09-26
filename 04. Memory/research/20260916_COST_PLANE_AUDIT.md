# Cost-plane audit — MetaQuotes-Demo economics for scalping (read-only)

Date: 2026-09-16. Status: `AUDIT_ONLY_NO_HYPOTHESIS_NO_RUN`.
Trigger: Owner 2026-09-16 re-focus on scalping EA; audit the cost/commission
assumption before any tick-scalp probe (step 1 of the plan).

## Question

Does the falsification cost model (`RESEARCH_PROXY` in every era-2 kill) reflect
what MetaQuotes-Demo actually charges, and what is the true round-trip cost a
scalper would face?

## Sources (read-only)

- `02. AlphaFactory/runs/EA_IchiTn/20260912_150306/config/run_manifest.json`
  (`spread=1`, `model=0`, broker/server fingerprints).
- `03. EA Developer/EA_IchiTn/research/evidence/COST_SOURCE_MANIFEST.json`.
- `03. EA Developer/EA_IchiTn/research/evidence/GBPUSD_spread_ticks.csv`
  (SHA `CF2471D5...`), `GBPUSD_slippage_quotes.csv` (SHA `3EE1A880...`).
- `02. AlphaFactory/tools/measure_cost_evidence.py:132` (`current_spread_points`
  = `info.spread` measured at loop time).
- `02. AlphaFactory/tools/build_research_cost_proxy_evidence.py` (proxy builder).
- 26 × `runs/**/analysis/verified_cost_artifact.json` (per-trade repricing).

## Findings

1. **The $7.00/lot round-turn commission is an assumed conservative bound, not
   broker reality.** COST_SOURCE_MANIFEST.json says: "broker-observed commission
   is 0.00 on every deal of the governed run; a $7.00/lot round-turn bound is
   applied to real position lifecycles so the falsification screen never
   understates cost." MetaQuotes-Demo commission on this plane = 0.
2. **Spread model = fixed 1 point (0.1 pip GBPUSD) applied to all 27 years**,
   measured from live quotes 2026-09-07→2026-09-11 (1,763,354 rows, raw sample
   window). Live sample: p50 ≈ 0.0-0.1 pip, p90 = 0.1 pip in liquid hours;
   **hour 00 UTC rollover p50 = 1.1 / p90 = 5.4 pips** (hard blackout for any
   scalper). Historical spread variation (1999-2025) is not modelled.
3. **Slippage proxy** = p90 adverse quote move 250 ms after decision quote:
   0.1 pip per side (0.2 pip round turn), measured over the same 5-day window.
4. **Dropping the $7 bound does not un-kill any cell.** Recompute over all 26
   artifacts (scenario = gross_r − slippage_r, commission = 0):

   | hypothesis | sym | n | PF gross | PF x1 proxy | PF comm=0 |
   |---|---|---:|---:|---:|---:|
   | HYP-H4PB-EU-M5-001 | EURUSD | 1,251 | 0.931 | 0.765 | 0.889 |
   | HYP-CAMF-EU-M15-001 | EURUSD | 14,755 | 0.908 | 0.763 | 0.871 |
   | HYP-H1D-EUR-M5-001 | EURUSD | 6,907 | 0.878 | 0.763 | 0.848 |
   | HYP-ICHITN-GB-M5-001 | GBPUSD | 21,738 | 0.833 | 0.703 | 0.797 |
   | HYP-GBB-S3-XAU-M15-001 | XAUUSD | 408 | 1.001 | 0.748 | 0.787 |

   Mean gross expectancy per trade is negative for every cell (range ≈ −0.03R
   to −0.15R). The kills are edge-negative, not cost artifacts. The commission
   bound moves PF by only ≈ +0.03..+0.13, nowhere near 1.30.
5. **True demo cost for scalp geometry** (spread + market slippage, comm 0):
   ≈ 0.1-0.3 pip round turn on EURUSD/GBPUSD outside the rollover hour. A
   2-4 pip-target tick scalper therefore pays ≈ 3-10% of R in cost, versus the
   ≈ 25-50% the conservative proxy assumes at such stops.
6. **Data-plane gate for tick microstructure (step 2).** All era-2 runs used
   `Model=0` ("Every tick" generated from M1), not real ticks. The mqdemo
   portable holds real-tick cache only for 202609 (`bases/MetaQuotes-Demo/ticks/*/202609.tkc`);
   deep real-tick availability on MQ-Demo is unverified. The FivePercent
   real-tick corpus documented in
   `04. Memory/research/20260812_NATIVE_REAL_TICK_CAPABILITY_INVENTORY.md`
   (EURUSD/GBPUSD/USDJPY 2018+, ~1-1.5 GiB each) is **not present** under
   `02. AlphaFactory/runtime/` anymore (only `mt5-portable-mqdemo` remains;
   `init_machine_paths.ps1` describes fivepercent as an unused alternate tree).

## Consequence for the scalping plan

- The M5-indicator class was not killed by the commission bound; adding cost
  accuracy does not revive it.
- The economics plane is favorable for a true tick scalper only if the signal
  clears ≈ 0.1-0.3 pip round-turn edge per trade (outside 00 UTC rollover).
- Step 2 (counts-only tick qualification + named microstructure probe) is
  blocked on the real-tick data plane: either MQ-Demo real ticks must be proven
  deep enough for the frozen window, or the FivePercent portable tree must be
  re-provisioned. No hypothesis may be minted until this gate clears.

Producer: this audit is a read-only re-read of bound artifacts; no strategy,
registry row, run, or cost contract was modified.
