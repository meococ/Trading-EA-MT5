# MR System — Phase 0 + Dashboard Monitor (spec v3)

Hệ thống Regime-Gated Mean-Reversion XAUUSD/EURUSD (H1) theo `Hybrid_Regime_MR_XAUUSD_Forex_v3_EA_Ready_Spec.md`.
Phase 0: data pipeline + cost model + gates + dashboard monitor-mode. **CHƯA đặt lệnh.**

## Cài đặt (Windows, Python 3.10+)
```
cd mr_system
pip install -r requirements.txt
```

## Chạy dashboard
```
streamlit run dashboard/app.py
```
- Mặc định mode **demo** (data giả lập — chạy được ngay, không cần MT5).
- Mode **mt5**: mở terminal MT5 (đăng nhập broker demo), chọn "mt5" ở sidebar.
  Yêu cầu: Windows + `pip install MetaTrader5` + symbol đúng tên broker (có broker
  dùng hậu tố, vd `XAUUSD.a` — sửa trong sidebar/code nếu cần).

## Chạy tests
```
python validation/test_indicators.py    # 11 sanity tests (half-life OU, sizing, session...)
```

## Cấu trúc
```
config/costs.yml        # cost model §9 (spread/slippage/swap p50-p90, triple day)
config/params.yml       # parameter registry §13 (default + grid + nhãn nguồn gốc)
data/loader.py          # MT5 loader (closed-bars only) + demo generator
features/indicators.py  # ATR/ADX Wilder (khớp MT5), detrend, z, half-life, ATR pctile
features/gates.py       # 8 gates §4 → bảng đèn
core/signal.py          # signal plan §5 (monitor): SL/TP/size/time-stop/swap ước tính
dashboard/app.py        # Streamlit: chart + bands, đèn gates, signal plan, auto-refresh
validation/             # tests + leakage checklist
```

## Việc còn lại của Phase 0 (theo roadmap §12)
1. Nối economic calendar (CSV export từ ForexFactory/Investing) → thay news gate stub.
2. Server-time → UTC converter có bảng DST (input: broker offset winter/summer).
3. Parity check indicators: export CSV iATR/iADX từ MT5 → script so sánh (checklist).
4. Lưu bars về Parquet để backtest Phase 1 không phụ thuộc terminal.

## Nhắc lại kỷ luật (spec §10)
Dashboard đẹp không tạo ra expectancy. Thứ tự vẫn là: Phase 1 baseline EURUSD →
Gates 0-4 → forward demo. Fail Gate 1 ở p75 costs → dừng dự án MR, giữ infrastructure.
