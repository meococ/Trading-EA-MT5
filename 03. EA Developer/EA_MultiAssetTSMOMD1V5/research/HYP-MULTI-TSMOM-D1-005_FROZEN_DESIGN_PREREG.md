# HYP-MULTI-TSMOM-D1-005 — frozen Jetta-H1 TSMOM DESIGN

Status: frozen before any V5 performance or PnL was inspected. The complete
source-validation and MT5 import gates must pass before this DESIGN cell may
run.

## Economic mechanism

The candidate is a diversified own-asset time-series-momentum portfolio across
seven liquid FX pairs, XAUUSD and BTCUSD. The claim is slow information and
capital-flow adjustment expressed through persistent multi-week trends. It is
not a candle-pattern, intraday-session, spread-arbitrage or tick-latency claim.

## Frozen signal, weights and execution

- Decision once per UTC Monday at the first common trade-ready generated H1
  tick for all active assets.
- Signal is only the sign of the most recent completed D1 close divided by the
  completed D1 close at or before the 365-calendar-day cutoff, minus one.
- Volatility is the sample standard deviation of 60 completed D1 log returns,
  annualized by observed calendar density.
- Missing data for any active asset invalidates the entire weekly snapshot.
- BTC becomes active at 2018-05-14 00:00 UTC; the other eight assets are active
  from the start of DESIGN.
- Inverse-volatility weights are capped only downward: 18% single asset, 70%
  aggregate FX, 25% XAU, 20% BTC, 25% absolute USD factor and 100% total gross.
  Freed capacity is never redistributed upward.
- Positions move by signed net delta. Reversals close the old direction before
  opening the new direction. There is no SL, TP, session/news alpha filter,
  daily/weekly loss filter, time exit or parameter optimization.

## Frozen source identity

- Official current Dukascopy Historical Data Export widget Jetta service.
- Monthly H1 BID/ASK; source spread is contemporaneous ASK open minus BID open.
- All prices are rounded to the source point. The default O/C envelope cap is
  one point. BTC source precision is two decimals; only BTC 2017-09 has a
  source-only exception capped at 50 points per bar and 5% corrected bars per
  side. The bound comes from the hash-bound full-history geometry profile
  (2017-05 through 2026-08): observed maxima were 4 BID and 33 ASK points in
  that month and zero in every other BTC month. Anything outside the frozen
  month, point cap or frequency cap fails.
- Ten BTC ASK/BID opens are crossed in official 2017-11/12 H1 payloads, all
  strictly before frozen BTC activation and none on/after activation. Those
  inactive-only bars receive one spread point solely for MT5 custom-rate
  validity; every raw hash/timestamp/deficit remains in the source profile and
  any crossed active bar fails.
- Custom M1 control bars deterministically preserve each H1 O/H/L/C and spread.
  Their intrahour path has no signal authority.
- Source contract SHA256:
  `82CB1576C9F7968F111225515A2F303727308A47C5EC2EA47579194F45C6CB9E`.
- BTC source-geometry profile SHA256:
  `6256A57B87A7B41EE700E0DDFABB3B23CEEFE2BA3D27E529A16B81C51E8CC243`.
- BTC open-spread profile SHA256:
  `CDFDC9BFD8AED137285EF60DFF8CC960D132541ABE6D6F23A951C898ABA946B0`.
- EA source SHA256:
  `F72034814CFD0FC9A887C574EDBBC3952F73579B8FC36C8EC3FF62149EDDE057`.
- EA EX5 SHA256:
  `D9394E9912B2E5EB8732E591F094206D28A22B28B47A6E27DE0D54E43226F87A`.
- Importer EX5 SHA256:
  `0C6EBDE8825929EEA67C3C10B0A38DAC3218A5746CDE91506889C89A64590EBC`.

## Frozen costs

The native custom-rate Bid/Ask spread remains inside MT5 deal profit. Native
signed swap is removed and replaced by the controlled adverse financing
overlay. Native commission remains in native net; only any shortfall versus the
frozen commission target is subtracted.

Per side commission is fixed before economics as USD 2 per standard FX lot,
0.001% of XAU deal notional and 0.03% of BTC deal notional. Same-terminal MT5
receipts contain 56 XAU and 218 BTC commissioned deals. Additional adverse
slippage is charged from every entry and exit deal's contemporaneous one-spread
USD value.

Financing floors are 6% annualized FX, 9% XAU and 70% BTC. FX/XAU weekday
coefficients Monday-first are `[1,1,1,1,3,0,0]`; BTC is `[1,1,1,1,1,1,1]`.
This is a conservative current-broker proxy, not historical PIT financing.

Cost scenarios are fixed as:

| Scenario | Commission | Extra slippage | Financing |
|---|---:|---:|---:|
| base | 1.00x | 0.25 spread/deal | 1.00x |
| adverse | 1.25x | 0.50 spread/deal | 1.50x |
| severe | 1.50x | 1.00 spread/deal | 2.00x |

Cost contract SHA256:
`81894A3D163A9D1AA055CCC55DD5696BF2D470CEE079AC06A49ABA30DCCC6801`.

## Frozen splits

- DESIGN: `[2018-01-01, 2022-01-01)`.
- VALIDATION: `[2022-01-01, 2024-01-01)`; sealed until DESIGN passes.
- HOLDOUT: `[2024-01-01, 2026-08-12)`; sealed until VALIDATION passes.

No source, commission, slippage, financing, universe, activation, direction,
lookback, volatility window, cap or execution change may be made after reading
the DESIGN result. Any change requires a new hypothesis identity.

## DESIGN acceptance

The cell must have at least 207 source-valid Monday decisions and at least 180
completed target transitions, with no failed terminal transition. Native MT5
profit factor after its imported spread must be at least 1.25. Base and adverse
controlled-cost adjusted net must be positive; severe adjusted net must be
nonnegative. Base adjusted annual return divided by native maximum equity
drawdown must be at least 0.70, native maximum equity drawdown must not exceed
18%, and at least three of four calendar years must be profitable before the
sealed validation is opened.

The candidate must also beat a separate hash-bound run of the same EX5 with
`InpLongOnlyComparator=true`, magic `260812008`, and otherwise identical source,
volatility, caps and costs on native PF and base adjusted annual return.
Top 5% realized weeks may contribute at most 25% of positive net profit and no
single asset may contribute more than 40%. These concentration diagnostics do
not authorize post-hoc filtering.

Failure kills this exact V5 identity. Passing DESIGN authorizes only the sealed
VALIDATION run, not live use or promotion.
