# HYP-G10-XMOM-W1-002 train forensic sampling plan

Status: frozen before reading individual leg or week outcomes.

Purpose: explain the terminal train kill without changing, rescuing, or
re-authorizing the tested strategy. This is diagnostic-only and cannot open the
sealed 2022-2024 holdout.

Bound evidence:

- `train_eval_legs.json` SHA256
  `CF105E71DB2500703D025E0FF60C9367ACB686006A606336CC5CFCFA9937FAEF`
- `train_eval_weeks.json` SHA256
  `6E282704964D6BD323C63B9EAE7CFCC63D0AC4BD4AAECCBCCF4DE5BD07581771`
- `train_eval_terminal.json` SHA256
  `F115DFB58BE43990FC5CF6C726947093A8F4CE58B86C30CCE529325ACD213FB0`
- train parquet SHA256
  `2FB4615129D8B8782F6A71AF8009B47C9210B2040FC57FD2082D0978755B4BB2`

Predeclared case sampling rule, challenger arm only:

1. Largest positive net-x1 leg.
2. Largest negative net-x1 leg.
3. Median positive net-x1 leg after sorting by `(net_x1, week, symbol, side)`.
4. Median negative net-x1 leg under the same ordering.
5. One same-symbol, same-side winner/loser pair with minimum calendar distance;
   ties break by symbol, side, winner week, loser week.
6. Best and worst challenger portfolio weeks by net-x1; ties break by week.

Population analysis is fixed to challenger versus matched reverse-direction
control, full 2018-2021 train population, and the already frozen x1 cost proxy.
Report year, month, direction, symbol/currency, payoff, breakeven win rate, cost
drag, tail concentration, and available formation-return buckets. Session,
intraday hour, stop width, volatility, news, account-currency PnL, and true R
are unavailable in the W1 research proxy and must be marked unknown rather than
reconstructed.

Charts may use only the hash-bound W1 OHLC parquet. Entry is the current W1 open
and exit is the current W1 close. A single W1 OHLC bar cannot prove intrabar
path, stop/target anatomy, spread path, or execution quality; those fields must
remain blocked/unknown.

No bucket observed here may be disabled, filtered, or converted into a threshold
for HYP-G10-XMOM-W1-002. Legal next ideas, if any, must be fresh mechanism-level
hypotheses with new IDs and outcome-blind preregistration.
