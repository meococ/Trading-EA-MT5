# EA Unicorn Precision Scalper

Source canonical: `EA_UnicornPrecisionScalper.mq5`, phiên bản engineering
`1.23`. EA giữ detector XAUUSD M5 event-anchored đã được dùng để falsify
HYP-006, nhưng canonical source hiện là bản hardening hậu kiểm và được gắn
`POST_KILL_HARDENED_NO_RUN_AUTHORITY`. Nó không phải EA được phép chạy live và
không viết lại kết quả Model 0 đã KILL.

## Logic đang được giữ lại

Luồng đóng nến: H4 EMA20/50 bias → D1 không ngược hướng → displacement tối
thiểu 1.20 ATR → FVG ba nến → sweep rolling 12 bar còn hiệu lực trong phiên →
opposite-candle overlap proxy → premium/discount proxy → score tối thiểu 75.
Plan cũ dùng SL ngoài sweep + 40 points, TP 2.5R, BE 1R và max hold 90 phút.

Detector này là proxy định lượng, không phải implementation đầy đủ của MSS/BOS
và breaker discretionary. Cả market-entry HYP-006 và FVG-CE limit HYP-007 đã
KILL; không được dùng hardening kỹ thuật để tuyên bố edge đã hồi sinh.

## Chế độ an toàn

- Preset active duy nhất: `presets/ALERT_ONLY_HARDENED.set`.
- `InpEnableAlertCasebook=false` theo mặc định. Khi bật, casebook chỉ chạy ở
  alert-only, yêu cầu terminal data path trên `D:` và giới hạn tối đa 200 dòng.
- Mặc định `InpResearchAutoMode=false` và
  `InpAllowRetiredResearchExecution=false`: không đặt, sửa hoặc đóng lệnh.
- Attach/restart giữa nến phải chờ M5 bar kế tiếp; không fire setup cũ.
- Nếu bật research-auto nhưng thiếu retired-execution override hoặc thiếu cost
  commission/slippage dương, `OnInit` fail-closed.
- Ownership bắt buộc symbol + magic `5600717` + strategy comment; exposure cùng
  symbol nhưng không thuộc EA chặn entry mới.
- News guard bật khi chưa có calendar hash-bound sẽ fail-closed.
- Emergency switch chỉ khóa entry mới, không tự ý flatten vị thế.

## Kernel đã harden

- Execution FSM tường minh và transaction-driven.
- `OrderCheck`, trade mode, filling mode, stop/freeze geometry và foreign
  exposure checks trước mutation.
- Cost-aware money-risk sizing qua `OrderCalcProfit`.
- Daily trade count theo unique position entry; loss streak theo lifecycle.
- Initial risk dùng fill/SL thật, không mất khi partial fill.
- Input peak-equity persistence được giữ để tương thích preset cũ nhưng đang
  chủ ý dormant: execution chỉ được phép trong Tester, còn GlobalVariable
  persistence chỉ dành cho non-tester. Mỗi tester run tự khởi tạo peak riêng.
- Bounded reject-reason summary thay cho log từng bar.
- Lifecycle telemetry profile `lifecycle-v3`, mặc định tắt trong alert-only để
  không sinh log giao dịch rỗng; không dùng `FILE_COMMON`.
- `ALERT_FIRST_CASEBOOK_V1` ghi context pre-outcome, không ghi
  PnL/MFE/MAE/forward return và không thay đổi signal.
- Casebook có metadata riêng để khóa source-contract, run id, broker/server,
  terminal data path, UTC offset và toàn bộ input detector; sweep age dùng cùng
  định nghĩa với frozen Python probe.
- New-bar gate, history-dependent risk guards và trade-result handling đều
  fail-closed; pending exposure cùng symbol và spread tăng lại trước send đều
  chặn mutation.
- Event-sweep invalidation kiểm toàn bộ closed bars tới decision bar; không bỏ
  sót hai nến displacement/FVG gần nhất.
- V1.23 chỉ bổ sung hardening: mutation chỉ có thể xảy ra trong Strategy Tester
  khi cả hai override nghiên cứu bật; quét position/order/history lỗi thì
  fail-closed; deviation dùng slippage budget; risk tiền được đối chiếu ngay
  theo fill thật và đóng ngay nếu vượt budget.
- Casebook V1.3 ghi exact source SHA256 ở metadata và từng row; không thay
  detector hay thêm outcome.

## Alert-first collection status

The authoritative D-portable, zero-trade collection is V1.3 under
`DATA-ACQ-UNICORN-CASEBOOK-V1-002`. AlphaFactory run `20260716_155111`
harvested 200 unique detector rows, zero prefilled labels and zero Strategy
Tester trades while every protected C-drive inventory remained identical.
V1.2 run `20260716_153059` is preserved as diagnostic-only because it did not
bind source SHA in row/meta. Neither collection is an active research gate.
See `research/20260716_ALERT_FIRST_CASEBOOK_V123_COLLECTION_READOUT.md`.

## Evidence

- HYP-006 Model-0 KILL: run `20260716_141244`, full-cost PF `0.498`, cadence
  `1.257/tuần`, MC P95 DD `7.118%`.
- HYP-007 fill probe KILL: 115/251 fill, `45.82%`, `1.110/tuần`; không code hay
  Tester run.
- Frozen Model-0 source:
  `research/source_snapshots/EA_UnicornPrecisionScalper_HYP-006_CB51EB2A.mq5`.
- Engineering closeout:
  `research/POST_KILL_ENGINEERING_HARDENING_READOUT.md`.
- Alert-first research/implementation closeout:
  `research/ALERT_FIRST_CASEBOOK_V1_READOUT.md`.
- Report-to-code fidelity audit:
  `research/20260716_UNICORN_REPORT_TO_CODE_FIDELITY_AUDIT.md`.
- Current verification: 58/58 tests, MetaEditor 0 errors/0 warnings,
  exact-source non-repaint PASS. Canonical source SHA256:
  `10E278435644E63FD6418047AC775537CECEE8BBA4A9E5D89842E0F15312CB18`.
- A direct Python bridge probe that omitted portable mode was rejected, its
  360,407,524-byte run-created C profile was removed with before/after receipts,
  and protected Common remained unchanged.

## Giới hạn còn lại

- Không có performance/backtest authority cho hardened source.
- Runtime smoke alert-only bị AlphaFactory chặn đúng thiết kế vì thiếu fresh
  contract receipt; không bypass harness.
- UTC offset vẫn là input cố định cho research contract, chưa phải lịch DST
  production.
- Không có historical news source hash-bound hay live fill-cost provenance.
- Candidate kinh tế tiếp theo phải có hypothesis và causal mechanism mới; compile
  xanh không đồng nghĩa deploy-ready.
- Không dùng collection này để chỉnh threshold hậu nghiệm hoặc mở lại family.
- Model-0 cũ chỉ falsify proxy đã code, không falsify đầy đủ memo discretionary;
  đồng thời không được dùng kết luận này để tự ý thêm MSS/retest rồi chạy lại.
