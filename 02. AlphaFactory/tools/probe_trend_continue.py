"""Stage-0: with-trend CONTINUATION at session opens (mirror of killed fade family).

Doctrine note: entry is booked at NEXT-BAR OPEN (executable semantics), not the
trigger-bar close — the bar-close convention was the probe-vs-governed gap root
cause in BEDGE. With-trend entries get favorable-or-neutral drift between close
and next open, so open-of-next-bar is the honest probe book price.

Levels (all strict past-only — no same-day-future bars):
  L1: prior session FULL extreme (wick)
  L2: prior session LAST-HOUR extreme (wick)
Pierce definition (separate legs):
  W: wick beyond level
  C: CLOSE beyond level
Trigger window: first 2h of session (24 M5 bars). Entry = open of bar AFTER
the pierce bar (k+1 open). Exit = session-end close.
Legs: CONT = enter WITH pierce direction; FADE = enter AGAINST (mirror check).
Split-half: |t|>2.8 in BOTH halves + same sign => anomaly candidate.

Sessions GMT: ASIA 00:00 (prior=prev-day NY 12:00-20:00, exit 07:00),
LDN 07:00 (prior=same-day ASIA 00:00-07:00, exit 16:00),
NY 12:00 (prior=same-day LDN 07:00-12:00, exit 20:00).
"""
import sys, math, datetime as dt, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from factory_paths import mt5_initialize_kwargs  # noqa: E402

import MetaTrader5 as mt5  # noqa: E402

SYMS = ["GBPUSD", "EURUSD", "USDJPY", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF"]
PIPS = {s: (1e-2 if s.endswith("JPY") else 1e-4) for s in SYMS}
COST = 3.6   # conservative RT pips on MQ-Demo
WANT_FROM = dt.datetime(2022, 1, 1).timestamp()
END = dt.datetime(2026, 9, 11)

# (name, open_min, close_min, prior_start_min, prior_end_min, prior_is_prev_day)
BOUNDS = [
    ("ASIA", 0, 420, 720, 1200, True),
    ("LDN", 420, 960, 0, 420, False),
    ("NY", 720, 1200, 420, 720, False),
]


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


def gmt_min(ts):
    return (ts % 86400) // 60


def day_key(ts):
    return ts // 86400


def stats(rets):
    if len(rets) < 15:
        return None
    m = sum(rets) / len(rets)
    sd = math.sqrt(sum((x - m) ** 2 for x in rets) / len(rets))
    t = m / (sd / math.sqrt(len(rets))) if sd > 0 else 0
    return m, t, len(rets)


def main():
    kw = mt5_initialize_kwargs()
    if not mt5.initialize(**kw):
        print("attach failed", mt5.last_error()); return 1
    try:
        for sym in SYMS:
            data = get_bars(sym)
            if not data:
                print(f"\n##### {sym} ##### NO DATA"); continue
            times = sorted(data)
            pip = PIPS[sym]
            days = (times[-1] - times[0]) / 86400.0
            print(f"\n##### {sym} ##### bars={len(times)} days={days:.0f}")
            for name, om, cm, pw0, pw1, prev in BOUNDS:
                # legs keyed (level, pierce_mode): lists of signed pips, CONT dir
                cont = {k: [] for k in ("L1W", "L1C", "L2W", "L2C")}
                tser = []  # event times for split-half
                i = 30
                while i < len(times) - 30:
                    t = times[i]
                    if gmt_min(t) != om:
                        i += 1; continue
                    dk = day_key(t)
                    pdk = dk - 1 if prev else dk
                    prior = [x for x in times
                             if day_key(x) == pdk and pw0 <= gmt_min(x) < pw1]
                    if len(prior) < 10:
                        i += 1; continue
                    # L1 full-session extreme; L2 last-hour of prior window
                    ph1 = max(data[x][1] for x in prior)
                    pl1 = min(data[x][2] for x in prior)
                    ph2 = max(data[x][1] for x in prior if gmt_min(x) >= pw1 - 60)
                    pl2 = min(data[x][2] for x in prior if gmt_min(x) >= pw1 - 60)
                    # session scan: first 2h (24 bars); track FIRST pierce per leg
                    hit = {k: 0 for k in cont}
                    entry_i = None
                    for k in range(0, 24):
                        bi = i + k
                        if bi + 1 >= len(times) or times[bi] - t != k * 300:
                            break
                        b = data[times[bi]]
                        for key, ph, pl in (("L1W", ph1, pl1), ("L1C", ph1, pl1),
                                            ("L2W", ph2, pl2), ("L2C", ph2, pl2)):
                            if hit[key]:
                                continue
                            if key.endswith("W"):
                                if b[1] > ph: hit[key] = +1   # pierce up
                                elif b[2] < pl: hit[key] = -1
                            else:
                                if b[3] > ph: hit[key] = +1
                                elif b[3] < pl: hit[key] = -1
                        if any(hit.values()) and entry_i is None:
                            entry_i = bi + 1  # next-bar open
                    if entry_i is None:
                        i += 24; continue
                    entry_px = data[times[entry_i]][0]  # OPEN
                    # exit: session-end close
                    j = entry_i
                    while j < len(times) and gmt_min(times[j]) < cm:
                        j += 1
                    if j <= entry_i:
                        i += 24; continue
                    exit_px = data[times[j - 1]][3]
                    for key in cont:
                        if hit[key]:
                            cont[key].append(hit[key] * (exit_px - entry_px) / pip)
                            tser.append((key, times[entry_i]))
                    i += 24
                for key in cont:
                    r = cont[key]
                    s = stats(r)
                    if not s:
                        print(f"  {name}-{key}-CONT: n={len(r)} too few"); continue
                    m, t, n = s
                    wk = n / (days / 7.0)
                    # split-half same-sign check
                    h = n // 2
                    s1, s2 = stats(r[:h]), stats(r[h:])
                    sh = (f"{s1[1]:+.1f}/{s2[1]:+.1f}" if s1 and s2 else "n/a")
                    flag = " <== CANDIDATE" if (s1 and s2 and abs(s1[1]) > 2.8
                                              and abs(s2[1]) > 2.8
                                              and (s1[0] > 0) == (s2[0] > 0)
                                              and m > COST) else ""
                    print(f"  {name}-{key}-CONT: n={n} {wk:.1f}/wk mean={m:+.2f}p "
                          f"t={t:+.2f} half_t={sh} net={m-COST:+.2f}p{flag}")
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
