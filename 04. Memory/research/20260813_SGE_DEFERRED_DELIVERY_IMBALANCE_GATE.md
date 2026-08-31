# SGE Au(T+D) deferred-delivery imbalance gate - 2026-08-13

## Scope and evidence boundary

- Source/mechanism-only, outcome-blind audit of one potentially fresh XAUUSD
  object: the Au(T+D) deferred compensation fee direction and reported delivery
  volume in official Shanghai Gold Exchange daily reports.
- The proposed sign was audited before acceptance: `Short pays Long` / `空付多`
  as BUY XAUUSD, `Long pays Short` / `多付空` as SELL XAUUSD, equal/blank as
  FLAT. No magnitude threshold, SGE price, return, volume, open interest,
  alternate contract or sign inversion was permitted.
- No report payload was downloaded. No XAUUSD target price, return, PF, code,
  compile, MT5 run, backtest or purchase was opened.
- Grok Build independently checked official SGE rules and pages. Lead retained
  only conclusions supported by the source mechanics and public contract.

## Field and mechanism reconciliation

- Official daily market-data surface:
  https://en.sge.com.cn/data/data_daily_international_new
- Official Au(T+D) product/rule material:
  https://en.sge.com.cn/upload/file/201906/10/fRETGQZuzTvg5wrx.pdf
- Official delivery rules:
  https://en.sge.com.cn/upload/file/201703/24/BKXufJhx04MMwkqQ.pdf
- Au(T+D) delivery tenders are submitted from 15:00 to 15:30 China Standard
  Time. The residual is handled by the neutral-warehouse/equalizer window from
  15:31 to 15:40.
- The published `Direction` is the direction of the deferred compensation fee,
  not a physical-delivery direction. When long receipt tender exceeds short
  delivery tender, shorts pay longs (`空付多`); when short delivery tender
  exceeds long receipt tender, longs pay shorts (`多付空`).
- The reported `Delivery Volume` is matched delivery. It is not the tender
  imbalance magnitude and cannot recover the excess receipt/delivery quantity.
- By the end of the official equalizer process, the imbalance has been covered
  and the same-day compensation obligation determined. The public field is a
  settled SGE cash-transfer state, not an unfilled physical claim.

## Source, clock, license and horizon

- Historical daily HTML pages exist, and the current live surface carries the
  same field labels. The public archive pages show a report date but do not
  establish one deterministic first-public HH:MM/time-zone clock for every
  2018-latest observation or a revision/vintage chain.
- SGE pages are copyright-reserved and route licensed market data through
  approved distributors. No public evidence reviewed here grants the required
  free internal/non-display historical-plus-live use contract for a local MT5
  research database.
- The proposed post-publication H4/D1 XAUUSD direction does not follow from the
  rules. `空付多` and `多付空` identify who pays the same-day deferred fee after
  the equalizer process; they do not document continuation into a global
  XAUUSD holding window. The effect may already be settled before any public
  report becomes usable.
- The object is distinct from the killed SGE SHAU fixing lineage, warehouse
  stock, GLD flow and monthly withdrawals. Novelty cannot repair the missing
  public clock, rights or post-publication causal horizon.

## Verdict

`NO_SGE_DEFERRED_IMBALANCE_CANDIDATE`

First fatal boundary: the official mechanism is settled/absorbed by the SGE
equalizer process before any documented public-use clock, so no mechanically
supported post-publication XAUUSD horizon exists. Missing HH:MM/PIT lineage and
internal-use permission independently fail closed.

Do not download daily reports, substitute SHAU/warehouse/withdrawals, invert
the sign or change contracts from this receipt. This is a scoped source and
mechanism rejection, not global infeasibility. No hypothesis or registry row is
created. Overall goal remains `ACTIVE / UNMET`; no market mechanism is active.
