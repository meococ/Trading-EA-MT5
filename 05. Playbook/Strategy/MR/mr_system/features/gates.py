"""
gates.py — Regime/session/spread/HL gates theo spec v3 §3–§4.
Trả về GateReport: từng gate (pass, value, threshold) — dashboard vẽ bảng đèn,
signal engine AND tất cả. Mọi giá trị tính trên bar ĐÃ ĐÓNG (t-1 so với decision).
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
import pandas as pd

from features.indicators import atr_wilder, adx_wilder, detrend, rolling_half_life, atr_percentile


@dataclass
class Gate:
    name: str
    passed: bool
    value: float
    threshold: str


@dataclass
class GateReport:
    gates: list[Gate] = field(default_factory=list)

    def add(self, name, passed, value, threshold):
        self.gates.append(Gate(name, bool(passed), float(value) if value == value else float("nan"), threshold))

    @property
    def all_pass(self) -> bool:
        return all(g.passed for g in self.gates)

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame([{"gate": g.name, "pass": g.passed, "value": g.value,
                              "threshold": g.threshold} for g in self.gates])


def compute_features(df_h1: pd.DataFrame, W: int) -> pd.DataFrame:
    """Tính toàn bộ feature trên H1 (bar đóng)."""
    out = df_h1.copy()
    out["atr14"] = atr_wilder(out, 14)
    out["adx14"] = adx_wilder(out, 14)
    D, sigma, z = detrend(out["close"], W)
    out["D"], out["sigma"], out["z"] = D, sigma, z
    out["mu"] = out["close"] - D
    lam, hl = rolling_half_life(D, W)
    out["lambda"], out["half_life"] = lam, hl
    out["atr_pctile"] = atr_percentile(out["atr14"], 250)
    out["sigma_over_atr"] = out["sigma"] / out["atr14"]   # deliverable Phase 1 (§5.3)
    return out


def evaluate_gates(symbol: str, feats_h1: pd.DataFrame, df_h4: pd.DataFrame,
                   params: dict, costs: dict,
                   now_utc: pd.Timestamp | None = None,
                   current_spread_price: float | None = None) -> GateReport:
    """Đánh giá gates tại bar H1 ĐÓNG cuối cùng. now_utc để test session độc lập."""
    p = params
    last = feats_h1.iloc[-1]
    now = now_utc or pd.Timestamp.utcnow()
    rep = GateReport()

    # 1. ADX H1
    thr = p["regime_gates"]["adx_h1_max"]["default"]
    rep.add("ADX H1 < max", last["adx14"] < thr, last["adx14"], f"< {thr}")

    # 2. ADX H4 (bar H4 đã đóng gần nhất)
    thr4 = p["regime_gates"]["adx_h4_max"]["default"]
    adx4 = adx_wilder(df_h4, 14).iloc[-1]
    rep.add("ADX H4 < max", adx4 < thr4, adx4, f"< {thr4}")

    # 3. ATR percentile band
    lo, hi = p["regime_gates"]["atr_pctile_band"]["default"]
    rep.add("ATR pctile in band", lo <= last["atr_pctile"] <= hi,
            last["atr_pctile"], f"[{lo},{hi}]")

    # 4. Half-life gate (lambda < 0 đã bao trong HL=NaN nếu >=0)
    lo_hl, hi_hl = p["alpha"]["hl_gate_bars"][symbol]["default"]
    hl = last["half_life"]
    rep.add("Half-life in gate", (hl == hl) and (lo_hl <= hl <= hi_hl),
            hl, f"[{lo_hl},{hi_hl}] bars")

    # 5. Session (UTC, nửa mở) — entry only
    s = p["sessions_utc"][symbol]
    rep.add("Session UTC", s["start"] <= now.hour < s["end"],
            now.hour, f"[{s['start']},{s['end']})h")

    # 6. Spread guard
    mult = p["regime_gates"]["spread_guard_mult_p75"]["default"]
    c = costs[symbol]
    if symbol == "XAUUSD":
        p75 = c["spread"]["p75"]                      # USD/oz — spread_price cùng đơn vị giá
        cur = current_spread_price if current_spread_price is not None else p75
    else:
        p75 = c["spread"]["p75"] * c["pip"]           # pips -> giá
        cur = current_spread_price if current_spread_price is not None else p75
    rep.add("Spread <= 1.5x p75", cur <= mult * p75, cur, f"<= {mult*p75:.5f}")

    # 7. Gap guard (open bar hiện tại vs close bar trước) — dùng 2 bar đóng cuối
    gmult = p["execution"]["gap_guard_atr_mult"]["default"]
    if len(feats_h1) >= 2:
        gap = abs(feats_h1["open"].iloc[-1] - feats_h1["close"].iloc[-2])
    else:
        gap = 0.0
    rep.add("Gap < 4x ATR", gap < gmult * last["atr14"], gap, f"< {gmult}xATR")

    # 8. News window — Phase 0: stub (calendar loader chưa nối)
    rep.add("News window (stub)", True, 0, "TODO: nối economic calendar CSV")
    return rep
