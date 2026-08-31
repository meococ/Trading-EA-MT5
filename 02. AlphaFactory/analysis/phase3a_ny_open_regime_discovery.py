#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

try:
    import MetaTrader5 as mt5
except ImportError as exc:
    raise SystemExit("MetaTrader5 package is required for Phase 3A prep.") from exc


ROOT = Path(r"02. AlphaFactory/runs/XAU_Scalp_Portfolio")
DATE_TAG = "20260308"
OUT_DIR = ROOT / f"phase3a_prep_{DATE_TAG}"
SYMBOL = "XAUUSD"
UTC_FROM = datetime(2020, 3, 7, tzinfo=timezone.utc)
UTC_TO = datetime(2026, 3, 6, 23, 59, 59, tzinfo=timezone.utc)

NY_PREOPEN_START_MIN = 8 * 60 + 30
NY_OPEN_MIN = 9 * 60 + 30
NY_OPEN_5_END_MIN = 9 * 60 + 35
NY_OPEN_10_END_MIN = 9 * 60 + 40
NY_OPEN_15_END_MIN = 9 * 60 + 45
NY_OPEN_30_END_MIN = 10 * 60
NY_SESSION_END_MIN = 13 * 60 + 30
LONDON_START_MIN = 3 * 60

CLASS_ACCEPTANCE = "OPEN_ACCEPTANCE"
CLASS_FAILURE = "OPEN_FAILURE"
CLASS_RECLAIM = "OPEN_RECLAIM"
CLASS_NOTRADE = "OPEN_NO_TRADE"

PLAYBOOK_MAP = {
    CLASS_ACCEPTANCE: "OPEN_ACCEPTANCE_TRADER",
    CLASS_FAILURE: "OPEN_FAILURE_FADE_TRADER",
    CLASS_RECLAIM: "POST_OPEN_RECLAIM_TRADER",
    CLASS_NOTRADE: "NO_TRADE",
}

TRADEABLE_CLASSES = {CLASS_ACCEPTANCE, CLASS_FAILURE, CLASS_RECLAIM}


@dataclass
class FeatureSpec:
    name: str
    family: str
    available_by: str
    note: str = ""
    supported: bool = True


FEATURE_SPECS: List[FeatureSpec] = [
    FeatureSpec("preopen_range_norm", "PREOPEN_EXPANSION_COMPRESSION", "09:30", "60m pre-open range proxy"),
    FeatureSpec("preopen_range_pct20", "PREOPEN_EXPANSION_COMPRESSION", "09:30", "20-day rolling percentile"),
    FeatureSpec("or10_width_norm", "OPENING_RANGE_WIDTH", "09:40"),
    FeatureSpec("or30_width_norm", "OPENING_RANGE_WIDTH", "10:00"),
    FeatureSpec("impulse10_norm", "OPENING_IMPULSE", "09:40"),
    FeatureSpec("impulse15_norm", "OPENING_IMPULSE", "09:45"),
    FeatureSpec("impulse30_norm", "OPENING_IMPULSE", "10:00"),
    FeatureSpec("accept_balance_10", "ACCEPTANCE_COUNT", "09:40"),
    FeatureSpec("accept_balance_30", "ACCEPTANCE_COUNT", "10:00"),
    FeatureSpec("accept_outside_london_30", "ACCEPTANCE_COUNT", "10:00"),
    FeatureSpec("rotation_10", "VWAP_ROTATION", "09:40"),
    FeatureSpec("rotation_30", "VWAP_ROTATION", "10:00"),
    FeatureSpec("london_pos_at_open", "LONDON_POSITION", "09:30"),
    FeatureSpec("london_extreme_sweep_norm", "LONDON_SWEEP_FAILURE", "10:00"),
    FeatureSpec("london_sweep_flag", "LONDON_SWEEP_FAILURE", "10:00"),
    FeatureSpec("vwap_dist_10_norm", "VWAP_DISTANCE_RECLAIM", "09:40"),
    FeatureSpec("vwap_dist_30_norm", "VWAP_DISTANCE_RECLAIM", "10:00"),
    FeatureSpec("vwap_reclaim_15", "VWAP_DISTANCE_RECLAIM", "09:45"),
    FeatureSpec("or_mid_status_30", "OR_MIDPOINT", "10:00"),
    FeatureSpec("spread_mean_10", "SPREAD_PERCENTILE", "09:40"),
    FeatureSpec("spread_pct_10", "SPREAD_PERCENTILE", "09:40"),
    FeatureSpec("handoff_conflict", "HANDOFF_ALIGNMENT_CONFLICT", "10:00"),
    FeatureSpec("time_since_major_news_min", "NEWS_DISTANCE", "09:30", "Historical calendar incomplete; not ranked", supported=False),
]


def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: List[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def nth_sunday(year: int, month: int, nth: int) -> datetime:
    d = datetime(year, month, 1)
    while d.weekday() != 6:
        d += timedelta(days=1)
    return d + timedelta(days=7 * (nth - 1))


def ny_dst_for_utc(utc_dt: datetime) -> bool:
    year = utc_dt.year
    start = nth_sunday(year, 3, 2).replace(hour=7)
    end = nth_sunday(year, 11, 1).replace(hour=6)
    return start <= utc_dt.replace(tzinfo=None) < end


def utc_to_ny(ts: float) -> datetime:
    utc_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return (utc_dt + timedelta(hours=(-4 if ny_dst_for_utc(utc_dt) else -5))).replace(tzinfo=None)


def parse_utc(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None)


def rotation_count(close_series: pd.Series, vwap_series: pd.Series) -> int:
    side = np.sign(close_series - vwap_series)
    return int(((side.shift(1) != side) & (side != 0) & (side.shift(1) != 0)).sum())


def anchored_vwap(df: pd.DataFrame) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    vol = df["tick_volume"].clip(lower=1)
    return (tp * vol).cumsum() / vol.cumsum()


def mutual_info(series: pd.Series, labels: pd.Series, bins: int = 5) -> float:
    s = pd.Series(series)
    y = pd.Series(labels)
    mask = s.notna() & y.notna()
    s = s[mask]
    y = y[mask]
    if s.empty or s.nunique() <= 1:
        return 0.0
    if pd.api.types.is_numeric_dtype(s):
        try:
            s = pd.qcut(s, q=min(bins, s.nunique()), duplicates="drop")
        except Exception:
            s = s.astype(str)
    else:
        s = s.astype(str)
    joint = pd.crosstab(s, y, normalize=True)
    px = joint.sum(axis=1)
    py = joint.sum(axis=0)
    out = 0.0
    for i in joint.index:
        for j in joint.columns:
            pxy = joint.loc[i, j]
            if pxy > 0:
                out += pxy * math.log2(pxy / (px[i] * py[j]))
    return float(out)


def dominant_class(series: pd.Series, labels: pd.Series) -> str:
    frame = pd.DataFrame({"v": series, "y": labels}).dropna()
    if frame.empty:
        return ""
    if pd.api.types.is_numeric_dtype(frame["v"]):
        stats = frame.groupby("y")["v"].median()
        return str(stats.idxmax()) if not stats.empty else ""
    stats = frame.groupby("y")["v"].agg(lambda x: x.value_counts().index[0])
    return str(stats.iloc[0]) if not stats.empty else ""


def classify_day(row: pd.Series) -> str:
    max_score = max(row["score_acceptance"], row["score_failure"], row["score_reclaim"])
    if max_score < 4:
        return CLASS_NOTRADE
    scores = [
        (CLASS_ACCEPTANCE, row["score_acceptance"]),
        (CLASS_FAILURE, row["score_failure"]),
        (CLASS_RECLAIM, row["score_reclaim"]),
    ]
    return max(scores, key=lambda kv: kv[1])[0]


def build_reason(row: pd.Series) -> str:
    if row["day_type"] == CLASS_ACCEPTANCE:
        return "one-sided acceptance after NY open; close stayed far from VWAP/value and rotations stayed contained"
    if row["day_type"] == CLASS_FAILURE:
        return "early sweep/acceptance failed; session reversed with two-sided excursion and opposite close"
    if row["day_type"] == CLASS_RECLAIM:
        return "open dislocation was rebalanced; price reclaimed VWAP/OR midpoint and rotated around value"
    return "open response stayed ambiguous or mixed; best action is no-trade"


def policy_viability(day_type: str) -> Dict[str, str]:
    if day_type == CLASS_ACCEPTANCE:
        return {
            "ftmo_standard": "MEDIUM_LOW",
            "ftmo_swing": "MEDIUM",
            "the5ers_highstakes": "MEDIUM",
            "note": "Often triggers near 10:00 NY; vulnerable to macro-news blackout overlap and open-spread spikes.",
        }
    if day_type == CLASS_FAILURE:
        return {
            "ftmo_standard": "MEDIUM",
            "ftmo_swing": "MEDIUM_HIGH",
            "the5ers_highstakes": "MEDIUM",
            "note": "Usually needs 10-30m post-open confirmation; safer than instant open chasing, but still early-session sensitive.",
        }
    if day_type == CLASS_RECLAIM:
        return {
            "ftmo_standard": "MEDIUM_HIGH",
            "ftmo_swing": "HIGH",
            "the5ers_highstakes": "MEDIUM_HIGH",
            "note": "Typically later and lower-intensity; structurally most portable under strict no-HFT / visible-SL expectations.",
        }
    return {
        "ftmo_standard": "HIGH",
        "ftmo_swing": "HIGH",
        "the5ers_highstakes": "HIGH",
        "note": "No-trade day type; safest prop action is to stay flat.",
    }


def playbook_secondary(day_type: str) -> str:
    if day_type == CLASS_ACCEPTANCE:
        return "NO_TRADE_CONSERVATIVE"
    if day_type == CLASS_FAILURE:
        return "POST_OPEN_RECLAIM_TRADER"
    if day_type == CLASS_RECLAIM:
        return "NO_TRADE_CONSERVATIVE"
    return "NO_TRADE"


def prototypical_rows(df: pd.DataFrame, label: str, n: int = 3) -> pd.DataFrame:
    subset = df[df["day_type"] == label].copy()
    if subset.empty:
        return subset
    cols = ["or30_width_norm", "impulse30_norm", "vwap_dist_30_norm", "rotation_30", "close_to_vwap_norm", "session_efficiency", "london_extreme_sweep_norm"]
    center = subset[cols].median()
    subset["_dist"] = ((subset[cols] - center) ** 2).sum(axis=1) ** 0.5
    return subset.nsmallest(n, "_dist")


def load_mt5_rates(symbol: str):
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    terminal = mt5.terminal_info()
    m1 = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, UTC_FROM, UTC_TO)
    m5 = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, UTC_FROM, UTC_TO)
    mt5.shutdown()
    if m1 is None or len(m1) == 0:
        raise RuntimeError("No M1 data returned from MT5.")
    if m5 is None or len(m5) == 0:
        raise RuntimeError("No M5 data returned from MT5.")
    df1 = pd.DataFrame(m1)
    df5 = pd.DataFrame(m5)
    for df in (df1, df5):
        df["utc_dt"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df["utc_naive"] = df["time"].apply(parse_utc)
        df["ny_dt"] = df["time"].apply(utc_to_ny)
        ny_dt = pd.to_datetime(df["ny_dt"])
        df["ny_date"] = ny_dt.dt.date
        df["ny_hour"] = ny_dt.dt.hour
        df["ny_minute"] = ny_dt.dt.minute
        df["ny_min_of_day"] = df["ny_hour"] * 60 + df["ny_minute"]
        df["weekday"] = ny_dt.dt.day_name()
        df["year"] = ny_dt.dt.year
    prev_close = df5["close"].shift(1)
    tr = pd.concat(
        [
            (df5["high"] - df5["low"]).abs(),
            (df5["high"] - prev_close).abs(),
            (df5["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df5["atr14"] = tr.rolling(14).mean()
    return df1, df5, terminal


def build_day_feature_table(m1: pd.DataFrame, m5: pd.DataFrame) -> pd.DataFrame:
    rows = []
    m5_groups = {d: g for d, g in m5.groupby("ny_date")}
    for ny_date, day in m1.groupby("ny_date"):
        if pd.Timestamp(ny_date).weekday() >= 5:
            continue
        pre = day[(day["ny_min_of_day"] >= NY_PREOPEN_START_MIN) & (day["ny_min_of_day"] < NY_OPEN_MIN)].copy()
        w5 = day[(day["ny_min_of_day"] >= NY_OPEN_MIN) & (day["ny_min_of_day"] < NY_OPEN_5_END_MIN)].copy()
        w10 = day[(day["ny_min_of_day"] >= NY_OPEN_MIN) & (day["ny_min_of_day"] < NY_OPEN_10_END_MIN)].copy()
        w15 = day[(day["ny_min_of_day"] >= NY_OPEN_MIN) & (day["ny_min_of_day"] < NY_OPEN_15_END_MIN)].copy()
        w30 = day[(day["ny_min_of_day"] >= NY_OPEN_MIN) & (day["ny_min_of_day"] < NY_OPEN_30_END_MIN)].copy()
        post = day[(day["ny_min_of_day"] >= NY_OPEN_30_END_MIN) & (day["ny_min_of_day"] < NY_SESSION_END_MIN)].copy()
        session = day[(day["ny_min_of_day"] >= NY_OPEN_MIN) & (day["ny_min_of_day"] < NY_SESSION_END_MIN)].copy()
        london = day[(day["ny_min_of_day"] >= LONDON_START_MIN) & (day["ny_min_of_day"] < NY_OPEN_MIN)].copy()
        if min(len(pre), len(w5), len(w10), len(w15), len(w30), len(post), len(session), len(london)) == 0:
            continue
        m5_day = m5_groups.get(ny_date)
        if m5_day is None or m5_day.empty:
            continue
        m5_pre = m5_day[m5_day["ny_min_of_day"] < NY_OPEN_MIN]
        if m5_pre.empty:
            continue
        atr14_pre = float(m5_pre.iloc[-1]["atr14"])
        if not atr14_pre or math.isnan(atr14_pre):
            continue

        preopen_range = float(pre["high"].max() - pre["low"].min())
        norm = max(preopen_range, 0.01)
        open_price = float(w30.iloc[0]["open"])
        close10 = float(w10.iloc[-1]["close"])
        close15 = float(w15.iloc[-1]["close"])
        close30 = float(w30.iloc[-1]["close"])
        session_close = float(session.iloc[-1]["close"])
        or30_high = float(w30["high"].max())
        or30_low = float(w30["low"].min())
        or30_mid = (or30_high + or30_low) / 2.0
        post_high = float(post["high"].max())
        post_low = float(post["low"].min())
        session_high = float(session["high"].max())
        session_low = float(session["low"].min())

        vwap10 = anchored_vwap(w10)
        vwap15 = anchored_vwap(w15)
        vwap30 = anchored_vwap(w30)
        vwap_session = anchored_vwap(session)
        rotation10 = rotation_count(w10["close"], vwap10)
        rotation30 = rotation_count(w30["close"], vwap30)

        london_high = float(london["high"].max())
        london_low = float(london["low"].min())
        london_open = float(london.iloc[0]["open"])
        london_close = float(london.iloc[-1]["close"])
        london_move_norm = (london_close - london_open) / norm
        london_position_open = (open_price - london_low) / max(london_high - london_low, 0.01)
        london_sweep_up = int(w30["high"].max() > london_high)
        london_sweep_dn = int(w30["low"].min() < london_low)
        london_sweep_flag = int(london_sweep_up or london_sweep_dn)
        london_extreme_sweep_norm = max(
            0.0,
            (float(w30["high"].max()) - london_high) / norm,
            (london_low - float(w30["low"].min())) / norm,
        )

        accept_count_10_up = int((w10["close"] > vwap10).sum())
        accept_count_10_dn = int((w10["close"] < vwap10).sum())
        accept_count_30_up = int((w30["close"] > vwap30).sum())
        accept_count_30_dn = int((w30["close"] < vwap30).sum())
        accept_balance_10 = abs(accept_count_10_up - accept_count_10_dn)
        accept_balance_30 = abs(accept_count_30_up - accept_count_30_dn)
        accept_outside_london_30 = int(((w30["close"] > london_high) | (w30["close"] < london_low)).sum())

        up_ext_norm = (post_high - or30_high) / norm
        dn_ext_norm = (or30_low - post_low) / norm
        close_rel_norm = (session_close - open_price) / norm
        close_to_vwap_norm = abs(session_close - float(vwap_session.iloc[-1])) / norm
        close_to_mid_norm = abs(session_close - or30_mid) / norm
        session_efficiency = abs(session_close - open_price) / max(session_high - session_low, 0.01)
        early_sign = int(np.sign(close30 - open_price))
        close_sign = int(np.sign(session_close - open_price))
        dominant_ext = max(up_ext_norm, dn_ext_norm)
        opposite_ext = min(up_ext_norm, dn_ext_norm)
        two_sided = int(up_ext_norm >= 0.70 and dn_ext_norm >= 0.70)

        score_acceptance = (
            int(abs(close_rel_norm) >= 0.80)
            + int(session_efficiency >= 0.22)
            + int(dominant_ext >= opposite_ext * 1.20)
            + int(close_to_vwap_norm >= 0.80)
            + int(rotation30 <= 4)
        )
        score_failure = (
            london_sweep_flag
            + two_sided
            + int(early_sign != 0 and close_sign != 0 and early_sign != close_sign)
            + int(close_to_vwap_norm >= 0.80)
            + int(rotation30 >= 4)
        )
        score_reclaim = (
            two_sided
            + int(close_to_vwap_norm <= 0.35)
            + int(rotation30 >= 4)
            + int(close_to_mid_norm <= 0.35)
            + int(abs(close_rel_norm) <= 0.50)
        )

        rows.append(
            {
                "ny_date": pd.Timestamp(ny_date),
                "year": int(pd.Timestamp(ny_date).year),
                "weekday": str(w30.iloc[0]["weekday"]),
                "split": "A" if pd.Timestamp(ny_date) <= pd.Timestamp("2023-03-06") else "B",
                "bars_m1_open30": int(len(w30)),
                "bars_m1_session": int(len(session)),
                "atr14_pre_m5": float(atr14_pre),
                "preopen_range": preopen_range,
                "preopen_range_norm": preopen_range / atr14_pre if atr14_pre > 0 else 0.0,
                "or5_width_norm": float(w5["high"].max() - w5["low"].min()) / norm,
                "or10_width_norm": float(w10["high"].max() - w10["low"].min()) / norm,
                "or30_width_norm": (or30_high - or30_low) / norm,
                "impulse10_norm": (close10 - open_price) / norm,
                "impulse15_norm": (close15 - open_price) / norm,
                "impulse30_norm": (close30 - open_price) / norm,
                "accept_count_10_up": accept_count_10_up,
                "accept_count_10_dn": accept_count_10_dn,
                "accept_count_30_up": accept_count_30_up,
                "accept_count_30_dn": accept_count_30_dn,
                "accept_balance_10": accept_balance_10,
                "accept_balance_30": accept_balance_30,
                "accept_outside_london_30": accept_outside_london_30,
                "rotation_10": rotation10,
                "rotation_30": rotation30,
                "london_position_open": london_position_open,
                "london_pos_at_open": london_position_open,
                "london_move_norm": london_move_norm,
                "london_sweep_flag": london_sweep_flag,
                "london_sweep_up": london_sweep_up,
                "london_sweep_dn": london_sweep_dn,
                "london_extreme_sweep_norm": london_extreme_sweep_norm,
                "vwap_dist_10_norm": abs(close10 - float(vwap10.iloc[-1])) / norm,
                "vwap_dist_30_norm": abs(close30 - float(vwap30.iloc[-1])) / norm,
                "vwap_reclaim_15": int(np.sign(close15 - float(vwap15.iloc[-1])) != np.sign(float(w15.iloc[0]["close"]) - float(vwap15.iloc[0])) and np.sign(float(w15.iloc[0]["close"]) - float(vwap15.iloc[0])) != 0),
                "or_mid_status_30": (close30 - or30_mid) / norm,
                "spread_mean_10": float(w10["spread"].mean()),
                "spread_median_10": float(w10["spread"].median()),
                "handoff_conflict": int(np.sign(london_move_norm) != np.sign(close30 - open_price) and abs(close30 - open_price) > 0.0),
                "time_since_major_news_min": np.nan,
                "up_ext_norm": up_ext_norm,
                "dn_ext_norm": dn_ext_norm,
                "close_rel_norm": close_rel_norm,
                "close_to_vwap_norm": close_to_vwap_norm,
                "close_to_mid_norm": close_to_mid_norm,
                "session_efficiency": session_efficiency,
                "session_high": session_high,
                "session_low": session_low,
                "session_range_norm": (session_high - session_low) / norm,
                "score_acceptance": score_acceptance,
                "score_failure": score_failure,
                "score_reclaim": score_reclaim,
                "primary_open_state": "UP" if close30 > open_price else ("DOWN" if close30 < open_price else "FLAT"),
            }
        )

    df = pd.DataFrame(rows).sort_values("ny_date").reset_index(drop=True)
    if df.empty:
        raise RuntimeError("Day feature table is empty; dataset extraction failed.")
    df["preopen_range_pct20"] = (
        df["preopen_range_norm"]
        .rolling(20, min_periods=10)
        .apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1] if len(x) else np.nan, raw=False)
    )
    df["spread_pct_10"] = df["spread_mean_10"].rank(pct=True)
    df["day_type"] = df.apply(classify_day, axis=1)
    df["recommended_playbook"] = df["day_type"].map(PLAYBOOK_MAP)
    df["secondary_playbook"] = df["day_type"].apply(playbook_secondary)
    df["tradeable"] = df["day_type"].isin(TRADEABLE_CLASSES)
    df["reason_text"] = df.apply(build_reason, axis=1)
    return df


def build_feature_scorecard(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    split_a = df[df["split"] == "A"]
    split_b = df[df["split"] == "B"]
    for spec in FEATURE_SPECS:
        if not spec.supported:
            rows.append(
                {
                    "feature": spec.name,
                    "family": spec.family,
                    "available_by": spec.available_by,
                    "supported": False,
                    "full_mi": np.nan,
                    "split_a_mi": np.nan,
                    "split_b_mi": np.nan,
                    "robust_score": np.nan,
                    "dominant_class": "",
                    "note": spec.note or "calendar_gap",
                }
            )
            continue
        full_mi = mutual_info(df[spec.name], df["day_type"])
        split_a_mi = mutual_info(split_a[spec.name], split_a["day_type"])
        split_b_mi = mutual_info(split_b[spec.name], split_b["day_type"])
        robust = min(full_mi, split_a_mi, split_b_mi)
        rows.append(
            {
                "feature": spec.name,
                "family": spec.family,
                "available_by": spec.available_by,
                "supported": True,
                "full_mi": round(full_mi, 6),
                "split_a_mi": round(split_a_mi, 6),
                "split_b_mi": round(split_b_mi, 6),
                "robust_score": round(robust, 6),
                "dominant_class": dominant_class(df[spec.name], df["day_type"]),
                "note": spec.note,
            }
        )
    out = pd.DataFrame(rows)
    out["sort_key"] = out["robust_score"].fillna(-1.0)
    return out.sort_values(["sort_key", "full_mi"], ascending=[False, False]).drop(columns=["sort_key"])


def build_trade_stories(df: pd.DataFrame):
    trade_rows, blocked_rows = [], []
    for _, row in df.iterrows():
        viability = policy_viability(row["day_type"])
        base = {
            "ny_date": row["ny_date"].strftime("%Y-%m-%d"),
            "weekday": row["weekday"],
            "outcome_class": row["day_type"],
            "recommended_playbook": row["recommended_playbook"],
            "secondary_playbook": row["secondary_playbook"],
            "primary_open_state": row["primary_open_state"],
            "reason": row["reason_text"],
            "key_metrics": {
                "or30_width_norm": round(float(row["or30_width_norm"]), 4),
                "impulse30_norm": round(float(row["impulse30_norm"]), 4),
                "rotation_30": int(row["rotation_30"]),
                "london_extreme_sweep_norm": round(float(row["london_extreme_sweep_norm"]), 4),
                "close_to_vwap_norm": round(float(row["close_to_vwap_norm"]), 4),
                "session_efficiency": round(float(row["session_efficiency"]), 4),
            },
            "prop_viability": viability,
            "research_mode": "daytype_story_not_executed_trade",
        }
        if row["tradeable"]:
            trade_rows.append(base)
        else:
            blocked = dict(base)
            blocked["blocked_reason"] = "OPEN_NO_TRADE classification"
            blocked_rows.append(blocked)
    return trade_rows, blocked_rows


def build_taxonomy_md(df: pd.DataFrame) -> str:
    counts = df["day_type"].value_counts()
    split_counts = df.groupby(["split", "day_type"]).size().unstack(fill_value=0)
    return f"""# NY Open Outcome Taxonomy

## Scope
- Symbol: `{SYMBOL}`
- Data: `M1 + M5`
- Window: `2020-03-07 -> 2026-03-06`
- Clock anchor: **New York local time**
- Day outcome horizon: `09:30 -> 13:30 NY`

## Deterministic windows
- Pre-open context: `08:30 -> 09:29`
- Opening response window: `09:30 -> 09:59`
- Outcome evaluation window: `10:00 -> 13:29`
- London handoff context: `03:00 -> 09:29`

## Deterministic label rules
Each day receives three scores:

### 1) `OPEN_ACCEPTANCE`
`score_acceptance =`
- `|close_13:30 - open_09:30| >= 0.80 * PREOPEN_RANGE`
- `session_efficiency >= 0.22`
- `dominant_extension >= 1.2 * opposite_extension`
- `close_13:30 far from anchored VWAP (>= 0.80 * PREOPEN_RANGE)`
- `rotation_30 <= 4`

### 2) `OPEN_FAILURE`
`score_failure =`
- London extreme swept during first 30m
- two-sided post-open excursion on both sides (`up_ext >= 0.70` and `dn_ext >= 0.70`)
- close direction opposite early open-response direction
- close still far from anchored VWAP (`>= 0.80 * PREOPEN_RANGE`)
- `rotation_30 >= 4`

### 3) `OPEN_RECLAIM`
`score_reclaim =`
- two-sided post-open excursion exists
- close near anchored VWAP (`<= 0.35 * PREOPEN_RANGE`)
- `rotation_30 >= 4`
- close near OR midpoint (`<= 0.35 * PREOPEN_RANGE`)
- net close back near open (`|close_rel| <= 0.50 * PREOPEN_RANGE`)

### 4) `OPEN_NO_TRADE`
- if `max(score_acceptance, score_failure, score_reclaim) < 4`, label = `OPEN_NO_TRADE`
- otherwise choose the max-score class deterministically

## Full-sample class counts
- `OPEN_ACCEPTANCE`: **{int(counts.get(CLASS_ACCEPTANCE, 0))}**
- `OPEN_FAILURE`: **{int(counts.get(CLASS_FAILURE, 0))}**
- `OPEN_RECLAIM`: **{int(counts.get(CLASS_RECLAIM, 0))}**
- `OPEN_NO_TRADE`: **{int(counts.get(CLASS_NOTRADE, 0))}**

## Split stability
{split_counts.to_markdown()}

## Interpretation
- `OPEN_ACCEPTANCE` is the dominant directional day type.
- `OPEN_FAILURE` exists but is materially rarer.
- `OPEN_RECLAIM` is present and denser than the rare Phase 2B pattern branch.
- `OPEN_NO_TRADE` is large enough that a future router must explicitly support staying flat.
"""


def build_cluster_report(df: pd.DataFrame) -> str:
    counts = df["day_type"].value_counts().rename("days").to_frame()
    counts["pct"] = (counts["days"] / counts["days"].sum() * 100.0).round(2)
    profile = (
        df.groupby("day_type")[
            [
                "or30_width_norm",
                "impulse30_norm",
                "up_ext_norm",
                "dn_ext_norm",
                "close_to_vwap_norm",
                "close_to_mid_norm",
                "session_efficiency",
                "rotation_30",
                "london_extreme_sweep_norm",
                "spread_mean_10",
            ]
        ]
        .median()
        .round(3)
    )
    tradeable = {
        CLASS_ACCEPTANCE: "Tradeable; best fit for continuation logic.",
        CLASS_FAILURE: "Tradeable but rarer; best fit for stop-run / fade logic.",
        CLASS_RECLAIM: "Tradeable; best fit for later value/VWAP reclaim logic.",
        CLASS_NOTRADE: "Toxic / ambiguous; router should mostly stay flat.",
    }
    lines = ["# Outcome Cluster Report", "", "## Counts", counts.to_markdown(), "", "## Median intraday structure", profile.to_markdown(), "", "## Tradeable vs toxic map"]
    for k in [CLASS_ACCEPTANCE, CLASS_FAILURE, CLASS_RECLAIM, CLASS_NOTRADE]:
        lines.append(f"- `{k}`: {tradeable[k]}")
    lines += [
        "",
        "## Average structure summary",
        f"- `{CLASS_ACCEPTANCE}`: lower rotations, close stays far from VWAP/value, directional efficiency is highest.",
        f"- `{CLASS_FAILURE}`: London extreme sweep + two-sided move + opposite close; strongest stop-run signature.",
        f"- `{CLASS_RECLAIM}`: closes near VWAP and OR midpoint, with repeated open-response rotations and rebalance behavior.",
        f"- `{CLASS_NOTRADE}`: mixed / ambiguous open response; not clean continuation, not clean failure, not clean reclaim.",
    ]
    return "\n".join(lines)


def build_playbook_fit_map(df: pd.DataFrame) -> str:
    counts = df["day_type"].value_counts()
    table = pd.DataFrame(
        [
            {
                "day_type": CLASS_ACCEPTANCE,
                "days": int(counts.get(CLASS_ACCEPTANCE, 0)),
                "best_playbook": "ACCEPTANCE trader",
                "secondary": "NO_TRADE conservative",
                "toxic_playbook": "FAILURE_FADE",
                "why": "One-sided close far from VWAP with contained early rotations.",
            },
            {
                "day_type": CLASS_FAILURE,
                "days": int(counts.get(CLASS_FAILURE, 0)),
                "best_playbook": "FAILURE_FADE trader",
                "secondary": "POST_OPEN_RECLAIM trader",
                "toxic_playbook": "ACCEPTANCE trader",
                "why": "Early sweep/acceptance fails and the session closes back through value.",
            },
            {
                "day_type": CLASS_RECLAIM,
                "days": int(counts.get(CLASS_RECLAIM, 0)),
                "best_playbook": "POST_OPEN_RECLAIM trader",
                "secondary": "NO_TRADE conservative",
                "toxic_playbook": "OPEN_ACCEPTANCE trader",
                "why": "Session rotates and rebalances around VWAP / OR midpoint.",
            },
            {
                "day_type": CLASS_NOTRADE,
                "days": int(counts.get(CLASS_NOTRADE, 0)),
                "best_playbook": "NO_TRADE",
                "secondary": "None",
                "toxic_playbook": "All active playbooks",
                "why": "Ambiguous open response; forcing entries is structurally low quality.",
            },
        ]
    )
    return "# Playbook Fit Map\n\n" + table.to_markdown(index=False)


def build_prop_viability_map() -> str:
    table = pd.DataFrame(
        [
            {
                "day_type": CLASS_ACCEPTANCE,
                "ftmo_standard": "Medium-Low",
                "ftmo_swing": "Medium",
                "the5ers_highstakes": "Medium",
                "note": "Earliest entries cluster around 10:00 NY; highest conflict with restricted-news / early-open spread spikes.",
            },
            {
                "day_type": CLASS_FAILURE,
                "ftmo_standard": "Medium",
                "ftmo_swing": "Medium-High",
                "the5ers_highstakes": "Medium",
                "note": "Usually confirmation-driven after the initial sweep, so more portable than pure open chase.",
            },
            {
                "day_type": CLASS_RECLAIM,
                "ftmo_standard": "Medium-High",
                "ftmo_swing": "High",
                "the5ers_highstakes": "Medium-High",
                "note": "Later/lower-intensity structure is most compatible with strict prop execution behavior.",
            },
            {
                "day_type": CLASS_NOTRADE,
                "ftmo_standard": "High",
                "ftmo_swing": "High",
                "the5ers_highstakes": "High",
                "note": "Flat is the safest prop action.",
            },
        ]
    )
    intro = """# Prop Viability Map

This is an **estimate only**.

- Historical calendar coverage for `2020-03-07 -> 2026-03-06` is still incomplete.
- Therefore this file does **not** claim FTMO / The5ers validation.
- Viability is based on structural timing, spread intensity, and official rule direction:
  - FTMO restricted-news windows remain a material issue for any open-driven playbook.
  - The5ers High Stakes also penalizes risky execution patterns (latency/news abuse/HFT-like behavior), so M5 closed-bar + low modification intensity remains preferable.
"""
    return intro + "\n\n" + table.to_markdown(index=False)


def build_daytype_gallery(df: pd.DataFrame) -> str:
    lines = ["# Daytype Gallery", ""]
    for label in [CLASS_ACCEPTANCE, CLASS_FAILURE, CLASS_RECLAIM, CLASS_NOTRADE]:
        sample = prototypical_rows(df, label, n=3)
        lines.append(f"## {label}")
        if sample.empty:
            lines.append("- No sample available")
            lines.append("")
            continue
        show = sample[
            [
                "ny_date",
                "weekday",
                "split",
                "recommended_playbook",
                "or30_width_norm",
                "impulse30_norm",
                "rotation_30",
                "london_extreme_sweep_norm",
                "close_to_vwap_norm",
                "session_efficiency",
            ]
        ].copy()
        show["ny_date"] = show["ny_date"].dt.strftime("%Y-%m-%d")
        lines.append(show.to_markdown(index=False))
        lines.append("")
    return "\n".join(lines)


def build_summary_json(df: pd.DataFrame, scorecard: pd.DataFrame, terminal) -> dict:
    counts = df["day_type"].value_counts().to_dict()
    top_features = scorecard[scorecard["supported"]].head(8)[["feature", "family", "robust_score"]].to_dict("records")
    return {
        "symbol": SYMBOL,
        "window_utc": [UTC_FROM.isoformat(), UTC_TO.isoformat()],
        "days_labeled": int(len(df)),
        "class_counts": counts,
        "top_features": top_features,
        "recommendation": "Proceed to a regime-router research lane; do not claim deployability or prop-safe validity.",
        "calendar_status": "incomplete_historical_coverage",
        "mt5_terminal": {
            "company": getattr(terminal, "company", ""),
            "path": getattr(terminal, "path", ""),
            "data_path": getattr(terminal, "data_path", ""),
            "maxbars": getattr(terminal, "maxbars", None),
        },
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    m1, m5, terminal = load_mt5_rates(SYMBOL)
    day_df = build_day_feature_table(m1, m5)
    scorecard = build_feature_scorecard(day_df)
    trade_rows, blocked_rows = build_trade_stories(day_df)

    save_df = day_df.copy()
    save_df["ny_date"] = save_df["ny_date"].dt.strftime("%Y-%m-%d")
    save_df.to_csv(OUT_DIR / "ny_open_day_features.csv", index=False)
    scorecard.to_csv(OUT_DIR / "regime_feature_scorecard.csv", index=False)

    write_text(OUT_DIR / "ny_open_outcome_taxonomy.md", build_taxonomy_md(day_df))
    write_text(OUT_DIR / "outcome_cluster_report.md", build_cluster_report(day_df))
    write_text(OUT_DIR / "playbook_fit_map.md", build_playbook_fit_map(day_df))
    write_text(OUT_DIR / "prop_viability_map.md", build_prop_viability_map())
    write_text(OUT_DIR / "daytype_gallery.md", build_daytype_gallery(day_df))
    write_jsonl(OUT_DIR / "trade_story.jsonl", trade_rows)
    write_jsonl(OUT_DIR / "blocked_signal_story.jsonl", blocked_rows)
    write_json(OUT_DIR / "phase3a_prep_summary.json", build_summary_json(day_df, scorecard, terminal))

    print(f"Phase 3A prep complete -> {OUT_DIR}")
    print(day_df["day_type"].value_counts().to_string())
    print(scorecard[scorecard["supported"]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
