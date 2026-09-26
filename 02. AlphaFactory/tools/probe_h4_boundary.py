"""Stage-0 closing probe: boundary momentum at WIDE geometry (H4/D1).

Last governed-untested class. M5 session-boundary mechanisms are all dead
(22 kills); SMOM proved wide session-holds reach breakeven - so push the
geometry further where cost drag is ~3% of risk instead of ~45%.

Legs (all strict past-only, closed-bar, entry at next-bar OPEN):
  H4C: H4 bar CLOSES beyond prior-session extreme (ASIA 00-07 / LDN 07-16 GMT
       full-session H4-envelope) -> enter WITH direction at next H4 open,
       exit after 2 H4 bars (8h) or session end.
  D1W: D1 week-open drift - Monday D1 open enters in direction of prior
       week's last-2-D1 close move, exit Wednesday D1 close.
  H4S: H4 session momentum - first H4 bar of NY session (12:00-16:00 GMT)
       closing in direction of prior LDN H4 envelope pierce, hold 3 bars.

Symbols: 7 FX majors. Window: verified local M5-derived H4/D1 (chunked
copy_rates_from). Report: n, /wk, mean, t, split-half t, net of 3.6p cost.
"""
import sys, math, datetime as dt, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from factory_paths import mt5_initialize_kwargs  # noqa: E402

import MetaTrader5 as mt5  # noqa: E402

SYMS = ["GBPUSD", "EURUSD", "USDJPY", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF"]
PIPS = {s: (1e-2 if s.endswith("JPY") else 1e-4) for s in SYMS}
COST = 3.6
WANT_FROM = dt.datetime(2016, 1, 1).timestamp()
END = dt.datetime(2026, 9, 11)


def get_bars(sym, tf):
    mt5.symbol_select(sym, True)
    out = {}
    anchor = END
    for _ in range(40):
        b = mt5.copy_rates_from(sym, tf, anchor, 30000)
        if b is None or len(b) == 0:
            break
        for x in b:
            out[int(x[0])] = (float(x[1]), float(x[2]), float(x[3]), float(x[4]))
        anchor = dt.datetime.utcfromtimestamp(int(b[0][0]))
        if int(b[0][0]) <= WANT_FROM:
            break
        time.sleep(0.3)
    return out or None


def gmt_min(ts):
    return (ts % 86400) // 60


def day_key(ts):
    return ts // 86400


def week_key(ts):
    # Monday=0 of the GMT week (epoch week starts Thursday 1970-01-01)
    return (ts - 3 * 86400) // (7 * 86400)


def stats(rets):
    if len(rets) < 15:
        return None
    m = sum(rets) / len(rets)
    sd = math.sqrt(sum((x - m) ** 2 for x in rets) / len(rets))
    t = m / (sd / math.sqrt(len(rets))) if sd > 0 else 0
    return m, t, len(rets)


def rep(tag, rets, days):
    s = stats(rets)
    if not s:
        print(f"  {tag}: n={len(rets)} too few"); return
    m, t, n = s
    h = n // 2
    s1, s2 = stats(rets[:h]), stats(rets[h:])
    wk = n / (days / 7.0)
    flag = ""
    if (s1 and s2 and s1[1] > 2.8 and s2[1] > 2.8 and m > COST):
        flag = " <== CANDIDATE"
    print(f"  {tag}: n={n} {wk:.1f}/wk mean={m:+.2f}p t={t:+.2f} "
          f"halves={s1[1] if s1 else 0:+.1f}/{s2[1] if s2 else 0:+.1f} "
          f"net={m-COST:+.2f}p{flag}")


def main():
    kw = mt5_initialize_kwargs()
    if not mt5.initialize(**kw):
        print("attach failed", mt5.last_error()); return 1
    try:
        for sym in SYMS:
            pip = PIPS[sym]
            h4 = get_bars(sym, mt5.TIMEFRAME_H4)
            d1 = get_bars(sym, mt5.TIMEFRAME_D1)
            print(f"\n##### {sym} #####")
            # ---------- H4 legs ----------
            if h4:
                ts = sorted(h4)
                days = (ts[-1] - ts[0]) / 86400.0
                print(f" H4 bars={len(ts)} days={days:.0f}")
                h4c, h4s = [], []
                # session envelopes per GMT day from H4 bars:
                # ASIA = bars opening 00:00,04:00 (2 bars); LDN = 08:00,12:00 (2 bars)
                for i, t in enumerate(ts):
                    m = gmt_min(t)
                    dk = day_key(t)
                    if m == 480:  # 08:00 H4 bar: prior ASIA env = today's 00:00+04:00 bars
                        asia = [x for x in ts if day_key(x) == dk and gmt_min(x) in (0, 240)]
                        if len(asia) == 2 and i + 2 < len(ts):
                            hi = max(h4[x][1] for x in asia)
                            lo = min(h4[x][2] for x in asia)
                            b = h4[t]
                            if b[3] > hi or b[3] < lo:
                                d = 1 if b[3] > hi else -1
                                entry = h4[ts[i + 1]][0]
                                exit_px = h4[ts[min(i + 2, len(ts) - 1)]][3]
                                h4c.append(d * (exit_px - entry) / pip)
                    if m == 720:  # 12:00 H4 bar: prior LDN env = today's 08:00 bar
                        ldn = [x for x in ts if day_key(x) == dk and gmt_min(x) == 480]
                        if len(ldn) == 1 and i + 3 < len(ts):
                            hi = h4[ldn[0]][1]
                            lo = h4[ldn[0]][2]
                            b = h4[t]
                            if b[3] > hi or b[3] < lo:
                                d = 1 if b[3] > hi else -1
                                entry = h4[ts[i + 1]][0]
                                exit_px = h4[ts[i + 3]][3]
                                h4s.append(d * (exit_px - entry) / pip)
                rep("H4C asia-env close-pierce cont", h4c, days)
                rep("H4S ldn-env close-pierce cont x3bar", h4s, days)
            # ---------- D1 week-open drift ----------
            if d1:
                ts = sorted(d1)
                days = (ts[-1] - ts[0]) / 86400.0
                print(f" D1 bars={len(ts)} days={days:.0f}")
                d1w = []
                byweek = {}
                for t in ts:
                    byweek.setdefault(week_key(t), []).append(t)
                weeks = sorted(byweek)
                for w in weeks[1:]:
                    prev = byweek.get(w - 1)
                    cur = byweek[w]
                    if not prev or len(prev) < 3 or not cur:
                        continue
                    # prior week's last-2-D1 close move
                    p2 = prev[-2:]
                    if len(p2) < 2:
                        continue
                    move = d1[p2[-1]][3] - d1[p2[0]][0]
                    if abs(move) < 1e-9:
                        continue
                    d = 1 if move > 0 else -1
                    # enter at first cur-week bar open, exit at 3rd cur-week bar close
                    if len(cur) < 3:
                        continue
                    entry = d1[cur[0]][0]
                    exit_px = d1[cur[2]][3]
                    d1w.append(d * (exit_px - entry) / pip)
                rep("D1W week-open drift follow", d1w, days)
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
