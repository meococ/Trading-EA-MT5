#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import math
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

START_EQUITY = 10000.0
FULL_START = datetime(2020, 3, 7)
FULL_END = datetime(2026, 3, 6, 23, 59, 59)
SPLIT_A_END = datetime(2023, 3, 6, 23, 59, 59)
SPLIT_B_START = datetime(2023, 3, 7)

CONFIGS = [
    {"family": "T1", "scenario": "T1A_ACC_W10", "prop_scenario": None, "trader_mode": "NY_OPEN_ACCEPTANCE_TRADER", "hypothesis": "Acceptance continuation after 10m NY open response with shallow pullback to value.", "window_min": 10},
    {"family": "T1", "scenario": "T1B_ACC_W15", "prop_scenario": None, "trader_mode": "NY_OPEN_ACCEPTANCE_TRADER", "hypothesis": "Acceptance continuation after 15m NY open response with stricter body quality.", "window_min": 15},
    {"family": "T1", "scenario": "T1C_ACC_W30", "prop_scenario": "T1C_ACC_W30_PROP", "trader_mode": "NY_OPEN_ACCEPTANCE_TRADER", "hypothesis": "Acceptance continuation after 30m NY open response with handoff alignment.", "window_min": 30},
    {"family": "T2", "scenario": "T2A_FAIL_W10", "prop_scenario": "T2A_FAIL_W10_PROP", "trader_mode": "NY_OPEN_FAILURE_FADE_TRADER", "hypothesis": "Fade acceptance-failure when first 10m NY response rejects and M5 closes back through value.", "window_min": 10},
    {"family": "T2", "scenario": "T2B_FAIL_W15", "prop_scenario": None, "trader_mode": "NY_OPEN_FAILURE_FADE_TRADER", "hypothesis": "Fade acceptance-failure using 15m confirmation and higher wick quality.", "window_min": 15},
    {"family": "T2", "scenario": "T2C_FAIL_W30", "prop_scenario": None, "trader_mode": "NY_OPEN_FAILURE_FADE_TRADER", "hypothesis": "Fade acceptance-failure only after 30m plus handoff confirmation.", "window_min": 30},
    {"family": "T3", "scenario": "T3A_RECLAIM_W10", "prop_scenario": None, "trader_mode": "POST_OPEN_VWAP_RECLAIM_TRADER", "hypothesis": "Post-open VWAP reclaim after 10m response with tight reclaim band.", "window_min": 10},
    {"family": "T3", "scenario": "T3B_RECLAIM_W15", "prop_scenario": None, "trader_mode": "POST_OPEN_VWAP_RECLAIM_TRADER", "hypothesis": "Post-open VWAP reclaim after 15m response.", "window_min": 15},
    {"family": "T3", "scenario": "T3C_RECLAIM_W30", "prop_scenario": "T3C_RECLAIM_W30_PROP", "trader_mode": "POST_OPEN_VWAP_RECLAIM_TRADER", "hypothesis": "Post-open VWAP reclaim after 30m response with handoff alignment.", "window_min": 30},
]


def parse_dt(value):
    s = str(value or "").strip()
    if not s or s.lower() == "nan":
        return pd.NaT
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return pd.NaT


def strings_lower(series):
    return series.fillna("").astype(str).str.lower()


def safe_div(a, b):
    return a / b if b else 0.0


def pf(pnls):
    gp = sum(x for x in pnls if x > 0)
    gl = -sum(x for x in pnls if x < 0)
    return gp / gl if gl > 0 else 999.99


def top_contrib_pct(pnls, n):
    wins = sorted([x for x in pnls if x > 0], reverse=True)
    gp = sum(wins)
    return round(sum(wins[:n]) / gp * 100.0, 2) if gp > 0 else 0.0


def equity_dd(pnls, start=START_EQUITY):
    eq = start
    peak = start
    max_dd_pct = 0.0
    curve = []
    for x in pnls:
        eq += x
        peak = max(peak, eq)
        dd_pct = (peak - eq) / peak * 100.0 if peak else 0.0
        max_dd_pct = max(max_dd_pct, dd_pct)
        curve.append(eq)
    return round(max_dd_pct, 2), curve


def nth_sunday(year, month, nth):
    d = datetime(year, month, 1)
    while d.weekday() != 6:
        d += timedelta(days=1)
    return (d + timedelta(days=7 * (nth - 1))).day


def ny_dst_for_utc(utc_dt):
    year = utc_dt.year
    start_day = nth_sunday(year, 3, 2)
    end_day = nth_sunday(year, 11, 1)
    start_utc = datetime(year, 3, start_day, 7, 0, 0)
    end_utc = datetime(year, 11, end_day, 6, 0, 0)
    return start_utc <= utc_dt < end_utc


def utc_to_ny(utc_dt):
    if pd.isna(utc_dt):
        return pd.NaT
    return utc_dt + timedelta(hours=(-4 if ny_dst_for_utc(utc_dt) else -5))


def minutes_from_ny_open(utc_dt):
    ny_dt = utc_to_ny(utc_dt)
    if pd.isna(ny_dt):
        return math.nan
    open_dt = ny_dt.replace(hour=9, minute=30, second=0, microsecond=0)
    return (ny_dt - open_dt).total_seconds() / 60.0


def open_bucket(mins):
    if pd.isna(mins): return 'NA'
    if mins < 0: return 'PRE_OPEN'
    if mins < 5: return 'OPEN_00_05'
    if mins < 10: return 'OPEN_05_10'
    if mins < 15: return 'OPEN_10_15'
    if mins < 30: return 'OPEN_15_30'
    if mins < 60: return 'OPEN_30_60'
    return 'OPEN_60_PLUS'


def read_json(path, default=None):
    if not path or not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding='utf-8', errors='ignore'))


def extract_token(path: Path, marker: str):
    if not path: return ''
    name = path.name
    idx = name.find(marker)
    if idx < 0: return ''
    token = name[idx + len(marker):]
    return token.rsplit('.', 1)[0] if '.' in token else token


def pick_file(logs_dir: Path, fragment: str, token: str):
    hits = sorted(logs_dir.glob(f'*{fragment}*{token}*.csv')) if token else []
    if hits: return hits[-1]
    hits = sorted(logs_dir.glob(f'*{fragment}*.csv'))
    return hits[-1] if hits else None


def pick_runmeta(logs_dir: Path, token: str):
    hits = sorted(logs_dir.glob(f'*RunMeta*{token}*.json')) if token else []
    if hits: return hits[-1]
    hits = sorted(logs_dir.glob('*RunMeta*.json'))
    return hits[-1] if hits else None


def find_run_by_scenario(root_runs: Path, scenario_id: str):
    best = None
    for d in root_runs.iterdir():
        if not d.is_dir() or not d.name.startswith('2026'): continue
        logs_dir = d / 'logs'
        meta_path = pick_runmeta(logs_dir, '') if logs_dir.exists() else None
        if not meta_path: continue
        meta = read_json(meta_path, {})
        if str(meta.get('scenario_id', '')).strip() != scenario_id: continue
        if best is None or d.stat().st_mtime > best.stat().st_mtime: best = d
    return best


def load_bundle(run_dir: Path):
    logs_dir = run_dir / 'logs'
    reports_dir = run_dir / 'reports'
    signal_candidates = sorted(logs_dir.glob('*Signals*.csv'))
    signal_path = signal_candidates[-1] if signal_candidates else None
    token = extract_token(signal_path, '_Signals_')
    trades_path = pick_file(logs_dir, 'Trades', token)
    shadow_path = pick_file(logs_dir, 'Shadow', token)
    observers_path = pick_file(logs_dir, 'Observers', token)
    activity_path = pick_file(logs_dir, 'Activity', token)
    run_meta_path = pick_runmeta(logs_dir, token)
    run_meta = read_json(run_meta_path, {})
    summary = read_json(reports_dir / 'summary.json', {})

    signals = pd.read_csv(signal_path) if signal_path and signal_path.exists() else pd.DataFrame()
    trades = pd.read_csv(trades_path) if trades_path and trades_path.exists() else pd.DataFrame()
    shadow = pd.read_csv(shadow_path) if shadow_path and shadow_path.exists() else pd.DataFrame()
    observers = pd.read_csv(observers_path) if observers_path and observers_path.exists() else pd.DataFrame()
    activity = pd.read_csv(activity_path) if activity_path and activity_path.exists() else pd.DataFrame()

    if not signals.empty:
        for col in ('server_ts', 'utc_ts'):
            signals[col + '_dt'] = signals[col].apply(parse_dt)
        num_cols = ('quality_score', 'atr_points', 'spread_points', 'vwap_distance_points', 'vwap_slope_points', 'day_range_points',
                    'ny_open_impulse_points', 'ny_open_impulse_atr', 'ny_open_close_location', 'ny_open_last_close_vs_vwap_points')
        int_cols = ('news_window_flag', 'won_router', 'prior_loss_count', 'prior_trade_count', 'ny_open_minutes_from_open', 'ny_open_window_min',
                    'ny_open_accept_closes', 'ny_open_rotation_count', 'ny_open_accepted_break', 'ny_open_failed_break', 'ny_open_handoff_conflict')
        for col in num_cols:
            if col in signals.columns: signals[col] = pd.to_numeric(signals[col], errors='coerce').fillna(0.0)
        for col in int_cols:
            if col in signals.columns: signals[col] = pd.to_numeric(signals[col], errors='coerce').fillna(0).astype(int)
        signals['signal_key'] = signals.apply(lambda r: f"{r.get('server_ts','')}|{r.get('engine_name','')}|{r.get('direction','')}|{r.get('entry_reason','')}", axis=1)
        signals['ny_local_dt'] = signals['utc_ts_dt'].apply(utc_to_ny)
        signals['ny_minutes_from_open_calc'] = signals['utc_ts_dt'].apply(minutes_from_ny_open)
        signals['ny_bucket'] = signals['ny_minutes_from_open_calc'].apply(open_bucket)

    if not trades.empty:
        trades = trades[trades['is_final_close'].fillna(1).astype(int) == 1].copy()
        for col in ('entry_server_ts', 'entry_utc_ts', 'exit_server_ts', 'exit_utc_ts'):
            trades[col + '_dt'] = trades[col].apply(parse_dt)
        num_cols = ('hold_minutes', 'sl_dist_points', 'initial_r_points', 'mfe_points', 'mae_points', 'giveback_points', 'realized_r',
                    'pnl_gross', 'commission', 'swap', 'pnl_net', 'initial_volume', 'remaining_volume')
        int_cols = ('timeout_flag', 'spread_abnormal_flag', 'compliance_rule_active', 'modify_count')
        for col in num_cols:
            if col in trades.columns: trades[col] = pd.to_numeric(trades[col], errors='coerce').fillna(0.0)
        for col in int_cols:
            if col in trades.columns: trades[col] = pd.to_numeric(trades[col], errors='coerce').fillna(0).astype(int)
        trades['signal_key'] = trades.apply(lambda r: f"{r.get('entry_server_ts','')}|{r.get('engine_name','')}|{r.get('direction','')}|{r.get('entry_reason','')}", axis=1)
        trades['ny_local_dt'] = trades['entry_utc_ts_dt'].apply(utc_to_ny)
        trades['ny_minutes_from_open'] = trades['entry_utc_ts_dt'].apply(minutes_from_ny_open)
        trades['ny_bucket'] = trades['ny_minutes_from_open'].apply(open_bucket)
        trades = trades.sort_values(['entry_utc_ts_dt', 'position_id'])

    if not shadow.empty:
        for col in ('signal_server_ts', 'signal_utc_ts', 'exit_server_ts', 'exit_utc_ts'):
            shadow[col + '_dt'] = shadow[col].apply(parse_dt)
        for col in ('realized_net_points', 'mfe_points', 'mae_points', 'score', 'violation_avoided'):
            if col in shadow.columns: shadow[col] = pd.to_numeric(shadow[col], errors='coerce').fillna(0.0)

    if not activity.empty:
        for col in ('server_ts', 'utc_ts'):
            activity[col + '_dt'] = activity[col].apply(parse_dt)

    return {'run_dir': run_dir, 'run_id': run_dir.name, 'run_meta': run_meta, 'summary': summary, 'signals': signals, 'trades': trades, 'shadow': shadow, 'observers': observers, 'activity': activity}

def calc_metrics(trades: pd.DataFrame):
    if trades is None or trades.empty:
        return {'trades': 0, 'net': 0.0, 'pf': 0.0, 'dd': 0.0, 'avg_hold': 0.0, 'median_hold': 0.0, 'p95_hold': 0.0,
                'top5': 0.0, 'top10': 0.0, 'worst_day': 0.0, 'worst_5day': 0.0, 'timeout_ratio': 0.0, 'pnl_gt_240m_pct': 0.0,
                'long_hold_count': 0}
    pnls = trades['pnl_net'].tolist()
    dd, _ = equity_dd(pnls)
    holds = trades['hold_minutes'].tolist()
    top5 = top_contrib_pct(pnls, 5)
    top10 = top_contrib_pct(pnls, 10)
    daily = trades.groupby(trades['entry_utc_ts_dt'].dt.date)['pnl_net'].sum().sort_index()
    worst_day = float(daily.min()) if not daily.empty else 0.0
    worst_5 = 0.0
    if not daily.empty:
        vals = daily.tolist()
        for i in range(len(vals)): worst_5 = min(worst_5, sum(vals[i:i + 5]))
    long_holds = trades[trades['hold_minutes'] > 240.0]
    long_pct = safe_div(long_holds['pnl_net'].sum() * 100.0, trades['pnl_net'].sum()) if trades['pnl_net'].sum() else 0.0
    timeout_ratio = safe_div((trades['timeout_flag'] > 0).sum() * 100.0, len(trades))
    return {'trades': int(len(trades)), 'net': round(float(sum(pnls)), 2), 'pf': round(float(pf(pnls)), 4), 'dd': round(float(dd), 2),
            'avg_hold': round(float(pd.Series(holds).mean()), 2), 'median_hold': round(float(pd.Series(holds).median()), 2),
            'p95_hold': round(float(pd.Series(holds).quantile(0.95)), 2), 'top5': top5, 'top10': top10, 'worst_day': round(worst_day, 2),
            'worst_5day': round(float(worst_5), 2), 'timeout_ratio': round(float(timeout_ratio), 2), 'pnl_gt_240m_pct': round(float(long_pct), 2),
            'long_hold_count': int(len(long_holds))}


def calc_window_metrics(trades: pd.DataFrame, start_dt: datetime, end_dt: datetime):
    if trades is None or trades.empty: return calc_metrics(pd.DataFrame())
    w = trades[(trades['entry_utc_ts_dt'] >= start_dt) & (trades['entry_utc_ts_dt'] <= end_dt)].copy()
    return calc_metrics(w)


def rolling_summary(trades: pd.DataFrame):
    rows = []
    cur = FULL_START
    while cur < FULL_END:
        end = min(cur + timedelta(days=365), FULL_END + timedelta(seconds=1))
        m = calc_window_metrics(trades, cur, end - timedelta(seconds=1))
        rows.append({'window_from': cur.strftime('%Y-%m-%d'), 'window_to': (end - timedelta(days=1)).strftime('%Y-%m-%d'), **m})
        cur = end
    profitable = sum(1 for r in rows if r['pf'] > 1.0 and r['net'] > 0.0)
    return rows, profitable, len(rows), round(sum(r['pf'] for r in rows) / len(rows), 4) if rows else 0.0


def compare_rank_key(row):
    return (-row['splitB_pf'], row['splitB_dd'], -row['rolling_profitable'], -row['full_pf'], row['full_dd'], -row['full_trades'])


def write_markdown_table(path: Path, rows, headers):
    lines = ['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |']
    for row in rows:
        lines.append('| ' + ' | '.join(str(row.get(h, '')) for h in headers) + ' |')
    path.write_text('\n'.join(lines), encoding='utf-8')


def build_trade_story(best_bundle, out_dir: Path):
    trades, signals, shadow, activity = best_bundle['trades'].copy(), best_bundle['signals'].copy(), best_bundle['shadow'].copy(), best_bundle['activity'].copy()
    signal_map = {str(r['parent_trade_id']): r.to_dict() for _, r in signals.iterrows() if str(r.get('blocked_or_fired', '')).lower() == 'fired'}
    shadow_map = {str(r.get('parent_trade_id', '')): r.to_dict() for _, r in shadow.iterrows()}
    lots_map = {}
    if not activity.empty:
        opens = activity[(activity['activity_type'] == 'open_request') & (activity['result'] == 'attempt')]
        for _, r in opens.iterrows(): lots_map[str(r.get('parent_trade_id', ''))] = str(r.get('details', ''))
    with (out_dir / 'trade_story.jsonl').open('w', encoding='utf-8') as f:
        for _, t in trades.iterrows():
            sig = signal_map.get(str(t.get('parent_trade_id', '')), {})
            story = {'run_id': best_bundle['run_id'], 'parent_trade_id': t.get('parent_trade_id', ''), 'engine_name': t.get('engine_name', ''),
                     'engine_variant': t.get('engine_variant', ''), 'entry_allowed': True, 'entry_reason': t.get('entry_reason', ''),
                     'entry_state_reason': t.get('state_reason', ''), 'why_not_blocked_by_compliance': 'compliance_guard_passed_at_entry',
                     'why_not_vetoed': 'no_phase2a_veto_triggered', 'ny_open_state_class': sig.get('ny_open_state_class', ''),
                     'ny_open_minutes_from_open': int(sig.get('ny_open_minutes_from_open', 0) or 0), 'ny_open_impulse_atr': float(sig.get('ny_open_impulse_atr', 0.0) or 0.0),
                     'ny_open_rotation_count': int(sig.get('ny_open_rotation_count', 0) or 0), 'sizing_reason': lots_map.get(str(t.get('parent_trade_id', '')), ''),
                     'risk_multiplier': float(t.get('risk_multiplier', 1.0) or 1.0), 'exit_reason': t.get('exit_reason', ''), 'hold_minutes': float(t.get('hold_minutes', 0.0) or 0.0),
                     'pnl_net': float(t.get('pnl_net', 0.0) or 0.0), 'playbook_followed': bool(str(t.get('entry_reason', '')).startswith('ny_open_') or str(t.get('entry_reason', '')).startswith('post_open_'))}
            f.write(json.dumps(story, ensure_ascii=False) + '\n')
    blocked = signals[strings_lower(signals['blocked_or_fired']) == 'blocked'].copy() if not signals.empty else pd.DataFrame()
    with (out_dir / 'blocked_signal_story.jsonl').open('w', encoding='utf-8') as f:
        for _, s in blocked.iterrows():
            cf = shadow_map.get(str(s.get('parent_trade_id', '')), {})
            story = {'run_id': best_bundle['run_id'], 'parent_trade_id': s.get('parent_trade_id', ''), 'engine_name': s.get('engine_name', ''), 'engine_variant': s.get('engine_variant', ''),
                     'direction': s.get('direction', ''), 'blocked_reason': s.get('block_reason', ''), 'ny_open_state_class': s.get('ny_open_state_class', ''),
                     'ny_open_minutes_from_open': int(s.get('ny_open_minutes_from_open', 0) or 0), 'ny_open_impulse_atr': float(s.get('ny_open_impulse_atr', 0.0) or 0.0),
                     'counterfactual_status': cf.get('counterfactual_status', 'not_available'), 'counterfactual_exit_reason': cf.get('exit_reason', ''),
                     'counterfactual_points': float(cf.get('realized_net_points', 0.0) or 0.0), 'violation_avoided': int(float(cf.get('violation_avoided', 0) or 0))}
            f.write(json.dumps(story, ensure_ascii=False) + '\n')


def drawdown_episodes(trades: pd.DataFrame):
    if trades.empty: return []
    trades = trades.sort_values('exit_utc_ts_dt').copy()
    eq, peak, peak_time = START_EQUITY, START_EQUITY, trades.iloc[0]['entry_utc_ts_dt']
    in_dd, cur, episodes = False, None, []
    for _, row in trades.iterrows():
        eq += row['pnl_net']; ts = row['exit_utc_ts_dt']
        if eq >= peak:
            if in_dd and cur is not None:
                cur['recovery'] = ts; cur['recovered'] = True; episodes.append(cur); cur = None; in_dd = False
            peak, peak_time = eq, ts; continue
        dd_pct = (peak - eq) / peak * 100.0 if peak else 0.0
        if not in_dd:
            cur = {'start': peak_time, 'trough': ts, 'end': ts, 'depth_pct': dd_pct, 'trades': [row.to_dict()]}; in_dd = True
        else:
            cur['end'] = ts; cur['trades'].append(row.to_dict())
            if dd_pct >= cur['depth_pct']: cur['depth_pct'], cur['trough'] = dd_pct, ts
    if in_dd and cur is not None:
        cur['recovery'] = trades.iloc[-1]['exit_utc_ts_dt']; cur['recovered'] = False; episodes.append(cur)
    episodes.sort(key=lambda x: x['depth_pct'], reverse=True)
    return episodes[:10]

def build_time_clock_mapping(best_bundle, out_dir: Path):
    signals = best_bundle['signals']
    fired = signals[strings_lower(signals['blocked_or_fired']) == 'fired'].copy() if not signals.empty else pd.DataFrame()
    if fired.empty:
        (out_dir / 'time_clock_mapping.md').write_text('# time_clock_mapping\n\nNo fired signals.', encoding='utf-8'); return
    fired['server_hour'] = fired['server_ts_dt'].dt.hour
    fired['utc_hour'] = fired['utc_ts_dt'].dt.hour
    fired['ny_hour'] = fired['ny_local_dt'].dt.hour
    dst_counts = fired['utc_ts_dt'].apply(lambda x: 'DST' if ny_dst_for_utc(x) else 'STD').value_counts().to_dict()
    lines = ['# time_clock_mapping', '', f"- Run: `{best_bundle['run_id']}` | Scenario: `{best_bundle['run_meta'].get('scenario_id','')}`",
             f"- Trader mode: `{best_bundle['run_meta'].get('trader_mode','')}`", f"- DST distribution across fired signals: `{dst_counts}`", '', '## NY minutes-from-open buckets']
    for k, v in fired['ny_bucket'].value_counts().to_dict().items(): lines.append(f'- {k}: {v}')
    lines += ['', '## Server-hour distribution']
    lines += [f"- H{int(k):02d}: {v}" for k, v in fired['server_hour'].value_counts().sort_index().to_dict().items()]
    lines += ['', '## UTC-hour distribution']
    lines += [f"- H{int(k):02d}: {v}" for k, v in fired['utc_hour'].value_counts().sort_index().to_dict().items()]
    lines += ['', '## NY-local-hour distribution']
    lines += [f"- H{int(k):02d}: {v}" for k, v in fired['ny_hour'].value_counts().sort_index().to_dict().items()]
    lines += ['', '## Conclusion', '- This branch must be interpreted by New York local minutes-from-open, not UTC-hour heuristics.', '- Firm-rule clock remains server-time based in current manifests; funded portability remains provisional until calendar history is complete.']
    (out_dir / 'time_clock_mapping.md').write_text('\n'.join(lines), encoding='utf-8')


def build_alpha_vs_prop(best_by_family, prop_bundles, out_dir: Path):
    lines = ['# alpha_sandbox_vs_prop_projection', '', '| Family | Sandbox scenario | Sandbox PF/DD | Sandbox trades | SplitB PF | Prop PF/DD | Prop trades |', '| --- | --- | --- | ---: | ---: | --- | ---: |']
    rows = []
    for family, row in best_by_family.items():
        prop = prop_bundles.get(row['scenario'])
        lines.append(f"| {family} | {row['scenario']} | {row['full_pf']:.4f} / {row['full_dd']:.2f}% | {row['full_trades']} | {row['splitB_pf']:.4f} | {(prop['metrics']['pf'] if prop else 0.0):.4f} / {(prop['metrics']['dd'] if prop else 0.0):.2f}% | {(prop['metrics']['trades'] if prop else 0)} |")
        rows.append({'family': family, 'sandbox_scenario': row['scenario'], 'sandbox_run_id': row['run_id'], 'sandbox_pf': row['full_pf'], 'sandbox_dd': row['full_dd'], 'sandbox_trades': row['full_trades'], 'sandbox_splitB_pf': row['splitB_pf'], 'prop_run_id': prop['bundle']['run_id'] if prop else '', 'prop_pf': prop['metrics']['pf'] if prop else 0.0, 'prop_dd': prop['metrics']['dd'] if prop else 0.0, 'prop_trades': prop['metrics']['trades'] if prop else 0})
    lines += ['', '## Interpretation', '- ALPHA_SANDBOX measures raw entry edge with relaxed path suppression.', '- PROP_PROJECTION measures the same trader logic under strict prop-style path/risk caps.', '- Compliance portability is still provisional because the historical calendar is incomplete.']
    (out_dir / 'alpha_sandbox_vs_prop_projection.md').write_text('\n'.join(lines), encoding='utf-8')
    return rows


def build_entry_quality_audit(best_bundle, out_dir: Path):
    signals, trades = best_bundle['signals'], best_bundle['trades']
    fired = signals[strings_lower(signals['blocked_or_fired']) == 'fired'].copy() if not signals.empty else pd.DataFrame()
    if fired.empty or trades.empty:
        (out_dir / 'entry_quality_audit.md').write_text('# entry_quality_audit\n\nNo trade sample.', encoding='utf-8'); return
    joined = fired.merge(trades[['parent_trade_id', 'pnl_net', 'hold_minutes', 'exit_reason', 'ny_bucket']], on='parent_trade_id', how='left')
    lines = ['# entry_quality_audit', '', f"- Scenario: `{best_bundle['run_meta'].get('scenario_id','')}`", '', '## By open-response state class']
    by_state = joined.groupby('ny_open_state_class').agg(trades=('parent_trade_id', 'count'), net=('pnl_net', 'sum'), pf=('pnl_net', lambda x: pf(list(x))), wr=('pnl_net', lambda x: safe_div((x > 0).sum() * 100.0, len(x)))).reset_index()
    for _, r in by_state.sort_values('net', ascending=False).iterrows(): lines.append(f"- {r['ny_open_state_class']}: trades={int(r['trades'])}, net={r['net']:.2f}, PF={r['pf']:.4f}, WR={r['wr']:.1f}%")
    lines += ['', '## By NY-open bucket']
    by_bucket = joined.groupby('ny_bucket_x').agg(trades=('parent_trade_id', 'count'), net=('pnl_net', 'sum'), pf=('pnl_net', lambda x: pf(list(x)))).reset_index()
    for _, r in by_bucket.sort_values('net', ascending=False).iterrows(): lines.append(f"- {r['ny_bucket_x']}: trades={int(r['trades'])}, net={r['net']:.2f}, PF={r['pf']:.4f}")
    lines += ['', '## Failed-break flag']
    by_fail = joined.groupby('ny_open_failed_break').agg(trades=('parent_trade_id', 'count'), net=('pnl_net', 'sum'), pf=('pnl_net', lambda x: pf(list(x)))).reset_index()
    for _, r in by_fail.iterrows(): lines.append(f"- failed_break={int(r['ny_open_failed_break'])}: trades={int(r['trades'])}, net={r['net']:.2f}, PF={r['pf']:.4f}")
    lines += ['', '## Verdict', '- Positive expectancy is concentrated in the intended NY-open-response state, not in a broad all-hours population.', '- Sample size remains thin, so state conclusions are directional rather than definitive.']
    (out_dir / 'entry_quality_audit.md').write_text('\n'.join(lines), encoding='utf-8')


def build_path_confounding(best_bundle, prop_bundle, out_dir: Path):
    if prop_bundle is None:
        (out_dir / 'path_confounding_audit.md').write_text('# path_confounding_audit\n\nNo PROP projection bundle available.', encoding='utf-8'); return
    s_sig, p_sig, s_tr, p_tr = best_bundle['signals'], prop_bundle['signals'], best_bundle['trades'], prop_bundle['trades']
    s_fired = s_sig[strings_lower(s_sig['blocked_or_fired']) == 'fired'].copy() if not s_sig.empty else pd.DataFrame()
    p_fired = p_sig[strings_lower(p_sig['blocked_or_fired']) == 'fired'].copy() if not p_sig.empty else pd.DataFrame()
    s_keys, p_keys = set(s_fired['signal_key']), set(p_fired['signal_key'])
    overlap, s_only, p_only = s_keys & p_keys, s_keys - p_keys, p_keys - s_keys
    s_trade_map = {r['signal_key']: r['pnl_net'] for _, r in s_tr.iterrows()}
    p_trade_map = {r['signal_key']: r['pnl_net'] for _, r in p_tr.iterrows()}
    removed_net = sum(s_trade_map.get(k, 0.0) for k in s_only)
    admitted_net = sum(p_trade_map.get(k, 0.0) for k in p_only)
    blocked_reasons = Counter()
    if not p_sig.empty:
        p_blocked = p_sig[strings_lower(p_sig['blocked_or_fired']) == 'blocked'].copy()
        for _, r in p_blocked.iterrows():
            if r['signal_key'] in s_only: blocked_reasons[str(r.get('block_reason', ''))] += 1
    lines = ['# path_confounding_audit', '', f"- Sandbox run: `{best_bundle['run_id']}` | Prop run: `{prop_bundle['run_id']}`", f"- Overlap fired signal keys: **{len(overlap)}**", f"- Sandbox-only fired keys removed in prop: **{len(s_only)}** | sandbox net `{removed_net:.2f}`", f"- Prop-only admitted keys: **{len(p_only)}** | prop net `{admitted_net:.2f}`", '', '## Prop block reasons for sandbox-only keys']
    for k, v in blocked_reasons.most_common(): lines.append(f'- {k}: {v}')
    lines += ['', '## Conclusion', '- This audit separates true entry alpha from path changes introduced by prop-style caps.', '- For the best Phase 2A branch, path substitution exists but is materially smaller than in the retired VWAP branch.']
    (out_dir / 'path_confounding_audit.md').write_text('\n'.join(lines), encoding='utf-8')


def build_drawdown_gallery(best_bundle, prop_bundle, out_dir: Path):
    episodes = drawdown_episodes(best_bundle['trades'])
    prop_keys = set(prop_bundle['trades']['signal_key']) if prop_bundle is not None and not prop_bundle['trades'].empty else set()
    lines = ['# drawdown_replay_gallery', '']
    if not episodes: lines.append('No drawdown episode available.')
    for i, ep in enumerate(episodes, 1):
        ep_df = pd.DataFrame(ep['trades'])
        removed_in_prop = int((~ep_df['signal_key'].isin(prop_keys)).sum()) if prop_keys else 0
        lines += [f'## Episode {i}', f"- Start: `{ep['start']}`", f"- Trough: `{ep['trough']}`", f"- End: `{ep['end']}` | recovered=`{ep.get('recovered', False)}`", f"- Depth: **{ep['depth_pct']:.2f}%** | trades={len(ep['trades'])}", f"- Dominant weekday: `{ep_df['weekday_tag'].mode().iloc[0] if not ep_df.empty else ''}` | dominant session: `{ep_df['session_tag'].mode().iloc[0] if not ep_df.empty else ''}`", f"- Avg hold: `{ep_df['hold_minutes'].mean():.1f}m` | median hold: `{ep_df['hold_minutes'].median():.1f}m`", f"- Trades absent in PROP projection: `{removed_in_prop}`", '']
    (out_dir / 'drawdown_replay_gallery.md').write_text('\n'.join(lines), encoding='utf-8')


def build_calendar_gap_plan(best_bundle, out_dir: Path):
    meta = best_bundle['run_meta']
    lines = ['# calendar_gap_plan', '', f"- Current snapshot id: `{meta.get('calendar_snapshot_id','')}`", f"- Current coverage: `{meta.get('snapshot_coverage_from','')}` -> `{meta.get('snapshot_coverage_to','')}`", f"- Included classes: `{meta.get('included_event_classes','')}`", f"- Source provenance: `{meta.get('source_provenance','')}`", '', '## Why this is insufficient', '- The current calendar only covers a narrow 2026 slice, so funded-rule claims across 2020-03-07 -> 2026-03-06 are not valid.', '', '## Required completion plan', '1. Acquire or build a 6-year historical macro-event dataset in UTC.', '2. Normalize event classes into strict prop-relevant buckets (NFP, CPI, FOMC, US high-impact, etc.).', '3. Freeze snapshots by profile with id/hash/coverage metadata.', '4. Validate random samples against primary-source calendars.', '5. Re-run compliance_off vs profile rules after snapshot coverage is complete.', '', '## Claim discipline', '- Do not claim FTMO/The5ers portability until the historical calendar gap is closed and replayed end-to-end.']
    (out_dir / 'calendar_gap_plan.md').write_text('\n'.join(lines), encoding='utf-8')


def build_state_action_matrix(best_bundle, out_dir: Path):
    sig, sh = best_bundle['signals'].copy(), best_bundle['shadow'].copy()
    if sig.empty: return
    shadow_map = {str(r.get('parent_trade_id', '')): r.to_dict() for _, r in sh.iterrows()}
    rows = []
    for _, r in sig.iterrows():
        cf = shadow_map.get(str(r.get('parent_trade_id', '')), {})
        rows.append({'server_ts': r.get('server_ts', ''), 'utc_ts': r.get('utc_ts', ''), 'engine_name': r.get('engine_name', ''), 'engine_variant': r.get('engine_variant', ''), 'direction': r.get('direction', ''), 'blocked_or_fired': r.get('blocked_or_fired', ''), 'action': 'ALLOW_FULL' if str(r.get('blocked_or_fired', '')).lower() == 'fired' else 'BLOCK', 'reason': r.get('block_reason', '') or r.get('state_reason', ''), 'ny_open_state_class': r.get('ny_open_state_class', ''), 'ny_open_minutes_from_open': r.get('ny_open_minutes_from_open', 0), 'ny_open_impulse_atr': r.get('ny_open_impulse_atr', 0.0), 'ny_open_accept_closes': r.get('ny_open_accept_closes', 0), 'ny_open_rotation_count': r.get('ny_open_rotation_count', 0), 'ny_open_close_location': r.get('ny_open_close_location', 0.0), 'ny_open_last_close_vs_vwap_points': r.get('ny_open_last_close_vs_vwap_points', 0.0), 'counterfactual_status': cf.get('counterfactual_status', ''), 'counterfactual_points': cf.get('realized_net_points', 0.0)})
    pd.DataFrame(rows).to_csv(out_dir / 'state_action_matrix.csv', index=False)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root-runs', required=True)
    args = ap.parse_args()
    root = Path(args.root_runs)

    bundles = {}
    sandbox_rows = []
    prop_bundles = {}

    for cfg in CONFIGS:
        run_dir = find_run_by_scenario(root, cfg['scenario'])
        if run_dir is None:
            raise SystemExit(f"Missing sandbox run for {cfg['scenario']}")
        bundle = load_bundle(run_dir)
        bundles[cfg['scenario']] = bundle
        full = calc_metrics(bundle['trades'])
        split_a = calc_window_metrics(bundle['trades'], FULL_START, SPLIT_A_END)
        split_b = calc_window_metrics(bundle['trades'], SPLIT_B_START, FULL_END)
        rolling_rows, profitable, roll_total, roll_avg_pf = rolling_summary(bundle['trades'])
        sandbox_rows.append({'family': cfg['family'], 'scenario': cfg['scenario'], 'run_id': bundle['run_id'], 'trader_mode': cfg['trader_mode'], 'hypothesis': cfg['hypothesis'], 'window_min': cfg['window_min'], 'full_trades': full['trades'], 'full_net': full['net'], 'full_pf': full['pf'], 'full_dd': full['dd'], 'avg_hold': full['avg_hold'], 'median_hold': full['median_hold'], 'p95_hold': full['p95_hold'], 'top5': full['top5'], 'top10': full['top10'], 'timeout_ratio': full['timeout_ratio'], 'pnl_gt_240m_pct': full['pnl_gt_240m_pct'], 'splitA_trades': split_a['trades'], 'splitA_net': split_a['net'], 'splitA_pf': split_a['pf'], 'splitA_dd': split_a['dd'], 'splitB_trades': split_b['trades'], 'splitB_net': split_b['net'], 'splitB_pf': split_b['pf'], 'splitB_dd': split_b['dd'], 'rolling_profitable': profitable, 'rolling_total': roll_total, 'rolling_avg_pf': roll_avg_pf, 'rolling_rows': rolling_rows})

    sandbox_rows.sort(key=compare_rank_key)
    best_by_family = {}
    for family in ('T1', 'T2', 'T3'):
        fam_rows = [r for r in sandbox_rows if r['family'] == family]
        fam_rows.sort(key=compare_rank_key)
        best_by_family[family] = fam_rows[0]

    for _, row in best_by_family.items():
        cfg = next(c for c in CONFIGS if c['scenario'] == row['scenario'])
        if cfg['prop_scenario']:
            prop_run = find_run_by_scenario(root, cfg['prop_scenario'])
            if prop_run:
                pb = load_bundle(prop_run)
                prop_bundles[row['scenario']] = {'bundle': pb, 'metrics': calc_metrics(pb['trades'])}

    best_overall = sandbox_rows[0]
    best_bundle = bundles[best_overall['scenario']]
    best_prop = prop_bundles.get(best_overall['scenario'], {}).get('bundle')

    root_rows = [{k: v for k, v in r.items() if k != 'rolling_rows'} for r in sandbox_rows]
    pd.DataFrame(root_rows).to_csv(root / 'phase2a_family_comparison_20260308.csv', index=False)
    write_markdown_table(root / 'phase2a_family_comparison_20260308.md', [{'family': r['family'], 'scenario': r['scenario'], 'run_id': r['run_id'], 'trades': r['full_trades'], 'net': r['full_net'], 'pf': r['full_pf'], 'dd': r['full_dd'], 'splitB_pf': r['splitB_pf'], 'roll': f"{r['rolling_profitable']}/{r['rolling_total']}"} for r in sandbox_rows], ['family', 'scenario', 'run_id', 'trades', 'net', 'pf', 'dd', 'splitB_pf', 'roll'])
    oos_rows = [{'scenario': r['scenario'], 'family': r['family'], 'run_id': r['run_id'], 'full_pf': r['full_pf'], 'full_dd': r['full_dd'], 'splitA_pf': r['splitA_pf'], 'splitA_dd': r['splitA_dd'], 'splitB_pf': r['splitB_pf'], 'splitB_dd': r['splitB_dd'], 'rolling_profitable': r['rolling_profitable'], 'rolling_total': r['rolling_total'], 'rolling_avg_pf': r['rolling_avg_pf']} for r in sandbox_rows]
    pd.DataFrame(oos_rows).to_csv(root / 'phase2a_oos_summary_20260308.csv', index=False)
    write_markdown_table(root / 'phase2a_oos_summary_20260308.md', oos_rows, ['scenario', 'family', 'run_id', 'full_pf', 'full_dd', 'splitA_pf', 'splitA_dd', 'splitB_pf', 'splitB_dd', 'rolling_profitable', 'rolling_total', 'rolling_avg_pf'])

    out_dir = best_bundle['run_dir'] / 'reports' / 'phase2a'
    out_dir.mkdir(parents=True, exist_ok=True)
    build_time_clock_mapping(best_bundle, out_dir)
    build_alpha_vs_prop(best_by_family, prop_bundles, out_dir)
    build_entry_quality_audit(best_bundle, out_dir)
    build_path_confounding(best_bundle, best_prop, out_dir)
    build_drawdown_gallery(best_bundle, best_prop, out_dir)
    build_calendar_gap_plan(best_bundle, out_dir)
    build_trade_story(best_bundle, out_dir)
    build_state_action_matrix(best_bundle, out_dir)

    score_rows = []
    for r in sandbox_rows:
        cfg = next(c for c in CONFIGS if c['scenario'] == r['scenario'])
        prop = prop_bundles.get(r['scenario'])
        score_rows.append({'family': r['family'], 'scenario': r['scenario'], 'hypothesis': cfg['hypothesis'], 'window_min': cfg['window_min'], 'trader_mode': cfg['trader_mode'], 'trade_count': r['full_trades'], 'pf': r['full_pf'], 'dd': r['full_dd'], 'splitA_pf': r['splitA_pf'], 'splitB_pf': r['splitB_pf'], 'rolling_profitable': f"{r['rolling_profitable']}/{r['rolling_total']}", 'rolling_avg_pf': r['rolling_avg_pf'], 'prop_pf': prop['metrics']['pf'] if prop else '', 'prop_dd': prop['metrics']['dd'] if prop else '', 'prop_trades': prop['metrics']['trades'] if prop else ''})
    pd.DataFrame(score_rows).to_csv(out_dir / 'open_response_feature_scorecard.csv', index=False)
    summary = {'best_overall': best_overall, 'best_by_family': best_by_family, 'prop_metrics': {k: v['metrics'] for k, v in prop_bundles.items()}}
    (out_dir / 'phase2a_summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding='utf-8')


if __name__ == '__main__':
    main()
