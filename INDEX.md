# INDEX — Bản Đồ Workspace

Cập nhật: 2026-07-22

Mỗi entry một dòng: file gì, mở khi nào. File này chỉ chứa con trỏ; nội
dung nằm ở đích đến. Cập nhật khi một file canonical bị di chuyển hoặc mở
lane mới — không cập nhật cho từng run/readout mới.

## Chuỗi đọc-trước (mọi session)

1. `CLAUDE.md` / `AGENTS.md` — quy tắc vận hành (root, entry tự nạp)
2. `01. GOAL/GOAL.md` — mục tiêu; chỉ đổi khi Owner quyết
3. Registry/prereg/task packet liên quan + AlphaFactory status/lock — contract
   và quyền thực thi hiện tại
4. `04. Memory/hot.md` — cache tham khảo lane/blocker/next moves, không phải
   authority hay blanket veto
5. Git có thể tồn tại (Owner đã mở remote private) nhưng **agent mặc định
   không stage/commit/push** trừ khi Owner yêu cầu rõ trong message hiện tại.
   Xác minh bằng receipt/hash/validator — không “dọn GitHub” tự ý. Chi tiết:
   `AGENTS.md`.
6. Trước hypothesis/EA mới: `04. Memory/do_not_repeat_failures.md`
   + registry — xác định failure radius; tránh exact replay/rescue nhưng không
   chặn mechanism/data contract mới.

## Doc điều khiển — `04. Memory/` (state) + `05. Playbook/` (rules)

**`04. Memory/`** — trí nhớ sống:

| File | Mở khi |
|---|---|
| `hot.md` | cache tham khảo đầu session (NEXT SESSION + ledger); phải verify, không cấp/veto quyền |
| `do_not_repeat_failures.md` | prior + failure radius trước revive/hyp mới; không phải blacklist |
| `source_of_truth.md`/`.json` + `validate_source_of_truth.py` | registry fact/path canonical + validator fail-closed |
| `research/CANDIDATE_REGISTRY.jsonl` + schema + validator | ledger hypothesis generic append-only; validate trước mọi run có ý nghĩa |

**`05. Playbook/`** — 5 file chỉ dẫn lõi:

| File | Mở khi |
|---|---|
| `validation_gates.md` | chấm run + delivery gate: stage, ngưỡng, evidence completeness, hard invalidation |
| `tool_runbook.md` | lệnh chính xác: compile/backtest/validate/analyze/delivery |
| `ea_golden_path.md` | flow mở EA mới + failure radius → brief/matrix → probe/prereg → build/Model 0 → forensics/delivery |
| `ea_engineering_standard.md` | viết/review code MQL5 (closed-bar, non-repaint) |
| `research_doctrine.md` | thiết kế hypothesis: registry, prereg, overfit budget, MT5 rules |

**Đã archive** (không active surface) → `00. Old File/project_control_archive_20260716/`:
workflow, multi_agent_roster + `agents/`, agent_ea_research_loop, run_data_policy,
forward_test_protocol, mcp_policy, `skills/`, receipts (cleanup/process/goal),
data_contracts, current_state, session_anchor, ea_rd_tooling_roadmap, DRAFT.

| Khác | Mở khi |
|---|---|
| `.codex/operator/STATUS.md` + `EXPERIMENTS.jsonl` | ledger recovery task dài; operational reference, không cấp quyền EA |

## Nghiên cứu — generic active + lịch sử archive

| Path | Mở khi |
|---|---|
| `04. Memory/research/CANDIDATE_REGISTRY.jsonl` + schema + validator | ledger active dùng chung mọi EA; source/prereg hash-bound, transition fail-closed |
| `04. Memory/research/20260716_GOAL_EXTERNAL_UNLOCK_BLOCKED_AUDIT.md` | evidence lịch sử của ba goal-turn cùng blocker; không phải active unlock contract |
| `02. AlphaFactory/templates/research/` | capability/prereg/task/readout + logic-to-code matrix, EA delivery packet và Grok chart-forensics packet |
| `03. EA Developer/<EA>/research/` | prereg/readout/evidence riêng package active |
| `00. Old File/EA_Archive/EA_SonicR/research/` | ledger và evidence Sonic lịch sử; archive-only, không chạy |

## Source EA — `03. EA Developer/` (16 compilable lanes + terminal research records)

| Path | Ghi chú |
|---|---|
| `03. EA Developer/README.md` | shelf pointer; current compilable lanes and terminal research records |
| `03. EA Developer/EA_FVGConfluence/` | Path-C scaffold retained for audit; HYP-001 terminal de-dup KILL. `research/comparison_202607/` holds the read-only report/public-EA/professional comparison; no Model 0/promotion/live authority |
| `03. EA Developer/EA_HybridICT_Sonic/` | lane active (Path-C stub, KILL@Model0); có `.mq5` + research |
| `03. EA Developer/EA_ICTFVGReportFidelity/` | v1.23 Human Context natural policy; 53/53 tests, compile 0/0, non-repaint V19 PASS. HYP-017 single 2018-YTD Model-0 run N=3,703, native PF 0.7553 and 1.5-pip diagnostic PF 0.3513 / -0.52139R; terminal KILL, no rerun/promotion/live authority |
| `03. EA Developer/EA_ICTVisualEdge/` | compilable visual extractor retained with terminal design-window economic KILL; no Model 0/rerun/live authority |
| `03. EA Developer/EA_KLR_Scalper/` | native MT5 replication `.mq5` retained for audit; control/USD Model-0 pair terminal `KILL_AT_MODEL0_CADENCE`, no live/rerun authority |
| `03. EA Developer/EA_MZMS_Scalper/` | closed-bar EURUSD/XAUUSD M5 audit package. EURUSD HYP-003/HYP-005 terminal; XAUUSD HYP-006 parked invalid at 98% history. Four-mechanism HYP-007..010 also parked invalid (98%<99%; runs 015121/021353/023841/024229; 400-chart Grok synthesis closed); no promotion/economic authority; no retune/rerun of these IDs |
| `03. EA Developer/EA_VRAS_RegimeAdaptiveScalper/` | HYP-001 byte-identical invalid `OrderCheck` execution record; zero-trade run has no economics and may not be rerun |
| `03. EA Developer/EA_VRAS_RegimeAdaptiveScalperV2/` | HYP-002 byte-identical invalid OnInit identity-guard record; no bars/trades/economic verdict |
| `03. EA Developer/EA_VRAS_RegimeAdaptiveScalperV3/` | final seven-gap VRAS HYP-003 package/readout: Model-0 N=93, PF0.5914, net -$5,243.22, cadence0.4465/week, terminal KILL; audit-only, no rerun/promotion/live authority |
| `03. EA Developer/EA_VRAS_PathConfirmedTrend/` | HYP-004 one-bar Trend path-confirmation matched pair: control `20260722_155551`, challenger `20260722_155635`; PF0.8996 and all frozen relative gates fail, terminal KILL with delivery evidence; no rerun/rescue/promotion/live authority |
| `03. EA Developer/EA_UnicornPrecisionScalper/` | canonical v1.23 alert-only audit kernel; event-anchored `HYP-UPS-XAU-M5-006` remains terminal KILL; V1.3 zero-trade collection is retained as D-only engineering evidence, not an active gate |
| `03. EA Developer/EA_UnicornPrecisionScalperControl/` | storage-safe four-bar Unicorn control; canonical `.mq5` retained with terminal Model-0 KILL readout and D-only evidence |
| `03. EA Developer/EA_UnicornPrecisionScalperRR15/` | post-outcome HYP-008 RR1.5 exact replay terminal `KILL_DIAGNOSTIC`; source/readout retained for audit, never rerun/promotion/live authority |
| `03. EA Developer/EA_ECRS_CompressionReleaseScalper/` | research-only `PARK_STAGE0_CADENCE_INFEASIBLE_NO_OUTCOME_READ` (2026-07-22): outcome-blind Stage-0 funnel, 0.0383 tpw at report defaults; no `.mq5`, no probe, no Model 0; economic edge untested |
| `03. EA Developer/EA_PO3_AMD_Scalper/` | research-only `KILLED_AT_OFFLINE_PROBE`; no `.mq5` |
| `03. EA Developer/EA_DRAT_ONNX_ICT_Hybrid/` | packet nghiên cứu đã dừng ở `KILL_AT_OFFLINE_PROBE`; chỉ giữ prereg/readout/evidence, không có source `.mq5` |
| `03. EA Developer/EA_GoldMacroPulse/` | real-yield external-data hypothesis `KILLED_AT_OFFLINE_PROBE`; no `.mq5`, holdout or Model 0 |
| `03. EA Developer/EA_GLDFlowPulse/` | official SPDR primary creation/redemption research-only package; HYP-001 schema kill and HYP-002 terminal offline no-edge kill; no `.mq5`, holdout or Model 0 |
| `03. EA Developer/EA_CFTCOptionsPulse/` | CFTC TFF economic probe terminal KILL plus DTCC/CME public-SDR source-feasibility readouts; no `.mq5`, Model 0 or live authority |
| `03. EA Developer/EA_CMEParticipationPulse/` | official CME daily-volume/OI research package; `HYP-CME-OI-CONT-H1-FX-001` terminal offline economic KILL; no `.mq5`, compile, Model 0 or holdout access |
| `03. EA Developer/EA_SGEFixingPulse/` | official SGE SHAU fixing source-feasibility record; density passed but temporal provenance failed before hypothesis/outcomes; no `.mq5`, compile, Model 0 or holdout access |
| `03. EA Developer/EA_HybridRegimeMR/` | MR spec lane: HYP-001 offline KILL + HYP-002 exhaustive grid KILL (family `CLOSED_EXHAUSTIVE`); no `.mq5`; EURUSD datasets now at `02. AlphaFactory/data/fivepercent/EURUSD/` |
| `03. EA Developer/EA_EURSessionDrift/` | Breedon-Ranaldo unconditional session drift `KILL_AT_OFFLINE_PROBE` (anomaly decayed post-2017); no `.mq5`; closes the last untested MR v3 branch |
| `03. EA Developer/EA_KalshiMacroPrint/` | Kalshi macro-print lane `HYP-KALSHI-MACRO-PRINT-H1-XAU-001` `KILL_AT_OFFLINE_PROBE` (gross PF 0.941/0.947 dead before cost); no `.mq5`/Model 0 |
| `03. EA Developer/EA_LSSOBPropScalper/` | LSS-OB EURUSD M15 exact-replication source + terminal MT5 evidence; control `20260719_001202` and challenger `20260719_001306` both 100% history, 388 sweeps, 0 displacement/FVG/trades; `KILL_AT_MT5_MODEL0_CADENCE_ZERO_TRADE`, no rerun/optimization/2023+/live authority |
| `00. Old File/EA_Archive/EA_SonicR/` | full SonicR ledger (archived THẬT 2026-07-15; bản duy nhất) |
| `00. Old File/EA_Archive/EA_SilverBullet/` | SilverBullet **binary-only** (`.ex5`; không còn source `.mq5` trên đĩa) |
| `00. Old File/EA_Archive/` | 80 dir archived (SonicR + SilverBullet + 78 stub `.ex5`) + manifest; **không** compile làm evidence |

## AlphaFactory — `02. AlphaFactory/`

| Path | Mở khi |
|---|---|
| `alpha.ps1` | lane compile / backtest / validate-full (cú pháp trong runbook) |
| `tools/ea_contract.ps1` | resolver fail-closed exact source + package capability contract; archive không hợp lệ |
| `tools/ea_research_loop.ps1` | entry generic dry-run mặc định cho control/challenger Model 0 |
| `tools/research_loop_engine.ps1` | engine nội bộ phía sau `ea_research_loop.ps1`; không gọi trực tiếp |
| `tools/alpha_candidate_compare.py` | comparator generic identity + control-relative |
| `tools/research/` | research kit dùng chung: `dsr.py`, `fivepercent_server_clock.py`, `snapshot_c_roots.ps1`; `chart_case_render.py` v2 dựng chuỗi M5 `PIVOT -> SWEEP/RECLAIM -> CONFIRM -> ENTRY -> EXIT` và panel M15/H1/H4/D1 có cây entry ở giữa; mode as-of che tương lai, mode anatomy hiện `POST-ENTRY OUTCOME`, hatch xanh giữ trạng thái partial đúng tại entry |
| `tools/validate_ea_delivery_packet.py` | completion gate fail-closed: rehash logic/source/run/log/analysis/casebook trước khi được gọi EA development hoàn tất |
| `schemas/ea_delivery_packet.v1.schema.json` | schema máy cho packet closeout logic → backtest → forensics |
| `data/<broker>/<symbol>/` | data shelf thị trường (parquet + manifest hash-bound); rules trong `data/README.md` |
| `runs/<EA>/<run_id>/` | evidence của run: report, run_manifest, `analysis/`, `logs/` |
| `runs.db` + `tools/runs_db.py` | catalog run (chỉ là index, không phải thẩm quyền) |
| `tools/backtest_storage_inventory.py` | inventory dung lượng, top file, orphan/generated file và mirror candidate; không xóa |
| `tools/large_log_reader.py` | inspect/search/window log triệu dòng bằng streaming, output bị cap và hash-bound |
| `external/` | dữ liệu external machine-local bị gitignore; paid CME chain ở `external/cme_fx_options_euro/`, public CME SDR ở `external/cme_sdr_fx/`, CME daily volume ở `external/cme_daily_volume/`, SGE SHAU archive ở `external/sge_shau_auction/`, Cboe source-feasibility files ở `external/cboe_fx_vol/`; không giữ corpus trên `C:` |
| `tools/acquire_cme_sdr_fx.py` + `profile_cme_sdr_fx_options.py` | acquisition/profile outcome-blind từ official CME FTP; exclude hourly fragments và 2024+ holdout, hash manifest, fail temporal-continuity trước prereg |
| `tools/acquire_cme_daily_volume.py` + `extract_cme_daily_fx_participation.py` | acquire/hash official daily-volume XLSX và extract exact EC/BP/J1 futures participation rows; outcome-blind source gate trước prereg/probe |
| `tools/acquire_sge_shau_auction.py` + `profile_sge_shau_auction.py` | acquire/parse official SGE fixing-round archive on D; density profile plus fail-closed publication/version provenance gate before prereg/outcomes |
| `tools/cme_fx_options_inventory.py` | hash + kiểm schema/coverage fail-closed cho CVOL và full EUR/USD option chain trước hypothesis mới |
| `tools/databento_fx_options_acquire.py` | Databento `GLBX.MDP3` plan → cost-ceiling submit → D-side download; `plan` không gọi time-series tính phí |
| `tools/configure_databento_key.ps1` | nhập kín API key vào Windows user environment; không ghi secret vào repo/artifact/log |
| `tools/dedupe_backtest_log_mirrors.ps1` | dry-run/convert mirror `logs` và `analysis/logs` giống hệt thành hardlink |
| `tools/archive_backtest_artifacts.ps1` | retention dry-run có plan atomic/contained; EA scope bắt buộc; protect run ID từ control docs + hot detail; archive off-volume theo copy/hash-verify/remove |
| `tools/workspace_hygiene.ps1` | inventory root sample/stale worktree mặc định; chỉ xóa hoặc rebuild `runs.db` khi có `-Execute` |
| `analysis/unified_validation.py` | validator; đồng thời định nghĩa artifact promotion-eligible phải trông thế nào |
| `analysis/walk_forward.py`, `robustness_suite.py`, `cscv_pbo.py`, `white_reality_check.py` | producer diagnostic-only (`promotion_eligible=false` theo thiết kế) |
| `tools/build_verified_cost_artifact.py` | artifact cost thực thi đã xác minh từ lifecycle telemetry generic/legacy + cost-source manifest |
| `schemas/execution_data_capture_manifest.v1.schema.json` | schema bundle broker quote/heartbeat/commission/slippage với safety và sample gates đóng băng |
| `tools/execution_data_foundation.py` | probe MT5 read-only, validate bundle và inventory evidence; không có mutating trade-call surface |
| `tools/impact_pressure_probe.py` | proxy probe M15 read-only đóng băng cho V5; dùng Bid/Ask ticks, matched return-z control, hash artifact; không phải Strategy Tester hay promotion evidence |
| `tools/research_cost_stress.py` | proxy cost stress cấp research (chỉ để falsify vòng đầu) |
| `tools/audit_mql5_nonrepaint.py` | audit non-repaint sau mọi thay đổi signal/data-access |
| `STRATEGY_LOG.md` | sử ký toàn bộ chiến lược đã test, kết quả, bài học (tiếng Việt) |
| `DECISION_FRAMEWORK.md` | cây quyết định ITERATE/PIVOT/ABANDON (impl: `analysis/decision_framework.py`) |
| `tools/` (còn lại) | probe/analyzer; tên file tự mô tả |

## Tests

| Path | Mở khi |
|---|---|
| `02. AlphaFactory/tests/test_operational_hygiene.py` | regression offline cho dry-run cleanup, archive protect roots/containment, validator encoding, registry pins và runbook command surface |
| `02. AlphaFactory/tests/test_ea_golden_path.py` | regression generic discovery, registry, capability, dry-run và comparator |
| `02. AlphaFactory/tests/test_ea_delivery_packet.py` | regression packet hợp lệ, tamper/missing evidence, full chart anatomy và zero-trade branch |
| `00. Old File/root_scratch_20260715/tests/` | stale `.pyc` lịch sử; archive-only, không dùng làm test hiện hành |

## Phần còn lại

| Path | Ghi chú |
|---|---|
| `docs/` | report độc lập: E8 symbol audit, EA audit, paper deploy guide, TraderViet research control, `handoff/` |
| `00. Old File/` | **một nhà archive** — `EA_Archive/` + `docs_archive/` + `tests_archive/` + `agent_guidance_archive/` + `git_metadata_archive/`; KHÔNG BAO GIỜ là nguồn compile/evidence hợp lệ |
| `00. Old File/docs_archive/` | gồm `README-SONIC-R*` (historical + pointer stub) và `SYNC_REPORT*` — **không** còn file README/SYNC ở root |
| `00. Old File/project_control_archive_20260716/cleanup_receipts/` | receipt cleanup (archived); mở khi audit move/xóa/giữ |
