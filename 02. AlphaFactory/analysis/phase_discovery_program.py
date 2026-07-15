#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import importlib.util
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from zoneinfo import ZoneInfo

ROOT = Path(r"02. AlphaFactory/runs/XAU_Scalp_Portfolio")
OUT_DIR = ROOT / "strategy_discovery_20260309"
PHASE3B_SCRIPT = Path(r"02. AlphaFactory/analysis/phase3b_router_simulation.py")
STRATEGY_LOG = Path(r"02. AlphaFactory/STRATEGY_LOG.md")
ALL_MONTHS = pd.period_range("2020-03", "2026-03", freq="M").astype(str).tolist()

NY_TZ = ZoneInfo("America/New_York")
LONDON_TZ = ZoneInfo("Europe/London")
NY_ENTRY_1005 = 10 * 60 + 5
NY_ENTRY_1020 = 10 * 60 + 20
NY_END = 13 * 60 + 30
LONDON_ENTRY_0835 = 8 * 60 + 35
LONDON_END = 12 * 60
BASE_RISK_PCT = 0.0025


def load_phase3b():
    spec = importlib.util.spec_from_file_location("phase3b_router_simulation", PHASE3B_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def safe_div(a, b):
    return a / b if b else 0.0


def pf(vals):
    vals = [float(v) for v in vals]
    gp = sum(v for v in vals if v > 0)
    gl = -sum(v for v in vals if v < 0)
    return gp / gl if gl > 0 else 999.99


def dd_pct(vals):
    equity = 100_000.0
    peak = equity
    max_dd = 0.0
    for v in vals:
        equity += equity * BASE_RISK_PCT * float(v)
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak * 100.0 if peak else 0.0)
    return round(max_dd, 2)


def top_pct(vals, n):
    wins = sorted([float(v) for v in vals if v > 0], reverse=True)
    gp = sum(wins)
    return round(sum(wins[:n]) * 100.0 / gp, 2) if gp > 0 else 0.0


def bucket(series, lo=0.33, hi=0.66, labels=("LOW", "MID", "HIGH")):
    clean = series.replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return pd.Series(["UNKNOWN"] * len(series), index=series.index)
    q1, q2 = clean.quantile([lo, hi]).tolist()
    def f(x):
        if pd.isna(x):
            return 'UNKNOWN'
        if x <= q1:
            return labels[0]
        if x <= q2:
            return labels[1]
        return labels[2]
    return series.apply(f)


def load_base(mod):
    features = mod.load_features()
    m1, m5, point = mod.load_mt5_rates()
    day_ctx = mod.build_daily_market_context(features, m1, m5, point)
    frame = features.merge(day_ctx, on='ny_date', how='inner').sort_values('ny_date').reset_index(drop=True)
    sim = mod.simulate_day_playbooks(frame, m5, point)
    frame = sim.copy()
    frame['ny_date'] = pd.to_datetime(frame['ny_date']).dt.date
    frame['month'] = pd.to_datetime(frame['ny_date']).dt.to_period('M').astype(str)
    frame['quarter'] = pd.to_datetime(frame['ny_date']).dt.to_period('Q').astype(str)
    return frame, m1, m5, point


def simulate_ny_trade(day_row, bars, point, direction_field, entry_min, timeout_bars=12, spread_mult=1.0, adverse_fill=False, m1_group=None, path_stress=False):
    direction = int(day_row.get(direction_field, 0))
    if direction == 0 or bars.empty:
        return {'executed': False, 'realized_r': 0.0, 'hold_minutes': 0.0, 'exit_reason': 'no_trade', 'entry_dt': None, 'exit_dt': None}
    trade = bars[(bars['ny_min_of_day'] >= entry_min) & (bars['ny_min_of_day'] < NY_END)].reset_index(drop=True)
    if trade.empty:
        return {'executed': False, 'realized_r': 0.0, 'hold_minutes': 0.0, 'exit_reason': 'no_trade', 'entry_dt': None, 'exit_dt': None}
    entry_bar = trade.iloc[0]
    risk_dist = max(0.80 * float(day_row['atr14_pre_m5']), 0.40 * float(day_row['preopen_range']), point)
    entry_price = float(entry_bar['open'])
    if adverse_fill and m1_group is not None:
        m1w = m1_group[(m1_group['ny_min_of_day'] >= entry_min) & (m1_group['ny_min_of_day'] < entry_min + 5)].copy()
        if not m1w.empty:
            entry_price = float(m1w['open'].max()) if direction > 0 else float(m1w['open'].min())
    spread_cost = float(entry_bar.get('spread', 0.0)) * point * spread_mult
    stop = entry_price - direction * risk_dist
    target = entry_price + direction * risk_dist
    exit_price = float(trade.iloc[min(timeout_bars, len(trade)) - 1]['close'])
    exit_dt = trade.iloc[min(timeout_bars, len(trade)) - 1]['ny_dt']
    exit_reason = 'timeout'
    path = trade.iloc[:timeout_bars].copy()
    if path_stress and m1_group is not None:
        m1path = m1_group[(m1_group['ny_min_of_day'] >= entry_min) & (m1_group['ny_min_of_day'] < entry_min + timeout_bars * 5)].copy()
        if not m1path.empty:
            path = m1path.copy()
    for _, bar in path.iterrows():
        hi = float(bar['high'])
        lo = float(bar['low'])
        if direction > 0:
            stop_hit = lo <= stop
            target_hit = hi >= target
        else:
            stop_hit = hi >= stop
            target_hit = lo <= target
        if stop_hit and target_hit:
            exit_price = stop; exit_reason = 'sl_first_same_bar'; exit_dt = bar['ny_dt']; break
        if stop_hit:
            exit_price = stop; exit_reason = 'sl_hit'; exit_dt = bar['ny_dt']; break
        if target_hit:
            exit_price = target; exit_reason = 'tp_hit'; exit_dt = bar['ny_dt']; break
    gross_r = direction * (exit_price - entry_price) / risk_dist
    return {
        'executed': True,
        'realized_r': gross_r - (spread_cost / risk_dist),
        'hold_minutes': min(len(path), timeout_bars) * (1.0 if path_stress and m1_group is not None else 5.0),
        'exit_reason': exit_reason,
        'entry_dt': entry_bar['ny_dt'].isoformat(),
        'exit_dt': exit_dt.isoformat() if hasattr(exit_dt, 'isoformat') else str(exit_dt),
    }

def build_postlock_context(frame, m1, m5, point):
    rows = []
    g5s = {d: g.reset_index(drop=True) for d, g in m5.groupby('ny_date')}
    for _, row in frame.iterrows():
        d = row['ny_date']
        g5 = g5s.get(d)
        if g5 is None or g5.empty:
            continue
        risk = max(0.80 * float(row['atr14_pre_m5']), 0.40 * float(row['preopen_range']), point)
        post = g5[(g5['ny_min_of_day'] >= 10 * 60) & (g5['ny_min_of_day'] < 10 * 60 + 25)].copy()
        e1020 = g5[g5['ny_min_of_day'] == NY_ENTRY_1020].copy()
        if post.empty:
            continue
        acc_dir = int(row['acceptance_dir'])
        close30 = float(row['close30_price'])
        adverse = 0.0
        confirm = 0.0
        if acc_dir > 0:
            adverse = max(0.0, (close30 - float(post['low'].min())) / risk)
        elif acc_dir < 0:
            adverse = max(0.0, (float(post['high'].max()) - close30) / risk)
        if not e1020.empty and acc_dir != 0:
            confirm = acc_dir * (float(e1020.iloc[0]['open']) - close30) / risk
        rows.append({'ny_date': d, 'postlock_pullback_r': adverse, 'postlock_confirm_r': confirm})
    return pd.DataFrame(rows)


def build_delayed(frame, m1, m5, point):
    rows = []
    g1s = {d: g.reset_index(drop=True) for d, g in m1.groupby('ny_date')}
    g5s = {d: g.reset_index(drop=True) for d, g in m5.groupby('ny_date')}
    for _, row in frame.iterrows():
        d = row['ny_date']
        g1 = g1s.get(d, pd.DataFrame())
        g5 = g5s.get(d, pd.DataFrame())
        cont = simulate_ny_trade(row, g5, point, 'acceptance_dir', NY_ENTRY_1020, m1_group=g1)
        recl = simulate_ny_trade(row, g5, point, 'reclaim_dir', NY_ENTRY_1020, m1_group=g1)
        base = {'ny_date': d}
        for prefix, res in [('DELAYED_ACCEPTANCE', cont), ('DELAYED_RECLAIM', recl)]:
            for k, v in res.items():
                base[f'{prefix}_{k}'] = v
        rows.append(base)
    return pd.DataFrame(rows)


def build_london_benchmark(m5, point):
    df = m5.copy()
    df['london_dt'] = df['utc_dt'].dt.tz_convert(LONDON_TZ)
    df['london_date'] = df['london_dt'].dt.date
    df['london_min'] = df['london_dt'].dt.hour * 60 + df['london_dt'].dt.minute
    rows = []
    for _, g in df.groupby('london_date'):
        pre = g[(g['london_min'] >= 7 * 60) & (g['london_min'] < 8 * 60)].copy()
        open30 = g[(g['london_min'] >= 8 * 60) & (g['london_min'] < 8 * 60 + 30)].copy()
        entry = g[g['london_min'] == LONDON_ENTRY_0835].copy()
        trade = g[(g['london_min'] >= LONDON_ENTRY_0835) & (g['london_min'] < LONDON_END)].copy().reset_index(drop=True)
        if pre.empty or open30.empty or entry.empty:
            continue
        atr14 = float((pre['high'] - pre['low']).tail(14).mean())
        pre_range = float(pre['high'].max() - pre['low'].min())
        direction = int(np.sign(float(open30.iloc[-1]['close']) - float(open30.iloc[0]['open'])))
        risk = max(0.80 * atr14, 0.40 * pre_range, point)
        entry_bar = entry.iloc[0]
        entry_price = float(entry_bar['open'])
        spread_cost = float(entry_bar.get('spread', 0.0)) * point
        stop = entry_price - direction * risk
        target = entry_price + direction * risk
        exit_price = float(trade.iloc[min(12, len(trade)) - 1]['close']) if not trade.empty else entry_price
        exit_dt = trade.iloc[min(12, len(trade)) - 1]['london_dt'] if not trade.empty else entry_bar['london_dt']
        exit_reason = 'timeout'
        for _, bar in trade.iloc[:12].iterrows():
            hi = float(bar['high']); lo = float(bar['low'])
            stop_hit = lo <= stop if direction > 0 else hi >= stop
            target_hit = hi >= target if direction > 0 else lo <= target
            if stop_hit and target_hit:
                exit_price = stop; exit_reason = 'sl_first_same_bar'; exit_dt = bar['london_dt']; break
            if stop_hit:
                exit_price = stop; exit_reason = 'sl_hit'; exit_dt = bar['london_dt']; break
            if target_hit:
                exit_price = target; exit_reason = 'tp_hit'; exit_dt = bar['london_dt']; break
        gross_r = direction * (exit_price - entry_price) / risk if direction != 0 else 0.0
        ny_date = entry_bar['utc_dt'].tz_convert(NY_TZ).date()
        rows.append({
            'ny_date': ny_date,
            'london_pre_range_norm': safe_div(pre_range, atr14 if atr14 else point),
            'london_impulse30_norm': safe_div(abs(float(open30.iloc[-1]['close']) - float(open30.iloc[0]['open'])), atr14 if atr14 else point),
            'LONDON_EXPANSION_executed': bool(direction != 0),
            'LONDON_EXPANSION_realized_r': gross_r - (spread_cost / risk) if direction != 0 else 0.0,
            'LONDON_EXPANSION_hold_minutes': 60.0 if len(trade) else 0.0,
            'LONDON_EXPANSION_exit_reason': exit_reason,
            'LONDON_EXPANSION_entry_dt': entry_bar['london_dt'].isoformat(),
            'LONDON_EXPANSION_exit_dt': exit_dt.isoformat() if hasattr(exit_dt, 'isoformat') else str(exit_dt),
        })
    return pd.DataFrame(rows)


def enrich_states(frame):
    frame = frame.copy()
    frame['vol_regime'] = bucket(frame['atr14_pre_m5'], labels=('VOL_LOW', 'VOL_MID', 'VOL_HIGH'))
    frame['spread_regime'] = bucket(frame['spread_pct_10'], labels=('SPREAD_LOW', 'SPREAD_MID', 'SPREAD_HIGH'))
    frame['trend_chop_regime'] = np.where((frame['rotation_30'] <= frame['rotation_30'].median()) & (frame['impulse30_norm'].abs() >= frame['impulse30_norm'].abs().median()), 'TREND', np.where((frame['rotation_30'] > frame['rotation_30'].median()) & (frame['close_to_vwap_norm'].abs() <= frame['close_to_vwap_norm'].abs().median()), 'CHOP', 'MIXED'))
    frame['or_width_bucket'] = bucket(frame['or30_width_norm'], labels=('OR_NARROW', 'OR_MID', 'OR_WIDE'))
    frame['day_range_bucket'] = bucket(frame['session_range_norm'], labels=('RANGE_LOW', 'RANGE_MID', 'RANGE_HIGH'))
    frame['handoff_state'] = np.where(frame['handoff_conflict'] == 1, 'HANDOFF_CONFLICT', 'HANDOFF_ALIGN')
    frame['acceptance_rejection_index'] = frame['accept_balance_30'] - 0.5 * frame['rotation_30'] + 0.25 * frame['impulse30_norm']
    frame['value_conflict_meter'] = frame['close_to_vwap_norm'].abs() + 0.5 * frame['close_to_mid_norm'].abs() + 0.75 * frame['handoff_conflict']
    frame['microstructure_fragility_index'] = frame['spread_pct_10'] + frame['close_to_vwap_norm'].abs() + 0.5 * frame['session_efficiency'].abs()
    frame['session_state_dashboard'] = np.where((frame['preopen_range_norm'] <= frame['preopen_range_norm'].median()) & (frame['or30_width_norm'] <= frame['or30_width_norm'].median()), 'COMPRESSED', np.where((frame['impulse30_norm'].abs() >= frame['impulse30_norm'].abs().median()) & (frame['rotation_30'] <= frame['rotation_30'].median()), 'EXPANDING', 'MIXED'))
    frame['event_risk_bucket'] = np.where(frame['time_since_major_news_min'].isna(), 'EVENT_UNKNOWN', np.where(frame['time_since_major_news_min'] < 60, 'EVENT_0_60', np.where(frame['time_since_major_news_min'] < 180, 'EVENT_60_180', 'EVENT_180_PLUS')))
    return frame


def thresholds(frame):
    a = frame[frame['split'] == 'A'].copy()
    signed_vdist = a['acceptance_dir'] * a['vwap_dist_30_norm']
    return {
        'spread_low': float(a['spread_pct_10'].quantile(0.60)),
        'accept_hi': float(a['accept_balance_30'].median()),
        'rotation_low': float(a['rotation_30'].median()),
        'rotation_high': float(a['rotation_30'].quantile(0.60)),
        'signed_vdist_hi': float(signed_vdist.median()),
        'close_vwap_low': float(a['close_to_vwap_norm'].abs().median()),
        'sweep_hi': float(a['london_extreme_sweep_norm'].quantile(0.75)),
        'pullback_ok': float(a['postlock_pullback_r'].median()),
        'confirm_ok': float(a['postlock_confirm_r'].median()),
        'london_pre_comp': float(a['london_pre_range_norm'].quantile(0.40)) if 'london_pre_range_norm' in a.columns else 0.0,
        'london_impulse_hi': float(a['london_impulse30_norm'].quantile(0.60)) if 'london_impulse30_norm' in a.columns else 0.0,
    }


def lane_specs(frame, thr):
    spread_ok = frame['spread_pct_10'] <= thr['spread_low']
    handoff_align = frame['handoff_conflict'] == 0
    handoff_conflict = frame['handoff_conflict'] == 1
    accept_hi = frame['accept_balance_30'] >= thr['accept_hi']
    rotation_low = frame['rotation_30'] <= thr['rotation_low']
    rotation_high = frame['rotation_30'] >= thr['rotation_high']
    signed_vdist_hi = frame['acceptance_dir'] * frame['vwap_dist_30_norm'] >= thr['signed_vdist_hi']
    close_vwap_low = frame['close_to_vwap_norm'].abs() <= thr['close_vwap_low']
    sweep_hi = frame['london_extreme_sweep_norm'] >= thr['sweep_hi']
    post_shallow = frame['postlock_pullback_r'] <= thr['pullback_ok']
    post_confirm = frame['postlock_confirm_r'] >= thr['confirm_ok']
    london_pre_comp = frame['london_pre_range_norm'] <= thr['london_pre_comp'] if 'london_pre_range_norm' in frame.columns else pd.Series(False, index=frame.index)
    london_impulse_hi = frame['london_impulse30_norm'] >= thr['london_impulse_hi'] if 'london_impulse30_norm' in frame.columns else pd.Series(False, index=frame.index)
    return {
        'A_NY_OPEN_CONTINUATION': ('NY_OPEN_CONTINUATION', 'ACCEPTANCE', handoff_align & accept_hi & rotation_low & signed_vdist_hi & spread_ok, 'Aligned handoff and accepted open impulse.'),
        'B_NY_OPEN_REVERSAL': ('NY_OPEN_REVERSAL', 'FAILURE_FADE', handoff_conflict & accept_hi & spread_ok & (frame['london_pos_at_open'] > frame['london_pos_at_open'].median()), 'Failed acceptance with handoff conflict.'),
        'C_POST_OPEN_RECLAIM': ('POST_OPEN_RECLAIM', 'DELAYED_RECLAIM', (frame['vwap_reclaim_15'] == 1) & rotation_high & close_vwap_low & spread_ok, 'Delayed reclaim toward value after early rotation.'),
        'D_LONDON_TO_NY_HANDOFF_REVERSAL': ('LONDON_TO_NY_HANDOFF_REVERSAL', 'FAILURE_FADE', handoff_conflict & (frame['london_sweep_flag'] == 1) & sweep_hi & spread_ok, 'London sweep into NY conflict reversal.'),
        'E_DELAYED_TREND_CONTINUATION': ('DELAYED_TREND_CONTINUATION', 'DELAYED_ACCEPTANCE', handoff_align & accept_hi & post_shallow & post_confirm & spread_ok, 'Continuation only after shallow pullback and confirmation.'),
        'F_NO_TRADE_POLICY': ('NO_TRADE_POLICY', 'NO_TRADE', pd.Series(False, index=frame.index), 'Flat benchmark lane.'),
        'G_NON_NY_BENCHMARK': ('LONDON_EXPANSION_BENCHMARK', 'LONDON_EXPANSION', london_pre_comp & london_impulse_hi, 'London expansion benchmark after compression.'),
    }

def apply_lane(frame, lane, spec):
    archetype, source, mask, reason = spec
    out = frame.copy()
    mask = mask.astype(bool)
    if source == 'NO_TRADE':
        out['strategy_executed'] = False
        out['strategy_r'] = 0.0
        out['strategy_hold'] = 0.0
        out['strategy_exit_reason'] = 'no_trade'
        out['strategy_entry_dt'] = None
        out['strategy_exit_dt'] = None
    else:
        out['strategy_executed'] = mask & out[f'{source}_executed'].astype(bool)
        out['strategy_r'] = np.where(out['strategy_executed'], out[f'{source}_realized_r'].astype(float), 0.0)
        out['strategy_hold'] = np.where(out['strategy_executed'], out[f'{source}_hold_minutes'].astype(float), 0.0)
        out['strategy_exit_reason'] = np.where(out['strategy_executed'], out.get(f'{source}_exit_reason', 'timeout'), 'blocked')
        out['strategy_entry_dt'] = np.where(out['strategy_executed'], out.get(f'{source}_entry_dt', out.get(f'{source}_entry_ny', None)), None)
        out['strategy_exit_dt'] = np.where(out['strategy_executed'], out.get(f'{source}_exit_dt', out.get(f'{source}_exit_ny', None)), None)
    out['lane'] = lane
    out['lane_family'] = archetype
    out['lane_source'] = source
    out['lane_reason'] = reason
    return out


def lane_metrics(mod, df):
    full = mod.equity_metrics_from_frame(df, 'strategy_r', 'strategy_executed', 'strategy_hold')
    split_a = mod.calc_strategy_metrics(df[df['split'] == 'A'].copy())
    split_b = mod.calc_strategy_metrics(df[df['split'] == 'B'].copy())
    rolling_rows, profitable, avg_pf = mod.rolling_summary(df.copy())
    full['rolling_profitable'] = f'{profitable}/{len(mod.ROLL_WINDOWS)}'
    full['rolling_avg_pf'] = avg_pf
    return full, split_a, split_b, rolling_rows


def stress_vals(df, source, m1, m5, point, variant):
    m1g = {d: g.reset_index(drop=True) for d, g in m1.groupby('ny_date')}
    m5g = {d: g.reset_index(drop=True) for d, g in m5.groupby('ny_date')}
    vals = []
    for _, row in df[df['strategy_executed']].iterrows():
        day = row['ny_date']
        if source == 'ACCEPTANCE':
            res = simulate_ny_trade(row, m5g.get(day, pd.DataFrame()), point, 'acceptance_dir', NY_ENTRY_1005, spread_mult=1.25 if variant == 'SPREAD25' else 1.5 if variant == 'SPREAD50' else 1.0, adverse_fill=(variant == 'ADVERSE'), m1_group=m1g.get(day, pd.DataFrame()), path_stress=(variant == 'PATH'))
            vals.append(res['realized_r'])
        elif source == 'FAILURE_FADE':
            res = simulate_ny_trade(row, m5g.get(day, pd.DataFrame()), point, 'failure_dir', NY_ENTRY_1005, spread_mult=1.25 if variant == 'SPREAD25' else 1.5 if variant == 'SPREAD50' else 1.0, adverse_fill=(variant == 'ADVERSE'), m1_group=m1g.get(day, pd.DataFrame()), path_stress=(variant == 'PATH'))
            vals.append(res['realized_r'])
        elif source == 'DELAYED_RECLAIM':
            res = simulate_ny_trade(row, m5g.get(day, pd.DataFrame()), point, 'reclaim_dir', NY_ENTRY_1020, spread_mult=1.25 if variant == 'SPREAD25' else 1.5 if variant == 'SPREAD50' else 1.0, adverse_fill=(variant == 'ADVERSE'), m1_group=m1g.get(day, pd.DataFrame()), path_stress=(variant == 'PATH'))
            vals.append(res['realized_r'])
        elif source == 'DELAYED_ACCEPTANCE':
            res = simulate_ny_trade(row, m5g.get(day, pd.DataFrame()), point, 'acceptance_dir', NY_ENTRY_1020, spread_mult=1.25 if variant == 'SPREAD25' else 1.5 if variant == 'SPREAD50' else 1.0, adverse_fill=(variant == 'ADVERSE'), m1_group=m1g.get(day, pd.DataFrame()), path_stress=(variant == 'PATH'))
            vals.append(res['realized_r'])
        elif source == 'LONDON_EXPANSION':
            base = float(row['strategy_r'])
            penalty = 0.0 if variant == 'BASE' else 0.35 if variant == 'ADVERSE' else 0.10 if variant == 'SPREAD25' else 0.20 if variant == 'SPREAD50' else 0.25
            vals.append(base - penalty)
    return vals


def lane_verdict(row):
    if row['lane'] == 'F_NO_TRADE_POLICY':
        return 'researchable'
    if row['trade_count'] < 40 or row['splitB_pf'] < 1.0 or row['rolling_profitable'] in {'0/6', '1/6', '2/6'}:
        return 'dead end' if row['pf'] < 1.0 else 'useful but weak'
    if row['pf'] >= 1.40 and row['splitB_pf'] >= 1.20 and row['trade_count'] >= 80 and row['top10_contribution'] <= 25.0 and row['execution_fragility_score'] <= 1.25:
        return 'promotable to standalone development'
    if row['pf'] >= 1.05 and row['splitB_pf'] >= 1.0:
        return 'researchable'
    return 'useful but weak'


def build_reports(mod, lanes, m1, m5, point):
    master_rows, month_rows, frag_rows, trade_rows, blocked_rows = [], [], [], [], []
    regime_lines = ['# Regime phase map', '']
    density_lines = ['# Yearly and quarterly density report', '']
    gallery_lines = ['# Market context replay gallery', '']
    cross_rows = []

    for lane, df in lanes.items():
        full, a, b, rolling = lane_metrics(mod, df)
        vals = df[df['strategy_executed']]['strategy_r'].astype(float).tolist()
        frag = {
            'lane': lane,
            'base_pf': round(float(pf(vals)), 4) if vals else 0.0,
            'base_dd': round(float(dd_pct(vals)), 2) if vals else 0.0,
            'real_ticks_status': 'PENDING_OFFLINE_DISCOVERY',
            'random_delay_status': 'PENDING_OFFLINE_DISCOVERY',
        }
        for key in ['ADVERSE', 'SPREAD25', 'SPREAD50', 'PATH']:
            sv = stress_vals(df, df['lane_source'].iloc[0], m1, m5, point, key)
            frag[f'{key.lower()}_pf'] = round(float(pf(sv)), 4) if sv else 0.0
            frag[f'{key.lower()}_dd'] = round(float(dd_pct(sv)), 2) if sv else 0.0
        frag['execution_fragility_score'] = round(max(0.0, frag['base_pf'] - frag['adverse_pf']) + max(0.0, frag['base_pf'] - frag['spread25_pf']) + max(0.0, frag['base_pf'] - frag['spread50_pf']) + max(0.0, frag['base_pf'] - frag['path_pf']), 4)
        frag_rows.append(frag)

        trades = df[df['strategy_executed']].copy()
        by_day = trades.groupby('ny_date')['strategy_r'].sum().sort_index() if not trades.empty else pd.Series(dtype=float)
        by_month_r = trades.groupby('month')['strategy_r'].sum() if not trades.empty else pd.Series(dtype=float)
        master_rows.append({
            'lane': lane,
            'archetype': df['lane_family'].iloc[0],
            'pf': full['pf'], 'dd': full['dd'],
            'splitA_pf': a['pf'], 'splitB_pf': b['pf'],
            'rolling_profitable': full['rolling_profitable'], 'rolling_avg_pf': full['rolling_avg_pf'],
            'trade_count': full['trades'], 'avg_hold': full['avg_hold'], 'median_hold': full['median_hold'], 'p95_hold': full['p95_hold'],
            'top5_contribution': full['top5'], 'top10_contribution': full['top10'],
            'worst_month': round(float(by_month_r.min()), 4) if not by_month_r.empty else 0.0,
            'worst_5day': round(float(by_day.rolling(5).sum().min()), 4) if len(by_day) >= 5 else 0.0,
            'reason': df['lane_reason'].iloc[0],
        })

        for month, g in trades.groupby('month'):
            r = g['strategy_r'].astype(float).tolist()
            month_rows.append({'lane': lane, 'month': month, 'trade_count': len(g), 'net_r': round(float(sum(r)), 4), 'pf': round(float(pf(r)), 4), 'dd': round(float(dd_pct(r)), 2), 'expectancy': round(float(np.mean(r)), 4)})
        y = trades.groupby('year').size().rename('trades').reset_index() if not trades.empty else pd.DataFrame(columns=['year', 'trades'])
        q = trades.groupby('quarter').size().rename('trades').reset_index() if not trades.empty else pd.DataFrame(columns=['quarter', 'trades'])
        m = trades.groupby('month').size().rename('trades').reset_index() if not trades.empty else pd.DataFrame(columns=['month', 'trades'])
        active_months = set(m['month'].tolist()) if not m.empty else set()
        zero_months = len([x for x in ALL_MONTHS if x not in active_months])
        density_lines.extend([f'## {lane}', '', f'- Total trades: **{len(trades)}**', f'- Median trades/month: **{float(m["trades"].median()) if not m.empty else 0.0:.2f}**', f'- Zero-trade months (full sample window): **{zero_months}**', '', '### By year', '', y.to_markdown(index=False) if not y.empty else '_No trades_', '', '### By quarter', '', q.to_markdown(index=False) if not q.empty else '_No trades_', ''])
        regime_lines.extend([f'## {lane}', ''])
        for dim in ['vol_regime', 'spread_regime', 'trend_chop_regime', 'or_width_bucket', 'day_range_bucket', 'handoff_state', 'event_risk_bucket', 'session_state_dashboard']:
            grp = trades.groupby(dim)['strategy_r'].agg(['count', 'sum', 'mean']).reset_index() if not trades.empty else pd.DataFrame(columns=[dim, 'count', 'sum', 'mean'])
            if not grp.empty:
                grp.columns = [dim, 'trade_count', 'net_r', 'expectancy']
                regime_lines.extend([f'### {dim}', '', grp.to_markdown(index=False), ''])
        if not trades.empty:
            best20 = trades.nlargest(20, 'strategy_r')[['ny_date', 'strategy_r', 'vol_regime', 'spread_regime', 'trend_chop_regime', 'handoff_state', 'lane_reason']]
            worst20 = trades.nsmallest(20, 'strategy_r')[['ny_date', 'strategy_r', 'vol_regime', 'spread_regime', 'trend_chop_regime', 'handoff_state', 'lane_reason']]
            gallery_lines.extend([f'## {lane}', '', '### 20 best trades', '', best20.to_markdown(index=False), '', '### 20 worst trades', '', worst20.to_markdown(index=False), ''])
            cross = trades.groupby(['month', 'vol_regime', 'trend_chop_regime', 'handoff_state'])['strategy_r'].agg(['count', 'sum', 'mean']).reset_index()
            cross['lane'] = lane
            cross.columns = ['month', 'vol_regime', 'trend_chop_regime', 'handoff_state', 'trade_count', 'net_r', 'expectancy', 'lane']
            cross_rows.append(cross)
        for _, row in df.iterrows():
            base = {'lane': lane, 'archetype': row['lane_family'], 'ny_date': str(row['ny_date']), 'split': row['split'], 'month': row['month'], 'weekday': row['weekday'], 'session_state_dashboard': row['session_state_dashboard'], 'acceptance_rejection_index': round(float(row['acceptance_rejection_index']), 5), 'value_conflict_meter': round(float(row['value_conflict_meter']), 5), 'microstructure_fragility_index': round(float(row['microstructure_fragility_index']), 5), 'event_risk_bucket': row['event_risk_bucket']}
            if bool(row['strategy_executed']):
                trade_rows.append({**base, 'why_allowed': row['lane_reason'], 'strategy_r': round(float(row['strategy_r']), 5), 'hold_minutes': round(float(row['strategy_hold']), 2), 'exit_reason': row['strategy_exit_reason'], 'entry_dt': row['strategy_entry_dt'], 'exit_dt': row['strategy_exit_dt'], 'vol_regime': row['vol_regime'], 'spread_regime': row['spread_regime'], 'trend_chop_regime': row['trend_chop_regime'], 'handoff_state': row['handoff_state']})
            else:
                blocked_rows.append({**base, 'blocked_reason': 'LANE_CONDITION_NOT_MET_OR_NO_TRADE_POLICY', 'lane_reason': row['lane_reason'], 'base_acceptance_r': round(float(row.get('ACCEPTANCE_realized_r', 0.0)), 5), 'base_failure_r': round(float(row.get('FAILURE_FADE_realized_r', 0.0)), 5), 'base_reclaim_r': round(float(row.get('POST_OPEN_RECLAIM_realized_r', 0.0)), 5)})
        if not trades.empty:
            by_day = trades.groupby('ny_date')['strategy_r'].sum().sort_index()
            cluster_rows = []
            for i in range(len(by_day)):
                for w in [3, 5]:
                    if i + w <= len(by_day):
                        sl = by_day.iloc[i:i+w]
                        cluster_rows.append({'lane': lane, 'from': str(sl.index[0]), 'to': str(sl.index[-1]), 'window_days': w, 'net_r': round(float(sl.sum()), 4)})
            cluster_rows = sorted(cluster_rows, key=lambda x: x['net_r'])[:5]
            gallery_lines.extend(['### Worst drawdown clusters', '', pd.DataFrame(cluster_rows).to_markdown(index=False) if cluster_rows else '_No clusters_', ''])

    master = pd.DataFrame(master_rows)
    fragility = pd.DataFrame(frag_rows)
    master = master.merge(fragility[['lane', 'execution_fragility_score']], on='lane', how='left')
    master['verdict'] = master.apply(lane_verdict, axis=1)
    master = master.sort_values(['splitB_pf', 'trade_count', 'execution_fragility_score'], ascending=[False, False, True]).reset_index(drop=True)
    return master, pd.DataFrame(month_rows), fragility, pd.concat(cross_rows, ignore_index=True) if cross_rows else pd.DataFrame(), '\n'.join(density_lines), '\n'.join(regime_lines), '\n'.join(gallery_lines), trade_rows, blocked_rows

def build_indicator_dashboard(frame, master):
    return '\n'.join([
        '# Research indicator dashboard',
        '',
        '## Indicator definitions',
        '- Session State Dashboard: compressed / expanding / mixed from pre-open range, OR width and rotation.',
        '- Acceptance-Rejection Index: accept balance minus rotation penalty plus impulse support.',
        '- Value Conflict Meter: VWAP/value displacement plus handoff conflict penalty.',
        '- Microstructure Fragility Index: spread percentile plus displacement plus session-efficiency penalty.',
        '- Event Risk Map: EVENT_0_60 / EVENT_60_180 / EVENT_180_PLUS / EVENT_UNKNOWN.',
        '',
        pd.DataFrame([{
            'acceptance_rejection_index_median': round(float(frame['acceptance_rejection_index'].median()), 4),
            'value_conflict_meter_median': round(float(frame['value_conflict_meter'].median()), 4),
            'microstructure_fragility_index_median': round(float(frame['microstructure_fragility_index'].median()), 4),
        }]).to_markdown(index=False),
        '',
        master[['lane', 'archetype', 'trade_count', 'pf', 'splitB_pf', 'execution_fragility_score', 'verdict']].to_markdown(index=False),
    ])


def append_strategy_log(master):
    best = master.iloc[0]
    lines = [
        '',
        '## XSP_STRATEGY_DISCOVERY_HARD_RESET',
        f"- Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        '- Scope: multi-lane archetype discovery under one neutral execution framework.',
        f"- Best lane by split-B / density / fragility mix: {best['lane']} ({best['archetype']})",
        f"- Headline: PF {best['pf']:.4f} | SplitB PF {best['splitB_pf']:.4f} | Trades {int(best['trade_count'])} | Verdict {best['verdict']}",
        '- Strategic read: stop forcing NY-open default if alternative lanes or benchmark show stronger evidence.',
    ]
    with STRATEGY_LOG.open('a', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


def main():
    mod = load_phase3b()
    frame, m1, m5, point = load_base(mod)
    frame = frame.merge(build_postlock_context(frame, m1, m5, point), on='ny_date', how='left')
    frame = frame.merge(build_delayed(frame, m1, m5, point), on='ny_date', how='left')
    frame = frame.merge(build_london_benchmark(m5, point), on='ny_date', how='left')
    frame = enrich_states(frame)
    thr = thresholds(frame)
    specs = lane_specs(frame, thr)
    lanes = {lane: apply_lane(frame, lane, spec) for lane, spec in specs.items()}

    master, monthly, fragility, month_regime, density_md, regime_md, gallery_md, trade_rows, blocked_rows = build_reports(mod, lanes, m1, m5, point)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(OUT_DIR / 'monthly_trade_heatmap.csv', index=False)
    fragility.to_csv(OUT_DIR / 'execution_fragility_matrix.csv', index=False)
    month_regime.to_csv(OUT_DIR / 'month_regime_cross_table.csv', index=False)
    master.to_csv(OUT_DIR / 'lane_comparison_master_table.csv', index=False)
    write_text(OUT_DIR / 'yearly_quarterly_density_report.md', density_md)
    write_text(OUT_DIR / 'regime_phase_map.md', regime_md)
    write_text(OUT_DIR / 'market_context_replay_gallery.md', gallery_md)
    write_text(OUT_DIR / 'research_indicator_dashboard.md', build_indicator_dashboard(frame, master))
    write_jsonl(OUT_DIR / 'trade_story.jsonl', trade_rows)
    write_jsonl(OUT_DIR / 'blocked_signal_story.jsonl', blocked_rows)
    write_json(OUT_DIR / 'strategy_discovery_summary.json', {
        'generated_at': datetime.now().isoformat(),
        'thresholds': {k: round(float(v), 6) if isinstance(v, (int, float)) else v for k, v in thr.items()},
        'master': master.to_dict(orient='records'),
    })
    append_strategy_log(master)


if __name__ == '__main__':
    main()
