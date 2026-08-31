# T2 P2 Formal Causal Grammar Specification

Status: `FROZEN_PRE_MARKET / P2_QC_PASS / NO_BUILD_OR_OUTCOME_AUTHORITY`  
Campaign: `CAMPAIGN-PTR-E01` · Generation: `T2`  
Frozen: `2026-07-30T22:52:05Z` after independent quant/prereg review  
P0 charter SHA256:
`D63F782926DEC4F12EA8EBB17B3511BC08C249A0AE4ECD9C1F25F5C611386E9E`  
P1 source matrix SHA256:
`9F82D03AA90DDAE694CA6716631354543BA21CC16D78CBD2B5E5A5DE6C5956BD`.

This file turns the frozen P0 concepts into one implementable M5 object before
market outcomes. It does not grant a hypothesis ID, MQL5 source, compile, MT5,
economic, validation, holdout, paper or live authority. After independent QC
freezes this file, any market-logic change requires a new pre-outcome version;
after any outcome exposure it is a new generation/search cell, not a repair.

## 1. Canonical bars and indicators

Input bars are completed M5 Bid OHLC records
`b_i = (open_i, high_i, low_i, close_i, utc_open_i)` in strictly increasing UTC
order. A decision after bar `t` may use only bars `<=t`.

For a contiguous segment:

`TR_i = max(high_i-low_i, abs(high_i-close_{i-1}), abs(low_i-close_{i-1}))`.

Wilder ATR14 is seeded by the arithmetic mean of the first 14 TR values and
then updated as `ATR_i = (13*ATR_{i-1}+TR_i)/14`.

EMA25 is seeded by the arithmetic mean of the first 25 closes and updated as
`EMA_i = (2/26)*close_i + (24/26)*EMA_{i-1}`.

`CLV_i = (2*close_i-high_i-low_i)/(high_i-low_i)` when range is positive,
otherwise zero. Direction `d` is `+1` for long and `-1` for short. All equality
comparisons use half a symbol tick unless a larger ATR tolerance is stated.

Every reset requires 50 new contiguous completed bars before a setup is legal;
earlier candidates emit `SKIP_WARMUP`. T2-001 has horizontal barriers only.
Angular/regression barriers would create an unbudgeted family and are forbidden.

## 2. Locked barriers and A0

At completed bar `l`, set `A_l=ATR_l` and `eps_l=0.10*A_l`.

For an upper candidate, initialize touch set `J={l}` and scan bars
`i=l-2,l-3,...,l-17`. Add `i` when `abs(high_i-high_l)<=eps_l` and its index is
at least two bars from every already selected touch. For a lower candidate use
lows symmetrically. The source 18-bar window must be contiguous and valid.

A barrier locks when at least three touches exist and the lock-bar close has
not already made a valid break: upper requires `close_l<=B+0.05*A_l`; lower
requires `close_l>=B-0.05*A_l`. `B` is the median selected touch price.

Before locking, compare the candidate with every active same-side barrier.
Reject and log `SKIP_DUPLICATE_BARRIER` when either
`abs(B_new-B_active)<=max(0.10*A_l,0.10*ATR_active_lock)` or the two barriers
share at least two touch timestamps. The active barrier is not refreshed,
recentered, extended or given new touches.

`barrier_id = SHA256(symbol|side|lock_utc|sorted_touch_utc|B_in_ticks)`.
Only one new barrier per side may lock on a bar. It is immutable, active on
completed bars `l+1..l+12`, expires before processing `l+13`, and is never
merged or recentered. Consumed/expired barriers retain an immutable tombstone
`(id,side,price,lock,consume_or_expire)` for 48 bars solely for PBP exclusion
and audit; tombstones cannot trigger, supply room or be relocked in place.

A close-break at bar `t` requires both:

- `d*(close_{t-1}-B)<=0`;
- `d*(close_t-B)>=0.05*ATR_t`.

If several barriers break in one direction, long chooses the smallest
`B>close_{t-1}` and short the largest `B<close_{t-1}`; ties choose older lock
time and then lexical `barrier_id`. All barriers crossed by that close are
consumed; only the nearest creates a candidate. This blocks repeated-break
densification.

`A0_LOCKED_BARRIER_BREAK` is exactly locked barrier plus close-break. It has no
pressure, buildup, room or EMA gate. Risk, cost, probability, clock and daily
consumption remain identical to the challenger arms.

## 3. Pressure

For a six-bar window ending at `u`:

- `Disp_d(u)=d*(close_u-close_{u-5})/ATR_u`;
- `ER_d(u)=d*(close_u-close_{u-5}) / sum_{k=u-4..u} abs(close_k-close_{k-1})`;
- `MeanCLV_d(u)=d*mean(CLV_{u-5..u})`;
- `EMASlope_d(u)=d*(EMA_u-EMA_{u-5})/ATR_u`.

A zero ER denominator makes pressure false. `PRESSURE_d(u)` is true only when
`Disp>=0.60`, `ER>=0.55`, `MeanCLV>=0.20`, and `EMASlope>=0.10`.
`pressure_duration` counts consecutive true completed bars, capped at 12.
A1-A3 require duration at least two. All four raw components are logged;
`pressure` is an OHLC path proxy and never actual order flow.

## 4. Buildup and A1

For a trigger candidate at `t`, try lengths `n=8,7,...,3` and take the largest
passing value. Buildup bars are `t-n..t-1`. The barrier must have locked no later
than `t-n-1`, and `PRESSURE_d(t-n-1)` with duration at least two must pass.
Use frozen barrier ATR `A_B=ATR_lock`.

Every buildup close stays inside and near the barrier:

`-0.05*A_B <= d*(B-close_i) <= 0.35*A_B`.

At least two buildup highs for long, or lows for short, must be within
`0.10*A_B` of `B`.

`Contraction = median(TR_{t-n..t-1}) /
median(TR_{t-n-12..t-n-1}) <= 0.75`.

For adjacent bars define
`ov_i=max(0,min(H_i,H_{i-1})-max(L_i,L_{i-1})) /
max(min(H_i-L_i,H_{i-1}-L_{i-1}),tick)`.
`OverlapMean=mean(clip(ov_i,0,1))>=0.50`.

Set support sequence `S_i=low_i` for long and `S_i=high_i` for short.
`Progression = count[d*(S_i-S_{i-1})>=-0.05*A_B]/(n-1) >= 2/3`.

Let `x_i=d*(B-S_i)`. Then
`CounterRatio=mean(x_{t-2..t-1}) /
max(mean(x_{t-n..t-n+1}),tick) <= 0.80`.

`A1_PATTERN_BREAK` requires all buildup predicates and the completed
close-break. Its contraction is legal only after an independently locked
three-touch barrier and an earlier ordered pressure state; it is not an ECRS
ATR-compression/range-break reconstruction.

## 5. A2 pattern-break combi

A2 inherits a complete A1 state. Pressure bar `p=t-2`, inside bar `q=t-1`, and
trigger bar `t` are immediate; no remote or approximate combi is allowed.

Pressure bar requires:

- `d*(close_p-open_p)>=0.35*ATR_p`;
- `d*CLV_p>=0.50`.

Inside bar requires:

- `high_q<=high_p+0.5*tick`;
- `low_q>=low_p-0.5*tick`;
- `(high_q-low_q)/(high_p-low_p)<=0.75`, with zero mother range invalid.

Both closes remain pre-break: `d*(close_p-B)<=0` and `d*(close_q-B)<=0`.
Bar `t` must then pass the normal completed close-break.

## 6. A3 pullback reversal and hard PBP exclusion

A3 is a correction of a pressure leg; it is never a post-break retest.
For trigger `t`, scan correction length `m=2,3,...,6` and choose the smallest
passing `m`. The leg ends at `k=t-m-1` and its window is exactly `k-7..k`.
Require `PRESSURE_d(k)` with duration at least two and
`LegAmp=d*(close_k-close_{k-7})>=1.20*ATR_k`.

Correction bars are `k+1..t-1`. Correction extreme `X_c` is their minimum low
for long and maximum high for short.

- `Depth=d*(close_k-X_c)/LegAmp` must be in `[0.40,0.60]`;
- `CorrER=-d*(close_{t-1}-close_k) /
  sum_{i=k+1..t-1} abs(close_i-close_{i-1})` must be in `[0,0.55]`;
- `d*(close_{t-1}-close_{t-2})>=-0.10*ATR_k`;
- `d*CLV_{t-1}>=-0.10`.

Contact passes by one route only:

- `STRUCTURE`: correction extreme is within `0.10*ATR_k` of a barrier locked
  before `k-7` and that barrier was still active at the exact correction-contact
  bar; or
- `EMA25`: at least one correction bar spans `EMA_i +/- 0.10*ATR_i`.

If both pass, record `STRUCTURE`; confluence gives no score bonus.

Reversal release requires long `close_t>=high_{t-1}+0.05*ATR_t`, or short
`close_t<=low_{t-1}-0.05*ATR_t`, plus `d*(close_t-open_t)>0` and
`d*CLV_t>=0.50`.

A3 emits `SKIP_PBP_EXCLUDED` if a same-direction locked-barrier close-break
occurred in `k-7..t-1` or the correction contacts a previously broken barrier.
Thus it cannot become SCC BREAK->HOLD->RETEST under another name.

## 7. Price reference, cost, invalidation, risk and room

The model/label reference `E` is the next M5 Bid open for both directions, not
the broker trade fill. Future label closes also use completed Bid closes for
both directions. This keeps spread, commission and slippage outside the path
label and inside one explicit cost term; actual MT5 deal fills/PnL remain the
economic truth and must reconcile separately.

At entry, all-in price cost is
`c=max(observed_spread, train_P90_nonzero_spread)+roundtrip_commission_price+
2*tick_size`. Missing, zero or nonfinite required fields are invalid.
`roundtrip_commission_price` converts cash commission through the decision-time
tick contract as `commission_cash_roundtrip/tick_value*tick_size`; nonpositive
tick size/value is invalid.

For A0-A2, long invalidation is the minimum low and short invalidation the
maximum high over `lock_time..trigger_time`, plus a `0.10*ATR_t` buffer beyond
that extreme. For A3 use the correction extreme with the same buffer.

Let path risk `r=abs(E-I)`, cost ratio `rho=c/r`, and cash-at-risk proxy
`R_cash=r+c`. Recompute once at the actual next-open reference. Accept only
`0.60*ATR_t<=R_cash<=1.40*ATR_t` and `rho<=0.20`. A nonpositive `r` is invalid.
A gap failure emits
`SKIP_ENTRY_GAP_RECHECK`, consumes the signal/barrier and consumes that UTC
date; there is no second-best replacement.

Nearest opposing room uses the nearest active pre-existing barrier beyond `E`
in trade direction; exclude the trigger barrier. If none exists, room is
infinite. `Room_r=d*(Z-E)/r`. A1/A2 require `Room_r>=2.0`. A0 has no room
gate. A3 logs room but does not gate it.

Round-grid context is telemetry/model context only:
`g_s=roundToTick(10^round(log10(10*medianTrainATR_s)))`. It never vetoes an
entry. A zero/nonfinite grid sets `grid_feature_missing=1`; no symbol-specific
level may be guessed. Otherwise `round_grid_room_r` is the distance from `E` to
the nearest multiple of `g_s` strictly ahead in direction `d`, divided by `r`:
long uses `G=g_s*(floor(E/g_s)+1)`, short uses
`G=g_s*(ceil(E/g_s)-1)`, and `round_grid_room_r=d*(G-E)/r`. If
`grid_feature_missing=1`, raw `round_grid_room_r` is fixed zero and the missing
flag is one; infinity is never emitted.

## 8. Label and close-only execution

For completed post-entry bars `j=1..12`, define frictionless Bid path excursion
`X_j=d*(BidClose_j-E)`.

1. If `X_j<=-r`, label `Y=0`, emit `CLOSE_STOP`, execute next open.
2. Else if `X_j>=+2r`, label `Y=1`, emit `CLOSE_TARGET`, execute next open.
3. Else continue; after bar 12 label `Y=0`, emit `TIME_EXIT`, execute next open.

Friday/session boundary exits no later than 23:55 UTC. Gaps and actual fills
are retained without clipping in MT5 economics. There is no intrabar SL/TP,
pending entry, trailing, break-even move, partial or discretionary exit.

With gross path payoff `+2r/-r` and one all-in cost `c`, net payoff is
`2r-c` or `-r-c`. Therefore `p_BE=(1+rho)/3` and
`tau=p_BE+0.05`. Trade only when calibrated probability strictly exceeds
`tau`. A deterministic fixture must reconcile price-space expectancy with cash
PnL and prove that spread/commission/slippage is counted once.

## 9. Fixed model and fitting

Raw common features are:

1. `clip((touch_count-3)/3,0,1)`;
2. barrier age `/12`;
3. `clip(d*(close_t-B)/ATR_t,0,1)`;
4. mean of the four pressure components divided by their frozen thresholds and
   clipped `[0,2]`;
5. pressure duration `/12`;
6. buildup duration `/8`;
7. `1-Contraction`;
8. `OverlapMean`;
9. `Progression`;
10. `1-CounterRatio`;
11. `clip(Room_r,0,4)/4`;
12. `clip(round_grid_room_r,0,4)/4`;
13. `rho`;
14. `R_cash/ATR_t`;
15. combi flag;
16. combi inside-range ratio;
17. PR leg amplitude `/ATR`;
18. PR depth;
19. PR correction duration `/6`;
20. `1-CorrER`;
21. structure-anchor flag;
22. EMA-anchor flag;
23. `grid_feature_missing`.

A4 appends one-hot `PB,PBC,PR`. Absent branch fields are zero and the one-hot
prevents zero from masquerading as an observed measurement. Arm masks:

- A0: 1,2,3,13,14;
- A1: 1..14 and 23;
- A2: 1..16 and 23;
- A3: 4,5,11..14 and 17..23;
- A4: all 23 plus the three setup flags.

Continuous features use that symbol's train-only
`z=(x-median)/(1.4826*MAD)`, clipped `[-5,5]`. If MAD is zero, normalized value
and coefficient are fixed zero and `CONSTANT_FEATURE` is logged; dimensions
cannot silently disappear.

Within a symbol, every UTC calendar year in the train split receives equal
total weight, and observations within that year share the weight equally.
Each arm-symbol logistic model minimizes this weighted log loss plus
`0.5*sum(beta_j^2)` for non-intercept coefficients. Intercept is unpenalized;
initial beta is zero; deterministic L-BFGS runs at most 1000 iterations and
requires gradient infinity norm `<=1e-10`. A single-class train set or optimizer
failure is fatal. No hyperparameter optimizer exists.

Calibration clips `p_raw` to `[1e-12,1-1e-12]` and fits
`p_cal=sigmoid(a*logit(p_raw)+b)` on that symbol/arm's
calibration split only, initialized `a=1,b=0` under the same deterministic
solver tolerance. Single-class calibration or failure is fatal; there is no
fallback calibrator.

## 10. A4 union and conflict rules

At each completed bar, generate A1, A2 and A3 independently. Opposite directions
produce `SKIP_DIRECTION_CONFLICT`. Same direction uses priority `A2>A1>A3`.
A4 evaluates only the selected branch with its single arm-symbol model.

For each candidate define margin `m=p_cal-tau`, because `tau` varies with cost/r.
Each UTC date starts with sentinel prior margin `-1`. The first candidate whose
previous margin is `<=0` and current margin is `>0` wins. It consumes the UTC
date even if actual-entry gap, min-lot or execution recheck rejects it.
Component arms apply the same margin crossing and daily consumption
independently. At most one entry per UTC date per arm.

## 11. Gap, schedule and reset rules

A valid adjacent M5 pair is exactly 300 seconds unless an immutable, hash-bound
broker schedule marks the interval closed.

- Duplicate or nonmonotonic UTC time makes the cell `INVALID_DATA`.
- Unexpected missing bar while flat expires all state and starts a 50-bar
  warmup.
- Scheduled closure resets state/warmup and is not a missing-data error.
- A setup crossing any reset emits `SKIP_GAP_CONTEXT`.
- Unexpected scheduled-open gap while in position exits next available open as
  `DATA_GAP_EXIT` and makes the cell engineering-invalid, not a win/loss.
- Entry is forbidden when its known 12-bar horizon crosses scheduled close or
  Friday flat.
- No state carries across weekend, maintenance closure or symbol remapping.

BTC weekend bars are coverage-only and cannot update economic state. Friday
reset and Monday warmup therefore match the five-day FX contract.

## 12. De-dup and diagnostics

T2 never uses ECRS ER10 shift `0.28->0.38`, ATR14/20-ATR ratio `<=0.70`, a
rolling 12-bar high/low as barrier, `1.7x` tick-volume surge, EMA20 or a
London/New-York filter. D7 still replays that exact ECRS trigger outcome-blind.
Jaccard overlap above 0.50 plus no source-attributable residual distinction is
fatal before build.

D8 compares PBP-like identities to the prior SCC surface without future
excursion or PnL. PBP remains non-selectable and absent from A4. D0-D6 retain
their charter roles and cannot contribute economic selection or trial credit.

## 13. Deterministic fixture and capability gates

Reference implementation must include at least:

- exact long/short mirror fixtures for A0, A1, A2 and A3;
- insufficient touches, mutable-barrier attempt and crossed-barrier consumption;
- no-pressure, no-contraction, no-overlap, no-progression and counter-excursion
  rejects;
- exact inside bar plus each containment/ratio failure;
- PR depth below/inside/above range, structure-vs-EMA priority and PBP exclusion;
- opposing-direction A4 conflict and same-direction priority;
- cost/r, cash-risk envelope, room, p_BE and count-cost-once fixtures;
- daily consumption, next-open gap rejection, Friday/weekend reset, unexpected
  gap and 50-bar warmup;
- prefix invariance: appending any future suffix cannot alter any prior barrier,
  state, feature, signal or reject log;
- deterministic replay and Python-reference to eventual MQL5 parity vectors.

Using seed `20260732`, at least 200 bounded perturbations per positive arm and
direction must recover the intended terminal transition with sensitivity
`>=0.95`. Event-order shuffled and time-reversed negative controls must trigger
at rate `<=0.05`. Invalid fixtures are counted and classified, never dropped.

P2 fails pre-build if the lawful source matrix cannot support the semantic
mapping, prefix invariance fails, the price/cash cost fixture cannot reconcile,
schedule provenance is not hash-bound, or any constant/branch remains ambiguous.
These are capability results, not market-edge conclusions.
