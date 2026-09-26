# PERCEPTION_SPEC — PA-PRO L1 (`struct/`, "pa_struct") — v0 DRAFT

Status: **v0 DRAFT for R00** — frozen at R01 start (code SHA + this file's SHA recorded in
`rounds/R01/FREEZE.json` before any outcome is computed). Owner: program Lead. Authority chain:
`PA_PRO_CHARTER.md` §2 (objects/events, lines 53-62) > this file > build code.
Charter SHA256 verified at R00: `3C57536848A4AA6113950D06D50331B8C664E18B79D34E08DEF2F1019BC5DC2C`.

> **Binding supersession — Charter Addendum 1 (`docs/CHARTER_ADDENDUM_1.md`, SHA256
> `37756D6922C7134901E94940A10E03EF4E11F7B72418F754D2CEFFE525D38592`, 2026-09-20).** Where this
> v0 draft conflicts with the addendum, the addendum wins: (1) perception is ZONE-FIRST — horizontal
> structure is a band `[low, high]` with width typically 0.2-0.6 x ATR14(H1), never an exact price;
> touch/respect/break are defined against the band with overshoot tolerance (a wick through that
> closes back inside is a TEST, not a break); (2) trendlines become BANDS, secondary to horizontal
> zones, and are NOT required in the first physics run; (3) chart hygiene — at most ~4-6 zones armed
> within ±2 x ATR14(H1) of price, merged, labelled, never duplicated; (4) R01 is a ZONE GENERATOR
> BAKE-OFF: every frozen candidate generator (LINE-1 swing clusters converted to zones as the
> baseline, the ZONE-1 survey's best indicators, anything we build) runs through the SAME
> preregistered physics test, winner chosen by a pre-declared criterion with multiplicity correction,
> every candidate run a ledger trial; (5) ported indicators must be non-repainting (causal) or made
> causal, with license-compliant attribution, algorithms described in our own words.
> The object map below is the build inventory; the R01 prereg must restate the zone-first widths and
> the bake-off candidate list before the freeze.

Scope: L1 only. **No outcomes, no fills, no PnL exist anywhere in this layer** (same E4/F7 rule as
LINE-1, `vpa_lines.py:44-45`). This file maps the charter L1 objects/events to LINE-1 (read-only seed)
and specifies the causal contract, the frozen strength score v0, and the copy/rebuild plan.

All LINE-1 line numbers are `03. EA Developer/EA_VolmanPA/research/lines/vpa_lines.py` unless a
different file is named. Read-only sources never edited in place (charter :62, :218-219).

---

## 1. LINE-1 provenance (the seed we copy)

| file | SHA256 (re-pinned 2026-09-20 12:26 UTC, current tree) | role |
|---|---|---|
| `EA_VolmanPA/research/lines/vpa_lines.py` | `A4E5B23440B5A230940420D6A760916B0B581CE5F08A911CA14C5C6CFF4900E2` | causal armed-line engine to copy |
| `EA_VolmanPA/research/lines/test_vpa_lines.py` | `2022135F5412F065F85F4B057D913FAF929EC99038C41B02B39DACDDF2AFE38D` | causal test harness to copy |
| `EA_VolmanPA/research/lines/lines1_common.py` | `46E545BF81FF57CA2BB669D20A4F594E606A7C3F9C152D78DDD34CF4106E65C5` | shared inputs / seed 20260920 (`:33`) |
| `EA_VolmanPA/research/lines/lines1_run.py` | `9A30558B647CBF34230501028A5060A6FDFB9BC0B710C790E41804F7D72748B8` | audit/snapshot runner (not copied; reads DR1 burned cases) |

> **Re-pin note (2026-09-20 12:26 UTC).** Every LINE-1 citation in this file was re-verified with
> `Get-FileHash` + a read of the cited lines against the hashes above (current working tree). The
> LINE-1 lane is owned by VPA and changes outside PA-PRO: the revision originally quoted at R00 draft
> time (vpa_lines.py `B3A5E6B6…`, test `7127E18A…`, lines1_run `5E9DB533…`) no longer exists on disk,
> so the earlier line numbers were stale and have been corrected here. The citations below are valid
> ONLY for the hashes in this table. **If any LINE-1 file changes before the R01 freeze, every
> citation must be re-pinned again and the R01 copy SHAs recorded in `docs/PROVENANCE.md` and
> `rounds/R01/FREEZE.json`.**

> **Known LINE-1 defect — `_htf_align` look-ahead (binding note, Lead 2026-09-20).** The LINE-1
> lane identified a look-ahead defect in `LineEngine._htf_align` (`vpa_lines.py:785-805` in the
> 12:26 UTC revision; `:806-827` in the 19:23 revision) — the higher-timeframe alignment term of the
> v0 score. It is being fixed in
> LINE-1's own session (owned by that lane; PA-PRO never edits it). PA-PRO contract: **the
> perception baseline must copy the FIXED revision**, re-pin its SHA256 here and in
> `docs/PROVENANCE.md` at copy time, and add a prefix-invariance test for the score (append future
> bars -> the score at bar t must not change). If the fixed revision is not on disk at the R01
> freeze, PA-PRO must implement the HTF-alignment term causally itself or drop it from the v0
> score — never copy a leaking function.
> Observed drift: every LINE-1 file changed again after the 12:26 UTC re-pin — `vpa_lines.py` SHA256
> `519A8C5A516A11C10155135D386E46F1166342522F26AAECC7B8E2F16B0BA1BF` (mtime 19:23:45),
> `test_vpa_lines.py` `BA236DAC7FD053A0280C6B441F2C58234B0AA6DA68DADDCC58A4D41D98579DA8` and
> `lines1_run.py` `5FE3D315813168CE0ED98BE4561E29F2B163918A6D1AC1533ECEAF765DA84605` (both mtime
> 21:09, observed 2026-09-20 21:12 local). The table above is a verified snapshot, not the freeze
> revision; the R01 freeze MUST re-pin all four files (and fix any line-number drift the re-pin finds).

LINE-1 outputs already on disk (READ-ONLY reference, produced 2026-09-20): `PLAN/lines1/LINE_AUDIT.md`,
`ARMED_COUNTS.csv`, `LINE_AUDIT_CASES.csv`, `DR3_BARRIER_COINCIDENCE.csv`, `snapshots/`. LINE-1 remains
owned by the VPA lane; PA-PRO copies code, never edits it.

Key measured context (not an outcome): LINE-1's drawn lines coincide with the frozen DR3 micro-barriers
within 0.35xATR(M5) on 76.5% of 45,266 locks (`PLAN/lines1/LINE_AUDIT.md:50`, current regeneration),
and the on-chart set is capped at 8 lines (`vpa_lines.py:130`, prune `:869-889`). This says the engine
draws plausible lines; it says nothing about respect (that is the R01 physics run).

---

## 2. Object map — charter §2 L1 objects

Status legend: **EXISTS** = usable as-is from the copy; **PARTIAL** = primitive exists, spec-level
object needs a wrapper/threshold; **MISSING** = build new.

| # | charter object (`PA_PRO_CHARTER.md:54-60`) | status | LINE-1 symbol(s) | file:line | build note |
|---|---|---|---|---|---|
| O1 | multi-scale ATR zigzag swings (micro M5, meso H1, macro H4), prominence in ATR units | **PARTIAL** | `LineEngine._confirm_swings` fills `self.swings[k]` = list of `(idx, price, side, confirm_idx)` for `k in htf_lags`; `htf_lags=(3,6,12)`, `htf_weights` | `_confirm_swings` :436-450 (rule :445-448, confirmed-at :442-448); store init :308; constants :113-117; consumers `_htf_align` :785-805 | LINE-1 pivots are `±k`-bar extrema with **no ATR prominence, no alternation, no min-leg**; `k` are M5 bar lags labelled "M15/H1 proxies" (:113, :786), not resampled H1/H4. Build `struct/swings.py`: true multiscale ATR-zigzag — micro = M5 pivot k=3/6, meso = H1 bars (resample M1, charter :99) k=1/2, macro = H4 k=1/2; leg prominence = `min(leg_up, leg_down)/ATR14(scale) >= swing_min_prom_atr`; strict alternation; keep the `(idx, price, side, confirm_idx)` tuple so `_htf_align` still works. |
| O2 | horizontal zones clustered from swings, width ~0.2-0.25 x ATR14(H1), touches, respected tests, broken state, role flip, age | **PARTIAL** | `_seed_levels` creates one `level` line per confirmed lag-3 pivot; state via `_step_line`; `_state_at` returns `ArmedLine` | seeding :453-480; dedupe eps :464-474 (`level_dedupe_atr=0.30`, :68); touches :726-730 (`min_touch_sep=2`, :57); broken :733-744 (`level_break_atr=0.25` :66, `level_break_keep=48` :67); role flip `side_at` :244-249; age :831; seed TTL :757-759 (`level_seed_ttl=96` :64, `level_min_touches=2` :63) | LINE-1 levels are **single-anchor lines** with tolerance `level_eps_atr=0.35 x ATR14(M5)` (:61) — not zones clustered from several swings, and no "respected test" counter. Build `struct/zones.py` (caller: `events.py`, `score`): `zone_width_atr_h1=0.25`, cluster eps `0.5 x w`; band `[mean-w/2, mean+w/2]`; `touches` (first bar of each episode, reuse `min_touch_sep=2`); `n_respected` = touches with a >= 1.0 x ATR14(H1) move away within 48 bars and no close beyond the break threshold before the next touch; keep LINE-1's `broken`/role-flip semantics (only a close through by > `level_break_atr=0.25 x ATR14(M5)` breaks, :733-744). |
| O3 | reference levels PDH/PDL/**PDC** | **PARTIAL** | `_seed_pd` creates `pdh`/`pdl` at the first closed bar of the new day; `pd_max_age=576` | `_seed_pd` :381-389; `_update_day` :363-379; constant :109 | PDC missing. Build `struct/refs.py`: same `Line` container/shape, add prior-day **close** (the last close of the previous server day), kinds `pdh|pdl|pdc`. Clock change: LINE-1 keys the day on the UTC day of the bar open (`int(b["t"][t])//86400`, :365); PA-PRO uses the **server clock** (charter :82-83) via `lib/pa_clock.py` so the new day's bars are all closed after the server-midnight rollover. |
| O4 | Asia high/low | **MISSING** | — | `sess_windows` has only `eu (300,660)` and `us (690,1050)` :110; `_session_of` :391-396 | Build in `struct/refs.py`: add `asia` window (server-day minutes 00:00-05:00 UTC equivalent) and reuse `_update_session` mechanics (:398-417) to emit `asia_hi`/`asia_lo`; running extremes updated as bars close (running-extreme `set_geom` calls :413-417). |
| O5 | week high/low | **MISSING** | — | — | Build in `struct/refs.py`: running ISO-week high/low on the server clock, seeded at week rollover exactly like `_seed_pd` :381-389; kinds `wkhi`/`wklo`. |
| O6 | round 00/50 | **EXISTS** | `_update_rounds` seeds `round` lines on the `round_grid_pips=50` grid once price closes within `round_near_atr=8.0 x ATR14(M5)` | :419-434; constants :103-106 | Reuse as-is. 50 pips = 0.0050 (EURUSD) / 0.50 (USDJPY, `vpa_data.py:21`) = the 00/50 big-figure grid. Note LINE-1 never breaks `round` lines (`kind != "round"` guard :733); keep that. |
| O7 | trendlines through **>= 3** same-scale swings, no close violation | **PARTIAL** | `_seed_trendlines` builds lines from lag-3 pivots; `_tl_integrity` = no close beyond by > `tl_break_atr` | seeding :482-535 (pairs :495-496, slope bounds :501, touch count :504-508, integrity gate :510, creation :531-533); `_tl_integrity` :550-561; constants :80-90 | LINE-1 requires only `touches >= 2` (:508) and anchors from M5 lag-3 pivots only. Build: copy the machinery, set `tl_min_touches=3` and feed same-scale swings from O1 (trendline per micro/meso/macro scale); keep `tl_slope_min/max_atr` (:84-85) and the integrity scan :555. |
| O8 | channels | **MISSING** | — | — | Build `struct/patterns.py`: parallel line offset from a base trendline (O7) through the opposing same-scale swings; offset = median distance in ATR14(scale); kinds `chan_upper`/`chan_lower`, both carry the base `lid`. |
| O9 | boxes (two opposing zones, >= 2 touches each) | **PARTIAL** | `_window_update` seeds `box_top`/`box_bottom` when `aspect >= box_min_aspect=3.0`; `_pattern_dup` retires unbroken twins | :564-628 (aspect :591-595, triangle/flag branches :582-589; seeding :611-618; window meta :617); `_pattern_dup` :643-656; constants :73-78 | Creation is window-extreme based; ">= 2 touches per side" is **not enforced at creation**. Build: filter created box boundaries by `n_touches >= 2` once two more bars have closed (see lag table), or let the score term carry it; keep `box_break_atr=0.25` (:77). |
| O10 | flags (impulse then shallow counter-channel) | **EXISTS** | `_pole_dir` returns the impulse direction/amplitude before the window; `_window_update` seeds `flag_upper`/`flag_lower` when the tight window is small vs the pole (`theight <= flag_pole_frac x pole_amp`); seed carries `pole_dir`, `pole_amp_atr` meta | pole :675-693; flag test :585-589; seed :619-628 (meta :627); constants :93-97 | Reuse. |
| O11 | triangles (converging lines) | **EXISTS** | envelope fit `_envelope_fit` + converging test -> `tri_upper`/`tri_lower` | convergence test :582-584; seed :619-628; `_envelope_fit` :658-673; `tri_slope_eps_atr` :98 | Reuse. |
| O12 | double top/bottom **with neckline** | **PARTIAL** | represented only as a horizontal `level` through equal highs/lows | module docstring :20-21; test `test_double_top` `test_vpa_lines.py:209-224` | Neckline missing; no pattern object. Build `struct/patterns.py`: two same-scale swing extremes (O1) within `dt_eps = 0.25 x ATR14(H1)` with an intervening opposite swing; object `dt_`/`db_` carries `(extreme_lids, neckline_slope, neckline_intercept)`; neckline = line through the intervening swing (horizontal when its swing is single). |
| O13 | Volman buildup (compression adjacent to a zone) | **MISSING** | — | partial primitive: the flag tightness test inside `_window_update` :585-587 (`theight <= flag_max_height_atr * A`; constant :97) | Build `struct/buildup.py`: within the last `buildup_window=20` closed bars require >= `buildup_min_bars=8` consecutive bars with mean range <= `0.7 x ATR14(M5)` and the run fully within `0.75 x ATR14(H1)` of a live zone band; expose `run_bars`, `comp_ratio`, `zone_lid`. |
| O14 | trend state per scale (HH/HL vs LH/LL + EMA slope) | **MISSING** | — | inputs exist: EMA `_update_bar` :357-361; swings :436-450 | Build `struct/trend.py`: per scale from O1, label last completed swing pair HH/HL vs LH/LL, combine with `slope(EMA25, last 6 bars)` sign; output `trend[scale] in {-1,0,+1}` + the swing pair ids. **Lead decision E7 (2026-09-20): EMA25 is ALLOWED as a logged feature** even though the charter names EMA20/50 — it must be logged as an extra L3 feature in every evaluation's params, not substituted silently; the R01 prereg must declare it. |
| O15 | session/volatility context | **PARTIAL** | `_session_of` (eu/us) :391-396; ATR14(M5) `_update_bar` :346-356; `self.ema` :357-361 | session constants :110-111; `_update_session` :398-417 | No Asia (O4), no ATR percentile, no minutes-since-open. Build `struct/context.py`: `sess in {asia, eu, us, off}`, `min_since_sess_open`, `atr_m5`, `atr_h1`, `atr_pct_30d` = percentile rank of ATR14(M5) vs its own trailing 30 server days, `dow`, `hour_utc`. |

---

## 3. Event map — charter §2 L1 events (`PA_PRO_CHARTER.md:60-61`)

LINE-1 exposes **state** (touches, broken), not an event stream: nothing in `vpa_lines.py` or
`lines1_run.py` emits events (the runner only audits armed sets, `lines1_run.py:162-185`). All events
are built in `struct/events.py` on top of the primitives; each event is emitted at the **close** of the
bar where its condition first holds and carries `bar_idx` and `known_at == bar_idx`.

| # | charter event | status | primitive in LINE-1 | file:line | build note (v0 constants) |
|---|---|---|---|---|---|
| E1 | APPROACH | **MISSING** | distance query `line_near(t, level, tol)` (price pre-filter :905) | `line_near` :891-914 | `struct/events.py::approach(line, t)`: stateful episode — last away-bar `b0` with `d_close(b0) >= 1.0 x ATR14(H1)` inside `[t-24, t-1]`, no range∩zone between `b0` and `t`, `t` = first range∩zone bar. Full experiment definition: `rounds/R01/PHYSICS_PREREG_DRAFT.md` §3. |
| E2 | TOUCH | **PARTIAL** (state only) | `st["touch_idx"]` appends `j` when `touched` and `(j - st["last"]) >= min_touch_sep` | `_step_line` :726-730; `min_touch_sep` :57 | Emit `(lid, j)` when the touch list grows; use `_state_at` (:808-840) so the event is the same object the engine reports. |
| E3 | BREAK_CLOSE | **PARTIAL** (state only) | `st["broken"] = j` on first close beyond by > `brk` | :733-744; per-kind `brk` :696-707 (`level_break_atr=0.25` :66, `tl_break_atr=0.25` :87, `pattern_break_atr=0.25` :99) | Emit `(lid, j, side)`; `round` cannot break (:733). Structural break threshold stays 0.25 x ATR14(M5); **not** the physics barrier (m = 1.0 x ATR14(H1), prereg §4). |
| E4 | BREAK_FAIL (reclaim) | **MISSING** | after `st["broken"]` nothing tracks a return | `side_at` :244-249 flips side with price only | `struct/events.py`: after break at `b`, `BREAK_FAIL` = first close back inside the band at `r`, `b < r <= b + reclaim_max(96)`, with no new close beyond before `r`; carries `(lid, b, r)`. |
| E5 | RETEST | **MISSING** | — | — | After break at `b`: first touch episode at `r > b` (reuse E2 tolerance + `min_touch_sep`) with no intervening close beyond; side = the new role. Only emitted once per break. |
| E6 | LINE_TOUCH | **MISSING** as event | = E2 restricted to `kind in {"level","trendline"}` / horizontal kinds (:140) | `HORIZONTAL_KINDS` :140, `DIAGONAL_KINDS` :138 | Thin wrapper; same emission rule as E2. |
| E7 | LINE_BREAK | **MISSING** as event | = E3 restricted to `{"level","trendline"}` | `DIAGONAL_KINDS` :138, `HORIZONTAL_KINDS` :140 | Thin wrapper; note LINE-1 keeps a broken line alive for role reversal (`level_break_keep=48` :67, `tl_break_keep` :88). |
| E8 | BOX_BREAK | **PARTIAL** | E3 on `box_top`/`box_bottom`; pair via `meta["window"]` | :611-618 (:617 meta) | Event carries the box pair `(lid_top, lid_bottom)`; side = boundary broken. |
| E9 | FLAG_BREAK | **PARTIAL** | E3 on `flag_upper`/`flag_lower`; `meta["pole_dir"]`, `meta["pole_amp_atr"]` | :619-628 (:627 meta) | Event carries `pole_dir` (continuation direction). |
| E10 | TRIANGLE_BREAK | **PARTIAL** | E3 on `tri_upper`/`tri_lower` | :619-628 | Same as E9 without pole meta. |
| E11 | NECK_BREAK | **MISSING** | — | — | Depends on O12 neckline; E3 semantics on the neckline line, event carries the double-top/bottom id. |
| E12 | BUILDUP_AT_ZONE | **MISSING** | — | partial primitive :585-587 | Depends on O13; emitted when a compression run reaches `buildup_min_bars` adjacent to a live zone. |

---

## 4. Causal rules (confirmation lags) — binding

**Invariant:** for every object/event returned at decision bar `t`, every bar it is built from has
index `<= t`. There is no exception, including "for display". LINE-1 enforces this by construction
(single forward pass + recompute-from-`born` in `_state_at`, `vpa_lines.py:30-41`, :808-840) and by
tests: prefix invariance (`test_vpa_lines.py:253-267`) and no-future-access
(`test_vpa_lines.py:294-309`). PA-PRO keeps **both** tests on the copied engine and adds the same two
tests for every new module (mandatory in R01: `tests/test_struct_causal.py`).

| object | bars it may use | confirmation lag | first usable bar | LINE-1 enforcement |
|---|---|---|---|---|
| swing, scale `k` | closes/highs/lows `<= j+k` (needs `k` bars both sides) | `k` bars (micro k=3/6; meso/macro H1/H4 k) | `j + k` | appended with `confirm_idx = t = j+k` in `_confirm_swings` :445-448; `_htf_align` skips `conf > t` :798-799 |
| `level` (legacy, one pivot) | bars `<= t`, anchor `j = t-3` | 3 bars | `j + 3` (`created_idx = t`) | seed requires `conf == t` :459-461; `_new_line(..., created_idx=t)` :475-477 |
| legacy `trendline` (2 anchors) | bars `<= t`; integrity scan `ja+1..t` | last anchor + 3 | `>= jb + 3` | swings come only from `self.swings` filled `<= t` :489-490; `_tl_integrity` :555 scans closed bars only |
| zone O2 (new) | swings confirmed `<= t`, bars `<= t` | = last anchor swing lag + 0 | confirm bar of the last anchor | built on O1 `confirm_idx`; never on an unconfirmed swing |
| reference O3/O4/O5 | previous day/week/session bars, all closed | next bar after the rollover | first closed bar of the new period | `_update_day` :363-379 / `_seed_pd` :381-389; PA-PRO: server-clock rollover |
| `sess_hi`/`sess_lo` | session bars `<= t` | 0 (rolling extreme) | first session bar (its own close) | `_update_session` :398-417 |
| `round` O6 | bars `<= t` | 0 | first bar whose close is within `round_near_atr x ATR14(M5)` of a grid price | `_update_rounds` :419-434 |
| box/flag/triangle O9-O11 | window `[s..t]`, swings confirmed `<= t` | 0 for the window; boundaries need >= 2 swings/side confirmed (`_envelope_fit` :658-673) | `t` in the engine; PA-PRO box post-filter `n_touches>=2` waits 2 extra bars | `_window_update` is driven from the closed-bar pass `run()` :917-933 (`_window_update(t)` :924); `_envelope_fit` filters `conf <= t` :665-668 |
| double top/bottom + neckline O12 (new) | swings confirmed `<= t` | = confirm bar of the 2nd extreme (+ `dt_confirm_bars`=1) | `second_confirm + 1` | build; same invariant test |
| buildup O13 (new) | last `buildup_window=20` closed bars | 0 | `t` (run counted on closed bars) | build |
| trend state O14 (new) | confirmed swings + EMA(t) | = swing lags | `t` | build |
| score v0 §5 | any field of the above at `t` | = object availability | `t` | build |
| role flip O2 (state) | break bar `b`, retest bar `r > b`, flip close `f >= r` | flip only after `BREAK_CLOSE` **and** `RETEST` | `f` | build; rule stated below |

**Role-flip rule (binding).** Side never flips on a wick or a single close-through. A role flip is
usable only in this order: `BREAK_CLOSE(b)` -> `RETEST(r > b)` -> first close `f >= r` that stays
beyond the break threshold (the retest fails to reclaim, i.e. the zone now holds in its new role)
= `FLIP_CONFIRMED(f)`. If instead a `BREAK_FAIL` (E4: close back inside the band, `<= b + 96`) happens
before `f`, no flip is confirmed and the zone keeps its pre-break role. Until `f`, the zone is treated as
broken (`broken_idx = b`) with its pre-break role.

---

## 5. Strength score v0 (FROZEN once R01 starts)

One formula, evaluated at the event bar `t` for a zone `Z`; all inputs are fields of objects that are
causally available at `t` (§4). Weights are pre-declared and sum to 1.00. `strength(Z,t) = 100 * S`,
`S in [0,1]`.

| term | weight | definition (all causal at `t`) |
|---|---|---|
| `T_touch` | 0.30 | `min(1, n_touches / 4)` — touch episodes to date (E2, `min_touch_sep=2`) |
| `T_resp` | 0.20 | `min(1, n_respected / 3)` — touches that produced a `>= 1.0 x ATR14(H1)` move away within 48 bars with no close beyond the break threshold before the next touch (O2) |
| `T_rec` | 0.15 | `exp(-(t - last_touch_idx) / 288)` — recency of the last touch (288 M5 bars = 1 server day); `T_rec = 0` when the zone has no touch yet |
| `T_age` | 0.10 | `min(1, age_bars / 288)` — established age from the zone's confirming swing |
| `T_scale` | 0.10 | 0.4 micro / 0.7 meso / 1.0 macro — strongest anchor scale in the cluster (O1); zones not built from swings take a fixed convention: PDH/PDL/PDC/week = 1.0, session/Asia = 0.7, round = 0.7 |
| `T_role` | 0.05 | 1.0 if `FLIP_CONFIRMED` happened before `t`, else 0 (O2 role rule) |
| `T_conf` | 0.05 | `min(1, (n_ref + n_round) / 2)` — `n_ref` = distinct reference levels (PDH/PDL/PDC/Asia/week) whose `+-w/2` band intersects `Z`; `n_round` = 1 if any 00/50 grid price's band intersects `Z` |
| `T_vol` | 0.05 | `min(1, median(tv over the last 6 closed bars) / median(tv over the last 288 closed bars))` — tick-volume character of the approach; if the symbol's parquet has no `tv` (`02. AlphaFactory/lab/cache/<SYM>_M1_2010_2026.parquet`, column `tv` exists for EURUSD), `T_vol = 0` for all zones of that symbol (constant, so within-symbol ranking is unaffected — stated in advance) |

`S = 0.30*T_touch + 0.20*T_resp + 0.15*T_rec + 0.10*T_age + 0.10*T_scale + 0.05*T_role + 0.05*T_conf + 0.05*T_vol`

Notes:
- LINE-1's own score (`score = 0.35*touch + 0.20*age + 0.25*vis + 0.20*htf`, `vpa_lines.py:120-123`,
  `_score_parts` :769-783) stays what it is — chart hygiene / arming. **v0 strength is a separate number** used for
  physics stratification; we borrow its touch/age ideas but not its weights.
- **Tercile mapping (physics run):** rank all FRESH APPROACH events of the pooled DESIGN event table by
  `strength` at their event bar; boundaries `q33`, `q67` are computed on the **event table only, before
  any outcome join**, recorded in `rounds/R01/FREEZE.json`, and never re-computed after outcomes exist.
  Primary terciles are pooled across core symbols; per-symbol terciles are a secondary report.
- **Freeze:** weights and definitions are frozen in R01 before outcomes; any change afterwards is a new
  calibration trial in the ledger (charter :121-122), calibrated on DESIGN physics only.

---

## 6. Copy vs rebuild

Charter seed rule (:62): "the LINE-1 module … copy, never edit in place."

**Copy (verbatim, `docs/PROVENANCE.md` records source path + SHA256):**
- `EA_VolmanPA/research/lines/vpa_lines.py` -> `PA_Pro/struct/line_engine.py`
- `EA_VolmanPA/research/lines/test_vpa_lines.py` -> `PA_Pro/tests/test_line_engine.py`
- `lines1_common.py`: only the seed constant (`:33`) and `min_touch_sep` convention are re-declared in
  `struct/config.py`; the file itself is not copied (it reads DR1 burned cases, irrelevant to PA-PRO).
- The copy is PA-PRO-owned after copying: threshold updates (e.g. `tl_min_touches=3`, box touch
  filter) happen in the copy, and the source file stays untouched.

**Rebuild (new modules; every function must have a caller in `struct/pa_struct.py`):**

```
lib/pa_clock.py     server offset +2/+3 EU DST, server day/week keys  (reuse semantics of
                    vpa_random_baseline.eu_server_offset_hours:60-70, mod-1440 fix vpa_data.py:60)
lib/pa_data.py      M5 + H1/H4 resample, tv/sp columns, DESIGN-only guard, suspect drop
lib/pa_slots.py     2-process lock, OMP/MKL/OPENBLAS=4, BelowNormal (charter :164-165)
struct/line_engine.py  copy of vpa_lines.py
struct/swings.py       O1 ATR-zigzag multi-scale
struct/zones.py        O2 zones (cluster/width/respected/broken/role/age)
struct/refs.py         O3/O4/O5 plus O6 wiring
struct/patterns.py     O8 channels, O12 double top/bottom + neckline
struct/buildup.py      O13
struct/trend.py        O14
struct/context.py      O15
struct/events.py       E1-E12 stream
struct/pa_struct.py    facade: objects_at(t), events_at(t)  (only public entry)
tests/test_struct_causal.py  prefix invariance + no-future-access + golden event-hash per module
```

**Provenance rule:** every copied/reused number keeps its source citation (this file); every file in
`struct/` gets an entry in `docs/PROVENANCE.md` with its source path + SHA256 at copy time.
