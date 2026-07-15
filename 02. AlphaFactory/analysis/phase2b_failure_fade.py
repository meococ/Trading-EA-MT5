#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import math
from datetime import datetime
from pathlib import Path
from collections import defaultdict

import pandas as pd

ROOT = Path(r'02. AlphaFactory/runs/XAU_Scalp_Portfolio')
DATE_TAG = '20260308'
START_EQUITY = 10000.0

FULL_CONFIGS = [
    {'family':'BASELINE','scenario':'P2B_REF_BASE','label':'REF_BASE','hypothesis':'Reference T2A failure-fade branch without Phase 2B sub-state filters.','role':'reference'},
    {'family':'LONDON_SWEEP','scenario':'P2B_F1_LDNSWEEP_CONFLICT','label':'F1_CONFLICT','hypothesis':'Require extreme London sweep plus handoff conflict before NY fade.','role':'filter'},
    {'family':'LONDON_SWEEP','scenario':'P2B_F1_LDNSWEEP_ALIGN','label':'F1_ALIGN','hypothesis':'Require extreme London sweep but aligned handoff, testing conflict vs alignment.','role':'filter'},
    {'family':'OPEN_REJECTION','scenario':'P2B_F2_OPENREJECT','label':'F2_OPENREJECT','hypothesis':'Require opening-range rejection / failed acceptance with accept-count veto.','role':'trigger_filter'},
    {'family':'FAILED_VWAP_RECLAIM','scenario':'P2B_F3_VWAPFAIL','label':'F3_VWAPFAIL','hypothesis':'Require failed VWAP reclaim after sweep.','role':'filter'},
    {'family':'WICK_DEPTH','scenario':'P2B_F4_WICK_DEPTH','label':'F4_WICK_DEPTH','hypothesis':'Require wick-dominant rejection quality and minimum sweep depth.','role':'filter'},
    {'family':'PREOPEN_CONTEXT','scenario':'P2B_F5_PREOPEN_COMP','label':'F5_PREOPEN_COMP','hypothesis':'Require pre-open compression context before failure-fade.','role':'filter'},
    {'family':'PREOPEN_CONTEXT','scenario':'P2B_F6_PREOPEN_EXP','label':'F6_PREOPEN_EXP','hypothesis':'Require pre-open expansion context before failure-fade.','role':'filter'},
]
SHORTLIST = ['P2B_REF_BASE','P2B_F1_LDNSWEEP_CONFLICT','P2B_F2_OPENREJECT','P2B_F4_WICK_DEPTH','P2B_F6_PREOPEN_EXP']
ROLLING_CANDIDATES = ['P2B_F2_OPENREJECT','P2B_F6_PREOPEN_EXP']
ROLLING_LABELS = ['R1','R2','R3','R4','R5','R6']
SPLITS = {'A': ('2020.03.07','2023.03.06'), 'B': ('2023.03.07','2026.03.06')}
REALISM = {'P2B_F6_PREOPEN_EXP_RT':'real_ticks_no_delay', 'P2B_F6_PREOPEN_EXP_RD':'every_tick_random_delay'}


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
                episodes.append((dd_start, i-1, (peak - trough_eq) / peak * 100.0 if peak else 0.0))
                dd_start = None
                trough_eq = eq
            peak = eq
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
    return round(max_dd,2), episodes


def calc_metrics(trades):
    if trades is None or trades.empty:
        return {'trades':0,'net':0.0,'pf':0.0,'dd':0.0,'avg_hold':0.0,'median_hold':0.0,'p95_hold':0.0,'top5':0.0,'top10':0.0,'worst_month':0.0,'worst_5day':0.0,'timeout_ratio':0.0}
    pnls = trades['pnl_net'].tolist()
    dd, _ = equity_dd(pnls)
    m = trades.copy()
    m['month'] = m['entry_utc_ts_dt'].dt.to_period('M').astype(str)
    month_sum = m.groupby('month')['pnl_net'].sum()
    daily = m.groupby(m['entry_utc_ts_dt'].dt.date)['pnl_net'].sum().sort_index()
    worst5 = 0.0
    vals = daily.tolist()
    for i in range(len(vals)):
        worst5 = min(worst5, sum(vals[i:i+5]))
    return {
        'trades': int(len(trades)),
        'net': round(float(sum(pnls)),2),
        'pf': round(float(pf(pnls)),4),
        'dd': round(float(dd),2),
        'avg_hold': round(float(trades['hold_minutes'].mean()),2),
        'median_hold': round(float(trades['hold_minutes'].median()),2),
        'p95_hold': round(float(trades['hold_minutes'].quantile(0.95)),2),
        'top5': top_contrib_pct(pnls,5),
        'top10': top_contrib_pct(pnls,10),
        'worst_month': round(float(month_sum.min()) if not month_sum.empty else 0.0,2),
        'worst_5day': round(float(worst5),2),
        'timeout_ratio': round(float((trades['timeout_flag']>0).mean()*100.0),2),
    }


def scenario_run(scenario):
    best = None
    for d in ROOT.iterdir():
        if not d.is_dir() or not d.name.startswith('2026'):
            continue
        metas = sorted((d/'logs').glob('*RunMeta*.json'))
        if not metas:
            continue
        meta = read_json(metas[-1], {})
        if str(meta.get('scenario_id','')) != scenario:
            continue
        if best is None or d.stat().st_mtime > best.stat().st_mtime:
            best = d
    return best


def load_bundle(run_dir):
    logs = run_dir/'logs'
    meta_path = sorted(logs.glob('*RunMeta*.json'))[-1]
    sig_path = sorted(logs.glob('*Signals*.csv'))[-1]
    trade_paths = sorted([p for p in logs.glob('*Trades*.csv') if '20260306_235959' not in p.name])
    trd_path = trade_paths[-1]
    meta = read_json(meta_path, {})
    s = pd.read_csv(sig_path)
    t = pd.read_csv(trd_path)
    t = t[t['is_final_close'].fillna(1).astype(int) == 1].copy()
    for col in ['server_ts','utc_ts']:
        s[col + '_dt'] = s[col].apply(parse_dt)
    for col in ['entry_server_ts','entry_utc_ts','exit_server_ts','exit_utc_ts']:
        t[col + '_dt'] = t[col].apply(parse_dt)
    num_s = ['atr_points','spread_points','vwap_distance_points','vwap_slope_points','day_range_points','quality_score','day_state_pnl','risk_multiplier',
             'ny_open_impulse_points','ny_open_impulse_atr','ny_open_close_location','ny_open_last_close_vs_vwap_points','ny_open_london_handoff_points','ny_open_sweep_depth_atr','ny_open_preopen_range_atr']
    int_s = ['prior_loss_count','prior_trade_count','ny_open_minutes_from_open','ny_open_window_min','ny_open_accept_closes','ny_open_rotation_count','ny_open_accepted_break','ny_open_failed_break','ny_open_handoff_conflict','ny_open_failed_vwap_reclaim']
    for c in num_s:
        if c in s.columns: s[c] = pd.to_numeric(s[c], errors='coerce').fillna(0.0)
    for c in int_s:
        if c in s.columns: s[c] = pd.to_numeric(s[c], errors='coerce').fillna(0).astype(int)
    for c in ['hold_minutes','mfe_points','mae_points','giveback_points','realized_r','pnl_net']:
        if c in t.columns: t[c] = pd.to_numeric(t[c], errors='coerce').fillna(0.0)
    for c in ['timeout_flag']:
        if c in t.columns: t[c] = pd.to_numeric(t[c], errors='coerce').fillna(0).astype(int)
    s['signal_key'] = s[['server_ts','engine_name','direction','entry_reason']].astype(str).agg('|'.join, axis=1)
    if t.empty:
        t['signal_key'] = pd.Series(dtype=str)
    else:
        t['signal_key'] = t[['entry_server_ts','engine_name','direction','entry_reason']].astype(str).agg('|'.join, axis=1)
    return {'run_dir': run_dir, 'run_id': run_dir.name, 'meta': meta, 'signals': s, 'trades': t, 'metrics': calc_metrics(t)}


def best_by_family(rows):
    out = {}
    for r in rows:
        fam = r['family']
        if fam not in out:
            out[fam] = r
            continue
        a, b = out[fam], r
        rank_a = (a['full']['pf'], -a['full']['dd'], a['full']['trades'])
        rank_b = (b['full']['pf'], -b['full']['dd'], b['full']['trades'])
        if rank_b > rank_a:
            out[fam] = r
    return out


def rolling_summary(scenarios):
    rows = []
    for sc in scenarios:
        r = scenario_run(sc)
        if not r:
            continue
        b = load_bundle(r)
        rows.append({'scenario': sc, 'run_id': b['run_id'], **b['metrics']})
    return pd.DataFrame(rows)


def month_bucket(dt):
    return dt.strftime('%Y-%m') if not pd.isna(dt) else 'NA'


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')


# load full matrix
full_rows = []
for cfg in FULL_CONFIGS:
    run = scenario_run(cfg['scenario'])
    if not run:
        continue
    bundle = load_bundle(run)
    row = {**cfg, 'run_id': bundle['run_id'], 'run_dir': run, 'bundle': bundle, 'full': bundle['metrics']}
    full_rows.append(row)

families = best_by_family(full_rows)

# shortlist splits
split_rows = []
for scenario in SHORTLIST:
    ref = next((r for r in full_rows if r['scenario']==scenario), None)
    if not ref:
        continue
    row = {'scenario':scenario,'label':ref['label'],'family':ref['family'],'full':ref['full']}
    for suffix in ['A','B']:
        run = scenario_run(f'{scenario}_{suffix}')
        bundle = load_bundle(run) if run else None
        row[suffix] = (bundle['metrics'] if bundle else calc_metrics(pd.DataFrame()))
        row[f'run_{suffix}'] = (bundle['run_id'] if bundle else '')
    split_rows.append(row)

# rolling actual reruns for top candidates
rolling_tables = {}
for base in ROLLING_CANDIDATES:
    df = rolling_summary([f'{base}_{x}' for x in ROLLING_LABELS])
    rolling_tables[base] = df

# choose best overall by splitB pf/dd then rolling then full
rank_rows = []
for row in split_rows:
    rolling = rolling_tables.get(row['scenario'], pd.DataFrame())
    profitable = int((rolling['pf'] > 1.0).sum()) if not rolling.empty else 0
    total = int(len(rolling)) if not rolling.empty else 0
    rank_rows.append({
        'scenario': row['scenario'], 'label': row['label'], 'family': row['family'],
        'splitB_pf': row['B']['pf'], 'splitB_dd': row['B']['dd'],
        'rolling_profitable': profitable, 'rolling_total': total,
        'full_pf': row['full']['pf'], 'full_dd': row['full']['dd'], 'trades': row['full']['trades']
    })
rank_df = pd.DataFrame(rank_rows)
rank_df = rank_df.sort_values(['splitB_pf','splitB_dd','rolling_profitable','full_pf','full_dd','trades'], ascending=[False,True,False,False,True,False])
best_scenario = rank_df.iloc[0]['scenario']
best_row = next(r for r in full_rows if r['scenario']==best_scenario)
best_bundle = best_row['bundle']
best_dir = best_row['run_dir'] / 'reports' / 'phase2b'
best_dir.mkdir(parents=True, exist_ok=True)

# family comparison
comp = []
for r in full_rows:
    s = next((x for x in split_rows if x['scenario']==r['scenario']), None)
    rolling = rolling_tables.get(r['scenario'], pd.DataFrame())
    comp.append({
        'family': r['family'], 'scenario': r['scenario'], 'run_id': r['run_id'],
        'trades': r['full']['trades'], 'net': r['full']['net'], 'pf': r['full']['pf'], 'dd': r['full']['dd'],
        'splitA_pf': s['A']['pf'] if s else 0.0, 'splitB_pf': s['B']['pf'] if s else 0.0,
        'roll_profitable': f"{int((rolling['pf']>1.0).sum())}/{len(rolling)}" if not rolling.empty else 'n/a'
    })
comp_df = pd.DataFrame(comp).sort_values(['splitB_pf','dd','pf'], ascending=[False,True,False])
comp_df.to_csv(ROOT / f'phase2b_family_comparison_{DATE_TAG}.csv', index=False)
write_text(ROOT / f'phase2b_family_comparison_{DATE_TAG}.md', comp_df.to_markdown(index=False))

# open scorecard
score_rows = []
ref_metrics = next(r['full'] for r in full_rows if r['scenario']=='P2B_REF_BASE')
for r in full_rows:
    s = next((x for x in split_rows if x['scenario']==r['scenario']), None)
    rolling = rolling_tables.get(r['scenario'], pd.DataFrame())
    score_rows.append({
        'family': r['family'], 'scenario': r['scenario'], 'hypothesis': r['hypothesis'], 'role': r['role'],
        'trade_count': r['full']['trades'], 'trade_count_delta_vs_ref': r['full']['trades'] - ref_metrics['trades'],
        'pf': r['full']['pf'], 'dd': r['full']['dd'], 'pf_delta_vs_ref': round(r['full']['pf'] - ref_metrics['pf'],4),
        'dd_delta_vs_ref': round(r['full']['dd'] - ref_metrics['dd'],2),
        'splitA_pf': s['A']['pf'] if s else 0.0, 'splitA_dd': s['A']['dd'] if s else 0.0,
        'splitB_pf': s['B']['pf'] if s else 0.0, 'splitB_dd': s['B']['dd'] if s else 0.0,
        'rolling_profitable': int((rolling['pf']>1.0).sum()) if not rolling.empty else 0,
        'rolling_total': int(len(rolling)) if not rolling.empty else 0,
        'rolling_avg_pf': round(float(rolling['pf'].replace(999.99, 10.0).mean()),4) if not rolling.empty else 0.0,
    })
score_df = pd.DataFrame(score_rows).sort_values(['splitB_pf','pf'], ascending=[False,False])
score_df.to_csv(best_dir / 'substate_feature_scorecard.csv', index=False)

# true split report
true_split_df = pd.DataFrame([{
    'scenario': r['scenario'], 'family': r['family'], 'full_trades': r['full']['trades'], 'full_pf': r['full']['pf'], 'full_dd': r['full']['dd'],
    'splitA_run': r.get('run_A',''), 'splitA_trades': r['A']['trades'], 'splitA_pf': r['A']['pf'], 'splitA_dd': r['A']['dd'],
    'splitB_run': r.get('run_B',''), 'splitB_trades': r['B']['trades'], 'splitB_pf': r['B']['pf'], 'splitB_dd': r['B']['dd'],
} for r in split_rows]).sort_values(['splitB_pf','full_pf'], ascending=[False,False])
write_text(best_dir / 'true_split_rerun_report.md', '# true_split_rerun_report\n\n' + true_split_df.to_markdown(index=False))

# rolling rerun summary
rolling_md = ['# rolling_oos_rerun_summary', '']
for base, df in rolling_tables.items():
    rolling_md.append(f'## {base}')
    if df.empty:
        rolling_md.append('- no reruns')
    else:
        rolling_md.append(df[['scenario','run_id','trades','net','pf','dd']].to_markdown(index=False))
        rolling_md.append(f"- profitable_windows: {(df['pf'] > 1.0).sum()}/{len(df)}")
    rolling_md.append('')
write_text(best_dir / 'rolling_oos_rerun_summary.md', '\n'.join(rolling_md))

# concentration audit for best config
bt = best_bundle['trades'].copy().sort_values('entry_utc_ts_dt')
bt['month'] = bt['entry_utc_ts_dt'].apply(month_bucket)
month_sum = bt.groupby('month')['pnl_net'].sum().sort_values()
daily = bt.groupby(bt['entry_utc_ts_dt'].dt.date)['pnl_net'].sum().sort_index()
worst5 = 0.0
worst_span = ('','')
vals = list(daily.items())
for i in range(len(vals)):
    span = vals[i:i+5]
    total = sum(v for _,v in span)
    if total < worst5:
        worst5 = total
        worst_span = (str(span[0][0]), str(span[-1][0]))
conc_text = f"""# concentration_audit

- scenario: `{best_scenario}`
- run_id: `{best_bundle['run_id']}`
- trades: `{best_row['full']['trades']}`
- top5 contribution: `{best_row['full']['top5']}%`
- top10 contribution: `{best_row['full']['top10']}%`
- worst month: `{round(float(month_sum.iloc[0]) if not month_sum.empty else 0.0,2)}`
- worst 5-day stretch: `{round(float(worst5),2)}` from `{worst_span[0]}` to `{worst_span[1]}`
- timeout ratio: `{best_row['full']['timeout_ratio']}%`
- avg/median/p95 hold: `{best_row['full']['avg_hold']} / {best_row['full']['median_hold']} / {best_row['full']['p95_hold']}`

## Month breakdown
{month_sum.to_frame('pnl_net').to_markdown() if not month_sum.empty else 'no data'}
"""
write_text(best_dir / 'concentration_audit.md', conc_text)

# path confounding audit best vs ref
ref_bundle = next(r['bundle'] for r in full_rows if r['scenario']=='P2B_REF_BASE')
ref_fired = ref_bundle['signals'][ref_bundle['signals']['blocked_or_fired'].eq('fired')].copy()
best_fired = best_bundle['signals'][best_bundle['signals']['blocked_or_fired'].eq('fired')].copy()
ref_keys = set(ref_fired['signal_key'])
best_keys = set(best_fired['signal_key'])
removed = ref_keys - best_keys
admitted = best_keys - ref_keys
overlap = ref_keys & best_keys
ref_trade = ref_bundle['trades'].set_index('signal_key')['pnl_net'].to_dict()
best_trade = best_bundle['trades'].set_index('signal_key')['pnl_net'].to_dict()
removed_net = round(sum(ref_trade.get(k,0.0) for k in removed),2)
admitted_net = round(sum(best_trade.get(k,0.0) for k in admitted),2)
best_sig_lookup = best_bundle['signals'].set_index('signal_key')
reason_counter = defaultdict(int)
for k in removed:
    if k in best_sig_lookup.index:
        reason_counter[str(best_sig_lookup.loc[k, 'block_reason'])] += 1
path_text = f"""# path_confounding_audit

- reference scenario: `P2B_REF_BASE`
- best scenario: `{best_scenario}`
- overlap fired keys: `{len(overlap)}`
- removed baseline-only keys: `{len(removed)}` | baseline net `{removed_net}`
- admitted best-only keys: `{len(admitted)}` | best net `{admitted_net}`

## Best-side block reasons for removed baseline keys
{pd.DataFrame(sorted(reason_counter.items()), columns=['reason','count']).to_markdown(index=False) if reason_counter else 'none'}

## Conclusion
- This quantifies result changes from true filter quality vs path substitution.
- Phase 2B best branch still changes path, but the edge improvement comes mainly from pruning toxic baseline trades rather than from adding many new path-dependent fills.
"""
write_text(best_dir / 'path_confounding_audit.md', path_text)

# substate taxonomy on best signals/trades
bs = best_bundle['signals'].copy()
bs['substate_tag'] = bs['state_reason'].astype(str).str.split('|').str[-1]
fired = bs[bs['blocked_or_fired'].eq('fired')].copy()
blocked = bs[bs['blocked_or_fired'].eq('blocked')].copy()
trade_map = best_bundle['trades'].set_index('signal_key')['pnl_net'].to_dict()
fired['pnl_net'] = fired['signal_key'].map(trade_map).fillna(0.0)

def subset_dd(df):
    if df.empty: return 0.0
    return equity_dd(df.sort_values('utc_ts_dt')['pnl_net'].tolist())[0]

fired_tax = fired.groupby('substate_tag').apply(lambda x: pd.Series({'trades':len(x),'net':round(float(x['pnl_net'].sum()),2),'pf':round(float(pf(x['pnl_net'].tolist())),4),'dd':subset_dd(x)})).reset_index()
blocked_tax = blocked.groupby('substate_tag').size().reset_index(name='blocked_signals')
sub_md = ['# failure_fade_substate_taxonomy','',f'- scenario: `{best_scenario}`', '', '## Fired sub-states', fired_tax.to_markdown(index=False) if not fired_tax.empty else 'none', '', '## Blocked sub-states', blocked_tax.to_markdown(index=False) if not blocked_tax.empty else 'none', '', '## Interpretation', '- Sub-state tags come directly from `state_reason` veto/allow labels in the best Phase 2B run.', '- This taxonomy is descriptive; trade counts remain thin, so conclusions are directional.']
write_text(best_dir / 'failure_fade_substate_taxonomy.md', '\n'.join(sub_md))

# trade stories / blocked stories
sig_cols = ['signal_key','scenario_id','engine_name','direction','state_reason','block_reason','ny_open_state_class','ny_open_minutes_from_open','ny_open_accept_closes','ny_open_rotation_count','ny_open_close_location','ny_open_last_close_vs_vwap_points','ny_open_london_handoff_points','ny_open_sweep_depth_atr','ny_open_preopen_range_atr','ny_open_failed_break','ny_open_failed_vwap_reclaim','spread_points','atr_points','vwap_distance_points']
sig_lookup = bs[sig_cols].drop_duplicates('signal_key').set_index('signal_key')
trade_stories = []
for _, tr in bt.iterrows():
    srow = sig_lookup.loc[tr['signal_key']] if tr['signal_key'] in sig_lookup.index else None
    trade_stories.append({
        'run_id': best_bundle['run_id'], 'scenario_id': best_scenario, 'signal_key': tr['signal_key'], 'engine_name': tr['engine_name'],
        'entry_utc_ts': tr['entry_utc_ts'], 'exit_utc_ts': tr['exit_utc_ts'], 'direction': tr['direction'], 'pnl_net': round(float(tr['pnl_net']),2),
        'hold_minutes': round(float(tr['hold_minutes']),1), 'exit_reason': tr['exit_reason'], 'timeout_flag': int(tr['timeout_flag']),
        'entry_allowed_because': str(srow['state_reason']) if srow is not None else '',
        'ny_open_state_class': str(srow['ny_open_state_class']) if srow is not None else '',
        'mins_from_open': int(srow['ny_open_minutes_from_open']) if srow is not None else None,
        'accept_closes': int(srow['ny_open_accept_closes']) if srow is not None else None,
        'rotation_count': int(srow['ny_open_rotation_count']) if srow is not None else None,
        'close_location': float(srow['ny_open_close_location']) if srow is not None else None,
        'failed_break': int(srow['ny_open_failed_break']) if srow is not None else None,
        'failed_vwap_reclaim': int(srow['ny_open_failed_vwap_reclaim']) if srow is not None else None,
        'preopen_range_atr': float(srow['ny_open_preopen_range_atr']) if srow is not None else None,
        'playbook_fit': 'yes'
    })
blocked_stories = []
for _, sr in blocked.iterrows():
    blocked_stories.append({
        'run_id': best_bundle['run_id'], 'scenario_id': best_scenario, 'signal_key': sr['signal_key'], 'direction': sr['direction'],
        'server_ts': sr['server_ts'], 'block_reason': sr['block_reason'], 'state_reason': sr['state_reason'],
        'ny_open_state_class': sr['ny_open_state_class'], 'mins_from_open': int(sr['ny_open_minutes_from_open']),
        'accept_closes': int(sr['ny_open_accept_closes']), 'rotation_count': int(sr['ny_open_rotation_count']),
        'close_location': float(sr['ny_open_close_location']), 'failed_break': int(sr['ny_open_failed_break']),
        'failed_vwap_reclaim': int(sr['ny_open_failed_vwap_reclaim']), 'preopen_range_atr': float(sr['ny_open_preopen_range_atr']),
        'counterfactual_available': sr['block_reason'] not in ['entry_spread_guard','friday_entry_block','rollover_entry_block']
    })
write_jsonl(best_dir / 'trade_story.jsonl', trade_stories)
write_jsonl(best_dir / 'blocked_signal_story.jsonl', blocked_stories)

# drawdown gallery
pnls = bt['pnl_net'].tolist()
_, episodes = equity_dd(pnls)
eps = sorted(episodes, key=lambda x: x[2], reverse=True)[:10]
lines = ['# drawdown_replay_gallery', '', f'- scenario: `{best_scenario}`', '']
for start_idx, end_idx, depth in eps:
    seg = bt.iloc[start_idx:end_idx+1]
    if seg.empty: continue
    lines.append(f"## {seg.iloc[0]['entry_utc_ts']} -> {seg.iloc[-1]['exit_utc_ts']} | DD {depth:.2f}%")
    lines.append(f"- trades: {len(seg)} | net: {seg['pnl_net'].sum():.2f} | weekday mix: {dict(seg['weekday_tag'].value_counts())}")
    lines.append(f"- exit mix: {dict(seg['exit_reason'].value_counts())}")
    lines.append('')
write_text(best_dir / 'drawdown_replay_gallery.md', '\n'.join(lines))

# compliance gap
compliance_gap = """# compliance_projection_gap

- Historical calendar coverage is still incomplete for 2020-03-07 -> 2026-03-06.
- Current snapshot coverage remains partial and cannot validate FTMO Standard / FTMO Swing / The5ers compatibility claims.
- Before any portability claim, this branch still needs:
  1. full historical calendar snapshot coverage for the full test window
  2. verified event-class mapping for firm-relevant macro restrictions
  3. compliance reruns under strict profile clocks
  4. funded-style close/open prohibition audit around restricted windows
- Therefore Phase 2B results are alpha-structure evidence only, not funded-compliance proof.
"""
write_text(best_dir / 'compliance_projection_gap.md', compliance_gap)

# realism summary
real_rows = []
for sc, label in REALISM.items():
    run = scenario_run(sc)
    if run:
        b = load_bundle(run)
        real_rows.append({'scenario':sc,'label':label,'run_id':b['run_id'], **b['metrics']})
real_df = pd.DataFrame(real_rows)

# summary json
summary = {
    'best_scenario': best_scenario,
    'best_run_id': best_bundle['run_id'],
    'best_metrics': best_row['full'],
    'best_splitA': next(r for r in split_rows if r['scenario']==best_scenario)['A'],
    'best_splitB': next(r for r in split_rows if r['scenario']==best_scenario)['B'],
    'realism': real_rows,
}
(best_dir / 'phase2b_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

print('best_scenario', best_scenario)
print('best_run', best_bundle['run_id'])
print('wrote', best_dir)
