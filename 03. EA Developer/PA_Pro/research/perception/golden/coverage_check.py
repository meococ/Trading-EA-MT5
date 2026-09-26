"""coverage_check.py — P0: does the M1 cache cover the BOOK window, and
what timezone does the feed use?

Writes golden/COVERAGE.md.  Light: one parquet scan of the window.
"""

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
for _p in (HERE, PERC, os.path.join(PERC, "..", "..", "lib")):
    _p = os.path.abspath(_p)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import book_loader  # noqa: E402
import cet  # noqa: E402
import pa_clock  # noqa: E402


def main():
    d = book_loader.load_m1()
    t, cet_e = d["t"], d["cet"]
    n = len(t)
    srv_min = (t % 86400) // 60
    dow = (((cet_e // 86400) + 3) % 7)
    cet_day = cet_e // 86400

    # per-CET-day bar counts
    days, counts = np.unique(cet_day, return_counts=True)
    weekday = (days + 3) % 7
    df_day = pd.DataFrame({"day0_cet": days * 86400, "dow": weekday,
                           "n_m1": counts})
    df_day["date"] = pd.to_datetime(df_day["day0_cet"], unit="s").dt.date
    wk = df_day[df_day["dow"] < 5]

    # feed timezone evidence: on a mid-week day, which minute-of-day is the
    # first bar of the *server* day vs the *CET* day?
    mid = df_day[(df_day["dow"] == 2)].iloc[10]     # a Wednesday
    mask = cet_day == (mid["day0_cet"] // 86400)
    tt = t[mask]
    first_srv_min = int((tt[0] % 86400) // 60)
    last_srv_min = int((tt[-1] % 86400) // 60)

    gaps = np.diff(t)
    big_gaps = gaps[gaps > 3600]
    n_gaps = int(len(big_gaps))

    lines = []
    a = lines.append
    a("# BOOK-window coverage check (P0)\n")
    a(f"- rows loaded: {n:,} M1 bars")
    a(f"- first bar (server epoch): {t[0]} = "
      f"{pd.to_datetime(t[0], unit='s')} server wall")
    a(f"- last  bar (server epoch): {t[-1]} = "
      f"{pd.to_datetime(t[-1], unit='s')} server wall")
    a(f"- CET days covered: {len(df_day)} "
      f"({df_day['date'].iloc[0]} -> {df_day['date'].iloc[-1]})")
    a(f"- weekday rows: {len(wk)}; median M1 bars/weekday: "
      f"{int(wk['n_m1'].median())} (full day ~= 1424 on this feed)")
    a(f"- weekdays with <1000 bars: "
      f"{(wk['n_m1'] < 1000).sum()} -> "
      f"{wk.loc[wk['n_m1'] < 1000, 'date'].tolist()}")
    a(f"- intra-day gaps > 1 h (excl. weekends): {n_gaps}; largest "
      f"{int(gaps.max())//3600} h")
    a("\n## Feed timezone\n")
    a(f"- sample CET Wednesday {mid['date']}: first bar at server "
      f"{first_srv_min//60:02d}:{first_srv_min%60:02d}, last at server "
      f"{last_srv_min//60:02d}:{last_srv_min%60:02d}")
    a("- `pa_clock` convention: server = UTC+2 (winter) / +3 (EU summer).")
    a("- CET = UTC+1/+2 on the same EU switch dates, so the feed reads "
      "**CET+1 h** during market hours. Empirical candle alignment "
      "(P1.3) will confirm against the book's printed hour labels.")
    # summer/winter offset check on data
    a("\n## Offset sanity on data\n")
    for dstr in ("2012-03-05", "2012-07-09"):
        day0 = int(pd.Timestamp(dstr).timestamp())
        sel = (cet_e // 86400 == day0 // 86400)
        if sel.any():
            tt2 = t[sel]
            a(f"- {dstr}: {int(sel.sum())} bars, first server "
              f"{int((tt2[0]%86400)//60)} min; pa_clock offset "
              f"{int(pa_clock.server_offset_hours(tt2[0]))} h, cet offset "
              f"{int(cet.cet_offset_hours(pa_clock.server_to_utc_epoch(tt2[0])))} h")
    out = os.path.join(HERE, "COVERAGE.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
