# GC Signed-Flow Mechanism Screen

Date: 2026-08-11

Verdict: `REJECT_RAW_PERSISTENCE_CONTINUATION / KEEP_ORDER_FLOW_INNOVATION_AS_PRE_SOURCE_RESEARCH_ONLY`

This is a mechanism-selection note, not a hypothesis, preregistration, data
purchase, outcome probe, EA build or MT5 authority. The workspace goal remains
active and unmet: zero economic-valid and zero promotion-ready EAs.

## Causal screen

The supported fact is narrower than the proposed strategy. Empirical and
theoretical work links persistent market-order signs to institutional order
splitting. That supports persistence in *future order signs*, not an automatic
continuation edge in price. Market-impact research also explains that liquidity
can adapt to predictable flow so returns remain difficult to forecast. A rule
equating a long same-side run with a profitable next-bar continuation therefore
does not yet have a sufficient causal contract.

The only retained research object is the **innovation** in exchange order flow:
the portion of signed flow that is unexpected relative to a causal model of the
already-observed sign history, measured together with contemporaneous top-of-
book response. No model, lookback, threshold, session, entry or exit is selected
by this note. Those must be fixed from primary-source reasoning before any paid
source pilot; they cannot be chosen to manufacture 2--5 events/week.

Primary references:

- Lillo, Mike and Farmer, *A theory for long-memory in supply and demand*:
  <https://arxiv.org/abs/cond-mat/0412708>
- Toth, Palit, Lillo and Farmer, *Why is order flow so persistent?*:
  <https://arxiv.org/abs/1108.1632>
- Gerig, *A Theory for Market Impact: How Order Flow Affects Stock Price*:
  <https://arxiv.org/abs/0804.3818>

## Source semantics

Candidate source remains `GLBX.MDP3 / GC.v.0 / tbbo`. Databento documents that
`side=B` means buyer aggressor, `side=A` means seller aggressor and `side=N`
means no side specified. This is venue/feed semantics, not Lee--Ready or quote-
tick inference. `N` records may occur for auctions, non-displayed or implied
orders and other cases. A future source-integrity pilot must measure `A/B/N`
coverage by date, session and contract and fail closed if signed coverage is not
predeclared and adequate.

Official field definitions:

- <https://databento.com/docs/schemas-and-data-formats/tbbo>
- <https://databento.com/docs/standards-and-conventions/common-fields-enums-types>

Clock/identity requirements, still unfrozen: matching-engine `ts_event` is the
causal source axis; the broker XAU decision bar must start strictly after the
completed source window; contract mapping and front-roll changes must remain
visible; no roll transition may silently combine different instruments; normal
Globex closures are not missing ticks.

## De-dup boundary

- Not TFCVD: broker quote-direction/generated-tick polarity is forbidden; only
  exchange trades with documented aggressor side may enter.
- Not V5 impact-per-pressure: no price/quote-activity proxy or renamed mid-price
  sign ratio.
- Not CME 6E book-state/book-transition: no five-level displayed-depth score and
  no unchanged raw-break entry surface.
- Not EventCLOB persistence: no scheduled-event PRE/LATE segment population and
  no reuse or relaxation of its one-second gap/staleness gates.
- Not raw CVD: cumulative signed volume, a same-side run or an imbalance
  percentile by itself is explicitly insufficient.

## Decision and shortest next work

1. Do not purchase the Q1-2019 pilot and do not seek a USD ceiling yet.
2. Formalize exactly one causal order-flow-innovation estimator and matched
   null from primary sources, with no outcomes and no cadence-targeted threshold.
3. Red-team that formula against the failure radii above. Only a material PASS
   may reopen the already quoted Q1 source-integrity pilot. A pilot PASS would
   authorize only schema/clock/coverage validation; multi-year outcome-blind
   cadence must pass before any EA or Model-0 baseline.

## Frozen estimator draft for independent red-team

This section freezes one estimator class for review; it does not authorize
source access. No DAR/HDIM/AR tournament is permitted.

1. **Event sequence.** Use raw-contract `tbbo` trade records in increasing
   `(ts_event, sequence)` order. `epsilon_i=+1` for `side=B`, `-1` for `side=A`;
   `side=N` is excluded and counted. Corrections, duplicates and out-of-order
   records fail closed. Keep `instrument_id`; never splice across a front-roll
   change. Official status records, not a hand-picked hour filter, delimit
   trading sessions and reset the previous-sign state.
2. **MRR(1) expectation.** For each raw instrument, after 20 completed trading
   sessions of feature-only burn-in, estimate one lag coefficient from the
   immediately preceding 20 completed sessions, using only within-session signed
   transitions (never the boundary between two sessions):
   `rho_d = mean(epsilon_j * epsilon_(j-1))`. Freeze `rho_d` for all trades in
   session `d`. The causal expected sign is
   `epsilon_hat_i = clip(rho_d * epsilon_(i-1), -1, +1)` and the innovation is
   `u_i = epsilon_i - epsilon_hat_i`. No same-session coefficient update.
3. **Five-minute source state.** Aggregate only completed, non-overlapping UTC
   five-minute bins inside an open status interval. For a bin with `n>0` signed
   trades, `U_t = sum(u_i)/sqrt(n)` and raw-flow control
   `X_t = sum(epsilon_i)/sqrt(n)`. Boundary midpoint response is
   `R_t=(mid_last-mid_first)/GC_tick`, using the first pre-trade BBO and final
   post-trade BBO contained in the same completed bin; stale/missing/crossed
   quotes fail that bin.
4. **Tail event, fixed before source.** After 20 completed prior sessions, set
   `sigma_t` to the population standard deviation (`ddof=0`) of valid `U` bins
   from the immediately preceding 20 completed sessions of the same raw
   instrument. Require at least 100 valid prior bins and `sigma_t>0`. A raw
   candidate is `abs(U_t)>=3*sigma_t`, `sign(R_t)=sign(U_t)` and
   `abs(R_t)>=1` tick. The threshold is the conventional three-sigma tail, not
   selected to achieve 2--5/week. Direction is `sign(U_t)`. Simultaneous or
   nonfinite states fail closed.
5. **Matched null.** Use exactly the challenger's candidate timestamps,
   source bins and eligible population. Replace only direction with
   `sign(X_t)`; zero raw-flow signs are explicit null no-trades. Before any
   outcome access, require the null population/count difference and direction
   balance to be reported. Later lift must be judged on identical clocks; a
   separate raw-flow percentile or threshold is forbidden.
6. **Broker decision mapping.** A source event is executable only on the first
   native broker XAUUSD M5 open strictly after the source bin end, with a frozen
   UTC/server mapping and exact-next coverage at least 97%. No broker price is
   used to create the source event. Entry, stop, target and holding period remain
   deliberately undefined and block EA/baseline work.

Source-integrity gates remain prior to candidate-density authority: exact file
identity/replay; at least 99% of trade count and contract volume carrying `A/B`
side; complete definition/status coverage; zero cross-contract splice; exact
clock mapping; and deterministic `rho/U/X/R` reconstruction. Q1 may test these
source gates only. It cannot validate the three-sigma cadence, year balance,
economics or market edge.

## Independent review of estimator draft v1

Reviewed artifact SHA256:
`36DD2F9BD88E58B2143CECED3A1764860C950AC93378E4E0E7710B99E5F86508`.

Verdict: `FAIL_PRE_SOURCE_RESEARCH`. No source or outcome was opened. The exact
failure radius is: count signs were described ambiguously as signed volume; the
zero-intercept `rho * previous_sign` form did not cover asymmetric transition
probabilities or enforce an estimation sample floor; and conditioning event
selection on `sign(R)=sign(U)` advantaged the innovation direction over the
raw-flow matched null. Draft v1 is not eligible for data acquisition.

## Estimator draft v2 for a new independent review

This revision changes only the three rejected definitions. It remains a
pre-source research object and creates no hypothesis or acquisition authority.

1. **Count-sign object.** This is explicitly an aggressor **trade-count sign**
   innovation, not signed volume. Trade size is retained only for source-quality
   coverage reporting and does not enter `epsilon`, `U`, `X`, the threshold or
   direction. The raw sequence, roll, session and quote rules from draft v1 are
   unchanged.
2. **Full one-lag Markov expectation.** For each raw instrument and each session
   `d`, count all within-session sign transitions in completed sessions strictly
   before `d`: `N_(s,+)` and `N_(s,-)` for previous sign `s in {-1,+1}`. Use an
   expanding window; never cross a session boundary and never update inside
   session `d`. Require `N_(s,+)+N_(s,-) >= 10000` separately for both previous
   states. Then
   `m_s=(N_(s,+)-N_(s,-))/(N_(s,+)+N_(s,-))`,
   `epsilon_hat_i=m_(epsilon_(i-1))`, and
   `u_i=epsilon_i-epsilon_hat_i`. Until both state floors pass, the feature is
   unavailable. This transition-matrix form permits asymmetric unconditional
   order signs without a forced zero intercept.
3. **Causal scale.** Keep the draft-v1 five-minute `U`, `X` and `R` definitions.
   At the start of each session, compute `sigma_d` with `ddof=0` from every valid
   feature-available `U` bin in completed prior sessions of the same instrument;
   freeze it for the full session. Require at least 1000 such bins and
   `sigma_d>0`.
4. **Direction-neutral event selection.** An eligible timestamp requires
   `abs(U_t)>=3*sigma_d`, `abs(R_t)>=1` GC tick, and `X_t!=0`; it does **not**
   condition on the sign of `R_t`. Challenger direction is `sign(U_t)`.
5. **Paired matched null.** On every identical eligible timestamp, the null
   direction is `sign(X_t)`. Both arms therefore have the same bins, quote
   response-magnitude condition, clocks and nonzero population. No raw-flow
   threshold, percentile or separately selected timestamp is allowed. Report
   how often the directions agree; only the differing-direction subset can
   identify incremental directional information, while all cadence gates use
   the common eligible population.

The five-minute clock, 10,000 transitions/state, 1,000 historical bins,
three-sigma tail and one-tick response are transparent ex-ante operational
choices, not claimed as literature constants. They may be accepted or rejected
only by formula review before data; they may not be tuned from cadence or
outcomes. Draft v2 must receive an independent `PASS_PRE_SOURCE_RESEARCH` before
any price estimate is converted into a purchase request.

## Independent review of estimator draft v2

Reviewed artifact SHA256:
`D7A5FE27FDEEA45FBE5BBAE427E83D65656170A972307719DC41FAA5A740193E`.

Verdict: `PASS_PRE_SOURCE_RESEARCH`. The reviewer found the v1 blockers closed:
the object is count-sign, the asymmetric one-lag estimator is causal and
session-bounded with explicit floors, and event selection permits a paired null
on identical timestamps without directional price conditioning. Novelty is
material relative to TFCVD/V5, the prior CME 6E book-state/raw-break objects and
EventCLOB. The operational choices remain falsifiable assumptions rather than
literature constants.

This verdict authorizes neither purchase nor hypothesis, EA, PF, cadence,
economics or promotion work. The next capital decision is a proposed Owner
ceiling of USD 10.00 for a Q1-2019 `GLBX.MDP3 / GC.v.0 / tbbo` source-integrity
pilot; the existing non-billable estimate is USD 8.955564200878. Any future
request must live-requote below the explicit ceiling, use deterministic fixtures
for session reset/asymmetric transitions/paired-null disagreement, and stop
after schema, side, status, roll, clock and replay gates. It may not inspect
multi-year cadence or outcomes.

## Offline deterministic fixture receipt

No source or outcome was opened. The pure reference implementation is
`04. Memory/research/gc_signed_flow_estimator_reference.py`, SHA256
`B6C2678E1E85D2D5850A580D5570B2C5B7ABF5054B6B8A72B46C220CE5F37FED`.
Its focused test is
`04. Memory/research/tests/test_gc_signed_flow_estimator_reference.py`, SHA256
`30A7CAA3B10D680B00F1AC9F70910A6A8587C446308F1698017B3E0293EA2343`.
The command
`python -B -m pytest -q 04. Memory/research/tests/test_gc_signed_flow_estimator_reference.py`
passed `12/12`.

The fixtures make two boundary rules explicit: the first trade after every
session reset has no prior sign, so any five-minute bin containing that
unavailable innovation fails closed; and transition counts are keyed by raw
instrument so singleton records on opposite sides of a front roll cannot create
a synthetic transition. Other fixtures cover asymmetric conditional means,
10,000-transition and 1,000-bin floors, exact `U/X/sigma`, response-sign-neutral
selection and paired challenger/null direction disagreement.

The first static fixture review found that accepting anonymous aggregate counts
and `U` history could not prove the session/instrument boundary. The corrected
reference therefore freezes parameters through an identity-bearing causal
session API and rejects current-session records, duplicate/out-of-order session
ordinals and cross-instrument expectation or sigma inputs. The three added
mutation fixtures cover those exact false-pass paths; no estimator threshold or
event rule changed.
