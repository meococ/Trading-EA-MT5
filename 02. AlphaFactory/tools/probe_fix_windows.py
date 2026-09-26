# Fix-window reversion at CORRECT server clocks (auditor: prior probes mislabeled hours).
# WMR 4pm-London fix ~18:00 server; ECB 14:15-CET fix ~15:15 server; Tokyo 09:55-JST ~03:00 server.
# Mechanism (published): fix-window moves revert after the fix (Evans JBF'18, Krohn-Suss JF'24).
import bisect
import datetime as dt
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hcc_reader import read_hcc_year, HISTORY_DIR  # noqa: E402

SYMS = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
CLIP = 150.0
WINDOWS = {"WMR": 18 * 60, "ECB": 15 * 60 + 15, "TKY": 3 * 60}


def st(v):
    v = [x for x in v if abs(x) < CLIP]
    n = len(v)
    if n < 20:
        return None
    m = sum(v) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / n)
    w = sum(1 for x in v if x > 0) / n
    gp = sum(x for x in v if x > 0)
    gl = -sum(x for x in v if x < 0)
    return m, m / (sd / math.sqrt(n)) if sd else 0.0, w, (gp / gl if gl > 0 else 99), n


def main():
    for sym in SYMS:
        pip = 1e-2 if sym.endswith("JPY") else 1e-4
        evs = {k: [] for k in WINDOWS}
        for y in range(2016, 2026):
            f = HISTORY_DIR / sym / f"{y}.hcc"
            if not f.exists():
                continue
            try:
                bars = read_hcc_year(f)
            except PermissionError:
                continue
            ts = sorted(bars)
            have = set(ts)
            for t in ts:
                d = dt.datetime.utcfromtimestamp(t)
                if d.weekday() > 4:
                    continue
                hm = d.hour * 60 + d.minute
                for name, wmin in WINDOWS.items():
                    if hm != wmin:
                        continue
                    t0 = t - 30 * 60          # 30m move into the fix
                    t2 = t + 60 * 60          # fade measured over next 60m
                    if t0 in have and t2 in have:
                        mv = (bars[t][0] - bars[t0][0]) / pip
                        fade = -(bars[t2][3] - bars[t][0]) / pip  # + = move reverted
                        evs[name].append((mv, fade))
        print(f"\n{sym}:")
        for name in WINDOWS:
            for th in (0.5, 1.0, 1.5, 2.0):
                v = [fd for mv, fd in evs[name] if abs(mv) >= th]
                s = st(v)
                if s:
                    print(f"  {name} fade |mv30|>={th}: {s[0]:+.2f}p t={s[1]:+.1f} "
                          f"w={s[2]:.0%} PF={s[3]:.2f} n={s[4]} ({s[4] / 9:.0f}/yr)")


if __name__ == "__main__":
    main()
