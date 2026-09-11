# INDICATOR WORKFLOW — Port TradingView → MT5 tới nơi tới chốn

Áp dụng khi làm / sửa **indicator** (look, HUD, object, HTF overlay, gắn chart).
EA edge vẫn theo `05. Playbook/WORKFLOW.md`. Hợp đồng vận hành ngắn:
`AGENTS.md` § Indicator.

Không khai DONE nếu vòng snapshot-review chưa **PASS**.

## 0. Contract

- Làm hết vòng. Research → plan → implement → deploy → snapshot → review.
- Nến chart (`default.tpl` trắng-đen) độc lập overlay indicator (màu TV).
- Compile: log mới `0 errors, 0 warnings` + EX5 mới. Live GUI load
  `%APPDATA%\MetaQuotes\Terminal\9CA16B8382AE4CF692710FB36B9DA355\MQL5\...`.
- Không `mt5__trade_*`. Không `path=` launch Owner terminal.
- Không commit/push trừ Owner hỏi trong message hiện tại.

## 1. Research TradingView — source + painting

Trước mọi edit:

1. Mở đúng script TV (link `#property link` hoặc URL Owner đưa).
2. **Source:** tab Source code / Pine. Ghi `input.color`, `table.new` position,
   `box`/`line`/`label` style, HTF (nếu có). Playwright MCP nếu session có;
   không thì Playwright + Chrome (`channel: 'chrome'`), không bịa màu.
3. **Painting:** screenshot preview chính thức (`s3.tradingview.com/i/<id>_mid.webp`)
   và/hoặc chart live. Ghi: nền chart, màu nến, màu BOS/MSS/cell/void/HUD,
   góc HUD, có/không ô HTF trên LTF.
4. Artifact: `04. Memory/research/` note ngắn + path ảnh (không commit binary
   nặng). Thiếu source hoặc thiếu painting = chưa được implement.

TV không vẽ overlay H4 trên LTF thì port MQL5 **không được giả** đó là “chart H4”.
Chart H4 = cửa sổ `PERIOD_H4` + EX5 gắn vào.

## 2. Convert plan — bắt buộc trước code

Plan phải map từng bề mặt TV → MT5:

| TV | MT5 |
|---|---|
| `input.color(#RRGGBB)` | `input color Inp* = C'R,G,B'` + COLORREF khi MCP add |
| `table.new(position.*)` | `OBJ_RECTANGLE_LABEL` + `OBJ_LABEL`, **góc không đè cột giá** |
| `box` / `line` / `label` | object hiện có; không mint object type thứ hai |
| HTF trên TV | chart H4 thật *hoặc* overlay — ghi rõ cái nào, chỗ đặt pixel |
| nến | `default.tpl` (B&W) trừ Owner đòi theme khác |

Nếu **chưa có plan** trong conversation: spawn `subagent_type: plan` (cố vấn).
Prompt: TV source snippet + painting path + file MQL5 hiện có. Cấm implement
trong sub đó. Main chỉ edit sau khi plan có caller/symbol/test thật
(implement-research).

## 3. Implement

- Search trùng tên/job trước khi mint (màu, HUD, HTF panel, spark).
- Sửa **cả** live `MQL5\Indicators\...` (GUI load) và copy repo nếu SHA lệch.
- Không đổi buffer contract / engine trừ Owner hỏi.
- Compile: MetaEditor `-Wait` vào data folder GUI **hoặc** `alpha.ps1 compile`
  rồi copy EX5 vào đúng path GUI. Evidence = log + EX5 mới.

## 4. Deploy lên chart

1. Unload: `chart_apply_template` `default.tpl` **trước** (không song song với add).
2. Compile (EX5 không bị lock).
3. `chart_add_indicator` với Name=Value: màu TV, `InpDrawObjects=1`,
   `InpShowHud=1`, module cần bật = 1, `InpHtfPeriod` đúng TF.
4. Chart H4: `chart_open` symbol `H4` → template → add. Trên H4,
   overlay HTF phải tắt (`g_htfSameAsChart` / không vẽ ô H4 trùng TF).
5. Đợi vẽ (vài giây). `list_open_charts` chỉ xác nhận EX5 + input, **không**
   thay snapshot.

### H4 inset `OBJ_CHART` — MT5 affordance, không phải TV parity

Contract từ `04. Memory/research/20260905_H4_OBJ_CHART_INSET.md`
(kèm `20260906_TV_SMC_INDICATOR_REVIEW.md`). Pine `IM2GxnOK` không có LTF H4
overlay — inset là tiện nghi MT5, không phải parity target.

- Chỉ trên LTF (M5/M15): pane H4 **góc trái-dưới**. `OBJ_CHART` không có
  ANCHOR — đặt `CORNER_LEFT_UPPER` + `Y = chartH − height − pad`;
  `LEFT_LOWER` đẩy box ra khỏi pane. Tên `g_prefix+"INSET_CHART"`, **không**
  dưới `HTF_` (RebuildVisuals từng wipe prefix đó).
- Size = % chart cha + floor pixel, pad X=10 Y=24 (visual 2.40: 42%×36%,
  ~380×220; 2.45 ship 52%×46%, floor 460×260).
- Nested = `_Symbol` `PERIOD_H4` thật, date+price scale on, B&W copy từ
  parent; `ChartApplyTemplate(tb_smc_inset.tpl)` sau save — `ChartIndicatorAdd`
  EX5 này trả 4114.
- Bool `InpShowHtfInset` default true, append **sau** 46-slot contract. MCP
  `chart_add_indicator` phải truyền `InpShowHud=1,InpDrawObjects=1,
  InpShowHtfInset=1` — bare add zero hết bool.
- Skip inset khi chart TF == H4. Nested HUD chỉ tắt khi
  `_Period == InpHtfPeriod` **và** `CHART_IS_OBJECT` — không gate host theo
  `CHART_IS_OBJECT` một mình.

## 5. Refresh + snapshot

- Focus đúng tab (title cửa sổ MT5 chứa `SYMBOL,TF`).
- Chụp cửa sổ `MetaQuotes::MetaTrader::5.00` (PrintWindow / PNG).
- Crop chart. Lưu
  `%APPDATA%\MetaQuotes\Terminal\9CA16B8382AE4CF692710FB36B9DA355\MQL5\Files\Temp\`.
- Thiếu ảnh đúng TF = chưa xong.

## 6. Subagent trung gian review

Spawn `explore` hoặc `general-purpose` **sau** snapshot. Prompt gồm:

- path ảnh vừa chụp;
- đề bài Owner + convert plan;
- painting TV (ảnh/hex);
- past mistakes (`AGENTS.md`).

Reviewer chỉ được PASS / FAIL. FAIL phải chỉ lỗ trên ảnh (đè cột giá, sai góc,
sai màu, thiếu H4, clock `gap`, HUD chồng overlay, …). Không PASS vì “code đã sửa”.

## 7. FAIL → làm lại từ đầu

Quay **bước 1**. Ghi lỗi mới vào `AGENTS.md` § Past mistakes (và đây nếu lặp).
Không vá lớp song song (HUD thứ hai, màu hardcode thêm, panel mới).

## Past mistakes (2026-09-05)

Xem `AGENTS.md` § Past mistakes. Tóm tắt: B&W đè màu TV; HUD phải đè giá;
H4 overlay chồng HUD trên pane tiled; spark ≠ chart H4; `gap` weekend trên
SOLUSD; add indicator song song template; không snapshot đúng tab.
