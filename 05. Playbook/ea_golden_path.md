# Golden Path Generic — Thiết kế đến quyết định EA

Cập nhật: 2026-07-26

Đây là đường mặc định cho mọi EA. Scope Owner hiện tại + active lock + prereg/
registry/task packet quyết định lane/run được phép; `hot.md` chỉ giúp định tuyến
và có thể trễ. AlphaFactory là harness. Compile xanh không phải edge và backtest
đẹp không phải quyền deploy.

## 0. Mở lane EA mới — không để prior biến thành blanket veto

Flow mặc định:

`Owner intent → kiểm lock/artifact hiện tại → failure-radius classification →
logic matrix → probe rẻ → freeze prereg/registry → build → test + compile +
non-repaint → Model 0 đóng băng → metrics/log triage → route: Fast-Kill hoặc
Heavy-Delivery → quyết định → lesson + ID mới`

Trước khi từ chối hoặc mở một EA mới, lead phải:

1. Viết outcome contract từ yêu cầu Owner; không lấy `hot.md` làm scope thay thế.
2. Kiểm active MT5/registry/source lock để không race shared lane.
3. Đọc `hot.md`, failure memory và registry như prior, rồi so candidate identity:
   mechanism, information/data source, decision timing/surface, symbol/TF/window,
   execution/cost và risk/exit.
4. Chặn exact replay và post-hoc rescue. Run vô hiệu chỉ mở sửa correctness.
5. Nếu delta là materially new, cho phép package/ID mới; khai prior nào liên quan,
   vì sao không phải rescue, probe nào có thể falsify rẻ và trial budget bao nhiêu.
6. Owner có thể yêu cầu build-first; khi đó freeze lý do, identity và gate trước
   khi đọc outcome, không dùng ngoại lệ để bỏ registry/non-repaint/delivery.

Kết quả “no edge” chỉ có hiệu lực trong tested object đã bind. Nó không cấm agent
tạo EA mới; nó buộc EA mới phải giải thích thông tin/cơ chế mới và trả chi phí
bằng chứng cao hơn.

Nếu outcome Owner là một EA/book có positive expectancy và outcome đó còn UNMET,
lead không được kết thúc ở `KILLED` hoặc một prompt `NO LEGAL CANDIDATE`. Phải
đóng artifact của cell hiện tại, ghi exact search boundary/failure packet, rồi mở
cell hợp pháp tiếp theo trong scope. Chỉ dừng toàn dự án khi boundary cấp dự án
đã được khai và tiêu hết, hoặc bước kế cần quyền mới như chi phí, live risk,
credential hay đổi symbol/TF/thesis vật chất.

## 1. Intake thiết kế

Agent chuyển brief của Owner thành rule định lượng: entry, invalidation, SL/TP,
quản trị lệnh, session, regime, symbol/TF, risk, cost và kill gate. Mọi quyết
định signal phải dùng bar đã đóng; tick chỉ được dùng cho execution/management
sau khi signal hợp lệ. Điểm mơ hồ làm thay đổi thesis phải được nêu trước khi
code; chi tiết kỹ thuật an toàn có thể do lead tự chốt và ghi assumption.

Trước source change, tạo `LOGIC_TO_CODE_MATRIX`: mỗi quan sát của trader phải
được gán đúng vai trò `context|qualification|trigger|invalidation|management|risk`,
rule định lượng, data/bar index tại thời điểm quyết định, vị trí code, telemetry
và test/parity proof. Context không được âm thầm thay thế trigger. Matrix còn
`MISSING` hoặc ambiguity vật chất thì chưa được gọi là fidelity-complete.

## 2. De-dup và probe rẻ

Tìm mechanism/family/ID/data-contract liên quan trong
`do_not_repeat_failures.md`, registry và lineage để xác định failure radius;
không cần nạp toàn bộ catalog cho một candidate hẹp và không lập blacklist
indicator/family. Ghi classification và material delta; tạo row `idea` hoặc
`probe`, draft prereg từ template, rồi chạy probe offline rẻ trước ceremony.
Probe mới import từ probe SDK `02. AlphaFactory/tools/research/` (indicators,
sealed_loader, trial_log, metrics, controls, dsr, chart_case_render) — nên
tái sử dụng thay vì copy lại code; tham số chiến lược đến từ frozen plan, không từ kit. Lane hướng
Model 0 dùng biến thể indicator `*_mt5` (parity đã chứng minh).
Probe dùng làm bằng chứng KILL/falsification phải có PROBE_PLAN đóng băng
TIỀN-kết-quả, SHA-bind vào row (template
`02. AlphaFactory/templates/research/PROBE_PLAN.template.md`); plan đã bind là
bất biến — amendment pre-outcome thành file `_V2.md` bind ở transition kế.
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
execution, ownership/state và telemetry. Cần xử lý cẩn thận magic/symbol
ownership, netting/hedging, restart/idempotency, partial fill, retcode,
volume/stop geometry, timezone/DST và sizing bằng `OrderCalc*` khi risk theo
tiền; nêu rõ trong repro note nếu bỏ qua mục nào.

Grok `builder/coder` có thể sở hữu trọn implementation loop thay parent. Handoff
phải đóng băng: input artifacts, candidate/hypothesis identity, write-set,
forbidden actions, exact tests, quyền compile/backtest, giới hạn một Model-0 và
result packet phải trả. Trong biên này Grok tự code, sửa test, compile và xử lý
lỗi implementation; parent làm commander/integrator, không viết song song cùng
file và không giám sát từng dòng. Parent chỉ nhận khi verify độc lập source hash,
test, compile, non-repaint và run/receipt identity. Grok `forensic reviewer` là
task stateless/read-only riêng, không được dùng outcome để patch chính terminal
object. Mọi MT5 mutation/backtest vẫn serial dưới global lock.

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
đổi. Comparator (net, PF, net/DD không kém control) được khai trong
`acceptance_contract` của registry rồi truyền máy-máy vào unified validation —
định nghĩa chuẩn ở `validation_gates.md` (Challenger). Sau đó chạy cost x1/x1.5/x2,
holdout/WFA, sensitivity, Monte Carlo, regime/concentration, execution audit và
casebook theo stage.

## 9. Post-run routing: Fast-Kill hoặc Heavy-Delivery

Ngay sau metrics, cost và log triage, route theo contract đã khóa trước outcome:

- **Fast-Kill:** exact cell đã chạm fatal gate preregistered. Chỉ đóng bằng
  `alphafactory_fast_kill_closeout.v1`; Model 0 vẫn phải bind source/compile/
  non-repaint/run/report/metrics/log triage. Không render casebook, không gọi
  Grok, không được dùng packet này để nói EA/book đã hoàn thành.
- **Heavy-Delivery:** candidate sống qua necessary-condition gates, cần đi tiếp,
  cần dùng anatomy để mở hypothesis mới, hoặc có claim `DONE|complete|ready`.
  Khi đó mới áp toàn bộ forensics/casebook/reviewer/delivery bên dưới.

Không Fast-Kill theo một cutoff nhìn thấy hậu nghiệm. Minimum observations và
sequential futility boundary phải nằm trong prereg trước kết quả. Engineering/
data invalid chỉ sửa fidelity hoặc đóng INVALID, không được suy rộng thành no-edge.

### Heavy-Delivery forensics và delivery gate

### Chẩn đoán full-horizon khi DD guard làm censor mẫu

Nếu account-DD guard dừng entry trước khi đi hết cửa sổ và Owner cần xem hành vi toàn chart, phải mở một ID chẩn đoán mới, đóng băng trước outcome và `promotion_eligible=false`. Chế độ này chỉ được bypass **entry halt** trong Strategy Tester; vẫn phải đo/nghi lại threshold breach, initial-equity DD, peak-to-trough DD, broker stop-out và full-window coverage. Giảm fixed-fraction risk để tester sống sót được phép khi khai trước và khi kết luận dựa trên PF/R/cadence thay vì so dollar P/L trực tiếp. Phải nhớ tester/account của broker có thể còn stop-out riêng dù EA không latch DD; nếu cần scale deposit và risk, giữ nguyên ngân sách rủi ro tiền ban đầu, mở ID engineering successor mới và chứng minh không làm mất signal vì minimum lot. Với EA intraday, full-horizon diagnostic còn phải audit elapsed wall-clock, overnight/weekend crossing và gap xuyên SL; time-stop đếm bar có thể tạm dừng khi market đóng và biến R:R danh nghĩa thành tail không kiểm soát. Không được dùng run full-horizon để nới risk live, cứu hypothesis terminal, chọn năm/giờ tốt hoặc tune SL/R:R hậu nghiệm.

Một survivor/continued-candidate backtest chưa khép kín sau khi có report hoặc
`validate-full`. Agent phải hoàn thành đủ vòng sau trên đúng source/run đã
hash-bind:

1. Re-read logic matrix và source để xác nhận state machine thực chạy đúng
   intent, đúng sequencing, không có mode/default dormant hoặc proxy bị gọi nhầm
   là full strategy.
2. Chạy log triage trước khi mở raw log; reconcile report ↔ lifecycle ↔ RunMeta,
   OPEN/final rows, deal P&L/cost/risk và mọi reject/error quan trọng.
3. Phân tích economics và funnel: net/PF/WR/expectancy/R, cadence theo elapsed
   weeks, DD/tail/holding, cost stress, time stability, year/session/direction,
   regime/context state, concentration và execution quality.
4. Giải thích riêng cơ chế thắng, cơ chế thua và điểm logic xung đột. Kết luận
   từ pattern hậu nghiệm chỉ là lead cho hypothesis mới, không được patch thẳng.
5. Freeze sampling trước khi xem ảnh, rồi render casebook cho Heavy-Delivery. Mức delivery tối
   thiểu vẫn là hai winner + hai loser khi có đủ mẫu; postmortem lớn nên có
   random population, tail, median, matched winner/loser cùng direction,
   session, volatility/risk bucket và anomaly/rejection. Profile mở rộng
   `2 Grok workers × 100 case disjoint` chỉ dùng khi population đủ lớn, không
   thay thế population statistics và không được hand-pick.
6. Mỗi case có hai lớp tách biệt: `decision_asof` kết thúc ở bar entry, không
   hiện outcome/net_R; `anatomy` mới hiện entry, initial SL, TP, actual exit,
   MAE/MFE/hold và post-entry path. Combined human view được phép nhưng không
   được dùng làm bằng chứng đánh giá entry outcome-blind. Với M5, context tối
   thiểu là M5 + M15 + H1; thêm H4/D1 khi thesis dùng regime đó.
7. Chart phải hiện toàn bộ indicator/gate thực sự tham gia decision, giá trị
   shift, threshold và PASS/FAIL. Ưu tiên telemetry/MT5 CopyBuffer capture tại
   decision time; post-run recompute chỉ được gắn `NON_PARITY_DIAGNOSTIC` cho
   tới khi parity harness chứng minh khớp. Manifest bind source, bars,
   renderer, indicator source, time axis, case IDs và từng PNG hash.
8. Khi chart review có giá trị vật chất hoặc được cite, fan-out visual review theo vai: Grok A ưu tiên timing/price/indicator
   context; Grok B ưu tiên adverse path, risk/exit/execution và phản biện.
   Mặc định 5 case/job, chạy Grok backend serial, request artifact + dry-run,
   validate exact coverage/IDs/image-open. Parent Lead Quant đối chiếu lại với
   lifecycle/population/source, sửa mọi count sai và giữ verdict cuối. Raw
   output ở `.context/`; parent chỉ nạp aggregate, contradiction và case đại
   diện để tránh cạn context.
9. Zero-trade phải thay bằng funnel + chart candidate bị reject; không được bịa
   economics. Grok review hoặc chart pattern chỉ mở tối đa ba hypothesis mới
   có cơ chế và prereg fresh; không patch trực tiếp terminal object.
10. Hash-bind toàn bộ vào `alphafactory_ea_delivery_packet.v1` và chạy:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File "02. AlphaFactory/alpha.ps1" delivery `
  -Packet "<EA_DELIVERY_PACKET.json>"
```

Thiếu bất kỳ surface nào phải trả `FAIL` hoặc `INSUFFICIENT_EXPLAINED`; cấm gọi
EA development `DONE`, `complete`, `ready` hay đề xuất cải thiện tiếp từ outcome
khi delivery packet chưa PASS. Gate này kiểm tính đầy đủ của quyết định; nó
không thay thế prereg, registry, `validate-full` hoặc promotion gates.

## 10. Quyết định và chốt phiên

Mỗi gate là `PASS|FAIL|INSUFFICIENT`. Fail hợp lệ → append `parked/killed`; muốn
đổi cơ chế/ngưỡng phải mở hypothesis mới. Pass research không đồng nghĩa live.
Cũng không được đồng nhất delivery packet `KILLED` với việc hoàn thành mục tiêu
book; packet chỉ khép đúng EA/hypothesis đã bind.
Cập nhật `hot.md`, registry/readout, failure memory nếu có kill, source-of-truth
nếu path đổi, rồi archive-first cleanup. Chỉ commit/push khi Owner yêu cầu rõ
trong message hiện tại. Closeout survivor/continued candidate phải trỏ tới
delivery packet PASS. Exact cell Fast-Kill được đóng terminal bằng Fast-Kill
packet PASS nhưng outcome book vẫn `UNMET`; không có một trong hai packet hợp lệ
thì trạng thái chỉ là `UNMET/PARTIAL`.

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
