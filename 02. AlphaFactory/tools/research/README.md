# Research Kit (probe SDK)

Shared, mechanism-neutral primitives for offline probes. New lanes import from
here instead of copying code; frozen terminal lanes keep their local copies
untouched (runnable-as-run).

## Charter — no strategy in the SDK

The kit contains PHYSICS only: data loading/sealing, indicator math, trade
statistics, control generators, deflation, clock models, rendering, log
triage. It must never contain:

- entry/exit/gate logic or templates that encode a mechanism;
- default thresholds, windows, sessions, symbols or periods of any strategy
  (every such value is a caller argument frozen in the lane's plan);
- anything fit to one lane's data quirks beyond documented, measured
  constraints (e.g. the broker clock model is a measured fact, not a tune).

If a helper only makes sense for one strategy family, it belongs in that
lane's package, not here.

## Modules

| Module | Role |
|---|---|
| `indicators.py` | Single-source indicator math. TWO variant families: `*_wilder` (literature) and `*_mt5` (`atr_mt5` = SMA of TR, `adx_mt5` = EMA of per-bar DI — parity-proven ~5e-11 vs iATR/iADX build 6006; `rsi_wilder` matches iRSI). A frozen plan must state which variant family it uses; Model-0-bound lanes use `*_mt5`. |
| `sealed_loader.py` | Holdout-sealed parquet loading (read-time filter + assert + seal receipt), split tagging, elapsed calendar weeks |
| `trial_log.py` | Canonical trial-log appender (`hypothesis_id` + `prereg_sha256` required, numpy-safe, one serialization) |
| `metrics.py` | PF, expectancy, DD (R / %), by-year, DSR inputs, top-1 share, leave-one-out PF |
| `controls.py` | Matched-random and time-shift entry generators (timestamps only; the lane's frozen exit engine simulates them) |
| `dsr.py` | Deflated Sharpe Ratio + trial-accounting conventions |
| `fivepercent_server_clock.py` | Measured FivePercent server→UTC model (era-hybrid DST) |
| `chart_case_render.py` | Per-case candlestick PNGs from hash-bound bars (asof/anatomy) |
| `log_triage.py` | Streaming error-pattern battery for heavy logs |
| `snapshot_c_roots.ps1` | Protected-C-roots before/after receipts (single digest source) |
| `parity_harness.py` + `mql5/ParityDump.mq5` | MT5 iATR/iADX/iRSI vs python parity: capture in-terminal values on identical bars, compare with tolerances, emit verdict artifact |

Usage from a lane script:

```python
import sys
sys.path.insert(0, r"02. AlphaFactory/tools/research")
from indicators import atr_wilder
from sealed_loader import load_sealed_bars
```
