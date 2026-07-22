"""ECRS Stage-0 preflight scan (OUTCOME-BLIND).

Compression-Release Scalper (ECRS) data preflight + condition-frequency funnel
for EURUSD M5. This script is a Stage-0 FREQUENCY probe only. It NEVER computes
PnL, forward returns, MFE/MAE, exit prices, or reads any bar data after a signal
bar t except the EXISTENCE / TIME / SPREAD / OPEN of the immediate next bar
(the entry bar t+1). Entry price = open of bar t+1 is decision-time information.

Outputs (all under this preflight/ directory):
  - stage0_funnel.json          data preflight + cumulative condition funnel
  - stage0_candidate_cases.csv  50 stratified candidate setups for rendering
  - stage0_bars_m5.parquet      derived M5 bars for the chart renderer

The SDK is imported, never copied. Holdout is sealed at read time: no bar with
time_utc >= 2023-01-01 is ever loaded.
"""

from __future__ import annotations

import json
import sys
from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd

SDK = r"D:\Trading EA MT5\02. AlphaFactory\tools\research"
sys.path.insert(0, SDK)
from indicators import atr_mt5, ema, sma  # noqa: E402
from sealed_loader import load_sealed_bars, elapsed_weeks, sha256_file  # noqa: E402

WORKSPACE = Path(r"D:\Trading EA MT5")
M1_PATH = WORKSPACE / "02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_M1_2015_now.parquet"
M1_MANIFEST = WORKSPACE / "02. AlphaFactory/data/fivepercent/EURUSD/manifest.json"
NEWS_PATH = WORKSPACE / "02. AlphaFactory/data/forexfactory/EURUSD/news_events/forexfactory_high_impact_eurusd_2019_2022.csv"
NEWS_MANIFEST = WORKSPACE / "02. AlphaFactory/data/forexfactory/EURUSD/news_events/manifest.json"

HERE = Path(__file__).resolve().parent
FUNNEL_OUT = HERE / "stage0_funnel.json"
CASES_OUT = HERE / "stage0_candidate_cases.csv"
M5_OUT = HERE / "stage0_bars_m5.parquet"

HOLDOUT_START = pd.Timestamp("2023-01-01")
NEWS_COV_LO = pd.Timestamp("2019-01-01")
NEWS_COV_HI_EXCL = pd.Timestamp("2023-01-01")  # events 2019-01-01 .. 2022-12-31
POOLED_YEARS = (2019, 2020, 2021, 2022)
POOLED_LO = "2019-01-01"
POOLED_HI = "2022-12-31"
NEWS_WINDOW_NS = np.int64(45 * 60) * np.int64(1_000_000_000)  # +/-45 min in ns
SEED = 20260722

# ECRS thresholds (frozen for Stage-0)
ER_LEN = 10
ER_LOW = 0.28          # G1 prior-bar chop ceiling
ER_HIGH = 0.38         # G1 release-bar trend floor
ATR_LEN = 14
ATR_SMA = 20
COMPRESSION_K = 0.70   # G2 atr <= 0.70 * sma20(atr)
BREAKOUT_LOOKBACK = 12  # G3 range excludes current bar
VOL_SMA = 20
VOL_SURGE = 1.7        # G4
EMA_BIAS = 20          # G5
EMA_SLOPE_LAG = 3      # G5 ema20[t] vs ema20[t-3]
SESSION_LO_MIN = 7 * 60          # 07:00 UTC inclusive
SESSION_HI_MIN = 16 * 60 + 30    # 16:30 UTC exclusive
SPREAD_MAX_PIPS = 0.8            # G8
NONOVERLAP_MIN_GAP = 18          # M5 bars, cadence lower-bound spacing


# ----------------------------------------------------------------------------
# M1 -> M5 resample (clone MZMS convention exactly, + tick_volume SUM)
# ----------------------------------------------------------------------------
def build_m5(m1: pd.DataFrame) -> pd.DataFrame:
    indexed = m1.set_index("time_server", drop=False)
    grouped = indexed.resample("5min", label="left", closed="left")
    m5 = grouped.agg(
        time_utc=("time_utc", "first"),
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        spread=("spread", "first"),
        tick_volume=("tick_volume", "sum"),
        minute_count=("close", "count"),
    )
    m5 = m5[m5["minute_count"] > 0].copy()
    # Keep the resample index (server-clock bucket start) as a column too.
    m5.index.name = "time_server"
    m5 = m5.reset_index()
    return m5


def load_news(path: Path) -> np.ndarray:
    news = pd.read_csv(path, usecols=["event_time_utc"])
    values = pd.to_datetime(news["event_time_utc"], utc=True).dt.tz_convert(None)
    return np.sort(values.to_numpy(dtype="datetime64[ns]"))


def news_blocked_vec(entry_ns: np.ndarray, news_ns: np.ndarray, window_ns: np.int64) -> np.ndarray:
    """True where a news event falls within +/- window of the entry time."""
    n = len(entry_ns)
    blocked = np.zeros(n, dtype=bool)
    if len(news_ns) == 0:
        return blocked
    valid = ~np.isnat(entry_ns)
    ev = entry_ns[valid]
    if len(ev) == 0:
        return blocked
    idx = np.searchsorted(news_ns, ev, side="left")
    big = np.iinfo(np.int64).max
    right_ok = idx < len(news_ns)
    ridx = np.clip(idx, 0, len(news_ns) - 1)
    dr = np.abs((news_ns[ridx] - ev).astype("timedelta64[ns]").astype(np.int64))
    dist_right = np.where(right_ok, dr, big)
    left_ok = idx > 0
    lidx = np.clip(idx - 1, 0, len(news_ns) - 1)
    dl = np.abs((ev - news_ns[lidx]).astype("timedelta64[ns]").astype(np.int64))
    dist_left = np.where(left_ok, dl, big)
    mind = np.minimum(dist_right, dist_left)
    blocked[valid] = mind <= np.int64(window_ns)
    return blocked


# ----------------------------------------------------------------------------
# Stratified allocation (largest-remainder with a per-key floor and caps)
# ----------------------------------------------------------------------------
def allocate(counts: dict, n_target: int, floor: int) -> dict:
    keys = list(counts)
    caps = {k: int(counts[k]) for k in keys}
    total = sum(caps.values())
    if total <= n_target:
        return dict(caps)
    alloc = {k: min(floor, caps[k]) for k in keys}
    assigned = sum(alloc.values())
    if assigned >= n_target:
        over = assigned - n_target
        for k in sorted(keys, key=lambda k: -alloc[k]):
            while over > 0 and alloc[k] > 0:
                alloc[k] -= 1
                over -= 1
            if over == 0:
                break
        return alloc
    remaining = n_target - assigned
    while remaining > 0:
        avail = [k for k in keys if caps[k] - alloc[k] > 0]
        if not avail:
            break
        best, best_def = None, -1e18
        for k in avail:
            ideal = n_target * counts[k] / total
            deficit = ideal - alloc[k]
            if deficit > best_def:
                best_def, best = deficit, k
        alloc[best] += 1
        remaining -= 1
    return alloc


def main() -> int:
    # --- data preflight: verify M1 SHA against manifest, abort on mismatch ---
    manifest = json.loads(M1_MANIFEST.read_text(encoding="utf-8"))
    expected_sha = next(
        f["sha256"] for f in manifest["files"] if f["file"] == "EURUSD_M1_2015_now.parquet"
    ).upper()
    actual_sha = sha256_file(M1_PATH)
    manifest_match = actual_sha == expected_sha
    if not manifest_match:
        raise SystemExit(
            f"ABORT parquet SHA mismatch: manifest={expected_sha} actual={actual_sha}"
        )

    news_manifest = json.loads(NEWS_MANIFEST.read_text(encoding="utf-8"))
    news_expected_sha = news_manifest["normalized_csv"]["sha256"].upper()
    news_actual_sha = sha256_file(NEWS_PATH)
    news_manifest_match = news_actual_sha == news_expected_sha

    # --- sealed load (holdout enforced at read time on time_utc) ---
    m1, receipt = load_sealed_bars(M1_PATH, holdout_start=HOLDOUT_START, time_col="time_utc")
    # Resample is server-aligned: sort by the server clock like MZMS.
    m1 = m1.sort_values("time_server").reset_index(drop=True)
    m5 = build_m5(m1)
    del m1

    # --- indicators (all backward-looking) ---
    close = m5["close"]
    high = m5["high"]
    low = m5["low"]
    tv = m5["tick_volume"].astype(float)

    er_num = (close - close.shift(ER_LEN)).abs()
    er_den = close.diff().abs().rolling(ER_LEN).sum()
    er = er_num / er_den.replace(0.0, np.nan)

    atr14 = atr_mt5(m5, ATR_LEN)
    atr_sma20 = sma(atr14, ATR_SMA)
    ema20 = ema(close, EMA_BIAS)
    tv_sma20 = sma(tv, VOL_SMA)

    # entry-bar (t+1) references: ONLY time / open / spread are read
    entry_time = m5["time_utc"].shift(-1)
    entry_open = m5["open"].shift(-1)
    entry_spread = m5["spread"].shift(-1).astype(float)
    entry_server = m5["time_server"].shift(-1)
    has_entry = entry_time.notna().to_numpy()

    et = pd.to_datetime(entry_time)
    et_min = (et.dt.hour * 60 + et.dt.minute)
    entry_year = et.dt.year

    # gates at bar t
    g1 = ((er.shift(1) < ER_LOW) & (er >= ER_HIGH)).fillna(False).to_numpy()
    g2_pre = (atr14.shift(1) <= COMPRESSION_K * atr_sma20.shift(1)).fillna(False).to_numpy()
    g2_at = (atr14 <= COMPRESSION_K * atr_sma20).fillna(False).to_numpy()
    g3_long = (close > high.shift(1).rolling(BREAKOUT_LOOKBACK).max()).fillna(False).to_numpy()
    g3_short = (close < low.shift(1).rolling(BREAKOUT_LOOKBACK).min()).fillna(False).to_numpy()
    g3_any = g3_long | g3_short
    g4 = (tv >= VOL_SURGE * tv_sma20.shift(1)).fillna(False).to_numpy()
    g5_long = ((close > ema20) & (ema20 > ema20.shift(EMA_SLOPE_LAG))).fillna(False).to_numpy()
    g5_short = ((close < ema20) & (ema20 < ema20.shift(EMA_SLOPE_LAG))).fillna(False).to_numpy()
    long_ok = g3_long & g5_long
    short_ok = g3_short & g5_short
    g5_align = long_ok | short_ok

    # G6 session on entry (t+1) time
    g6 = ((et_min >= SESSION_LO_MIN) & (et_min < SESSION_HI_MIN)).fillna(False).to_numpy()

    # G8 spread on entry (t+1) bar
    sp_pips = (entry_spread / 10.0).replace([np.inf, -np.inf], np.nan)
    g8 = (sp_pips.notna() & (sp_pips > 0.0) & (sp_pips <= SPREAD_MAX_PIPS)).to_numpy()

    # G7 news on entry (t+1) time (only meaningful within coverage)
    news_ns = load_news(NEWS_PATH)
    entry_ns = et.to_numpy(dtype="datetime64[ns]")
    g7_pass = ~news_blocked_vec(entry_ns, news_ns, NEWS_WINDOW_NS)

    direction = np.where(long_ok, 1, np.where(short_ok, -1, 0))
    yr = entry_year.to_numpy()  # float with NaN where no entry

    # cumulative chains (variant_pre = mainline)
    c1 = g1
    c2 = c1 & g2_pre
    c3 = c2 & g3_any
    c4 = c3 & g4
    c5 = c4 & g5_align
    c6 = c5 & g6
    c7 = c6 & g7_pass
    c8_cov = c7 & g8         # news-gated final (coverage years)
    c8_nocov = c6 & g8       # final without news gate (non-coverage years)

    # variant_at chain (for Phase-2 freeze decision)
    c2a = c1 & g2_at
    c3a = c2a & g3_any
    c4a = c3a & g4
    c5a = c4a & g5_align
    c6a = c5a & g6
    c8a_cov = c6a & g7_pass & g8
    c8a_nocov = c6a & g8

    def year_mask(y: int) -> np.ndarray:
        return has_entry & (yr == y)

    def csum(mask: np.ndarray, sub: np.ndarray) -> int:
        return int(np.count_nonzero(mask & sub))

    def build_funnel(sub: np.ndarray, cov: bool) -> "OrderedDict":
        c8 = c8_cov if cov else c8_nocov
        final_mask = sub & c8
        fn = OrderedDict()
        fn["n_bars"] = int(np.count_nonzero(sub))
        fn["G1"] = csum(sub, c1)
        fn["G1_G2"] = csum(sub, c2)
        fn["G1_G2_G3"] = csum(sub, c3)
        fn["plus_G4"] = csum(sub, c4)
        fn["plus_G5"] = csum(sub, c5)
        fn["plus_G6"] = csum(sub, c6)
        fn["plus_G7"] = csum(sub, c7) if cov else None
        fn["plus_G8_final"] = int(np.count_nonzero(final_mask))
        fn["final_longs"] = int(np.count_nonzero(final_mask & (direction == 1)))
        fn["final_shorts"] = int(np.count_nonzero(final_mask & (direction == -1)))
        c8a = c8a_cov if cov else c8a_nocov
        fn["final_variant_at"] = int(np.count_nonzero(sub & c8a))
        if cov:
            fn["news_gate"] = "EVALUATED"
        else:
            fn["news_gate"] = "NOT_EVALUATED"
            fn["plus_G7"] = None
        return fn

    per_year = OrderedDict()
    for y in range(2015, 2023):
        cov = y in POOLED_YEARS
        per_year[str(y)] = build_funnel(year_mask(y), cov)

    pooled_mask = has_entry & np.isin(yr, POOLED_YEARS)
    pooled = build_funnel(pooled_mask, cov=True)

    # entry-hour histogram (UTC) of pooled final candidates
    pooled_final_mask = pooled_mask & c8_cov
    final_pos = np.nonzero(pooled_final_mask)[0]
    hours = et.iloc[final_pos].dt.hour.to_numpy()
    hour_hist = OrderedDict(
        (str(h), int(np.count_nonzero(hours == h))) for h in range(24)
    )
    # pre-session (post-G5, before session gate G6) hour histogram: shows where
    # the mechanism actually fires vs the fixed session window (bottleneck diag).
    presession_pos = np.nonzero(pooled_mask & c5)[0]
    presession_hours = et.iloc[presession_pos].dt.hour.to_numpy()
    presession_hour_hist = OrderedDict(
        (str(h), int(np.count_nonzero(presession_hours == h))) for h in range(24)
    )

    # cadence: raw + non-overlapping (greedy min-gap 18 M5 bars)
    weeks = elapsed_weeks(POOLED_LO, POOLED_HI)
    n_final = int(len(final_pos))
    raw_per_week = n_final / weeks if weeks > 0 else None
    accepted = []
    last = None
    for p in final_pos:  # already ascending
        if last is None or (p - last) >= NONOVERLAP_MIN_GAP:
            accepted.append(p)
            last = p
    n_nonoverlap = len(accepted)
    nonoverlap_per_week = n_nonoverlap / weeks if weeks > 0 else None

    # contiguity anomaly: entry bar not exactly 5 min after signal bar
    sig_server = m5["time_server"].to_numpy(dtype="datetime64[ns]")
    entry_server_ns = entry_server.to_numpy(dtype="datetime64[ns]")
    gap_ns = (entry_server_ns[final_pos] - sig_server[final_pos]).astype("timedelta64[ns]").astype(np.int64)
    noncontig = int(np.count_nonzero(gap_ns != np.int64(5 * 60) * np.int64(1_000_000_000)))

    # ---------------- data preflight diagnostics ----------------
    m5_utc = pd.to_datetime(m5["time_utc"])
    m5_min = m5_utc.dt.hour * 60 + m5_utc.dt.minute
    sess = (m5_min >= SESSION_LO_MIN) & (m5_min < SESSION_HI_MIN)
    sess_1922 = sess & m5_utc.dt.year.between(2019, 2022)
    n_sess = int(np.count_nonzero(sess_1922.to_numpy()))
    zero_rate = (
        float((m5.loc[sess_1922, "spread"] == 0).mean()) if n_sess else None
    )
    mc = m5["minute_count"]
    mc_counts = OrderedDict(
        (str(int(k)), int(v)) for k, v in mc.value_counts().sort_index().items()
    )
    weekend_bars = int(np.count_nonzero(m5_utc.dt.dayofweek.isin([5, 6]).to_numpy()))

    preflight = OrderedDict(
        parquet_path=str(M1_PATH),
        parquet_sha256=actual_sha,
        parquet_manifest_sha256=expected_sha,
        parquet_manifest_match=manifest_match,
        news_path=str(NEWS_PATH),
        news_sha256=news_actual_sha,
        news_manifest_sha256=news_expected_sha,
        news_manifest_match=news_manifest_match,
        news_events_loaded=int(len(news_ns)),
        seal_receipt=receipt,
        m5_row_count=int(len(m5)),
        m5_time_utc_min=str(m5_utc.min()),
        m5_time_utc_max=str(m5_utc.max()),
        session_bars_2019_2022=n_sess,
        spread_zero_rate_session_2019_2022=zero_rate,
        minute_count_distribution=mc_counts,
        minute_count_summary=OrderedDict(
            min=int(mc.min()), max=int(mc.max()),
            mean=round(float(mc.mean()), 4), median=float(mc.median()),
        ),
        weekend_m5_bars=weekend_bars,
    )

    outcome_blind = OrderedDict(
        outcome_blind=True,
        not_computed=[
            "PnL / returns / net_r",
            "forward returns of any horizon",
            "MFE / MAE / excursions",
            "exit prices, exit times, stops, targets, holding time",
            "any high/low/close of the entry bar t+1 or any later bar",
            "win rate / profit factor / expectancy",
        ],
        entry_bar_reads_allowed=["existence", "time_utc", "open (=entry price)", "spread"],
        note="Gates G1-G5 use only bars <= t; G6/G7/G8 use only time/spread of bar t+1.",
    )

    funnel = OrderedDict(
        schema_version="ecrs_stage0_preflight_funnel.v1",
        lane="EA_ECRS_CompressionReleaseScalper",
        stage="stage0_preflight",
        symbol="EURUSD",
        timeframe="M5",
        generated_from=str(Path(__file__).resolve()),
        thresholds=OrderedDict(
            er_len=ER_LEN, er_low=ER_LOW, er_high=ER_HIGH,
            atr_len=ATR_LEN, atr_sma=ATR_SMA, compression_k=COMPRESSION_K,
            breakout_lookback=BREAKOUT_LOOKBACK, vol_sma=VOL_SMA, vol_surge=VOL_SURGE,
            ema_bias=EMA_BIAS, ema_slope_lag=EMA_SLOPE_LAG,
            session_utc=[SESSION_LO_MIN, SESSION_HI_MIN], spread_max_pips=SPREAD_MAX_PIPS,
            news_window_min=45, nonoverlap_min_gap_bars=NONOVERLAP_MIN_GAP,
        ),
        data_preflight=preflight,
        outcome_blind_attestation=outcome_blind,
        funnel_mainline_variant="variant_pre",
        funnel_per_year=per_year,
        funnel_pooled_2019_2022=pooled,
        pooled_entry_hour_histogram_utc=hour_hist,
        pooled_presession_hour_histogram_utc=presession_hour_hist,
        pooled_presession_note="entry-hour of post-G5 survivors BEFORE the session gate G6; contrast with the final histogram to see the session bottleneck",
        cadence_pooled_2019_2022=OrderedDict(
            elapsed_weeks=round(float(weeks), 4),
            final_candidates=n_final,
            raw_signals_per_week=raw_per_week,
            nonoverlapping_candidates=n_nonoverlap,
            nonoverlapping_signals_per_week=nonoverlap_per_week,
            nonoverlap_rule=f"greedy: skip candidates within {NONOVERLAP_MIN_GAP} M5 bars of an accepted one",
        ),
        anomalies=OrderedDict(
            noncontiguous_entry_bars=noncontig,
            noncontiguous_note="final candidates whose entry bar t+1 is not exactly 5 min after signal bar t (session/weekend gaps)",
        ),
    )

    # ---------------- stratified candidate sample (50) ----------------
    cand = pd.DataFrame({
        "signal_pos": final_pos,
        "signal_time_server": m5["time_server"].to_numpy()[final_pos],
        "entry_time_utc": et.iloc[final_pos].to_numpy(),
        "entry_time_server": entry_server_ns[final_pos],
        "direction": direction[final_pos],
        "entry": entry_open.to_numpy()[final_pos],
        "year": et.iloc[final_pos].dt.year.to_numpy(),
    })

    rng = np.random.RandomState(SEED)
    n_target = min(50, len(cand))
    if len(cand) <= n_target:
        chosen = cand.copy()
    else:
        year_counts = {int(y): int((cand["year"] == y).sum()) for y in sorted(cand["year"].unique())}
        year_alloc = allocate(year_counts, n_target, floor=4)
        picks = []
        for y, ycount in year_alloc.items():
            ysub = cand[cand["year"] == y]
            dir_counts = {int(d): int((ysub["direction"] == d).sum()) for d in sorted(ysub["direction"].unique())}
            dir_alloc = allocate(dir_counts, ycount, floor=0)
            for d, dcount in dir_alloc.items():
                cell = ysub[ysub["direction"] == d]
                take = min(dcount, len(cell))
                if take <= 0:
                    continue
                idx = rng.choice(cell.index.to_numpy(), size=take, replace=False)
                picks.extend(idx.tolist())
        chosen = cand.loc[picks]
        # top up to n_target from the remaining pool if under-filled
        if len(chosen) < n_target:
            remaining = cand.drop(index=chosen.index)
            extra_n = min(n_target - len(chosen), len(remaining))
            if extra_n > 0:
                extra_idx = rng.choice(remaining.index.to_numpy(), size=extra_n, replace=False)
                chosen = pd.concat([chosen, cand.loc[extra_idx]])

    chosen = chosen.sort_values("signal_pos").reset_index(drop=True)
    side_map = {1: "LONG", -1: "SHORT"}
    rows = []
    for i, r in chosen.iterrows():
        y = int(r["year"])
        s = "L" if r["direction"] == 1 else "S"
        rows.append(OrderedDict(
            case_id=f"ECRS-S0-{i + 1:02d}-{y}{s}",
            entry_time_utc=pd.Timestamp(r["entry_time_utc"]).strftime("%Y-%m-%d %H:%M:%S"),
            direction=int(r["direction"]),
            entry=round(float(r["entry"]), 5),
            side=side_map[int(r["direction"])],
            year=y,
            signal_time_server=pd.Timestamp(r["signal_time_server"]).strftime("%Y-%m-%d %H:%M:%S"),
        ))
    cases_df = pd.DataFrame(rows)
    cases_df.to_csv(CASES_OUT, index=False)

    # sample stratification summary into funnel
    funnel["candidate_sample"] = OrderedDict(
        seed=SEED,
        requested=50,
        selected=int(len(cases_df)),
        pooled_final_available=int(len(cand)),
        by_year=OrderedDict(
            (str(int(y)), int((cases_df["year"] == y).sum())) for y in sorted(cases_df["year"].unique())
        ),
        by_direction=OrderedDict(
            longs=int((cases_df["direction"] == 1).sum()),
            shorts=int((cases_df["direction"] == -1).sum()),
        ),
        csv_path=str(CASES_OUT),
    )

    # ---------------- write derived M5 parquet for renderer ----------------
    m5_out = m5[["time_server", "time_utc", "open", "high", "low", "close",
                 "spread", "tick_volume", "minute_count"]].copy()
    m5_out.to_parquet(M5_OUT, index=False)
    funnel["derived_m5_parquet"] = OrderedDict(
        path=str(M5_OUT),
        rows=int(len(m5_out)),
        sha256=sha256_file(M5_OUT),
        note="derived from canonical M1, NOT a canonical source; for chart rendering only",
    )

    FUNNEL_OUT.write_text(json.dumps(funnel, indent=2, default=str) + "\n", encoding="utf-8")

    print(json.dumps({
        "pooled_final": pooled["plus_G8_final"],
        "pooled_final_variant_at": pooled["final_variant_at"],
        "raw_per_week": round(raw_per_week, 4) if raw_per_week else None,
        "nonoverlap_per_week": round(nonoverlap_per_week, 4) if nonoverlap_per_week else None,
        "candidates_selected": int(len(cases_df)),
        "spread_zero_rate_session_1922": zero_rate,
        "m5_rows": int(len(m5)),
        "funnel": str(FUNNEL_OUT),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
