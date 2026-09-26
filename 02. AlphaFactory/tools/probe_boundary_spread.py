# Real tick-level spread at the day-boundary (00:00 server = 21:00 UTC DST)
# vs liquid control hour. ~4 recent weeks, all inside US-DST window.
import sys, datetime as dt, collections
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from factory_paths import mt5_initialize_kwargs  # noqa: E402
import MetaTrader5 as mt5  # noqa: E402

SYMS = ["GBPUSD", "AUDUSD", "NZDUSD", "EURUSD", "USDCAD", "USDCHF", "USDJPY"]
PIPS = {s: (1e-2 if s.endswith("JPY") else 1e-4) for s in SYMS}
# UTC windows (server = UTC+3 in DST): entry 00:00-00:05 srv = 21:00-21:05 UTC
WINS_UTC = {"entry_0005": (21 * 60, 21 * 60 + 5),
            "hold_0030": (21 * 60 + 5, 21 * 60 + 30),
            "hold_0200": (21 * 60 + 30, 24 * 60),
            "ctrl_1500srv": (12 * 60, 13 * 60)}   # 15:00 server = 12:00 UTC


def main():
    kw = mt5_initialize_kwargs()
    assert mt5.initialize(**kw), mt5.last_error()
    try:
        for sym in SYMS:
            mt5.symbol_select(sym, True)
            pip = PIPS[sym]
            spreads = collections.defaultdict(list)
            day0 = dt.datetime(2026, 9, 11)
            for wback in range(0, 28):
                base = day0 - dt.timedelta(days=wback)
                for lab, (m0, m1) in WINS_UTC.items():
                    a = base + dt.timedelta(minutes=m0)
                    b = base + dt.timedelta(minutes=m1)
                    if a >= b:
                        continue
                    tk = mt5.copy_ticks_range(sym, a, b, mt5.COPY_TICKS_INFO)
                    if tk is None or len(tk) == 0:
                        continue
                    step = max(1, len(tk) // 300)
                    for x in tk[::step]:
                        bid, ask = float(x[1]), float(x[2])
                        if ask <= 0 or bid <= 0:
                            continue
                        sp = (ask - bid) / pip
                        if 0 < sp < 60:
                            spreads[lab].append(sp)
            print(f"--- {sym} ---")
            for lab in WINS_UTC:
                v = sorted(spreads[lab])
                if v:
                    print(f"  {lab:<13} n={len(v):>5} p25={v[len(v)//4]:.2f} "
                          f"p50={v[len(v)//2]:.2f} p90={v[int(len(v)*0.9)]:.2f}p")
    finally:
        mt5.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
