# DN_TF — tease/false labels, bar markers, and time gating

Three related output surfaces: (a) **LABEL_TF** — the T(tease)/F(false)
annotations the author puts on edge pokes; (b) **BAR_MARKER** —
evening-star ticks and named-bar marks; (c) the **time gates** —
session windows and scheduled stand-asides that decide *when*
structure may be evaluated at all. Today: 209 LABEL_TF born
(mechanical, one per poke); BAR_MARKER coverage 0/4 — no route.

## 1. Market mechanism

RT3 P4/P7: scheduled flows are *non-structure events* — the 14:30
CET US-data jump (conditional-mean jump, ABDV), the 14:15 CET ECB
fix (~2.5bp pre-fix drift then reversion — Krohn et al. 2024), the
16:00 CET NY option cut (EBS-documented volume spike), the 17:00 CET
WMR fix (5-min window since Feb-2015; month-end amplified — Evans
2018). Structure evaluated through these windows reads flow noise as
geometry. Conversely, *teases* are the mechanism's texture: stops
beyond a level fire and TP depth absorbs them — poke-and-fail is the
expected signature of a working edge, which is exactly what a T/F
label annotates.

## 2. Volman's criteria (RT1 §5, §6.2–6.3)

- **T then F:** a poke beyond the edge that closes back inside is a
  tease; a tease that *then* breaks is relabeled false-break
  retrospectively — labels may overlap, so objects carry a primary
  label plus attributes (RT1 §4.4: "false and tease labels may
  overlap").
- Tease depth is small and bounded — measured, not fixed (RT1 §9:
  "tease depth" is a must-measure).
- **Session discipline:** quiet/open windows and lunch windows
  filter evaluation; news and abnormal volatility → stand-aside is
  a first-class output (RT1 §5).
- Bar markers (evening-star ticks over/under a named bar) mark
  *events*, not levels — "an evening-star marker over the ~14:00
  spike bar" (9.37c), "tick under the 08:05 low" (9.62a).

## 3. Other schools (RT2)

- "False breakout" is implied by the Osler asymmetry (mechanism =
  EVIDENCE) but the named pattern is untested in FX (PRACTITIONER).
- Session seasonality is EVIDENCE-grade (Dacorogna; Andersen &
  Bollerslev; Ito & Hashimoto): three activity humps, lunch dips;
  Asia is the documented low-activity trough — quiet-tape filtering
  is not superstition.
- Option-cut *pinning* is unproven in FX → soft gate only (RT3 P4).

## 4. Golden measurements (TUNE v2)

- LABEL_TF: 209 born candidates — labels attach to box/line edges
  on poke events; golden count small (labels fold into object
  attributes; the engine's standalone births over-count).
- BAR_MARKER: 4 golden, **0 covered** — evening-star ticks
  (9.37c#1, 9.41b#2), morning-star tick (9.62a#2), star ticks over
  highs (9.66a#0).
- Session: ignored candidates concentrate in Asia (Q2 readout);
  golden objects cluster in EU/US hours.
- RT3 P7iii: per-15-min CET volatility curve on our feed is a
  pending self-measurement that calibrates all windows.

## 5. Operational rule

**LABEL_TF.** A label is an *attribute event on a live object*, not
an object:
- `tease`: bar extreme beyond a live edge by ≤ tease_tol, close
  back inside — `tease_tol ≈ max(1–3 pips, ~0.4·ABR)` MEASURE
  (distribution of poke depth vs edge on TUNE).
- `false`: a tease window where price then traverses the edge
  (close beyond far side + no immediate re-entry) → relabel
  within ≤3 bars (spec); kept as the object's label history.
- Primary label + attributes model (RT1) — never a separate object;
  dedupe: one label per edge per excursion.
- Depth rule: tease excursion ≥ ~½ the edge's box height relabels
  context differently (spec §3.2's relabel window — keep, MEASURE).

**BAR_MARKER.** New minimal route: a named local candle pattern
(evening/morning star: three-bar sequence, middle bar extreme beyond
neighbors) or a text-named single bar → marker at that bar's
extreme. Detection runs on confirmed θ₁ pivots where the middle
bar's extreme exceeds both neighbors by ≥ ~0.5×ABR (MEASURE on the
4 goldens). Deterministic O(1) check at pivot confirm.

**Time gates (hard calendar, CET wall clock via cet.py):**

| window | rule | grade |
|---|---|---|
| 14:30 CET ±15m (US data) | no level/edge break *initiated* inside counts as structure; objects neither born nor killed on the window's bars alone | EVIDENCE (ABDV; Chaboud) |
| 14:15 CET ±10m (ECB fix) | same — V-shaped non-level event | EVIDENCE (Krohn 2024) |
| 16:50–17:10 CET (WMR fix) | stand-aside; month-end double weight | EVIDENCE (Evans 2018) — **note: 17:00 CET, not 16:00** (RT3 correction) |
| 16:00 CET ±10m (option cut) | soft stand-aside pending our own pinning study | PRACTITIONER+EVIDENCE-mech |
| Asia 00:00–08:00 CET | breakout *evaluations* during Asia are low-conviction — demote in salience, don't ban | EVIDENCE (thin-session cascades cut both ways) |
| 01:55 CET (Tokyo fix) | noise source inside Asian range | EVIDENCE |

**STAND_ASIDE output.** First-class engine output (RT1 §5): emitted
on (i) hard calendar windows, (ii) abnormal volatility —
`range_t > q~95 of rolling same-time-of-day ranges` or FOCuS/CUSUM
alarm on bar ranges (RT4 §5.2), (iii) chop veto: CI(n≈14) and
ER(n≈10) high-choppiness suppression in salience (RT4 §12.9 —
calibrate on golden no-object vs drawn panels).

## 6. Failure modes

**False positives:**
- 209 mechanical LABEL_TF births — one per poke, no dedupe, no
  attachment to a *decision-relevant* edge. Asia-session pokes
  generate the bulk.
- Structure born inside 14:30 CET window reads a data spike as an
  extreme (the 15:15-spike class — 9.15b's ceiling ruled the spike a
  poke; same principle at birth).
- Evening-star detection on every three-bar bump → marker spam;
  needs the θ₁-pivot + middle-extreme-dominance requirement.

**False negatives:**
- `9.37c#1`, `9.41b#2`, `9.62a#2`, `9.66a#0` — all four golden
  markers uncovered: no route exists.
- Tease labels on *named* edges during the decision window are
  decision-relevant ink the author uses; a pure-suppression design
  must not delete them.
- WMR-fix bars may carry a real level traverse → gate suppresses
  *initiation*, not a traverse already underway (evidence first,
  window second).

## 7. Tests

**Golden-derived:**
- (a) Marker route: ≥3/4 golden BAR_MARKERs covered (the 4th is the
  multi-bar 9.66a ticks over highs — may need a variant).
- (b) T/F agreement ≥0.60 on matched boxes (RT4 §12.8 gate).
- (c) Label dedupe: ≤1 label per edge per excursion in telemetry.

**Theory fixtures:**
- (d) Poke fixture: wick beyond edge, close inside → tease; second
  bar traverses → false relabel within 3 bars.
- (e) Calendar fixtures: synthetic break exactly at 14:32 CET → not
  counted as initiated-in-window logic boundary tests (14:15/14:45
  edges inclusive/exclusive per spec).
- (f) DST boundary: windows computed via cet.py across the Mar/Oct
  switch — regression on real 2012 dates.
- (g) Stand-aside is emitted, not silent: abnormal-range bar →
  STAND_ASIDE row with reason code.
