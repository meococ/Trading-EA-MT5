# NOTES FOR BOX-LAB — levels as pre-existing barriers

From LEVEL-LAB V2/V4. A box edge gains credibility when it sits on an
*already defended* price — the level registry is the causal source for
"was this price already a wall before the box formed?"

## What a credible barrier looks like at time t

A live level (or origin record) qualifies as a pre-existing barrier for
a candidate box edge `(price P, side s)` iff ALL of:

- `|level.price − P| <= 3.0 p` (V2 zone width p50 5–8 p → half-band ~3);
- `level.dir == s` (a defended low backs a box floor, a defended high
  backs a box ceiling);
- `level.origin_bar < box.build_start` (strictly pre-existing — the
  structure the box is *resting on*, not the box itself);
- `level.n_def >= 2` (≥1 retest after origin — the defended-wall rule);
- not stale: `t − level.last_touch <= 60 bars` (R11 staleness bound).

## Causal query

Per bar, the registry is a list sorted by price — one query per edge:

```python
def barrier_at(t_bar, price, side, origins, tol=3.0):
    hits = [og for og in origins
            if og["dir"] == side
            and abs(og["price"] - price) <= tol
            and og["bar"] < t_bar
            and og["n_def"] >= 2
            and t_bar - og["last_t"] <= 60]
    return hits   # strongest = max(n_def, then age)
```

Features worth feeding a box scorer (all causal at t):

- `barrier_n_def` — defence count of the strongest backing level;
- `barrier_age_min` — `(t_bar − og.bar)·5`, how long the wall stood;
- `barrier_dist_p` — `|price − og.price|`, exactness of the seat;
- `barrier_cls` — theta2 / theta1 / session / asia (θ2 + asia are the
  author's heaviest classes per V2).

## How BOX-LAB consumes it

- In the lab sandbox: `levels_lab.LevelLabEngine.origins` is the
  registry — import and run it alongside the box proposer, or copy the
  30-line origin block (it is self-contained: `_add_origin`,
  `_session_origins`, `_mark_superseded`, `_expire_sweep`,
  `_touch_sweep`).
- In production after integration: `LevelBook.origins` + live
  `LEVEL_CARRIED`/`MINI_LEVEL` objects — same query on `o.geometry`.
- Do **not** use born objects only: the registry (`origins`) is the
  superset — born levels are the subset that salience promoted, and
  rate-limiting would hide real barriers from the box scorer.

## Caveats measured

- ~10% of trusted golden levels have no in-day bar origin within 2 p —
  either Tier-A misprices or structures older than the day. A missing
  barrier hit is weak evidence *against*, not proof the edge is bad.
- Level dir convention: `dir=−1` = defended low (support), `+1` = high.
- Asia extremes only exist once Asia ends (m ≥ 420); before that they
  are still "running" — a box edge on a live Asia extreme mid-session
  is fine, the registry exposes it with `cls='asia'`.

## Post-ledger note (R25/R27, measured 22:4xZ)

If `salience.fam_ledger` is ever on: `broken_box_edge_up/down` objects
are typed LEVEL_CARRIED and therefore draw on the LC share
(`fam_rate_level_carried`, currently 1/72) — they compete head-to-head
with `defended_origin` births for that single slot (measured: a
score-13.16 `broken_box_edge_up` cand on 9.57b died `rate_limited` to
a defended birth).  BOX-LAB's edge emitters and my route are now
intra-family rivals; any future LC-share raise or per-route split
changes both lanes' numbers — re-run the paired A/B before trusting
either side's totals.
