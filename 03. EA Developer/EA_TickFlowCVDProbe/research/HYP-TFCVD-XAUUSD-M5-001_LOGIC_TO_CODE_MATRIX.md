# Logic-to-code matrix — HYP-TFCVD-XAUUSD-M5-001

| Trader observation | Quantified role | Decision-time data | Source location | Telemetry / proof |
|---|---|---|---|---|
| Intrabar buying/selling pressure can be approximated by polarized lower-timeframe activity | Build one signed quote-update count per completed M5 bar | Bid/Ask ticks received during the bar only | `ProcessTick()` | `up_updates`, `down_updates`, `zero_mid_updates`, `quote_tick_delta` |
| Equal-price activity must not be silently discarded or hindsight-labelled | Carry the most recent non-zero tick polarity; use zero only before any polarity exists | Prior and current mid only | `ProcessTick()` | `zero_mid_updates`, `classified_updates` |
| Absorption means strong one-sided activity with weak/opposite price displacement | Source-only event: `abs(delta/classified)>=0.35`, at least 20 unique/classified updates, close efficiency `<=0.20`, and delta x close displacement `<=0` | The just-completed M5 bar only | `analyze_tick_flow_source.py::is_candidate()` | event count, direction balance, cadence; no future return |
| CFD volume is not exchange aggressor volume | Primary weight is one per unique Bid/Ask update; trade/volume flags remain diagnostics only | `MqlTick.flags`, `volume`, `volume_real` | `ProcessTick()` | `trade_flag_ticks`, `buy_flag_ticks`, `sell_flag_ticks`, `positive_volume_ticks` |
| Missing or invalid ticks invalidate evidence rather than create a signal | Reject non-finite/non-positive/crossed quotes; record counts; never substitute bars | Current tick only | `QuoteValid()` | `invalid_ticks`, `valid_quote_ticks`, `gap_from_prev_bars` |
| An economic child must be causal | The completed absorption bar may only inform a decision at the next M5 open | Row emitted only when a later bar begins | `FinalizeBar()` | static test asserts finalize-before-current-bar consumption |
| This stage cannot trade | No trade classes/functions/hooks or FILE_COMMON | Entire source | whole-file static test | zero forbidden trading/API tokens |
