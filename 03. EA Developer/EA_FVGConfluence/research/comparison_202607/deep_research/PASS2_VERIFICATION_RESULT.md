# Pass 2 - frozen-cohort performance verification

The GPT-5.6 Sol / Pro / Deep Research response is bound by
`PASS2_VERIFICATION_RECEIPT.json`. It inspected exactly F01-F15 after cohort
freeze and returned the mandatory verdict `INSUFFICIENT_VERIFIED_DATA`.

## Frozen EA cohort result

- Grade A: 0.
- Grade B: 0.
- Grade C: 15.
- Performance-eligible exact-product accounts: 0; the minimum was 5.
- No return ranking, average CAGR, or best-EA claim is permitted.

F01 had the closest account-level evidence: an MQL5 signal from the same
author, but only 40 weeks and 226 trades. The provider disclosed that a second
EA was added and attributed an earlier drawdown to another EA, so exact-product
attribution to Liquidity Sweeper failed. F02 exposed only vendor-controlled
backtest images without a complete hash-bound experiment. F03-F14 exposed
vendor descriptions/reviews only. F15 claimed Strategy Tester capability but
did not expose the binary/source, preset, data manifest, MT5 build, execution
model, and complete report required for Grade B.

## Professional context result

- The Barclay Currency Traders Index remains a broad equal-weight composite of
  managed currency programs, not an exact-EA account cohort.
- NFA BASIC is an identity/registration gate, not performance verification.
  No named CTA program existed in the frozen cohort, so admitted CTA programs
  remained zero.
- Nine DARWINs with Forex exposure and more than 36 months were recorded as a
  secondary risk-normalized context subset only. They often also trade indices
  or commodities, expose gross rather than strategy-attributed net returns,
  and provide no evidence of ICT/FVG style. They do not replace the missing EA
  cohort or the current EA's absent OOS monthly series.

The result is a discovery input, not independent proof by itself. The machine
ledger preserves all 15 rejections and the final readout is produced by the
local fail-closed validator.
