# SF01 — DECISIONS (autonomous judgement calls)

One entry per call: what, why, alternatives. Newest last.

## D1 — Structural stops through a fixed-S_pips engine (2026-09-21)

`pa_fill.simulate` supports only `S_pips` (fixed per spec) and `tp_mult`
(fixed R from fill); entry dicts carry `order_px`/`inv`/`atr` but no per-entry
SL/TP. Editing `lib/` is off-limits (R02 freeze bundles cover it; the mandate
treats lib as the referee).

**Decision:** every setup computes a STRUCTURAL stop price first (zone far
edge / probe extreme / retest extreme + 0.25 x ATR14(M5) buffer). The detector
then assigns the entry to a declared ladder rung `S` — the smallest rung
`>= d_struct` with `d_struct >= 0.6 * S` — and skips candidates whose
structural distance fits no rung (also enforces `S >= 10 x c_rt(symbol)` at
order time, the charter geometry guard). Effect: the realised SL always sits
at or beyond the structural extreme, never inside it; each ladder rung is a
separate ledger config. Ladder (pips): {11, 14, 18, 24, 32} — covers
EURUSD..USDJPY guard floors and M5 swing scales.

Alternatives rejected: (a) fixed 10-pip Volman stop — fails the guard on
GBPUSD/JPY and isn't structural; (b) per-entry SL engine edit — forbidden;
(c) ATR-multiple stops without structure — that's the legacy repackaging
mistake (VRAS-006 kill).

## D2 — Zone generators for the setup families

F1-F4 grids use `generator in {line1_cluster, sd_base}`: swing-cluster zones
(dense, multi-touch, the baseline perception) vs supply/demand bases (the
institutional unfilled-orders story — mandate's "pro zones"). `ref_levels`
excluded: raw PDH/PDL/Asia/round fades are legacy kills and the mandate says
zone-vs-empty physics is unproven, so ref levels add a dead-mechanism risk;
they remain available as context (room gates can use any armed zone).
fractal_h1/kde_swing/profile_va deferred: same marginal mechanism as
line1_cluster at higher compute cost. F5 needs no zones (pure structure).
F6 uses line1_cluster zones as box edges.

## D3 — Session gate is mechanism, not a rescue filter

Entries are emitted only when the signal bar closes inside eu (05-11 UTC) or
us (11:30-17:30 UTC) sessions — Volman trades only active sessions, and the
matched-random baseline only covers in-session bars (out-of-session signals
get no lift measurement). Declared a priori in every spec; never added
post-hoc to a dead config.

## D4 — Exact replay semantics for the zone pass

`ZoneGen._step_all` (used by `run()`) is an approximation: it steps only zones
intersecting the bar or still "warm", so it can miss (a) reclaims after the
48-bar response window and (b) break/flip closes on bars whose range clears
the band + 2 x break pad entirely (gap bars). `views_at`/`state_at` replay
every bar in [born, t] and is the R01-tested reference. My snapshotter
(`families/sf_ctx.py`) drives `_on_bar` + backfills new zones from born_idx +
steps EVERY live zone each bar => provably identical to `views_at` (unit
tested). Cost is O(live zones) per bar — acceptable once per (symbol, gen).

## D5 — Compute scheduling

Heavy jobs (zcache build, census scans, evaluate screens) run as background
python via `pa_slots.acquire(timeout=large)` — they queue behind R02's two
slot holders. Light jobs (unit tests on synthetic data / small real slices,
file writes, spec hashing) run inline without a slot — they take seconds and
hold no shared resource. This matches the charter's intent (<= 2 heavy
processes) without dead time.

## D6 — Config budget shape

Per family: <= 24 configs total = revision-1 grid (<= 12) + optional
revision-2 grid (<= 12). Grids pre-declared in the family spec before any
outcome. Neighbouring grid cells are evaluated anyway, which supplies the
plateau check (gate 7) for free.

## D7 — Warm-up smoke failure was in the random baseline, not the detector (2026-09-21)

`pa_eval.evaluate` guards strategy entries by UTC (`utc[sig] < utc_start` ->
raise) and guards matched-random picks only via `live_cut =
d.get("utc_start", 0)`. `pa_data.frame()` does NOT return `utc_start`, so
`live_cut` is 0 and the random-baseline warm-up filter is silently disabled.
`match_random` draws uniformly over ALL in-session bars of a cell, including
the 30-day warm-up, so a warm-up pick reached `pa_fill.simulate`, which raised
"signal bar 1900 ... first live bar = 5818". Verified: the F1 detector's own
minimum sig is >= first_live_idx on every (symbol, gen) cache, and
`random_warmup_dropped` exists precisely for this filter.

**Decision:** keep `lib/` untouched (referee). Supply `data_provider` to
`evaluate()` — the contract's sanctioned hook — via `families/sf_provider.py`,
which wraps `pa_data.frame` and adds `utc_start`/`utc_end` from
`pa_sealed.split_bounds`. Both fields are inside `_DATA_SHA_FIELDS`, so the
ledger commitment covers them. Effect: warm-up random picks are dropped
(correctly — the baseline must be DESIGN-period bars), and
`random_warmup_dropped` is reported per config.

Alternatives rejected: (a) filter inside `entries_fn` — wrong layer, the
randoms are the referee's; (b) edit `pa_data.frame` — off-limits; (c) drop the
matched-random control — forbidden by the screen.

## LEAD NOTE (03:10Z) - read rounds/SF01/LEAD_RULINGS.md

The Lead's rulings on D1-D6 and on F1 spec v2 are in `rounds/SF01/LEAD_RULINGS.md`. Re-read that file
at every family start. The PA-PRO python cap is now 4 (charter addendum 3), and this lane may hold 2
slots at once.

## D8 — F2 anchor moved from role_flip to the break bar (pre-outcome revision)

F2 v1 required role_flip==1 (the engine only flips a zone after the close
holds beyond the far edge for > reclaim_bars=96). DESIGN census of v1
(detector-only, no outcomes): basket ~1,672 signals / 314 wk = 5.3/wk, and
most grid cells fail N>=300 pooled (S=11 cell ~92). That is the AND-gate
cadence trap again.

**Decision (v2):** anchor the retest episode at the BREAK bar
(broken_idx) and let it persist through the flip — the classic
break-and-retest pullback happens within a few bars of the break, long
before the 96-bar flip confirmation. Population = zones currently broken
(broken_idx set, within break_keep_bars) OR role-flipped, with the first
post-anchor touch + rejection close back out of the band in the break
direction. side = -broken_side for both phases (broken ceiling that broke
up -> long; flipped floor has the same broken_side). Superset of v1, same
hypothesis, still structural. Allowed because NO F2 outcome has been
computed (Lead Review 2: pre-outcome re-spec is still preregistration).

Alternatives rejected: (a) keep v1 and accept dead N-gates — wasteful;
(b) per-touch instead of first-pullback — held in reserve as revision 3
material; (c) drop the session gate — violates D3.

## D9 — entry tag must be the signal index, not the zone id (referee contract)

pa_eval.evaluate links matched-random entries to their source signal via
tag: randoms get tag = kept[i//K] = the source entry's INDEX in the
per-symbol entries list; the matched strategy subset is trades whose
tag is in kept.  My detectors emitted tag = zid, so "matched" was a
near-empty accidental overlap — F2/F3 lift_pp came out None and F1's
lift was computed off a corrupted subset.

**Decision:** all detectors now emit tag = entry index (referee
contract) plus a separate zid field used by sf_snap for zone
highlighting.  This does not change which signals are emitted, so spec
hashes stand — no re-preregistration needed.  F1/F2 verdicts are
PF-driven and unaffected; F1/F2 screens were re-run with correct tags so
the ledger rows carry valid lift fields.

## D10 — F5 v2: inv at the pullback's deepest point (pre-outcome revision)

F5 v1 put `inv` at the second-leg pivot bar extreme:
`s_struct = pivot-bar range + 2p`. DESIGN census of v1 (detector-only,
no outcomes): basket 0.19-1.85 sig/wk — catastrophic. Funnel on EURUSD
(h1 trend): 16,374 trend-aligned two-leg pairs -> tol 8,195 -> bounce
6,212 -> session 2,914 -> range 2,753 -> **s_struct in [10,32]p: 447**.
The 10x c_rt floor kills ~84% because M5 pivot bars are usually <8p
tall.

**Decision (v2):** `inv` moves to the DEEPEST point of the whole
two-legged pullback — long: `inv = min(l[i1], l[i2]) - buf`; short:
`inv = max(h[i1], h[i2]) + buf`. This is the textbook Brooks stop
("below the pullback low", i.e. below BOTH legs, not just the second
bar) and lifts s_struct into the middle rungs instead of failing the
cost floor. Entry stays the stop beyond the pivot bar (unchanged).
Grid stays 20 cells (S x tr_src x tol_atr). Legal pre-outcome revision
per Lead Review 2 — no F5 outcome has been computed. Revision count:
1/2 used.

Alternatives rejected: (a) relax the 10x cost floor — charter-mandated,
untouchable; (b) drop the bounce-pivot requirement — destroys the
two-leg identity; (c) fixed-S entries like F1 v1 — rejected in D1.

## D11 — F6 box_atr scale fix (pre-outcome spec correction)

F6 v1 declared `box_atr in {0.7, 0.9}`: box height over the last 12
bars <= box_atr * ATR_m5. DESIGN census produced literally 0 signals —
a 12-bar window compressed under ONE average bar's range essentially
never occurs; the threshold was calibrated for per-bar width, not the
window's total height. Detector-only funnel confirms 0 bars pass the
box gate in the first 20k live bars of EURUSD.

**Decision (v2):** `box_atr` re-scaled to `{2.5, 4.0}` — box height vs
ATR, i.e. the whole 12-bar box spans at most 2.5-4 average bars (a
real compression; the median 12-bar range is ~6-8x ATR). All other
rules unchanged; this is a pre-outcome correction justified by census
diagnosis alone (no outcome computed). Revision count: 1/2 used.

## D9-bis — F1 screen re-run with the corrected tag contract (SF02 Q0)

Lead Review 3 caught that F1's screen was never re-run after the D9 tag
fix (its SCREEN.json was stamped 03:26:37Z, before the fix). Re-run
executed under SF02 Q0; new ledger trial ids T000226..T000246 (minus
T000229, which is the SF02 autopsy plan preregistration interleaved in
the ledger). Verification: all 20 cells produce IDENTICAL N, PF_x1 and
t_x1 vs the pre-fix screen (backup: SCREEN_v1tags_backup.json) — as
required, since tags only affect the matched-random linkage. Lift
fields are now valid (e.g. S11/line1/rb0: lift -1.03pp, CI
[-2.96,+0.94]). The DEAD verdict is unchanged.
