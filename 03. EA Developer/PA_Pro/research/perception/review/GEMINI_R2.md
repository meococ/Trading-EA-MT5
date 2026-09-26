# GEMINI_R2 — G-REVIEW round 2 (partial), 23/09 11:55–12:23Z

- **Set under review:** `s1b` (S1-b, box age cap 75 bars) on the 12 fixed panels (`review/sets/s1b`, copied to `_scratch/gr2/s1b`).
- **Tooling log (R81 §81.2 addendum):**
  - **3.8 Flash + prompt P1** (the short R1 prompt, "biểu đồ giá ... đầu tư"): refused 3 of 3.
    - app/1b65be59bee400ab
    - app/0d1262884bbb0b47
    - one run in a parallel tab that did not submit.
  - **3.8 Flash + neutral prompt P2** ("đồ thị chuỗi thời gian", no price or investment words): 1 answered (app/691fbdb65827c770), and 1 started answering and was then replaced by a refusal (app/5ddf9a77299c8fbf).
  - **3.1 Pro + P2:** answered (app/62f770b1dc4f9c51, about 5 min). `get_page_text` misses Pro's rendered answer; it was read via DOM `model-response` innerText.
  - Parallel tabs do not submit reliably. One chat at a time, click the send button (Enter does not submit in this layout), and open the + menu with one click plus a 2 s wait.

## Verdicts (verbatim, trimmed)

**Batch s1b-A — Flash P2** (9.10c, 9.11b, 9.17b, 9.25a), app/691fbdb65827c770:

| panel | verdict | findings |
|---|---|---|
| 9.10c | Lỗi-nặng | **NEW:** "Hộp chữ nhật liền nét lớn (09:30 – 15:45) … bao trọn toàn bộ cấu trúc sóng, bị đâm xuyên liên tục bởi đợt bứt phá tăng … phải hủy/cắt ngắn hộp khi nến breakout thoát ra ngoài." Plus the R1 errors: diagonals cut bodies; dashed levels pierced. |
| 9.11b | Lỗi | Dashed box 07:45 – 14:00 too wide; diagonals cut the recovery; old lines at lower left. |
| 9.17b | Lỗi-nặng | "Hộp liền kéo dài tới cuối dù giá đã bứt phá tăng >70 pip từ 08:30 … Đóng hộp tại nến đóng cửa vượt biên trên." |
| 9.25a | Lỗi-nặng | Level 1.3225 through the crash; floating diagonals; duplicate dashed levels. |

**Batch s1b-B — Pro P2** (9.2b, 9.33c, 9.36c, 9.40a), app/62f770b1dc4f9c51:

| panel | verdict | findings |
|---|---|---|
| 9.2b | Lỗi nặng | Dashed box at the top far from price; diagonal 10:00 – 11:30 cuts bodies. |
| 9.33c | Lỗi nặng | **NEW:** "Hộp lớn (từ 11:15 đến cuối): Bao trọn cả một xu hướng tăng trưởng kéo dài … không được bọc cả một đoạn trend mạnh." Dashed level ~1.3060 crossed back and forth. |
| 9.36c | Lỗi nặng | **NEW:** "Hộp lớn phía trên (12:00 đến cuối): bọc luôn cả đoạn sập giá mạnh lúc 13:30." Too many objects (3 boxes, 2 dashed, 4 diagonals, 1 ellipse). |
| 9.40a | Lỗi nặng (R1: **OK**) | **NEW:** "Hộp lớn (04:45 đến cuối, 1.3200 – 1.3225): Bao trọn vùng sideway kéo dài và cả đoạn sóng bứt phá tăng rất mạnh lúc 09:00 … Thu hẹp … chỉ bọc vùng đi ngang từ 05:00 đến trước nhịp breakout 08:45." |

Pro's closing note: "Thuật toán hiện tại đang rất yếu trong việc phân biệt giữa vùng sideway (có thể dùng hộp) và vùng trend (tuyệt đối không bọc hộp) … ngừng vẽ hộp khi có biến động giá vượt ngưỡng (breakout)."

Batch s1b-C (9.42b, 9.48b, 9.52a, 9.57b) was not run; see the reading below.

## Lead reading (paired, fixed/remain/new, R80 §80.5)

**S1-b introduces a new fatal error on 4 of 8 panels** (9.10c, 9.33c, 9.36c, 9.40a). None of these was reported for c3 in R1.
- **Mechanism.** Under C-3 these long-lived boxes start before the visible window. Their left edge is off-screen, so they show only as two horizontal lines. The 75-bar age cap moves the left edge inside the window, and the stale box becomes a visible rectangle that swallows the trend or the breakout.
- **Result:** 9.40a goes from OK to fatal.
- **Verdict:** S1-b **fails G-REVIEW** (R80 §80.3a). Its M1 pass does not save it. The remaining 4 panels would not change this, so batch C was not run to save reviewer calls.

**What Gemini asks for, the same way in both rounds and both models:** a box must **end at the breakout**. That means box lifetime at the break, not the age cap and not the left edge.
