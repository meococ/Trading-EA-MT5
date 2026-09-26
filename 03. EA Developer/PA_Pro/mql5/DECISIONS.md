# DECISIONS — PA-PRO MQL5 lane (judgement calls, dated)

## D1 — Compile unit layout (2026-09-21)
alpha.ps1's EA contract resolves `<Name>` -> `03. EA Developer/<Name>/<Name>.mq5`
(tools/ea_contract.ps1:35-42). The charter forbids writes outside
`03. EA Developer/PA_Pro/`. Both hold with: `PA_Pro/PA_Pro.mq5` = one-line shim
(`#include "mql5\\PA_Pro_EA.mq5"`), compiled as `alpha.ps1 compile "PA_Pro"`;
the real EA lives at `PA_Pro/mql5/PA_Pro_EA.mq5` as mandated. EX5 = PA_Pro.ex5.

## D2 — Zone state = replay semantics, two tracks (2026-09-21, Lead)
`ZoneGen.views_at`/`state_at` replay `_step_zone` over EVERY bar in
[born_idx, t]; the live pass (`_step_all`) is an approximation (steps only
near-band/pending/warm zones; misses gap-bar breaks and late reclaims —
SF01 DECISIONS.md D4). The MQL5 port must therefore keep, per zone:
- `st`  = pass state, stepped only when the Python prefilter would step it
  (near-band scan on the 256-bar `_sorted` snapshot + `_pending` + `_warm`),
  carrying lifecycle side effects (end_idx shorten on break, retire, counters);
- `stx` = shadow read state, stepped over every bar in [born_idx, t]
  (`_replaying` semantics: no side effects), with a backfill loop
  [born..t-1] when a zone is created at t > born_idx — exactly the proven
  pattern of `families/sf_ctx.py` `run_pass` (:127-208), which is unit-tested
  bit-equal against `run()` + `views_at`.
Reference for any ambiguity: sf_ctx.py, not my own derivation. Zone VISIBILITY
at t uses pass-produced `end_idx`; strength/fresh/touches use `stx`.

## D3 — H1 bars aggregated from the same M5 array (2026-09-21)
Python resamples M1->H1 keeping only complete 60-M1 buckets. On the MQL5 side
the identical object is "12 complete M5 bars per server-hour bucket" — so the
EA/parity path builds H1 by grouping its own M5 series (12 bars per t//3600
bucket), never CopyRates(PERIOD_H1) (different feed = data diff, not logic).

## D4 — No NaN arithmetic in MQL5 (2026-09-21)
Python signals invalid ATR/refs with NaN + `a != a`. MQL5 uses parallel
`*_ok` bool arrays (VPA_Core pattern m_atr_ok). Sentinel values: None -> -1
for bar indices, 0 for side (Python `or +1` maps to `side!=0?side:+1`).

## D5 — SIGNAL_ONLY proof (2026-09-21)
Every order-API call lives inside `PaExecutePlan()` in PA_Trade.mqh whose
first statement is `if(signal_only) return false;`. Static proof:
mql5/tests/test_signal_only.py greps all trade-API tokens and asserts they
occur only inside that function body. Also documented for grep review.

## D6 — Journal schema (2026-09-21)
"Columns identical to the Python side" = the `pa_fill.simulate()` record keys
(pa_fill.py:324-335) — the referee's canonical trade record — prefixed with
signal-phase columns (bar, setup, zone, strength, decision). Fill-phase
fields stay empty while SIGNAL_ONLY (they cannot occur). Rationale: no other
Python journal schema exists; simulate() IS the record contract.

## D7 — Parity harness shape (2026-09-21)
alpha.ps1 can only compile `03. EA Developer/<Name>/<Name>.mq5`. Two export
paths ship, both over the SAME engine code:
- `03. EA Developer/PA_Pro_Parity/PA_Pro_Parity.mq5` — a standalone Script
  package (`alpha.ps1 compile "PA_Pro_Parity"` -> 0/0, 69498 B) that loads
  M5 history, steps the engine, and writes the armed-view CSV. Quoted
  `..\PA_Pro\mql5\*.mqh` includes resolve relative-to-file under the
  alpha.ps1 "local" include rule — no writes outside the two package dirs.
- `InpExportZones` input mode inside the EA (same CSV via CPaExport).
Python side: `mql5/parity/export_zones.py` (pa_slots-guarded) emits the
identical schema through `sf_ctx.run_pass` on `pa_data.load_m1(DESIGN +
30d warmup)`; `compare_parity.py` joins on `(t_epoch, gen)` — bar indices
never cross the wire, only server epochs (data-window agnostic).
Comparator self-check on the Python file: 2,061,858 keys, 100% identical.

## D8 — Live-bar context extension = PushBar watermarks (2026-09-21)
OnTick used to append to `ctx.b` only — `h1_idx`/`atr_m5`/pivot caches were
Init-sized and would index out of range on the first live bar.  `PushBar`
now extends every derived array causally and O(1): H1 bucket finalize on
hour-key change (same 12-aligned-slots rule as BuildH1), Wilder ATR
recursion in the Python form `a*prev + (1-a)*tr` (bit-exact), h1_idx
bisect, pivot emission watermarks (`piv3_scan`, `h1raw_scan`, `h1p2_pend`
FIFO — a pivot whose m5_confirm is still future correctly blocks the tail
since confirm times are non-decreasing).  Proof: `PaRunCtxSelfTest`
(InpSelfTest mode) Inits on N-1500 bars + PushBars the rest, compares
every derived array cell-for-cell against a fresh Init on all N.

## D9 — Closed-bars-only book + live catch-up (2026-09-21)
`CopyRates(shift=0)` returns the still-FORMING bar as r[0]; Init'ing ctx on
it poisoned the book (partial OHLC stepped as if closed, then the same bar
re-pushed finalized -> duplicated timestamp, every downstream index off by
one).  Both loaders now copy from shift 1 (closed bars only); OnInit steps
all n loaded bars; OnTick pushes every closed bar with `t > g_last_pushed`
(CopyRates shift 1..16, oldest->newest) — the catch-up loop also covers a
bar that closes while the Init step loop is still running.  Parity script
`PA_Pro_Parity.mq5` fixed identically (Python exporter only ever sees
closed M5 bars).

## D10 — Generator streams must follow live pivot growth (2026-09-21)
Three generators materialize pivot-derived streams:
- `line1_cluster` cached `m_npiv=ctx.Pivots3()` at Prepare -> new live
  pivots never consumed.  Now refreshes `m_npiv` each OnBar (O(1)).
- `fractal_h1` qualified `ctx.h1p2` into `piv[]` once at Prepare.  Now
  `Qualify(i)`/`SyncPivots()` with an `m_src` cursor over ctx.h1p2.
- `kde_swing` qualified both streams once at Prepare.  Same pattern:
  `QualifyM5/QualifyH1` + `SyncSamples()` + `m5_src`/`h1_src` cursors.
Python re-run over an extended book sees these pivots, so the live engine
must too — qualification inputs (prom window, ATR at confirm) are all
<= confirm-bar causal, so lazy qualification is bit-identical to batch.
Proof upgraded: `PaRunZoneSelfTest` runs TWO full perceptions on real M5
(Init k0 -> PushBar+StepBar vs Init n -> StepBar) and diffs armed views
(lo/hi/strength/touches/respected/broken/flip/approach/quality) on every
pushed bar, every generator.

## D11 — Salience hook, no score (LEAD RULINGS R1 item 3, 2026-09-21)
SF02 will define a per-zone SALIENCE score and arm only the top 1-2 zones
per side.  To make that a drop-in rather than a refactor:
- `PaZoneView.salience` — populated by the new virtual
  `CPaGenBase::SalienceOf(z,t,strength)`, which returns `strength` until
  SF02 defines the real score (override = injection point).
- `cfg_arm_topk` (default 0 = OFF) on every generator + `InpArmTopK` on
  both the EA and the parity script.  When >0 the arm pass re-sorts by
  (-salience, zid) and keeps at most k zones per side of price
  (center vs close: > = above/resistance, < = below/support) inside the
  existing near/dedupe/cap funnel.  At 0 the armed set is bit-identical
  to Python `arm_zones` — parity output unaffected.
- NOT exported to the parity CSV (Python has no such column).
F1-F6 stay stubs: SF01 closed 0/6 (LEAD R1) — no setup logic ported until
the SF lane reports a survivor.

## D12 — SF02 salience score implemented (2026-09-21)
SF02's AUTOPSY_PLAN.md A3 declared the a-priori score, satisfying R1's
"do not implement until SF02 defines one".  `cfg_salience_mode` selects:
- 0 (default, parity-safe): salience := strength;
- 1: `1.0*n_respected + 1.0*pivot_conf + 0.5*round_conf
     - 0.5*(width/ATR_H1) + 0.25*log(1+age_bars/96)`
  where pivot_conf = confirmed +-2 H1 or H4 pivot within 0.5*ATR_H1 of a
  zone edge, round_conf = zone mid within 0.25*ATR_H1 of a 25-pip
  gridline, age_bars = t - born_idx.  Implementation lives in
  `CPaGenCtx::SalienceOf` (the class that owns ctx).
- New `CPaCtx` H4 track (BuildH4/H4Finalize/H4Pivots2/PivotNear):
  complete 48-M5-bar buckets per `pa_data.resample` (240 M1), raw +-2
  pivot table with `h4raw_scan` watermark; confirmation at bar t iff
  `h4_close[conf] <= b[t].t+300` — the h1p2 mapping rule.  H4 machinery
  exists ONLY for salience; with mode 0 nothing consumes it, so parity
  is untouched.
- `InpSalienceMode` (default 0) on the EA and the parity script.
- `PaRunZoneSelfTest` gained a second pass (mode 1 + topk 2) so the H4
  incremental-vs-batch path is proven cell-for-cell alongside the rest.
If SF02 revises the formula, `SalienceOf` is the single edit point.

- **D13** (2026-09-21 ~13:20 local) — Perception wire format = CSV, not
  JSON, on the MT5 side. `schema/perception_v1.json` exists now; it
  uses bar INDICES and JSONL shape. MQL5 keeps a flat-CSV projection
  (`perception_csv_v1`: `[bar_t,]id,type,state,role,t_birth,t1,t2,p1,p2,
  letter,side,why`, all times = server epochs). `tools/jsonl_to_csv.py`
  does JSONL->CSV with idx->epoch via `t_cet` (+1h, perception D2);
  MQL5 never parses JSON. Rationale: epoch stays the join key, importer
  stays trivial, and the same CSV serves viewer + parity comparator.
  `id` is a STRING per schema; `STAND_ASIDE` kept as a provisional
  pseudo-type for `stand_aside[]` codes. Aliases tolerated on
  state/role so pre-freeze mock files still parse.
