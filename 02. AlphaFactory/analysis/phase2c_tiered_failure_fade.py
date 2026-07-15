#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict

import pandas as pd

ROOT = Path(r'02. AlphaFactory/runs/XAU_Scalp_Portfolio')
DATE_TAG = '20260308'
START_EQUITY = 10000.0

CONFIGS = [
    {'family':'CORE','scenario':'P2C_REF_CORE','label':'REF_CORE','hypothesis':'Core failure-fade baseline without Phase 2C overlays.','tier':'TIER0_CORE'},
    {'family':'OPEN_REJECTION_TIER','scenario':'P2C_T1_OPENREJ_HALF','label':'OPENREJ_HALF','hypothesis':'Core + open-rejection quality tier, half-risk on miss.','tier':'TIER1_FILTER'},
    {'family':'WICK_DEPTH_TIER','scenario':'P2C_T2_WICK_HALF','label':'WICK_HALF','hypothesis':'Core + wick-quality tier, half-risk on low-quality wick.','tier':'TIER1_FILTER'},
    {'family':'HANDOFF_CONFLICT_TIER','scenario':'P2C_T3_HANDOFF_HALF','label':'HANDOFF_HALF','hypothesis':'Core + London-NY handoff conflict tier, half-risk when conflict absent.','tier':'TIER1_FILTER'},
    {'family':'PREOPEN_EXP_OVERLAY','scenario':'P2C_T4_PREOPENEXP_HALF','label':'PREOPENEXP_HALF','hypothesis':'Core + rare pre-open expansion overlay, half-risk when overlay absent.','tier':'TIER2_OVERLAY'},
    {'family':'ACCEPT_COUNT_TIGHT_TIER','scenario':'P2C_T5_ACCEPTTIGHT_HALF','label':'ACCEPTTIGHT_HALF','hypothesis':'Core + tighter accept-count discipline, half-risk on looser NY acceptance.','tier':'TIER1_FILTER'},
    {'family':'SWEEP_DEPTH_TIER','scenario':'P2C_T6_SWEEPDEPTH_HALF','label':'SWEEPDEPTH_HALF','hypothesis':'Core + sweep-depth quality tier, half-risk when sweep is shallow.','tier':'TIER1_FILTER'},
]
SPLIT_SCENARIOS = [c['scenario'] for c in CONFIGS]
ROLLING_CANDIDATES = ['P2C_REF_CORE','P2C_T2_WICK_HALF','P2C_T5_ACCEPTTIGHT_HALF']
ROLLING_LABELS = ['R1','R2','R3','R4','R5','R6']
REALISM = {
    'P2C_T5_ACCEPTTIGHT_HALF_RT':'real_ticks_no_delay',
    'P2C_T5_ACCEPTTIGHT_HALF_RD':'every_tick_random_delay'
}


def read_json(path, default=None):
    if not path or not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding='utf-8', errors='ignore'))


def parse_dt(s):
    s = str(s or '').strip()
    if not s or s.lower() == 'nan':
        return pd.NaT
    for fmt in ('%Y.%m.%d %H:%M:%S','%Y.%m.%d %H:%M'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return pd.NaT


def pf(pnls):
    gp = sum(x for x in pnls if x > 0)
    gl = -sum(x for x in pnls if x < 0)
    return gp / gl if gl > 0 else (999.99 if gp > 0 else 0.0)


def top_contrib_pct(pnls, n):
    wins = sorted([x for x in pnls if x > 0], reverse=True)
    gp = sum(wins)
    return round(sum(wins[:n]) / gp * 100.0, 2) if gp > 0 else 0.0


def equity_dd(pnls, start=START_EQUITY):
    eq = start
    peak = start
    max_dd = 0.0
    episodes = []
    dd_start = None
    trough_eq = start
    trough_idx = -1
    for i, pnl in enumerate(pnls):
        eq += pnl
        if eq >= peak:
            if dd_start is not None:
                episodes.append((dd_start, i - 1, (peak - trough_eq) / peak * 100.0 if peak else 0.0))
                dd_start = None
            peak = eq
            trough_eq = eq
            trough_idx = i
        else:
            if dd_start is None:
                dd_start = i
                trough_eq = eq
                trough_idx = i
            elif eq < trough_eq:
                trough_eq = eq
                trough_idx = i
            dd = (peak - eq) / peak * 100.0 if peak else 0.0
            max_dd = max(max_dd, dd)
    if dd_start is not None:
        episodes.append((dd_start, trough_idx, (peak - trough_eq) / peak * 100.0 if peak else 0.0))
    return round(max_dd, 2), episodes


def calc_metrics(trades):
    if trades is None or trades.empty:
        return {
            'trades':0,'net':0.0,'pf':0.0,'dd':0.0,'avg_hold':0.0,'median_hold':0.0,'p95_hold':0.0,
            'top5':0.0,'top10':0.0,'worst_month':0.0,'worst_5day':0.0,'timeout_ratio':0.0,
            'yearly_counts':{},'quarter_median':0.0,'active_days':0
        }
    t = trades.sort_values('entry_utc_ts_dt').copy()
    pnls = t['pnl_net'].tolist()
    dd, _ = equity_dd(pnls)
    t['month'] = t['entry_utc_ts_dt'].dt.to_period('M').astype(str)
    t['year'] = t['entry_utc_ts_dt'].dt.year.astype(str)
    t['quarter'] = t['entry_utc_ts_dt'].dt.to_period('Q').astype(str)
    month_sum = t.groupby('month')['pnl_net'].sum()
    daily = t.groupby(t['entry_utc_ts_dt'].dt.date)['pnl_net'].sum().sort_index()
    worst5 = None
    vals = list(daily.items())
    for i in range(len(vals)):
        total = sum(v for _, v in vals[i:i+5])
        worst5 = total if worst5 is None else min(worst5, total)
    return {
        'trades': int(len(t)),
        'net': round(float(sum(pnls)),2),
        'pf': round(float(pf(pnls)),4),
        'dd': round(float(dd),2),
        'avg_hold': round(float(t['hold_minutes'].mean()),2),
        'median_hold': round(float(t['hold_minutes'].median()),2),
        'p95_hold': round(float(t['hold_minutes'].quantile(0.95)),2),
        'top5': top_contrib_pct(pnls,5),
        'top10': top_contrib_pct(pnls,10),
        'worst_month': round(float(month_sum.min()) if not month_sum.empty else 0.0,2),
        'worst_5day': round(float(worst5 if worst5 is not None else 0.0),2),
        'timeout_ratio': round(float((t['timeout_flag'] > 0).mean() * 100.0),2),
        'yearly_counts': {str(k): int(v) for k, v in t.groupby('year').size().items()},
        'quarter_median': round(float(t.groupby('quarter').size().median()),2),
        'active_days': int(len(daily)),
    }


def scenario_run(scenario):
    best = None
    for d in ROOT.iterdir():
        if not d.is_dir() or not d.name.startswith('2026'):
            continue
        metas = sorted((d / 'logs').glob('*RunMeta*.json'))
        if not metas:
            continue
        meta = read_json(metas[-1], {})
        if str(meta.get('scenario_id','')) != scenario:
            continue
        if best is None or d.stat().st_mtime > best.stat().st_mtime:
            best = d
    return best


def load_bundle(run_dir):
    logs = run_dir / 'logs'
    meta_path = sorted(logs.glob('*RunMeta*.json'))[-1]
    sig_path = sorted(logs.glob('*Signals*.csv'))[-1]
    act_path = sorted(logs.glob('*Activity*.csv'))[-1] if list(logs.glob('*Activity*.csv')) else None
    shadow_path = sorted(logs.glob('*Shadow*.csv'))[-1] if list(logs.glob('*Shadow*.csv')) else None
    trade_candidates = [p for p in logs.glob('*Trades*.csv') if '20260306_235959' not in p.name]
    trade_path = sorted(trade_candidates)[-1] if trade_candidates else (sorted(logs.glob('*Trades*.csv'))[-1] if list(logs.glob('*Trades*.csv')) else None)

    meta = read_json(meta_path, {})
    s = pd.read_csv(sig_path)
    t = pd.read_csv(trade_path) if trade_path and trade_path.exists() else pd.DataFrame()
    a = pd.read_csv(act_path) if act_path and act_path.exists() else pd.DataFrame()
    sh = pd.read_csv(shadow_path) if shadow_path and shadow_path.exists() else pd.DataFrame()

    for col in ['server_ts','utc_ts']:
        if col in s.columns:
            s[col + '_dt'] = s[col].apply(parse_dt)
    for col in ['entry_server_ts','entry_utc_ts','exit_server_ts','exit_utc_ts']:
        if col in t.columns:
            t[col + '_dt'] = t[col].apply(parse_dt)
    if 'server_ts' in a.columns:
        a['server_ts_dt'] = a['server_ts'].apply(parse_dt)
    if 'utc_ts' in a.columns:
        a['utc_ts_dt'] = a['utc_ts'].apply(parse_dt)
    if not sh.empty:
        for col in ['signal_server_ts','signal_utc_ts','exit_server_ts','exit_utc_ts']:
            if col in sh.columns:
                sh[col + '_dt'] = sh[col].apply(parse_dt)

    num_sig = ['atr_points','spread_points','vwap_distance_points','vwap_slope_points','day_range_points','quality_score','day_state_pnl','risk_multiplier',
               'ny_open_impulse_points','ny_open_impulse_atr','ny_open_close_location','ny_open_last_close_vs_vwap_points','ny_open_london_handoff_points','ny_open_sweep_depth_atr','ny_open_preopen_range_atr']
    int_sig = ['prior_loss_count','prior_trade_count','ny_open_minutes_from_open','ny_open_window_min','ny_open_accept_closes','ny_open_rotation_count','ny_open_accepted_break','ny_open_failed_break','ny_open_handoff_conflict','ny_open_failed_vwap_reclaim']
    for c in num_sig:
        if c in s.columns:
            s[c] = pd.to_numeric(s[c], errors='coerce').fillna(0.0)
    for c in int_sig:
        if c in s.columns:
            s[c] = pd.to_numeric(s[c], errors='coerce').fillna(0).astype(int)
    for c in ['hold_minutes','mfe_points','mae_points','giveback_points','realized_r','pnl_net','risk_multiplier']:
        if c in t.columns:
            t[c] = pd.to_numeric(t[c], errors='coerce').fillna(0.0)
    for c in ['timeout_flag','modify_count']:
        if c in t.columns:
            t[c] = pd.to_numeric(t[c], errors='coerce').fillna(0).astype(int)

    if 'engine_name' in t.columns and 'direction' in t.columns and 'entry_reason' in t.columns and 'entry_server_ts' in t.columns:
        t['signal_key'] = t[['entry_server_ts','engine_name','direction','entry_reason']].astype(str).agg('|'.join, axis=1) if not t.empty else pd.Series(dtype=str)
    else:
        t['signal_key'] = pd.Series(dtype=str)
    if s.empty:
        s['signal_key'] = pd.Series(dtype=str)
    else:
        s['signal_key'] = s[['server_ts','engine_name','direction','entry_reason']].astype(str).agg('|'.join, axis=1)

    return {
        'run_id': run_dir.name,
        'run_dir': run_dir,
        'meta': meta,
        'signals': s,
        'trades': t,
        'activity': a,
        'shadow': sh,
        'metrics': calc_metrics(t)
    }


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')


def rolling_df(base):
    rows = []
    for tag in ROLLING_LABELS:
        run = scenario_run(f'{base}_{tag}')
        if not run:
            rows.append({'scenario': f'{base}_{tag}', 'run_id':'', 'trades':0, 'net':0.0, 'pf':0.0, 'dd':0.0})
            continue
        b = load_bundle(run)
        rows.append({'scenario': f'{base}_{tag}', 'run_id': b['run_id'], **b['metrics']})
    return pd.DataFrame(rows)


full_rows = []
for cfg in CONFIGS:
    run = scenario_run(cfg['scenario'])
    if not run:
        continue
    bundle = load_bundle(run)
    full_rows.append({**cfg, 'run_id': bundle['run_id'], 'run_dir': run, 'bundle': bundle, 'full': bundle['metrics']})

split_rows = []
for cfg in CONFIGS:
    base = cfg['scenario']
    ref = next((r for r in full_rows if r['scenario'] == base), None)
    if not ref:
        continue
    row = {'scenario': base, 'label': cfg['label'], 'family': cfg['family'], 'tier': cfg['tier'], 'full': ref['full'], 'run_full': ref['run_id']}
    for suff in ['A','B']:
        run = scenario_run(f'{base}_{suff}')
        bundle = load_bundle(run) if run else None
        row[suff] = (bundle['metrics'] if bundle else calc_metrics(pd.DataFrame()))
        row[f'run_{suff}'] = (bundle['run_id'] if bundle else '')
    split_rows.append(row)

rolling_tables = {base: rolling_df(base) for base in ROLLING_CANDIDATES}

comparison_rows = []
for r in full_rows:
    sr = next((x for x in split_rows if x['scenario'] == r['scenario']), None)
    rolling = rolling_tables.get(r['scenario'], pd.DataFrame())
    active_prof = int(((rolling['trades'] > 0) & (rolling['pf'] > 1.0)).sum()) if not rolling.empty else 0
    zero_windows = int((rolling['trades'] == 0).sum()) if not rolling.empty else 0
    comparison_rows.append({
        'family': r['family'], 'tier': r['tier'], 'scenario': r['scenario'], 'run_id': r['run_id'],
        'trades': r['full']['trades'], 'net': r['full']['net'], 'pf': r['full']['pf'], 'dd': r['full']['dd'],
        'splitA_pf': sr['A']['pf'] if sr else 0.0, 'splitA_dd': sr['A']['dd'] if sr else 0.0,
        'splitB_pf': sr['B']['pf'] if sr else 0.0, 'splitB_dd': sr['B']['dd'] if sr else 0.0,
        'top10': r['full']['top10'], 'quarter_median': r['full']['quarter_median'],
        'roll_active_profitable': active_prof, 'roll_zero_windows': zero_windows
    })
comparison_df = pd.DataFrame(comparison_rows)
comparison_df = comparison_df.sort_values(['splitB_pf','splitB_dd','trades','top10','pf','dd','roll_active_profitable'], ascending=[False,True,False,True,False,True,False])
comparison_df.to_csv(ROOT / f'phase2c_family_comparison_{DATE_TAG}.csv', index=False)
write_text(ROOT / f'phase2c_family_comparison_{DATE_TAG}.md', comparison_df.to_markdown(index=False))

best_scenario = comparison_df.iloc[0]['scenario']
best_row = next(r for r in full_rows if r['scenario'] == best_scenario)
best_bundle = best_row['bundle']
best_dir = best_row['run_dir'] / 'reports' / 'phase2c'
best_dir.mkdir(parents=True, exist_ok=True)

# scorecard / tiered overlay audit
ref_bundle = next(r['bundle'] for r in full_rows if r['scenario'] == 'P2C_REF_CORE')
ref_metrics = next(r['full'] for r in full_rows if r['scenario'] == 'P2C_REF_CORE')
ref_fired = ref_bundle['signals'][ref_bundle['signals']['blocked_or_fired'].eq('fired')].copy()
rows = []
audit_lines = ['# tiered_overlay_audit', '']
for r in full_rows:
    sr = next(x for x in split_rows if x['scenario'] == r['scenario'])
    rolling = rolling_tables.get(r['scenario'], pd.DataFrame())
    fired = r['bundle']['signals'][r['bundle']['signals']['blocked_or_fired'].eq('fired')].copy()
    half_ratio = round(float((fired['state_action'].eq('ALLOW_HALF_RISK')).mean() * 100.0),2) if not fired.empty and 'state_action' in fired.columns else 0.0
    zero_windows = int((rolling['trades'] == 0).sum()) if not rolling.empty else 0
    active_prof = int(((rolling['trades'] > 0) & (rolling['pf'] > 1.0)).sum()) if not rolling.empty else 0
    trade_delta = r['full']['trades'] - ref_metrics['trades']
    sparsity_note = 'quality/risk-throttle' if trade_delta == 0 else 'sparsity/filtering'
    rows.append({
        'family': r['family'], 'scenario': r['scenario'], 'trade_count': r['full']['trades'],
        'trade_delta_vs_ref': trade_delta, 'pf': r['full']['pf'], 'dd': r['full']['dd'],
        'splitA_pf': sr['A']['pf'], 'splitB_pf': sr['B']['pf'], 'top10': r['full']['top10'],
        'rolling_active_profitable': active_prof, 'rolling_zero_windows': zero_windows,
        'half_risk_signal_pct': half_ratio, 'improvement_driver': sparsity_note
    })
    audit_lines += [
        f"## {r['scenario']}",
        f"- trades: {r['full']['trades']} (delta vs ref: {trade_delta})",
        f"- PF/DD: {r['full']['pf']} / {r['full']['dd']}%",
        f"- split A PF/DD: {sr['A']['pf']} / {sr['A']['dd']}%",
        f"- split B PF/DD: {sr['B']['pf']} / {sr['B']['dd']}%",
        f"- rolling active profitable windows: {active_prof}/{len(rolling)} | zero-trade windows: {zero_windows}",
        f"- concentration top10: {r['full']['top10']}%",
        f"- half-risk signal pct: {half_ratio}%",
        f"- interpretation: improvement comes mainly from `{sparsity_note}`",
        ''
    ]
score_df = pd.DataFrame(rows).sort_values(['splitB_pf','top10','pf'], ascending=[False,True,False])
write_text(best_dir / 'tiered_overlay_audit.md', '\n'.join(audit_lines))

# true split report
split_df = pd.DataFrame([{
    'scenario': r['scenario'], 'family': r['family'], 'tier': r['tier'],
    'full_run': r['run_full'], 'full_trades': r['full']['trades'], 'full_pf': r['full']['pf'], 'full_dd': r['full']['dd'],
    'splitA_run': r['run_A'], 'splitA_trades': r['A']['trades'], 'splitA_pf': r['A']['pf'], 'splitA_dd': r['A']['dd'],
    'splitB_run': r['run_B'], 'splitB_trades': r['B']['trades'], 'splitB_pf': r['B']['pf'], 'splitB_dd': r['B']['dd']
} for r in split_rows]).sort_values(['splitB_pf','full_pf'], ascending=[False,False])
write_text(best_dir / 'true_split_rerun_report.md', '# true_split_rerun_report\n\n' + split_df.to_markdown(index=False))

# rolling rerun summary
rolling_lines = ['# rolling_oos_rerun_summary', '']
for base, df in rolling_tables.items():
    active_prof = int(((df['trades'] > 0) & (df['pf'] > 1.0)).sum())
    zero_windows = int((df['trades'] == 0).sum())
    rolling_lines += [f'## {base}', df[['scenario','run_id','trades','net','pf','dd']].to_markdown(index=False), f'- active_profitable_windows: {active_prof}/{len(df)}', f'- zero_trade_windows: {zero_windows}/{len(df)}', '']
write_text(best_dir / 'rolling_oos_rerun_summary.md', '\n'.join(rolling_lines))

# sample density report
best_trades = best_bundle['trades'].sort_values('entry_utc_ts_dt').copy()
best_trades['year'] = best_trades['entry_utc_ts_dt'].dt.year.astype(str) if not best_trades.empty else pd.Series(dtype=str)
best_trades['quarter'] = best_trades['entry_utc_ts_dt'].dt.to_period('Q').astype(str) if not best_trades.empty else pd.Series(dtype=str)
yearly = best_trades.groupby('year').size().reset_index(name='trades') if not best_trades.empty else pd.DataFrame(columns=['year','trades'])
quarterly = best_trades.groupby('quarter').size().reset_index(name='trades') if not best_trades.empty else pd.DataFrame(columns=['quarter','trades'])
density_df = pd.DataFrame([{
    'scenario': r['scenario'], 'family': r['family'], 'full_trades': r['full']['trades'], 'splitA_trades': r['A']['trades'], 'splitB_trades': r['B']['trades'], 'median_trades_per_quarter': r['full']['quarter_median']
} for r in split_rows]).sort_values(['full_trades','splitB_trades'], ascending=[False,False])
sample_text = ['# sample_density_report', '', '## Config comparison', density_df.to_markdown(index=False), '', f'## Best scenario: {best_scenario}', yearly.to_markdown(index=False) if not yearly.empty else 'no yearly data', '', '## Quarter counts', quarterly.to_markdown(index=False) if not quarterly.empty else 'no quarter data']
rolling_best = rolling_tables.get(best_scenario, pd.DataFrame())
if not rolling_best.empty:
    sample_text += ['', '## Rolling windows', rolling_best[['scenario','trades','pf','dd']].to_markdown(index=False)]
write_text(best_dir / 'sample_density_report.md', '\n'.join(sample_text))

# concentration vs quality curve
curve_rows = []
for r in full_rows:
    curve_rows.append({
        'scenario': r['scenario'], 'family': r['family'], 'trades': r['full']['trades'], 'pf': r['full']['pf'], 'dd': r['full']['dd'],
        'top5': r['full']['top5'], 'top10': r['full']['top10'], 'worst_month': r['full']['worst_month'], 'worst_5day': r['full']['worst_5day'], 'timeout_ratio': r['full']['timeout_ratio']
    })
curve_df = pd.DataFrame(curve_rows).sort_values(['pf','top10'], ascending=[False,True])
write_text(best_dir / 'concentration_vs_quality_curve.md', '# concentration_vs_quality_curve\n\n' + curve_df.to_markdown(index=False))

# portability gap
portability_gap = """# news_portability_gap_report

- Historical news/calendar coverage is still incomplete for the full test window 2020-03-07 -> 2026-03-06.
- Current snapshot coverage is still partial and cannot validate FTMO Standard / FTMO Swing / The5ers compatibility.
- Missing pieces before any portability claim:
  1. full historical calendar coverage for the whole backtest window
  2. verified event-class mapping per firm restriction class
  3. strict-profile reruns using completed calendar history
  4. open/close prohibition audit around restricted macro windows
  5. firm-clock reconciliation reports under each policy manifest
- Therefore Phase 2C is alpha-structure evidence only, not funded-compliance proof.
"""
write_text(best_dir / 'news_portability_gap_report.md', portability_gap)

# trade and blocked stories
sig_cols = ['signal_key','scenario_id','engine_name','direction','state_action','state_reason','risk_multiplier','ny_open_state_class','ny_open_minutes_from_open','ny_open_accept_closes','ny_open_rotation_count','ny_open_close_location','ny_open_london_handoff_points','ny_open_sweep_depth_atr','ny_open_preopen_range_atr','spread_points','atr_points','vwap_distance_points']
sig_lookup = best_bundle['signals'][sig_cols].drop_duplicates('signal_key').set_index('signal_key') if not best_bundle['signals'].empty else pd.DataFrame()
trade_stories = []
for _, tr in best_trades.iterrows():
    srow = sig_lookup.loc[tr['signal_key']] if tr['signal_key'] in sig_lookup.index else None
    trade_stories.append({
        'run_id': best_bundle['run_id'], 'scenario_id': best_scenario, 'signal_key': tr['signal_key'], 'engine_name': tr.get('engine_name',''),
        'entry_utc_ts': tr.get('entry_utc_ts',''), 'exit_utc_ts': tr.get('exit_utc_ts',''), 'direction': tr.get('direction',''),
        'pnl_net': round(float(tr.get('pnl_net',0.0)),2), 'hold_minutes': round(float(tr.get('hold_minutes',0.0)),1),
        'exit_reason': tr.get('exit_reason',''), 'timeout_flag': int(tr.get('timeout_flag',0)),
        'state_action': '' if srow is None else str(srow['state_action']),
        'state_reason': '' if srow is None else str(srow['state_reason']),
        'risk_multiplier': None if srow is None else float(srow['risk_multiplier']),
        'ny_open_state_class': '' if srow is None else str(srow['ny_open_state_class']),
        'mins_from_open': None if srow is None else int(srow['ny_open_minutes_from_open']),
        'accept_closes': None if srow is None else int(srow['ny_open_accept_closes']),
        'rotation_count': None if srow is None else int(srow['ny_open_rotation_count']),
        'close_location': None if srow is None else float(srow['ny_open_close_location']),
        'playbook_fit': 'yes'
    })
blocked = best_bundle['signals'][best_bundle['signals']['blocked_or_fired'].eq('blocked')].copy()
shadow_map = {}
if not best_bundle['shadow'].empty and 'parent_trade_id' in best_bundle['shadow'].columns:
    for _, r in best_bundle['shadow'].iterrows():
        shadow_map[str(r['parent_trade_id'])] = {
            'counterfactual_status': r.get('counterfactual_status',''),
            'counterfactual_exit_reason': r.get('exit_reason',''),
            'counterfactual_points': float(r.get('realized_net_points',0.0)) if pd.notna(r.get('realized_net_points',0.0)) else 0.0
        }
blocked_stories = []
for _, sr in blocked.iterrows():
    cf = shadow_map.get(str(sr.get('parent_trade_id','')), {})
    blocked_stories.append({
        'run_id': best_bundle['run_id'], 'scenario_id': best_scenario, 'signal_key': sr['signal_key'], 'server_ts': sr.get('server_ts',''),
        'direction': sr.get('direction',''), 'state_action': sr.get('state_action',''), 'state_reason': sr.get('state_reason',''), 'block_reason': sr.get('block_reason',''),
        'risk_multiplier': float(sr.get('risk_multiplier',0.0)), 'counterfactual_status': cf.get('counterfactual_status','not_available'),
        'counterfactual_exit_reason': cf.get('counterfactual_exit_reason',''), 'counterfactual_points': cf.get('counterfactual_points',0.0)
    })
write_jsonl(best_dir / 'trade_story.jsonl', trade_stories)
write_jsonl(best_dir / 'blocked_signal_story.jsonl', blocked_stories)

# drawdown gallery
_, episodes = equity_dd(best_trades['pnl_net'].tolist()) if not best_trades.empty else (0.0, [])
episodes = sorted(episodes, key=lambda x: x[2], reverse=True)[:10]
lines = ['# drawdown_replay_gallery', '', f'- scenario: `{best_scenario}`', '']
for start_idx, end_idx, depth in episodes:
    seg = best_trades.iloc[start_idx:end_idx+1]
    if seg.empty:
        continue
    lines.append(f"## {seg.iloc[0]['entry_utc_ts']} -> {seg.iloc[-1]['exit_utc_ts']} | DD {depth:.2f}%")
    lines.append(f"- trades: {len(seg)} | net: {seg['pnl_net'].sum():.2f} | exits: {dict(seg['exit_reason'].value_counts())}")
    lines.append('')
write_text(best_dir / 'drawdown_replay_gallery.md', '\n'.join(lines))

# realism summary
real_rows = []
for sc, label in REALISM.items():
    run = scenario_run(sc)
    if not run:
        continue
    b = load_bundle(run)
    real_rows.append({'scenario': sc, 'label': label, 'run_id': b['run_id'], **b['metrics']})
real_df = pd.DataFrame(real_rows)

summary = {
    'best_scenario': best_scenario,
    'best_run_id': best_bundle['run_id'],
    'best_metrics': best_row['full'],
    'best_splitA': next(r for r in split_rows if r['scenario'] == best_scenario)['A'],
    'best_splitB': next(r for r in split_rows if r['scenario'] == best_scenario)['B'],
    'realism': real_rows,
}
(best_dir / 'phase2c_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

print('best_scenario', best_scenario)
print('best_run', best_bundle['run_id'])
print('wrote', best_dir)
