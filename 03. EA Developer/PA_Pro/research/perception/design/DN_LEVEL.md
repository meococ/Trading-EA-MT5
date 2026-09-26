# DN_LEVEL — LEVEL_CARRIED and MINI_LEVEL

Horizontal references carried forward from earlier structure: broken
box edges, congestion tops/bottoms, session extremes — the "price the
market remembers." Golden coverage today: LEVEL_CARRIED 23%,
MINI_LEVEL 19% — the worst families, and the clearest evidence that
the current route set (mostly `broken_box_edge`) is far too narrow.

## 1. Market mechanism

RT3 §3 (Osler 2003, EVIDENCE for the mechanism): resting depth is
**asymmetric around a level** — take-profit orders at/just before it,
stops just beyond it. Consequences for the object:
- A level is a **zone**, not a mathematical line: near side where
  TPs cluster (≈1 pip tolerance, Osler's 0.01% "reach"), far side
  where stops sit (a few pips beyond — MEASURE on our data).
- **Magnet-then-accelerator** (RT3 P3): approach → stall/absorption;
  decisive traverse → elevated continuation speed for ~3–24 bars.
- Role reversal is mechanically expected: a broken edge's stop
  cluster has fired, leaving TP depth behind — the same price now
  caps from the other side (K&OW depth-at-level mechanism).
- Depth is *consumed* by touches → a level weakens per test (RT3 §4);
  the engine should track "consumption" rather than "strength".

## 2. Volman's criteria (RT1 §4.2, §6.3; Q1 rulings)

- Carried levels draw as **long-dashed horizontals** whose span is
  the *carry era*: from the source event to a stated or implied end
  ("to ~17:00" sets the END of the dash — Q1 9.5c residual ruling;
  sibling convention verified on 9.23c 14:01→17:35, 9.6c
  13:53→15:30).
- **Sibling price resolution:** "projected from that congestion top"
  prices the level at the *referenced formation's* edge (9.5c →
  1.3137), not at any local extreme.
- **MINI_LEVEL** = short horizontal marking a micro-ceiling/floor of
  a named small formation ("a tiny horizontal under the combi,
  ~17:50–18:00"); span = the formation's own little window; price =
  the extreme-with-company on the stated side (9.15b ruling: the
  "small ceiling" is the cluster of highs, not the span low, and not
  the lone spike).
- Round numbers are **context/magnets, not emitted structures**
  (RT1 §5) — "under the 1.30" describes position, and may anchor a
  box edge, but a round number alone never births a level.
- Broken barriers extend dashed (RT1 §6.3) — a carried level is the
  horizontal counterpart of the dashed broken line.

## 3. Other schools (RT2)

- Classical "polarity principle" (old resistance → new support):
  PRACTITIONER, convergent with the depth mechanism.
- Wyckoff: ice/creek = the carried edge of a TR; events (SOW/SOS)
  define when it matters.
- ICT/SMC: "breaker"/"mitigation" blocks — same family, weaker
  causal discipline (PRACTITIONER-FOLKLORE); we keep only the
  role-reversal core.
- AMT: prior value-area edges carry — same object at daily scale.

## 4. Golden measurements (TUNE v2)

- LEVEL_CARRIED (n=47): span median 100 min, p25 58, p90 312 —
  carries run for hours; sources are congestion tops/bottoms
  (9.5c, 9.6c), old breakout bases (9.1b "the old breakout base"),
  supports' continuations (9.3c "a long-dashed continuation of the
  support").
- MINI_LEVEL (n=31): span median 30 min, p25 20 — genuinely small
  windows; prices cluster at formation extremes (ceiling/floor of
  combs, evening stars, tops of small patterns).
- Q2: 460 LEVEL_CARRIED born (single `broken_box_edge` route) —
  drawn rate low; 37 golden levels uncovered entirely (no route:
  congestion-top, continuation, evening-star marker types). 26
  MINI_LEVELs uncovered — **no route exists** for "a short
  horizontal".

## 5. Operational rule — multi-source level book

**Sources (each a named route):**
1. `broken_edge` — a box/line edge that died by traverse → level at
   the frozen edge price (spec; keep).
2. `congestion_edge` — a finished congestion formation's defended
   side (top/bottom of the cluster) → carried level; covers
   "projected from that congestion top".
3. `continuation` — an existing carried level whose text/formation
   says it extends ("continuation of the support") → extends the
   span, same price.
4. `session_extreme` — Asia/EU-open high-low as level after its
   window (e.g., "from the ~12:00 high ≈1.3263 to ~14:00").
5. `formation_extreme` (MINI_LEVEL) — ceiling/floor of a named micro
   formation: extreme-with-company on the stated side over the
   formation's own span.
6. `marker` — event markers ("tick under the 08:05 low",
   evening-star tops) → BAR_MARKER-adjacent single-bar level.

**Zone geometry (RT3 P1).** Stored price = the defended extreme
(cluster price). Rendered zone: asymmetric — near side
`z_near = max(1 pip, 0.15·ABR)`, far side `z_far = z_near + q75(
poke-depth past level)`, cap ~0.5·ABR. **MEASURE:** histogram of
poke-depth-past-level on TUNE (RT4 §12.5) sets q75.

**Span rule.** `t0` = source event bar (congestion start for
congestion-edge, break bar for broken_edge); `t1` = stated end when
the text gives one, else "while un-consumed": active until a close
back through the zone or panel end. The dash ENDS at the stated end —
the 9.5c ruling (carry era ≠ carry target).

**Consumption tracking.** Each touch within the zone decrements an
internal `depth` counter (starts ~3); at 0 the level demotes —
stops generating bracket/label context (keeps drawing if golden
shows long-lived carries; MEASURE: golden levels' post-birth touch
counts vs whether they remain drawn — likely "consumption" doesn't
remove the *drawing*, only its *decision weight* — encode as weight,
not death).

**Freeze.** Price frozen at birth; never re-priced (a level is a
memory). Only span extends (continuation route).

## 6. Failure modes

**False positives:**
- `9.1a` broken_box_edge levels born 02:10, 05:55, 09:40 — three
  carries in one morning, all ignored: mechanical birth on every
  box break with no salience test (460 born vs 48 drawn).
- Consumption-blind carry: a level broken-and-retested repeatedly
  keeps emitting context events after its depth is gone.
- Session-extreme spam risk: every session high/low is a *candidate*
  — only those the tape later respects should rank (salience).

**False negatives (all uncovered in Q2):**
- `9.5c#1` "long-dashed horizontal projected from that congestion
  top to ~17:00" — congestion_edge route missing → covered by no
  candidate.
- `9.6c#0` "long-dashed horizontal from the ~12:50 congestion lows
  ≈1.3223 to ~15:30" — same route.
- `9.3c#4` "a long-dashed continuation of the support ~16:45–17:25"
  — continuation route missing.
- `9.17b#3` "long-dashed horizontal from the ~12:00 high ≈1.3263
  to ~14:00" — session_extreme route missing.
- `9.1c#3` "a tiny horizontal under the combi ~17:50–18:00",
  `9.4a#4`/`9.11b#2` "a short horizontal ~HH:MM–HH:MM" — MINI_LEVEL
  has **no route at all**; 26 golden objects unreachable.
- `9.62a#2` "tick under the 08:05 low (Morning Star)" — marker route
  missing.

## 7. Tests

**Golden-derived:**
- (a) Coverage from 23%/19% to ≥ ~80% via the new routes; measured
  per route.
- (b) Sibling-price regression: 9.5c prices at 1.3137; 9.23c span
  ends 17:35; stated-end rule: dash `t1` == stated end (9.5c residual
  documented as the known-fail fixture until yardstick v3).
- (c) Extreme-with-company: 9.15b ceiling at the high-cluster, not
  the spike, not the span low.
- (d) Round numbers never birth a level by themselves (negative
  fixture).

**Theory fixtures:**
- (e) Broken-edge fixture: box breaks, level births at frozen edge,
  zone asymmetric (far side > near side).
- (f) Consumption fixture: 3 touches → weight demotes; drawing
  persists; no context events after exhaustion.
- (g) Continuation fixture: second formation at same price extends
  the dash span without repricing.
- (h) Magnet-then-accelerator analysis label (not engine input):
  measure post-traverse speed distribution on TUNE for the spec's
  continuation claim (RT3 P3/P7ii).
