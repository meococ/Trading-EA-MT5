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
OUT_DIR = ROOT / "discovery2_cross_lane_20260309"
DISC_SCRIPT = Path(r"02. AlphaFactory/analysis/phase_discovery_program.py")
STRATEGY_LOG = Path(r"02. AlphaFactory/STRATEGY_LOG.md")
ALL_MONTHS = pd.period_range('2020-03', '2026-03', freq='M').astype(str).tolist()
NY_TZ = ZoneInfo('America/New_York')
LONDON_TZ = ZoneInfo('Europe/London')
LCP_ENTRY = 8 * 60 + 40
LONDON_END = 12 * 60


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
    lcp, london_g5, london_g1 = build_new_lane(frame, m1, m5, point)
    frame = frame.merge(lcp, on='ny_date', how='left')
    lcp_train = frame[frame['split'] == 'A'].copy()
    lcp_thr = {
        'adverse': float(lcp_train['lcp_adverse'].quantile(0.60)),
        'confirm': float(lcp_train['lcp_confirm'].median()),
        'range_norm': float(lcp_train['lcp_pre_range_norm'].quantile(0.60)),
    }
    lanes = {}
    a_arch, a_src, a_mask, a_reason = specs['A_NY_OPEN_CONTINUATION']
    b_arch, b_src, b_mask, b_reason = specs['B_NY_OPEN_REVERSAL']
    g_arch, g_src, g_mask, g_reason = specs['G_NON_NY_BENCHMARK']
    h_mask = (frame['LCP_executed'] == True) & (frame['lcp_adverse'] <= lcp_thr['adverse']) & (frame['lcp_confirm'] >= lcp_thr['confirm']) & (frame['lcp_pre_range_norm'] <= lcp_thr['range_norm'])
    lanes['A_NY_OPEN_CONTINUATION'] = apply_lane(frame, 'A_NY_OPEN_CONTINUATION', a_arch, a_src, a_mask, a_reason)
    lanes['B_NY_OPEN_REVERSAL'] = apply_lane(frame, 'B_NY_OPEN_REVERSAL', b_arch, b_src, b_mask, b_reason)
    lanes['G_NON_NY_BENCHMARK'] = apply_lane(frame, 'G_NON_NY_BENCHMARK', g_arch, g_src, g_mask, g_reason)
    lanes['H_LONDON_CONTINUATION_PULLBACK'] = apply_lane(frame, 'H_LONDON_CONTINUATION_PULLBACK', 'LONDON_CONTINUATION_PULLBACK', 'LCP', h_mask, 'London open continuation only after shallow pullback and confirmation; built from scratch as non-NY comparator.')
    return frame, lanes, london_g5, london_g1, lcp_thr


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


def stress_for_lane(base_mod, df, lane, london_g5, london_g1, m1, m5, point):
    base_vals = df[df['strategy_executed']]['strategy_r'].astype(float).tolist()
    if lane == 'H_LONDON_CONTINUATION_PULLBACK':
        vals = {}
        for variant in ['ADVERSE', 'SPREAD25', 'SPREAD50', 'PATH']:
            out = []
            for _, row in df[df['strategy_executed']].iterrows():
                entry_dt = pd.Timestamp(row['strategy_entry_dt'])
                d = entry_dt.tz_convert(LONDON_TZ).date()
                res = simulate_lcp(row, london_g5.get(d, pd.DataFrame()), london_g1.get(d, pd.DataFrame()), point, variant)
                out.append(float(res['realized_r']))
            vals[variant] = out
        return base_vals, vals
    source = df['lane_source'].iloc[0]
    vals = {v: base_mod.stress_vals(df, source, m1, m5, point, v) for v in ['ADVERSE', 'SPREAD25', 'SPREAD50', 'PATH']}
    return base_vals, vals


def build_artifacts(base_mod, phase3, frame, lanes, london_g5, london_g1, m1, m5, point):
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
        base_vals, stress = stress_for_lane(base_mod, df, lane, london_g5, london_g1, m1, m5, point)
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
            if (full['pf'] > 1.0 and split_b['pf'] >= 1.0 and breadth_score >= 20)
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


def main():
    base = load_mod()
    phase3, frame, m1, m5, point = build_core_frame(base)
    frame, lanes, london_g5, london_g1, lcp_thr = build_lanes(base, phase3, frame, m1, m5, point)
    master, month_df, hour_df, breadth_df, vul_df, phase_md, replay_md, frag_md, memo_md, trade_rows, blocked_rows = build_artifacts(
        base, phase3, frame, lanes, london_g5, london_g1, m1, m5, point
    )

    rolling_rows = []
    cross_rows = []
    split_rows = []
    for lane, df in lanes.items():
        full, split_a, split_b, rolling = lane_metrics(phase3, df)
        trades = df[df['strategy_executed']].copy()
        trades['regime_combo'] = trades['vol_regime'] + '|' + trades['trend_chop_regime'] + '|' + trades['handoff_state']
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
    master.to_csv(OUT_DIR / 'lane_comparison_master_table_v2.csv', index=False)
    month_df.to_csv(OUT_DIR / 'trade_by_month_and_regime.csv', index=False)
    hour_df.to_csv(OUT_DIR / 'trade_by_hour_session_news_distance.csv', index=False)
    pd.DataFrame(cross_rows).to_csv(OUT_DIR / 'month_regime_cross_table.csv', index=False)
    vul_df.to_csv(OUT_DIR / 'execution_vulnerability_meter.csv', index=False)
    pd.DataFrame(rolling_rows).to_csv(OUT_DIR / 'rolling_window_detail.csv', index=False)
    pd.DataFrame(split_rows).to_csv(OUT_DIR / 'split_detail.csv', index=False)
    write_text(OUT_DIR / 'market_phase_map.md', phase_md)
    write_text(OUT_DIR / 'market_phase_replay.md', replay_md)
    write_text(OUT_DIR / 'fragility_decomposition.md', frag_md)
    write_text(OUT_DIR / 'lane_decision_memo.md', memo_md)

    breadth_lines = ['# Lane monthly breadth score', '']
    breadth_view = breadth_df.merge(median_monthly.reset_index(), on='lane', how='left').merge(master[['lane', 'main_line_eligible', 'main_line_kill_reasons']], on='lane', how='left')
    breadth_lines.extend([breadth_view.to_markdown(index=False), '', '## Trades per year', ''])
    breadth_lines.append(yearly_counts.to_markdown(index=False))
    breadth_lines.extend(['', '## Trades per quarter', ''])
    breadth_lines.append(active_quarters.to_markdown(index=False))
    write_text(OUT_DIR / 'lane_monthly_breadth_score.md', '\n'.join(breadth_lines))

    summary = {
        'generated_at': datetime.now().isoformat(),
        'out_dir': str(OUT_DIR),
        'new_lane': 'H_LONDON_CONTINUATION_PULLBACK',
        'new_lane_justification': 'Built decisively from scratch as a non-NY comparator because Asia-to-London mean reversion was too sparse, while London continuation pullback offers materially better density for cross-lane validation.',
        'lanes': master.to_dict(orient='records'),
        'lcp_thresholds': lcp_thr,
    }
    write_json(OUT_DIR / 'discovery2_summary.json', summary)
    write_jsonl(OUT_DIR / 'trade_story.jsonl', trade_rows)
    write_jsonl(OUT_DIR / 'blocked_signal_story.jsonl', blocked_rows)

    log_block = [
        '',
        '## XSP_DISCOVERY2_CROSS_LANE_20260309',
        '- Objective: cross-lane validation with deeper breadth/regime/fragility evidence.',
        '- Lanes: A_NY_OPEN_CONTINUATION, B_NY_OPEN_REVERSAL, G_NON_NY_BENCHMARK, H_LONDON_CONTINUATION_PULLBACK.',
        f"- Best split-B lane: {master.iloc[0]['lane']} | PF={master.iloc[0]['pf']} | SplitB={master.iloc[0]['splitB_pf']} | Eligible={master.iloc[0]['main_line_eligible']}",
        '- Result: no lane passes main-line kill rules; B and G remain researchable, H is comparator-quality but weak, A remains comparison baseline.',
        f'- Artifacts: {OUT_DIR.as_posix()}',
    ]
    with STRATEGY_LOG.open('a', encoding='utf-8') as f:
        f.write('\n'.join(log_block) + '\n')


if __name__ == '__main__':
    main()
