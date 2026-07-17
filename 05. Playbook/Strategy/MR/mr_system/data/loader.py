"""
loader.py — nguồn dữ liệu bar ĐÃ ĐÓNG (leakage-safe).
- source="mt5":  MetaTrader5 package (Windows, terminal MT5 đang mở).
                 copy_rates_from_pos(..., start_pos=1, ...) — pos=1 để BỎ bar
                 đang chạy (bar 0 = forming bar). Đây là điểm chống look-ahead.
- source="demo": synthetic data (random walk + đoạn OU mean-revert trộn vào)
                 để chạy dashboard/test không cần MT5.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

H1_PER_DAY = 24


def load_bars(symbol: str, timeframe: str = "H1", n: int = 1500,
              source: str = "demo", seed: int | None = None) -> pd.DataFrame:
    if source == "mt5":
        return _load_mt5(symbol, timeframe, n)
    return _demo_series(symbol, timeframe, n, seed)


def get_live_info(symbol: str, source: str = "demo") -> dict:
    """Spread hiện tại + giá bid/ask cho spread guard & dashboard."""
    if source == "mt5":
        import MetaTrader5 as mt5
        info = mt5.symbol_info(symbol)
        tick = mt5.symbol_info_tick(symbol)
        if info is None or tick is None:
            raise RuntimeError(f"MT5: không đọc được {symbol}")
        return {"bid": tick.bid, "ask": tick.ask,
                "spread_price": tick.ask - tick.bid,
                "swap_long": info.swap_long, "swap_short": info.swap_short,
                "contract_size": info.trade_contract_size,
                "stops_level_points": info.trade_stops_level}
    return {"bid": np.nan, "ask": np.nan, "spread_price": 0.0,
            "swap_long": np.nan, "swap_short": np.nan,
            "contract_size": np.nan, "stops_level_points": 0}


# ----------------------------------------------------------------------
def _load_mt5(symbol: str, timeframe: str, n: int) -> pd.DataFrame:
    import MetaTrader5 as mt5
    TF = {"H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1}
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize() fail: {mt5.last_error()}")
    rates = mt5.copy_rates_from_pos(symbol, TF[timeframe], 1, n)  # pos=1: bỏ bar đang chạy
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"MT5: không có data {symbol} {timeframe}: {mt5.last_error()}")
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)  # LƯU Ý: đây là GIỜ SERVER
    # Chuyển server time -> UTC: cần offset broker (GMT+2/+3 theo DST) từ config khi
    # dùng session filter. Monitor mode: hiển thị cả hai; EA thật phải convert chuẩn.
    df = df.rename(columns={"tick_volume": "volume"})
    return df[["time", "open", "high", "low", "close", "volume", "spread"]]


def _demo_series(symbol: str, timeframe: str, n: int, seed: int | None) -> pd.DataFrame:
    """Random walk + 3 đoạn OU xen kẽ (để dashboard có lúc gates pass) + vol regime."""
    rng = np.random.default_rng(seed if seed is not None else (42 if symbol == "EURUSD" else 7))
    if symbol == "XAUUSD":
        p0, vol = 4000.0, 4.0     # ~$4/oz mỗi H1 bar
    else:
        p0, vol = 1.09, 0.0011    # ~11 pips mỗi H1 bar
    x = np.zeros(n)
    x[0] = p0
    regime = np.zeros(n, dtype=int)
    # 3 đoạn mean-revert: mỗi đoạn ~15% chuỗi
    seg = [(int(n*0.20), int(n*0.35)), (int(n*0.55), int(n*0.70)), (int(n*0.85), int(n*0.97))]
    theta = 0.08                   # HL ~ ln2/0.08 ~ 8.7 bars — nằm trong HL gate
    for i in range(1, n):
        in_mr = any(a <= i < b for a, b in seg)
        regime[i] = 1 if in_mr else 0
        v = vol * (0.7 if in_mr else 1.0) * (1.5 if (i % 300) > 260 else 1.0)
        if in_mr:
            anchor = x[max(0, i - 100):i].mean()
            x[i] = x[i-1] + theta * (anchor - x[i-1]) + rng.normal(0, v)
        else:
            x[i] = x[i-1] + rng.normal(0, v) + (0.15 * v if (i // 400) % 2 == 0 else -0.1 * v)
    close = pd.Series(x)
    h1 = pd.Timedelta(hours=1) if timeframe == "H1" else pd.Timedelta(hours=4)
    t_end = pd.Timestamp.utcnow().floor("h")
    times = pd.date_range(end=t_end, periods=n, freq=h1)
    rr = pd.Series(rng.uniform(0.2, 1.0, n)) * vol
    df = pd.DataFrame({
        "time": times,
        "open": close.shift(1).fillna(p0),
        "close": close,
        "high": np.maximum(close, close.shift(1).fillna(p0)) + rr * 0.5,
        "low": np.minimum(close, close.shift(1).fillna(p0)) - rr * 0.5,
        "volume": rng.integers(500, 5000, n),
        "spread": 0,
    })
    df.attrs["demo_regime"] = regime.tolist()
    return df
