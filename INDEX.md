# INDEX — Bản Đồ Workspace

Cập nhật: 2026-07-16

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

## Doc điều khiển — `04. Memory/` (state) + `05. Playbook/` (rules)

**`04. Memory/`** — trí nhớ sống:

| File | Mở khi |
|---|---|
| `hot.md` | bắt đầu session; "hiện tại cái gì đang đúng" (NEXT SESSION + ledger) |
| `do_not_repeat_failures.md` | trước khi đề xuất revive / hyp mới |
| `source_of_truth.md`/`.json` + `validate_source_of_truth.py` | registry fact/path canonical + validator fail-closed |
| `research/CANDIDATE_REGISTRY.jsonl` + schema + validator | ledger hypothesis generic append-only; validate trước mọi run có ý nghĩa |

**`05. Playbook/`** — 5 file chỉ dẫn lõi:

| File | Mở khi |
|---|---|
| `sonic_validation_gates.md` | chấm run: stage, ngưỡng, hard invalidation |
| `sonic_tool_runbook.md` | lệnh chính xác: compile/backtest/validate/analyze |
| `ea_golden_path.md` | đường generic từ brief → de-dup/probe → code → Model 0 → quyết định |
| `ea_engineering_standard.md` | viết/review code MQL5 (closed-bar, non-repaint) |
| `research_doctrine.md` | thiết kế hypothesis: registry, prereg, overfit budget, MT5 rules |

**Đã archive** (không active surface) → `00. Old File/project_control_archive_20260716/`:
workflow, multi_agent_roster + `agents/`, agent_ea_research_loop, run_data_policy,
forward_test_protocol, mcp_policy, `skills/`, receipts (cleanup/process/goal),
data_contracts, current_state, session_anchor, ea_rd_tooling_roadmap, DRAFT.

| Khác | Mở khi |
|---|---|
| `.codex/operator/STATUS.md` + `EXPERIMENTS.jsonl` | ledger recovery task dài; operational, nhường `hot.md` |

## Nghiên cứu — generic active + lịch sử archive

| Path | Mở khi |
|---|---|
| `04. Memory/research/CANDIDATE_REGISTRY.jsonl` + schema + validator | ledger active dùng chung mọi EA; source/prereg hash-bound, transition fail-closed |
| `02. AlphaFactory/templates/research/` | tạo capability contract, prereg/readout và kiểm trường task packet |
| `03. EA Developer/<EA>/research/` | prereg/readout/evidence riêng package active |
| `00. Old File/EA_Archive/EA_SonicR/research/` | ledger và evidence Sonic lịch sử; archive-only, không chạy |

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
| `tools/ea_contract.ps1` | resolver fail-closed exact source + package capability contract; archive không hợp lệ |
| `tools/ea_research_loop.ps1` | entry generic dry-run mặc định cho control/challenger Model 0 |
| `tools/sonic_research_loop.ps1` | compatibility engine phía sau generic entry; không dùng như workflow Sonic-only mới |
| `tools/alpha_candidate_compare.py` | comparator generic identity + control-relative, không hardcode gate Sonic |
| `runs/<EA>/<run_id>/` | evidence của run: report, run_manifest, `analysis/`, `logs/` |
| `runs.db` + `tools/runs_db.py` | catalog run (chỉ là index, không phải thẩm quyền) |
| `tools/backtest_storage_inventory.py` | inventory dung lượng, top file, orphan/generated file và mirror candidate; không xóa |
| `tools/large_log_reader.py` | inspect/search/window log triệu dòng bằng streaming, output bị cap và hash-bound |
| `tools/dedupe_backtest_log_mirrors.ps1` | dry-run/convert mirror `logs` và `analysis/logs` giống hệt thành hardlink |
| `tools/archive_backtest_artifacts.ps1` | retention dry-run có plan atomic/contained; EA scope bắt buộc; protect run ID từ control docs + hot detail; archive off-volume theo copy/hash-verify/remove |
| `tools/workspace_hygiene.ps1` | inventory root sample/stale worktree mặc định; chỉ xóa hoặc rebuild `runs.db` khi có `-Execute` |
| `analysis/unified_validation.py` | validator; đồng thời định nghĩa artifact promotion-eligible phải trông thế nào |
| `analysis/walk_forward.py`, `robustness_suite.py`, `cscv_pbo.py`, `white_reality_check.py` | producer diagnostic-only (`promotion_eligible=false` theo thiết kế) |
| `tools/build_verified_cost_artifact.py` | artifact cost thực thi đã xác minh từ lifecycle telemetry generic/legacy + cost-source manifest |
| `schemas/execution_data_capture_manifest.v1.schema.json` | schema bundle broker quote/heartbeat/commission/slippage với safety và sample gates đóng băng |
| `tools/execution_data_foundation.py` | probe MT5 read-only, validate bundle và inventory evidence; không có mutating trade-call surface |
| `tools/impact_pressure_probe.py` | proxy probe M15 read-only đóng băng cho V5; dùng Bid/Ask ticks, matched return-z control, hash artifact; không phải Strategy Tester hay promotion evidence |
| `tools/sonic_cost_stress.py` | proxy cost stress cấp research (chỉ để falsify vòng đầu) |
| `tools/audit_mql5_nonrepaint.py` | audit non-repaint sau mọi thay đổi signal/data-access |
| `STRATEGY_LOG.md` | sử ký toàn bộ chiến lược đã test, kết quả, bài học (tiếng Việt) |
| `DECISION_FRAMEWORK.md` | cây quyết định ITERATE/PIVOT/ABANDON (impl: `analysis/decision_framework.py`) |
| `tools/` (còn lại) | probe/analyzer; tên file tự mô tả |

## Tests

| Path | Mở khi |
|---|---|
| `02. AlphaFactory/tests/test_operational_hygiene.py` | regression offline cho dry-run cleanup, archive protect roots/containment, validator encoding, registry pins và runbook command surface |
| `02. AlphaFactory/tests/test_ea_golden_path.py` | regression generic discovery, registry, capability, dry-run và comparator |
| `00. Old File/root_scratch_20260715/tests/` | stale `.pyc` lịch sử; archive-only, không dùng làm test hiện hành |

## Phần còn lại

| Path | Ghi chú |
|---|---|
| `docs/` | report độc lập: E8 symbol audit, EA audit, paper deploy guide, TraderViet research control, `handoff/` |
| `00. Old File/` | **một nhà archive** — `EA_Archive/` + `docs_archive/` + `tests_archive/` + `agent_guidance_archive/` + `git_metadata_archive/`; KHÔNG BAO GIỜ là nguồn compile/evidence hợp lệ |
| `00. Old File/docs_archive/` | gồm `README-SONIC-R*` (historical + pointer stub) và `SYNC_REPORT*` — **không** còn file README/SYNC ở root |
| `00. Old File/project_control_archive_20260716/cleanup_receipts/` | receipt cleanup (archived); mở khi audit move/xóa/giữ |
