# PA-PRO EA — hướng dẫn cho anh (Owner)

## EA này làm gì

`PA_Pro` là EA nhận diện vùng giá (zone) nhân quả trên khung M5, port
nguyên bản từ research Python PA-PRO. Mỗi khi một nến M5 **đóng**, EA
chạy một vòng: cập nhật 6 bộ sinh zone → phát hiện setup → kiểm tra
veto (session/weekend/Friday/risk) → dựng order plan → vẽ lên chart +
ghi journal CSV.

**Mặc định `InpSignalOnly = true`: EA chỉ vẽ và ghi log, KHÔNG gửi
lệnh.** Chỉ anh mới được flip cờ này. Toàn bộ API order nằm gọn trong
một hàm `PaExecutePlan` (PA_Trade.mqh) với gate `if(signal_only) return`
ở dòng đầu — test `tests/test_signal_only.py` chứng minh không đường
nào tới order API khi cờ bật.

## Cấu trúc file (mql5/)

| File | Vai trò |
|---|---|
| `PA_Types.mqh` | struct + hằng số frozen từ Python (cite từng dòng) |
| `PA_Clock.mqh` | server→UTC, DST +2/+3, mod-1440, dow Monday=0 |
| `PA_Zones.mqh` | engine zone: 2 track state (pass `st` + replay `sx`), 6 generators |
| `PA_Session.mqh` | cửa sổ EU/US, veto cuối tuần/thứ 6, flat rules |
| `PA_Risk.mqh` | size theo stop distance 0.5%; lock -4%/ngày; lock -8% DD |
| `PA_Trade.mqh` | order plan (stop +1 pip, SL structure, TP 2R, expiry 3 nến) + `PaExecutePlan` gated |
| `PA_Setups.mqh` | interface module + 2 stub (F1 rejection, F2 break-retest) — Setup Factory thả survivors vào đây |
| `PA_Journal.mqh` | CSV 23 cột giống hệt `pa_fill.simulate` |
| `PA_Visual.mqh` | overlay (zone-era, legacy): zone rectangle, entry/SL/TP, SKIP, HUD |
| `PA_Export.mqh` | export armed zones → CSV cho parity |
| `PA_Perception.mqh` | schema mirror + importer snapshot CSV (perception lane) |
| `PA_Draw.mqh` | grammar vẽ Volman (12 loại object, spec §2) + theme + budget |
| `../PA_Pro_View/` | indicator view-only: đọc snapshot CSV, vẽ object lên chart |
| `PA_SelfTest.mqh` | 1372 golden vectors clock/session |
| `PA_Pro_EA.mq5` | EA chính; `PA_Pro.mq5` ở thư mục cha là shim compile |

## PA_Pro_View — xem snapshot Volman trên chart

Direction mới (Lead Ruling 2): lớp vẽ dùng **object grammar** thưa thớt
theo spec `docs/perception/VOLMAN_PERCEPTION_SPEC_v1.md` — không còn vẽ
zone dày đặc. Engine Python lane vẫn đang build; `PA_Pro_View` là
indicator **chỉ-xem** (không một dòng trade code) đọc file snapshot CSV
từ `MQL5\Files` và vẽ các object lên các bar đang nhìn thấy.

Cách chạy đầy đủ: **`VIEWER_RUNBOOK.md`** (compile → sinh mock CSV →
copy vào `MQL5\Files\PA_Pro\` → kéo indicator lên chart EURUSD M5,
scroll về ngày của snapshot). Mock test: `python tools/mock_snapshot.py
EURUSD out\perception_EURUSD.csv 2019-03-04` → scroll về 2019-03-04.

### Bảng object → cách đọc (paraphrase theo spec §2)

| Type | Hình dạng | Nghĩa trên chart |
|---|---|---|
| `BOX` | hình chữ nhật đặc + 2 dải mỏng ở mép ±tol | vùng sideway/bế tắc — 2 mép là rào giá |
| `RANGE_OPEN` | 2 đường ngang trơn, không đầu mút | range đang mở (ví dụ Asia hi/lo) — rào chưa bị phá |
| `CONTEXT_RANGE` | hình chữ nhật chấm | vùng cảnh giới (ví dụ quanh 1.1350) — không phải structure |
| `PATTERN_LINE` | chéo nét liền, kéo dài sang phải | đường trigger của pattern (M/W...) |
| `CONTEXT_LINE` | chéo chấm mịn | đường gợi ý hướng, không phải trigger |
| `LEVEL_CARRIED` | ngang gạch dài, chiếu sang phải | mức cũ còn giá trị (role reversal, ceiling...) |
| `MINI_LEVEL` | ngang ngắn | đáy/đỉnh nhỏ trong zigzag |
| `SQUEEZE` | ellipse gạch | tường 2 phía siết lại — pressure đang nén |
| `LABEL_TF` | chữ `T` hoặc `F` nhỏ tại bar | `T` = bar đó poke qua mép (test), `F` = poke fail/đảo |
| `BRACKET` | đường span + chữ `M`/`W`/`Mm`/`Ww`/`SHS` giữa | đánh dấu hình thái pattern trên một nhịp |
| `FALSE_EXT` | tick nhỏ | wick vượt quá mép rồi bị kéo lại (false extension) |
| `STAND_ASIDE` | dải cảnh báo mỏng | vùng chop — Volman bảo đứng ngoài |
| `EMA25` | đường chấm xám | chỉ báo DUY NHẤT — thước đo độ dốc/áp lực |

**Không vẽ 00/50** — những mức tròn chỉ là context, không phải structure.

### Đọc chart kiểu Volman (nói đơn giản)

1. Chart M5 chỉ có nến + EMA25 + vài object — mắt phải nhìn thấy
   ngay, không phân tích. Nếu phải nghĩ >2 giây thì đó là chop.
2. Cấu trúc = **rào** (mé p box/range/level). Giá chạy giữa các rào;
   setup nổ ra khi giá ép vào một rào và lực đẩy gãy.
3. `T` tại mép = giá thử rào mà bị bật lại → rào còn cứng.
   `F` / `FALSE_EXT` = vượt mép giả → bẫy.
4. `SQUEEZE` = hai phía siết vào nhau — chuẩn bị có quyết định; không
   đoán hướng trước.
5. `BOX`/`CONTEXT_RANGE` = chỗ giá mắc kẹt — phần lớn thời gian đứng
   ngoài, chỉ canh mép.
6. Object thưa là **cố ý**: spec giới hạn ≤5 object (cap 8). Ít nét =
   ít nhiễu — đúng tinh thần chart sạch của Volman.

### Inputs của viewer

`InpFile` (đường dẫn trong `MQL5\Files` — loader tự thử `Common\Files`
trước), `InpTheme` (0 = nền tối, default; 1 = nền sáng), `InpDrawEma25`,
`InpTolPips` (nửa bề rộng dải mép BOX), `InpMaxObj`/`InpHardCap`
(ngân sách vẽ 5/8), `InpPollMs` (chu kỳ đọc lại file — sửa CSV là
chart tự vẽ lại), `InpHudY` (vị trí HUD).

## Compile

```powershell
cd "02. AlphaFactory"
.\alpha.ps1 compile "PA_Pro"        # -> PA_Pro.ex5, phải 0 errors/0 warnings
.\alpha.ps1 compile "PA_Pro_Parity" # script export cho parity
```

## Chạy EA

1. Gắn `PA_Pro` lên chart EURUSD M5.
2. Inputs quan trọng: `InpSignalOnly=true` (giữ nguyên), `InpDrawZones`,
   `InpJournal`, từng generator bật/tắt, session EU/US, giờ flat.
3. `InpSelfTest=true` → chạy 1372 vector clock + self-test incremental
   (ctx + zone, gồm pass salience SF02) rồi dừng (không trade).
4. Hook SF02 (để nguyên mặc định khi chưa có quyết định của Lead):
   `InpSalienceMode=0` (0 = strength; 1 = công thức a-priori SF02
   AUTOPSY_PLAN A3 — đã implement sẵn, gồm track pivot H4) và
   `InpArmTopK=0` (0 = tắt; >0 = giữ tối đa k zone mỗi phía theo salience).

## Parity (chứng minh EA nhìn giống Python)

Xem `mql5/parity/RUNBOOK.md`. Tóm tắt:

```bash
# Python (tự xin slot pa_slots):
python mql5/parity/export_zones.py EURUSD mql5/parity/out
# MQL5: gắn script PA_Pro_Parity lên chart EURUSD M5
#   -> MQL5\Files\PA_Pro\zones_EURUSD.csv
# So sánh:
python mql5/parity/compare_parity.py \
    mql5/parity/out/zones_EURUSD_py.csv \
    "<MT5 Files>\PA_Pro\zones_EURUSD.csv" 0.00001 --report out/diff.txt
```

Target: ≥ 99.5% bars khớp biên zone trong 0.1 pip.

## Journal

`MQL5\Files\PA_Pro\pa_journal.csv` — mỗi signal/veto một dòng, cột giống
record của `pa_fill.simulate` (`sig,side,tag,symbol,status,order_type,
fill_idx,fill,...`). Status: `SIGNAL`, `VETO_WEEKEND`, `VETO_FRIDAY`,
`VETO_SESSION`, `VETO_WARMUP`, `SPREAD`, `RISK_LOCK`, `NO_PLAN`...

## Quyết định quan trọng (xem DECISIONS.md)

- **D4 replay**: reads dùng `views_at` = replay state từ `born_idx`, còn
  pass chỉ step từ `created_idx` → engine giữ 2 track `st`/`sx`, zone mới
  backfill `sx` từ `born_idx` ngay lúc tạo. Reference: `families/sf_ctx.py`.
- `utc_min/dow` tính trên **bar close**; dow Monday=0; veto Friday theo
  corrected dow (bug R00 flatten Thursday đã loại trừ, `legacy_flats`
  hard-wired false).

## Khi nào anh cần can thiệp

- Flip `InpSignalOnly=false` — chỉ anh có quyền này.
- Setup Factory xong → thay stub trong `PA_Setups.mqh` bằng module
  survivor (subclass `CPaSetupBase`, `Detect` + `Bind`).
- Chạy parity ở bước 2 của RUNBOOK (lane không được mở terminal).
