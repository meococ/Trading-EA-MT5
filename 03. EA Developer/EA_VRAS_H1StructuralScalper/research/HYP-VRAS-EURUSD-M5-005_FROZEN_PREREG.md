# HYP-VRAS-EURUSD-M5-005 — Frozen Preregistered Hypothesis

> **STATUS: FROZEN PRE-OUTCOME**  
> ID: `HYP-VRAS-EURUSD-M5-005`  
> Symbol: `EURUSD` | Timeframe: `M5` (H1 Context) | Window: `2019.01.01 -- 2022.12.31` (2023+ sealed)

## 1. Hypothesis Thesis

Việc tinh chỉnh VRAS ở HYP-003 làm sụt giảm số lượng lệnh từ hàng ngàn xuống còn 93 lệnh (0.45 lệnh/tuần) do sử dụng quá nhiều tầng lọc bọc bên ngoài và ADX14 hysteresis M5 bị trễ làm đổi regime 6.92 lần/ngày. 

Bằng cách chuyển bộ định hướng Regime sang **Closed H1 Structure Bias (H1 EMA200 + H1 Session VWAP)** và đặt điểm vào lệnh khi M5 pullback về Session VWAP / AVWAP có tín hiệu xác nhận đà nến M5 (Path Confirmation), hệ thống sẽ:
- Triệt tiêu hoàn toàn hiện tượng Whipsaw của ADX M5.
- Khôi phục số lượng lệnh chuẩn (Cadence ≥ 2.0 – 5.0 lệnh/tuần, N ≥ 350 lệnh).
- Cải thiện tỷ lệ Thắng/Thua nhờ cơ chế Break-Even tại 1.0R (khắc phục Archetype 2 MFE Giveback).

## 2. Decision Surface & Signal Matrix

- **100% Closed Bar / Non-Repaint**: Tín hiệu được tính toán hoàn toàn tại nến 1 (`bar [1]`).
- **Trend Long**:
  - Closed H1 Bar [1] Close > H1 EMA200
  - Price M5 Bar [1] Low ≤ Session VWAP / AVWAP (Pullback) && M5 Bar [1] Close > Session VWAP / AVWAP (Reclaim)
  - M5 Bar [1] Close > M5 Bar [2] High (Path Confirmation)
- **Trend Short**:
  - Closed H1 Bar [1] Close < H1 EMA200
  - Price M5 Bar [1] High ≥ Session VWAP / AVWAP (Pullback) && M5 Bar [1] Close < Session VWAP / AVWAP (Rejection)
  - M5 Bar [1] Close < M5 Bar [2] Low (Path Confirmation)

## 3. Position Geometry & Risk Rules

- **Risk per trade**: Fixed 0.25% Account Balance.
- **Stop Loss (SL)**: Swing High/Low gần nhất trong 10 nến M5 + 1.5 pips buffer (tối thiểu 4.0 pips, tối đa 15.0 pips).
- **Take Profit (TP)**: Fixed 1.5 × SL_distance (R:R = 1:1.5).
- **Break-Even**: Khi giá đạt `+1.0R`, dời SL về `Entry Price + 0.5 pip`.
- **Max Hold**: 24 nến M5 (2 giờ).

## 4. Frozen Gates (Pass/Fail Criteria)

- **Total Trades (N)**: ≥ 350 trades (2019-2022).
- **Cadence**: 2.0 – 5.0 trades / elapsed week.
- **Profit Factor (PF)**: ≥ 1.30 diagnostic (≥ 1.25 under 1.5x cost stress).
- **Expectancy**: > +0.05R per trade.
- **Max Drawdown**: ≤ 6.0%.
