# INDEX — Bản Đồ Workspace

Cập nhật: 2026-07-15

Mỗi entry một dòng: file gì, mở khi nào. File này chỉ chứa con trỏ; nội
dung nằm ở đích đến. Cập nhật khi một file canonical bị di chuyển hoặc mở
lane mới — không cập nhật cho từng run/readout mới.

## Chuỗi đọc-trước (mọi session)

1. `CLAUDE.md` / `AGENTS.md` — quy tắc vận hành (root, entry tự nạp)
2. `04. Memory/hot.md` — sự thật SỐNG: lane, blocker, next moves
3. `01. GOAL/GOAL.md` — mục tiêu; chỉ đổi khi Owner quyết
4. Git có thể tồn tại (Owner đã mở remote private) nhưng **agent mặc định
   không stage/commit/push** trừ khi Owner yêu cầu rõ trong message hiện tại.
   Xác minh bằng receipt/hash/validator — không “dọn GitHub” tự ý. Chi tiết:
   `AGENTS.md`.
5. Trước hypothesis/EA mới: `04. Memory/do_not_repeat_failures.md`
   + registry — tránh lặp dead end đã kill.

## Doc điều khiển — `04. Memory/` (state) + `05. Guidance/` (rules)

**`04. Memory/`** — trí nhớ sống:

| File | Mở khi |
|---|---|
| `hot.md` | bắt đầu session; "hiện tại cái gì đang đúng" (NEXT SESSION + ledger) |
| `do_not_repeat_failures.md` | trước khi đề xuất revive / hyp mới |
| `source_of_truth.md`/`.json` + `validate_source_of_truth.py` | registry fact canonical + validator fail-closed |

**`05. Guidance/`** — 4 file chỉ dẫn lõi:

| File | Mở khi |
|---|---|
| `sonic_validation_gates.md` | chấm run: stage, ngưỡng, hard invalidation |
| `sonic_tool_runbook.md` | lệnh chính xác: compile/backtest/validate/analyze |
| `ea_engineering_standard.md` | viết/review code MQL5 (closed-bar, non-repaint) |
| `research_doctrine.md` | thiết kế hypothesis: registry, prereg, overfit budget, MT5 rules |

**Đã archive** (không active surface) → `00. Old File/project_control_archive_20260716/`:
workflow, multi_agent_roster + `agents/`, agent_ea_research_loop, run_data_policy,
forward_test_protocol, mcp_policy, `skills/`, receipts (cleanup/process/goal),
data_contracts, current_state, session_anchor, ea_rd_tooling_roadmap, DRAFT.

| Khác | Mở khi |
|---|---|
| `.codex/operator/STATUS.md` + `EXPERIMENTS.jsonl` | ledger recovery task dài; operational, nhường `hot.md` |

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

## Source EA — `03. EA Developer/` (2 lane active)

| Path | Ghi chú |
|---|---|
| `03. EA Developer/README.md` | shelf pointer; 2 lane active (2026-07-15) |
| `03. EA Developer/EA_FVGConfluence/` | lane active (Owner Path-C); có `.mq5` + research |
| `03. EA Developer/EA_HybridICT_Sonic/` | lane active (Path-C stub, KILL@Model0); có `.mq5` + research |
| `00. Old File/EA_Archive/EA_SonicR/` | full SonicR ledger (archived THẬT 2026-07-15; bản duy nhất) |
| `00. Old File/EA_Archive/EA_SilverBullet/` | SilverBullet **binary-only** (`.ex5`; không còn source `.mq5` trên đĩa) |
| `00. Old File/EA_Archive/` | 80 dir archived (SonicR + SilverBullet + 78 stub `.ex5`) + manifest; **không** compile làm evidence |

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

Root `tests/` chỉ còn stale `.pyc` (không source), đã chuyển (2026-07-15) →
`00. Old File/root_scratch_20260715/tests/`. Không có bộ test active ở root
(source `.py` không còn trên đĩa — nếu cần xem git history). Harness
AlphaFactory vẫn ở `02. AlphaFactory/`.

## Phần còn lại

| Path | Ghi chú |
|---|---|
| `docs/` | report độc lập: E8 symbol audit, EA audit, paper deploy guide, TraderViet research control, `handoff/` |
| `00. Old File/` | **một nhà archive** — `EA_Archive/` + `docs_archive/` + `tests_archive/` + `agent_guidance_archive/` + `git_metadata_archive/`; KHÔNG BAO GIỜ là nguồn compile/evidence hợp lệ |
| `00. Old File/docs_archive/` | gồm `README-SONIC-R*` (historical + pointer stub) và `SYNC_REPORT*` — **không** còn file README/SYNC ở root |
| `00. Old File/project_control_archive_20260716/cleanup_receipts/` | receipt cleanup (archived); mở khi audit move/xóa/giữ |
