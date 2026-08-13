# HYP-QPF-EURUSD-M1-004 source verdict

Verdict: `KILL_QUOTE_PATH_FIDELITY_EXACT_EURUSD_METATICKS`

This is an engineering-valid, outcome-blind source verdict. It is not an
economic backtest and does not authorize a Sonic R child, optimization, paper
trading or live trading.

## Frozen run

- Run: `EA_QuotePathFidelityProbe/20260812_205728`
- FivePercent Real EURUSD M1, MT5 Model 0, `[2018-01-01,2026-08-01)`
- History Quality: 99%; report ticks: 207,698,274; report bars: 3,194,620
- Completed M5 buckets: 639,403; CSV ticks: 207,696,735
- Trades/orders: 0; net profit: 0; out-of-order buckets: 0
- AlphaFactory data-quality gate: `FULL_2018_PLUS`; D0 proof passed; journal
  complete and untruncated.
- Required CSV is present once and hash-bound in the completed manifest.

## Frozen simultaneous gates

Passed pooled and for every year 2018-2026:

- invalid quote share `0.0` <= `0.001`;
- reverse millisecond clocks `0`;
- positive timestamp coverage `1.0`;
- active buckets with at least 20 changes `0.9913794586512732` >= `0.95`;
- duplicate transition share `0.006806394943119327` < `0.05`;
- spread-change share `0.5419591913274862` >= `0.01`.

Failed pooled and for every year 2018-2026:

- one-sided quote-update share was `0.0019210883561223745` versus the frozen
  `0.05` minimum. Annual values ranged from about `0.0001504` to `0.0089853`.

The gap is structural and large. The exact native EURUSD MetaTicks path does
not preserve enough one-sided Bid-versus-Ask update events for the proposed
asynchronous revision-clock family. The gate cannot be lowered, the years
cannot be shortened, and the denominator/symbol cannot be changed under this
object.

## Artifact bindings

- Manifest SHA256:
  `47658A1D6BB7B0D4476AE6A2572BAF68F60C207F09BECF026619DC31585DB7CA`
- CSV SHA256:
  `E8D5F5F0BC36049EB18B8EE0B4118675419FBDD038D1FE0617ED5CDC3080D796`
- Result SHA256:
  `39506AE9F93E800CFE70BDB47629B6B042F330BF0DB04F5EC4B8430C82D12B48`
- Report SHA256:
  `7EC5AF59E0B8FAEF4966231546FB6BDF81FDFBC63BDBFCEA062AC968FC3E275C`
- Journal SHA256:
  `DED3E7D7F72E9C6EA0E258A58453A157AD53F38A7D04FE01054D297E099182BA`
- Source SHA256:
  `A0FA62262839B8B10D405CA4EAD3C0C99802815B81CDAB0231144A9174F7F499`

The generic non-repaint audit cannot authorize this collection receipt because
its current collection-authority branch requires `required_sidecars=[]`, while
this preregistered source run requires exactly one CSV. Without the receipt it
flags only the D0 `CopyTime` availability proof as an unproven shift. That call
is the exact fail-closed AlphaFactory series proof, not a signal or outcome
read. The EA contains no trade API and no economic or directional logic.

## Closure

No closed-M5/M15 economic child may be opened from this object. Discovery must
move to a materially distinct information family and pass de-dup plus a fresh
source-capability contract before reading outcomes.
