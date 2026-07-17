"""
signal.py — Signal engine MONITOR MODE theo spec v3 §5 (Variant A).
KHÔNG đặt lệnh. Chỉ tính: có signal không, hướng, SL/TP/size đề xuất, lý do chặn.
Execution live để Phase 3/4 (Python MT5 API -> MQL5 + parity §11.3).
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import math
import numpy as np
import pandas as pd

from features.gates import GateReport


@dataclass
class SignalPlan:
    symbol: str
    time: str
    direction: str            # LONG | SHORT | NONE
    z: float
    entry_ref: float          # open bar kế = giá tham chiếu (monitor: close bar đóng)
    sl: float
    tp: float
    tp_binding: str           # "TP_cap" | "TP_mean"
    r_per_unit: float         # khoảng R theo đơn vị giá
    lots: float
    effective_time_stop_bars: int
    est_swap_per_night_usd: float
    est_swap_per_night_R: float
    blockers: list[str]

    def to_dict(self):
        return asdict(self)


def evaluate_signal(symbol: str, feats: pd.DataFrame, gates: GateReport,
                    params: dict, costs: dict,
                    account_equity: float = 10_000.0) -> SignalPlan:
    p, c = params, costs[symbol]
    last = feats.iloc[-1]
    z = float(last["z"]) if last["z"] == last["z"] else 0.0
    Z = p["alpha"]["Z_entry"]["default"]

    direction = "NONE"
    if z <= -Z:
        direction = "LONG"
    elif z >= Z:
        direction = "SHORT"

    blockers = [g.name for g in gates.gates if not g.passed]
    if direction == "NONE":
        blockers.insert(0, f"|z|={abs(z):.2f} < Z_entry={Z}")

    # --- SL/TP theo §5.2–5.3 (đóng băng mu_e, sig_e tại entry) ---
    price = float(last["close"])          # monitor mode: tham chiếu close bar đóng
    atr = float(last["atr14"])
    K = p["exits"]["K_sl_atr"]["default"]
    sgn = 1.0 if direction == "LONG" else -1.0
    sl = price - sgn * K * atr
    R = abs(price - sl)

    mu_e, sig_e = float(last["mu"]), float(last["sigma"])
    buf = p["exits"]["tp_buffer_sigma"]["default"]
    cap = p["exits"]["tp_cap_R"]["default"]
    tp_mean = mu_e - sgn * buf * sig_e
    tp_cap = price + sgn * cap * R
    # TP = mức GẦN entry hơn; validity: TP_mean phải ở phía có lợi
    tp_mean_valid = (tp_mean - price) * sgn > 0
    if tp_mean_valid and abs(tp_mean - price) < abs(tp_cap - price):
        tp, binding = tp_mean, "TP_mean"
    else:
        tp, binding = tp_cap, "TP_cap"

    # --- Sizing §8: lots = risk_$ / (SL_dist_giá x contract_size) ---
    risk_usd = account_equity * p["risk"]["per_trade_pct"]["default"] / 100.0
    contract = c["contract_size"]
    lots_raw = risk_usd / (R * contract) if R > 0 else 0.0
    lots = math.floor(lots_raw * 100) / 100.0        # floor theo step 0.01
    if lots < 0.01:
        blockers.append("size < min lot 0.01 (§8: bỏ signal)")

    # --- effective time-stop = min(ceil(k_ts x HL), bars đến night-cap) §5.3 ---
    hl = float(last["half_life"]) if last["half_life"] == last["half_life"] else np.nan
    k_ts = p["exits"]["k_ts"]["default"]
    nights = p["exits"]["night_cap"][symbol]
    bars_to_cap = nights * 24                        # xấp xỉ H1; EA thật đếm rollover thực
    ts = int(min(math.ceil(k_ts * hl), bars_to_cap)) if hl == hl else 0

    # --- swap ước tính ---
    sw = c["swap_per_lot_per_night"]["long" if direction != "SHORT" else "short"]
    est_swap = sw * lots
    est_swap_R = est_swap / risk_usd if risk_usd > 0 else 0.0

    return SignalPlan(
        symbol=symbol,
        time=str(last["time"]),
        direction=direction if not blockers else f"{direction} (BLOCKED)" if direction != "NONE" else "NONE",
        z=round(z, 3),
        entry_ref=round(price, 5),
        sl=round(sl, 5),
        tp=round(tp, 5),
        tp_binding=binding,
        r_per_unit=round(R, 5),
        lots=lots,
        effective_time_stop_bars=ts,
        est_swap_per_night_usd=round(est_swap, 2),
        est_swap_per_night_R=round(est_swap_R, 4),
        blockers=blockers,
    )
