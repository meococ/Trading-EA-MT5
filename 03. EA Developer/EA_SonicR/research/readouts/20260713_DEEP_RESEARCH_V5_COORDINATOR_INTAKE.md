# Deep Research V5 Coordinator Intake

Date: 2026-07-13  
Status: `ONE FROZEN PROXY PROBE AUTHORIZED / NO EA CODE AUTHORIZED`

## Owner intent

The lane must discover and test a genuinely new MT5 strategy, not turn the
research objective into a data-infrastructure project. Deep Research output is
an idea source only. The coordinator owns source audit, family de-duplication,
the cheap-probe contract, and the final kill/continue decision.

## V5 result

Authoritative conversation:
`https://chatgpt.com/c/6a54e57c-892c-83ec-9446-cafddaa53193`

Deep Research returned two current-data candidates and ranked exactly one for a
first probe:

1. `Impact-per-Pressure Continuation` (rank 1).
2. `Round-Number Release Persistence` (rank 2).

Candidate 2 is rejected at intake. It is a cosmetic symbol/session variant of
the closed `S558 / EA_GoldRound` family. That family already failed both the
rejection and breakout interpretations on retail M15 evidence. A symbol switch
from XAUUSD to EURUSD/GBPUSD does not create an independent causal mechanism.

Candidate 1 is adjacent to, but not byte-for-byte identical with, `S617`,
`S624`, `S625`, `S677`, and `S679`. Those rows already warn that retail
tick-volume and price-derived flow proxies are fragile or regime-concentrated.
The new formula therefore receives one cheap falsification probe, not a new
hypothesis ID, preregistration, or EA implementation.

## Source audit

The cited microstructure literature does not validate the proposed MT5 proxy:

- Evans and Lyons describe signed order flow as a proximate exchange-rate
  determinant: `https://www.nber.org/papers/w7317`.
- Breedon and Vitale use direct EBS/Reuters FX transactions:
  `https://www.ecb.europa.eu/pub/research/authors/profiles/francis-breedon.en.html`.
- Ranaldo and Somogyi use participant-classified CLS order flow:
  `https://www.sciencedirect.com/science/article/pii/S0304405X20303470`.
- `MqlTick` and `CopyTicksRange` distinguish Bid/Ask quote changes from
  Last/Volume trade ticks and Buy/Sell deal flags:
  `https://www.mql5.com/en/docs/constants/structures/mqltick` and
  `https://www.mql5.com/en/docs/series/copyticksrange`.

The live one-hour MetaQuotes-Demo read-only audit had Bid/Ask quote updates but
zero Last, Volume, Buy, and Sell observations for both EURUSD and GBPUSD.
Consequently `q = sign(mid[t] - mid[t-1])` is not signed order flow. It is a
price-path transform. Under equal one-point moves, the proposed statistic
largely reduces to directional efficiency and move per quote update. The
matched return-shock control is therefore a hard identity test: the candidate
must beat that control, not merely produce a positive standalone PF.

## Frozen probe contract

- Symbols: `EURUSD`, `GBPUSD`.
- Bar: closed `M15`; signal on the closed bar; entry at the first executable
  Bid/Ask tick of the next contiguous bar.
- Train: `[2018-01-01, 2023-01-01)` UTC.
- Holdout: `[2023-01-01, 2026-01-01)` UTC.
- Formula: exactly V5 `IPP`, `PE`, `Raw`, and prior-20 robust z-score.
- Fixed constants: `k=2.7`, `c=1.5`, `Nmin=30`.
- Exit: stop `0.5 * abs(signal Move)`, target `1.0 * abs(signal Move)`, time
  stop after two M15 bars. If both barriers appear inside one aggregated bar,
  assume adverse-first.
- Cost stress A: `0.8 pip` round trip.
- Cost stress B: `1.2 pip` round trip.
- Negative control: absolute prior-20 return z-score threshold selected once on
  train to match the pooled primary train signal count.
- Exactly one run; no threshold changes, exclusions, symbol vetoes, time vetoes,
  or rescue filters after reading its outcome.

Hard kill gates:

- pooled trades `<180` or holdout trades `<60`;
- pooled cadence outside `2.0-5.5` trades per elapsed calendar week;
- holdout PF under stress B `<1.20` or pooled PF under stress B `<1.25`;
- holdout expectancy under stress B `<=0`;
- pooled max drawdown `>8R`;
- positive-PnL concentration above year `45%`, symbol `70%`, or side `70%`;
- primary does not strictly beat the matched control on holdout PF,
  expectancy, and net pips;
- missing/incorrect source coverage or any feed/server identity mismatch.

The V5 report also named a `12%` drawdown ceiling. This discovery probe has no
account-risk sizing, so percent drawdown is not computable and cannot be
silently approximated. If the probe passes every computable gate, the later
preregistration must bind risk sizing and restore the `12%` Model 0 ceiling.

## Data authority boundary

The local FivePercentOnline-Real tick-cache directory has monthly EURUSD and
GBPUSD files covering `201601` through `202607`, but file presence is not
API-validated continuity or broker identity proof. The active read-only MT5
login is `MetaQuotes-Demo`.

One run on MetaQuotes-Demo is authorized only as research-only falsification:

- a failure kills the proxy candidate;
- a pass cannot promote it, cannot satisfy FivePercent provenance, and cannot
  authorize production claims;
- any later serious run must first repeat source continuity and formula checks
  under the target broker login.

## Authority after this intake

Allowed now: focused unit tests, source hashes, one frozen read-only offline
probe, and a coordinator readout.

Not allowed now: registry row, preregistration, MQL5 EA source, compile,
Strategy Tester Model 0, optimization, WFA, demo/prop/live deployment, or any
order/trade mutation.
