#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from zoneinfo import ZoneInfo

from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

try:
    import MetaTrader5 as mt5
except ImportError as exc:
    raise SystemExit("MetaTrader5 package is required for Phase 3B router simulation.") from exc


ROOT = Path(r"02. AlphaFactory/runs/XAU_Scalp_Portfolio")
PHASE3A_DIR = ROOT / "phase3a_prep_20260308"
OUT_DIR = ROOT / "phase3b_router_20260308"
SUMMARY_PATH = OUT_DIR / "phase3b_router_summary.json"

SYMBOL = "XAUUSD"
UTC_FROM = datetime(2020, 3, 7, tzinfo=timezone.utc)
UTC_TO = datetime(2026, 3, 6, 23, 59, 59, tzinfo=timezone.utc)
FULL_START = date(2020, 3, 7)
FULL_END = date(2026, 3, 6)
SPLIT_A_END = date(2023, 3, 6)
SPLIT_B_START = date(2023, 3, 7)
START_EQUITY = 100_000.0
RISK_PCT = 0.0025
WARMUP_DAYS = 120

NY_TZ = ZoneInfo("America/New_York")
UTC_TZ = timezone.utc
LOCK_TIME = time(10, 0)
ENTRY_TIME = time(10, 5)
TIMEOUT_BARS = 12
CONF_MIN = 0.42
MARGIN_MIN = 0.08

CLASS_ACCEPTANCE = "OPEN_ACCEPTANCE"
CLASS_FAILURE = "OPEN_FAILURE"
CLASS_RECLAIM = "OPEN_RECLAIM"
CLASS_NOTRADE = "OPEN_NO_TRADE"

PLAYBOOK_ACCEPTANCE = "ACCEPTANCE"
PLAYBOOK_FAILURE = "FAILURE_FADE"
PLAYBOOK_RECLAIM = "POST_OPEN_RECLAIM"
PLAYBOOK_NO_TRADE = "NO_TRADE"

CLASS_TO_PLAYBOOK = {
    CLASS_ACCEPTANCE: PLAYBOOK_ACCEPTANCE,
    CLASS_FAILURE: PLAYBOOK_FAILURE,
    CLASS_RECLAIM: PLAYBOOK_RECLAIM,
    CLASS_NOTRADE: PLAYBOOK_NO_TRADE,
}
CLASSES = [CLASS_ACCEPTANCE, CLASS_FAILURE, CLASS_RECLAIM, CLASS_NOTRADE]
TRADEABLE_PLAYBOOKS = [PLAYBOOK_ACCEPTANCE, PLAYBOOK_FAILURE, PLAYBOOK_RECLAIM]

FEATURES = [
    "rotation_30",
    "or30_width_norm",
    "preopen_range_norm",
    "preopen_range_pct20",
    "or10_width_norm",
    "vwap_dist_30_norm",
    "impulse30_norm",
    "london_pos_at_open",
]

ROLL_WINDOWS = [
    ("ROLL_2020_2021", date(2020, 3, 7), date(2021, 3, 6)),
    ("ROLL_2021_2022", date(2021, 3, 7), date(2022, 3, 6)),
    ("ROLL_2022_2023", date(2022, 3, 7), date(2023, 3, 6)),
    ("ROLL_2023_2024", date(2023, 3, 7), date(2024, 3, 6)),
    ("ROLL_2024_2025", date(2024, 3, 7), date(2025, 3, 6)),
    ("ROLL_2025_2026", date(2025, 3, 7), date(2026, 3, 6)),
]


@dataclass
class TradeResult:
    executed: bool
    playbook: str
    side: str
    direction: int
    entry_utc: Optional[str]
    entry_ny: Optional[str]
    exit_utc: Optional[str]
    exit_ny: Optional[str]
    entry_price: float
    exit_price: float
    risk_dist: float
    target_dist: float
    spread_cost: float
    realized_r: float
    gross_r: float
    mfe_r: float
    mae_r: float
    hold_minutes: float
    exit_reason: str
    blocked_reason: str = ""

    def to_dict(self):
        return {
            "executed": self.executed,
            "playbook": self.playbook,
            "side": self.side,
            "direction": self.direction,
            "entry_utc": self.entry_utc,
            "entry_ny": self.entry_ny,
            "exit_utc": self.exit_utc,
            "exit_ny": self.exit_ny,
            "entry_price": round(float(self.entry_price), 5) if self.entry_price else 0.0,
            "exit_price": round(float(self.exit_price), 5) if self.exit_price else 0.0,
            "risk_dist": round(float(self.risk_dist), 5) if self.risk_dist else 0.0,
            "target_dist": round(float(self.target_dist), 5) if self.target_dist else 0.0,
            "spread_cost": round(float(self.spread_cost), 5) if self.spread_cost else 0.0,
            "realized_r": round(float(self.realized_r), 5),
            "gross_r": round(float(self.gross_r), 5),
            "mfe_r": round(float(self.mfe_r), 5),
            "mae_r": round(float(self.mae_r), 5),
            "hold_minutes": round(float(self.hold_minutes), 2),
            "exit_reason": self.exit_reason,
            "blocked_reason": self.blocked_reason,
        }


def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def write_jsonl(path: Path, rows: List[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_markdown_table(path: Path, rows: List[dict], headers: List[str]):
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(h, "")) for h in headers) + " |")
    write_text(path, "\n".join(lines))


def safe_div(a, b):
    return a / b if b else 0.0


def pf(values: List[float]) -> float:
    gp = sum(v for v in values if v > 0)
    gl = -sum(v for v in values if v < 0)
    return gp / gl if gl > 0 else 999.99


def top_contrib_pct(values: List[float], n: int) -> float:
    wins = sorted([v for v in values if v > 0], reverse=True)
    gp = sum(wins)
    return round(safe_div(sum(wins[:n]) * 100.0, gp), 2) if gp > 0 else 0.0


def anchored_vwap(df: pd.DataFrame) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    vol = df["tick_volume"].clip(lower=1)
    return (tp * vol).cumsum() / vol.cumsum()


def playbook_to_key(playbook: str) -> str:
    return {
        PLAYBOOK_ACCEPTANCE: "acceptance",
        PLAYBOOK_FAILURE: "failure",
        PLAYBOOK_RECLAIM: "reclaim",
    }.get(playbook, "")


def load_features() -> pd.DataFrame:
    path = PHASE3A_DIR / "ny_open_day_features.csv"
    df = pd.read_csv(path)
    df["ny_date"] = pd.to_datetime(df["ny_date"]).dt.date
    return df.sort_values("ny_date").reset_index(drop=True)


def load_mt5_rates() -> Tuple[pd.DataFrame, pd.DataFrame, float]:
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        symbol_info = mt5.symbol_info(SYMBOL)
        point = float(symbol_info.point) if symbol_info and symbol_info.point else 0.01
        m1 = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_M1, UTC_FROM, UTC_TO)
        m5 = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_M5, UTC_FROM, UTC_TO)
    finally:
        mt5.shutdown()

    if m1 is None or len(m1) == 0:
        raise RuntimeError("No M1 data returned from MT5")
    if m5 is None or len(m5) == 0:
        raise RuntimeError("No M5 data returned from MT5")

    def prep(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["utc_dt"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df["ny_dt"] = df["utc_dt"].dt.tz_convert(NY_TZ)
        df["ny_date"] = df["ny_dt"].dt.date
        df["ny_hour"] = df["ny_dt"].dt.hour
        df["ny_minute"] = df["ny_dt"].dt.minute
        df["ny_min_of_day"] = df["ny_hour"] * 60 + df["ny_minute"]
        return df.sort_values("utc_dt").reset_index(drop=True)

    return prep(pd.DataFrame(m1)), prep(pd.DataFrame(m5)), point


def build_daily_market_context(features: pd.DataFrame, m1: pd.DataFrame, m5: pd.DataFrame, point: float) -> pd.DataFrame:
    day_rows = []
    m1_groups = {d: g.reset_index(drop=True) for d, g in m1.groupby("ny_date")}
    m5_groups = {d: g.reset_index(drop=True) for d, g in m5.groupby("ny_date")}
    open_min = 9 * 60 + 30
    lock_min = 10 * 60
    entry_min = 10 * 60 + 5
    end_min = 13 * 60 + 30

    for _, row in features.iterrows():
        d = row["ny_date"]
        g1 = m1_groups.get(d)
        g5 = m5_groups.get(d)
        if g1 is None or g5 is None:
            continue
        w30 = g1[(g1["ny_min_of_day"] >= open_min) & (g1["ny_min_of_day"] < lock_min)].copy()
        post = g5[(g5["ny_min_of_day"] >= entry_min) & (g5["ny_min_of_day"] < end_min)].copy()
        entry_bar = g5[g5["ny_min_of_day"] == entry_min].copy()
        if w30.empty or entry_bar.empty:
            continue

        vwap30 = anchored_vwap(w30)
        open_price = float(w30.iloc[0]["open"])
        close30 = float(w30.iloc[-1]["close"])
        vwap30_last = float(vwap30.iloc[-1])
        sign_impulse = int(np.sign(close30 - open_price))
        sign_reclaim = -int(np.sign(close30 - vwap30_last))
        entry_row = entry_bar.iloc[0]
        day_rows.append({
            "ny_date": d,
            "open_price": open_price,
            "close30_price": close30,
            "vwap30_price": vwap30_last,
            "price_minus_vwap30": close30 - vwap30_last,
            "acceptance_dir": sign_impulse,
            "failure_dir": -sign_impulse,
            "reclaim_dir": sign_reclaim,
            "entry_utc_seed": entry_row["utc_dt"].isoformat(),
            "entry_ny_seed": entry_row["ny_dt"].isoformat(),
            "entry_price_raw": float(entry_row["open"]),
            "entry_spread_points": float(entry_row.get("spread", 0.0)),
            "bars_available": int(len(post)),
            "point": point,
        })
    return pd.DataFrame(day_rows)


def fit_predict_walk_forward(features: pd.DataFrame) -> pd.DataFrame:
    df = features.copy().sort_values("ny_date").reset_index(drop=True)
    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("logit", LogisticRegression(max_iter=2000, class_weight="balanced")),
    ])
    preds = []
    for idx in range(len(df)):
        cur = df.iloc[idx]
        train = df.iloc[:idx]
        if idx < WARMUP_DAYS or train["day_type"].nunique() < 4:
            prob_map = {c: 0.0 for c in CLASSES}
            preds.append({
                "pred_class": CLASS_NOTRADE,
                "pred_playbook": PLAYBOOK_NO_TRADE,
                "pred_conf": 0.0,
                "pred_margin": 0.0,
                "routing_reason": "WARMUP",
                **{f"prob_{c}": prob_map[c] for c in CLASSES},
            })
            continue

        x_train = train[FEATURES]
        y_train = train["day_type"]
        model.fit(x_train, y_train)
        probs = model.predict_proba(pd.DataFrame([cur[FEATURES].to_dict()]))[0]
        prob_map = dict(zip(model.classes_, probs))
        for c in CLASSES:
            prob_map.setdefault(c, 0.0)
        ranked = sorted(prob_map.items(), key=lambda kv: kv[1], reverse=True)
        top_class, top_prob = ranked[0]
        second_prob = ranked[1][1] if len(ranked) > 1 else 0.0
        margin = top_prob - second_prob
        if top_prob < CONF_MIN:
            pred_class = CLASS_NOTRADE
            reason = "LOW_CONFIDENCE"
        elif margin < MARGIN_MIN:
            pred_class = CLASS_NOTRADE
            reason = "LOW_MARGIN"
        else:
            pred_class = top_class
            reason = "CLASS_LOCKED"

        preds.append({
            "pred_class": pred_class,
            "pred_playbook": CLASS_TO_PLAYBOOK[pred_class],
            "pred_conf": float(top_prob),
            "pred_margin": float(margin),
            "routing_reason": reason,
            **{f"prob_{c}": float(prob_map[c]) for c in CLASSES},
        })
    return pd.concat([df, pd.DataFrame(preds)], axis=1)


def simulate_playbook_trade(playbook: str, day_row: pd.Series, bars: pd.DataFrame, point: float) -> TradeResult:
    if playbook == PLAYBOOK_NO_TRADE:
        return TradeResult(
            executed=False, playbook=playbook, side="FLAT", direction=0,
            entry_utc=None, entry_ny=None, exit_utc=None, exit_ny=None,
            entry_price=0.0, exit_price=0.0, risk_dist=0.0, target_dist=0.0,
            spread_cost=0.0, realized_r=0.0, gross_r=0.0, mfe_r=0.0, mae_r=0.0,
            hold_minutes=0.0, exit_reason="no_trade", blocked_reason="ROUTED_NO_TRADE"
        )

    direction = int(day_row[f"{playbook_to_key(playbook)}_dir"])
    if direction == 0:
        return TradeResult(
            executed=False, playbook=playbook, side="FLAT", direction=0,
            entry_utc=None, entry_ny=None, exit_utc=None, exit_ny=None,
            entry_price=0.0, exit_price=0.0, risk_dist=0.0, target_dist=0.0,
            spread_cost=0.0, realized_r=0.0, gross_r=0.0, mfe_r=0.0, mae_r=0.0,
            hold_minutes=0.0, exit_reason="no_trade", blocked_reason="DIRECTION_UNRESOLVED"
        )
    if bars.empty:
        return TradeResult(
            executed=False, playbook=playbook, side="FLAT", direction=0,
            entry_utc=None, entry_ny=None, exit_utc=None, exit_ny=None,
            entry_price=0.0, exit_price=0.0, risk_dist=0.0, target_dist=0.0,
            spread_cost=0.0, realized_r=0.0, gross_r=0.0, mfe_r=0.0, mae_r=0.0,
            hold_minutes=0.0, exit_reason="no_trade", blocked_reason="NO_ENTRY_BAR"
        )

    entry_bar = bars.iloc[0]
    trade_bars = bars.iloc[:TIMEOUT_BARS].copy()
    if trade_bars.empty:
        return TradeResult(
            executed=False, playbook=playbook, side="FLAT", direction=0,
            entry_utc=None, entry_ny=None, exit_utc=None, exit_ny=None,
            entry_price=0.0, exit_price=0.0, risk_dist=0.0, target_dist=0.0,
            spread_cost=0.0, realized_r=0.0, gross_r=0.0, mfe_r=0.0, mae_r=0.0,
            hold_minutes=0.0, exit_reason="no_trade", blocked_reason="NO_TRADE_WINDOW"
        )

    risk_dist = max(0.80 * float(day_row["atr14_pre_m5"]), 0.40 * float(day_row["preopen_range"]), point)
    target_dist = risk_dist
    entry_price = float(entry_bar["open"])
    spread_cost = float(entry_bar.get("spread", 0.0)) * point
    stop = entry_price - direction * risk_dist
    target = entry_price + direction * target_dist

    side = "LONG" if direction > 0 else "SHORT"
    exit_reason = "timeout"
    exit_price = float(trade_bars.iloc[-1]["close"])
    exit_utc = trade_bars.iloc[-1]["utc_dt"]
    exit_ny = trade_bars.iloc[-1]["ny_dt"]
    hold_minutes = len(trade_bars) * 5.0

    mfe = 0.0
    mae = 0.0

    for i, bar in trade_bars.iterrows():
        bar_high = float(bar["high"])
        bar_low = float(bar["low"])
        if direction > 0:
            mfe = max(mfe, (bar_high - entry_price) / risk_dist)
            mae = max(mae, (entry_price - bar_low) / risk_dist)
            stop_hit = bar_low <= stop
            target_hit = bar_high >= target
        else:
            mfe = max(mfe, (entry_price - bar_low) / risk_dist)
            mae = max(mae, (bar_high - entry_price) / risk_dist)
            stop_hit = bar_high >= stop
            target_hit = bar_low <= target

        if stop_hit and target_hit:
            exit_reason = "sl_first_same_bar"
            exit_price = stop
            exit_utc = bar["utc_dt"]
            exit_ny = bar["ny_dt"]
            hold_minutes = (i + 1) * 5.0
            break
        if stop_hit:
            exit_reason = "sl_hit"
            exit_price = stop
            exit_utc = bar["utc_dt"]
            exit_ny = bar["ny_dt"]
            hold_minutes = (i + 1) * 5.0
            break
        if target_hit:
            exit_reason = "tp_hit"
            exit_price = target
            exit_utc = bar["utc_dt"]
            exit_ny = bar["ny_dt"]
            hold_minutes = (i + 1) * 5.0
            break

    gross_r = direction * (exit_price - entry_price) / risk_dist
    realized_r = gross_r - (spread_cost / risk_dist)
    return TradeResult(
        executed=True,
        playbook=playbook,
        side=side,
        direction=direction,
        entry_utc=entry_bar["utc_dt"].isoformat(),
        entry_ny=entry_bar["ny_dt"].isoformat(),
        exit_utc=exit_utc.isoformat(),
        exit_ny=exit_ny.isoformat(),
        entry_price=entry_price,
        exit_price=exit_price,
        risk_dist=risk_dist,
        target_dist=target_dist,
        spread_cost=spread_cost,
        realized_r=realized_r,
        gross_r=gross_r,
        mfe_r=mfe,
        mae_r=mae,
        hold_minutes=hold_minutes,
        exit_reason=exit_reason,
    )


def simulate_day_playbooks(pred_df: pd.DataFrame, m5: pd.DataFrame, point: float) -> pd.DataFrame:
    m5_groups = {
        d: g[(g["ny_min_of_day"] >= 10 * 60 + 5) & (g["ny_min_of_day"] < 13 * 60 + 30)].reset_index(drop=True)
        for d, g in m5.groupby("ny_date")
    }
    rows = []
    for _, day in pred_df.iterrows():
        d = day["ny_date"]
        bars = m5_groups.get(d, pd.DataFrame())
        base = day.to_dict()
        for pb in TRADEABLE_PLAYBOOKS:
            res = simulate_playbook_trade(pb, day, bars, point)
            for k, v in res.to_dict().items():
                base[f"{pb}_{k}"] = v
        rows.append(base)
    return pd.DataFrame(rows)


def apply_router(day: pd.Series) -> dict:
    chosen = day["pred_playbook"]
    if chosen == PLAYBOOK_NO_TRADE:
        res = TradeResult(
            executed=False, playbook=PLAYBOOK_NO_TRADE, side="FLAT", direction=0,
            entry_utc=None, entry_ny=None, exit_utc=None, exit_ny=None,
            entry_price=0.0, exit_price=0.0, risk_dist=0.0, target_dist=0.0,
            spread_cost=0.0, realized_r=0.0, gross_r=0.0, mfe_r=0.0, mae_r=0.0,
            hold_minutes=0.0, exit_reason="no_trade", blocked_reason=str(day["routing_reason"])
        )
        return {"router_playbook": PLAYBOOK_NO_TRADE, **res.to_dict()}

    prefix = f"{chosen}_"
    res = {
        "executed": bool(day.get(prefix + "executed", False)),
        "playbook": chosen,
        "side": day.get(prefix + "side", ""),
        "direction": int(day.get(prefix + "direction", 0)),
        "entry_utc": day.get(prefix + "entry_utc"),
        "entry_ny": day.get(prefix + "entry_ny"),
        "exit_utc": day.get(prefix + "exit_utc"),
        "exit_ny": day.get(prefix + "exit_ny"),
        "entry_price": float(day.get(prefix + "entry_price", 0.0)),
        "exit_price": float(day.get(prefix + "exit_price", 0.0)),
        "risk_dist": float(day.get(prefix + "risk_dist", 0.0)),
        "target_dist": float(day.get(prefix + "target_dist", 0.0)),
        "spread_cost": float(day.get(prefix + "spread_cost", 0.0)),
        "realized_r": float(day.get(prefix + "realized_r", 0.0)),
        "gross_r": float(day.get(prefix + "gross_r", 0.0)),
        "mfe_r": float(day.get(prefix + "mfe_r", 0.0)),
        "mae_r": float(day.get(prefix + "mae_r", 0.0)),
        "hold_minutes": float(day.get(prefix + "hold_minutes", 0.0)),
        "exit_reason": day.get(prefix + "exit_reason", ""),
        "blocked_reason": day.get(prefix + "blocked_reason", ""),
    }
    if not res["executed"]:
        res["playbook"] = PLAYBOOK_NO_TRADE
        res["exit_reason"] = "no_trade"
        res["blocked_reason"] = res["blocked_reason"] or "PLAYBOOK_UNAVAILABLE"
        return {"router_playbook": PLAYBOOK_NO_TRADE, **res}
    return {"router_playbook": chosen, **res}


def realized_ideal_playbook(day_type: str) -> str:
    return CLASS_TO_PLAYBOOK.get(day_type, PLAYBOOK_NO_TRADE)


def build_router_frame(sim_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in sim_df.iterrows():
        router = apply_router(row)
        ideal_pb = realized_ideal_playbook(str(row["day_type"]))
        ideal_r = 0.0 if ideal_pb == PLAYBOOK_NO_TRADE else float(row.get(f"{ideal_pb}_realized_r", 0.0))
        chosen_r = float(router["realized_r"])
        rows.append({
            **row.to_dict(),
            **router,
            "ideal_playbook": ideal_pb,
            "ideal_realized_r": ideal_r,
            "misclass_cost_r": round(float(ideal_r - chosen_r), 5),
            "is_unknown_state": bool(row["pred_playbook"] == PLAYBOOK_NO_TRADE),
        })
    return pd.DataFrame(rows)


def equity_metrics_from_frame(df: pd.DataFrame, r_col: str, exec_col: str, hold_col: str) -> dict:
    if df.empty:
        return {
            "trades": 0, "net_r": 0.0, "pf": 0.0, "dd": 0.0,
            "avg_hold": 0.0, "median_hold": 0.0, "p95_hold": 0.0,
            "top5": 0.0, "top10": 0.0, "worst_day": 0.0, "worst_5day": 0.0,
        }

    trades = df[df[exec_col]].copy()
    r_vals = trades[r_col].astype(float).tolist()
    equity = START_EQUITY
    peak = START_EQUITY
    max_dd = 0.0
    ordered = df.sort_values("ny_date")
    for _, row in ordered.iterrows():
        if bool(row[exec_col]):
            equity += equity * RISK_PCT * float(row[r_col])
        peak = max(peak, equity)
        max_dd = max(max_dd, safe_div(peak - equity, peak) * 100.0 if peak else 0.0)

    holds = trades[hold_col].astype(float) if len(trades) else pd.Series(dtype=float)
    by_day = trades.groupby("ny_date")[r_col].sum() if len(trades) else pd.Series(dtype=float)
    worst_day = float(by_day.min()) if not by_day.empty else 0.0
    worst_5 = float(by_day.sort_index().rolling(5).sum().min()) if len(by_day) >= 5 else 0.0
    return {
        "trades": int(len(trades)),
        "net_r": round(float(sum(r_vals)), 4),
        "pf": round(float(pf(r_vals)), 4),
        "dd": round(float(max_dd), 2),
        "avg_hold": round(float(holds.mean()), 2) if len(holds) else 0.0,
        "median_hold": round(float(holds.median()), 2) if len(holds) else 0.0,
        "p95_hold": round(float(holds.quantile(0.95)), 2) if len(holds) else 0.0,
        "top5": top_contrib_pct(r_vals, 5),
        "top10": top_contrib_pct(r_vals, 10),
        "worst_day": round(worst_day, 4),
        "worst_5day": round(worst_5, 4),
    }


def strategy_frame(router_df: pd.DataFrame, strategy: str) -> pd.DataFrame:
    df = router_df.copy()
    if strategy == "ROUTER":
        df["strategy_executed"] = df["executed"].astype(bool)
        df["strategy_r"] = df["realized_r"].astype(float)
        df["strategy_hold"] = df["hold_minutes"].astype(float)
        df["strategy_playbook"] = df["router_playbook"]
    else:
        prefix = f"{strategy}_"
        df["strategy_executed"] = df[f"{prefix}executed"].astype(bool)
        df["strategy_r"] = df[f"{prefix}realized_r"].astype(float)
        df["strategy_hold"] = df[f"{prefix}hold_minutes"].astype(float)
        df["strategy_playbook"] = strategy
    return df


def calc_strategy_metrics(df: pd.DataFrame) -> dict:
    return equity_metrics_from_frame(df, "strategy_r", "strategy_executed", "strategy_hold")


def window_slice(df: pd.DataFrame, start_d: date, end_d: date) -> pd.DataFrame:
    return df[(df["ny_date"] >= start_d) & (df["ny_date"] <= end_d)].copy()


def rolling_summary(df: pd.DataFrame) -> Tuple[List[dict], int, float]:
    rows = []
    for name, start_d, end_d in ROLL_WINDOWS:
        w = window_slice(df, start_d, end_d)
        m = calc_strategy_metrics(w)
        rows.append({"window": name, "from": str(start_d), "to": str(end_d), **m})
    profitable = int(sum(1 for r in rows if r["pf"] > 1.0 and r["net_r"] > 0))
    avg_pf = round(float(pd.Series([r["pf"] for r in rows]).mean()), 4) if rows else 0.0
    return rows, profitable, avg_pf


def confusion_counts(df: pd.DataFrame) -> pd.DataFrame:
    eval_df = df[df["routing_reason"] != "WARMUP"].copy()
    if eval_df.empty:
        return pd.DataFrame()
    return pd.crosstab(eval_df["pred_class"], eval_df["day_type"], dropna=False)


def classify_confidence_bin(x: float) -> str:
    if x < 0.42:
        return "<0.42"
    if x < 0.50:
        return "0.42-0.50"
    if x < 0.60:
        return "0.50-0.60"
    return ">=0.60"


def build_classification_audit(df: pd.DataFrame, out_dir: Path):
    eval_df = df[df["routing_reason"] != "WARMUP"].copy()
    conf = confusion_counts(df)
    lines = [
        "# Classification quality audit",
        "",
        "## Anti-leakage lock",
        "- Lock time: **10:00 New York local**",
        "- Inputs: Phase 3A top-stable features available by or before lock time.",
        "- Unknown-state rule: route to `OPEN_NO_TRADE` if `top_prob < 0.42` or `margin < 0.08`.",
        "",
        "## Confusion-style matrix (predicted vs realized)",
        "",
        conf.to_markdown() if not conf.empty else "_No evaluable rows_",
        "",
    ]
    class_split = df.groupby(["split", "pred_class"]).size().unstack(fill_value=0)
    lines.extend([
        "## Predicted class frequency by split",
        "",
        class_split.to_markdown(),
        "",
        f"- Predicted `OPEN_NO_TRADE` days: **{int((df['pred_class'] == CLASS_NOTRADE).sum())} / {len(df)}**",
        f"- Evaluated accuracy (excluding warmup rows): **{safe_div(((eval_df['pred_class'] == eval_df['day_type']).sum()) * 100.0, len(eval_df)):.2f}%**",
    ])
    write_text(out_dir / "classification_quality_audit.md", "\n".join(lines))

    bins = df.copy()
    bins["conf_bin"] = bins["pred_conf"].apply(classify_confidence_bin)
    rows = []
    for b, g in bins[bins["routing_reason"] != "WARMUP"].groupby("conf_bin"):
        rows.append({
            "conf_bin": b,
            "days": int(len(g)),
            "accuracy_pct": round(safe_div(((g["pred_class"] == g["day_type"]).sum()) * 100.0, len(g)), 2),
            "avg_margin": round(float(g["pred_margin"].mean()), 4),
            "no_trade_pct": round(safe_div(((g["pred_class"] == CLASS_NOTRADE).sum()) * 100.0, len(g)), 2),
        })
    pd.DataFrame(rows).to_csv(out_dir / "confidence_distribution.csv", index=False)
    lines = [
        "# Confidence distribution report",
        "",
        pd.DataFrame(rows).to_markdown(index=False) if rows else "_No rows_",
    ]
    write_text(out_dir / "confidence_distribution_report.md", "\n".join(lines))


def build_no_trade_value_audit(router_df: pd.DataFrame, out_dir: Path):
    nt = router_df[router_df["router_playbook"] == PLAYBOOK_NO_TRADE].copy()
    rows = []
    for pb in TRADEABLE_PLAYBOOKS:
        forced = nt[f"{pb}_realized_r"].astype(float)
        rows.append({
            "forced_playbook": pb,
            "days": int(len(nt)),
            "forced_net_r": round(float(forced.sum()), 4),
            "forced_pf": round(float(pf(forced.tolist())), 4) if len(nt) else 0.0,
            "loss_days_pct": round(safe_div((forced < 0).sum() * 100.0, len(nt)), 2) if len(nt) else 0.0,
            "avg_r_per_day": round(float(forced.mean()), 4) if len(nt) else 0.0,
        })
    dist = nt["day_type"].value_counts().to_dict()
    lines = [
        "# NO_TRADE value audit",
        "",
        f"- Predicted `OPEN_NO_TRADE` days: **{len(nt)}**",
        f"- Realized class mix inside predicted `NO_TRADE`: `{dist}`",
        f"- Tradeable days routed flat: **{int((nt['day_type'] != CLASS_NOTRADE).sum())}**",
        "",
        pd.DataFrame(rows).to_markdown(index=False),
    ]
    write_text(out_dir / "no_trade_value_audit.md", "\n".join(lines))


def build_misclassification_audit(router_df: pd.DataFrame, out_dir: Path):
    rows = []
    cases = [
        (CLASS_ACCEPTANCE, PLAYBOOK_FAILURE, "ACCEPTANCE day -> FAILURE playbook"),
        (CLASS_FAILURE, PLAYBOOK_ACCEPTANCE, "FAILURE day -> ACCEPTANCE playbook"),
        ("TRADEABLE_TO_NO_TRADE", PLAYBOOK_NO_TRADE, "Tradeable day -> NO_TRADE"),
        (CLASS_NOTRADE, "TRADE_FORCED", "NO_TRADE day -> forced trade"),
    ]
    tradeable_classes = {CLASS_ACCEPTANCE, CLASS_FAILURE, CLASS_RECLAIM}
    for realized, chosen, label in cases:
        if realized == "TRADEABLE_TO_NO_TRADE":
            sub = router_df[(router_df["day_type"].isin(tradeable_classes)) & (router_df["router_playbook"] == PLAYBOOK_NO_TRADE)]
        elif chosen == "TRADE_FORCED":
            sub = router_df[(router_df["day_type"] == CLASS_NOTRADE) & (router_df["router_playbook"] != PLAYBOOK_NO_TRADE)]
        else:
            sub = router_df[(router_df["day_type"] == realized) & (router_df["router_playbook"] == chosen)]
        rows.append({
            "case": label,
            "days": int(len(sub)),
            "router_net_r": round(float(sub["realized_r"].sum()), 4),
            "ideal_net_r": round(float(sub["ideal_realized_r"].sum()), 4),
            "cost_r": round(float(sub["misclass_cost_r"].sum()), 4),
            "avg_cost_r": round(float(sub["misclass_cost_r"].mean()), 4) if len(sub) else 0.0,
        })
    write_text(out_dir / "misclassification_cost_audit.md", "# Misclassification cost audit\n\n" + pd.DataFrame(rows).to_markdown(index=False))


def build_playbook_specs(out_dir: Path):
    lines = [
        "# Playbook prototype specs",
        "",
        "- Lock time: **10:00 NY local**",
        "- Entry time: **10:05 NY local**",
        "- Shared stop: `max(0.80 * ATR14_pre_M5, 0.40 * preopen_range, point)`",
        "- Shared target: `1.0R`",
        "- Shared timeout: `12` M5 bars (60 minutes)",
        "- Same-bar SL/TP collision rule: **SL first**",
        "- Cost model: subtract **1x entry spread** from all trades",
        "- No trailing, no partials, no playbook-specific exits",
        "",
        f"- `{PLAYBOOK_ACCEPTANCE}` direction = sign(close_10:00 - open_09:30)",
        f"- `{PLAYBOOK_FAILURE}` direction = opposite of first-30m impulse",
        f"- `{PLAYBOOK_RECLAIM}` direction = back toward anchored 09:30-10:00 VWAP",
        f"- `{PLAYBOOK_NO_TRADE}` = flat",
    ]
    write_text(out_dir / "playbook_prototype_specs.md", "\n".join(lines))


def build_trade_stories(router_df: pd.DataFrame, out_dir: Path):
    trade_rows = []
    blocked_rows = []
    for _, r in router_df.iterrows():
        story = {
            "ny_date": str(r["ny_date"]),
            "pred_class": r["pred_class"],
            "realized_day_type": r["day_type"],
            "router_playbook": r["router_playbook"],
            "ideal_playbook": r["ideal_playbook"],
            "confidence": round(float(r["pred_conf"]), 4),
            "margin": round(float(r["pred_margin"]), 4),
            "routing_reason": r["routing_reason"],
            "probabilities": {c: round(float(r[f"prob_{c}"]), 4) for c in CLASSES},
            "feature_snapshot": {f: (round(float(r[f]), 4) if pd.notna(r[f]) else None) for f in FEATURES},
            "anti_leakage": {"lock_time_ny": "10:00", "entry_time_ny": "10:05", "pre_10_only": True},
            "misclass_cost_r": round(float(r["misclass_cost_r"]), 4),
        }
        if bool(r["executed"]):
            trade_rows.append({
                **story,
                "entry_utc": r["entry_utc"],
                "entry_ny": r["entry_ny"],
                "exit_utc": r["exit_utc"],
                "exit_ny": r["exit_ny"],
                "side": r["side"],
                "realized_r": round(float(r["realized_r"]), 4),
                "gross_r": round(float(r["gross_r"]), 4),
                "mfe_r": round(float(r["mfe_r"]), 4),
                "mae_r": round(float(r["mae_r"]), 4),
                "hold_minutes": round(float(r["hold_minutes"]), 2),
                "exit_reason": r["exit_reason"],
            })
        else:
            blocked_rows.append({
                **story,
                "blocked_reason": r["blocked_reason"] or r["routing_reason"],
                "counterfactual_acceptance_r": round(float(r[f"{PLAYBOOK_ACCEPTANCE}_realized_r"]), 4),
                "counterfactual_failure_r": round(float(r[f"{PLAYBOOK_FAILURE}_realized_r"]), 4),
                "counterfactual_reclaim_r": round(float(r[f"{PLAYBOOK_RECLAIM}_realized_r"]), 4),
            })
    write_jsonl(out_dir / "trade_story.jsonl", trade_rows)
    write_jsonl(out_dir / "blocked_signal_story.jsonl", blocked_rows)


def build_router_summary(router_metrics: dict, baseline_rows: List[dict], out_dir: Path):
    lines = [
        "# Router simulation summary",
        "",
        "- Offline regime router only. No live router, no basket, no deployability claim.",
        "- Decision lock: **10:00 New York local**; entry: **10:05 NY**.",
        "- Anti-leakage enforced: only lock-time features available by 10:00 are used.",
        "- Unknown-state rule routes weak/close scores to `OPEN_NO_TRADE`.",
        "",
        "## Router headline",
        f"- Trades: **{router_metrics['trades']}**",
        f"- Net R: **{router_metrics['net_r']}**",
        f"- PF: **{router_metrics['pf']}**",
        f"- DD: **{router_metrics['dd']}%**",
        f"- Avg / Median / P95 hold: **{router_metrics['avg_hold']} / {router_metrics['median_hold']} / {router_metrics['p95_hold']} min**",
        f"- Top5 / Top10 contribution: **{router_metrics['top5']}% / {router_metrics['top10']}%**",
        "",
        "## Router vs single-playbook baselines",
        "",
        pd.DataFrame(baseline_rows).to_markdown(index=False),
    ]
    write_text(out_dir / "router_simulation_summary.md", "\n".join(lines))


def strategy_result_rows(router_df: pd.DataFrame) -> Tuple[List[dict], pd.DataFrame]:
    rows = []
    rolling_all = []
    for name, strategy in [
        ("ROUTER", "ROUTER"),
        ("ALWAYS_ACCEPTANCE", PLAYBOOK_ACCEPTANCE),
        ("ALWAYS_FAILURE", PLAYBOOK_FAILURE),
        ("ALWAYS_RECLAIM", PLAYBOOK_RECLAIM),
    ]:
        sdf = strategy_frame(router_df, strategy)
        full = calc_strategy_metrics(sdf)
        split_a = calc_strategy_metrics(window_slice(sdf, FULL_START, SPLIT_A_END))
        split_b = calc_strategy_metrics(window_slice(sdf, SPLIT_B_START, FULL_END))
        rolling_rows, profitable, avg_pf = rolling_summary(sdf)
        rows.append({
            "strategy": name,
            "trades": full["trades"],
            "net_r": full["net_r"],
            "pf": full["pf"],
            "dd": full["dd"],
            "splitA_pf": split_a["pf"],
            "splitA_dd": split_a["dd"],
            "splitB_pf": split_b["pf"],
            "splitB_dd": split_b["dd"],
            "rolling_profitable": f"{profitable}/{len(ROLL_WINDOWS)}",
            "rolling_avg_pf": avg_pf,
            "avg_hold": full["avg_hold"],
            "median_hold": full["median_hold"],
            "p95_hold": full["p95_hold"],
            "top5": full["top5"],
            "top10": full["top10"],
            "worst_day": full["worst_day"],
            "worst_5day": full["worst_5day"],
        })
        for rr in rolling_rows:
            rolling_all.append({"strategy": name, **rr})
    return rows, pd.DataFrame(rolling_all)


def build_split_stability_report(result_rows: List[dict], rolling_df: pd.DataFrame, out_dir: Path):
    lines = [
        "# Split stability router report",
        "",
        "## Full / split A / split B",
        "",
        pd.DataFrame(result_rows).to_markdown(index=False),
        "",
        "## Rolling 12-month windows",
        "",
        rolling_df.to_markdown(index=False),
    ]
    write_text(out_dir / "split_stability_router_report.md", "\n".join(lines))


def build_pathless_realism_note(out_dir: Path):
    lines = [
        "# Realism feasibility note",
        "",
        "- Phase 3B is offline simulation only; no MT5 tester execution realism was run here.",
        "- Neutral spread friction was charged explicitly.",
        "- Any future live-router phase still needs tester real-ticks / delay validation.",
    ]
    write_text(out_dir / "realism_feasibility_note.md", "\n".join(lines))


def update_strategy_log(out_dir: Path, best_row: dict):
    log_path = Path(r"02. AlphaFactory/STRATEGY_LOG.md")
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "",
        f"### XSP_PHASE3B_OFFLINE_ROUTER_SIM ({stamp})",
        f"- Run folder: `{out_dir.as_posix()}`",
        "- Router design: offline only, lock at `10:00 NY`, enter at `10:05 NY`, unknown-state => `OPEN_NO_TRADE`.",
        f"- Router headline: trades `{best_row['trades']}`, PF `{best_row['pf']}`, DD `{best_row['dd']}%`, splitB PF `{best_row['splitB_pf']}`.",
        "- Purpose: test whether NY-open regime selection improves structure versus single-playbook prototypes before any live router implementation.",
        "- Constraint note: no deployability claim; full historical news calendar still missing.",
    ]
    with log_path.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    features = load_features()
    m1, m5, point = load_mt5_rates()
    day_ctx = build_daily_market_context(features, m1, m5, point)
    df = features.merge(day_ctx, on="ny_date", how="inner").sort_values("ny_date").reset_index(drop=True)
    pred = fit_predict_walk_forward(df)
    sim = simulate_day_playbooks(pred, m5, point)
    router_df = build_router_frame(sim)

    result_rows, rolling_df = strategy_result_rows(router_df)
    pd.DataFrame(result_rows).to_csv(OUT_DIR / "router_vs_single_playbook.csv", index=False)
    rolling_df.to_csv(OUT_DIR / "rolling_oos_router_vs_single.csv", index=False)

    router_metrics = next(r for r in result_rows if r["strategy"] == "ROUTER")
    build_router_summary(router_metrics, result_rows, OUT_DIR)
    build_classification_audit(router_df, OUT_DIR)
    build_misclassification_audit(router_df, OUT_DIR)
    build_no_trade_value_audit(router_df, OUT_DIR)
    build_playbook_specs(OUT_DIR)
    build_trade_stories(router_df, OUT_DIR)
    build_split_stability_report(result_rows, rolling_df, OUT_DIR)
    build_pathless_realism_note(OUT_DIR)

    summary = {
        "lock_time_ny": "10:00",
        "entry_time_ny": "10:05",
        "features": FEATURES,
        "confidence_rule": {"top_prob_min": CONF_MIN, "margin_min": MARGIN_MIN, "warmup_days": WARMUP_DAYS},
        "strategies": result_rows,
    }
    write_json(SUMMARY_PATH, summary)
    update_strategy_log(OUT_DIR, router_metrics)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
