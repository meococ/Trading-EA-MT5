# Session Trader Control Plane

MVP vận hành theo nguyên tắc:

> AI được quyền đề xuất. Code có quyền từ chối. Broker state là sự thật cuối cùng.

Package này đứng cạnh AlphaFactory; không thêm live/demo command vào `alpha.ps1` và
không chạm package EA đang chạy. Import package không kết nối MT5.

## Trạng thái

| Mode | Trạng thái | Quyền |
|---|---|---|
| `OBSERVE` | implemented | read-only snapshot, plan, heartbeat, journal |
| `SHADOW` | implemented | candidate/critic/intent/risk thật; chỉ `would-send` |
| `DEMO_EXECUTE` | locked | trả `MQL5_HANDOFF_REQUIRED` cho tới khi EA executor canonical được compile/accept |
| `LIVE_LOCKED` | hard locked | Python không có live path; `live_execution_authorized` chỉ nhận `false` |

Không có `MetaTrader5.order_send()` hoặc `order_check()` trong control plane.
Python chỉ đọc terminal và tạo artifact; execution tiền phải thuộc một EA MQL5
canonical có `OrderCheck`/send/`OnTradeTransaction`/broker reconciliation.

## Luồng đã có

```text
SessionPlan vN (write-once + SHA link)
  -> read-only Market/Account/Calendar snapshot
  -> deterministic heartbeat (no trigger = sleep)
  -> Candidate task
  -> blind Critic task (không thấy narrative/confidence vòng đầu)
  -> TradeIntent
  -> deterministic Risk Gateway
  -> hash-bound MQL5 handoff packet (broker_mutation_allowed=false)
  -> execution receipt / reconciliation contract
  -> hash-chain ledger
  -> JournalReport + offline ResearchQueue only
```

`SessionPlan` v2+ bắt buộc trỏ đúng SHA256 của v ngay trước và có thời điểm tạo
muộn hơn version trước. Store dùng exclusive create nên không thể overwrite v1.
Ledger JSONL khóa concurrent writers, reserve idempotency atomically, `fsync` và
hash-link từng record; sửa/cắt file sẽ làm verification fail. SHA-chain chưa phải
chữ ký chống privileged writer rewrite toàn bộ lịch sử, nên demo executor vẫn bị
khóa cho tới khi có external anchor/signing hoặc append-only authority tương đương.

## Risk Gateway

Gateway thuần code và giữ toàn bộ lý do reject. Các gate hiện có:

- kill switch và hard live lock;
- demo/contest/real mode, account fingerprint allowlist;
- account, quote, calendar TTL; calendar unavailable;
- server-time to UTC mapping chưa verified;
- terminal disconnected/trading/expert disabled;
- intent expiry và duplicate idempotency key;
- symbol allowlist, entry range, SL/TP geometry, broker stop distance;
- minimum R:R, spread và high-impact news blackout;
- daily/weekly loss, drawdown, consecutive losses, max trades/session;
- aggregate, per-symbol và correlation-group open risk;
- risk cap và volume làm tròn **xuống** theo tick-size/value + broker volume step.

Risk state ngày/tuần không thể suy ra an toàn từ một snapshot. Collector chỉ nhận
typed `RiskState` khi nó đồng thời khớp account fingerprint, SessionPlan, verified
ledger head và TTL; boolean `verified` tự khai không còn tồn tại. Nếu thiếu bất kỳ
binding nào, `risk_metrics_complete=false` và Gateway reject.

Terminal/broker build có thể trả tick epoch theo UTC hoặc theo server clock. Local
MetaQuotes-Demo 5.0.5509 hiện trả epoch lệch +3h, nên collector không đoán basis để
cấp quyền. Muốn verified mapping phải khai báo cả offset và basis (`UTC` hoặc
`SERVER`); thiếu một trong hai thì chỉ inference để quan sát và
`time_mapping_verified=false`.

## Agent boundary

`agents.py` chỉ tạo typed task và validate JSON output. Không có provider cloud mặc
định vì spend hiện là USD 0. `FileOutputAdapter` nhận output từ model/human runner
ngoài package. Candidate và Critic có thể bắt buộc provider khác nhau; blind Critic
chỉ nhận raw plan/market/account và order fields, không nhận confidence, evidence
narrative hay reasoning của Candidate.

AI output luôn phải được ghi thành immutable `Candidate`/`Critique`/`TradeIntent`.
`Candidate` bind cả plan, market và account snapshot. `pipeline.py` đọc-hash-parse
cùng một byte buffer, xác minh toàn bộ SHA chain/chronology và cấm Trade Architect đổi
symbol/direction/scenario/SL/TP, tăng risk, nới entry range hoặc kéo dài expiry.
Generic CLI không được mint `RiskDecision`, `ExecutionAttempt`, `Reconciliation`,
`AccountSnapshot`, `RiskState` hoặc policy authority.

## CLI

Chạy từ `02. AlphaFactory` hoặc đặt thư mục này vào `PYTHONPATH`:

```powershell
$env:PYTHONPATH=(Resolve-Path "02. AlphaFactory").Path

# Chỉ đọc terminal. Không có calendar/risk ledger thì snapshot ghi rõ unavailable.
# `--terminal` bắt buộc từ 2026-08-31: thiếu nó thì collector gọi
# mt5.initialize() trần và bám vào bất kỳ terminal nào đang chạy.
# Observation plane trỏ vào Owner GUI; research/backtest KHÔNG chạy ở đây
# (xem "Hai mặt phẳng MT5" bên dưới).
python -m session_trader probe --symbol EURUSD --terminal "D:\Meta 5\terminal64.exe"

# Offset + tick basis phải đến từ source đã xác minh trước khi pass Risk Gateway.
python -m session_trader probe --symbol EURUSD --terminal "D:\Meta 5\terminal64.exe" `
  --server-utc-offset-minutes 180 --tick-time-basis SERVER

# Plan là write-once; v2 phải link SHA của v1.
python -m session_trader write-plan `
  --input "02. AlphaFactory/session_trader/examples/SESSION_PLAN_2099-01-01_LONDON_v1.json" `
  --artifact-root "02. AlphaFactory/runtime/session-trader"

# Candidate/Critique/Intent typed artifact. Authority artifacts không đi qua lệnh này.
python -m session_trader write-artifact --model TradeIntent `
  --input <intent.json> --path "intents/INTENT-001.json" `
  --artifact-root "02. AlphaFactory/runtime/session-trader" `
  --ledger "02. AlphaFactory/runtime/session-trader/events.jsonl" `
  --session-plan-id SESSION_PLAN_2026-08-27_LONDON

# Một heartbeat deterministic; gọi lệnh này mỗi 10 phút hoặc khi có event.
python -m session_trader watch --refs <watch-refs.json> `
  --config "02. AlphaFactory/session_trader/examples/watcher.example.json" `
  --artifact-root "02. AlphaFactory/runtime/session-trader" `
  --ledger "02. AlphaFactory/runtime/session-trader/events.jsonl"

# Chỉ SHADOW/OBSERVE; kết quả luôn sent=false.
python -m session_trader shadow --refs <trade-chain-refs.json> `
  --artifact-root "02. AlphaFactory/runtime/session-trader" `
  --ledger "02. AlphaFactory/runtime/session-trader/events.jsonl"

python -m session_trader verify-ledger `
  --ledger "02. AlphaFactory/runtime/session-trader/events.jsonl"

python -m session_trader journal `
  --ledger "02. AlphaFactory/runtime/session-trader/events.jsonl" `
  --artifact-root "02. AlphaFactory/runtime/session-trader" `
  --session-plan-id SESSION_PLAN_2026-08-27_LONDON `
  --session-date 2026-08-27
```

Runtime nằm dưới `02. AlphaFactory/runtime/` nên không vào Git. Không bật scheduler
hay Algo Trading trong tranche này. Heartbeat là one-shot để Task Scheduler/service
gọi sau khi OBSERVE/SHADOW replay được Owner chấp nhận.

## Calendar

Local `MetaTrader5 5.0.5509` không expose Calendar API. Native calendar nằm phía
MQL5 và dùng trade-server time. Vì thế collector chỉ nhận calendar artifact đã
normalize UTC kèm server-time/offset evidence. Calendar thiếu/stale sẽ làm Risk
Gateway reject; package không tự suy diễn “không có tin”.

## Verification

```powershell
$tests = Get-ChildItem "02. AlphaFactory/tests/test_session_trader_*.py"
python -m pytest -q -p no:cacheprovider $tests.FullName
```

Focused suite kiểm tra immutability/tamper/concurrent ledger + atomic reservation, heartbeat sleep và
event triggers, blind critic, risk gates, sizing, time/calendar freshness,
idempotency, shadow handoff, read-only collector, journal và static no-order-send.

## Trạng thái đã chạy thật (2026-08-31)

Trước ngày này Python trên máy Owner là Microsoft Store stub, nên **chưa dòng
nào của package này từng chạy**. Sau khi cài Python 3.12.10 và pydantic, đã
verify end-to-end:

| Bước | Lệnh | Kết quả |
|---|---|---|
| OBSERVE | `probe --symbol XAUUSD --terminal "D:\Meta 5\terminal64.exe"` | `connected=true`, `read_only=true`, `orders_sent=0`, XAUUSD 4435.68/4435.98 |
| Time mapping | thêm `--server-utc-offset-minutes 180 --tick-time-basis SERVER` | `time_mapping_verified=true`, source `EXPLICIT_SERVER_TICK_EPOCH` (không có 2 cờ này thì chỉ `INFERRED`, Gateway reject) |
| Artifact | `write-plan --input examples/SESSION_PLAN_...v1.json` | ghi kèm SHA256 |
| Immutability | chạy lại đúng lệnh trên | từ chối: `artifact already exists` |
| Test | 12 module `test_session_trader_*` | 12/12 pass |

Quan sát từ terminal Owner lúc verify: `trade_mode=DEMO`,
`terminal_trade_allowed=false` (AutoTrading đang tắt), `positions_count=0`.

**`--terminal` là bắt buộc.** Trước đây bỏ trống thì collector gọi
`mt5.initialize()` trần và bám vào bất kỳ terminal nào đang chạy.

Còn khoá: `DEMO_EXECUTE` vẫn trả `MQL5_HANDOFF_REQUIRED`. Mở được nó cần một EA
executor MQL5 canonical đã compile + accept, không phải thêm code Python.

## Hai mặt phẳng MT5

Chốt 2026-08-31 khi bật MCP. Doctrine này trước nằm ở `AGENTS.md`; file đó đã bị
gỡ khỏi repo nên nội dung chuyển về đây.

- **Research plane** — `alpha.ps1` + portable isolate dưới
  `02. AlphaFactory/runtime/`. Là **nơi duy nhất** được compile, backtest và sinh
  evidence. Có thẩm quyền kinh tế.
- **Observation plane** — package này, và MCP server nội bộ của MT5 tại
  `127.0.0.1:22346`, gắn vào terminal GUI Owner đang trade. Chỉ đọc:
  account/positions, lịch sử lệnh, chart/tick history theo giá broker thật,
  journal. **Không** có thẩm quyền kinh tế, không sinh evidence.

Cấm:

- Dùng `tester_run_backtest` qua MCP để lấy số ra quyết định. MCP backtest được
  thật (đã verify 2026-08-31, trả report JSON đầy đủ), nhưng nó chạy trong
  terminal Owner, tranh CPU với lệnh sống và dùng history của broker đó chứ không
  phải isolate đã pin.
- Pin `alpha.local.ps1` vào `D:\Meta 5`. `alpha.ps1` throw ở cả hai trường hợp.

Python attach: luôn `mt5.initialize(**mt5_initialize_kwargs())` từ
`02. AlphaFactory/tools/factory_paths.py`. `mt5.initialize()` trần bám vào
terminal Owner. Gác bởi `tools/check_mt5_attach_contract.ps1`.

### MCP có đường gửi lệnh — không được dùng

`get_trading_account_info` trả về hai quyền **độc lập**:

```
"experts_trade_allowed": false     <- nút AutoTrading trong GUI
"mcp_trade_allowed":     true      <- đường lệnh của MCP, nút trên KHÔNG phủ
```

MCP expose `trade_send_market_order`, `trade_send_pending_order`,
`trade_modify_sl_tp`, `trade_close_single_position`, `trade_close_by_position`,
`trade_delete_order`. Đường đó **đi vòng qua toàn bộ control plane này** — không
SessionPlan, không blind Critic, không Risk Gateway, không idempotency key, không
ledger. Quyền thuộc về terminal chứ không phải account, nên nó giữ nguyên sau khi
login tài khoản funded.

Không gọi bất kỳ tool `mcp__mt5__trade_*` nào. Mọi execution đi qua Risk Gateway.
