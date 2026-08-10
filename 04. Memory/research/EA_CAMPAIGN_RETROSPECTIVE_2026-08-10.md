# EA Campaign Retrospective — 2026-08-10

## Kết luận thẳng

Goal vẫn `ACTIVE / UNMET`. Tôi đã bảo vệ tốt ranh giới bằng chứng, nhưng điều hành campaign kém: time-to-admissible-economic-baseline quá dài và số artifact/hypothesis tăng nhanh hơn lượng thông tin kinh tế thu được.

Đây không phải vì ngưỡng PF >1.30 quá khó. Nguyên nhân chính là tôi đã áp tiêu chuẩn provenance gần mức promotion cho discovery, biến receipt/parser/authority/hash/path-set thành luồng công việc chính. Tôi đã tối ưu xác suất không tuyên bố sai, nhưng không tối ưu thời gian tới một baseline đúng và có thể kết luận.

## Số liệu kiểm điểm

### Checkpoint cập nhật sau baseline JCDR006

Sau snapshot đầu tiên, registry đã tăng lên `907` rows / `358` hypothesis. Theo
latest row của từng hypothesis, trạng thái hiện tại là `177 parked`, `175
killed`, `5 probe`, `1 screened`. Từ 2026-08-09 có `47` hypothesis terminal mới:
`28 killed`, `19 parked`; `32` thuộc Supertrend/STBS. Operator ledger đã có
`224` failure entries và worktree có `803` dirty paths (`22` tracked, `781`
untracked), trong khi HEAD vẫn là `521688f` từ 2026-08-09 00:49:06+07:00.

JCDR006 là bằng chứng rằng đường rút gọn hoạt động tốt hơn: một prereg ngắn,
focused tests, compile/non-repaint, một AlphaFactory Model-0 baseline và hai
review độc lập đã tạo verdict kinh tế dứt khoát. Baseline có `562` trades,
cadence `2.1568/week`, nhưng PF sau report costs chỉ `0.763972`, price-only PF
`0.851207`, expectancy `-$14.04/trade` và equity DD `8.02%`. Exact mechanism bị
KILL ngay; không phát sinh comparator/governance child và không mở
optimization/OOS.

HYP-ST-XAUUSD-H1-010 minh họa trực tiếp đơn vị tiến bộ sai: nó không phải một
chiến lược mới mà chỉ là comparator-only child. Attempt bị KILL vì zero-trade
validator coi dòng nạp vốn `balance` bắt buộc trong report là một trade. Việc
đánh số lỗi parser thành market hypothesis đã làm campaign dài và khó đọc mà
không thêm thông tin về edge.

Snapshot registry và workspace tại 2026-08-10:

- Registry có `899` rows / `354` hypothesis; latest states: `171 killed`, `176 parked`, `6 probe`, `1 screened`.
- Từ 2026-08-09 đến snapshot: `43` hypothesis; `24 killed`, `18 parked`, `1 probe`.
- Theo scope campaign chính xác ở registry rows `785–899`: `115` records / `51` hypothesis IDs trong gần 33 giờ; `29 killed`, `21 parked`, `1 probe`.
- Riêng chuỗi Supertrend Burst Scalper có `28` hypothesis.
- Nếu tính cả 12 H1 parity children, `40/51` campaign IDs xoay quanh cùng một Supertrend thesis; ít nhất `26/40` chủ yếu sửa harness/governance/parser/provenance.
- Chuỗi đó đã dùng `9` packet-build attempts, `11` comparator attempts và `12` MT5 launches. Chỉ `5` attempts chạm order-capable execution; bốn attempts tạo tổng cộng `1108` trade rows nhưng không có admissible economic baseline.
- Chỉ `9/43` hypothesis gần đây chạm Model-0; `0` có `returns_computed > 0`; `0` có economic verdict hợp lệ.
- Sau chuỗi STBS, chín source/indicator lanes liên tiếp được mở và đều dừng trước baseline: CRSI, Aroon x2, TRIX, WPR, TD9, AOTP, PSAR, BWAF và BKSR.
- Operator ledger ghi `196` failure từ 2026-08-09 đến snapshot.
- Worktree có `763` dirty entries: `22` tracked modifications và `741` untracked files.
- Commit gần nhất là `521688f` lúc 2026-08-09 00:49:06+07:00; khối artifact phát sinh sau đó chưa được gom thành checkpoint sạch.

Số hypothesis lớn không phải progress. HYP010–HYP012, chẳng hạn, chỉ là comparator/parser engineering children; chúng không đại diện cho ba chiến lược và không tạo thêm edge.

## Nguyên nhân gốc

### 1. Dùng sai mức assurance theo giai đoạn

Tôi áp claim-before-read, one-shot terminal, registry raw-row hash, full path-set hash, immutable receipts và mutation matrix gần như đồng đều cho source screen, parity, DQ, baseline và comparator. Một số lớp là cần thiết, nhưng toàn bộ bộ máy đó chỉ hợp lý khi artifact có khả năng ảnh hưởng verdict kinh tế hoặc promotion. Discovery cần fail-closed, không cần promotion-grade ceremony.

### 2. Chọn sai đơn vị tiến bộ

Mỗi lỗi engineering nhỏ thường sinh fresh HYP thay vì một engineering incident hoặc attempt correction bị giới hạn. HYP count trở thành proxy giả cho tiến bộ. Đặc biệt, parser funding row, Orders colspan, journal cap, receipt normalization và path-set drift không phải market hypotheses.

### 3. Không có budget cứng cho time-to-baseline

Workflow có anti-setup guardrail nhưng tôi không thực thi. Chuỗi STBS vượt xa ba engineering revisions mà vẫn tiếp tục vì từng blocker riêng lẻ có vẻ hợp lý. Tôi đánh giá từng bước cục bộ, không đánh giá opportunity cost toàn campaign.

Các điểm đáng lẽ phải dừng hoặc đổi sớm hơn là HYP-ST-012 sau exact MQL parity, STBS006 sau signal/ATR/geometry audit, hoặc muộn nhất sau STBS013 với đúng một margin/lifecycle revision. Sau diagnostic research-proxy xấp xỉ PF `0.33`, tiếp tục comparator recovery không còn đủ expected information value.

### 4. Review đúng nhưng quá muộn

Reviewer bắt được nhiều lỗi thật, nhưng thường sau khi prereg, builder, registry row hoặc compile package đã được tạo. Review đáng lẽ phải diễn ra trên một source-to-spec matrix tối thiểu trước khi đóng băng identity. Lỗi CBRK là ví dụ: session gate dùng decision time thay vì signal-bar time; kiểm tra bốn boundary bars trước compile đã phát hiện ngay.

### 5. Governance tự tham chiếu trong một worktree động

Sealing toàn bộ `git status` path-set trong workspace nhiều agent/artifact khiến chính review/failure docs mới tạo ra drift. Sau đó drift lại buộc fresh outer HYP. Đây là thiết kế harness tạo lỗi cho chính nó. Run evidence phải bind scoped inputs/attempt-local outputs, không bind mọi path không liên quan trong repo.

### 6. Mở tournament source-screen quá rộng

Sau khi dừng STBS, tôi chuyển nhanh qua nhiều indicator, nhưng vẫn tạo prereg/analyzer/receipt/registry/review đầy đủ cho từng source screen. Nhiều lane chỉ trả lời cadence/coverage, không trả lời expectancy. Source feasibility là gate cần thiết khi dữ liệu/cadence chưa biết, không phải sản phẩm cuối của mỗi indicator.

Trong các source scans hoàn tất sau Supertrend, sáu fail cadence; ba fail exact-next/clock coverage và Aroon còn fail feature coverage. PARK từng mapping là đúng, nhưng prior turnover của TRIX zero-cross, WPR re-entry, AO twin-peaks, PSAR flip và BWAF đáng lẽ phải được đánh giá trước khi mở đầy đủ evidence object.

### 7. Không đưa market question lên trước

Mỗi vòng đáng lẽ phải hỏi: “Thông tin tiếp theo có làm tăng hoặc giảm xác suất PF sau phí không?” Nhiều vòng thực tế chỉ hỏi: “Hash/receipt/parser này đã tuyệt đối kín chưa?” Câu hỏi thứ hai chỉ có giá trị khi nó mở khóa câu hỏi thứ nhất trong thời gian ngắn.

### 8. Không giữ một baseline sạch của repository

Worktree quá bẩn làm tăng rủi ro ownership, hash drift, false failure và chi phí review. Tôi đã để artifact tích lũy thay vì tạo checkpoint có chủ đích. Điều này vừa vi phạm tinh thần AGENTS.md vừa làm AlphaFactory khó vận hành ổn định.

### 9. Quá nhiều tool/harness errors có thể tránh

Các lỗi shell quoting, unsupported parameters, patch context, broad search và fixture góp thêm noise. Chúng không giải thích toàn bộ độ trễ, nhưng cho thấy tôi chưa chuẩn hóa command path và chưa dùng đủ exact-scope inspection.

### 10. Tự đánh đồng persistence với tiếp tục cùng một đường

Owner yêu cầu không hủy goal khi PF thấp; điều đó có nghĩa tiếp tục tìm edge qua hypothesis/mechanism mới, không có nghĩa phải cứu một engineering chain vô hạn. Tôi đã hiểu đúng trên lý thuyết nhưng vận hành sai ở STBS.

## Điều làm đúng và phải giữ

- Không dùng outcome từ engineering-invalid run để tuyên bố edge hoặc no-edge.
- Không sửa ngược hypothesis sau khi nhìn kết quả.
- Tách `engineering-valid`, `economic-valid`, `promotion-ready`.
- Reviewer độc lập bắt được lookahead/clock/lifecycle/provenance false-pass thật.
- Failure radius được đóng hẹp; goal không bị hủy vì một hypothesis thất bại.
- Cost, data quality, closed-bar causality và lifecycle reconciliation vẫn là hard gates.

Những điều này không biện minh cho độ dài campaign; chúng là nền tối thiểu cần giữ trong một quy trình gọn hơn.

## Operating policy mới

### KPI điều hành

KPI chính từ đây là `time-to-first-admissible-untuned-baseline`, không phải số HYP, số test hay số receipt.

Mọi update phải mang một trong năm nhãn: `market thesis`, `source/formula`, `implementation`, `economic evidence`, `validation`. `governance only` không được tính là tiến bộ về goal.

### Budget cho một mechanism

1. Một prereg ngắn và một source-to-spec matrix trước code/run.
2. Một static review trước freeze; boundary time/indexing phải có fixture.
3. Tối đa hai engineering revisions sau source pass trước baseline. Revision thứ ba cần independent opportunity-cost PASS và phải có xác suất cao mở baseline, không chỉ sửa metadata.
4. Không tạo wrapper/harness riêng nếu AlphaFactory hiện hữu có đường hợp lệ. Lỗi hạ tầng chung đi vào backlog hoặc một shared fix, không sinh chuỗi market HYP.
5. Không mở nhiều hơn một market mechanism active cùng lúc.

### Đường mặc định

`market thesis -> frozen spec -> focused tests/compile/NR -> one zero-outcome DQ smoke only when needed -> one untuned Model-0 baseline -> economic triage`.

Source-only cadence scan chỉ dùng khi cadence/data availability thực sự chưa biết. Nếu một EA hoàn chỉnh đã có source-density evidence phù hợp, đi thẳng tới correctness rồi baseline.

### Triage sau baseline

- Engineering failure: sửa tối đa một bounded revision nếu nguyên nhân không thay đổi market logic.
- PF xa ngưỡng, expectancy âm rộng theo năm/hướng và không có implementation defect: đóng mechanism, không thêm filter/session/R:R.
- PF gần ngưỡng và diagnostics hỗ trợ một causal revision đã prereg: cho đúng một revision.
- PF >1.30 x1 và cadence đạt: mở cost stress x1.5/x2 rồi validation; chưa tối ưu trước đó.

### Hygiene

- Trước bất kỳ one-shot run nào phải có scoped clean checkpoint hoặc isolated evidence root.
- Không seal toàn bộ dynamic worktree path-set; bind exact source/config/prereg/task/runner và attempt-local outputs.
- Review artifact phải được tạo trước authority hoặc nằm trong reserved attempt-local path, không tự làm drift receipt.
- Cuối mỗi bounded task: review diff, validator/tests, secret scan, commit/push khi quyền/remote cho phép.
- Duy trì KPI: source-pass tới admissible baseline không quá một ngày; tối đa ba engineering IDs per baseline; governance-only IDs luôn được báo là chi phí, không phải progress.

## Quyết định cho CBRK

HYP-CBRK-XAUUSD-M5-001 được PARK ở mức engineering trước execution vì session gate dùng decision-time `utc_now`, làm lệch signal-bar window một M5 bar. Không có MT5/outcome/economics và cơ chế chưa bị bác bỏ.

Fresh HYP-CBRK-XAUUSD-M5-002 là revision duy nhất được phép cho lỗi này:

- dùng `ServerToUtc(rates[0].time)` sau `LoadClosedBars()`;
- gate `[07:00,16:00)` trên signal bar;
- dùng signal UTC cho exact 72 Asian bars;
- test 06:55 reject, 07:00 accept, 15:55 accept, 16:00 reject;
- DQ phải freeze đúng `351303` bars và dùng một path AlphaFactory chuẩn, không mở một campaign harness mới.

Sau khi HYP002 có một baseline admissible, phải đưa ra economic verdict ngay. Không có HYP003 governance rescue. Nếu baseline kinh tế fail rõ, chuyển mechanism; nếu pass, mở validation/holdout theo GOAL.

Adverse prior phải được giữ trong quyết định: EURUSD cùng atomic sleeve đã có PF `0.7466504499` và cadence `1.1026645768/week`. Nó không được dùng để bác bỏ XAU trước khi chạy, nhưng làm expected value của việc cứu thêm revision sau baseline thấp hơn đáng kể.
