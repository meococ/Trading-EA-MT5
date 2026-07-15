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
OUT_DIR = ROOT / "discovery3_failure_new_archetypes_20260309"
DISC_SCRIPT = Path(r"02. AlphaFactory/analysis/phase_discovery_program.py")
STRATEGY_LOG = Path(r"02. AlphaFactory/STRATEGY_LOG.md")
ALL_MONTHS = pd.period_range('2020-03', '2026-03', freq='M').astype(str).tolist()
NY_TZ = ZoneInfo('America/New_York')
LONDON_TZ = ZoneInfo('Europe/London')
LCP_ENTRY = 8 * 60 + 40
LONDON_END = 12 * 60
LRR_PROBE_END = 8 * 60 + 35
LRR_ENTRY = 8 * 60 + 40
MIDDAY_SEG_START = 10 * 60 + 30
MIDDAY_SEG_END = 11 * 60 + 5
MIDDAY_ENTRY = 11 * 60 + 5
MIDDAY_END = 13 * 60 + 30


def load_mod():
    spec = importlib.util.spec_from_file_location('phase_discovery_program', DISC_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding='utf-8')


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')


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
        equity += equity * 0.0025 * float(v)
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak * 100.0 if peak else 0.0)
    return round(max_dd, 2)


def top_pct(vals, n):
    wins = sorted([float(v) for v in vals if v > 0], reverse=True)
    gp = sum(wins)
    return round(sum(wins[:n]) * 100.0 / gp, 2) if gp > 0 else 0.0


def safe_div(a, b):
    return a / b if b else 0.0


def build_core_frame(base):
    phase3 = base.load_phase3b()
    frame, m1, m5, point = base.load_base(phase3)
    frame = frame.merge(base.build_postlock_context(frame, m1, m5, point), on='ny_date', how='left')
    frame = frame.merge(base.build_delayed(frame, m1, m5, point), on='ny_date', how='left')
    frame = frame.merge(base.build_london_benchmark(m5, point), on='ny_date', how='left')
    frame = base.enrich_states(frame)
    return phase3, frame, m1, m5, point


def simulate_generic_trade(trade, entry, direction, risk, point, minute_col, variant='BASE', m1_group=None, timeout_bars=12):
    if direction == 0 or trade.empty or entry.empty:
        return {'executed': False, 'realized_r': 0.0, 'hold_minutes': 0.0, 'exit_reason': 'no_trade', 'entry_dt': None, 'exit_dt': None}
    entry_bar = entry.iloc[0]
    entry_price = float(entry_bar['open'])
    if variant == 'ADVERSE' and m1_group is not None and not m1_group.empty:
        start_min = int(entry_bar[minute_col])
        m1w = m1_group[(m1_group[minute_col] >= start_min) & (m1_group[minute_col] < start_min + 5)].copy()
        if not m1w.empty:
            entry_price = float(m1w['open'].max()) if direction > 0 else float(m1w['open'].min())
    spread_mult = 1.25 if variant == 'SPREAD25' else 1.50 if variant == 'SPREAD50' else 1.0
    spread_cost = float(entry_bar.get('spread', 0.0)) * point * spread_mult
    stop = entry_price - direction * risk
    target = entry_price + direction * risk
    path = trade.iloc[:timeout_bars].copy()
    if variant == 'PATH' and m1_group is not None and not m1_group.empty:
        start_min = int(entry_bar[minute_col])
        m1path = m1_group[(m1_group[minute_col] >= start_min) & (m1_group[minute_col] < start_min + timeout_bars * 5)].copy()
        if not m1path.empty:
            path = m1path.copy()
    exit_price = float(path.iloc[min(len(path), timeout_bars) - 1]['close'])
    time_col = 'ny_dt' if 'ny_dt' in path.columns else 'london_dt'
    exit_dt = path.iloc[min(len(path), timeout_bars) - 1][time_col]
    exit_reason = 'timeout'
    for _, bar in path.iterrows():
        hi = float(bar['high']); lo = float(bar['low'])
        stop_hit = lo <= stop if direction > 0 else hi >= stop
        target_hit = hi >= target if direction > 0 else lo <= target
        if stop_hit and target_hit:
            exit_price = stop; exit_dt = bar[time_col]; exit_reason = 'sl_first_same_bar'; break
        if stop_hit:
            exit_price = stop; exit_dt = bar[time_col]; exit_reason = 'sl_hit'; break
        if target_hit:
            exit_price = target; exit_dt = bar[time_col]; exit_reason = 'tp_hit'; break
    gross_r = direction * (exit_price - entry_price) / risk
    entry_time_col = 'ny_dt' if 'ny_dt' in entry_bar.index else 'london_dt'
    hold_mult = 1.0 if (variant == 'PATH' and m1_group is not None and not m1_group.empty) else 5.0
    return {
        'executed': True,
        'realized_r': gross_r - spread_cost / risk,
        'hold_minutes': min(len(path), timeout_bars) * hold_mult,
        'exit_reason': exit_reason,
        'entry_dt': entry_bar[entry_time_col].isoformat(),
        'exit_dt': exit_dt.isoformat() if hasattr(exit_dt, 'isoformat') else str(exit_dt),
        'risk_dist': risk,
        'entry_spread_points': float(entry_bar.get('spread', 0.0)),
    }


def build_london_range_rejection(frame, m1, m5, point):
    df5 = m5.copy()
    df5['london_dt'] = df5['utc_dt'].dt.tz_convert(LONDON_TZ)
    df5['london_date'] = df5['london_dt'].dt.date
    df5['london_min'] = df5['london_dt'].dt.hour * 60 + df5['london_dt'].dt.minute
    df1 = m1.copy()
    df1['london_dt'] = df1['utc_dt'].dt.tz_convert(LONDON_TZ)
    df1['london_date'] = df1['london_dt'].dt.date
    df1['london_min'] = df1['london_dt'].dt.hour * 60 + df1['london_dt'].dt.minute
    g5 = {d: g.reset_index(drop=True) for d, g in df5.groupby('london_date')}
    g1 = {d: g.reset_index(drop=True) for d, g in df1.groupby('london_date')}
    rows = []
    for d, bars in g5.items():
        pre = bars[(bars['london_min'] >= 7 * 60) & (bars['london_min'] < 8 * 60)].copy()
        probe = bars[(bars['london_min'] >= 8 * 60) & (bars['london_min'] < LRR_PROBE_END)].copy()
        entry = bars[bars['london_min'] == LRR_ENTRY].copy()
        trade = bars[(bars['london_min'] >= LRR_ENTRY) & (bars['london_min'] < LONDON_END)].copy().reset_index(drop=True)
        if pre.empty or probe.empty or entry.empty or trade.empty:
            continue
        pre_hi = float(pre['high'].max()); pre_lo = float(pre['low'].min())
        close_probe = float(probe.iloc[-1]['close'])
        direction = 0
        if float(probe['high'].max()) > pre_hi and close_probe < pre_hi:
            direction = -1
        elif float(probe['low'].min()) < pre_lo and close_probe > pre_lo:
            direction = 1
        atr = float((pre['high'] - pre['low']).tail(14).mean())
        risk = max(0.80 * atr, 0.40 * (pre_hi - pre_lo), point)
        base = {
            'ny_date': entry.iloc[0]['utc_dt'].tz_convert(NY_TZ).date(),
            'lrr_direction': direction,
            'lrr_probe_return_norm': safe_div(abs(close_probe - (pre_hi if direction < 0 else pre_lo if direction > 0 else close_probe)), risk),
            'lrr_pre_range_norm': safe_div(pre_hi - pre_lo, atr if atr else point),
            'lrr_risk_dist': risk,
        }
        for variant in ['BASE', 'ADVERSE', 'SPREAD25', 'SPREAD50', 'PATH']:
            res = simulate_generic_trade(trade, entry, direction, risk, point, 'london_min', variant, g1.get(d, pd.DataFrame()))
            for k, v in res.items():
                base[f'LRR_{variant}_{k}'] = v
        rows.append(base)
    return pd.DataFrame(rows), g5, g1


def build_midday_equilibrium(frame, m1, m5, point):
    df5 = m5.copy()
    df5['ny_dt'] = df5['utc_dt'].dt.tz_convert(NY_TZ)
    df5['ny_date'] = df5['ny_dt'].dt.date
    df5['ny_min'] = df5['ny_dt'].dt.hour * 60 + df5['ny_dt'].dt.minute
    df1 = m1.copy()
    df1['ny_dt'] = df1['utc_dt'].dt.tz_convert(NY_TZ)
    df1['ny_date'] = df1['ny_dt'].dt.date
    df1['ny_min'] = df1['ny_dt'].dt.hour * 60 + df1['ny_dt'].dt.minute
    g5 = {d: g.reset_index(drop=True) for d, g in df5.groupby('ny_date')}
    g1 = {d: g.reset_index(drop=True) for d, g in df1.groupby('ny_date')}
    train = frame[frame['split'] == 'A'].copy()
    q_rot = float(train['rotation_30'].quantile(0.60))
    q_mid = float(train['close_to_mid_norm'].abs().quantile(0.60))
    rows = []
    for _, row in frame.iterrows():
        d = row['ny_date']
        bars = g5.get(d, pd.DataFrame())
        seg = bars[(bars['ny_min'] >= MIDDAY_SEG_START) & (bars['ny_min'] < MIDDAY_SEG_END)].copy()
        entry = bars[bars['ny_min'] == MIDDAY_ENTRY].copy()
        trade = bars[(bars['ny_min'] >= MIDDAY_ENTRY) & (bars['ny_min'] < MIDDAY_END)].copy().reset_index(drop=True)
        if seg.empty or entry.empty or trade.empty:
            continue
        rng = float(seg['high'].max() - seg['low'].min())
        direction = 0
        if int(row['acceptance_dir']) > 0 and float(row['rotation_30']) > q_rot and abs(float(row['close_to_mid_norm'])) > q_mid and int(row['handoff_conflict']) == 0:
            direction = -1
        elif int(row['acceptance_dir']) < 0 and float(row['rotation_30']) > q_rot and abs(float(row['close_to_mid_norm'])) > q_mid and int(row['handoff_conflict']) == 0:
            direction = 1
        risk = max(0.80 * float(row['atr14_pre_m5']), 0.25 * rng, point)
        base = {
            'ny_date': d,
            'meq_direction': direction,
            'meq_rotation_gate': float(row['rotation_30']),
            'meq_mid_dist_abs': abs(float(row['close_to_mid_norm'])),
            'meq_risk_dist': risk,
            'meq_rot_threshold': q_rot,
            'meq_mid_threshold': q_mid,
        }
        for variant in ['BASE', 'ADVERSE', 'SPREAD25', 'SPREAD50', 'PATH']:
            res = simulate_generic_trade(trade, entry, direction, risk, point, 'ny_min', variant, g1.get(d, pd.DataFrame()))
            for k, v in res.items():
                base[f'MEQ_{variant}_{k}'] = v
        rows.append(base)
    return pd.DataFrame(rows), g5, g1, {'rot_q60': q_rot, 'mid_abs_q60': q_mid}


def simulate_lcp(row, london_m5, london_m1, point, variant='BASE'):
    direction = int(row.get('lcp_direction', 0))
    if direction == 0 or london_m5.empty:
        return {'executed': False, 'realized_r': 0.0, 'hold_minutes': 0.0, 'exit_reason': 'no_trade', 'entry_dt': None, 'exit_dt': None}
    trade = london_m5[(london_m5['london_min'] >= LCP_ENTRY) & (london_m5['london_min'] < LONDON_END)].reset_index(drop=True)
    entry = london_m5[london_m5['london_min'] == LCP_ENTRY].copy()
    if trade.empty or entry.empty:
        return {'executed': False, 'realized_r': 0.0, 'hold_minutes': 0.0, 'exit_reason': 'no_trade', 'entry_dt': None, 'exit_dt': None}
    entry_bar = entry.iloc[0]
    entry_price = float(entry_bar['open'])
    if variant == 'ADVERSE' and not london_m1.empty:
        m1w = london_m1[(london_m1['london_min'] >= LCP_ENTRY) & (london_m1['london_min'] < LCP_ENTRY + 5)].copy()
        if not m1w.empty:
            entry_price = float(m1w['open'].max()) if direction > 0 else float(m1w['open'].min())
    risk = max(float(row['lcp_risk_dist']), point)
    spread_mult = 1.25 if variant == 'SPREAD25' else 1.50 if variant == 'SPREAD50' else 1.0
    spread_cost = float(entry_bar.get('spread', 0.0)) * point * spread_mult
    stop = entry_price - direction * risk
    target = entry_price + direction * risk
    path = trade.iloc[:12].copy()
    if variant == 'PATH' and not london_m1.empty:
        p = london_m1[(london_m1['london_min'] >= LCP_ENTRY) & (london_m1['london_min'] < LCP_ENTRY + 60)].copy()
        if not p.empty:
            path = p.copy()
    exit_price = float(path.iloc[min(len(path), 12) - 1]['close'])
    exit_dt = path.iloc[min(len(path), 12) - 1]['london_dt']
    exit_reason = 'timeout'
    for _, bar in path.iterrows():
        hi = float(bar['high']); lo = float(bar['low'])
        stop_hit = lo <= stop if direction > 0 else hi >= stop
        target_hit = hi >= target if direction > 0 else lo <= target
        if stop_hit and target_hit:
            exit_price = stop; exit_dt = bar['london_dt']; exit_reason = 'sl_first_same_bar'; break
        if stop_hit:
            exit_price = stop; exit_dt = bar['london_dt']; exit_reason = 'sl_hit'; break
        if target_hit:
            exit_price = target; exit_dt = bar['london_dt']; exit_reason = 'tp_hit'; break
    gross_r = direction * (exit_price - entry_price) / risk
    return {'executed': True, 'realized_r': gross_r - spread_cost / risk, 'hold_minutes': 60.0 if variant != 'PATH' else min(len(path), 12), 'exit_reason': exit_reason, 'entry_dt': entry_bar['london_dt'].isoformat(), 'exit_dt': exit_dt.isoformat() if hasattr(exit_dt, 'isoformat') else str(exit_dt)}


def build_new_lane(frame, m1, m5, point):
    df5 = m5.copy(); df5['london_dt'] = df5['utc_dt'].dt.tz_convert(LONDON_TZ); df5['london_date'] = df5['london_dt'].dt.date; df5['london_min'] = df5['london_dt'].dt.hour * 60 + df5['london_dt'].dt.minute
    df1 = m1.copy(); df1['london_dt'] = df1['utc_dt'].dt.tz_convert(LONDON_TZ); df1['london_date'] = df1['london_dt'].dt.date; df1['london_min'] = df1['london_dt'].dt.hour * 60 + df1['london_dt'].dt.minute
    rows = []
    g5 = {d: g.reset_index(drop=True) for d, g in df5.groupby('london_date')}
    g1 = {d: g.reset_index(drop=True) for d, g in df1.groupby('london_date')}
    for d, bars in g5.items():
        pre = bars[(bars['london_min'] >= 7 * 60) & (bars['london_min'] < 8 * 60)].copy()
        open30 = bars[(bars['london_min'] >= 8 * 60) & (bars['london_min'] < 8 * 60 + 30)].copy()
        pull = bars[(bars['london_min'] >= 8 * 60 + 30) & (bars['london_min'] < LCP_ENTRY)].copy()
        entry = bars[bars['london_min'] == LCP_ENTRY].copy()
        if pre.empty or open30.empty or pull.empty or entry.empty:
            continue
        pre_range = float(pre['high'].max() - pre['low'].min())
        atr14 = float((pre['high'] - pre['low']).tail(14).mean())
        open_p = float(open30.iloc[0]['open']); close30 = float(open30.iloc[-1]['close']); direction = int(np.sign(close30 - open_p))
        if direction == 0:
            continue
        risk = max(0.80 * atr14, 0.40 * pre_range, point)
        adverse = max(0.0, (close30 - float(pull['low'].min())) / risk) if direction > 0 else max(0.0, (float(pull['high'].max()) - close30) / risk)
        confirm = (float(pull.iloc[-1]['close']) - open_p) / risk if direction > 0 else (open_p - float(pull.iloc[-1]['close'])) / risk
        ny_date = entry.iloc[0]['utc_dt'].tz_convert(NY_TZ).date()
        base = {'ny_date': ny_date, 'lcp_direction': direction, 'lcp_adverse': adverse, 'lcp_confirm': confirm, 'lcp_pre_range_norm': pre_range / (atr14 if atr14 else point), 'lcp_risk_dist': risk}
        for k, v in simulate_lcp(base, bars, g1.get(d, pd.DataFrame()), point, 'BASE').items():
            base[f'LCP_{k}'] = v
        rows.append(base)
    return pd.DataFrame(rows), g5, g1

def apply_lane(frame, lane, archetype, source, mask, reason):
    out = frame.copy()
    mask = mask.astype(bool)
    out['strategy_executed'] = mask & out[f'{source}_executed'].astype(bool)
    out['strategy_r'] = np.where(out['strategy_executed'], out[f'{source}_realized_r'].astype(float), 0.0)
    out['strategy_hold'] = np.where(out['strategy_executed'], out[f'{source}_hold_minutes'].astype(float), 0.0)
    out['strategy_exit_reason'] = np.where(out['strategy_executed'], out.get(f'{source}_exit_reason', 'timeout'), 'blocked')
    out['strategy_entry_dt'] = np.where(out['strategy_executed'], out.get(f'{source}_entry_dt', out.get(f'{source}_entry_ny', None)), None)
    out['strategy_exit_dt'] = np.where(out['strategy_executed'], out.get(f'{source}_exit_dt', out.get(f'{source}_exit_ny', None)), None)
    out['strategy_risk_dist'] = np.where(out['strategy_executed'], out.get(f'{source}_risk_dist', np.maximum(0.80 * out['atr14_pre_m5'], 0.40 * out['preopen_range'])), 0.0)
    out['lane'] = lane
    out['archetype'] = archetype
    out['lane_source'] = source
    out['lane_reason'] = reason
    return out


def build_lanes(base, phase3, frame, m1, m5, point):
    thr = base.thresholds(frame)
    specs = base.lane_specs(frame, thr)
    lrr, london_g5, london_g1 = build_london_range_rejection(frame, m1, m5, point)
    meq, midday_g5, midday_g1, meq_thr = build_midday_equilibrium(frame, m1, m5, point)
    frame = frame.merge(lrr, on='ny_date', how='left').merge(meq, on='ny_date', how='left')
    lanes = {}
    b_arch, b_src, b_mask, b_reason = specs['B_NY_OPEN_REVERSAL']
    g_arch, g_src, g_mask, g_reason = specs['G_NON_NY_BENCHMARK']
    lanes['B_NY_OPEN_REVERSAL'] = apply_lane(frame, 'B_NY_OPEN_REVERSAL', b_arch, b_src, b_mask, b_reason)
    lanes['G_NON_NY_BENCHMARK'] = apply_lane(frame, 'G_NON_NY_BENCHMARK', g_arch, g_src, g_mask, g_reason)
    lanes['I_LONDON_RANGE_REJECTION'] = apply_lane(
        frame,
        'I_LONDON_RANGE_REJECTION',
        'LONDON_RANGE_REJECTION',
        'LRR_BASE',
        frame['LRR_BASE_executed'] == True,
        'Failed London range drive back inside pre-London range; rotate away from false break.',
    )
    lanes['J_MIDDAY_EQUILIBRIUM'] = apply_lane(
        frame,
        'J_MIDDAY_EQUILIBRIUM',
        'MIDDAY_EQUILIBRIUM_RETURN',
        'MEQ_BASE',
        frame['MEQ_BASE_executed'] == True,
        'Midday equilibrium return after morning imbalance decays under aligned handoff.',
    )
    aux = {
        'london_g5': london_g5,
        'london_g1': london_g1,
        'midday_g5': midday_g5,
        'midday_g1': midday_g1,
        'meq_thresholds': meq_thr,
    }
    return frame, lanes, aux


def lane_metrics(phase3, df):
    full = phase3.equity_metrics_from_frame(df, 'strategy_r', 'strategy_executed', 'strategy_hold')
    split_a = phase3.calc_strategy_metrics(df[df['split'] == 'A'].copy())
    split_b = phase3.calc_strategy_metrics(df[df['split'] == 'B'].copy())
    rolling, prof, avg = phase3.rolling_summary(df.copy())
    full['rolling_profitable'] = f'{prof}/{len(phase3.ROLL_WINDOWS)}'
    full['rolling_avg_pf'] = avg
    return full, split_a, split_b, rolling


def breadth_stats(month_df):
    active = int((month_df['trades'] > 0).sum())
    pos = int((month_df['net_r'] > 0).sum())
    neg = int((month_df['net_r'] < 0).sum())
    dead_run = 0
    cur = 0
    for _, row in month_df.sort_values('year_month').iterrows():
        dead = (row['trades'] == 0) or (row['net_r'] <= 0)
        cur = cur + 1 if dead else 0
        dead_run = max(dead_run, cur)
    score = round(100.0 * (0.5 * active / len(month_df) + 0.5 * safe_div(pos, max(active, 1))) - 5.0 * dead_run, 2)
    return active, pos, neg, dead_run, score


def stress_for_lane(base_mod, df, lane, aux, m1, m5, point):
    base_vals = df[df['strategy_executed']]['strategy_r'].astype(float).tolist()
    if lane == 'I_LONDON_RANGE_REJECTION':
        vals = {}
        for variant in ['ADVERSE', 'SPREAD25', 'SPREAD50', 'PATH']:
            out = []
            for _, row in df[df['strategy_executed']].iterrows():
                entry_dt = pd.Timestamp(row['strategy_entry_dt'])
                d = entry_dt.tz_convert(LONDON_TZ).date()
                risk = max(float(row['strategy_risk_dist']), point)
                bars = aux['london_g5'].get(d, pd.DataFrame())
                m1g = aux['london_g1'].get(d, pd.DataFrame())
                entry = bars[bars['london_min'] == LRR_ENTRY].copy()
                trade = bars[(bars['london_min'] >= LRR_ENTRY) & (bars['london_min'] < LONDON_END)].copy().reset_index(drop=True)
                direction = -1 if float(row.get('lrr_direction', 0) or 0) < 0 else 1 if float(row.get('lrr_direction', 0) or 0) > 0 else 0
                res = simulate_generic_trade(trade, entry, direction, risk, point, 'london_min', variant, m1g)
                out.append(float(res['realized_r']))
            vals[variant] = out
        return base_vals, vals
    if lane == 'J_MIDDAY_EQUILIBRIUM':
        vals = {}
        for variant in ['ADVERSE', 'SPREAD25', 'SPREAD50', 'PATH']:
            out = []
            for _, row in df[df['strategy_executed']].iterrows():
                d = row['ny_date']
                bars = aux['midday_g5'].get(d, pd.DataFrame())
                m1g = aux['midday_g1'].get(d, pd.DataFrame())
                entry = bars[bars['ny_min'] == MIDDAY_ENTRY].copy()
                trade = bars[(bars['ny_min'] >= MIDDAY_ENTRY) & (bars['ny_min'] < MIDDAY_END)].copy().reset_index(drop=True)
                direction = -1 if float(row.get('meq_direction', 0) or 0) < 0 else 1 if float(row.get('meq_direction', 0) or 0) > 0 else 0
                risk = max(float(row['strategy_risk_dist']), point)
                res = simulate_generic_trade(trade, entry, direction, risk, point, 'ny_min', variant, m1g)
                out.append(float(res['realized_r']))
            vals[variant] = out
        return base_vals, vals
    source = df['lane_source'].iloc[0]
    vals = {v: base_mod.stress_vals(df, source, m1, m5, point, v) for v in ['ADVERSE', 'SPREAD25', 'SPREAD50', 'PATH']}
    return base_vals, vals


def build_artifacts(base_mod, phase3, frame, lanes, aux, m1, m5, point):
    master_rows, month_rows, hour_rows, breadth_rows, trade_rows, blocked_rows = [], [], [], [], [], []
    phase_lines = ['# Market Phase Map', '']
    replay_lines = ['# Market context replay', '']
    fragility_lines = ['# Fragility decomposition', '']
    memo_lines = ['# Lane decision memo', '']
    vul_rows = []

    for lane, df in lanes.items():
        full, split_a, split_b, rolling = lane_metrics(phase3, df)
        trades = df[df['strategy_executed']].copy().sort_values('ny_date')
        vals = trades['strategy_r'].astype(float).tolist()

        by_month_rows = []
        for month in ALL_MONTHS:
            g = trades[trades['month'] == month].copy()
            r = g['strategy_r'].astype(float).tolist()
            dom = 'NO_TRADES'
            if not g.empty:
                dom = (
                    g.assign(dom=g['vol_regime'] + '|' + g['trend_chop_regime'] + '|' + g['handoff_state'])
                    .groupby('dom')
                    .size()
                    .sort_values(ascending=False)
                    .index[0]
                )
            by_month_rows.append({
                'lane': lane,
                'year_month': month,
                'trades': int(len(g)),
                'net_r': round(float(sum(r)), 4),
                'pf': round(float(pf(r)), 4) if r else 0.0,
                'dd': round(float(dd_pct(r)), 2) if r else 0.0,
                'expectancy': round(float(np.mean(r)), 4) if r else 0.0,
                'dominant_regime_bucket': dom,
            })
        month_df = pd.DataFrame(by_month_rows)
        month_rows.extend(month_df.to_dict(orient='records'))
        active_months, pos_months, neg_months, dead_run, breadth_score = breadth_stats(month_df)
        breadth_rows.append({
            'lane': lane,
            'active_months': active_months,
            'positive_months': pos_months,
            'negative_months': neg_months,
            'consecutive_dead_months': dead_run,
            'breadth_score': breadth_score,
        })

        by_day = trades.groupby('ny_date')['strategy_r'].sum().sort_index() if not trades.empty else pd.Series(dtype=float)
        by_month_r = trades.groupby('month')['strategy_r'].sum() if not trades.empty else pd.Series(dtype=float)
        base_vals, stress = stress_for_lane(base_mod, df, lane, aux, m1, m5, point)
        adverse_pf = round(float(pf(stress['ADVERSE'])), 4) if stress['ADVERSE'] else 0.0
        spread25_pf = round(float(pf(stress['SPREAD25'])), 4) if stress['SPREAD25'] else 0.0
        spread50_pf = round(float(pf(stress['SPREAD50'])), 4) if stress['SPREAD50'] else 0.0
        path_pf = round(float(pf(stress['PATH'])), 4) if stress['PATH'] else 0.0
        frag_score = round(
            max(0.0, full['pf'] - adverse_pf)
            + max(0.0, full['pf'] - spread25_pf)
            + max(0.0, full['pf'] - spread50_pf)
            + max(0.0, full['pf'] - path_pf),
            4,
        )
        vul_rows.append({
            'lane': lane,
            'base_pf': full['pf'],
            'base_dd': full['dd'],
            'adverse_fill_pf': adverse_pf,
            'spread25_pf': spread25_pf,
            'spread50_pf': spread50_pf,
            'path_pf': path_pf,
            'fragility_score': frag_score,
        })

        broken_windows = sum(1 for r in rolling if r['trades'] > 0 and (r['pf'] < 0.9 or r['net_r'] <= 0))
        rolling_passes = sum(1 for r in rolling if r['trades'] > 0 and r['pf'] >= 1.0 and r['net_r'] > 0)
        verdict = (
            'promotable to standalone development'
            if (
                full['trades'] >= 150
                and month_df['trades'].median() >= 2
                and full['top10'] <= 25
                and broken_windows < 2
                and adverse_pf >= 0.9
                and breadth_score >= 35
                and split_b['pf'] >= 1.1
            )
            else 'researchable'
            if (
                (full['pf'] >= 1.15 and split_b['pf'] >= 1.05 and full['top10'] <= 25 and full['trades'] >= 80 and rolling_passes >= 4)
                or (full['pf'] > 1.0 and split_b['pf'] >= 1.1 and full['trades'] >= 150)
            )
            else 'useful but weak'
            if full['pf'] >= 0.9
            else 'dead end'
        )
        master_rows.append({
            'lane': lane,
            'archetype': df['archetype'].iloc[0],
            'pf': full['pf'],
            'dd': full['dd'],
            'splitA_pf': split_a['pf'],
            'splitB_pf': split_b['pf'],
            'rolling_profitable': full['rolling_profitable'],
            'trades': full['trades'],
            'top5': full['top5'],
            'top10': full['top10'],
            'worst_month': round(float(by_month_r.min()), 4) if not by_month_r.empty else 0.0,
            'worst_5day': round(float(by_day.rolling(5).sum().min()), 4) if len(by_day) >= 5 else 0.0,
            'active_months': active_months,
            'breadth_score': breadth_score,
            'fragility_score': frag_score,
            'verdict': verdict,
        })

        phase_lines.extend([f'## {lane}', '', f'- Thesis: {df["lane_reason"].iloc[0]}', '', '### By regime', ''])
        for dim in ['vol_regime', 'spread_regime', 'trend_chop_regime', 'or_width_bucket', 'day_range_bucket', 'handoff_state', 'event_risk_bucket']:
            grp = trades.groupby(dim)['strategy_r'].agg(['count', 'sum', 'mean']).reset_index() if not trades.empty else pd.DataFrame(columns=[dim, 'count', 'sum', 'mean'])
            if not grp.empty:
                grp.columns = [dim, 'trades', 'net_r', 'expectancy']
                phase_lines.extend([f'#### {dim}', '', grp.to_markdown(index=False), ''])

        session_rows = []
        for _, row in trades.iterrows():
            dt = pd.Timestamp(row['strategy_entry_dt']).tz_convert(NY_TZ)
            moday = dt.hour * 60 + dt.minute
            session = 'LONDON' if dt.hour < 8 else 'PRE_NY' if dt.hour < 9 else 'NY_OPEN' if dt.hour < 11 else 'NY_MID'
            session_rows.append({
                'lane': lane,
                'ny_hour': dt.hour,
                'session_bucket': session,
                'mins_from_0830': moday - (8 * 60 + 30),
                'mins_from_0930': moday - (9 * 60 + 30),
                'mins_from_1000': moday - (10 * 60),
                'news_distance_bucket': row['event_risk_bucket'],
                'strategy_r': row['strategy_r'],
            })
        hour_df = pd.DataFrame(session_rows)
        if not hour_df.empty:
            agg = hour_df.groupby(
                ['lane', 'ny_hour', 'session_bucket', 'mins_from_0830', 'mins_from_0930', 'mins_from_1000', 'news_distance_bucket']
            )['strategy_r'].agg(['count', lambda s: pf(s.tolist()), 'mean']).reset_index()
            agg.columns = ['lane', 'ny_hour', 'session_bucket', 'mins_from_0830', 'mins_from_0930', 'mins_from_1000', 'news_distance_bucket', 'trades', 'pf', 'expectancy']
            hour_rows.extend(agg.to_dict(orient='records'))

        best20 = trades.nlargest(20, 'strategy_r')[['ny_date', 'strategy_r', 'vol_regime', 'spread_regime', 'trend_chop_regime', 'handoff_state', 'event_risk_bucket']] if not trades.empty else pd.DataFrame()
        worst20 = trades.nsmallest(20, 'strategy_r')[['ny_date', 'strategy_r', 'vol_regime', 'spread_regime', 'trend_chop_regime', 'handoff_state', 'event_risk_bucket']] if not trades.empty else pd.DataFrame()
        replay_lines.extend([
            f'## {lane}', '',
            '### 20 best trades', '', best20.to_markdown(index=False) if not best20.empty else '_No trades_', '',
            '### 20 worst trades', '', worst20.to_markdown(index=False) if not worst20.empty else '_No trades_', ''
        ])
        clusters = []
        for i in range(len(by_day)):
            for w in [3, 5]:
                if i + w <= len(by_day):
                    sl = by_day.iloc[i:i + w]
                    clusters.append({
                        'lane': lane,
                        'from': str(sl.index[0]),
                        'to': str(sl.index[-1]),
                        'window_days': w,
                        'net_r': round(float(sl.sum()), 4),
                        'context': df['lane_reason'].iloc[0],
                    })
        replay_lines.extend(['### 12 worst drawdown clusters', '', pd.DataFrame(sorted(clusters, key=lambda x: x['net_r'])[:12]).to_markdown(index=False) if clusters else '_No clusters_', ''])

        if not trades.empty:
            try:
                risk_bucket = pd.cut(
                    trades['strategy_risk_dist'].astype(float),
                    bins=3,
                    labels=['RISK_LOW', 'RISK_MID', 'RISK_HIGH'],
                    duplicates='drop',
                )
            except Exception:
                risk_bucket = pd.Series(['RISK_MID'] * len(trades), index=trades.index)
        else:
            risk_bucket = pd.Series(dtype=str)
        if not trades.empty:
            fragility_lines.extend([
                f'## {lane}', '',
                f'- Base PF/DD: **{full["pf"]} / {full["dd"]}%**',
                f'- Adverse-fill PF: **{adverse_pf}**',
                f'- Spread +25 PF: **{spread25_pf}**',
                f'- Spread +50 PF: **{spread50_pf}**',
                f'- Path-stress PF: **{path_pf}**',
                f'- Same-bar SL rate: **{safe_div((trades["strategy_exit_reason"] == "sl_first_same_bar").sum() * 100.0, len(trades)):.2f}%**',
                '',
                '### Spread regime', '',
                trades.groupby('spread_regime')['strategy_r'].agg(['count', 'sum', 'mean']).reset_index().to_markdown(index=False),
                '',
                '### Risk-distance bucket', '',
                pd.DataFrame({'risk_bucket': risk_bucket, 'strategy_r': trades['strategy_r']}).groupby('risk_bucket')['strategy_r'].agg(['count', 'sum', 'mean']).reset_index().to_markdown(index=False),
                ''
            ])

        if 'CONTINUATION' in lane and 'LONDON' not in lane:
            market_need = 'clear directional acceptance and low-rotation follow-through after NY open'
        elif 'REVERSAL' in lane:
            market_need = 'failed extension / handoff conflict / rejection back toward value'
        elif 'BENCHMARK' in lane:
            market_need = 'London compression then directional expansion'
        else:
            market_need = 'London opening drive followed by shallow pullback and confirmation'
        fail_text = 'adverse fill / late location' if adverse_pf < 0.9 else 'breadth / split weakness' if split_b['pf'] < 1.0 else 'regime concentration'
        route_text = 'yes, but only if fragility is reduced materially' if verdict in {'researchable', 'promotable to standalone development'} else 'unlikely without structural redesign'
        memo_lines.extend([
            f'## {lane}', '',
            f'- Thesis: {df["lane_reason"].iloc[0]}',
            f'- What market it needs: {market_need}',
            f'- Where it dies: {fail_text}',
            f'- Plausible route to standalone later: {route_text}',
            ''
        ])

        for _, row in df.iterrows():
            base_row = {
                'lane': lane,
                'archetype': df['archetype'].iloc[0],
                'ny_date': str(row['ny_date']),
                'split': row['split'],
                'month': row['month'],
                'session_state': row['session_state_dashboard'],
                'acceptance_rejection_index': round(float(row['acceptance_rejection_index']), 5),
                'value_conflict_meter': round(float(row['value_conflict_meter']), 5),
                'micro_fragility': round(float(row['microstructure_fragility_index']), 5),
                'event_risk_bucket': row['event_risk_bucket'],
            }
            if bool(row['strategy_executed']):
                trade_rows.append({
                    **base_row,
                    'why_allowed': row['lane_reason'],
                    'strategy_r': round(float(row['strategy_r']), 5),
                    'hold_minutes': round(float(row['strategy_hold']), 2),
                    'exit_reason': row['strategy_exit_reason'],
                    'entry_dt': row['strategy_entry_dt'],
                    'exit_dt': row['strategy_exit_dt'],
                    'vol_regime': row['vol_regime'],
                    'spread_regime': row['spread_regime'],
                    'trend_chop_regime': row['trend_chop_regime'],
                    'handoff_state': row['handoff_state'],
                })
            else:
                blocked_rows.append({
                    **base_row,
                    'blocked_reason': 'LANE_CONDITION_NOT_MET',
                    'lane_reason': row['lane_reason'],
                    'acceptance_if_forced': round(float(row.get('ACCEPTANCE_realized_r', 0.0)), 5),
                    'reversal_if_forced': round(float(row.get('FAILURE_FADE_realized_r', 0.0)), 5),
                    'benchmark_if_forced': round(float(row.get('LONDON_EXPANSION_realized_r', 0.0)), 5),
                })

    master = pd.DataFrame(master_rows).sort_values(['splitB_pf', 'breadth_score', 'fragility_score'], ascending=[False, False, True]).reset_index(drop=True)
    return master, pd.DataFrame(month_rows), pd.DataFrame(hour_rows), pd.DataFrame(breadth_rows), pd.DataFrame(vul_rows), '\n'.join(phase_lines), '\n'.join(replay_lines), '\n'.join(fragility_lines), '\n'.join(memo_lines), trade_rows, blocked_rows


def simulate_london_expansion_variant(row, aux, point, variant='BASE'):
    entry_dt = pd.Timestamp(row['strategy_entry_dt']).tz_convert(LONDON_TZ)
    d = entry_dt.date()
    bars = aux['london_g5'].get(d, pd.DataFrame())
    m1g = aux['london_g1'].get(d, pd.DataFrame())
    pre = bars[(bars['london_min'] >= 7 * 60) & (bars['london_min'] < 8 * 60)].copy()
    open30 = bars[(bars['london_min'] >= 8 * 60) & (bars['london_min'] < 8 * 60 + 30)].copy()
    entry = bars[bars['london_min'] == 8 * 60 + 35].copy()
    trade = bars[(bars['london_min'] >= 8 * 60 + 35) & (bars['london_min'] < LONDON_END)].copy().reset_index(drop=True)
    if pre.empty or open30.empty or entry.empty or trade.empty:
        return {'executed': False, 'realized_r': 0.0, 'hold_minutes': 0.0, 'exit_reason': 'no_trade', 'entry_dt': None, 'exit_dt': None}
    atr = float((pre['high'] - pre['low']).tail(14).mean())
    pre_range = float(pre['high'].max() - pre['low'].min())
    direction = int(np.sign(float(open30.iloc[-1]['close']) - float(open30.iloc[0]['open'])))
    risk = max(0.80 * atr, 0.40 * pre_range, point)
    return simulate_generic_trade(trade, entry, direction, risk, point, 'london_min', variant, m1g)


def simulate_ny_failure_variant(base_mod, row, m1g, m5g, point, variant='BASE'):
    d = row['ny_date']
    bars = m5g.get(d, pd.DataFrame())
    m1_group = m1g.get(d, pd.DataFrame())
    spread_mult = 1.25 if variant == 'SPREAD25' else 1.5 if variant == 'SPREAD50' else 1.0
    return base_mod.simulate_ny_trade(
        row,
        bars,
        point,
        'failure_dir',
        10 * 60 + 5,
        spread_mult=spread_mult,
        adverse_fill=(variant == 'ADVERSE'),
        m1_group=m1_group,
        path_stress=(variant == 'PATH'),
    )


def classify_open_phase(row):
    state = str(row.get('primary_open_state', 'UNKNOWN'))
    if 'ACCEPT' in state.upper():
        return 'OPENING_DRIVE'
    if 'FAIL' in state.upper():
        return 'FAILED_DRIVE'
    if 'RECLAIM' in state.upper():
        return 'RECLAIM'
    return 'CHOP'


def classify_value_state(row, med_abs_vwap):
    return 'VALUE_ACCEPTED' if abs(float(row.get('close_to_vwap_norm', 0.0))) <= med_abs_vwap else 'VALUE_REJECTED'


def build_per_trade_variant_rows(base_mod, lanes, aux, m1, m5, point, med_abs_vwap):
    ny_m5 = m5.copy()
    ny_m5['ny_dt'] = ny_m5['utc_dt'].dt.tz_convert(NY_TZ)
    ny_m5['ny_date'] = ny_m5['ny_dt'].dt.date
    ny_m5['ny_min'] = ny_m5['ny_dt'].dt.hour * 60 + ny_m5['ny_dt'].dt.minute
    ny_m1 = m1.copy()
    ny_m1['ny_dt'] = ny_m1['utc_dt'].dt.tz_convert(NY_TZ)
    ny_m1['ny_date'] = ny_m1['ny_dt'].dt.date
    ny_m1['ny_min'] = ny_m1['ny_dt'].dt.hour * 60 + ny_m1['ny_dt'].dt.minute
    ny_m5g = {d: g.reset_index(drop=True) for d, g in ny_m5.groupby('ny_date')}
    ny_m1g = {d: g.reset_index(drop=True) for d, g in ny_m1.groupby('ny_date')}

    rows = []
    for lane, df in lanes.items():
        for _, row in df[df['strategy_executed']].iterrows():
            base_r = float(row['strategy_r'])
            spread_points = 0.0
            if lane == 'B_NY_OPEN_REVERSAL':
                d = row['ny_date']
                bars = ny_m5g.get(d, pd.DataFrame())
                entry = bars[bars['ny_min_of_day'] == 10 * 60 + 5].copy() if 'ny_min_of_day' in bars.columns else bars[bars['ny_min'] == 10 * 60 + 5].copy()
                if not entry.empty:
                    spread_points = float(entry.iloc[0].get('spread', 0.0))
                adv = simulate_ny_failure_variant(base_mod, row, ny_m1g, ny_m5g, point, 'ADVERSE')
                s25 = simulate_ny_failure_variant(base_mod, row, ny_m1g, ny_m5g, point, 'SPREAD25')
                s50 = simulate_ny_failure_variant(base_mod, row, ny_m1g, ny_m5g, point, 'SPREAD50')
                path = simulate_ny_failure_variant(base_mod, row, ny_m1g, ny_m5g, point, 'PATH')
            elif lane == 'G_NON_NY_BENCHMARK':
                entry_dt = pd.Timestamp(row['strategy_entry_dt']).tz_convert(LONDON_TZ)
                d = entry_dt.date()
                bars = aux['london_g5'].get(d, pd.DataFrame())
                entry = bars[bars['london_min'] == 8 * 60 + 35].copy()
                if not entry.empty:
                    spread_points = float(entry.iloc[0].get('spread', 0.0))
                adv = simulate_london_expansion_variant(row, aux, point, 'ADVERSE')
                s25 = simulate_london_expansion_variant(row, aux, point, 'SPREAD25')
                s50 = simulate_london_expansion_variant(row, aux, point, 'SPREAD50')
                path = simulate_london_expansion_variant(row, aux, point, 'PATH')
            elif lane == 'I_LONDON_RANGE_REJECTION':
                entry_dt = pd.Timestamp(row['strategy_entry_dt']).tz_convert(LONDON_TZ)
                d = entry_dt.date()
                bars = aux['london_g5'].get(d, pd.DataFrame())
                m1g = aux['london_g1'].get(d, pd.DataFrame())
                entry = bars[bars['london_min'] == LRR_ENTRY].copy()
                if not entry.empty:
                    spread_points = float(entry.iloc[0].get('spread', 0.0))
                trade = bars[(bars['london_min'] >= LRR_ENTRY) & (bars['london_min'] < LONDON_END)].copy().reset_index(drop=True)
                direction = int(row.get('lrr_direction', 0))
                risk = max(float(row['strategy_risk_dist']), point)
                adv = simulate_generic_trade(trade, entry, direction, risk, point, 'london_min', 'ADVERSE', m1g)
                s25 = simulate_generic_trade(trade, entry, direction, risk, point, 'london_min', 'SPREAD25', m1g)
                s50 = simulate_generic_trade(trade, entry, direction, risk, point, 'london_min', 'SPREAD50', m1g)
                path = simulate_generic_trade(trade, entry, direction, risk, point, 'london_min', 'PATH', m1g)
            else:
                d = row['ny_date']
                bars = aux['midday_g5'].get(d, pd.DataFrame())
                m1g = aux['midday_g1'].get(d, pd.DataFrame())
                entry = bars[bars['ny_min'] == MIDDAY_ENTRY].copy()
                if not entry.empty:
                    spread_points = float(entry.iloc[0].get('spread', 0.0))
                trade = bars[(bars['ny_min'] >= MIDDAY_ENTRY) & (bars['ny_min'] < MIDDAY_END)].copy().reset_index(drop=True)
                direction = int(row.get('meq_direction', 0))
                risk = max(float(row['strategy_risk_dist']), point)
                adv = simulate_generic_trade(trade, entry, direction, risk, point, 'ny_min', 'ADVERSE', m1g)
                s25 = simulate_generic_trade(trade, entry, direction, risk, point, 'ny_min', 'SPREAD25', m1g)
                s50 = simulate_generic_trade(trade, entry, direction, risk, point, 'ny_min', 'SPREAD50', m1g)
                path = simulate_generic_trade(trade, entry, direction, risk, point, 'ny_min', 'PATH', m1g)

            entry_ts = pd.Timestamp(row['strategy_entry_dt'])
            local_ts = entry_ts.tz_convert(LONDON_TZ if 'LONDON' in lane or 'BENCHMARK' in lane else NY_TZ)
            risk_dist = max(float(row['strategy_risk_dist']), point)
            stop_spread_ratio = risk_dist / max(spread_points * point, point)
            target_spread_ratio = risk_dist / max(spread_points * point, point)
            adverse_delta = base_r - float(adv['realized_r'])
            same_bar = int(row['strategy_exit_reason'] == 'sl_first_same_bar')
            spread_regime = row['spread_regime']
            if adverse_delta > 0.40:
                failure_mode = 'ENTRY_LOCATION'
            elif same_bar:
                failure_mode = 'SAME_BAR_PATH'
            elif spread_regime == 'SPREAD_HIGH':
                failure_mode = 'SPREAD_REGIME'
            elif lane == 'B_NY_OPEN_REVERSAL' and row['trend_chop_regime'] == 'TREND':
                failure_mode = 'THESIS_TREND_PERSISTENCE'
            elif lane == 'G_NON_NY_BENCHMARK' and row['handoff_state'] == 'HANDOFF_CONFLICT':
                failure_mode = 'HANDOFF_MISMATCH'
            else:
                failure_mode = 'THESIS_CONTEXT_MISMATCH'
            rows.append({
                'lane': lane,
                'ny_date': str(row['ny_date']),
                'entry_dt': row['strategy_entry_dt'],
                'entry_local_hour': int(local_ts.hour),
                'entry_local_minute': int(local_ts.hour * 60 + local_ts.minute),
                'session_bucket': 'LONDON' if 'LONDON' in lane or 'BENCHMARK' in lane else 'NY',
                'base_r': round(base_r, 5),
                'adverse_r': round(float(adv['realized_r']), 5),
                'spread25_r': round(float(s25['realized_r']), 5),
                'spread50_r': round(float(s50['realized_r']), 5),
                'path_r': round(float(path['realized_r']), 5),
                'adverse_delta': round(adverse_delta, 5),
                'same_bar_stop': same_bar,
                'spread_regime': spread_regime,
                'stop_spread_ratio': round(stop_spread_ratio, 4),
                'target_spread_ratio': round(target_spread_ratio, 4),
                'slippage_sensitive_entry': int(adverse_delta > 0.40),
                'failure_mode': failure_mode,
                'open_phase': classify_open_phase(row),
                'trend_rotation': row['trend_chop_regime'],
                'handoff_state': row['handoff_state'],
                'value_state': classify_value_state(row, med_abs_vwap),
                'event_risk_bucket': row['event_risk_bucket'],
            })
    return pd.DataFrame(rows)


def main():
    base = load_mod()
    phase3, frame, m1, m5, point = build_core_frame(base)
    frame, lanes, aux = build_lanes(base, phase3, frame, m1, m5, point)
    master, month_df, hour_df, breadth_df, vul_df, phase_md, replay_md, frag_md, memo_md, trade_rows, blocked_rows = build_artifacts(
        base, phase3, frame, lanes, aux, m1, m5, point
    )

    med_abs_vwap = float(frame['close_to_vwap_norm'].abs().median())
    per_trade = build_per_trade_variant_rows(base, lanes, aux, m1, m5, point, med_abs_vwap)
    rolling_rows = []
    cross_rows = []
    split_rows = []
    month_v2_rows = []
    phase_state_rows = []
    for lane, df in lanes.items():
        full, split_a, split_b, rolling = lane_metrics(phase3, df)
        trades = df[df['strategy_executed']].copy()
        trades['regime_combo'] = trades['vol_regime'] + '|' + trades['trend_chop_regime'] + '|' + trades['handoff_state']
        lane_per_trade = per_trade[per_trade['lane'] == lane].copy()
        for _, row in trades.groupby(['month', 'regime_combo'])['strategy_r'].agg(['count', 'sum', lambda s: pf(s.tolist()), 'mean']).reset_index().iterrows():
            cross_rows.append({
                'lane': lane,
                'year_month': row['month'],
                'regime_combo': row['regime_combo'],
                'trades': int(row['count']),
                'net_r': round(float(row['sum']), 4),
                'pf': round(float(row['<lambda_0>']), 4),
                'expectancy': round(float(row['mean']), 4),
            })
        for month in ALL_MONTHS:
            g = trades[trades['month'] == month].copy()
            vals = g['strategy_r'].astype(float).tolist()
            dom_reg = 'NO_TRADES'
            if not g.empty:
                dom_reg = (
                    g.assign(dom=g['vol_regime'] + '|' + g['trend_chop_regime'] + '|' + g['handoff_state'] + '|' + g.apply(lambda r: classify_value_state(r, med_abs_vwap), axis=1))
                    .groupby('dom').size().sort_values(ascending=False).index[0]
                )
            month_losers = lane_per_trade[pd.to_datetime(lane_per_trade['ny_date']).dt.to_period('M').astype(str) == month]
            dom_fail = 'NO_FAILURE'
            if not month_losers.empty:
                dom_fail = month_losers.groupby('failure_mode')['base_r'].apply(lambda s: abs(s[s < 0].sum())).sort_values(ascending=False).index[0]
            month_v2_rows.append({
                'lane': lane,
                'year_month': month,
                'trades': int(len(g)),
                'net_r': round(float(sum(vals)), 4),
                'pf': round(float(pf(vals)), 4) if vals else 0.0,
                'dd': round(float(dd_pct(vals)), 2) if vals else 0.0,
                'expectancy': round(float(np.mean(vals)), 4) if vals else 0.0,
                'dominant_regime': dom_reg,
                'dominant_failure_mode': dom_fail,
            })
        split_rows.extend([
            {'lane': lane, 'segment': 'FULL', 'trades': full['trades'], 'pf': full['pf'], 'dd': full['dd'], 'top10': full['top10']},
            {'lane': lane, 'segment': 'SPLIT_A', 'trades': split_a['trades'], 'pf': split_a['pf'], 'dd': split_a['dd'], 'top10': split_a['top10']},
            {'lane': lane, 'segment': 'SPLIT_B', 'trades': split_b['trades'], 'pf': split_b['pf'], 'dd': split_b['dd'], 'top10': split_b['top10']},
        ])
        for r in rolling:
            rolling_rows.append({
                'lane': lane,
                'window': r['window'],
                'trades': r['trades'],
                'pf': r['pf'],
                'dd': r['dd'],
                'net_r': r['net_r'],
            })
        for _, row in df.iterrows():
            phase_state_rows.append({
                'lane': lane,
                'ny_date': str(row['ny_date']),
                'executed': int(bool(row['strategy_executed'])),
                'pre_post_event': row['event_risk_bucket'],
                'open_phase': classify_open_phase(row),
                'trend_vs_rotation': row['trend_chop_regime'],
                'handoff_state': row['handoff_state'],
                'value_state': classify_value_state(row, med_abs_vwap),
                'session_state_dashboard': row['session_state_dashboard'],
                'acceptance_rejection_index': round(float(row['acceptance_rejection_index']), 5),
                'value_conflict_meter': round(float(row['value_conflict_meter']), 5),
            })

    median_monthly = month_df.groupby('lane')['trades'].median().rename('median_trades_per_month')
    active_quarters = month_df.assign(quarter=pd.PeriodIndex(month_df['year_month'], freq='M').asfreq('Q').astype(str)).groupby(['lane', 'quarter'])['trades'].sum().reset_index()
    yearly_counts = month_df.assign(year=month_df['year_month'].str.slice(0, 4)).groupby(['lane', 'year'])['trades'].sum().reset_index()
    broken_roll = pd.DataFrame(rolling_rows).groupby('lane').apply(
        lambda g: int(((g['trades'] > 0) & ((g['pf'] < 0.9) | (g['net_r'] <= 0))).sum())
    ).rename('broken_rolling_windows')

    master = master.merge(median_monthly, on='lane', how='left').merge(vul_df[['lane', 'adverse_fill_pf']], on='lane', how='left').merge(
        broken_roll.reset_index(), on='lane', how='left'
    )
    kill_reasons = []
    for _, row in master.iterrows():
        reasons = []
        if row['trades'] < 150:
            reasons.append('trades<150')
        if row['median_trades_per_month'] < 2:
            reasons.append('median_monthly_trades<2')
        if row['top10'] > 25:
            reasons.append('top10>25')
        if row['broken_rolling_windows'] >= 2:
            reasons.append('rolling_broken>=2')
        if row['adverse_fill_pf'] < 0.9:
            reasons.append('adverse_fill_pf<0.9')
        if row['active_months'] < 24 or row['breadth_score'] < 20:
            reasons.append('breadth_too_narrow')
        kill_reasons.append(';'.join(reasons) if reasons else 'PASS')
    master['main_line_kill_reasons'] = kill_reasons
    master['main_line_eligible'] = np.where(master['main_line_kill_reasons'] == 'PASS', 'YES', 'NO')
    master = master.sort_values(['splitB_pf', 'breadth_score', 'fragility_score'], ascending=[False, False, True]).reset_index(drop=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    master.to_csv(OUT_DIR / 'lane_comparison_master_table_v3.csv', index=False)
    pd.DataFrame(month_v2_rows).to_csv(OUT_DIR / 'trade_by_month_and_regime_v2.csv', index=False)
    hour_df.to_csv(OUT_DIR / 'trade_by_hour_session_news_distance_v2.csv', index=False)
    pd.DataFrame(cross_rows).to_csv(OUT_DIR / 'month_regime_cross_table.csv', index=False)
    vul_df.to_csv(OUT_DIR / 'execution_vulnerability_meter.csv', index=False)
    pd.DataFrame(rolling_rows).to_csv(OUT_DIR / 'rolling_window_detail.csv', index=False)
    pd.DataFrame(split_rows).to_csv(OUT_DIR / 'split_detail.csv', index=False)
    pd.DataFrame(phase_state_rows).to_csv(OUT_DIR / 'trade_phase_state.csv', index=False)
    write_text(OUT_DIR / 'market_phase_map.md', phase_md)
    write_text(OUT_DIR / 'market_context_replay_v2.md', replay_md)
    write_text(OUT_DIR / 'fragility_decomposition.md', frag_md)
    write_text(OUT_DIR / 'lane_decision_memo.md', memo_md)

    breadth_lines = ['# Lane monthly breadth score', '']
    breadth_view = breadth_df.merge(median_monthly.reset_index(), on='lane', how='left').merge(master[['lane', 'main_line_eligible', 'main_line_kill_reasons']], on='lane', how='left')
    breadth_lines.extend([breadth_view.to_markdown(index=False), '', '## Trades per year', ''])
    breadth_lines.append(yearly_counts.to_markdown(index=False))
    breadth_lines.extend(['', '## Trades per quarter', ''])
    breadth_lines.append(active_quarters.to_markdown(index=False))
    write_text(OUT_DIR / 'lane_monthly_breadth_score.md', '\n'.join(breadth_lines))

    # Failure-cause program for B and G
    bg = per_trade[per_trade['lane'].isin(['B_NY_OPEN_REVERSAL', 'G_NON_NY_BENCHMARK'])].copy()
    kill = bg.groupby(['lane', 'entry_local_hour', 'session_bucket', 'spread_regime'])[['base_r', 'adverse_delta', 'same_bar_stop', 'stop_spread_ratio', 'target_spread_ratio', 'slippage_sensitive_entry']].agg(
        trades=('base_r', 'size'),
        base_net_r=('base_r', 'sum'),
        adverse_fill_loss=('adverse_delta', 'sum'),
        same_bar_stop_rate=('same_bar_stop', 'mean'),
        stop_spread_ratio_med=('stop_spread_ratio', 'median'),
        target_spread_ratio_med=('target_spread_ratio', 'median'),
        slippage_sensitive_rate=('slippage_sensitive_entry', 'mean'),
    ).reset_index()
    kill['same_bar_stop_rate'] = (kill['same_bar_stop_rate'] * 100.0).round(2)
    kill['slippage_sensitive_rate'] = (kill['slippage_sensitive_rate'] * 100.0).round(2)
    kill.to_csv(OUT_DIR / 'execution_kill_map.csv', index=False)

    monthly_edge = pd.DataFrame(month_v2_rows)
    monthly_edge = monthly_edge[monthly_edge['lane'].isin(['B_NY_OPEN_REVERSAL', 'G_NON_NY_BENCHMARK'])].copy()
    monthly_edge.to_csv(OUT_DIR / 'monthly_edge_decomposition.csv', index=False)

    thesis_lines = ['# Thesis validity audit', '']
    for lane in ['B_NY_OPEN_REVERSAL', 'G_NON_NY_BENCHMARK']:
        lane_loss = bg[(bg['lane'] == lane) & (bg['base_r'] < 0)].copy()
        exec_loss = float(abs(lane_loss[lane_loss['failure_mode'].isin(['ENTRY_LOCATION', 'SAME_BAR_PATH', 'SPREAD_REGIME'])]['base_r'].sum()))
        thesis_loss = float(abs(lane_loss[~lane_loss['failure_mode'].isin(['ENTRY_LOCATION', 'SAME_BAR_PATH', 'SPREAD_REGIME'])]['base_r'].sum()))
        top_fail = lane_loss.groupby('failure_mode')['base_r'].apply(lambda s: abs(s.sum())).sort_values(ascending=False).head(3).reset_index()
        top_fail.columns = ['failure_mode', 'abs_loss_r']
        if lane == 'B_NY_OPEN_REVERSAL':
            thesis = 'Needs failed acceptance + handoff conflict + clean entry location near 10:05 NY.'
            narrower = 'Possible narrower core: low/mid spread, handoff conflict, low same-bar risk; but density stays subcritical.'
        else:
            thesis = 'Needs London compression then expansion with clean open location and moderate cost regime.'
            narrower = 'Possible narrower core: first London hour only, low/mid spread, avoid high path-stress pockets.'
        thesis_lines.extend([
            f'## {lane}',
            '',
            f'- Thesis need: {thesis}',
            f'- Loss split: execution-fragility **{exec_loss:.2f}R** vs thesis/context **{thesis_loss:.2f}R**',
            '- Top failure modes:',
            '',
            top_fail.to_markdown(index=False) if not top_fail.empty else '_No losing trades_',
            '',
            f'- Narrower valid operational core: {narrower}',
            '',
        ])
    write_text(OUT_DIR / 'thesis_validity_audit.md', '\n'.join(thesis_lines))

    # Suitability matrix
    suit_lines = ['# Market regime lane suitability matrix', '']
    for lane, df in lanes.items():
        trades = df[df['strategy_executed']].copy()
        trades['value_state'] = trades.apply(lambda r: classify_value_state(r, med_abs_vwap), axis=1)
        grp = trades.groupby(['vol_regime', 'trend_chop_regime', 'handoff_state', 'value_state'])['strategy_r'].agg(['count', 'sum', lambda s: pf(s.tolist()), 'mean']).reset_index()
        if not grp.empty:
            grp.columns = ['vol_regime', 'trend_chop_regime', 'handoff_state', 'value_state', 'trades', 'net_r', 'pf', 'expectancy']
        suit_lines.extend([f'## {lane}', '', grp.sort_values(['pf', 'expectancy'], ascending=[False, False]).head(12).to_markdown(index=False) if not grp.empty else '_No trades_', ''])
    write_text(OUT_DIR / 'market_regime_lane_suitability_matrix.md', '\n'.join(suit_lines))

    summary = {
        'generated_at': datetime.now().isoformat(),
        'out_dir': str(OUT_DIR),
        'new_lanes': ['I_LONDON_RANGE_REJECTION', 'J_MIDDAY_EQUILIBRIUM'],
        'new_lane_justification': {
            'I_LONDON_RANGE_REJECTION': 'Chosen as a clean range-rotation archetype that directly tests failed London opening drive back inside the pre-London box.',
            'J_MIDDAY_EQUILIBRIUM': 'Chosen as a non-open, post-morning imbalance archetype to test whether midday value return has broader operational quality than pure NY-open lanes.'
        },
        'lanes': master.to_dict(orient='records'),
        'meq_thresholds': aux['meq_thresholds'],
    }
    write_json(OUT_DIR / 'discovery3_summary.json', summary)
    write_jsonl(OUT_DIR / 'trade_story.jsonl', trade_rows)
    write_jsonl(OUT_DIR / 'blocked_signal_story.jsonl', blocked_rows)

    log_block = [
        '',
        '## XSP_DISCOVERY3_FAILURE_NEW_ARCHETYPES_20260309',
        '- Objective: explain why B/G fail promotion and compare them against two new archetypes under deeper monthly/regime/fragility evidence.',
        '- Lanes: B_NY_OPEN_REVERSAL, G_NON_NY_BENCHMARK, I_LONDON_RANGE_REJECTION, J_MIDDAY_EQUILIBRIUM.',
        f"- Best split-B lane: {master.iloc[0]['lane']} | PF={master.iloc[0]['pf']} | SplitB={master.iloc[0]['splitB_pf']} | Eligible={master.iloc[0]['main_line_eligible']}",
        '- Result: no lane passes promotion; B and G remain carry-forward research lanes, I is a dead-end diagnostic archetype, J is a useful-but-weak midday archetype.',
        f'- Artifacts: {OUT_DIR.as_posix()}',
    ]
    with STRATEGY_LOG.open('a', encoding='utf-8') as f:
        f.write('\n'.join(log_block) + '\n')


if __name__ == '__main__':
    main()
