# V8 COT TFF Spec-Net Change Probe Contract V1 — 2026-07-13

Status: `JOIN_CONTRACT_FROZEN / OFFLINE_PROBE_ONLY / NO_EA_BUILD`

## Authority

Owner autonomous GOAL mandate + Owner order to skip GPT Deep Research
(2026-07-13). Self-research from workspace COT TFF archives only. This
contract authorizes exactly one cheap offline probe. It does not authorize
registry append, prereg freeze, MQL5 EA code, MetaEditor compile, or Strategy
Tester.

## Independence (de-dup)

Not a carry / public-rates rescue. Carry weekly, daily, and rate-event probes
are already `KILL_AT_OFFLINE_PROBE` for cadence/sample. Causal variable here is
CFTC Traders in Financial Futures (TFF) speculative positioning change, not
short-rate differentials.

Not a rename of `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001`.

## Probe identity

- Working ID: `HYP-SR-FX-COT-TFF-SPEC-NET-001` (mint only if later registered)
- Probe tag: `V8_COT_TFF_SPEC_NET_CHG_V1`
- Mechanism: after the lagged COT release, trade FX in the direction of the
  weekly change in Asset Manager + Leveraged Money net futures positioning.

## Data

- Sources: `preflight/v8_exogenous/raw/cot_tff_extracted/FinFutYY_202{2,3,4,5}.txt`
- Markets mapped:
  - `EURO FX - CHICAGO MERCANTILE EXCHANGE` → EURUSD (positive Δspec → long EURUSD)
  - `BRITISH POUND - CHICAGO MERCANTILE EXCHANGE` or `BRITISH POUND STERLING`
    → GBPUSD (positive Δspec → long GBPUSD)
  - `JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE` → USDJPY
    (positive Δspec on JPY futures → short USDJPY; negative → long USDJPY)
- `spec_net = (Asset_Mgr_Long - Asset_Mgr_Short) + (Lev_Money_Long - Lev_Money_Short)`
- `available_at_utc = Report_Date + 3 calendar days at 00:00Z`
  (conservative proxy for Friday CFTC release of Tuesday as-of data; no
  same-week peek).
- Fail closed on missing market week for a required symbol.

## Signal (frozen)

On each `available_at` date with a completed prior week:

1. Compute `d_spec = spec_net_t - spec_net_{t-1}`.
2. Require `|d_spec| / max(OI_t, 1) >= 0.015` (a priori 1.5% of open interest).
3. Direction as mapped above; flat if threshold fails.
4. Enter on the first closed D1 bar at or after `available_at` (MetaQuotes-Demo
   falsification OK). Exit on the next COT decision or Friday flatten before
   weekend (scalp contract: no weekend hold).
5. Stop: 1.5 * ATR14_D1 from entry; time-stop at next COT decision.

One position per symbol; symbols independent (up to three concurrent sleeves).

## Control

Same COT calendar and threshold machinery, but direction = sign of prior
5 completed D1 log returns of the FX pair (rates/COT unused). Isolates
positioning change from ordinary price continuation.

## Cost stress (kill-only)

Stress A 1.5 pip RT; Stress B 3.0 pip RT. Missing broker provenance ≠ zero.

## Splits

- Train: `[2022-01-01, 2024-01-01)` (COT archive starts 2022)
- Holdout: `[2024-01-01, 2026-01-01)` gated behind train pass

## Kill gates (train)

- trades < 80
- trades/elapsed_week < 0.5
- stress-A PF < 1.05
- fail to beat control on stress-A PF **and** expectancy
- year concentration of positive net > 0.55 (if evaluated)

## Explicit non-rescues after readout

Do not retune the 1.5% OI threshold, swap Asset Mgr vs Lev Money only, or
add price filters mined from this probe. A survivor requires new ID + prereg.
