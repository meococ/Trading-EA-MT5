# Hot Cache — Current State

Updated: 2026-09-17. **Cache, không phải authority** — `01. GOAL/GOAL.md`
thắng mọi con số ở đây.

## Shelf

`03. EA Developer/` (sau cleanup 2026-09-17): `EA_SonicR_PVSRA` (host, không
bắt buộc), `EA_ExecutionKernelHarness`, `EA_LiquiditySweep`, `_Shared/`
(Execution/MarketData/Telemetry), 4 indicator `iCustom` +
`TB_Smart_Money_Concept_2026.mq5` ở root. Fleet mint ~410 probes **đã xóa**
theo lệnh Owner — verdict giữ ở `CANDIDATE_REGISTRY.jsonl`.

## Active direction (Owner 2026-09-17) — KILLED 2026-09-18

**XAUUSD session-sweep scalp** = `EA_LiquiditySweep` sleeve
`HYP-LSWEEP-XAU-M5-001`. Governed Model 0 run `20260918_002905`
(1970→2026.09.10, HQ 98%): **N=136, PF 0.556, net -950 USD, cadence
~0.12/tuần** → KILLED_AT_MODEL_0 (cadence + economics, cả 2 frozen kill
criteria). Cost PF x1/x1.5/x2 = 0.48/0.44/0.41; robustness 0/7; PASS:
nonrepaint, DD 9.9%, MC p95 11.3%, overnight/weekend 0/0. Mechanism hiếm
một cách cấu trúc (~6 sweep/năm) trên cả EUR lẫn XAU — không burn revision.

**Session open-drive ORB** = `EA_SessionDrive` (minted 2026-09-18, cả 2
sleeve đều KILLED_AT_MODEL_0 cùng ngày):

- `HYP-SDRIVE-GBP-M5-001` run `20260918_080056` (1999→2026.09.11): 21,099
  signals ~14.6/tuần (đúng probe) nhưng contract safety veto 98.6%
  (DD-lock 14,354 + spread 6,248) → 287 trades, PF 0.778 gross / 0.717
  cost-x1. Cadence 0.20/tuần. Cả 2 kill criteria.
- `HYP-SDRIVE-JPY-M5-001` run `20260918_081608` (1999→2026.09.11, HQ 99%):
  21,049 signals, veto 99.1% (DD-lock 12,402 + spread 7,924) → 180 trades,
  PF 0.660 gross / 0.585 cost-x1. Cadence 0.125/tuần. **SDRIVE family
  falsified trên cả 2 symbol** — per prereg, không còn cell nào legal.

Bài học chung: signal rate ~15/tuần đạt được, nhưng contract DD-lock 10%
latch vĩnh viễn sau drawdown đầu + spread filter chặn ~99% — và executed
trades PF 0.66–0.78 nên edge cũng âm kể cả khi mở khóa.

## Falsification board tổng (2026-09-18) — joint-constraint rỗng

19 governed kills (era-2 15 + LSW-EUR + LSW-XAU + SDRIVE-GBP/JPY) + shelf
88 strategies + **4 probe campaigns Stage-0** → **bimodal**: PF>1.3 luôn
rare-event; cadence 10–40/tuần luôn PF 0.5–0.95. Vùng giao trên MQ-Demo
= **rỗng**.

### Probe campaigns 2026-09-18 (tools/probe_*.py)

- **Cross-asset lead-lag M5**: same-bar ρ đúng (EUR-GBP +0.78) nhưng
  lag-1 |ρ| ≤ 0.013 mọi cặp → contemporaneous common factor, không lag.
  DEAD rẻ. (probe_cross_asset_leadlag.py)
- **Session-flow legs** (momentum / handover-fade / fix-fade, wide
  geometry hold-to-session-end): chỉ ASIA last-hour-extreme
  close-pierce fade dương thật (~+2.4p delayed / +6.7p immediate entry,
  ~3/wk); momentum NY âm → fade hướng đó cũng chỉ ~0 sau cost.
  (probe_session_flow.py)
- **Lookahead artifact lesson**: `probe_us_extreme_fade.py` bản đầu lọc
  `day_key(x) <= dk` thay vì `== dk-1` → level "prior NY extreme" chứa
  cả NY session tương lai cùng ngày → fake edge +8~19p (t=4.4–7.2). Đã
  fix + ghi chú trong file. Probe boundary map đúng
  (probe_boundary_map.py, probe_close_pierce.py) → không edge nào đủ
  frequency. **Luôn kiểm tra level chỉ chứa bar quá khứ.**
- **Cost math định hướng**: MQ-Demo RT ≈ $11–36/lot → M5 tight stop
  (~$60–80/lot risk) mất ~45% gross winner, cần gross PF ~1.6+ (bất khả
  thi); wide stop ≥25 pips mới giảm cost drag xuống ~5–10%. Mọi family
  đã chết đều tight-geometry — đây là lý do cấu trúc, không phải param.
- **Residual anomaly duy nhất** (lookahead-free): ASIA open (00:00 GMT)
  close-pierce của previous-hour extreme → fade về session end. GBP
  +2.4~6.7p t~2.3–6.2, EUR +2.1~4.7p, ~2.5–3.5/wk. Dưới band 10–40 —
  chỉ dùng được nếu Owner nới cadence (low-frequency sleeve).

## Pipeline gotchas (2026-09-18, đã fix trong tools)

- `measure_cost_evidence.py` giờ emit cả 3 CSV (spread_ticks,
  slippage_quotes, commission_proxy) + JSON; `--end-utc` pin window vào
  trong run window — `build_verified_cost_artifact.py` reject row ngoài
  `[from..to]`.
- Slippage CSV phải **non-overlap theo side** (next reference >= prev
  future) — chain `i = j + 4` trong tool.
- Isolate terminal **liveupdate build giữa run** (6192→6198→6201; bump
  6201 đã xảy 2 lần ngay giữa run USDJPY) → server_fingerprint report ≠
  packet. Fix: re-run `measure_cost_evidence.py` để refresh `ident`
  (packet builder đọc identity từ spread evidence JSON, không attach
  trực tiếp), rebuild packet, rerun.
- `coverage_mode`: sentinel `1970.01.01`/`all_available_asof` bị HQ gate
  reject (HQ 82 trên build 6198+). Dùng `verified_m1_asof` + real M1
  boundary (GBP=1999.01.01). Symbol mới chưa có identity → 1 discovery
  run lấy report identity (post-run fingerprint check chỉ verify sau
  run, không chặn pre-run), rồi rebuild packet.
- USDJPY M1 local `.hcc` chỉ có 2022+ nhưng tester **tự sync full 1999+**
  từ server khi request window rộng (bars 2,051,420 ≈ GBP).
- `ALPHAFACTORY_FORCE_NOGIT=1` bắt buộc cho `ea_research_loop.ps1` khi repo
  có .git thật (packet ghi NOGIT provenance).

## Era-2 screen result (không lặp lại)

26 hypothesis fleet-mint → 25 `KILLED_AT_MODEL_0` (PF 0.7–0.9, cadence qua
được nhưng gross-negative), 1 pending (`HYP-ICHITN-GB-M5-001`). Probe
indicator đơn giản trên M5/M15 = không edge. Family từng PASS đều là
session-window + structure: Phoenix XAU M15 PF 1.68–1.83, SMC_Confluence
NYOnly PF 1.36–1.61, SilverBullet USDJPY ICT KZ+FVG PF 1.28 (WFA 5/5).

## Toolchain

- Python 3.12.10 user-scope. `alpha.ps1`: compile → backtest → analyze;
  `validate-full`/`delivery` chỉ cho survivor. `alpha.ps1 clean` = post-run
  hygiene (dry-run mặc định).
- Research plane: portable isolate `02. AlphaFactory/runtime/`. Observation
  plane: MCP `127.0.0.1:22346` (đọc; backtest MCP không phải số quyết định).
- `session_trader`: OBSERVE đã chạy thật; `DEMO_EXECUTE` vẫn khóa chờ EA
  executor MQL5 canonical.
- Chi tiết fail-deadly đã ghi: `04. Memory/do_not_repeat_failures.md`.

## BoundaryEdge campaign + governed-pipeline traps (2026-09-18)

- **MT5 tester last-used `.set` memory trap**: tester replays input values
  từ `MQL5/Profiles/Tester/<EA>.set` cho mọi param KHÔNG pin trong
  `[TesterInputs]` — đổi default trong source KHÔNG có tác dụng. Run
  20260918_105756 chứng minh: source defaults 0.0 nhưng tester replay
  40.0/0.2 → byte-identical results. Fix: pin ALL spec params qua
  `exact_overrides` + `--extra-overrides` của build_control_packet.
- **build_control_packet overrides phải canonical sorted** — engine
  normalize CLI qua ConvertFrom-NormalizedOverrideMap (alphabetical);
  tool đã patch emit sorted. Trio-only packet "vô tình" đúng vì đã sorted.
- **Registry schema**: screened rows cần verdict='SCREENED_PENDING_RUN',
  reason, metrics={}, validation, updated_at_utc. Killed rows cần
  `validation.source_snapshot_path`+`source_snapshot_sha256` khi
  canonical source diverge — snapshot lấy từ
  `runs/<ea>/<run>/snapshot/source/`.
- **Non-repaint audit**: CopyRates/CopyBuffer shift arg chỉ pass khi là
  bare identifier param + `if(param<1) return` guard trong CÙNG function
  (`allowed_guarded_shift_param`). Computed local expr = unproven →
  refactor vào guarded helper (xem BeCopyClosedM5).
- **Probe-vs-governed gap (lesson lớn nhất)**: Stage-0 probe book entry
  tại signal-bar CLOSE; governed fill tại next-bar OPEN — counter-move
  entries mất phần reversion + trả real spread 2 đầu. Edge +6.28p của
  Asia-pierce-fade bốc hơi hoàn toàn (PF 0.825 ngay trong window 2022+
  của probe). Mọi probe edge ở bar-close granularity cần discount
  ~(spread RT + adverse gap) trước khi tin.
- **Selection-on-survival artifact**: conditioning "trades đạt time-exit"
  (không bị SL cắt) chọn winners — subset PF 2.42 của HYP-001 là artifact,
  full-set PF chỉ 0.82. Không bao giờ đọc PF của exit-conditioned subset
  như evidence cho mechanism.
- HYP-BEDGE-CHF-M5-001 KILLED (PF 0.767, frozen 4xATR SL bound 53%):
  SL interior stop giết mean-reversion — nhưng thay SL cũng không cứu.
- HYP-BEDGE-CHF-M5-002 KILLED (PF 0.822, SL 25xATR non-binding 98.6%
  designed exits, full pipeline PASS): mechanism âm cả 2 legs
  (FADE 0.845, MONCH 0.667), không regime story. **Family dead.**
- Orphan terminal64 của isolate spawn sau mỗi governed run — kill trước
  compile/run kế (compile gate refuse khi còn orphan).

## 2026-09-18 SMOM-JPY kill + probe-vs-governed gap CONFIRMED x2

- HYP-SMOM-JPY-M5-001 (EA_SessionMomentum, with-trend session-open continuation):
  governed PF 1.0045 n=6205 - ECONOMIC NULL. First EA to reach PF>=1.0 in 59 runs.
  Probe edge +12.4p -> governed ~0, even in probe's own window (NY leg 0.66-0.73 in 2025-26).
- CONFIRMED RULE: bar-granularity Stage-0 probes CANNOT predict governed economics,
  in EITHER direction. Fade probe +6.28p -> PF 0.825; continuation probe +12.4p -> PF 1.00.
  The gap consumes 100pct of edge. Only governed runs are evidence.
- MULTIPLE-TESTING RULE: across ~50+ probed cells, max-cell t~3 is the noise-max
  expectation under null. Anomaly threshold: both split-halves |t|>2.8 AND t>4
  AND cross-asset replication AND survival after governed-discount.
- With-trend fill advantage is REAL directionally (fade 0.82 -> cont 1.00) but
  does not create edge where none exists.
- build_control_packet: --extra-overrides must include InpVerboseLog explicitly;
  builder does not auto-append it. CostSourceManifest CLI path needs forward slashes.
- New screened rows need verdict=SCREENED_PENDING_RUN + reason + metrics:{} +
  validation + updated_at_utc or validator rejects.

## 2026-09-18 H4/D1 boundary class Stage-0 DEAD (probe_h4_boundary.py)

- H4 asia-env close-pierce continuation: -2.6..+1.2p across 7 symbols - nothing.
- H4 ldn-env continuation x3bar: -0.8..+1.9p - nothing.
- D1 week-open drift follow: -9.8..+2.0p (JPY/CHF/EUR negative t~-3 -> mirror
  week-open reversal +8-10p but split-halves inconsistent, 1/wk cadence).
- Wide geometry does NOT rescue dead mechanisms: the information at session
  boundaries is M5-granular; H4 smooths it away. The class space is now
  exhausted end-to-end (M5->D1, fade AND continuation, price AND calendar).


## SMOM family — KILLED airtight 2026-09-18 (2 regimes)

`HYP-SMOM-JPY-M5-001` run `20260918_115433`: passive session-exit
**PF 1.0045**, n=6205 — best-ever governed result but economic null.

`HYP-SMOM-JPY-M5-002` run `20260918_135142`: autopsy-driven engineered
exits (BE+2p@15, trail peak-12p@20, inv-cut 2h/MFE<10p) executed exactly
as designed — INV_CUT 46%, SL stop-outs 46%, BE armed ~4026 — and made it
**WORSE: PF 0.903**, n=8542, -$1133, LDN 0.833 / NY 0.963.

**Lesson (the real one): MFE excursion != harvestable edge.** SMOM signal
produces volatility, not drift — any ratchet tight enough to lock profit
gets hit by ordinary retracement (+2p scratches); passive exits net ~0
after cost. Under 2 independent management regimes realized edge <= 0 →
premise dead, not just management-dead. Autopsy must check whether
excursions survive ANY plausible ratchet before minting an exit-stack
hypothesis.

## Pipeline traps (new)

- **Tester journal delta cap 256MB**: per-tick `PositionModify` spam
  (trail stepping 0.1pip) inflated journal 48MB -> 268MB -> `truncated=true`
  -> run invalid. Fix: min 1-pip modify step (conformance patch, also
  broker-realistic). Check `data_quality_journal_delta.truncated` first
  when a run dies at the data-quality gate.
- **`.tst` report cache**: `Tester/cache/*.tst` replayed a stale report
  in ~90s with empty journal delta. Delete stale `.tst` + `.set` when a
  run returns instantly.
- Lifecycle CSV has OPEN/CLOSE + deal_net only; exit reasons live in the
  tester journal (`reason=INV_CUT/LEG_TIME_STOP/TRAIL/BE_MOVE`), each
  line double-logged (EA journal + Core 01) — halve raw grep counts.


## DEEP RESEARCH 2026-09-18 — day-boundary reversal complex (Stage-0 verified)

Full doc: `04. Memory/research/20260918_DAY_BOUNDARY_MARKET_PHYSICS.md`

Method breakthrough: **conditional-vs-unconditional** measurement
(signal vs same-hour baseline, signed direction, next-bar-open entry,
tick-level cost at execution hour) — found the edge every prior probe
missed by measuring unsigned/unconditional.

**Mechanism 1 — day-open sweep fade**: bars 00:00-00:30 server piercing
prior-6h range -> FADE, 1-4h hold. PF 1.45-5.56 per-bar, win 56-89%,
~1.6-4.3 events/wk, 6/7 majors (JPY exempt = home session). Stable
2025->2026. Effect UNIQUE to day boundary (LDN/NY/dayHL = no fade).
MAE median -3~-6p, p25 -7~-14p -> stop design ~10-15p or delayed entry.

**Mechanism 2 — early-Asia drift**: unconditional long 00:55 server +1h,
PF 1.57-3.94, all 7 incl JPY. Calendar mechanism (~5/wk).

**Cost at boundary**: spread p90 0.2-0.3p on feed (flat, no rollover
widening). Real RT ~0.5-1p.

**Cadence total**: ~7-9/wk top symbols (CHF 9.3, NZD 9.1, AUD 8.2) —
closest ever to GOAL floor 10. Universe fixed (8 syms, per-symbol gate).

Lesson: MAE/MFE autopsy + conditional-vs-baseline + signed direction +
cost-at-hour = the research method that found this. Prior probes hid
the edge inside hour baselines.


## 2026-09-19 DEEP-HISTORY CORRECTION — roll-gap reversion VERIFIED, fade WITHDRAWN

Full doc: 

**Method fix**:  reads tester M1 .hcc directly (2010->2025,
~370k bars/yr) — the copy_rates probes only saw 16 months (2025-05->2026-09)
because get_bars silently stops at the stub-.hcc gap. Event-level accounting
(one event/day), server-time labels, pip sanity clip.

**VERIFIED — roll-reopen gap reversion** (first real mechanism, 16y):
- 00:00 server (5pm-ET roll) reopen gaps DOWN vs fair value -> LONG ~00:05,
  exit +60-120m (PF peaks 120m), SL ~10-12p (MAE med -3~-5p).
- gap<=-1.5p: PF 2.0-4.3, t 6-18, win 65-80%, ~60 events/yr/symbol, 7/7
  majors + XAUUSD at its 01:00 boundary. Post-2016 stable, both DST regimes
  (anchored to real roll, not clock artifact). USDCHF also reverts gap-UPS
  (short PF 2.5-6.7). Week-open adds ~0.3-0.5/wk on CHF/CAD/GBP.
- Cadence honest: ~1.2-1.5/wk conditional — GOAL floor NOT met alone.
  Run tests governed economics; cadence is separate contract question.

**WITHDRAWN**: pierce-fade claim (2026-09-18 doc) — event-level M1 shows
up-pierces CONTINUE (fade -2~-7.7p, win 15-35%, all years). M5 probe's
+5-7.5p was sign/tranche artifact. Also dead: 23h pre-roll (post-2016),
WMR/ECB/Tokyo-fix reversions at correct clocks (PF 0.85-1.15),
post-reversion giveback, boundary gap itself (CIP carry repricing).

**AUDIT findings incorporated** (subagent 8842e967):
- BEDGE/SMOM governed kills ran GMT-shifted windows DISJOINT from probed
  server-time cells — clock-corrupted, did not test day-boundary. New EA
  gates on SERVER time (out.server_hour / server minutes), never 'GMT'.
- Spread-contradiction resolved: COST_PLANE_AUDIT p90-5.4p is 00:00 UTC
  = 02:00-03:00 server, NOT the 21-22 UTC entry window (p90 0.2-0.3p).
- '7/7 same sign' = ONE factor replicated (USD basket), not 7 independent
  bets — conditional-gap test (fires only on big gaps) is the real proof.
- Probe conventions now: assert times[0/-1] coverage, event-level not
  tranche, sanity clip, no GMT labels on server data.

---

## 2026-09-18 — HYP-RGR-CHF-M1-001 KILLED + hcc_reader FABRICATION TRAP (critical)

**Verdict**: KILLED_AT_MODEL_0. Run `EA_RollReversion/20260918_205000`: PF 0.14
(<< 1.30 gate), 857 trades, -$7026, DD 70.5%, win 19.3%, ~80% SL -15p stopouts.
HQ 98%, 6.06M bars, 261M ticks — evidence authoritative. Every year negative.

**Root cause — premise was a DATA ARTIFACT, not market economics:**

`tools/hcc_reader.py` (60-byte phase-scan) fabricates M1 records inside the
roll-minute tick burst (00:00-00:10 server). Evidence:
- 2781/2789 USDCHF days show an absurd 00:00 "spike bar" (range 59-173p,
  tv ~50-57k vs normal ~50, sp=0) — misaligned record, not a real bar.
- 86% of real tester entry fills fall OUTSIDE the reader's bar range for that
  minute. Decisive: 2026-04-10 fill BUY @0.79050 vs reader 00:04 bar max
  0.78843 — the tester fill proves the reader's bar is wrong by 20p.
- The probe "enter at 00:05 open" systematically landed on fabricated prices
  sitting at the post-flush bottom → manufactured +3.8p "reversion" / PF 4.3
  that never existed at tradable prices.
- Gap event itself (open0 − prev_close) WAS real — EA journal gaps match.
  What does not exist: the reversion at executable prices.

**TRAP — standing rule:** never measure entries/exits inside roll/burst windows
on hcc_reader output. Any probe edge whose entry or exit price lands in a
burst region must be validated against real fills (tester journal / tick data)
before minting. Bar-open entries near liquidity events are fabrication-prone.

**Secondary conformance defect**: nonrepaint audit FAIL — time-range
`CopyRates(start,stop)` / `CopyTime(from,1)` flagged as unproven shift
(no lookahead possible, but contract requires guarded helpers).

Day-boundary family now fully dead: pierce-fade (up-pierce=continuation),
23h pre-roll (dead post-2016), fix-window reversions, roll-gap reversion.

### Data-integrity infrastructure (2026-09-18, post-RGR kill)

- `hcc_reader.py` v2: `read_hcc_year_flagged(path)` -> (bars, suspect_set,
  report). Suspect = tv>max(2000,50x median) OR range>2% of price, plus a
  15-min contamination window after each burst marker + ctm collisions.
  `read_hcc_year`/`load_symbol` keep legacy API; `load_symbol(flagged=True)`
  returns flags. **Any probe touching suspect ctms is void.**
- `validate_bars_against_fills.py` — GATE A tool: lifecycle CSV fills vs
  reader bars; reports outside-rate by minute-of-day. On the RGR run:
  684/684 fills inside suspect regions, 86% outside bar range (dev to 38p).
- Trusted-windows map (.hcc, per symbol): majors UNTRUSTED 00:00-00:15
  server (roll burst); XAUUSD 01:00-01:16 (its own boundary); USDJPY 22%
  suspect — roll + scattered bursts, treat all JPY edges cautiously.
  Everything else provisionally trustworthy pending spot fill-validation.
- Structural truth: .hcc stores roll bursts in a packed non-bar layout
  (marker record tv~50k); tester reconstructs real ticks → tester bars
  span wider than reader bars. Tester fills/journal = ground truth.

### Research factory `02. AlphaFactory/lab/` (2026-09-18)

Replaces artisanal probe scripts with a systematic pipeline:

- `etl.py` -> `cache/<SYM>_M1_2010_2026.parquet`: canonical plane, suspect
  flags baked in (8 symbols, ~50M bars, USDJPY 17.5% suspect).
- `features.py` vectorized event detectors; `labels.py` next-bar-open
  path sim (SL-first on ambiguity); `stats.py` welch-t/BH-FDR/split-half/
  per-year; `sweep.py` -> `lab.duckdb` results ledger (dedup by cell hash,
  negatives stored); `mine.py` family grids (impulse_cont, breakout_cont,
  pullback_cont); `model.py` HGB + purged/embargoed CV.
- Rules: events touching suspect bars dropped+counted; cooldown on every
  mask (no tranche oversampling); anomaly needs q<0.05 FDR + split-half
  same-sign + pos_year_frac>=0.6 + t>=2.8; cost_rt=1.0p baked in.
- First sanity check: EURUSD 15-bar +5p impulse -> continuation -1.26p,
  PF 0.80 (impulse CONTINUATION loses gross; fade side +1.26 gross but
  adverse-fill discount kills it net — both directions dead at that spec).

### Lab first harvest — M1 event-edge ceiling measured (2026-09-19)

7,335 cells (impulse/breakout/pullback continuation, 4 symbols, cost_rt=1.0p):

- **max |raw edge| = 1.27p across the entire grid**; only 16/7335 cells >1.0p;
  mean |raw| = 0.29p. Both directions die: continuation net ~-1.3p,
  fade net ~-0.7p (fade_net = -cont_net - 2*cost).
- |raw| scales with hold (0.25@30m -> 0.46@240m) but SUBLINEARLY — never
  reaches cost floor. Scales with theta (stronger impulse -> more reversion)
  but caps ~1.3p.
- **Structural law on this feed: event-driven M1 edges live entirely below
  the ~1.0-1.5p round-trip cost floor.** Not a mechanism failure — a
  measured ceiling. Any new mechanism must clear ~1.5p gross/event to be
  viable; check that FIRST before elaborate exits.
- Model layer (HGB, purged CV): AUC 0.52-0.54, IC 0.05-0.08 stable across
  folds; high-confidence predictions anti-correlate (conv_acc 0.26-0.42) —
  model independently learned "impulse reverts", matching the sweep.
- hcc_reader v3: plausibility validation added (rolling-median 3x band +
  magnitude bounds) — garbage records mimic valid RELATIVE structure at any
  magnitude (o=3.5e121 passes h-l<0.5*o); only local-median bands catch
  them. >0.8% 1m jumps flagged suspect (mostly real flash moves, still
  unverifiable). Plane clipped to [y0,y1].

### Lab sim unit bug (2026-09-19) — always check exit-mix invariant

`labels._eval` compared price-unit excursions to pip-unit SL/TP
(`ls <= -20` vs ls~-0.002) -> SL/TP NEVER fired; every recorded cell was a
pure-drift measurement, not a tradable exit. Detection heuristic that
catches the whole class: **exit_mix 100% TIME while sl/tp set = unit bug.**
`sweep.record` now emits verdict=WARN_ALL_TIME_EXITS on that invariant.
Old drift-surface rows preserved in `results_log_simv1_drift.csv`.
Fixed sim: Wednesday EURUSD-11h-short improved PF 1.35 -> 1.40 (SL cuts
left tail); TP caps kill the drift (tp=12 -> -0.49).

## 2026-09-19 — GATE A caught sim bug #3: side-swapped SL/TP fields (D1)

Second advisory-board save in one day. Both GATE A seats independently
flagged `labels.py` short-side SL/TP: for side=-1 the adverse field was
the bar LOW (favorable), so stops fired only on whole-bar penetration —
every wick-touch booked as a continuation win. Bias ~+1.5p on shorts.
Longs were always correct. Fix: per-side adverse/favorable fields +
inert tail-pad + ctm-adjacency counters + suspect-on-signal-bar. Sim now
`SIM_VERSION=3`; `cell_hash` includes it -> full auto re-measure.

Corrected headline: EURUSD European-USD-bid short **dies in-probe** —
11h Tue-Fri: v2 +2.81/PF1.36 -> v3 +1.29/PF1.15; best variant
(pure-drift h240) PF 1.25 < 1.30. Premise real (baseline control:
all-liquid-hours short = -0.82) but economics uncapturable -> KILLED,
see 04. Memory/research/20260919_EURUSD_EUROPEAN_USDBID_EVIDENCE.md.

Pattern to internalize: **sim bugs keep surfacing one layer deeper**
(v1: exits never fired on unit mismatch; v2: pip fix exposed the field
swap). Rule: any new evaluator must be unit-tested on a hand-computed
short AND long case before the first cell is mined.

Post-v3 valid lead: LONG-side cells are unaffected — USDCHF Mon 1h long
+1.46/t5.01/PF1.62, USDJPY Mon 1h long +1.47/PF1.37 (Monday Asia-open
USD bid), EURUSD Wed 1h long +1.44/PF1.27. All ~1-2/wk — cadence floor
remains the binding constraint campaign-wide.

## 2026-09-19 GATE B kill: HYP-WOPEN-CHF-M1-001 — the cost-model trap

USDCHF Mon-01h long (+1.46/t5.01/PF1.62 at flat cost=1.0p) **killed
before freeze** by the auditor's decisive checks:

- **Recorded spread kills it**: feed `sp` at Mon 01h = med 1.5p / p90
  3.3p. At entry-recorded-spread+0.7p comm the cell = -1.11p / PF 0.69.
  The edge was 100% cost understatement.
- **Edge-cost anti-correlation (structural)**: recorded sp = 0.7p
  midday -> 1.2-1.5p at the hours where anomalies appeared -> 4.1p at
  the roll. Edges live exactly where liquidity is thin and cost is
  widest. ALL 4 corrected-grid survivors die at honest cost (CHF -0.69,
  JPY 1.15, XAU 0.62, EUR-Wed 0.73).
- **Mechanism mislabeled**: edge exists only in weekend-gap-down weeks
  (+2.82/PF2.51 vs gap-up +0.12/1.04) = weekend-gap FADE, not weekly-
  open drift; the conditional variant also dies at real cost (0.97).
- **Era concentration**: post-2020 only (2010-15 PF 1.11 -> 2024-26
  3.48). Per-year pos-count masked it.
- **NOT fabrication**: 360/360 Owner-GUI bars match lab .hcc at Mon 01h
  (0.20p med dev). Week opens 00:00 server on both feeds.

NEW STANDING RULES (added to gate checklists):
1. **Cost = per-event recorded `sp` + commission, never flat proxy.**
   The data plane already stores `sp`; sweep/eval must use it. A cell
   that only survives at tight-spread brokers is a broker-transfer
   hypothesis — declare it, don't measure it as a feed edge.
2. GATE B mandatory decompositions for clock/boundary cells: era
   split, weekend-gap conditioning, first-bar-of-week census,
   sister-cell coherence dump, `sp` at window.
3. Aggregate pos-year counts are insufficient stability evidence —
   require era-level PF table.

## 2026-09-19 TWO COST PLANES — critical reframe

Measured FivePercentOnline-Real ticks (deploy venue): EURUSD 0.0–0.1p
median ALL hours; USDCHF 0.1–0.2p all hours (roll hour ~1.2p). The
MetaQuotes-Demo feed's recorded `sp` runs ~7–15x wider (0.7–1.5p+).

- `cost_deploy` ≈ flat 1.0p RT (v3 ledger) = deployment economics.
- `cost_recorded` = per-event `sp`+0.7 (v4 ledger) = research-feed
  economics / stress bound.
- A cell passing only at deploy cost is a broker-transfer hypothesis —
  legal because funded IS the deploy target, but must be DECLARED.
- Governed tester note: to validate at deploy cost, the tester spread
  must be CONFIGURED to funded-typical (fixed ~5pt), not the feed's
  recorded spread.

## Falsification map (76k+ cells, real conventions)

DEAD at demo-feed cost (v4): every unconditional + event + gap surface
(0/20k drift cells ≥1.30). DEAD at both costs: daily-open gap fade,
multi-day context holds, trend-pullback@scale. MARGINAL (PF 1.2–1.45,
sub-cadence, erratic years): Monday cluster at deploy cost (CHF/JPY
Mon-01h, XAU Mon-8/9h), EURUSD prior-day sweep-low fade, ML follow
EURUSD-shorts (PF 1.31, ~3/wk) + USDJPY both-sides (~PF1.22, ~8/wk).

Structural law: cadence×edge inverse — every family peaks PF~1.2–1.45
on ~100–900 events/17y. GOAL's joint contract (PF>1.3 × 10–40/wk × 2x
cost) is beyond measured density on this feed.

## LEAK CLASS: suspect bars in FEATURE computation (2026-09-19)

The 00:00 daily-summary record (h/l = full-day range, flagged suspect)
leaks future extremes into any rolling/cummax/cummin feature built on
raw h/l. `day_pos` on raw h/l had univariate AUC 0.70 — pure lookahead.
Dropping suspect at entry/path (evaluator) is NOT enough: features must
be computed on h_eff/l_eff (suspect → -inf/+inf) too. Any feature that
touches h/l must be audited for this channel. Day-context features must
use first NON-suspect bar's open.

## 2026-09-19 WGAP-JPY calibration run — status

HYP-WGAP-JPY-M1-001 (EA_WeekGap, USDJPY Mon-01h long, gap<-2p, SL20p,
time-stop 61 bars = close of 02:01 bar): FROZEN after GATE B round 2 —
Auditor PASS-with-conditions (all 3 mechanical items closed), Gatekeeper
PASS. Probe: n=450, recorded +2.16p/PF1.54/t3.12; deploy +3.24/1.90;
x1.5=1.25, x2=1.01 (on gates). Registry row SCREENED_PENDING_RUN.
CALIBRATION ONLY: ~0.51/wk, DONE structurally unreachable.

EA_WeekGap.mq5 written on shared substrate (AF kernel, LSW clock/
session/risk, WG telemetry). Gap scan uses OPEN/CLOSE only — fabricated
first-bar h/l never read; signal bar itself can serve as week-first bar
(lab parity).

## 2026-09-19 WGAP-JPY governed run — DONE (calibration)

Run EA_WeekGap/20260919_183811 (Model 0, USDJPY M1, verified_m1_asof
2010.01.04–2026.09.18, HQ 99%): 427 trades, PF 1.58, +$1082, DD 2.58%.
Verdict REVIEW 6/14 — premise CONFIRMED (probe 1.54 → tester 1.58;
415 common Mondays, gap dev med 1.5p inside declared feed fragility;
entry :01 / exit :02 / SL 20p exact). KILLED as GOAL candidate:
cadence 0.49/wk structural, recorded-plane PF 1.13, cost stress
x1.5=0.96 / x2=0.82, equity REJECT (spike 96%, R2 0.61). Readout:
EA_WeekGap/research/HYP-WGAP-JPY-M1-001_GOVERNED_RUN_READOUT.md.

Standing lessons learned this run:

- Registry schema: rows need source_hash (not source_sha256),
  prereg_path, run_ids, exact_overrides as string ("" if none),
  evidence_contract_kind + acceptance_contract even when killed;
  file must be single-spaced (validator counts physical lines).
- build_control_packet.py --extra-overrides is merged with the 3 base
  pins and Python-sorted — but the engine canonicalizes with PowerShell
  order (InpSlippagePoints before InpSlPips). Post-fix packet overrides
  to the engine order.
- EmitD0SeriesProof wire contract: m5_* fields must literally read
  PERIOD_M5 with var name m5_first_epoch (nonrepaint whitelist +
  data-quality gate both parse it). m1_* = terminal M1 bounds.
- data_fingerprint in packet/manifest = PRE-RUN claim only; post-run
  the manifest is overwritten by the report's actual hq/bars/ticks —
  rebuild with actuals once a discovery run reveals them.
- verified_m1_asof flow: run-1 all_available_asof (HQ fails on sparse
  pre-2010 era) → read actual dense start → repin window (USDJPY
  2010.01.04) → run-2 verified. Same as RGR's USDCHF (2010.05.10).
- Isolate auto-updates terminal build (6201→6204): evidence identity
  must be re-measured on the CURRENT build before packet build, else
  server_fingerprint mismatch post-run.

## 2026-09-19 — Cross-asset lead-lag killed; falsification map complete

- HYP-XLEAD-AUDXAU-M1-001 KILLED_AT_PROBE: AUDUSD 15m impulse >20p →
  XAUUSD +60m. Genuine lead-lag confirmed (XAU-flat subset +10.3p PF2.15)
  but deduped+net: PF 1.20 @ 7.8/wk, edge concentrated 2011-2014 gold era.
- New probe rule: cross-asset screens must dedup events (60-bar cooldown)
  before believing PF — undeduped raw was PF 1.55 vs deduped 1.45 vs net 1.20.
- XAUUSD `sp` is 41.7% corrupt (0 or >=500 pts); sane-median = 16 pts
  (1.6p of 0.1-pips). Always v4-style cap before cost math.
- Every mechanism family on this data plane is now falsified. Only two
  lawful doors: Owner cadence amendment, or different data plane.

## 2026-09-19b — Universe +12 symbols; WGAP replicates; tick pilot running

- Same-feed expansion: AUDJPY/AUDNZD/AUDCAD/AUDCHF/USDSEK/USDNOK/USDPLN/
  USDTRY/USDZAR/USDMXN/USDCNH/USDSGD synced via EA_ExecutionKernelHarness
  dataacq runs (receipts under runs/_dataacq/). ETL'd to lab cache.
- WGAP replicates on clean 01:00 paths cross-symbol (PF ~1.6-2.5 gross,
  2020+ 3-7). Gap-up side dead. Cadence ceiling ~6/wk multi-symbol —
  GOAL floor still unreachable on M1.
- pip_size() now resolves *JPY -> 0.01 via suffix (was default 1e-4).
- Dukascopy tick pilot (AUDUSD+XAUUSD 2026-06->09) downloading under
  external/dukascopy_pilot/ — flaky host, resume-by-day receipts via
  dukacopy_pilot_runner.ps1 loop.
- TRAP: Mon 00:00-00:10 roll is suspect; lab can't measure week-open.

## 2026-09-20 tick-plane campaign
- HYP-WGAP-JPY-M1-002 (00:05 slot): governed run 20260920_000259 -> 0 trades,
  signals fire but rollover guard rejects 100%. KILLED (untradeable window).
- Week-open REAL ticks (Dukascopy AUDUSD Sun 06-07): spread ~15.6p first 30min
  vs ~1.0p normal. Week-open edge <15p dead on cost. Guard is justified.
- Tick lead-lag probe: lab/probe_tick_leadlag.py (strict causality, real
  spread at entry+exit ticks, dedup=H). Week-open probe: probe_weekopen_tick.py.
- Sync wave3 running: 20 crosses (EURJPY GBPJPY CADJPY CHFJPY NZDJPY EURGBP
  EURAUD EURCAD EURCHF EURNZD GBPAUD GBPCAD GBPCHF GBPNZD NZDCAD NZDCHF
  CADCHF EURSEK EURNOK EURZAR) via runs/_dataacq/sync_wave3.ps1.
- WGAP-basket plan: gap-down->fade replicated on AUDJPY/AUDCAD/AUDNZD/USDCHF/
  USDJPY (PF 2.07-2.52, 2020+ stronger). If JPY/EUR/GBP crosses replicate too,
  basket cadence could reach ~10/wk -> first real GOAL candidate path.
- Builder for new-symbol receipts: tools/build_dataacq_receipts.py.

## 2026-09-20 wave3 + tick probes
- Universe now ~35 symbols parquet (wave3 crosses all synced+ETL'd).
- WGAP NET truth (probe_weekgap.run): survivors USDJPY 1.54, EURZAR 4.26
  (+64.8p/ev, 12/12yr positive!), EURSEK 1.72, EURNOK 1.41, GBPJPY 1.23,
  EURJPY 1.16, AUDJPY 1.04. Earlier AUDCAD/AUDNZD/AUDCHF/USDCHF "replication"
  was GROSS — net they die (0.59-0.73). All EUR/GBP crosses dead.
- Basket: ~6 trades/wk, PF 1.71 net — cadence-blocked by GOAL floor 10/wk.
  Deployability gate: does The5ers offer EURZAR/EURSEK/EURNOK? (check when
  Owner GUI back online).
- XAUUSD tick autocorrelation (Dukascopy, 4.6M ticks): momentum dead at ALL
  scales 5s-5min (mean ~-6p = exactly round-trip spread). Microstructure
  efficient; fade side equally dead.
- AUDUSD->XAUUSD tick lead-lag (15d): W300/H900/th6 PF 1.72 +23p 23/wk BUT
  per-day episodic (4 days carry all). Needs full Jun->Sep range.
- Week-open ticks: AUDUSD Sun-open spread ~15.6p first 30min — kills <15p edges.

## 2026-09-20 CORRECTION (important)
- Exotic "edges" (EURZAR WGAP 4.26, daily-01:00 drift +28p, USDMXN
  bidirectional) were PHANTOMS: spread_cost_arr's <200pts sane bound treats
  real exotic spreads (22-107p median!) as corrupt and imputes ~5p cost.
  Re-priced at real spread every exotic cell is PF 0.03-0.28. VOID.
- Trap: if >50% of `sp` corrupt on a symbol, sane-median fallback is
  meaningless — measure (0,5000]pts band first. Majors bound 200pts does
  not transfer to exotics.
- Standing truth: M1 plane survivors = USDJPY WGAP core only (~0.5/wk).
  GOAL via M1 remains cadence-blocked. Tick plane is the active hope.

## 2026-09-20 late — cost fix consequences
- spread_cost_arr bound fixed: sane = 0<=sp<1e6pts (garbage signature),
  was <200 which silently imputed ~5p cost on exotics w/ real 22-107p spreads.
- Re-priced: AUDJPY WGAP -2.36p PF 0.70 (was +1.04 phantom). Basket now
  USDJPY 1.54 + GBPJPY 1.21 + EURJPY 1.14 only -> ~1.6 trades/wk. Dead floor.
- Hold-sweep: gap-fade completes ~60m, longer holds decay to 0.
- Tick lead-lag AUD->XAU: PF 1.72 on 16d BUT excl top-2 days -> 0.96.
  Provisionally dead (episodic). Reverse XAU->AUD dead.
- Session-open tick probe built (probe_sessionopen_tick.py); cells noisy
  n<20, awaiting full range.
- build_control_packet.py argparse % bug FIXED (help works).
- Downloads alive: AUDUSD 25d, XAUUSD 17d, BTCUSD 7d (3 runners grinding
  rate-limited host; resume-by-day via runner loops).

## 2026-09-20 final iteration state
- AUDUSD session-open dead on full 110d (all cells PF<1.5, most <1).
- BTC tick momentum dead all scales (~-$56 = round-trip spread).
- Week-open CLOSED definitively: n=15 Sundays all cells negative both
  directions. Lab void + EA guard + tick cost = 3 confirmations.
- News-drift dead (869 events 2019-22, majors PF 0.67-0.78).
- Pair-divergence dead (EURGBP/AUDNZD/EURCHF PF<0.90; EUR->GBP mean +16p
  is fat-tail lottery, not GOAL cell).
- Unconditional hour-sweep: EVERY hour×side on USDJPY/EURUSD/XAUUSD
  PF<0.70 (n=180-260k/cell). Clock families dead unconditionally.
- Tick data integrity verified: 178 files, 13.46M ticks, all valid.
- XAUUSD tick download resumed (19d->110d range pending); BTC backfill
  Jan->Aug running. The5ers plane remains untested (needs GUI).

## 2026-09-20 iteration 2 — lead-lag killed, data planes expanding
- AUD->XAU lead-lag DEAD: 53d overlap, 97 events, PF1.43 headline but
  ex-top3 PF=0.98 — fat-tail lottery, same as EUR->GBP div.
- XAUUSD session-open DEAD: cross-feed replicated on same 15d (real
  regime) but 16y decomposition shows only weak persistent NY-summer
  drift (+1-12p gross < cost). Episodic, not mechanism.
- AUDUSD tick mom/rev DEAD all 72 cells (mean=-RT spread ~1p).
- H1 compression-breakout DEAD (gross PF<=1.45, net ~1.0, 0.5/wk).
- Asia-range->London brk DEAD (net -0.02..-1.41p, n~2500/sym).
- Overnight roll drift: noise, dead.
- META-LAW confirmed x4: positive-mean cells are either regime-
  concentrated or fat-tail lottery. GOAL needs median-event profit.
- XAUUSD receipts fix: 19 rebound to canonical pilot contract sha
  (binary hashes verified); downloader resumed, at Jul-28.
- New contract: EURUSD+USDJPY ticks Jun1->Sep19 (tightest spreads —
  last tick-plane check). BTC backfill at Jan-2026->Sep (86d done).
- Trap learned: powershell for-loops via bash need \$ escaping;
  contract CLI must match frozen workers/retries exactly.
