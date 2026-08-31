# EA_VRAS_H1StructuralScalper

Package phát triển EA theo Hypothesis **`HYP-VRAS-H1STRUCT-EURUSD-M5-005`**.

## Cải tiến cốt lõi so với HYP-003 / HYP-004

1. **Thay thế ADX M5 Hysteresis bằng Closed H1 Structure Bias**: Sử dụng H1 Close vs H1 EMA200 và H1 Session VWAP để định hướng Trend/Range thay cho ADX M5 bị whipsaw (6.92 lần/ngày).
2. **Khôi phục Cadence (2.0 – 5.0 lệnh/tuần)**: Tháo bỏ bộ lọc G11 cost-distance cứng nhắc và bọc lọc entry dời dạc, thay bằng H1 Structure Reclaim + M5 VWAP Pullback.
3. **Hình thái SL/TP mới (Structural Geometry & Break-Even)**: SL được đặt theo mốc Swing High/Low gần nhất (+1.5 pips buffer), TP = 1.5R. Tự động dời SL về Break-Even khi đạt 1.0R.
