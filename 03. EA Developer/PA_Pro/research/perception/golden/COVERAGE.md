# BOOK-window coverage check (P0)

- rows loaded: 211,597 M1 bars
- first bar (server epoch): 1329094800 = 2012-02-13 01:00:00 server wall
- last  bar (server epoch): 1347058740 = 2012-09-07 22:59:00 server wall
- CET days covered: 179 (2012-02-13 -> 2012-09-07)
- weekday rows: 150; median M1 bars/weekday: 1424 (full day ~= 1424 on this feed)
- weekdays with <1000 bars: 0 -> []
- intra-day gaps > 1 h (excl. weekends): 29; largest 50 h

## Feed timezone

- sample CET Wednesday 2012-04-25: first bar at server 01:00, last at server 00:59
- `pa_clock` convention: server = UTC+2 (winter) / +3 (EU summer).
- CET = UTC+1/+2 on the same EU switch dates, so the feed reads **CET+1 h** during market hours. Empirical candle alignment (P1.3) will confirm against the book's printed hour labels.

## Offset sanity on data

- 2012-03-05: 1424 bars, first server 60 min; pa_clock offset 2 h, cet offset 1 h
- 2012-07-09: 1424 bars, first server 60 min; pa_clock offset 3 h, cet offset 2 h
