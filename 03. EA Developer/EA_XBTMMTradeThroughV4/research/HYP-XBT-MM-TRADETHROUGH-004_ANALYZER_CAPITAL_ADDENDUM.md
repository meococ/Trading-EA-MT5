# HYP-XBT-MM-TRADETHROUGH-004 — Analyzer Capital Addendum

Status: frozen before full-DESIGN engineering or economic results.

Disposition: never executed. V4 subsequently failed the source/expiry gate and
economics remained forbidden; see `HYP-XBT-MM-TRADETHROUGH-004_SOURCE_GATE_RESULT.md`.

This addendum changes reporting and economic gates only. It does not change the
V4 signal, quote price, fill, latency, inventory, funding, or source contract.

## Exchange-mechanics disposition

- The strict trade-through full-fill rule is retained. Under BitMEX price-time
  priority, a public execution strictly through a displayed resting price means
  executable displayed liquidity at that better price was exhausted. The size
  of the final through-price print is not a cap on the fill at the resting
  price. Primary rule: https://www.bitmex.com/legal/exchange-rules (Rule 9.18).
- The same-latency, same-size, same-risk best-touch engine remains the matched
  null. An arbitrary wider quote would change the opportunity set.
- The 400 ms activation delay already replays all intervening market events and
  is economic, not a cosmetic latency adjustment.

## Outcome-blind capital contract

- `Reference_Risk_Capital_USD = HARD_CAP_CONTRACTS * 1 USD = 400 USD`.
- This is the unlevered 1x capacity of the declared hard inventory cap. It never
  depends on observed inventory, observed margin, or realized outcomes.
- Convert every ledger `realized_delta_xbt` to USD at that row's exact execution
  price.
- Strategy NAV starts at 400 USD and changes only by strategy PnL. BTC collateral
  beta is excluded.
- Annualized return is `total_realized_usd / 400 / (1461 / 365.25)`.
- The EA's original 1 XBT NAV and drawdown remain engineering telemetry only.

## Additional DESIGN gates

- Base annualized return on reference risk capital: at least 15%.
- At 15 bps forced-taker cost (2x the frozen 7.5 bps): annualized return must
  remain strictly positive and PF must remain at least 1.00.
- Daily maximum drawdown on the 400 USD strategy NAV: at most 12%.
- Recovery from the maximum daily drawdown: at most 45 calendar days.
- Existing PF, yearly fill/coverage, matched-null, holding-time, concentration,
  and engineering gates remain binding.

## Promotion boundary

If V4 passes every DESIGN gate, its verdict is
`PASS_DESIGN_REQUIRES_V5_INTRADAY_RISK`, not promotion-ready. A fresh metrics-only
V5 replay must report exact intraday USD-equivalent mark-to-market drawdown. V5
must preserve the V4 signal and fill logic byte-for-byte in behavior; it is not
an opportunity to tune the strategy after observing V4.
