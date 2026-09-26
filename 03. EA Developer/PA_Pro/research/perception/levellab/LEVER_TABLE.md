# LEVER TABLE — defended-origin level route (LEVEL-LAB, for the Owner pack)

All arms measured at one engine hash `a62edc19`, ruler `50e11fd5`,
198 TUNE panels, paired in-process (ab_engine.py).  Flag-off is
bit-identical to STABLE `584c7743` (identity_check.py: 198/198
canonical-equal).  Flag stays OFF by keep-rule; these are levers.

## The flag family

| arm | params | idea |
|---|---|---|
| flag_off | (defaults) | production baseline |
| flag_on | `defended_origin=1` | defended-origin route, 2 LC + 1 MINI live |
| v2 | +`def_mini_off=1` | defended LC only — MINIs were 43% of births, 0 hits |
| v2b | +`def_all_lc=1` | every defended birth typed LC (match is type-agnostic) |

## Metrics (ab_engine lens; scoreboard rows appended at same hash)

| metric | off | flag_on | v2 | v2b |
|---|---|---|---|---|
| LC born recall | .146 | **.229** | .167 | .146 |
| LC trusted born | .150 | .250 | .175 | .175 |
| LC snapshot@τ | .021 | .106 | .085 | .085 |
| LC recall@2 | .021 | **.106** | .085 | .085 |
| MINI born recall | .065 | .065 | .065 | .097 |
| births/panel (all, med) | 6.0 | 6.5 | 6.0 | 7.0 |
| clutter ratio (med) | 2.50 | 2.50 | 2.50 | 2.50 |
| live levels @τ (med) | 0.0 | 0.0 | 0.0 | 0.0 |
| flicker (med ch/h) | 0.33 | 0.43 | 0.33 | 0.33 |

## Keep-rule (R18) per-family matched-object deltas

| family | flag_on | v2 | v2b |
|---|---|---|---|
| LEVEL_CARRIED | +4 | +1 | 0 |
| MINI_LEVEL | 0 | 0 | +1 |
| BOX | **−2 FAIL** | +1 | −1 |
| PATTERN_LINE | 0 | **−2 FAIL** | −1 |
| BRACKET | 0 | +3 | 0 |
| RANGE_OPEN | 0 | 0 | −1 |

- **flag_on:** max recall; fails on BOX −2.
- **v2:** BOX healed, flicker gone; fails on PATTERN_LINE −2; recall smaller.
- **v2b:** the only variant with every family within −1, but **NOT
  KEPT (R26 §26.1)**: aggregate cumulative recall is net −2 (LC flat)
  and live clutter at τ rises 10 → 11.  The snapshot/.@k gains are
  real but reported under recall@k, not as a keep.

## CIs (paired day-bootstrap, vs flag_off)

| diff | flag_on | v2 | v2b |
|---|---|---|---|
| LC born | **+.071 [.010,.152]** | +.025 [−.081,.136] w | +.004 [−.096,.100] w |
| LC@2 | +.068 [0.000,.156] w | +.073 [0.000,.167] w | +.061 [−.006,.150] w |
| MINI born | 0 | 0 | +.062 [−.042,.208] w |

w = CI includes/touches 0 → weak evidence.  flag_on's LC born gain is
the only positive-CI diff in the table — and it survives the trusted
subset too: +.089 [.018,.179] over 28 days (v2 +.036 weak, v2b +.018
weak).  The recall gain is real; the failure is collateral only.
(V8 lab-vs-prod LC@2 +.056 [−.086,.202] and lab-vs-naive +.067
[−.039,.179] — both weak.)  Sparse day drivers: the whole LC@2 signal
rests on ~3 days.

## Mechanisms (all verified in cand_log / object events)

1. **rate_total ledger bleed** — the single root cause of every
   keep-rule failure.  Defended births spend the shared joint counter;
   whichever family proposes in the same 72-bar window loses the slot.
   Victim moved BOX→PL→spread across variants; mechanism identical.
   Fix = REQ-L3 option 1 (`cont` exemption in `salience.py` ~line 493 —
   build lane's file; spec written in REQUESTS.md).
2. **MINI-carried LC hits** — family match is type-agnostic; flag_on's
   .229 includes ~3 LC goldens hit by MINI-typed defended objects.
   v2 loses them; v2b recovers them as LC but pays budget thrash.
3. **Budget thrash** — under all-LC typing, young-origin proposals
   compete against mature heavy origins for 2 slots: matched objects
   get superseded twice in 2 bars (9.57b#4) or never born (9.57c:
   288 proposals, 222 suppressed).  Widening the budget (v2c, 3 LC)
   is *worse* — more births spend more ledger.
4. **Flicker premium was MINI churn** — flag_on .43 vs off .33; both
   LC-only variants are .33.

## Recommendation ordering for the Owner

1. If the goal is level recall regardless of collateral: **flag_on**
   (LC +4, weak CI).
2. If the goal is a keep-rule-clean lever: **v2b + REQ-L3 option 1**
   — the exemption should heal the remaining −1s while keeping the
   recall; needs a build-lane line in `salience.py` and a re-A/B.
3. Otherwise: keep OFF; the defended-origin grammar is validated
   (gains are exactly "old defended price re-approached") but its
   cost is ledger contention, not perception quality.

## Pooled CIs for v2b − flag_off (extended)

- level-family born recall (LC+MINI): +.025 [−.059, .112] — weak.
- LC snapshot recall at τ: +.061 [−.006, .150] — weak.

## Generator coverage (flag_on, per R22 §22.4 framing)

A defended-origin proposal within match tolerance during the golden
span exists for: **LC 40/47 = .851** (trusted subset **36/39 = .923**),
MINI 26/30 = .867.  Born-hit conversion under the ledger+budget is
.213/.033 — coverage is essentially solved; what remains is selection
(the shared rate_total ledger) plus internal budget ordering.

## Residual generator gap (trusted goldens with NO in-tol proposal)

6 trusted level goldens have origins but no proposal inside tolerance —
all are **sub-2-pip price misses**, not missing structure:

| golden | type | golden | nearest prop | gap |
|---|---|---|---|---|
| 9.14c#0 | MINI | 13183.4 | 13185.6 | 2.2p |
| 9.17b#0 | MINI | 13235.1 | 13236.7 | 1.6p |
| 9.17b#1 | LC | 13264.8 | 13266.8 | 2.0p |
| 9.33b#0 | MINI | 13036.0 | 13037.0 | 1.0p |
| 9.37c#2 | LC | 13176.2 | 13178.3 | 2.1p |
| 9.65a#1 | LC | 12480.6 | 12482.3 | 1.7p |

The defended-edge convention (outermost defended price) sits ~1–2p off
the author's anchor on these.  Proposal-precision work: cluster the
origin's actual touch prices and pick the modal touch, or keep a
secondary candidate at the densest touch — generator-side, cheap.

## THE ZERO-SUM TEST (R25 §25.5) — fam_ledger landed, 3 arms @2795e5e0

| | LC born | LC@1 | LC@2 | BOX Δ | PL Δ | keep-rule |
|---|---|---|---|---|---|---|
| (b) fam_ledger only | .125 | .021 | .021 | **−2** | 0 | FAIL (BOX) |
| (c) fam_ledger + v2 | **.229** | **.064** | **.128** | **0** | **0** | **PASSES** |

(R28 §28.5 asked for LC@1: the author's median live count is 1, so
@1 is the honest single-slot reading — (c) triples it .021→.064,
trusted .026→.077.)

(c) is the first defended-origin configuration to satisfy every
keep-rule leg: LC +4, BRACKET +5†, CL +1, worst loss CONTEXT_RANGE −1;
clutter ratio 2.50=2.50, live@τ 0=0, flicker .33=.33, births/panel
6.0=6.0.  CIs POSITIVE: LC born +.120 [.009,.242], LC@2 +.119
[.021,.233] (lab ranker).  Scoreboard @2795e5e0: LC .12→.21,
clutter 10=10, snap .10→.11.  EVAL-AUDIT independent re-run
@9283b389: keep-rule pass CONFIRMED (LC .12→.21, BOX 0, PL 0).

**R29 §29.2 narrowed verdict — the pack's exact wording:**
"famledger v1 + defended LC: keep-rule pass on born recall
(verified); four kinds silenced (defect); no gain at the author's
budget."  A direction, not a result: under the engine's top-k
ranker (c) is flat at the author's budget (.006/.025/.088 at
k=1/2/5 vs base .01/.01/.07); the @k/snapshot gains above are
lab-ranker readings.  famledger v1 defects: zero-share kinds
silenced, shared live-budget/NMS/timing coupling, cont bypass.
Both flags stay default OFF.

† BRACKET deltas are an **upper bound** — the ruler's BRACKET rule
has no price check (R30 §30.3).

### Ceiling probe (same hash): second LC slot = priced trade

| arm | LC born | LC@2 | clutter | live@τ | flicker | verdict |
|---|---|---|---|---|---|---|
| (c) famledger_v2 | .229 | .128 | 2.50 | 0.0 | .33 | KEEP-RULE PASS |
| (d2) +rate_lc=2 | **.292** | **.170** | 3.00 | 1.0 | .67 | family leg pass, INK leg fails |

Note: `fam_rate_level_carried=2` alone is a no-op (bit-identical) —
the binding cap is per-kind `rate_level_carried=1`
(salience.py:483).  d2's +3 goldens cost +1 object/panel and 2x
flicker: a priced trade for the Owner, not a free keep.
