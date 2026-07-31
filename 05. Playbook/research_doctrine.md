# Doctrine Nghiên Cứu

Cập nhật: 2026-07-26

Doc chi tiết được `AGENTS.md` trỏ tới. Chứa toàn bộ doctrine nghiên cứu/
validation trước đây nằm inline trong `AGENTS.md`. Mở khi thiết kế hoặc
review một hypothesis, run, hay thay đổi code EA. `hot.md` chỉ là cache tham
khảo; trạng thái có thẩm quyền nằm ở scope Owner hiện tại, registry/prereg/task
packet và artifact hash-bound. Ngưỡng theo stage nằm ở `validation_gates.md`.

Nguyên tắc chung rút từ mọi lane: indicator context/qualification nên đóng vai qualifier hơn là
trigger độc lập (nếu một brief thực sự dùng nó làm trigger, khai + biện minh
trong plan); quan sát chart nên thành feature khả kiểm trước khi code;
sideway là một regime hạng nhất; tránh nới luật lõi của một setup chỉ vì regime — nếu regime đòi điều chỉnh, coi đó là hypothesis/biến thể mới và khai trong plan.
Doctrine riêng của lane đã archive nằm cạnh ledger lane đó trong
`00. Old File/EA_Archive/`.

## Bản chất thị trường tài chính và trading

Đây là market model mặc định để lead ra quyết định; không phải một strategy
template và không cấp quyền trade:

1. **Adaptive và non-stationary:** người tham gia, regulation, liquidity,
   volatility và execution thay đổi; một anomaly lịch sử có thể decay hoặc đổi
   dấu. Không ngoại suy một average return thành luật bất biến.
2. **Edge là phân phối sau cost:** dùng expectancy
   `P(win)*AvgWin - P(loss)*AvgLoss - all-in cost`, kèm dispersion/tail. PF, WR,
   net profit hay Sharpe đứng riêng đều không đủ.
3. **Signal, risk và execution là ba lớp khác nhau:** risk sizing/stop có thể đổi
   variance và ruin probability nhưng không biến signal âm thành alpha; execution
   có thể tiêu diệt gross edge dù setup đúng.
4. **Backtest là phép đo implementation:** nó chỉ nói rule/code/data/clock/cost
   contract đã chạy tạo ra gì. Nó không tự chứng minh causal story, khả năng live,
   hay rằng một discretionary memo đã được tái tạo đầy đủ.
5. **Selection làm méo kết quả:** chọn symbol, timeframe, session, year, direction,
   filter hoặc parameter sau khi xem outcome đều tiêu trial budget. Subgroup đẹp
   là hypothesis mới, không phải bằng chứng cứu run cũ.
6. **Regime phải biết tại decision time:** trend/range/volatility/liquidity/macro
   state chỉ hợp lệ khi feature và timestamp tồn tại trước entry. Nhãn hindsight
   không được làm filter trading.
7. **Optimization tìm plateau, không tìm champion:** một tham số chỉ đáng giữ khi
   vùng lân cận, split thời gian, cost stress và OOS cùng ổn. Đỉnh nhọn là prior
   curve-fit, kể cả khi PF cao.
8. **Cadence và exposure là một phần của edge:** DD/net loss thấp hơn do giảm 70%
   fills không đồng nghĩa signal tốt hơn. So expectancy/R, PF, opportunity set,
   time-in-market và loss drivers trên matched control.
9. **Data quality là đa chiều:** phần trăm history chỉ là coverage. Clock, gaps,
   bid/ask, commission, slippage, swap, symbol geometry và point-in-time lineage
   vẫn phải đúng theo claim. Ngoại lệ `>=98%` không tạo microstructure/order-flow
   data và không hồi tố run cũ.
10. **Portfolio edge cần độc lập thực:** nhiều EA dùng cùng EURUSD/session/stop
    geometry không tự thành diversification. Phải kiểm correlation, overlap,
    common loss driver và stress aggregation.

## Nhiệm vụ của Lead Quant/Systematic Trader

- Chuyển intent của Owner thành market thesis, decision-time rule, invalidation,
  matched control, risk/cost contract và phép falsify; chủ động đề xuất lựa chọn
  tốt hơn thay vì chỉ chấm input đạt/không đạt.
- Sau một valid failure, đóng đúng ID, tạo failure packet và tiếp tục sang search
  cell/materially-new hypothesis hợp pháp khi mục tiêu kinh tế còn UNMET. Kill
  nhanh là tốt; dừng sáng tạo sau kill là sai vai trò.
- Một search cell phải khai tối thiểu mechanism class, information set, symbol/
  timeframe, decision surface và trial budget. `NO LEGAL CANDIDATE` chỉ có hiệu
  lực trong cell đó.
- Không đánh dấu goal/book hoàn thành chỉ vì một lane terminal, một Deep Research
  không tìm được candidate, hoặc một delivery packet PASS với verdict KILLED.
  Goal completion cần outcome trong `01. GOAL/GOAL.md` hoặc quyết định dừng rõ của
  Owner.
- Báo cáo tiến độ phải mở đầu bằng trading outcome và trạng thái quyền:
  `no EA with positive expectancy | research survivor | confirmed | deploy-ready`;
  sau đó mới nêu engineering, artifact và blocker.
- Dừng xin Owner chỉ khi bước kế tiếp cần đổi thesis/symbol/risk scope vật chất,
  chi tiền, live/paper exposure, credential hoặc external authority. Các bước
  research/build/backtest an toàn đã nằm trong scope phải được tự đi tiếp.

## Authority, failure radius và quyền mở EA mới

Thứ tự quyết định một hành động có hợp lệ: scope Owner hiện tại → hard safety/
active lock → prereg + registry/task packet đã đóng băng → source/run/receipt/
validator thực tế. `hot.md`, `do_not_repeat_failures.md`, Deep Research và memo
review chỉ là evidence/context; chúng không tự cấp hoặc phủ quyết quyền build.

Mọi failure phải được đóng khung theo đúng **tested object**: hypothesis ID,
candidate identity, mechanism, data/source, symbol/timeframe/window, execution/
cost contract và mức fidelity. Không được suy từ “object này không có edge”
thành “indicator/family/thị trường này không thể có edge”. Phân loại trước khi
quyết định:

1. **Same ID / exact replay:** terminal row vẫn terminal; cấm rerun để tìm kết
   quả khác.
2. **Post-hoc rescue:** đổi threshold, session, direction, year, BE/SL/TP hoặc
   filter từ outcome vừa xem; cấm dưới ID cũ và mặc định không được bọc lại bằng
   ID mới nếu mechanism không đổi.
3. **Invalid engineering/data run:** sửa lỗi để tái hiện đúng frozen packet được
   phép khi outcome chưa có thẩm quyền; run vô hiệu không kết luận edge.
4. **Materially new hypothesis:** mechanism, information set/data contract hoặc
   decision surface thay đổi có luận cứ; được mở EA/ID mới sau khi ghi delta với
   prior, probe rẻ và prereg độc lập. Prior xấu làm tăng burden of proof, không
   phải blanket veto.
5. **Owner build-first:** được phép khi Owner yêu cầu rõ và lý do đảo thứ tự được
   freeze trước outcome; engineering vẫn phải qua test/compile/non-repaint và
   Model 0 vẫn cần registry/prereg/task packet đầy đủ.

Mục tiêu của de-dup là tránh lặp đúng dead end và budget data-snooping, không
phải làm agent mất khả năng sáng tạo hypothesis mới.

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
7. Mỗi search cell có budget hữu hạn. Nếu GPT lặp lại family đã đóng hoặc cùng
   blocker dữ liệu/execution chưa đổi, park **cell đó** và ghi exact boundary.
   Nếu mục tiêu Owner còn rộng hơn cell vừa đóng, lead phải chủ động mở search
   cell khác có mechanism/information set/decision surface thực sự khác trong
   scope; không được suy rộng thành frontier toàn dự án. Chỉ dừng toàn bộ khi
   search boundary cấp dự án đã khai và tiêu hết, hoặc bước kế cần quyền mới.

## Quy Trình Nghiên Cứu

Dùng vòng lặp này cho công việc chiến lược EA có ý nghĩa:

1. Định lượng thesis của trader và ghi nguồn/provenance. Deep Research là công
   cụ discovery khi cần cơ chế/nguồn mới, không phải ceremony bắt buộc cho brief
   đã đủ rõ.
2. De-dup với `do_not_repeat_failures.md` và registry bằng failure-radius test:
   ghi rõ `same replay|post-hoc rescue|invalid-run repair|materially new`; chỉ hai
   loại đầu bị chặn. Candidate hợp lệ tạo row `idea|probe`, draft MỘT prereg theo
   `02. AlphaFactory/templates/research/PREREG_TEMPLATE.md`.
3. Chạy probe/scanner offline rẻ TRƯỚC code entry EA. Probe dùng làm bằng
   chứng KILL/falsification phải freeze PROBE_PLAN tiền-kết-quả và SHA-bind
   vào row `idea|probe` (window/model/override/contract đóng băng ngay khi rời
   `idea`). Plan đã bind là bất biến: amendment pre-outcome PHẢI thành file
   `_V2.md` bind ở transition kế — không sửa in-place (validator hash-check
   mọi row lịch sử). Probe fail thì park/kill; probe pass giữ state `probe`
   (source có thể còn `null`); prereg Model 0 đầy đủ chỉ freeze khi thực sự
   build EA. Probe khám phá thuần (không dùng làm verdict) không cần plan
   đóng băng.
4. Build package canonical theo `ea_golden_path.md`, audit non-repaint, compile,
   rồi append `screened` với source + prereg hash:
   `powershell -NoProfile -ExecutionPolicy Bypass -File "02. AlphaFactory/alpha.ps1" compile "<EA_NAME>"`.
5. Trước MT5, capability contract, lifecycle telemetry, cost provenance và task
   packet phải đầy đủ; runner phải block sớm nếu thiếu.
6. Chạy control rồi challenger cùng symbol, timeframe, window, Model 0 và data/
   cost identity. Public strict loop chỉ chạy Model 0; evidence Model 1 từ lane
   legacy/được Owner duyệt chỉ có thể kill/park, không promote.
7. So với matched control đã đóng băng; không chấm một run đứng một mình.
8. Phân tích theo lane, hướng, session, giờ, tháng, năm, pha thị trường,
   giải phẫu trade, cost stress, và evidence screenshot/casebook. Với thay
   đổi strategy-state, ưu tiên snapshot MT5-native hoặc nhãn chart-state đã
   khóa trước khi patch luật EA — chi tiết ở "Contract Nhãn Chart-State".
9. Nếu run hợp lệ trượt gate hoặc hiệu suất yếu, đóng version hiện tại rồi chạy
   `Vòng Lặp Deep Research Sau Failure`; không tune/rescue cùng hypothesis.
10. Sau khi công việc ổn định, cập nhật đúng bề mặt sống: `hot.md`, registry,
    prereg/readout, `source_of_truth.*` nếu path đổi và failure memory nếu có kill.
11. Lưu trữ telemetry Common Files và artifact run cũ kèm manifest sau các
    backtest có ý nghĩa.
12. Dùng `02. AlphaFactory/tools/ea_research_loop.ps1` cho full-loop nghiêm túc;
    `research_loop_engine.ps1` là engine nội bộ phía sau, không gọi trực tiếp.

## Quy Trình Team Review

Khi user yêu cầu team/agent tham gia, dùng ba vai tách biệt và giữ
`fork_context=false` cho mọi agent được spawn:

- Strategy/trader critic: kiểm tra EA có ánh xạ đúng setup, regime, timing và
  invalidation của brief thay vì chỉ khớp mẫu indicator.
- Quant validation critic: kiểm tra data mining, candidate registry,
  matched control, WFA/PBO/Reality Check/Monte Carlo, cost stress, và luật
  kill/park.
- MQL5/MT5 systems critic: kiểm tra source path, bất biến non-repaint,
  sizing rủi ro, hình học broker, tier telemetry, dọn cache MT5, và khả
  năng tái lập artifact.

Memo của agent là input review, không phải thẩm quyền. Coordinator tổng hợp
chúng thành một hypothesis cụ thể, kế hoạch code/test, hoặc quyết định
park/kill có ghi chép.

## Candidate Registry

Không để thí nghiệm chỉ sống trong các readout rải rác. Mọi ý tưởng có ý
nghĩa cần registry row và prereg trước khi kết quả được dùng cho quyết
định.

Registry bao phủ mọi hypothesis EA/portfolio FX được Owner mở rõ ràng trong
workspace. Nó là append-only state ledger; vị trí file không tự cấp quyền chạy.
Registry + prereg/task packet hash-bound là authority máy cho trạng thái/run;
`hot.md` chỉ tóm tắt và có thể trễ.

Registry canonical:

- `04. Memory/research/CANDIDATE_REGISTRY.jsonl`
- schema + validator cùng thư mục; chạy
  `python "04. Memory/research/validate_candidate_registry.py"`
- template: `02. AlphaFactory/templates/research/`

Mọi run có ý nghĩa phải gắn với một `hypothesis_id`, `ea_name`, prereg/source
hash và row hash. Row `parked|killed` là terminal; không được revive cùng ID.
Khi canonical source tiếp tục sang hypothesis mới, row terminal cũ phải bind
source snapshot bất biến trong `research/source_snapshots/`; row còn active vẫn
phải bind canonical source. Không sửa ngược source hash lịch sử để làm validator xanh.

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

Quy tắc registry bổ sung:

- Registry `acceptance_contract` = bar GOAL/promotion (schema pin PF≥1.3,
  2-5 tpw), KHÔNG phải verdict instrument của probe. Kill-gate của probe sống
  trong plan đã SHA-bind; đọc verdict một row theo plan, không theo contract.
- Một design-only screen (không probe/evidence, ví dụ cron O-screen) thường
  chỉ ghi một prior chứ không tự thành kill terminal; chỉ verdict
  evidence-terminal (probe/Model 0 đã chạy) mới bind chống reopen. Khi một
  hypothesis Owner-scoped đã de-dup clearance muốn override prior đó, khai
  lựa chọn và lý do trong plan đóng băng.
- Append registry = ghi nguyên dòng + newline trong một lần write; chạy
  validator ngay sau mỗi append như commit gate. Binding sai phát hiện trước
  khi đọc outcome → sửa bằng corrective append/row mới, không mutate lịch sử.
- `trials/trial_log.jsonl` giữ per-EA-package (không ledger chung); mỗi row
  phải mang `hypothesis_id` + `prereg_sha256` để tự xác thực với plan.

Probe khám phá có thể gợi ý idea, nhưng promotion đòi một run tiền đăng ký
mới. Public strict loop không mở Model 1; evidence Model 1 legacy chỉ được kill
hoặc park, không được promote.

## Contract Fidelity Brief → Code

Trước probe kinh tế hoặc Model 0 cho brief discretionary/SMC/ICT, nên lập
matrix requirement→code cho các hard gate, entry timing, invalidation, stop,
target và quản trị trọng yếu, và khai độ phủ matrix trong plan. Mỗi hàng chỉ được phân loại `exact`, `proxy`, `missing` hoặc
`contradictory`, kèm source line và rule định lượng. Fixed score/điểm placeholder
không được đại diện cho một feature chưa đo.

- Probe builder, EA source, preset và prereg phải dùng cùng parameter semantics.
  Trước Model 0, so candidate identity/event id giữa builder và source; khác
  lookback, anchor hoặc invalidation là lỗi provenance, không phải variant edge.
- Kết quả run chỉ falsify hoặc support đúng proxy/source/config đã chạy. Không
  được tuyên bố đã falsify toàn bộ memo khi matrix còn `missing|contradictory`;
  đồng thời fidelity gap cũng không tự revive family hay cấp quyền rescue.
- Điều kiện chỉ tồn tại sau formation (retest, rejection, CISD/micro-confirmation)
  phải là state transition ở quyết định sau. Không gắn nó vào signal tại chính
  close hình thành FVG/zone rồi gọi signal đó `entry-ready`.
- Sửa correctness mà không đổi candidate identity không tự cấp quyền đọc lại
  outcome. Nếu identity đổi, đó là child/idea mới và phải qua de-dup, window và
  prereg mới; không dùng sửa bug làm đường vòng hậu nghiệm.

## Contract Nhãn Chart-State

Patch luật EA nên tựa vào feature đo được hoặc case image đã khóa, không nên đến trực tiếp từ trực giác nhìn chart.

Chart-claim trong readout/prereg nên tựa vào case image đã render (review) qua
`tools/research/chart_case_render.py` hoặc feature đo được, thay vì mô tả chart
thuần bằng suy diễn. Ảnh render từ chính bar data hash-bound của lane; mode
`asof` (không vẽ bar sau decision) cho chất lượng setup, mode `anatomy` cho
giải phẫu outcome.

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

Nên kèm negative control khi phân tích chart-state — ví dụ các lệnh thua
`SIDEWAY_WIDE`, lệnh thắng impulse, trade bỏ lỡ high-MFE, false positive
high-MAE, và session liền kề; khai bộ control đã chọn trong analysis plan.

Với corpus outcome-blind hoặc taxonomy discretionary:

- Freeze rubric, annotation schema, sample/density gates và analysis plan trước
  annotation output hoặc outcome join. `ambiguous` là nhãn thật, không ép thành
  pass/fail để làm đẹp thống kê.
- Source CSV bất biến; annotation ghi overlay theo `event_id`. Row và metadata
  phải bind collection id, contract/schema version, source SHA256, input identity,
  symbol/timeframe và decision cutoff. Schema thiếu hard-gate label thì corpus
  cũ chỉ diagnostic, không được vá label ngược vào source CSV.
- Lưu cả server time và UTC cùng offset đã đóng băng; ghi rõ decision timestamp
  là bar open hay close cutoff. MT5 Python history phải query theo trục broker
  server rồi chuẩn hóa offset và chứng minh bar cuối đã đóng trước cutoff.
- Annotation chỉ được dùng thông tin tồn tại tại cutoff. Nhãn post-formation cần
  packet/state sau formation; nếu chưa thể tồn tại thì phải `no`, không suy từ
  outcome tương lai.
- AI/rule annotation phải ghi rõ provenance và không tự cấp quyền economic run.
- Không join PnL/forward return/fill/MFE/MAE cho tới khi annotation contract và
  accepted-density gate qua, rồi đóng băng một analysis plan riêng. Gate fail
  thì đóng detector-to-memo gap, không tune taxonomy từ outcome.

## Contract Data-Acquisition / Casebook

Trước một acquisition trả phí hoặc thu toàn bộ corpus event-driven, phải chạy
một **source-semantics pilot tối thiểu, outcome-blind** trên mẫu đại diện đã khóa
trước. Pilot phải đo distribution của inter-arrival/gap, final staleness, clock
mà vendor dùng để cắt range (`event` hay `receive`) và pass-rate dự kiến của từng
source-quality gate. Không dùng full purchase để lần đầu khám phá rằng contract
nguồn không phù hợp.

- Mỗi ngưỡng source-quality phải ghi physical meaning, failure mode cần bắt và
  cách phân biệt missing/corrupt data với market inactivity hợp lệ. Với feed
  event-driven, "không có update" không mặc định đồng nghĩa "mất dữ liệu".
- Chi phí phải đi theo tầng: free metadata/quote -> minimal paid semantics pilot
  -> frozen full-design acquisition -> economic probe. PASS tầng trước chỉ mở
  tầng kế; không tự cấp quyền PnL, EA, promotion hay live.
- Báo cáo funnel dùng đúng từ:
  `request -> nonempty segment -> source-quality event -> feature-eligible event
  -> executable trade -> economic survivor`. Không gọi chung các tầng này là
  "tín hiệu", và phải nói trước goal EA/economic của Owner đang `MET` hay `UNMET`.

Data collection là một lane evidence riêng, không phải economic backtest rút
gọn. Trước khi chạy phải khóa collection id, authority, source contract, exact
source SHA, schema/header, taxonomy label, row cap, zero-trade rule, storage
roots và downstream consumer.

- Exact source identity phải khớp xuyên suốt task, receipt, manifest, metadata,
  từng row và extractor. Chỉ bind hash ở manifest không đủ cho label corpus.
- Freeze toàn bộ cột cần review trước collection. Thiếu một khái niệm cốt lõi
  làm corpus cũ `diagnostic-only`; giữ nguyên artifact cũ và thu corpus version
  mới, không backfill/ghi đè để giả vờ prereg từ đầu.
- Label/outcome columns phải trống; không ghi PnL, MFE, MAE, forward return hoặc
  fill outcome. Zero trade phải được report + summary chứng minh và đồng nghĩa
  WR/PF/expectancy không xác định, không phải bằng 0.
- Required sidecar thiếu, `OnInit` reject, input literal sai type, hash mismatch
  hoặc consumer schema drift đều là infrastructure-invalid. Sửa correctness rồi
  chạy lại cùng packet chỉ khi chưa đọc outcome; không dùng lỗi harness để kết
  luận strategy và không nới validation của EA.
- Extractor/analyzer phải có schema version riêng, bind exact corpus và
  preflight actual rows trước khi tiêu thụ. Parse được JSON/CSV chưa đủ.
- Mutation authority của collector phải tắt; terminal/tester nằm đúng storage
  contract; protected C roots có before/after inventory. Evidence D-side được
  giữ theo manifest, không xóa phá hủy chỉ vì collection không có trade.
- Engineering/data-lineage PASS không mở hypothesis kinh tế. Feature family
  mới phải có causal mechanism mới, analysis plan đóng băng, de-dup và fresh
  hypothesis/window.

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
- Verdict multi-simulation dùng DSR (Bailey/López de Prado, floor 0.95):
  N = MỌI simulation đã chạy (mọi stage, kể cả control và arm fail); cost
  tier x1/x1.5/x2 KHÔNG phải trial riêng (cùng trade set); V[SR] trên tất cả
  arm; PSR dùng skew + kurtosis non-excess, radicand ≤ 0 ⇒ fail (không skip).
  Chuỗi primary = pooled train+validation (split đã bị search không còn là
  OOS); implementation tự viết + self-test với ví dụ số trong paper
  (canonical: `02. AlphaFactory/tools/research/dsr.py`).

## Gate Promotion

Đừng promote một EA chỉ dựa trên profit factor. Ngưỡng theo stage và
artifact bắt buộc: `05. Playbook/validation_gates.md`.

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
- Git có thể tồn tại và remote private có thể đã được Owner mở. Agent không
  `git init`, stage/commit/push, amend hay force-push trừ khi Owner yêu cầu rõ
  trong message hiện tại; không dùng Git/archive làm nguồn build. Provenance
  run vẫn phải bind workspace snapshot + hash/receipt/validator/test đúng scope.
- Mọi compile/backtest lấy nguồn từ `00. Old File` hoặc path lưu trữ khác
  là evidence không hợp lệ và phải được đánh dấu như vậy trước khi trích
  dẫn.
- Run Strategy Tester zero-trade chỉ được gọi data acquisition khi có prereg
  `DATA_ACQUISITION_ONLY`, mutation false, outcome/labels blank, summary xác nhận
  zero trades và `performance_metrics_authorized=false`. Nó không cần/không tạo
  một economic hypothesis, không được trích PF/WR/cadence và phải dừng nếu phát
  sinh trade hoặc outcome-like field.
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
- Sau mọi pull MetaTrader5 qua python-bridge: `mt5.shutdown()` KHÔNG kết thúc
  `terminal64.exe` mà `initialize(path=...)` tự mở. Verify không còn orphan
  `terminal64.exe` và stop nó; receipt ghi process count before/after, không
  chỉ "shutdown() called".
- Probe/grid engine phải ghi raw per-trial/per-sim ra đĩa TRƯỚC bước
  summarize/serialize (crash bước tổng hợp → re-emit bằng post-processing,
  không re-simulate). `json.dumps` phải cast numpy (bool_/int64/float64) →
  native hoặc set `default=`.
