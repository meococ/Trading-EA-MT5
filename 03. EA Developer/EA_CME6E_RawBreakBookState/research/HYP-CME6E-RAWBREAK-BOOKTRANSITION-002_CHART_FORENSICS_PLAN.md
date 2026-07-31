# HYP-CME6E-RAWBREAK-BOOKTRANSITION-002 — frozen chart-forensics plan

Date: `2026-07-27`  
Status: `FROZEN_POSTMORTEM_ONLY / TERMINAL HYPOTHESIS UNCHANGED`

## Purpose and boundary

Explain why the already terminal HYP-002 challenger failed by combining its
hash-bound outcome ledger with decision-time EURUSD M1/H1 price context, the
active raw-BREAK signal telemetry, direct lifecycle costs and the causal CME 6E
MBP-10 trace across the completed break bar.

This is descriptive postmortem evidence. It cannot change the terminal verdict,
select a rescue threshold, disable a weak bucket, build or edit MQL5, rerun
Model 0, promote or deploy. Any mechanism suggested after viewing outcomes
requires a fresh population, hypothesis ID and preregistration.

## Bound population and run identity

- Hypothesis: `HYP-CME6E-RAWBREAK-BOOKTRANSITION-002`.
- Terminal prereg SHA256:
  `E0E7040E29EB2A37D11532293C298167D7C429618B38D722C9D1599AF799A894`.
- Terminal result SHA256:
  `7736F456C2685AFCE15C6761C70AA5CFB75E4B29A009377B13B975BBD5E0265E`.
- Joined HYP-002 ledger SHA256:
  `7B19591BED7802F70A15A9C628EE46D236B7AA7BE610BC49E9758FB8EBBE3069`.
- Challenger: exact 258 quality-eligible rows with frozen transition score
  `>= -0.012342488801680875`.
- Parent control run: `20260725_210715`, active mode
  `CONTROL_FIRST_CLOSE_BREAK`, `InpUseHoldRetest=false`, Model 0.
- Run manifest SHA256:
  `6F88B403B869A010262953C5741E0F9856D2493ABDCC734FEA5E858BF3259D84`.
- Report SHA256:
  `FA8F40FBE0BF194486509548010B05D1BD7C64336601E97C5C5EFDC13F0D270F`.
- RunMeta SHA256:
  `8DB131F7BAC833F9A48B2C2B84D607D201594210E818DA21299D3BAFB8E28E78`.
- Lifecycle CSV SHA256:
  `515EFB5F5D4F86C54A2442206F9B508D1B2F7CDE5C0CF77A45F8250124A023C5`.
- Decision telemetry SHA256:
  `B5714589986D9B4E06B460C47AC38B7FB7C02FA30B1C36199157018314DA3C78`.
- Exact source snapshot SHA256:
  `9C03F4CB913E18B6CF660E48E7ADBD86034B1352A80167C32CC238BA7F7817B3`.
- Overrides SHA256:
  `0FCE3AE70CB8241197547550760C148C078BF3A1DCDCA85E3FCD30ACA0C5762E`.
- Non-repaint audit SHA256:
  `A0FEA4EF075569A0776745A1680BD7FF334FADF275742FB531C14C0A9781A30E`
  (`PASS`, zero findings).
- EURUSD M1 bar source SHA256:
  `2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A`.
- Clock model SHA256:
  `A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52`.
- HYP-002 feature extractor SHA256:
  `E1DA8963A05FFFCDF3745E02EB1051B5E54DADCCD998145B3B6DEE6A3DA1402B`.
- Frozen reusable forensic foundation SHA256:
  `5DE0157F883E1041B7887A3539B0E3AFD1DFF209864199DB11C1475CE63A5367`.

The generated TCA summary that reports zero trades is rejected: it failed to
discover the lifecycle filename. Direct lifecycle aggregation must reconcile
every selected position's entry and final-close rows to the joined ledger.

## Frozen sampling rule before chart viewing

Select exactly 12 unique challenger positions in this order:

1. `EXTREME_WIN`: two largest realized-R rows, tie by position ID.
2. `EXTREME_LOSS`: two smallest realized-R rows, tie by position ID.
3. `MEDIAN_WIN`: two remaining positive-net rows nearest the positive-net
   population median R, tie by position ID.
4. `MEDIAN_LOSS`: two remaining nonpositive-net rows nearest the nonpositive-net
   population median R, tie by position ID.
5. `MATCHED_BUY_WIN` and `MATCHED_SELL_WIN`: from remaining rows, select the
   positive-net BUY and SELL closest to the challenger median frozen transition
   score.
6. For each matched winner, choose one remaining same-direction nonpositive-net
   row minimizing population-standardized Euclidean distance over entry-known
   fields: frozen transition score, initial stop pips, volume and UTC
   minute-of-day. Tie by position ID. Label these `MATCHED_BUY_LOSS` and
   `MATCHED_SELL_LOSS`.

No chart may be viewed before `case_selection.csv`, population analysis and the
sample manifest are written and hashed.

## Decision-time context contract

Only data knowable at the actual next-bar entry may enter setup comparisons:

- active signal telemetry: pivot-break level, break-bar OHLC, ATR, spread,
  direction and accepted entry geometry;
- break-bar range/ATR, body fraction, close location, direction-aligned close
  beyond the pivot and entry gap from the break close;
- EURUSD M1 price path strictly before entry: prior 60-minute direction-aligned
  return/range and entry location in the prior 24-hour range;
- H1 context strictly before entry: direction-aligned 12-hour return;
- stop pips, target pips, UTC hour/session, weekday, direction and book score
  components.

Post-entry MFE/MAE, exit class and realized R are outcome-bearing and must be
kept in the outcome analysis layer only.

## Chart layers

For every selected case render:

- `decision`: EURUSD M1 ending strictly before entry, H1 as-of context,
  entry/SL/TP, break-bar-open and actual-entry markers, plus the full causal CME
  trace from break-bar open to actual decision. No exit or R label.
- `outcome`: price from 60 minutes pre-entry through exit plus 30 minutes,
  entry/SL/TP/exit and realized R; the CME trace remains causal and unchanged.

Every image must bind case ID, position ID, selection stratum, source hashes,
first/last bar and whether future price is visible.

## Required population analysis

- Trades, PF, net, win rate and expectancy in account currency and R.
- Average win/loss, realized payoff ratio and implied breakeven win rate.
- Direct lifecycle commission/swap/fee per trade; spread remains embedded and
  unseparated, so total cost provenance remains `UNVERIFIED_DIAGNOSTIC_ONLY`.
- Year, month, UTC session/hour, weekday, direction, exit, holding-time,
  stop-width and score-decile buckets where counts support them.
- Tail contribution, score-versus-R rank association and score-decile ordering.
- Winner/loser context differences with counts, medians and standardized effect
  sizes; matched BUY/SELL case contrasts.
- M1 OHLC approximate MFE/MAE and early excursion, explicitly labeled
  path-ambiguous and outcome-bearing.
- Active source call path and dormant HOLD/retest logic with exact lines.

## Output contract

Use `OBSERVED`, `STRONG INFERENCE`, `HYPOTHESIS` and `UNKNOWN`. The readout must
satisfy the `grok-ea-trade-forensics` analysis contract and finish with at most
three legal fresh hypotheses. No mined threshold or same-sample veto is legal.
