# MT5-only EURUSD frontier input after Owner >=98% data decision

Status: evidence input for bounded forensic review only. This is not a
preregistration, registry authorization, source-build authorization, or backtest
authorization.

## Owner decision and boundary

- On 2026-07-26 the Owner prospectively accepted MT5 Strategy Tester history
  quality `>=98%` for new candidates.
- This does not retroactively validate, promote, or reinterpret any prior run
  whose frozen gate required 99% or 100%.
- The relaxed completeness gate does not turn broker OHLC/quotes into CME/EBS
  order-book data and does not relax spread, slippage, commission, clock,
  non-repaint, OOS, WFO, Monte Carlo, or delivery requirements.
- Paid Databento acquisition remains parked. No paid request was made.

## Browser Deep Research result

- Surface: ChatGPT web, model `GPT-5.6 Sol`, reasoning tier `Pro`, tool
  `Nghiên cuu sau` (Deep Research); UI state was read back before submission.
- Prompt restricted the information set to closed bars, broker bid/ask ticks,
  tick timestamps/directions, spread, tick volume, and ex-ante calendar time.
- It explicitly de-duplicated HYP004/SCC, ASRS, ICT/SMC/FVG/OB/MSS/BOS/CHOCH,
  PO3/KLR/Unicorn/DRAT/opening-range sweep-reclaim, generic trend/session/
  indicator/breakout/mean-reversion combinations, and HYP018/HYP020-HYP026
  quote/tick-path lineages.
- After 12 minutes 7 seconds and 11 web sources, the exact final answer was:
  `NO LEGAL MT5-ONLY CANDIDATE`.
- Browser conversation URL:
  `https://chatgpt.com/c/6a65838b-3228-83ec-b9a7-942958128c44`.

## Independent primary-source cross-check

1. Hashi et al., NBER Working Paper 14160, found continuation in actual deal
   prices but explicitly did not find the same run tendency in quote prices.
   This blocks relabeling broker quote-sign runs as transaction-order-flow alpha.
   Source: https://www.nber.org/papers/w14160
2. Krohn, Mueller, and Whelan document an institutional FX-fixing mechanism:
   unconditional USD demand, dealer pre-fix hedging, USD appreciation before
   major fixes, and depreciation after. The source-defined European pre-fix leg
   shorts foreign currency versus USD from 08:00 Frankfurt local to the 14:15
   Frankfurt/ECB fix. The paper also reports that full transaction costs turn
   most windows negative and says average-trader exploitability is not obvious.
   Source: https://www.bankofcanada.ca/2021/10/staff-working-paper-2021-48/
   PDF: https://www.bankofcanada.ca/wp-content/uploads/2021/10/swp2021-48.pdf
3. Fenn et al. and Ito et al. show triangular arbitrage opportunities are tiny,
   short-lived, and dominated by speed and multi-leg execution risk; this is not
   a credible retail-MT5 fallback without synchronized firm quotes and atomic
   execution.
   Sources: https://arxiv.org/abs/0812.0913 and
   https://www.nber.org/papers/w26706

## Local observability feasibility (no outcome read)

- Data: `02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_M1_2015_now.parquet`
  SHA256 `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`.
- Columns read for feasibility only: `time_server`, `time_utc`,
  `utc_offset_h`, `tick_volume`, `spread`. No OHLC, future return, trade,
  MFE/MAE, PnL, PF, or expectancy was read.
- Exact paired event days at FivePercent server 09:00 and 15:15:
  2019=259, 2020=260, 2021=260, 2022=260; total=1,039.
- Both event rows had positive tick volume on 1,039/1,039 days.
- Clock parity: server 09:00 -> Frankfurt 08:00 and server 15:15 -> Frankfurt
  14:15 on 2,078/2,078 rows across 2019-2022, including DST; zero mismatches.
- Offline spread is not cost truth: zero spread share is 28.1039% at entry and
  29.5476% at exit. Any legal economic test must use direct MT5 real-tick
  bid/ask execution plus explicit commission/slippage stress.

## Sole adversarial candidate, not yet authorized

Candidate label: `FX_FIX_INVENTORY_WAVE_PRE_ECB`.

- Mechanism: dealer inventory/pre-hedging around a published institutional fix,
  not a price-pattern sweep, indicator filter, generic session rule, or inferred
  quote imbalance.
- Source-defined challenger: one daily short EURUSD from FivePercent server
  09:00 to 15:15, which is exactly Frankfurt 08:00 to 14:15.
- Prospective placebo control for novelty falsification: same short and duration
  shifted +60 minutes (server 10:00 to 16:15). This is a source-time anchoring
  test, not an optimized hour search.
- Strong adverse prior: the primary paper reports that full costs turn most
  windows negative. A retail MT5 test should therefore be cost-first and killed
  immediately if net expectancy/PF fail; no threshold, weekday, volatility,
  spread-regime, stop, target, or window rescue under the same identity.

The forensic reviewer must decide whether this is materially new and legal for
one fresh hypothesis/prereg/Model-0 matched pair, or whether the correct verdict
remains `NO_LEGAL_MT5_ONLY_CANDIDATE`. Fewer candidates are preferred; inventing
another price-only family is forbidden.
