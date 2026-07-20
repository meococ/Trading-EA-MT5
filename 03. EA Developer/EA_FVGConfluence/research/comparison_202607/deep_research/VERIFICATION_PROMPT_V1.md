# Deep Research Pass 2 - Verification After Cohort Freeze

Use only the frozen cohort supplied with this prompt. Do not add candidates.

For every frozen entity, find the strongest primary performance evidence and
classify it:

- A: independent live history with full account verification.
- B: source/demo reproducible on hash-bound data.
- C: vendor copy, screenshot, review, or vendor backtest.

Performance eligibility requires at least 36 months, 200 closed trades, no
hidden/custom-start history, observable deposits/withdrawals, and either both
Myfxbook Track Record plus Trading Privileges or an MQL5 real monitored account
with full history. Verification does not prove strategy attribution or remove
selection bias. Grade C never enters return ranking.

Also verify the Barclay Currency Traders Index definition, any regulated CTA
program only after identity/status checking through NFA BASIC and applicable
CFTC performance presentation, and FX DARWINs with at least 36 months as a
secondary risk-normalized cohort. Do not call them ICT traders without direct
style evidence.

Return a source ledger with URL, access date, exact evidence, missing fields,
grade, inclusion decision, rejection reason, delisted/terminated state, and
confidence. Preserve every rejected entity. If fewer than five grade A/B
comparable EA accounts survive, the mandatory performance verdict is
INSUFFICIENT_VERIFIED_DATA. Do not substitute reviews, leaderboards, payouts,
or top-trader anecdotes.

