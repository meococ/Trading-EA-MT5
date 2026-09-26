"""order_cache.py - persist generated pending orders per (sym,cfg,window)."""
import os

import pandas as pd

LANE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(LANE, "out", "sigs")


def save_orders(sym, cfg_id, window, orders):
    os.makedirs(CACHE_DIR, exist_ok=True)
    rows = [{"t": o["t"], "dir": o["dir"], "entry": o["entry"],
             "sl": o["sl"], "tp": o["tp"], "expiry_ctm": o["expiry_ctm"],
             **{f"m_{k}": v for k, v in o["meta"].items()}}
            for o in orders]
    df = pd.DataFrame(rows)
    path = _path(sym, cfg_id, window)
    df.to_parquet(path)
    return path


def load_orders(sym, cfg_id, window):
    path = _path(sym, cfg_id, window)
    if not os.path.exists(path):
        return None
    df = pd.read_parquet(path)
    meta_cols = [c for c in df.columns if c.startswith("m_")]
    orders = []
    for _, r in df.iterrows():
        orders.append({"t": int(r["t"]), "dir": int(r["dir"]),
                       "entry": float(r["entry"]), "sl": float(r["sl"]),
                       "tp": float(r["tp"]),
                       "expiry_ctm": int(r["expiry_ctm"]),
                       "meta": {c[2:]: r[c] for c in meta_cols}})
    return orders


def _path(sym, cfg_id, window):
    return os.path.join(CACHE_DIR, f"{sym}_{cfg_id}_{window[0]}.parquet")
