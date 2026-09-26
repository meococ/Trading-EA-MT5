"""One-time ETL driver: build parquet cache for all symbols."""
import sys
import time

import data_plane


def main():
    syms = sys.argv[1:] or data_plane.SYMBOLS
    for s in syms:
        t0 = time.time()
        p = data_plane.etl_symbol(s)
        df = data_plane.load(s)
        sus = df["suspect"].mean() * 100
        span = f"{df.index[0]}..{df.index[-1]}"
        print(f"{s}: {len(df):,} bars | suspect {sus:.2f}% | {span} | "
              f"{time.time()-t0:.0f}s -> {p}", flush=True)


if __name__ == "__main__":
    main()
