# INDEX — Bản Đồ Workspace

Cập nhật cấu trúc: 2026-08-06.

INDEX chỉ trả lời **nguồn nào dùng cho việc gì**. Không giữ metric run, trạng
thái từng hypothesis hay danh sách package dài; các dữ liệu động phải nằm ở
registry, package ledger và artifact canonical.

## Chuỗi đọc-trước

1. `AGENTS.md` — authority, hard rules và vai trò Lead Quant.
2. `01. GOAL/GOAL.md` — outcome kinh tế và định nghĩa DONE.
3. Registry/prereg/task packet liên quan + AlphaFactory status/lock — contract
   và quyền thực thi hiện tại.
4. `04. Memory/hot.md` — cache handoff ngắn; luôn verify bằng artifact.
5. Trước hypothesis/EA mới, tìm đúng mechanism/ID trong
   `04. Memory/do_not_repeat_failures.md` và registry để xác định failure radius;
   không cần nạp toàn bộ ledger cho một task hẹp.

Git có thể bẩn. Mặc định không stage/commit/push nếu Owner chưa yêu cầu rõ trong
message hiện tại. Evidence được xác minh bằng file/hash/validator/test.

## Bản đồ thẩm quyền

| Cần quyết định | Nguồn canonical | Không dùng thay thế |
|---|---|---|
| Outcome book và DONE | `01. GOAL/GOAL.md` | lane KILL, compile xanh, cache |
| Vai trò Lead Quant và hard rules | `AGENTS.md` | report hoặc sub-agent |
| Market/hypothesis/overfit/frontier | `05. Playbook/research_doctrine.md` | một prompt research |
| Vòng end-to-end EA | `05. Playbook/ea_golden_path.md` | plan/status update |
| Gate kinh tế/promotion | `05. Playbook/validation_gates.md` | PF/WR đứng riêng |
| Lệnh AlphaFactory | `05. Playbook/tool_runbook.md` | toolchain tự chế |
| Code/risk/execution MQL5 | `05. Playbook/ea_engineering_standard.md` | screenshot đẹp |
| Quyền hypothesis/run | registry + prereg + task packet + lock | package tồn tại |
| Trạng thái package | `03. EA Developer/README.md` + artifact | `INDEX.md`/`hot.md` |
| Đường dẫn canonical | `04. Memory/source_of_truth.json` + validator | đường dẫn nhớ lại |

## Điều khiển và trí nhớ

| Path | Mở khi |
|---|---|
| `04. Memory/hot.md` | handoff gần nhất; cache, không cấp/veto quyền |
| `04. Memory/research/PRO_TRADER_REPLACEMENT_CAMPAIGN.md` | biên bản duy nhất cho chuỗi strategy generation tuần tự T1→T100; một Tn active, chưa thay prereg/run authority |
| `04. Memory/research/PRO_TRADER_REPLACEMENT_E01_T1_P0_CHARTER.json` | charter T1 đã đóng băng trước outcome: 9 symbol, M5, 5 arm, 45 cell, all-history >97% |
| `04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_P0_CHARTER.json` | charter T2 đang active P0: Volman-inspired M5 causal price-action grammar, 9 symbol bắt buộc, 5 arm, 45 cell, all-history >97%, chưa cấp quyền MT5/economics |
| `04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_P1_SOURCE_MATRIX.md` | P1 lawful-source matrix: tách UPA M5 khỏi FPAS 70-tick, forum chỉ discovery, chưa phải economic evidence |
| `04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_P2_FORMAL_SPEC.md` | P2 exact closed-bar grammar đã independent-QC và SHA-frozen; authority chỉ synthetic fixtures/reference, chưa cấp `.mq5`/MT5/economics |
| `04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_P3_DEDUP_CONTRACT_V2.json` + `PRO_TRADER_REPLACEMENT_E02_T2_P3_EXECUTION_FREEZE_V1.json` | P3 outcome-blind D7/D8 contract và execution lock; 49 tests + prior SCC replay pass, không cấp build/economics |
| `03. EA Developer/EA_VolmanCausalGrammar/research/evidence/T2_P3_DEDUP_V1_ENGINEERING_BLOCKED/timeout_receipt.json` | T2/P3 full replay timeout 3,600s, không có result/count packet; engineering blocker, không phải strategy/edge verdict |
| `04. Memory/research/CAMPAIGN_EXPOSURE.jsonl` + schema/validator | machine ledger SHA-chain cho trial/alpha/split/data exposure; tách khỏi hypothesis registry để không làm vỡ reader cũ |
| `04. Memory/research/PRO_TRADER_REPLACEMENT_E01_T1_DATA_EPOCH.json` + `PRO_TRADER_REPLACEMENT_E01_T1_DATA_EVIDENCE.jsonl` | T1 data epoch archive: all-history/HQ>97 contract, 0/9 selected PASS, not market evidence |
| `04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_DATA_EPOCH.json` + `PRO_TRADER_REPLACEMENT_E02_T2_DATA_EVIDENCE.jsonl` | T2 active data epoch: all-history/HQ>97 contract đã frozen; evidence ledger header-only 0/9 selected PASS |
| `04. Memory/research/validate_data_epoch.py` | generation-generic gate tổng hợp no-skip; `--require-complete` chỉ PASS khi đủ đúng một receipt hợp lệ cho cả 9 symbol |
| `03. EA Developer/EA_HVGQAWAP_StateEngine/research/HYP-PTR-T1-QAWAP-HVG-M5-001_P12_CLOSEOUT.json` | T1 terminal pre-economic closeout; chỉ đóng exact N256/m32/DFA/Lo/HVG synthetic capability object |
| `04. Memory/research/CANDIDATE_REGISTRY.jsonl` | transition hypothesis append-only |
| `04. Memory/research/validate_candidate_registry.py` | validate registry trước meaningful run/closeout |
| `04. Memory/do_not_repeat_failures.md` | tra failure radius trước revive/candidate mới |
| `04. Memory/source_of_truth.md`/`.json` | registry path/fact canonical |
| `04. Memory/validate_source_of_truth.py` | fail-closed path validation |
| `.codex/operator/STATUS.md` | con trỏ recovery, không phải live ledger |
| `.codex/operator/EXPERIMENTS.jsonl` | lịch sử operator append-only |

## Playbook lõi và pipelines

| Path | Mở khi |
|---|---|
| `05. Playbook/pipeline_economic_strategy.md` | phát triển chiến lược kinh tế (brief → probe → build → Model 0 → Heavy Delivery) |
| `05. Playbook/pipeline_fast_kill.md` | đóng terminal nhanh các hypothesis/cell trượt fatal gate sơ khởi |
| `05. Playbook/pipeline_data_acquisition.md` | thu thập/đồng bộ dữ liệu zero-trade (no performance metrics) |
| `05. Playbook/research_doctrine.md` | thiết kế hypothesis, search boundary, overfit, market reality |
| `05. Playbook/ea_golden_path.md` | tổng quan đường mặc định cho EA |
| `05. Playbook/validation_gates.md` | ma trận ngưỡng stage gates, hard invalidation, run-manifest |
| `05. Playbook/tool_runbook.md` | cheat-sheet câu lệnh AlphaFactory và log triage |
| `05. Playbook/ea_engineering_standard.md` | chuẩn MQL5 closed-bar, non-repaint, risk/execution |

## EA, indicator shelf và research

| Path | Vai trò |
|---|---|
| `03. EA Developer/README.md` | ledger canonical của shelf compilable và research records |
| `03. EA Developer/<EA>/<EA>.mq5` | source canonical khi `ea_contract.ps1` resolve hợp lệ |
| `03. EA Developer/<EA>/ALPHAFACTORY_EA_CONTRACT.json` | capability/contract của package |
| `03. EA Developer/<EA>/research/` | prereg, readout và evidence riêng package |
| `03. EA Developer/EA_FiveIndicatorAtomicV2/` | Owner-authorized FIV2 atomic rebuild (engines R/T/B, role-locked indicators). Campaign `FIV2-20260808-ATOMIC` on branch `codex/five-indicator-rebuild-v2`. Stage-0 first ID `HYP-FIV2-R-EURUSD-M5-STAGE0-001`; engineering compile PASS only — no economics/promotion. Manifest: `04. Memory/research/campaigns/FIV2_20260808/` |
| `03. EA Developer/EA_RegimeStructureFusion/` | EA MQL5 một-file kết hợp AIRD/VRC/MBB/TB SMC/QQE; TB v3 liquidity-pool và telemetry đã engineering-valid, nhưng full EURUSD M5 HYP-010 âm PF0.7145/N162 và terminal economic-kill; xem `research/liquidity_pool/HYP-RSF-EURUSD-M5-LIQUIDITY-POOL-ECON-010_RESULT.md` |
| `03. EA Developer/EA_RegimeStructureFusionStateCensus/` | Zero-trade M5 census của đủ năm indicator; HYP-012..014 đóng state/transition trên EURUSD và USDJPY, không mở OOS |
| `03. EA Developer/EA_RegimeStructureFusionStateCensusM15/` | Zero-trade native-M15 census; HYP-015..018 đóng state/barrier/MBB-event/TB-event, không resample M5 và không mở OOS |
| `04. Memory/research/20260808_FIVE_INDICATOR_NATIVE_CENSUS_CLOSEOUT.md` | Closeout định lượng vai trò từng indicator, khác biệt EURUSD/USDJPY và M5/M15, cùng frontier stop sau bảy hypothesis không có survivor |
| `03. EA Developer/EA_RegimeStructureFusion/research/evidence/HYP-RSF-EURUSD-M5-FORENSICS-001/` | Cell-16 forensic casebook: 14 outcome-locked losing/winner comparisons with all five indicators, exact 670-trade replay, population/path metrics and independent Grok review; terminal diagnostic only, no parameter rescue |
| `03. EA Developer/EA_RegimeStructureFusionForensics/research/visual/native_structural_event_005/` | 8 ảnh native MT5 Visual Mode thật (MBB + QQE + TB structure + entry/SL/TP/exit) ghép cặp breakout/trend long/short thắng-thua; dùng để giải thích hành vi giá, không cấp quyền post-hoc filter |
| `06.Indicator Alpha/` | source canonical của custom indicators MQL5 một-file; EA chỉ đọc public buffer ở closed-bar shift >=1 |
| `06.Indicator Alpha/Volatility_Regime_Classifier_QuantRegime.mq5` | VRC overlay port từ Pine v6: 9 regime Hurst/ADX/CHOP/ATR-percentile, candle/background/bands/labels/dashboard, closed-bar alerts và public buffer contract 0..35 |
| `06.Indicator Alpha/TB_Smart_Money_Concept_2026.mq5` | TB SMC 2026.2.0 v3 structural overlay: immutable `TV_2026_2_0` parity profile plus optimizer-ready `EA_CUSTOM`; incremental closed-bar BOS/MSS, Origin Cells, FVG+CE lifecycle, sweeps, HUD/alerts, buffers 0..43 tương thích và causal unconsumed-swing liquidity pool buffers 44..47 |
| `00. Old File/EA_Archive/` | archive-only; không compile/backtest làm evidence |

Không lặp trạng thái từng package ở INDEX. Muốn biết lane nào sống, terminal hay
audit-only: đọc `03. EA Developer/README.md`, latest registry row và artifact của
đúng package.

## Owner-directed preflight records

| Path | Role |
|---|---|
| `03. EA Developer/EA_VRAS_RegimeAdaptiveScalperV4/research/HYP-VRAS-EURUSD-M5-015_PREFLIGHT_READOUT.md` | V4 plan parked before EA source: mislabeled USDJPY evidence, wrong coverage and missing true-flow/estimator/async contracts; zero outcome/economic exposure, T2 authority unchanged |
| `03. EA Developer/EA_VRAS_RegimeAdaptiveScalperV4/research/HYP-VRAS-USDJPY-M5-001_READOUT.md` | Corrected atomic USDJPY M5 Asian OU successor: P0 6/6, 33 tests, compile 0/0, non-repaint PASS; engineering-valid but terminally parked before Model 0 for missing USDJPY commission/slippage provenance |
| `03. EA Developer/EA_VRAS_RegimeAdaptiveScalperV4/research/HYP-VRAS-USDJPY-M5-002_OPERATIONAL_CLOSEOUT.json` | Outcome-blind HYP-002 operational closeout: actual FivePercent report dataset identity differed from the foundation proxy; parked before PF/PnL/DD/trade-count access |
| `03. EA Developer/EA_VRAS_RegimeAdaptiveScalperV4/research/HYP-VRAS-USDJPY-M5-003_FAILURE_PACKET.json` | Identity-corrected USDJPY M5 Model 0 terminal kill: 3/3 losses, PF 0, 0.0115 trades/week, plus invalid zero-volume lifecycle exit rows; no optimization/validation/holdout/promotion route |
| `03. EA Developer/EA_LOMX_MultiAssetMomentum/research/HYP-LOMX-MULTI-M5-001_IMPLEMENTATION_REVIEW.md` | Review of the supplied dual-engine plan: combined cadence/collision contract invalid before outcomes; routes only separable atomic cells |
| `03. EA Developer/EA_LOMX_MultiAssetMomentum/research/HYP-CBRK-EURUSD-M5-001_FAILURE_PACKET.json` | Engineering-valid EA and identity-valid EURUSD M5 generic compression-breakout Model 0; terminal economic kill at PF 0.7467 and 1.1027 trades/week; XAUUSD remains unproven, no optimization/validation/holdout/promotion/live route |
| `03. EA Developer/EA_AIRQMB_RegimeFusion/research/HYP-AIRQMB-MULTI9-M5-SCREEN-006_RESULTS.md` | Owner-directed one-file fusion EA combining AIRD + MBB + QQE; nine 2023–2024 Model-4 real-tick baselines all PF<1 with negative expectancy, so all cells are terminal kills and the conditional per-symbol grid never opened |

## AlphaFactory

| Path | Vai trò |
|---|---|
| `02. AlphaFactory/alpha.ps1` | entry duy nhất: status/compile/backtest/analyze/validate/delivery |
| `02. AlphaFactory/alpha.local.ps1` | path máy local, gitignore; không commit |
| `02. AlphaFactory/tools/ea_contract.ps1` | resolve source/package fail-closed |
| `02. AlphaFactory/tools/ea_research_loop.ps1` | full-loop generic, dry-run mặc định |
| `02. AlphaFactory/templates/research/` | prereg/task/readout/Fast-Kill/Heavy-Delivery templates |
| `02. AlphaFactory/tools/research/` | indicator-neutral probe, metrics, parity, clock, chart/log tools |
| `02. AlphaFactory/tools/research/empirical_probe_runner.py` | hash-bound V4 plan/data capability forensic runner; exact-symbol, non-stitched-session and true-flow fail-closed checks, not an economic analyzer |
| `02. AlphaFactory/tools/research/setup_fivepercent_market_data.py` | one-use zero-trade producer for the FivePercent five-asset M1/M5/H1/H4 raw corpus; source-epoch primary, exact-duplicate reconciliation and explicit BTC DST UTC ambiguity |
| `02. AlphaFactory/tools/research/finalize_fivepercent_market_data_receipt.py` | consumed receipt-only recovery for dataset-004; re-hashes the 20-file manifest and never starts MT5 or rewrites data |
| `02. AlphaFactory/data/<broker>/<symbol>/` | data shelf D:, manifest hash-bound |
| `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json` | canonical 5-symbol x 4-timeframe raw broker-bar manifest: 48,314,068 rows, zero orders/economics; not T2/HQ/economic evidence |
| `02. AlphaFactory/runs/<EA>/<run_id>/` | report, manifest, analysis và logs của run |
| `02. AlphaFactory/runs.db` + `tools/runs_db.py` | catalog tiện tra cứu, không phải authority |
| `02. AlphaFactory/tools/audit_mql5_nonrepaint.py` | audit sau mọi đổi signal/data-access |
| `02. AlphaFactory/analysis/param_optimizer.py` | import full MT5 optimization family, DSR/heatmap pass thật; schema v1 diagnostic-only, không tự chứng minh cumulative `N` |
| `02. AlphaFactory/analysis/purged_cpcv.py` | event-level purged combinatorial split/PBO; aligned universe, diagnostic-only, chưa reconstruct paths |
| `02. AlphaFactory/analysis/dynamic_cost_model.py` | stress cost account-currency theo volume/liquidity/volatility; schema v1 diagnostic-only |
| `02. AlphaFactory/tools/validate_ea_delivery_packet.py` | rehash closeout packet fail-closed |
| `02. AlphaFactory/tools/workspace_hygiene.ps1` | inventory/cleanup dry-run có containment |
| `02. AlphaFactory/tools/backtest_storage_inventory.py` | inventory dung lượng, orphan/mirror candidate |
| `02. AlphaFactory/tools/large_log_reader.py` | đọc log lớn bằng streaming có cap |
| `02. AlphaFactory/external/` | external data machine-local trên D:, không commit corpus |
| `02. AlphaFactory/STRATEGY_LOG.md` | lịch sử chiến lược và bài học |
| `02. AlphaFactory/DECISION_FRAMEWORK.md` | cây ITERATE/PIVOT/ABANDON |
| `03. EA Developer/_Shared/Execution/AF_ExecutionKernel.mqh` | experimental async FSM, mutation-default-off; compile reference, chưa được adopt |
| `03. EA Developer/_Shared/MarketData/AF_TickCursor.mqh` | optional bounded tick-history cursor cho tick-path logic |

Các acquisition/analyzer chuyên biệt nằm trong `02. AlphaFactory/tools/` và
được package research/task packet trỏ trực tiếp; INDEX không liệt kê từng script
để tránh drift.

## Tests và schema

| Path | Vai trò |
|---|---|
| `02. AlphaFactory/tests/` | regression harness, hygiene, golden path, packet và research tools |
| `02. AlphaFactory/schemas/` | schema machine-readable cho delivery/data contracts |
| `02. AlphaFactory/analysis/` | producer phân tích; promotion eligibility theo gates |

## Archive và tài liệu khác

| Path | Vai trò |
|---|---|
| `00. Old File/` | một nhà archive; không phải source/evidence chạy mới |
| `00. Old File/project_control_archive_20260716/` | workflow/roster/policy cũ, reference-only |
| `00. Old File/agent_guidance_archive/governance_cleanup_20260730/` | snapshot có hash trước lần tinh gọn này |
| `docs/` | report/handoff độc lập, không cấp run authority |

Quy tắc diễn giải cuối: một hypothesis terminal chỉ đóng tested object; một
search cell `NO LEGAL CANDIDATE` chỉ đóng boundary đã khai. Không cái nào tự
hoàn thành goal hoặc cấm một cơ chế/data contract mới có prereg độc lập.

Frontier-stop mới nhất của chiến dịch indicator/visual:
`04. Memory/research/20260807_INDICATOR_FUSION_FRONTIER_STOP.md`. Kết luận chỉ
đóng các recombination AIRD/VRC/MBB/QQE/TB và biên dữ liệu free/broker-native
đã kiểm tra; goal vẫn ACTIVE/UNMET. Bước mở lại phải là một nguồn PIT mới có
license, budget, lịch sử/live latency và map đủ chín symbol trước source probe.
