# Doctrine Nghiên Cứu

Cập nhật: 2026-07-13

Doc chi tiết được `AGENTS.md` trỏ tới. Chứa toàn bộ doctrine nghiên cứu/
validation trước đây nằm inline trong `AGENTS.md`. Mở khi thiết kế hoặc
review một hypothesis, run, hay thay đổi code EA. Trạng thái sống nằm ở
`hot.md`; ngưỡng theo stage nằm ở `sonic_validation_gates.md`.

## Doctrine Sonic R

- Bản Sonic R hiện tại là nghiên cứu parity được tái dựng, không phải
  parity nguồn gốc đã xác nhận.
- Classic là setup lõi: sóng price-action cộng góc Dragon, rồi tới Trend,
  HTF, session, và context S/R.
- PVSRA là context/qualification, không phải trigger vào lệnh độc lập.
- Không biến volume spike, số tròn, hay quan sát sweep/reclaim thành entry
  thực thi khi chưa có hypothesis tiền đăng ký riêng và evidence.
- Sideway là một regime hạng nhất, không phải lý do nới lỏng luật Classic.
- Chất lượng chart nhìn thấy phải được chuyển thành feature khả kiểm trước
  khi code: độ mượt sóng, Dragon nở/nén, non-chase, runway S/R, trap/build
  vs run-for-profits, pha session, độ thực của cost/spread.

## ChatGPT Deep Research Cho Nghiên Cứu Chiến Lược

Kích hoạt workflow này khi cần tìm chiến lược mới, nghiên cứu cơ chế edge,
đề xuất cách cải thiện/tối ưu strategy hiện có, so sánh strategy family hoặc
chuyển quan sát trader thành hypothesis có thể code/test.

1. Dùng **tool Browser** để mở ChatGPT trong browser được chỉ định hoặc browser
   mặc định của app. Ưu tiên session đã đăng nhập; không đọc cookie, password,
   local storage hay thông tin xác thực. Nếu ChatGPT yêu cầu đăng nhập, dừng và
   yêu cầu Owner đăng nhập trong browser đó; không tự đổi sang web search để
   lách authentication.
2. Trong ChatGPT, chọn đúng model **`GPT-5.6 Sol`**, mode **`Pro`**, rồi nhấn
   dấu **`+`** và chọn tool **`Nghiên cứu sâu`**. Trước khi gửi phải readback UI
   xác nhận cả ba trạng thái; prompt phải giữ nguyên sau khi gắn tool. Chỉ ghi đã
   dùng cấu hình này khi UI thực sự hiển thị và cho phép chọn; nếu thiếu một
   capability, báo rõ và xin Owner quyết định fallback, không âm thầm thay model
   hoặc biến câu trả lời thường thành Deep Research.
3. Trước khi gửi research, chuẩn bị một prompt packet ngắn nhưng đủ contract:
   mục tiêu edge, symbol/timeframe/session, baseline và failure đã biết, data
   window/quality, spread-commission-slippage-swap, closed-bar/non-repaint,
   giới hạn parameter/trial, cadence/DD mong muốn và điều kiện kill.
4. Yêu cầu Deep Research trả về tối thiểu: thesis/cơ chế thị trường; nguồn và
   URL; rule entry/exit/SL/TP/time-stop đủ chính xác; assumption; failure mode;
   parameter có source default; expected regime; rủi ro execution; de-dup với
   catalog hiện tại; và 1-3 hypothesis nhỏ có kill gate trước code.
5. Ưu tiên nguồn sơ cấp (paper, tài liệu chính thức, dữ liệu/broker spec). Forum,
   Reddit, TraderViet hay ForexFactory dùng để phát hiện idea và trader context,
   không tự trở thành bằng chứng edge. Lưu ngày truy cập, URL và tách rõ fact,
   inference, suggestion của model.
6. Output Deep Research là **research input**, không phải thẩm quyền. Agent chính
   phải kiểm nguồn, loại rule mơ hồ/lookahead, de-dup, chạy probe rẻ, rồi mới
   prereg một hypothesis. Không dùng Deep Research để biện minh cho post-hoc
   filter, parameter rescue, production claim hay lời hứa lợi nhuận.
7. Không gửi credential, account number, token, dữ liệu cá nhân hoặc artifact
   nhạy cảm vào ChatGPT. Chỉ dùng source/rule/metric tối thiểu cần cho nghiên cứu.

## Vòng Lặp Deep Research Sau Failure

Khi strategy có vấn đề hoặc hiệu suất không đạt gate, tiếp tục Deep Research
theo contract dưới đây; failure là input để mở hypothesis mới, không phải giấy
phép tune hypothesis cũ.

1. Xác minh failure đến từ một run hợp lệ. Nếu lỗi là source/config/report sai,
   data thiếu, cost chưa xác minh, compile/runtime hỏng hoặc artifact identity
   không sạch, sửa correctness/infrastructure trước rồi tái hiện đúng packet cũ;
   không dùng một run vô hiệu để kết luận strategy yếu.
2. Nếu run hợp lệ nhưng trượt cadence, PF/cost, stability, drawdown, execution,
   concentration hoặc holdout, đóng version hiện tại thành `killed` hoặc
   `parked`, ghi readout/registry và đóng băng toàn bộ artifact trước khi hỏi GPT.
3. Tạo **failure packet** gồm thesis/prereg đã khóa, source/input/config hash,
   exact gate bị trượt, metric train/holdout/cost, regime/year concentration,
   execution issue, tried-family budget và catalog họ đã killed/parked. Không đổ
   raw log lớn hay credential vào ChatGPT.
4. Chạy lại Browser -> ChatGPT -> `GPT-5.6 Sol` -> `Pro` -> `+` ->
   `Nghiên cứu sâu`. Yêu cầu GPT phân loại `bad thesis`, `bad data`, `bad
   execution`, `insufficient sample`, `regime dependence` hoặc `unknown`, kiểm
   nguồn sơ cấp và được quyền trả `NO LEGAL CANDIDATE`/`BLOCKED_BY_DATA`.
5. Output hợp lệ chỉ có thể là chẩn đoán, data-acquisition contract, hoặc một
   hypothesis độc lập/child mới với cơ chế và kill gate mới. Cấm đổi threshold,
   hour/day/session/symbol, SL/TP/BE hay filter từ chính readout vừa fail rồi gọi
   đó là cùng hypothesis được cải thiện.
6. Agent chính kiểm nguồn, de-dup với registry, chạy probe offline rẻ, rồi mới
   tạo `hypothesis_id` và prereg mới. Holdout đã mở của hypothesis cũ không được
   tái dùng làm holdout của child.
7. Mỗi vòng có budget hữu hạn. Nếu GPT lặp lại family đã đóng hoặc cùng blocker
   dữ liệu/execution chưa đổi, park frontier và dừng; chỉ mở vòng tiếp theo khi
   có cơ chế, source, data hoặc external-state mới thật sự.

## Quy Trình Nghiên Cứu

Dùng vòng lặp này cho công việc chiến lược EA có ý nghĩa:

1. Nghiên cứu thesis của trader và ghi lại nguồn/provenance. Khi scope thuộc
   strategy discovery/improvement/optimization/ideation, chạy workflow ChatGPT
   Deep Research ở trên trước khi chốt hypothesis.
2. Tiền đăng ký MỘT hypothesis theo
   `03. EA Developer/EA_SonicR/research/PREREG_TEMPLATE.md`: feature thay
   đổi, symbol/timeframe, cửa sổ ngày, model, override, gate pass/fail,
   budget feature, luật holdout, và các chỉnh sửa hậu kết quả bị cấm.
3. Chạy một probe/scanner offline rẻ trên artifacts sẵn có TRƯỚC mọi code
   entry EA. Đây là gate đầu tiên mặc định cho mọi hypothesis, không phải
   bước tùy chọn; kill nhanh ở đây là kết quả tốt.
4. Compile qua AlphaFactory:
   `powershell -NoProfile -ExecutionPolicy Bypass -File "02. AlphaFactory/alpha.ps1" compile "EA_SonicR"`.
5. Chạy matched control và challenger với symbol, timeframe, ngày, model,
   override tường minh.
6. Model 1 chỉ dùng làm screen nhanh. Survivor nào cũng cần Model 0 xác
   nhận và `validate-full`.
7. So với baseline đã đóng băng/liên quan; không chấm một run đứng một
   mình.
8. Phân tích theo lane, hướng, session, giờ, tháng, năm, pha thị trường,
   giải phẫu trade, cost stress, và evidence screenshot/casebook. Với thay
   đổi strategy-state, bắt buộc có snapshot MT5-native hoặc nhãn
   chart-state đã khóa trước mọi patch luật EA.
9. Nếu run hợp lệ trượt gate hoặc hiệu suất yếu, đóng version hiện tại rồi chạy
   `Vòng Lặp Deep Research Sau Failure`; không tune/rescue cùng hypothesis.
10. Sau khi công việc ổn định, chỉ cập nhật các doc ngắn liên quan:
   `hot.md`, `current_state.md`, `source_of_truth.*`, một prereg/readout,
   hoặc `README-SONIC-R.md` nếu bài học lõi thay đổi.
11. Lưu trữ telemetry Common Files và artifact run cũ kèm manifest sau các
    backtest có ý nghĩa.
12. Dùng `02. AlphaFactory/tools/sonic_research_loop.ps1` cho thí nghiệm
    full-loop nghiêm túc, hoặc tái hiện tường minh các gate
    compile/backtest/validate/cost/attribution/compare/cleanup của nó.

## Quy Trình Team Review

Khi user yêu cầu team/agent tham gia, dùng ba vai tách biệt và giữ
`fork_context=false` cho mọi agent được spawn:

- Sonic trader critic: kiểm tra EA có đang đọc trạng thái Classic/PVSRA
  như một trader thay vì chỉ khớp mẫu indicator.
- Quant validation critic: kiểm tra data mining, candidate registry,
  matched control, WFA/PBO/Reality Check/Monte Carlo, cost stress, và luật
  kill/park.
- MQL5/MT5 systems critic: kiểm tra source path, bất biến non-repaint,
  sizing rủi ro, hình học broker, tier telemetry, dọn cache MT5, và khả
  năng tái lập artifact.

Memo của agent là input review, không phải thẩm quyền. Coordinator phải
merge chúng thành một hypothesis cụ thể, kế hoạch code/test, hoặc quyết
định park/kill có ghi chép.

## Candidate Registry

Không để thí nghiệm chỉ sống trong các readout rải rác. Mọi ý tưởng có ý
nghĩa cần registry row và prereg trước khi kết quả được dùng cho quyết
định.

Registry bao phủ mọi hypothesis EA/portfolio FX được Owner mở rõ ràng trong
workspace, không chỉ Sonic R. Path dưới `EA_SonicR/research` được giữ vì tương
thích lịch sử; vị trí file không cấp quyền chạy và không thay thế `hot.md`.

Registry canonical:

- `03. EA Developer/EA_SonicR/research/CANDIDATE_REGISTRY.jsonl`
- schema: `03. EA Developer/EA_SonicR/research/CANDIDATE_REGISTRY.schema.json`
- template prereg: `03. EA Developer/EA_SonicR/research/PREREG_TEMPLATE.md`
- template readout: `03. EA Developer/EA_SonicR/research/READOUT_TEMPLATE.md`

Mọi run có ý nghĩa phải gắn với một `hypothesis_id`. Mọi registry row cuối
cùng phải chuyển về `parked`, `killed`, `confirmed`, hoặc
`portfolio-sleeve`.

Field tối thiểu:

- `hypothesis_id`, candidate cha, feature family, lane, symbol/timeframe,
  nguồn/provenance, override chính xác, hash hoặc path source, run ids,
  model, cửa sổ ngày, số trade/năm, PF/net/DD, cost PF x1/x1.5/x2, số
  tháng/nửa-năm/năm dương, trạng thái WFA/PBO/Reality Check/Monte Carlo,
  vấn đề execution, độ đầy đủ sidecar, trạng thái casebook, verdict, và lý
  do.

Trạng thái cho phép:

- `idea -> probe -> screened -> challenger -> confirmed -> portfolio-sleeve`
- trạng thái kết thúc: `parked`, `killed`

Probe khám phá có thể gợi ý idea, nhưng promotion đòi một run tiền đăng ký
mới. Model 1 được kill hoặc park; không được promote.

## Contract Nhãn Chart-State

Không patch luật EA nào được đến trực tiếp từ trực giác nhìn chart.

Đường đi bắt buộc:

```text
chart claim -> locked labels -> offline separation -> matched control -> default-off patch
```

Với mọi hypothesis dựa trên trạng thái, gán nhãn trước entry:

- trạng thái sóng: clean / choppy / overlap / unclear
- trạng thái Dragon: flat / compressed / expanding / angled
- trạng thái Trend/HTF: aligned / soft conflict / hard conflict / unknown
- runway S/R: clear / blocked / near whole-half-quarter / unknown
- rủi ro chase: early / mature / late chase / unknown
- trap/build vs run-for-profits: build / run / trap risk / unknown
- pha session và runway còn lại
- điều kiện vô hiệu hóa

Negative control là bắt buộc: các lệnh thua `SIDEWAY_WIDE`, các lệnh thắng
impulse, trade bị bỏ lỡ high-MFE, false positive high-MAE, và các session
liền kề.

## Multiple Testing Và Budget Chống Overfit

- Một hypothesis bằng một feature family và một phép tách trạng thái.
- Prereg phải định nghĩa số tham số/ngưỡng tinh chỉnh tối đa.
- Phát hiện subgroup hậu nghiệm trở thành `idea` mới; không phải luật thực
  thi trong cùng run.
- Không veto giờ/ngày/năm/session mới từ chính readout đó khi chưa có
  prereg mới.
- Cửa sổ holdout dùng để validation không được dùng để thiết kế feature.
- Đếm các filter thất bại, veto giờ, gate pha, và các lần sweep tham số
  vào variant family khi diễn giải PBO/Reality Check.

## Gate Promotion

Không bao giờ promote một EA chỉ từ profit factor. Ngưỡng theo stage và
artifact bắt buộc: `05. Guidance/sonic_validation_gates.md`.

Research-only là bắt buộc khi bất kỳ điều nào sau đây đúng:

- `validate-full` là `REVIEW` hoặc fail.
- WFA, robustness, Monte Carlo, equity audit, hoặc cost stress yếu.
- Edge phụ thuộc vào một năm, tháng, giờ, thứ, lane, hoặc hướng được đào.
- Slippage, hình học stop của broker, min lot, spread, hoặc xử lý news
  chưa được giải quyết.
- Exposure qua đêm/cuối tuần vi phạm contract của lane.
- Danh tính run/source path không chắc chắn hoặc evidence đến từ code lưu
  trữ.

Deploy-readiness đòi hỏi an toàn execution, đầy đủ rủi ro, độ trung thực
tester, truy vết artifact, phân tích trade thô, cost stress, và các giới
hạn đã biết được nêu thẳng.

## Quy Tắc MT5 Và Non-Repaint

- Quyết định dùng dữ liệu closed-bar: `CopyRates(..., 1, ...)` và
  `CopyBuffer(..., 1, ...)`.
- Hướng dài hạn: chỉ một wrapper truy cập dữ liệu được gọi
  `CopyRates`/`CopyBuffer`; các module setup/gate tiêu thụ context
  closed-bar đã chuẩn bị sẵn.
- `iTime(..., 0)` chỉ được phép cho gate bar-mới.
- Không thêm logic tín hiệu bar-zero.
- Sizing XAU phải dùng logic kiểu `OrderCalc*` nhận biết broker và fail
  closed khi không chứng minh được hình học.
- Với validation XAU nghiêm túc, coi sizing không-OrderCalc là chế độ
  tương thích research-only cho tới khi được chứng minh an toàn với broker.
- Không nới stop, grid, martingale, DCA, hay trung bình giá xuống.
- News guard phải fail closed khi thiếu dữ liệu calendar cho một test cần
  news.
- Sau mọi thay đổi signal/data-access, chạy audit non-repaint tìm
  `CopyRates(..., 0, ...)`, `CopyBuffer(..., 0, ...)`, mảng giá bar-zero
  trực tiếp, đọc indicator bar hiện tại, và ngoại lệ bar-mới ẩn. Một run
  có lãi hay screenshot không thay thế được audit này.

## Vệ Sinh Backtest

- Lane chính: `02. AlphaFactory/alpha.ps1`.
- Mọi run dùng ngày, symbol, period, model, override tường minh.
- Preflight phải xác nhận: source path canonical, hash source, timestamp/
  hash artifact đã compile, path tester đã copy, snapshot provenance no-Git,
  suffix symbol, model, ngày, override, tier telemetry, path runtime MT5,
  đích sidecar sạch, và trạng thái process tester do runner sở hữu.
- Snapshot provenance phải dùng `workspace_files.v1`: danh sách path tương đối,
  byte length và SHA256 được sắp xếp ổn định trên code/control surface đang
  hoạt động. Task packet, execution receipt và run manifest phải cùng bind
  `provenance_mode`, `workspace_snapshot_sha256` và file count; mọi drift trước
  compile/backtest phải fail closed.
- Root `.git` bị cấm theo quyết định Owner 2026-07-11. Không `git init`, không
  stage/commit/push, không dùng archive Git làm nguồn build. Metadata lịch sử
  chỉ được phục hồi khi Owner yêu cầu rõ ràng; closeout dùng hash/receipt,
  validator và tests đúng scope.
- Mọi compile/backtest lấy nguồn từ `00. Old File` hoặc path lưu trữ khác
  là evidence không hợp lệ và phải được đánh dấu như vậy trước khi trích
  dẫn.
- Closure phải xác nhận: path report, check row/header sidecar,
  `validate-full`, cost stress, attribution pha/regime khi áp dụng, refresh
  `runs.db`, chuyển trạng thái registry, manifest cục bộ của run, và
  verdict cuối.
- Tránh lỗi setup/cache cũ: kiểm tra path EA đã copy, run id, inputs, copy/
  purge sidecar, và dọn Common Files.
- Tier telemetry: `off`, `trade-only`, `state-lite`, `state-full`,
  `snapshot-casebook`. Screen cửa sổ dài nên tránh telemetry full trừ khi
  sample các case có giới hạn.
- Mọi thay đổi schema/header telemetry phải cập nhật analyzer và readout
  trước khi kết quả được tin.
- `02. AlphaFactory/runs/` và `02. AlphaFactory/runtime/` là kho evidence/
  runtime. Lưu trữ kèm manifest trước khi xóa, tránh dọn dẹp phá hủy.
- Không schedule/cron vòng lặp MT5 khi chưa được duyệt rõ ràng. Run MT5
  dài có thể ngốn bộ nhớ và bỏ lại process tester.
