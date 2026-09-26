# ROUND_L9 — production paired A/B: `level.defended_origin` OFF vs ON

One code state, engine hash `1c24be53`, 198 TUNE panels, ruler
`50e11fd5`.  Arm OFF = shipped params; arm ON = same engine with only
`level.defended_origin=true`.  Harness: `ab_engine.py` (fresh engine
per panel per arm, deterministic — verified: 0 per-panel LC-hit diffs
between PYTHONHASHSEED 0 and 42 over all 198 panels).

## Headline numbers

| metric | flag_off | flag_on |
|---|---|---|
| LC born recall | .146 (7/48) | .229 (11/48) |
| LC born recall, trusted | .150 (6/40) | .250 (10/40) |
| LC precision | .036 | .043 |
| MINI born recall | .065 (2/31) | .065 (2/31) |
| LC snapshot recall | .021 (1/47) | .106 (5/47) |
| LC recall@2 (birth-score rank) | .021 | .106 (tr .128) |
| MINI recall@2 | .000 | .000 |
| LC births/panel | 0.98 | 1.03 |
| MINI births/panel | 0.04 | 0.07 |
| all objects born/panel (med) | 6.0 | 6.5 |
| clutter ratio (med) | 2.50 | 2.50 |
| live level objects @tau (med) | 0.0 | 0.0 |
| flicker (level-set changes/h, med) | 0.33 | 0.43 |

Paired day-bootstrap (10k resamples over dates):

| diff (on − off) | estimate | 95% CI | verdict |
|---|---|---|---|
| LC born recall | +.071 | [.010, .152] | positive |
| MINI born recall | +.000 | [−.062, .062] | weak evidence |
| LC recall@2 | +.068 | [.000, .156] | weak evidence (edge at 0) |
| MINI recall@2 | +.000 | [.000, .000] | weak evidence |

## Keep-rule (R18 §18.1) verdict — flag stays default OFF

Rule: default ON only if recall rises at equal-or-lower ink AND no
family loses more than one matched object.

- recall: LC up (+4 matched objects), MINI flat — rises.
- ink: clutter ratio 2.50 = 2.50, live clutter at tau 0 = 0 — equal.
- **family loss: BOX −2 net (4 lost: 9.2b#3, 9.18a#0, 9.40c#2,
  9.45b#0; 2 won: 9.7b#0, 9.39a#0) — violates the ≤1 rule.**
- flicker 0.33 -> 0.43 ch/h (a side metric, not part of the rule).

Result: flag stays `false` in `params_v1_1.json`.  The result is a
lever for the Owner's pack, per R18.

## Route realization — starvation finding (measured)

`defended_origin` candidate outcomes under flag ON (all panels):

| outcome | count | share |
|---|---|---|
| proposed (trigger log) | 164,067 | 55.9% |
| suppressed_budget (my 2+1 gate) | 122,913 | 41.9% |
| rate_limited (salience) | 3,123 | 1.1% |
| expired (pool TTL) | 2,895 | 1.0% |
| outranked (pool NMS) | 428 | 0.1% |
| born | 262 | 0.09% |
| nms_suppressed | 10 | — |

Interpretation:

1. The trigger re-proposes every bar while price is in range — the
   cand_log volume is honest but noisy (≈830 log rows/panel).
2. The local 2+1 budget dominates suppression (122,913) because
   `pending` pool members count toward occupancy — once 2 LC proposals
   are queued behind `rate_level_carried=1/72`, every later approach
   is budget-suppressed.  The cap mechanism works as designed, but it
   spends most of its force blocking its own queue, not rivals.
3. Salience then admits a trickle: 262 born ≈ 1.3/panel — the
   author's-ink-sized output.  `live@tau` median stays 0 because level
   objects also die fast (traverse/stale/price_left) or arrive after
   tau.
4. The lab's "2 live LC at tau" design point is NOT reachable while
   `rate_level_carried=1/72` + `rate_total=5/72` govern births — two
   live defended LCs need two births inside overlapping windows, which
   the per-kind cap rarely permits.  This is a REQUESTS.md item
   (REQ-L3), not a silent param change: salience params are outside
   the LEVEL-LAB scope (R19 §19.3 scope = levels.py + level params).

## Hash-drift note (for the record)

The first flag_off scoreboard row was measured at `a7b09b74`; files
`swings.py`/`gates.py` show external mtimes (19:54Z / 20:12Z) and the
code hash drifted to `1c24be53` between the two appends.  flag_off was
re-measured and re-appended at `1c24be53` — the flag_off row above is
the paired one.  Per R14 §14.2 both arms are now at one code state.

## Files

- `ab_engine.py` — paired harness + metrics + scoreboard wrapper.
- `ab_r2.json` — per-day per-family recall@k for both arms.
- `ci_bootstrap.py` + `sb_r2.json` — V8 proposer day-bootstrap CIs:
  lab−prod LC@2 +.056 [−.086,.202] weak; lab−naive +.067
  [−.039,.179] weak.

## Addendum — who wins, live occupancy, churn, Tier-A

Flag ON gains vs OFF (per-golden, 198 panels):

| golden | type | note |
|---|---|---|
| 9.4a#2 | MINI | "a short horizontal M floor, ~08:05–09:05" |
| 9.39b#2 | LC | "a nearly flat floor, ~10:45→~12:50" |
| 9.40c#1 | LC | "short-dashed horizontal at the W lows (≈1.3194)" |
| 9.51a#1 | LC | "DASH ~08:00–10:05 at an older low" |
| 9.59a#2 | LC | "DASH ~08:55–10:30 at the base low" |
| 9.66c#1 | LC | "DASH ~12:00–15:10 (the older 09:45 low)" |

Lost: 9.14c#0 (MINI).  Every gain is an *old defended price*
re-approached — the intended grammar.

Live occupancy (15-min samples, flag ON): 0 live 40.2%, 1 live 48.6%,
2 live 10.1%, 3+ 1.1% — the author-shaped cap holds; the τ-median of
0 comes from timing (levels die between goldens' decision points).

Churn: 267 defended births, **171 closed 'superseded' (64%)** — the
budget keeps ≤2 live but pays birth+death churn to get there.
n_def at birth spans 2..24 (median ~7); class mix asia 124 /
theta1 74 / theta2 66 / session 3.  Median lifespan 55 bars.

Tier-A misses (V1 suspect labels): 10 of 11 Tier-A level labels are
missed under flag ON — the route's hits concentrate on clean labels;
only 9.57b#3 (LC) was matched.  Consistent with trusted recall (.250)
> all-labels recall (.229).

Trusted subset (RESUME-5 item 6a): the budget mechanism's recall@2
holds and *strengthens* on trusted labels — lab budget 2+1 LC born
.667 all -> .750 trusted (ROUND_L8 reruns); V8 stream LC@2 .333 ->
.400 trusted vs prod .208 -> .250 (sb_r2 ktr columns).

## Addendum 2 — BOX loss mechanism; defended MINIs

BOX −2 mechanism (per-golden cand_log on the 4 lost panels): defended
births spend the shared `rate_total` ledger — flag_on shows defended
births on all 4 panels (1–3 each, none inside the golden box span) and
BOX born counts drop (9.18a: 2→1, 9.40c: 3→2) with shifted
rate_limited/outranked counts.  The loss is ledger contention, not
match noise.  Fix is REQ-L3: separate `rate_defended` ledger or exempt
the route from `rate_total`.

Defended MINIs: 201 births (~43% of defended births), cls asia 117 /
theta1 52 / theta2 31 — yet 0/31 golden MINIs hit.  V6 explanation
confirmed in production: young-origin MINIs birth ~60 bars after the
origin bar at recent-session prices, while golden MINIs are
mid-lifecycle micro floors — a class mismatch, not a tuning gap.
