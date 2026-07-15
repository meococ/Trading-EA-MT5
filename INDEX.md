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
| `agent_ea_research_loop.md` | contract vòng lặp EA manager/worker có gate evidence + Failure Triage trước Deep Research |
| `multi_agent_roster.md` | roster session (red-team/research/impl/qc) + model pin Grok; chốt phiên §E (docs / self-improve merge / cleanup); specs trong `agents/` |
| `agents/` | role specs, SESSION memory, TASK_PACKET / MERGE_MEMO / SESSION_CLOSEOUT templates |
| `skills/session-closeout/` | chốt phiên A/B/C checklist (canonical); twin local `.cursor/skills/session-closeout/` |
| `DRAFT_multi_agent_roster_and_failure_loop_20260715.md` | pointer lịch sử → `multi_agent_roster.md` (đã approve) |
| (local, gitignored) `.cursor/agents/ea-*.md` + `.cursor/skills/{failure-triage,chart-state-probe,session-closeout}/` | launcher mỏng + skill triage/chart-state/closeout; canonical roster/skills dưới `04.../agents/` + `04.../skills/` |
| `process_receipts/20260713_FAILURE_DEEP_RESEARCH_LOOP_V1.json` | receipt hash-bound cho rule failure/hiệu suất yếu -> Deep Research hypothesis mới, không post-hoc rescue |
| `goal_receipts/20260713_DEEP_RESEARCH_V4_DATA_ACQUISITION_GOAL.json` | receipt goal V4 đã close: foundation sẵn sàng nhưng data chưa đạt gate, không mở quyền build |
| `data_contracts/20260713_EXECUTION_DATA_ACQUISITION_CONTRACT_V1.md` | contract no-live cho quote/heartbeat/commission/slippage, schema hash và stop rules QFSI |
| `session_anchor.md` | anchor khởi động legacy (2026-05-01); nhường `hot.md`/`current_state.md` khi mâu thuẫn |
| `mcp_policy.md` | thứ tự tin cậy cho output MCP/tool ngoài |
| `ea_rd_tooling_roadmap.md` | roadmap tooling (2026-05-01) |

## Nghiên cứu — archived ledger

**Owner archive 2026-07-15:** research ledger moved with the package.

Base path: `00. Old File/EA_Archive/EA_SonicR/research/`

| File (relative to base) | Mở khi |
|---|---|
| `CANDIDATE_REGISTRY.jsonl` + `.schema.json` + `validate_candidate_registry.py` | ledger nghiên cứu FX; TRƯỚC mọi run có ý nghĩa: append/validate row hypothesis — **path archived**, not active surface |
| `PREREG_TEMPLATE.md`, `READOUT_TEMPLATE.md` | viết prereg hoặc readout (archive copy) |
| `preregs/`, `readouts/`, `preflight/` | prereg/readout/preflight lịch sử (registry row trỏ tới) |
| `20260710_EA_FAILURE_PORTFOLIO_AUDIT.md` | audit frontier 217 runs / 34 EA |
| chi tiết file dated khác | xem folder archive; INDEX không còn liệt kê từng readout như surface active |

## Source EA — `03. EA Developer/` (active shelf **empty**)

| Path | Ghi chú |
|---|---|
| `03. EA Developer/README.md` | active shelf empty (2026-07-15); pointer tới Old File + `hot.md` |
| `00. Old File/EA_Archive/EA_SonicR/` | full SonicR package + research ledger (archived) |
| `00. Old File/EA_Archive/EA_SilverBullet/` | full SilverBullet package (archived) |
| `00. Old File/EA_Archive/` | shelf/failed/duplicate packages + manifests; **không** compile làm evidence |

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

## Tests — archived

Root `tests/` đã chuyển (2026-07-15) →
`00. Old File/tests_archive/tests_20260715/`.
Không còn bộ test active ở root. Harness AlphaFactory vẫn ở
`02. AlphaFactory/`.

## Phần còn lại

| Path | Ghi chú |
|---|---|
| `docs/` | report độc lập: E8 symbol audit, EA audit, paper deploy guide, TraderViet research control, `handoff/` |
| `00. Old File/` | **một nhà archive** — `EA_Archive/` + `docs_archive/` + `tests_archive/` + `agent_guidance_archive/` + `git_metadata_archive/`; KHÔNG BAO GIỜ là nguồn compile/evidence hợp lệ |
| `00. Old File/docs_archive/` | gồm `README-SONIC-R*` (historical + pointer stub) và `SYNC_REPORT*` — **không** còn file README/SYNC ở root |
| `04. Project Control/ai/cleanup_receipts/` | receipt cleanup (gồm archive moves 2026-07-15); mở khi audit move/xóa/giữ |
