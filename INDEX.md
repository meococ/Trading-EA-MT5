# INDEX — Bản Đồ Workspace

Cập nhật: 2026-07-15

Mỗi entry một dòng: file gì, mở khi nào. File này chỉ chứa con trỏ; nội
dung nằm ở đích đến. Cập nhật khi một file canonical bị di chuyển hoặc mở
lane mới — không cập nhật cho từng run/readout mới.

## Chuỗi đọc-trước (mọi session)

1. `CLAUDE.md` / `AGENTS.md` — quy tắc vận hành (root, entry tự nạp)
2. `04. Project Control/ai/hot.md` — sự thật SỐNG: lane, blocker, next moves
3. `01. GOAL/GOAL.md` — mục tiêu; chỉ đổi khi Owner quyết
4. Git có thể tồn tại (Owner đã mở remote private) nhưng **agent mặc định
   không stage/commit/push** trừ khi Owner yêu cầu rõ trong message hiện tại.
   Xác minh bằng receipt/hash/validator — không “dọn GitHub” tự ý. Chi tiết:
   `AGENTS.md`.
5. Trước hypothesis/EA mới: `04. Project Control/ai/do_not_repeat_failures.md`
   + registry — tránh lặp dead end đã kill.

## Doc điều khiển — `04. Project Control/ai/`

| File | Mở khi |
|---|---|
| `hot.md` | bắt đầu session; mọi câu hỏi "hiện tại cái gì đang đúng" |
| `sonic_validation_gates.md` | chấm bất kỳ run nào: stage, ngưỡng, hard invalidation |
| `research_doctrine.md` | thiết kế/review hypothesis: contract registry, nhãn, budget chống overfit, team review, quy tắc MT5, vệ sinh backtest |
| `workflow.md` | vòng đời phát triển (ideate -> research -> prereg -> develop -> validate) |
| `sonic_tool_runbook.md` | lệnh chính xác: compile / backtest / validate / analyze / cleanup |
| `ea_engineering_standard.md` | viết hoặc review code MQL5 |
| `current_state.md` | context session sâu hơn hot.md |
| `source_of_truth.md` / `.json` + `validate_source_of_truth.py` | registry fact canonical và validator của nó |
| (root) `.codex/operator/STATUS.md` + `EXPERIMENTS.jsonl` | ledger recovery cho task dài; chỉ operational, luôn nhường sự thật sống cho `hot.md` |
| `forward_test_protocol.md` | quy tắc forward/demo test |
| `run_data_policy.md` | dữ liệu run nào được giữ hoặc xóa |
| `do_not_repeat_failures.md` | EA/approach đã fail + pointer evidence; đọc trước khi đề xuất revive |
| `agent_ea_research_loop.md` | contract vòng lặp EA manager/worker có gate evidence cho lane tự hành |
| `process_receipts/20260713_FAILURE_DEEP_RESEARCH_LOOP_V1.json` | receipt hash-bound cho rule failure/hiệu suất yếu -> Deep Research hypothesis mới, không post-hoc rescue |
| `goal_receipts/20260713_DEEP_RESEARCH_V4_DATA_ACQUISITION_GOAL.json` | receipt goal V4 đã close: foundation sẵn sàng nhưng data chưa đạt gate, không mở quyền build |
| `data_contracts/20260713_EXECUTION_DATA_ACQUISITION_CONTRACT_V1.md` | contract no-live cho quote/heartbeat/commission/slippage, schema hash và stop rules QFSI |
| `session_anchor.md` | anchor khởi động legacy (2026-05-01); nhường `hot.md`/`current_state.md` khi mâu thuẫn |
| `mcp_policy.md` | thứ tự tin cậy cho output MCP/tool ngoài |
| `ea_rd_tooling_roadmap.md` | roadmap tooling (2026-05-01) |

## Nghiên cứu — `03. EA Developer/EA_SonicR/research/`

| File | Mở khi |
|---|---|
| `CANDIDATE_REGISTRY.jsonl` + `.schema.json` + `validate_candidate_registry.py` | ledger nghiên cứu FX toàn workspace tại path tương thích cũ; TRƯỚC mọi run có ý nghĩa: append/validate row hypothesis |
| `PREREG_TEMPLATE.md`, `READOUT_TEMPLATE.md` | viết prereg hoặc readout |
| `20260712_NEW_STRATEGY_DEEP_RESEARCH_PACKET_V2.md` | packet Browser -> ChatGPT authoritative cho lane strategy mới; bắt buộc `+ -> Nghiên cứu sâu` + `Pro`, chưa cấp quyền prereg/code/run; V1 lịch sử không phải Deep Research evidence |
| `readouts/20260713_DEEP_RESEARCH_V2_COORDINATOR_AUDIT.md` | audit local của báo cáo V2; kill benchmark-fix candidate vì trùng S214-S217/S532/S564 |
| `20260713_NEW_STRATEGY_DEEP_RESEARCH_FAILURE_PACKET_V3.md` | failure packet cho vòng Deep Research kế tiếp; khóa toàn bộ fix/benchmark/session-timing family |
| `preflight/20260713_NEW_STRATEGY_DEEP_RESEARCH_SUBMISSION_V3.json` | receipt UI/hash và kết quả V3 `NO_LEGAL_CANDIDATE`; frontier dừng theo contract dữ liệu/chi phí hiện tại |
| `readouts/20260713_DEEP_RESEARCH_V3_COORDINATOR_AUDIT.md` | audit V3: cross-check local event drift/S703, chốt không có candidate hợp lệ và điều kiện dữ liệu để mở lại |
| `readouts/20260713_DEEP_RESEARCH_V4_COORDINATOR_INTAKE.md` | intake V4: data-acquisition-only cho QFSI/GVBCI; chưa có strategy probe hay quyền build EA |
| `readouts/20260713_V4_DATA_FOUNDATION_COORDINATOR_READOUT.md` | closeout foundation: QFSI STOP, GVBCI cost-quote-only, SCFIS excluded, không có strategy authority |
| `readouts/20260713_DEEP_RESEARCH_V5_COORDINATOR_INTAKE.md` | intake V5: kill round-number duplicate, chỉ cho phép đúng một proxy probe Impact-per-Pressure với matched return control; chưa cấp quyền code EA |
| `readouts/20260713_IMPACT_PRESSURE_PROXY_PROBE_READOUT.md` | probe V5 offline đã `KILL_AT_OFFLINE_PROBE`; đóng trước registry/prereg/code |
| `readouts/20260713_REDTEAM_V5_KILL_V6_FRONTIER_COORDINATOR.md` | redteam 3 vai + coordinator: affirm kill V5; không EA build ngay; search chỉ qua V6 |
| `20260713_NEW_STRATEGY_DEEP_RESEARCH_FAILURE_PACKET_V6.md` | failure packet V6 khóa toàn bộ rescue/rename V5 và yêu cầu đúng một hypothesis độc lập hoặc NO LEGAL CANDIDATE |
| `preflight/20260713_NEW_STRATEGY_DEEP_RESEARCH_SUBMISSION_V6.json` | receipt UI/hash V6: GPT-5.6 Sol + Pro + Nghiên cứu sâu đã được readback trước khi chạy |
| `preflight/20260713_NEW_STRATEGY_DEEP_RESEARCH_RESULT_V6.json` | receipt kết quả V6: `NO LEGAL CANDIDATE`, hash audit và toàn bộ quyền probe/build đều false |
| `readouts/20260713_DEEP_RESEARCH_V6_COORDINATOR_AUDIT.md` | audit V6: ba near-miss đều sai data/timescale nếu ép vào MT5; dừng frontier, không goal/EA/V7 tự động |
| `20260713_NEW_STRATEGY_DEEP_RESEARCH_SCOPE_EXPANSION_V7.md` | packet V7 do Owner mở scope H4/D1 đa cặp; tìm đúng một mechanism độc lập hoặc NO CANDIDATE, chưa cấp quyền probe/code/run |
| `preflight/20260713_NEW_STRATEGY_DEEP_RESEARCH_SUBMISSION_V7.json` | receipt UI/hash V7: GPT-5.6 Sol + Pro + Nghiên cứu sâu, plan H4/D1 đang chạy tại conversation URL được ghi |
| `readouts/20260713_V7_H4_D1_LOCAL_DEDUP_BASELINE.md` | baseline de-dup được đóng băng trước khi đọc kết quả V7; khóa các H4/D1/consensus/trend/proxy family cũ, không cấp quyền build |
| `preflight/20260713_NEW_STRATEGY_DEEP_RESEARCH_RESULT_V7.json` | receipt kết quả V7: không candidate H4/D1, năm family bị loại và toàn bộ quyền probe/build đều false |
| `readouts/20260713_DEEP_RESEARCH_V7_COORDINATOR_AUDIT.md` | audit V7: source mạnh cần flow/carry/liquidity/external series; price-only trùng family cũ, dừng frontier và không build EA |
| `readouts/20260713_OWNER_1A_GROK_PANEL_V7_STOP_COORDINATOR.md` | Owner 1A fail-closed + panel grok; V8 draft carry rates; chưa compile |
| `20260713_NEW_STRATEGY_DEEP_RESEARCH_DATA_CONTRACT_V8.md` | packet V8 rates-only; Deep Research submit `BLOCKED_BY_BROWSER_AUTH` tới khi Owner login ChatGPT |
| `readouts/20260713_V8_EXOGENOUS_LOCAL_DEDUP_BASELINE.md` | baseline de-dup trước V8 result |
| `readouts/20260713_V8_EXOGENOUS_DATA_ACQUISITION_INVENTORY.md` | inventory lịch sử; rates đã có — xem readiness |
| `readouts/20260713_V8_G3_RATES_PANEL_READINESS.md` | panel G3 rates đã hash; chờ ChatGPT login rồi submit V8 |
| `readouts/20260713_V8_RATES_ACQUISITION_READOUT.md` | acquisition hash-bound Treasury/ECB/BoE + Phase 0 identity draft |
| `readouts/20260713_V8_CARRY_DIFF_OFFLINE_PROBE_READOUT.md` | weekly carry offline probe `KILL_AT_OFFLINE_PROBE` (PF cao, cadence chết) |
| `preflight/20260713_PHASE0_UNIVERSE_IDENTITY_INVENTORY_DRAFT_V1.json` | draft universe identity-only 225 members; chưa freeze Phase 0 |
| `readouts/20260713_OWNER_DECISION_CONFIRM_V8_SUBMIT.md` | blocker auth ChatGPT; Owner login Browser rồi resume submit V8 |
| `preflight/20260713_NEW_STRATEGY_DEEP_RESEARCH_SUBMISSION_V8.json` | attempt V8: `BLOCKED_BY_BROWSER_AUTH`; packet hash đã ghi |
| `20260713_GVBCI_DATA_ACQUISITION_FEASIBILITY.md` | assessment CME/Databento về license, cost, timestamp, roll và exact quote request cho GC |
| `preflight/v4_data/` | probe/inventory/quote-request/receipt hash-bound của lane data V4; tester proxy không phải broker evidence |
| `preregs/` | prereg đã đóng băng và draft được gắn nhãn rõ; luôn đọc status banner trước khi dùng |
| `20260711_CODEX_EXECUTION_PLAN_V2.md` | kế hoạch authoritative cho lane FX portfolio/SilverBullet; Phase 0 đã implement nhưng clearance và Phase 1+ bị chặn |
| `preflight/20260711_PHASE0_ARTIFACT_SUFFICIENCY_V1.json` | verdict machine-readable chỉ về độ đủ artifact; cả hai probe `BLOCKED` và có contamination record bắt buộc clean review |
| `preflight/20260711_PHASE0_COORDINATION_CONTAMINATION_ATTESTATION_V1.json` | attestation hash-bound cho accidental `RunMeta` display; không chứa outcome value và buộc clean future review |
| `preregs/20260711_H_SB_WEEKEND_FLAT_001_PREREG.md` | draft A1 weekend-flat, chưa đóng băng; A2 max-hold là child tương lai riêng |
| `preregs/20260713_H_SB_WEEKEND_FLAT_001_RESEARCH_FREEZE.md` | research freeze Model 0 weekend-flat A1 (Owner self-research) |
| `preflight/20260714_OWNER_MT_BACKTEST_AUTONOMY_RECEIPT.json` | Owner MT-backtest autonomy campaign receipt (status + selected path) |
| `readouts/20260714_OWNER_MT_BACKTEST_AUTONOMY_COORDINATOR.md` | coordinator merge: path selection + Model 0 status toward GOAL |
| `preflight/20260714_STRATEGY_REBUILD_CAMPAIGN_RECEIPT.json` | Owner rebuild/refine campaign receipt (2026-07-14); status `GOAL_NEAR_MISS` |
| `readouts/20260714_STRATEGY_REBUILD_CAMPAIGN_COORDINATOR.md` | rebuild matrix + Model 0 results; MaxKZ2 research-bar survivor |
| `preregs/20260711_H_PORTFOLIO_COMPOSE_001_PREREG.md` | draft composition exact-universe, cấm chọn per-EA best theo outcome |
| `20260710_EA_FAILURE_PORTFOLIO_AUDIT.md` | vì sao 217 runs / 34 EA trượt mục tiêu; evidence về frontier |
| `20260711_BROKER_COST_PROVENANCE_AUDIT.md` | blocker cost-data hiện tại và điều kiện mở lại |
| `SONIC_SOURCE_INVENTORY.md`, `SONIC_RULES_MATRIX.md`, `SONIC_PARITY_SPEC.md` | spec source-parity của Sonic |
| `label_packets/`, `mt5_snapshot/` | nhãn chart-state đã khóa và snapshot |
| các file `*_READOUT.md` có ngày | kết quả thí nghiệm cũ (registry row trỏ tới) |

## Source EA — `03. EA Developer/` (active only)

| Path | Ghi chú |
|---|---|
| `EA_SonicR/EA_SonicR.mq5` | source Sonic canonical (research-only) |
| `EA_SonicR/Include/SNR_Telemetry.mqh` | writer lifecycle `sonic_telemetry.v3` (emitter v3 duy nhất) |
| `EA_SonicR/research/` | research ledger toàn workspace — **không archive**; registry/prereg/readout ở đây |
| `EA_SilverBullet/EA_SilverBullet_v2.mq5` | source SilverBullet đã pin bởi shared runner contract; Index/`*_backup*` đã archive — xem package `README.md` |
| `EA_SilverBullet/README.md` / `EA_SonicR/README.md` | pointer package-level (lane + pin / research-only) |
| `00. Old File/EA_Archive/` | **119** package EA shelf/failed/duplicate (2026-07-15) + `EA_SilverBullet_dead_siblings/`; không phải nguồn compile/evidence hợp lệ; xem `MANIFEST_20260715_workspace_cleanup.json` |

## AlphaFactory — `02. AlphaFactory/`

| Path | Mở khi |
|---|---|
| `alpha.ps1` | lane compile / backtest / validate-full (cú pháp trong runbook) |
| `tools/ea_contract.ps1` | resolver fail-closed cho exact main source và telemetry profile từng EA; dùng chung bởi `alpha.ps1` và research loop |
| `runs/<EA>/<run_id>/` | evidence của run: report, run_manifest, `analysis/`, `logs/` |
| `runs.db` + `tools/runs_db.py` | catalog run (chỉ là index, không phải thẩm quyền) |
| `tools/backtest_storage_inventory.py` | inventory dung lượng, top file, orphan/generated file và mirror candidate; không xóa |
| `tools/large_log_reader.py` | inspect/search/window log triệu dòng bằng streaming, output bị cap và hash-bound |
| `tools/dedupe_backtest_log_mirrors.ps1` | dry-run/convert mirror `logs` và `analysis/logs` giống hệt thành hardlink |
| `tools/archive_backtest_artifacts.ps1` | retention dry-run có plan; archive off-volume theo copy/hash-verify/remove |
| `analysis/unified_validation.py` | validator; đồng thời định nghĩa artifact promotion-eligible phải trông thế nào |
| `analysis/walk_forward.py`, `robustness_suite.py`, `cscv_pbo.py`, `white_reality_check.py` | producer diagnostic-only (`promotion_eligible=false` theo thiết kế) |
| `tools/build_verified_cost_artifact.py` | artifact cost thực thi đã xác minh (đòi telemetry v3 + cost-source manifest) |
| `schemas/execution_data_capture_manifest.v1.schema.json` | schema bundle broker quote/heartbeat/commission/slippage với safety và sample gates đóng băng |
| `tools/execution_data_foundation.py` | probe MT5 read-only, validate bundle và inventory evidence; không có mutating trade-call surface |
| `tools/impact_pressure_probe.py` | proxy probe M15 read-only đóng băng cho V5; dùng Bid/Ask ticks, matched return-z control, hash artifact; không phải Strategy Tester hay promotion evidence |
| `tools/sonic_cost_stress.py` | proxy cost stress cấp research (chỉ để falsify vòng đầu) |
| `tools/audit_mql5_nonrepaint.py` | audit non-repaint sau mọi thay đổi signal/data-access |
| `tools/sonic_research_loop.ps1` | runner full-loop cho nghiên cứu |
| `STRATEGY_LOG.md` | sử ký toàn bộ chiến lược đã test, kết quả, bài học (tiếng Việt) |
| `DECISION_FRAMEWORK.md` | cây quyết định ITERATE/PIVOT/ABANDON (impl: `analysis/decision_framework.py`) |
| `tools/` (còn lại) | probe/analyzer; tên file tự mô tả |

## Tests — `tests/`

Bộ pytest/unittest + `runner/runner_contract_tests.ps1` bảo vệ pipeline:
candidate registry, non-repaint audit, validation hardening, verified cost
builder, runner contract, SilverBullet exposure controls (pin
`EA_SilverBullet_v2.mq5`), signal equivalence.
Path EA chỉ còn `EA_SonicR` + `EA_SilverBullet` dưới `03. EA Developer/`.
Chạy trước khi tin bất kỳ thay đổi framework nào. MT5 live không bắt buộc
cho smoke contract/path.

## Phần còn lại

| Path | Ghi chú |
|---|---|
| `README-SONIC-R.md` | pointer Sonic hiện tại (không còn knowledge dump); lịch sử → `00. Old File/docs_archive/` |
| `SYNC_REPORT.md` | stub trỏ archive; report lean-copy 2026-06-21 → `00. Old File/docs_archive/SYNC_REPORT_20260621.md` |
| `docs/` | report độc lập: E8 symbol audit, EA audit, paper deploy guide, TraderViet research control, `handoff/` |
| `AlphaTester/<run_id>/` | thư mục config tester thô của đợt 2026-06-21; bản evidence đã phân tích nằm ở `02. AlphaFactory/runs/` |
| `00. Old File/` | **một nhà archive** — README + `EA_Archive/` + `docs_archive/` + `agent_guidance_archive/` + `git_metadata_archive/`; KHÔNG BAO GIỜ là nguồn compile/evidence hợp lệ |
| `04. Project Control/ai/cleanup_receipts/` | receipt cleanup (gồm `20260715_workspace_ea_archive.json`, `20260715_stale_surface_cleanup*`); mở khi audit move/xóa/giữ |
