# Golden Path Generic — Thiết kế đến quyết định EA

Cập nhật: 2026-07-16

Đây là đường mặc định cho mọi EA, không phụ thuộc Sonic R. `hot.md` quyết định
lane đang mở; AlphaFactory là harness; prereg/registry/gate quyết định một run có
ý nghĩa hay không. Compile xanh không phải edge và backtest đẹp không phải quyền
deploy.

## 1. Intake thiết kế

Agent chuyển brief của Owner thành rule định lượng: entry, invalidation, SL/TP,
quản trị lệnh, session, regime, symbol/TF, risk, cost và kill gate. Mọi quyết
định signal phải dùng bar đã đóng; tick chỉ được dùng cho execution/management
sau khi signal hợp lệ. Điểm mơ hồ làm thay đổi thesis phải được nêu trước khi
code; chi tiết kỹ thuật an toàn có thể do lead tự chốt và ghi assumption.

## 2. De-dup và probe rẻ

Đọc `do_not_repeat_failures.md`, registry và lineage liên quan. Tạo row `idea`
hoặc `probe`, draft prereg từ template, rồi chạy probe offline rẻ trước ceremony.
Không cần ép Deep Research cho brief cơ chế đã đủ rõ; dùng nó khi cần discovery,
nguồn hoặc cơ chế mới. Probe fail thì `parked/killed`, chưa code để cứu.

## 3. Freeze hypothesis

Khi probe hợp lệ, khóa một `hypothesis_id`, window, Model, exact overrides,
train/holdout, matched control, budget thử nghiệm và gate. Hash prereg vào row
`probe`; source có thể còn `null` trước build. Chỉ row mới được append, không sửa
lịch sử. Sau code/audit/compile, append `screened` với cả source + prereg hash;
`screened|challenger` và Model 0 mới đủ điều kiện cho run nghiêm túc.

## 4. Build package canonical

Source duy nhất: `03. EA Developer/<EA>/<EA>.mq5`. Package có `research/`, preset,
README/repro note và `ALPHAFACTORY_EA_CONTRACT.json`. Sau khi artifact code đã
ổn định, bind source/prereg hash vào transition `screened`. Tách signal, risk,
execution, ownership/state và telemetry. Bắt buộc xử lý magic/symbol ownership,
netting/hedging, restart/idempotency, partial fill, retcode, volume/stop geometry,
timezone/DST và sizing bằng `OrderCalc*` khi risk theo tiền.

## 5. Gate code trước MT5

Chạy static/non-repaint audit, unit/offline test phù hợp, parse/lint và compile
qua `alpha.ps1`. Thay đổi signal/data-access phải audit lại. EA standalone không
cần include; include có dùng phải được hash-bound. Compile từ archive không có
giá trị.

## 6. Capability và cost trước backtest

Run có ý nghĩa cần lifecycle contract thật, không chỉ logger giả:

- `telemetry_profile=lifecycle-v3`, input `InpEnableTelemetry`;
- đúng một `*_LifecycleTrades_*.csv` và một `*_RunMeta_*.json` được manifest bind;
- RunMeta dùng schema `alphafactory_run_meta.v1`, bind `run_id`, EA, symbol và
  telemetry profile; filename chứa đúng `run_id`;
- deal/position/P&L/risk reconcile với report;
- spread, commission và slippage có provenance cùng broker/data scope.

Thiếu contract hoặc cost evidence phải block trước MT5. `none` chỉ cho compile,
probe và dry-run, không được coi là research execution.

## 7. Packet và Model 0

Tạo task packet từ evidence hiện tại: registry row, prereg, source, capability,
include closure, Git/no-Git identity, broker/data fingerprint, symbol geometry,
cost manifest, matched control và `acceptance_contract` sao chép chính xác từ
registry row đã đóng băng. Chạy dry-run:

```powershell
& "02. AlphaFactory/tools/ea_research_loop.ps1" `
  -EaName <EA_NAME> -HypothesisId <HYP_ID> -RunRole control `
  -Symbol <SYMBOL> -Period <TF> -From <YYYY.MM.DD> -To <YYYY.MM.DD> `
  -Model 0 -TelemetryTier trade-only -TaskPacket <PACKET.json> `
  -CostSourceManifest <COST_SOURCE_MANIFEST.json>
```

Chỉ thêm `-Execute` khi `execution_allowed=true`. MT5 tester chạy tuần tự dưới
global lock; các phân tích hậu kỳ độc lập mới được fan-out. Public strict loop
chỉ chạy Model 0. Evidence Model 1 legacy hoặc lane khác được Owner duyệt chỉ có
thể dùng để kill/park, không promote.

## 8. Control → challenger → validation

Control phải hoàn tất và đóng băng trước challenger. Challenger giữ cùng
symbol/TF/window/Model/data/cost identity; chỉ decision surface đã prereg được
đổi. Generic comparator yêu cầu net, PF và net/DD không kém control; absolute
gate được khóa trong registry `acceptance_contract` rồi truyền máy-máy vào
unified validation. Sau đó chạy cost x1/x1.5/x2,
holdout/WFA, sensitivity, Monte Carlo, regime/concentration, execution audit và
casebook theo stage.

## 9. Quyết định và chốt phiên

Mỗi gate là `PASS|FAIL|INSUFFICIENT`. Fail hợp lệ → append `parked/killed`; muốn
đổi cơ chế/ngưỡng phải mở hypothesis mới. Pass research không đồng nghĩa live.
Cập nhật `hot.md`, registry/readout, failure memory nếu có kill, source-of-truth
nếu path đổi, rồi archive-first cleanup. Chỉ commit/push khi Owner yêu cầu rõ
trong message hiện tại.

## Owner gửi thiết kế như thế nào

Owner có thể nhắn ngắn; agent phải tự bù phần engineering và phản biện:

```text
Hãy tự build EA end-to-end theo generic golden path.
Mục tiêu/thesis: ...
Symbol, timeframe, session: ...
Entry và invalidation theo góc nhìn trader: ...
SL/TP/quản trị lệnh: ...
Risk và giới hạn DD: ...
Điều em được tự quyết: kiến trúc, telemetry, test, tham số kỹ thuật an toàn.
Điều cần hỏi anh trước: thay đổi thesis, symbol/TF, risk budget hoặc live deploy.
Quyền lần này: code/compile/backtest/commit [ghi rõ cái nào được phép].
```

Nếu Owner chưa có con số, ghi “em đề xuất và prereg trước khi test”; agent không
được lấy kết quả vừa thấy để chọn ngưỡng ngược lại.
