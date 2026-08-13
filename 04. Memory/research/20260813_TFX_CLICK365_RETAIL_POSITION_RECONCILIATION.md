# TFX Click365 retail-position reconciliation - 2026-08-13

## Scope and evidence boundary

- Source-only, outcome-blind audit of one USDJPY information object after the
  H4/D1 multi-horizon reset: Click365 weekly buy-side versus sell-side open
  positions (`weekly_sellbuy.xls`).
- Weekly cadence is not an automatic rejection. The source still had to prove
  free official 2018-latest first-public history, an identical live surface,
  a deterministic publication clock, PIT/revision semantics, exact population
  and units, lawful internal use, a source-defined USDJPY sign and holding
  horizon, adequate independent releases and source-family novelty.
- No target return, PF, threshold, fitted inversion, payload download, paid
  quote, purchase, code, compile, MT5 run or backtest was opened.
- Grok Build independently checked official TFX/Click365 material. Lead kept
  the final verdict bounded to the actual public source contract.

## Official-source reconciliation

- TFX Historical Database: https://www.tfx.co.jp/en/historical/
  The database page permits use without restrictions or fees, but that license
  applies to the database content actually exposed there.
- TFX Click365 historical FX files:
  https://www.tfx.co.jp/en/historical/fx/
  They expose daily OHLC, volume, swap points and total open interest. They do
  not expose the required buy-side versus sell-side position split.
- TFX notice dated 2012-09-10:
  https://www.tfx.co.jp/newsfile/article/20120910-01
  Pair-level buy/sell open-position data were distributed through information
  vendors to Click365 firms/institutions, with individuals obtaining access
  through brokers contracted with those vendors. That is not a free official
  2018-latest first-public archive.
- Current Click365 FX trading-trend surface:
  https://www.click365.jp/market.html
  Resource description:
  https://www.click365.jp/service/resorces/
  The public object is updated weekly on Tuesday from the prior Tuesday close
  and retains only the past 42 weeks. It is a rolling live display/file, not an
  immutable historical vintage tape.
- TFX's 2013-04-16 notice describes publication at about 10:00 JST and a much
  shorter then-current public history:
  https://www.tfx.co.jp/newsfile/article/20130416-01
  The approximate clock does not cure the missing 2018-latest first-public
  chain or establish revision/vintage replay for overwritten rows.

## Signal, horizon and de-dup

- Buy/sell positions describe the participant positioning population, but TFX
  does not define whether an imbalance should be faded or followed in USDJPY.
  Choosing contrarian versus continuation after target outcomes would be a
  fitted direction and is forbidden.
- TFX does not document a causal H4/D1 holding horizon that must terminate by
  Friday. The Tuesday publication cadence alone cannot manufacture that link.
- The Click365 participant population is distinct from CFTC positioning, but
  distinctness cannot repair the missing historical/PIT/sign contract.
- Total open interest from the free historical database is directionless and
  cannot substitute for the rejected buy/sell object; doing so would also
  reopen the already consumed aggregate-OI family.

## Verdict

`NO_TFX_RETAIL_POSITION_CANDIDATE`

First fatal gate: the official free buy/sell history is a rolling 42-week
overwrite, not an immutable 2018-latest first-public archive. The missing PIT
chain, non-deterministic publication clock, undefined fade/follow sign and
undocumented Friday-flat horizon are independent fail-closed blockers.

Do not download `weekly_sellbuy.xls`, substitute total OI, switch to CFTC or
open a vendor purchase from this receipt. This is a scoped source rejection,
not an economic backtest verdict and not global infeasibility. No hypothesis or
registry row is created. Overall goal remains `ACTIVE / UNMET`; no market
mechanism is active.
