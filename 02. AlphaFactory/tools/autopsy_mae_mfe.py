"""Post-kill autopsy: WHERE did the expectancy leak?

For every executed trade in a governed run's lifecycle CSV, reconstruct the
M5 path between entry and exit and measure:
  MAE  - max adverse excursion (worst drawdown during the trade, pips)
  MFE  - max favorable excursion (best reachable profit, pips)
  captured = realized / MFE  (how much of the available move the exit took)
  tMFE - time to MFE (was the move early and given back?)

Verdict map:
  MFE median >> 0 and captured << 1  -> exit design leaks value (trail/partial)
  MFE median ~ 0                    -> entry premise dead (price never moves for us)
  MAE median >> stop               -> stop placement wrong
This is autopsy on EXECUTED data - legitimate design input, not outcome-tuning.
"""
import sys, csv, math, datetime as dt, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from factory_paths import mt5_initialize_kwargs  # noqa: E402

import MetaTrader5 as mt5  # noqa: E402

RUN = (r"D:\Meta 5\Trading-EA-MT5\02. AlphaFactory\runs\EA_SessionMomentum"
       r"\20260918_115433\logs\USDJPY_LifecycleTrades_HYP-SMOM-JPY-M5-001_189036328.csv")
SYM, PIP = "USDJPY", 1e-2
WANT_FROM = dt.datetime(1999, 1, 1).timestamp()
END = dt.datetime(2026, 9, 11)


def get_bars():
    mt5.symbol_select(SYM, True)
    out = {}
    anchor = END
    for _ in range(120):
        b = mt5.copy_rates_from(SYM, mt5.TIMEFRAME_M5, anchor, 50000)
        if b is None or len(b) == 0:
            break
        for x in b:
            out[int(x[0])] = (float(x[1]), float(x[2]), float(x[3]), float(x[4]))
        anchor = dt.datetime.utcfromtimestamp(int(b[0][0]))
        if int(b[0][0]) <= WANT_FROM:
            break
        time.sleep(0.2)
    return out


def parse_trades():
    rows = list(csv.DictReader(open(RUN, encoding='utf-8-sig')))
    opens, trades = {}, []
    for r in rows:
        if r['action'] == 'OPEN':
            opens[r['position_id']] = (r['event_time'], float(r['price']),
                                       1 if r['order_type'] == 'BUY' else -1)
        elif r['action'] == 'CLOSE' and r['position_id'] in opens:
            t0, px0, d = opens[r['position_id']]
            trades.append({'pos': r['position_id'], 't0': t0, 't1': r['event_time'],
                           'dir': d, 'px0': px0, 'px1': float(r['price']),
                           'net': float(r['deal_net'] or 0)})
    return trades


def epoch(s):
    # lifecycle event_time is server-time seconds; parse as naive UTC to match
    # mt5 bar.time keys (machine local tz would shift the epoch by hours).
    return int(dt.datetime.strptime(s, '%Y.%m.%d %H:%M:%S')
               .replace(tzinfo=dt.timezone.utc).timestamp())


def main():
    trades = parse_trades()
    print(f"trades={len(trades)}")
    if not mt5.initialize(**mt5_initialize_kwargs()):
        print("attach failed"); return 1
    try:
        bars = get_bars()
        print(f"bars={len(bars)}")
        ts = sorted(bars)
        stats = {'LDN': [], 'NY': []}
        for tr in trades:
            e0, e1 = epoch(tr['t0']), epoch(tr['t1'])
            gmt0 = (e0 % 86400) // 60
            # server->GMT -2h; LDN entries 07-09 GMT, NY 12-14 GMT
            g = (gmt0 - 120) % 1440
            leg = 'LDN' if 420 <= g < 600 else 'NY'
            # proper MAE/MFE over the path; skip trades outside loaded coverage
            if not any(bars.get(x) for x in range(e0, e1 + 1, 300)):
                continue
            mae = mfe = 0.0
            tmfe = 0
            for x in range(e0, e1 + 1, 300):
                b = bars.get(x)
                if not b:
                    continue
                if tr['dir'] > 0:
                    fav = (b[2] - tr['px0']) / PIP
                    adv = (b[1] - tr['px0']) / PIP
                else:
                    fav = (tr['px0'] - b[1]) / PIP
                    adv = (tr['px0'] - b[2]) / PIP
                if fav > mfe:
                    mfe, tmfe = fav, x - e0
                if adv < mae:
                    mae = adv
            realized = (tr['px1'] - tr['px0']) / PIP * tr['dir']
            stats[leg].append((mae, mfe, realized, tmfe / 3600.0, tr['net']))
        for leg, rows in stats.items():
            if not rows:
                continue
            n = len(rows)
            med = lambda v: sorted(v)[len(v) // 2]
            maes = [r[0] for r in rows]
            mfes = [r[1] for r in rows]
            reals = [r[2] for r in rows]
            cap = [r[2] / r[1] for r in rows if r[1] > 1]
            wins = [r for r in rows if r[2] > 0]
            losses = [r for r in rows if r[2] <= 0]
            print(f"\n== {leg} n={n} ==")
            print(f"  MAE p25/p50/p75: {sorted(maes)[n//4]:.1f} / {med(maes):.1f} / {sorted(maes)[3*n//4]:.1f} p")
            print(f"  MFE p25/p50/p75: {sorted(mfes)[n//4]:.1f} / {med(mfes):.1f} / {sorted(mfes)[3*n//4]:.1f} p")
            print(f"  realized mean {sum(reals)/n:+.2f}p | median MFE-capture {med(cap) if cap else 0:.2f}")
            print(f"  winners n={len(wins)}: MFE med {med([r[1] for r in wins]) if wins else 0:.1f}p "
                  f"tMFE med {med([r[3] for r in wins]) if wins else 0:.1f}h")
            print(f"  losers  n={len(losses)}: MAE med {med([r[0] for r in losses]) if losses else 0:.1f}p "
                  f"MFE med {med([r[1] for r in losses]) if losses else 0:.1f}p")
            # counterfactual: what if we exited at MFE*0.5 (trail 50% giveback)?
            for frac in (0.4, 0.5, 0.6):
                cf = sum(min(r[2], r[1] * frac) for r in rows) / n
                print(f"  counterfactual trail@{frac:.0%}-of-MFE: mean {cf:+.2f}p/trade")
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
