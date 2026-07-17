"""
app.py — Dashboard monitor-mode (Streamlit) theo spec v3.
Chạy:  streamlit run dashboard/app.py
Mode:  demo (mặc định, không cần MT5)  |  mt5 (Windows + terminal MT5 đang mở)
Dashboard KHÔNG đặt lệnh — chỉ hiển thị signal plan + bảng đèn gates + risk.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import streamlit as st
import yaml
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data.loader import load_bars, get_live_info
from features.gates import compute_features, evaluate_gates
from core.signal import evaluate_signal

st.set_page_config(page_title="MR Monitor — v3 spec", layout="wide")


@st.cache_data(ttl=3600)
def load_cfg():
    with open(ROOT / "config" / "params.yml", encoding="utf-8") as f:
        params = yaml.safe_load(f)
    with open(ROOT / "config" / "costs.yml", encoding="utf-8") as f:
        costs = yaml.safe_load(f)
    return params, costs


PARAMS, COSTS = load_cfg()

with st.sidebar:
    st.title("MR Monitor v3")
    source = st.radio("Nguồn dữ liệu", ["demo", "mt5"], index=0,
                      help="mt5: cần Windows + terminal MT5 đang mở + pip install MetaTrader5")
    symbol = st.selectbox("Symbol", ["EURUSD", "XAUUSD"])
    n_bars = st.slider("Số bars H1", 500, 3000, 1500, step=100)
    refresh_s = st.slider("Auto-refresh (giây)", 5, 60, 10)
    equity = st.number_input("Equity ($)", 1000.0, 1_000_000.0, 10_000.0, step=500.0)
    st.caption("Monitor-mode: không đặt lệnh. Spec v3 §5 Variant A.")


@st.fragment(run_every=f"{refresh_s}s")
def render():
    W = PARAMS["alpha"]["W"]["default"]
    try:
        df_h1 = load_bars(symbol, "H1", n_bars, source=source)
        df_h4 = load_bars(symbol, "H4", max(300, n_bars // 4), source=source)
        live = get_live_info(symbol, source=source)
    except Exception as e:
        st.error(f"Lỗi data source: {e}")
        return

    feats = compute_features(df_h1, W)
    gates = evaluate_gates(symbol, feats, df_h4, PARAMS, COSTS,
                           current_spread_price=live.get("spread_price") or None)
    plan = evaluate_signal(symbol, feats, gates, PARAMS, COSTS, account_equity=equity)
    last = feats.iloc[-1]

    # ---------- hàng metric ----------
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("z-score", f"{plan.z:+.2f}", help="Ngưỡng vào lệnh ±%.1f" % PARAMS["alpha"]["Z_entry"]["default"])
    hl = last["half_life"]
    c2.metric("Half-life (bars H1)", "—" if hl != hl else f"{hl:.1f}")
    c3.metric("ADX H1", f"{last['adx14']:.1f}")
    c4.metric("ATR pctile", "—" if last["atr_pctile"] != last["atr_pctile"] else f"{last['atr_pctile']:.0f}%")
    c5.metric("σ_D / ATR", "—" if last["sigma_over_atr"] != last["sigma_over_atr"] else f"{last['sigma_over_atr']:.2f}",
              help="Deliverable Phase 1 §5.3 — nếu >1.67 thì TP_cap binding")
    c6.metric("Signal", plan.direction,
              delta=None if plan.direction == "NONE" else f"{plan.lots} lots")

    # ---------- chart ----------
    show = feats.tail(400)
    Z = PARAMS["alpha"]["Z_entry"]["default"]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28],
                        vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=show["time"], open=show["open"], high=show["high"],
                                 low=show["low"], close=show["close"], name=symbol,
                                 increasing_line_color="#26a69a", decreasing_line_color="#ef5350"),
                  row=1, col=1)
    fig.add_trace(go.Scatter(x=show["time"], y=show["mu"], name=f"SMA{W}",
                             line=dict(color="#ffb300", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=show["time"], y=show["mu"] + Z * show["sigma"], name=f"+{Z}σ",
                             line=dict(color="#789", width=1, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=show["time"], y=show["mu"] - Z * show["sigma"], name=f"-{Z}σ",
                             line=dict(color="#789", width=1, dash="dot")), row=1, col=1)
    if plan.direction not in ("NONE",) and plan.lots >= 0.01:
        fig.add_hline(y=plan.sl, line_color="#ef5350", line_dash="dash",
                      annotation_text="SL", row=1, col=1)
        fig.add_hline(y=plan.tp, line_color="#26a69a", line_dash="dash",
                      annotation_text=f"TP ({plan.tp_binding})", row=1, col=1)
    fig.add_trace(go.Scatter(x=show["time"], y=show["z"], name="z",
                             line=dict(color="#42a5f5", width=1.2)), row=2, col=1)
    for yv, colr in [(Z, "#ef5350"), (-Z, "#26a69a"), (0, "#888")]:
        fig.add_hline(y=yv, line_color=colr, line_width=1,
                      line_dash="dot" if yv else "solid", row=2, col=1)
    fig.update_layout(height=560, xaxis_rangeslider_visible=False,
                      margin=dict(l=10, r=10, t=25, b=10), legend_orientation="h")
    st.plotly_chart(fig, use_container_width=True)

    # ---------- bảng đèn gates + signal plan ----------
    left, right = st.columns([1.1, 1])
    with left:
        st.subheader("Gates (bảng đèn)")
        gdf = gates.to_frame()
        gdf["đèn"] = np.where(gdf["pass"], "🟢", "🔴")
        gdf["value"] = gdf["value"].map(lambda v: "—" if v != v else f"{v:.4g}")
        st.dataframe(gdf[["đèn", "gate", "value", "threshold"]],
                     hide_index=True, use_container_width=True)
        st.caption("EA chỉ vào lệnh khi TẤT CẢ đèn xanh và |z| ≥ Z_entry (§5.1). "
                   "News gate là stub — nối calendar ở Phase 0 hoàn chỉnh.")
    with right:
        st.subheader("Signal plan (monitor)")
        st.json(plan.to_dict())
        if plan.est_swap_per_night_R:
            st.caption(f"Swap ước tính {plan.est_swap_per_night_R:+.3f}R/đêm — "
                       f"night-cap {PARAMS['exits']['night_cap'][symbol]} đêm (§5.4).")

    if source == "demo":
        st.info("DEMO DATA (random walk + đoạn OU giả lập). Chuyển 'mt5' trên máy Windows có MT5 để xem data thật.")


render()
