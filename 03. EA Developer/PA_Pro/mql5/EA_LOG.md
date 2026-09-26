# PA-PRO MQL5 EA lane — work log (append-only)

## SUMMARY
- Lane: PA-PRO EA build (Owner mandate 2026-09-21, resumed after 02:32Z cut).
- NEW DIRECTION (LEAD R2, 06:01Z): drawing layer rebuilt on Volman
  grammar per docs/perception/VOLMAN_PERCEPTION_SPEC_v1.md. PA_Zones is
  frozen. Queue E1 draw grammar -> E2 snapshot viewer -> E3
  PA_Perception skeleton -> E4 HUONG_DAN -> E5 PORT_PLAN (no engine
  port before P-FREEZE).
- Done (zone era): all components — PA_Types/PA_Clock (1372 clock vectors PASS);
  PA_Zones.mqh ~2400 ln (2-track st/sx replay per sf_ctx D4, 6 gens,
  incremental PushBar for live bars — batch==incremental self-test);
  PA_Session; PA_Risk (0.5%/4%/8%); PA_Trade (plan + gated PaExecutePlan);
  PA_Setups (F1/F2 stubs); PA_Journal (pa_fill.simulate 23-col CSV);
  PA_Visual; PA_Export; PA_Pro_EA.mq5 wired end-to-end; PA_Pro_Parity
  script package; HUONG_DAN.md; contract JSON.
- Compile: PASS 0/0 — PA_Pro.ex5 131262 B; PA_Pro_Parity.ex5 76464 B.
- Salience: SF02 score IMPLEMENTED (D12, AUTOPSY_PLAN A3 formula) behind
  InpSalienceMode (default 0 = strength; parity untouched); H4 bucket +
  pivot track added to CPaCtx; self-test pass 2 proves inc-vs-batch.
- Tests: session mirror PASS; signal-only static proof PASS 0 violations.
- Parity: Python side DONE — out/zones_EURUSD_py.csv 6,170,124 rows via
  sf_ctx.run_pass on DESIGN+30d; comparator verified (self-check 100%);
  MQL5 side READY-TO-RUN (PA_Pro_Parity script or EA InpExportZones;
  this lane cannot launch a terminal). RUNBOOK.md = one-command steps.
- Key ruling: reads = views_at replay [born..t]; 2 tracks + creation
  backfill (sf_ctx.py:127-208, SF01 D4). DECISIONS.md D1-D11.
- LEAD RULINGS R1 (04:32Z) read + applied: D1-D7 accepted; SF01 = 0/6
  survivors -> F1/F2 stay stubs (no setup ports until an SF survivor);
  salience hook shipped (PaZoneView.salience + SalienceOf virtual +
  cfg_arm_topk/InpArmTopK, default OFF -> parity unchanged).
- Review fixes (2026-09-21 later): forming-bar leak into ctx (CopyRates
  shift 0 -> 1, both loaders; OnTick = catch-up loop t>g_last_pushed);
  live pivot-stream staleness in line1/fractal/kde (m_npiv refresh,
  SyncPivots/SyncSamples cursors); StepZone ATR guard !(A>0) matching
  Python. New proof: PaRunZoneSelfTest (zone-level incremental==batch).
- Perception direction (R2) status: E1-E5 DONE —
  PA_Perception.mqh (schema-v1 aligned: string ids, schema state/role
  enums, side field; CSV wire = perception_csv_v1, optional leading
  bar_t column = per-bar parity mode); PA_Draw.mqh (12-type grammar,
  dark/light palettes, edge bands +-tol, budget <=5/hard cap 8,
  PAV_ prefix wiped on redraw/deinit); PA_Pro_View indicator package
  (view-only, polls MQL5\Files CSV, draws objects overlapping the
  visible window + EMA25 buffer) compiles 0/0 = 33262 B;
  tools/mock_snapshot.py (15 objects, all types, real 2019-03-04 week);
  tools/jsonl_to_csv.py (schema JSONL -> CSV v1 projector, t_cet-based
  idx->epoch map, smoke-tested); parity/compare_perception.py (per-bar
  id-keyed diff, PASS >= 99.5% bars); VIEWER_RUNBOOK.md; HUONG_DAN.md
  viewer section; PORT_PLAN.md (state machines + vectors + parity plan,
  P-FREEZE gate). test_signal_only extended to scan PA_Pro_View: PASS.
- Open issues: PERCEPTION_API.md / PORT_NOTES_MQL5.md not yet emitted
  by the perception lane — re-read on arrival; live MT5 visual check
  pending Owner (VIEWER_RUNBOOK.md); zone-era MQL5 parity leg still
  pending Owner/Lead terminal run.
- Next: Owner/Lead runs the MQL5 export leg -> compare_parity verdict;
  Owner runs PA_Pro_View per VIEWER_RUNBOOK.md.

## LOG
- 02:15Z recon complete; PA_Types.mqh + PA_Clock.mqh written (box cut at 02:32Z).
- resume: read SF01 DECISIONS D4 + families/sf_ctx.py; created this log and
  DECISIONS.md; starting PA_Zones.mqh.
- PA_Zones.mqh written (2-track st/sx replay per sf_ctx:127-208; all six
  generators cross-checked line-by-line vs their .py sources); fixed
  MQL5 issues (array-by-ref, member-ref state -> struct copy, GetPointer).
  First compile: 0 errors / 0 warnings, fresh ex5.
- Next: PA_Session.mqh (windows + Friday flat) + session test script.
- PA_Session.mqh + clock_vectors (1372) + test_session_mirror.py PASS;
  compile 0/0 (77656 B). PA_Risk/Trade/Setups/Journal/Visual/Export +
  full EA wiring; test_signal_only.py PASS 0 violations; compile 0/0
  (112688 B).
- CPaCtx.PushBar incremental extension (live-bar OOB fix): H1 finalize on
  hour boundary, Wilder a*prev+(1-a)*tr bit-exact, pivot watermarks;
  PaRunCtxSelfTest proves batch==incremental. PA_Pro_Parity script package
  compiles 0/0 (69498 B). Python export_zones.py ran under pa_slots:
  zones_EURUSD_py.csv 6,170,124 armed rows; compare_parity self-check
  100% identical. PA_Pro compile 0/0 (120570 B). Parity MQL5 side:
  READY-TO-RUN (no terminal in this lane).
- deep-review pass (continuation): verified all 6 gen NAME/SCALE/QUAL_REF
  vs Python registry; KDE per-zone meso/micro scale + link/absorb logic
  line-by-line equal.  Found+fixed: (a) forming-bar leak — loaders now
  CopyRates shift 1, OnInit steps n bars, OnTick catch-up pushes all
  closed bars t>g_last_pushed (DECISIONS D9); (b) stale pivot streams in
  live mode — line1 m_npiv refresh, fractal SyncPivots, kde SyncSamples
  (D10); (c) StepZone guard !(A>0) matching Python `A<=0` early-return.
  Added PaRunZoneSelfTest (armed-view diff, incremental vs batch engine).
  Recompiled: PA_Pro 122732 B 0/0; PA_Pro_Parity 69066 B 0/0.
- verified CPaRefs vs refs.py field-by-field (pdh carry-forward R02-A F3,
  Monday wk rollover, asia window run/done semantics, confluence, round
  grid) + RoundNear grid<=0 guard added; verified _strength/views_at/
  arm_zones/_step_all/_step_zone/confirmed_pivots/h1_pivots/wilder_atr/
  h1_align all line-by-line identical; profile_va + kde_swing verified.
  LEAD_RULINGS.md appeared -> R1 applied: salience hook (D11). Compiles:
  PA_Pro 122426 B 0/0; PA_Pro_Parity 72176 B 0/0.
- export-path verify: Python cb rows = arm_zones(near-3.5A set) which is
  provably identical to arm_zones(all views) (2.0<3.5 near bound, dedupe
  only sees armed centers) — MQL5 BarZones(ViewsAt arm=true) equivalent.
  CSV columns/sentinels/rounding match byte-format (%.6f, %.*f dg, -1).
  RoundNear now returns bool (grid<=0 -> no publish, refs.py parity);
  journal veto rows match the 5-key Python shape (order_type/reason
  empty). Recompiled: PA_Pro 123664 B 0/0; PA_Pro_Parity 70940 B 0/0.
- comparator hardened: verdict is strict (single-side keys = misses),
  plus new overlap-% diagnostic and --e0/--e1 epoch bounds for the
  shallower-MQL5-history case (zone state needs >=~30d shared warmup;
  RUNBOOK documents the margin rule). Py export span measured:
  444,916 epochs, 2015-12-02..2021-12-31.
- SF02 defined its a-priori SALIENCE score (rounds/SF02/AUTOPSY_PLAN.md
  A3) -> R1's gate satisfied, so D12 implements it: cfg_salience_mode /
  InpSalienceMode (default 0 = strength, parity unchanged); CPaCtx grew
  an H4 bucket+ pivot track (48-bar rule per pa_data.resample) feeding
  PivotNear; SalienceOf lives in CPaGenCtx. PaRunZoneSelfTest pass 2
  (mode1+topk2) proves inc-vs-batch incl. salience; PaRunCtxSelfTest
  now also diffs h4 buckets + h4raw2 rows cell-for-cell. Compiles 0/0:
  PA_Pro 131262 B; PA_Pro_Parity 76464 B.
- 13:30 local — R2 queue E1-E5 closed. schema/perception_v1.json landed
  mid-session -> PA_Perception.mqh realigned to it (D13): string ids,
  schema state/role enums, side column, CSV v1 wire
  ([bar_t,]id,type,state,role,t_birth,t1,t2,p1,p2,letter,side,why).
  PA_Pro_View gained OnTimer file polling (weekend charts get no
  ticks), InpDrawEma25/InpPollMs inputs; runbook + HUONG_DAN aligned.
  tools/jsonl_to_csv.py projects JSONL snapshots -> CSV v1 (idx->epoch
  via t_cet +1h). compare_perception.py = per-bar id-keyed diff.
  Compiles: PA_Pro_View 0/0 (33236 B). Tests: signal_only PASS
  (now scans the viewer package), session_mirror 1372/1372 PASS.
  PENDING (Owner): run PA_Pro_View per VIEWER_RUNBOOK.md; zone-era
  parity leg unchanged.
