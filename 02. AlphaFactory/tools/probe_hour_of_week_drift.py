# Hour-of-week signed-drift scan — the unmeasured cadence question.
# For every hour-of-week cell x symbol: signed E[close-open +1h / +2h].
# A calendar sleeve trading every qualifying cell/day could reach 10-30/wk.
# Controls: split-half sign, cross-asset replication, multiple-testing aware.
import sys, math, datetime as dt, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from factory_paths import mt5_initialize_kwargs  # noqa: E402
import MetaTrader5 as mt5  # noqa: E402

SYMS = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
PIPS = {s: (1e-2 if s.endswith("JPY") else 1e-4) for s in SYMS}
WANT_FROM = dt.datetime(2022, 1, 1).timestamp()
END = dt.datetime(2026, 9, 11)


def get_bars(sym):
    mt5.symbol_select(sym, True)
    out = {}
    anchor = END
    for _ in range(30):
        b = mt5.copy_rates_from(sym, mt5.TIMEFRAME_M5, anchor, 30000)
        if b is None or len(b) == 0:
            break
        for x in b:
            out[int(x[0])] = (float(x[1]), float(x[2]), float(x[3]), float(x[4]))
        anchor = dt.datetime.utcfromtimestamp(int(b[0][0]))
        if int(b[0][0]) <= WANT_FROM:
            break
        time.sleep(0.3)
    return out or None


def how(ts):
    # hour-of-week in raw server-time terms (consistent with probes)
    d = (ts // 86400 + 4) % 7            # 0=Sun..6=Sat per epoch mapping
    return int(d * 24 + (ts % 86400) // 3600)


def stats(v):
    n = len(v)
    if n < 30:
        return None
    m = sum(v) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / n)
    return m, (m / (sd / math.sqrt(n)) if sd > 0 else 0.0), n


def main():
    kw = mt5_initialize_kwargs()
    if not mt5.initialize(**kw):
        print("attach failed", mt5.last_error()); return 1
    try:
        cell_data = {}   # (sym, how) -> list of (ret, ts)
        for sym in SYMS:
            data = get_bars(sym)
            if not data:
                continue
            times = sorted(data)
            pip = PIPS[sym]
            for i in range(1, len(times) - 13):
                t = times[i]
                if times[i + 12] - t > 3900:   # gap guard: need contiguous hour
                    continue
                r = (data[times[i + 12]][3] - data[t][0]) / pip
                cell_data.setdefault((sym, how(t)), []).append((r, t))
            print(f"{sym} done")

        # evaluate: per cell per symbol -> mean/t + halves; then cross-asset
        results = []
        for hw in range(168):
            row = []
            for sym in SYMS:
                v = cell_data.get((sym, hw), [])
                if len(v) < 60:
                    row.append(None); continue
                vals = [x[0] for x in v]
                ts_l = [x[1] for x in v]
                mid = ts_l[len(ts_l) // 2]
                s1 = stats([x for x, t in zip(vals, ts_l) if t <= mid])
                s2 = stats([x for x, t in zip(vals, ts_l) if t > mid])
                s = stats(vals)
                row.append((s, s1, s2))
            results.append((hw, row))

        print("\n=== CELLS: |mean|>1.0p AND |t|>2.5 AND halves same-sign AND >=4/7 sym same-sign ===")
        hits = []
        for hw, row in results:
            for si, sym in enumerate(SYMS):
                e = row[si]
                if not e or not e[0] or not e[1] or not e[2]:
                    continue
                s, s1, s2 = e
                if abs(s[1]) < 2.5 or abs(s[0]) < 1.0:
                    continue
                if s1[0] * s2[0] <= 0:
                    continue
                # cross-asset same-sign count at this hour
                same = sum(1 for r in row if r and r[0] and r[0][0] * s[0] > 0)
                if same < 4:
                    continue
                hits.append((hw, sym, s[0], s[1], same))
        hits.sort(key=lambda x: -abs(x[3]))
        for hw, sym, m, t, same in hits[:40]:
            dow = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][hw // 24]
            print(f"  {dow} {hw % 24:02d}h {sym:<7} mean={m:+6.2f}p t={t:+5.2f} sym_same_sign={same}/7")
        print(f"\ntotal qualifying (sym,cell): {len(hits)}")
    finally:
        mt5.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
