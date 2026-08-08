# PREREG — HYP-FIV2-R-EURUSD-M5-STAGE0-001

Status: **FROZEN DRAFT (pre-run)**  
Outcome fields: **SEALED**  
Economic authority: **NONE**

## Identity

| Field | Value |
|---|---|
| Hypothesis ID | `HYP-FIV2-R-EURUSD-M5-STAGE0-001` |
| Campaign | `FIV2-20260808-ATOMIC` |
| Engine | ENGINE_R (Range / Mean Reversion) |
| Symbol | EURUSD |
| Timeframe | M5 |
| Model | Model 0 preferred when HQ>97%; Stage-0 is zero-trade |
| Broker terminal | FivePercent portable (`alpha.local.ps1`) |
| Window | DESIGN only: 2016-01-01 → 2021-06-30 |
| Embargo to validation | 7 calendar days (validation starts 2021-07-08) |

## Object under test

Outcome-blind **zero-trade** closed-bar census of ENGINE_R event clock and
context readiness on EURUSD M5 DESIGN bars.

No orders. No SL/TP. No MFE/MAE/return labels. No barrier outcomes.

## Decision surface (pre-filter raw event)

A raw candidate bar `t` (closed bar, shift≥1) requires **all**:

1. **MBB event**: S1 long or S1 short rising-edge **or** close re-enters robust band after exterior touch (definition fixed in indicator contract).
2. **AIRD context**: held regime == Ranging; `valid==1`; confidence ≥ `0.45` (design default; ablation later).
3. **VRC context**: regime in {mean_reverting=2, ranging=3, compression=7}; `stable_valid==1`.
4. **TB structure**: sweep/reclaim flag same side as MBB event within last `K=3` closed bars; `ClosedBarValid==1`.
5. **QQE timing**: composite state leaves extreme or primary zero-cross causal against extreme (exact rule in QQE contract); consume shift≥1.
6. **Readiness**: all five indicators ready; no EMPTY_VALUE; warm-up complete; spread/ATR recorded but not optimized here.

## Stage-0 acceptance (hard, pre-outcome)

| Gate | Floor |
|---|---|
| Export rows | One row per completed DESIGN bar with indicator readiness flags |
| Snapshot failures | 0 on indicator-ready bars |
| Duplicate timestamps | 0 |
| Nonfinite required fields | 0 |
| Raw ENGINE_R candidates / elapsed week | ≥ 25 (path to filters; not executable trades) |
| Long/short raw balance | Each direction ≥ 30% of raw candidates |
| Year coverage | Every full DESIGN year contributes ≥ 10% of raw candidates |
| Warm-up coverage | Ready fraction after max lookback ≥ 95% of post-warm bars |
| Signal conflicts | Document rate; fail if > 25% of raw candidates have opposite-engine simultaneous fire |
| Executable path estimate | After preregistered spread/ATR and one-position filters, projected cadence in **2–5 / week** band (estimate only; not PnL) |

If any hard Stage-0 gate fails:

- emit failure packet;
- **do not** relax thresholds under this ID;
- open a new ID only with a material mechanism/data-contract change.

## Explicit non-goals

- No PF, expectancy, Sharpe, or equity
- No parameter mining on DESIGN outcomes (none exist)
- No chart mining into filters
- No reuse of RSF/AIRQMB trade lists

## Success next step

If Stage-0 PASS → freeze ENGINE_R atomic probe prereg
`HYP-FIV2-R-EURUSD-M5-PROBE-002` (still DESIGN-only economics under nested plan).

## Artifact bindings (fill at freeze completion)

| Artifact | SHA256 |
|---|---|
| This prereg | TBD at hash seal |
| Campaign manifest | TBD |
| Indicator contracts set | TBD |
| Census EA / exporter source | TBD after build |
