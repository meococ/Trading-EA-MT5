"""
Trade Forensics — Deep analysis of individual trades
Extracts every trade from MT5 report, classifies by R-multiple,
analyzes hold time, entry quality, exit type, and market context.
"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def parse_trades_from_html(path):
    """Parse MT5 report into structured trade list (round-trip: open + close)."""
    with open(path, 'rb') as f:
        raw = f.read()
    try:
        text = raw.decode('utf-16')
    except:
        text = raw.decode('utf-8', errors='ignore')

    soup = BeautifulSoup(text, 'html.parser')

    # Find the deals table with 13-column header including "Lợi nhuận" and "Cân bằng"
    deals = []
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 12:
                try:
                    type_text = cells[3].get_text(strip=True).lower()
                    if type_text in ('buy', 'sell', 'balance'):
                        deal = {
                            'time': cells[0].get_text(strip=True)[:19],
                            'ticket': cells[1].get_text(strip=True),
                            'symbol': cells[2].get_text(strip=True),
                            'type': type_text,
                            'direction': cells[4].get_text(strip=True).lower() if len(cells) > 4 else '',
                            'volume': cells[5].get_text(strip=True).replace(' ','') if len(cells) > 5 else '',
                            'price': cells[6].get_text(strip=True).replace(' ','') if len(cells) > 6 else '',
                            'order': cells[7].get_text(strip=True) if len(cells) > 7 else '',
                            'commission': cells[8].get_text(strip=True).replace(' ','').replace('\xa0','') if len(cells) > 8 else '0',
                            'swap': cells[9].get_text(strip=True).replace(' ','').replace('\xa0','') if len(cells) > 9 else '0',
                            'profit': cells[10].get_text(strip=True).replace(' ','').replace('\xa0','') if len(cells) > 10 else '0',
                            'balance': cells[11].get_text(strip=True).replace(' ','').replace('\xa0','') if len(cells) > 11 else '',
                            'comment': cells[12].get_text(strip=True) if len(cells) > 12 else '',
                        }
                        deals.append(deal)
                except:
                    pass

    # Pair up trades: entry (direction='in') + exit (direction='out')
    # MT5 format: entries have 'in' direction, exits have 'out'
    open_positions = {}  # order -> entry deal
    completed_trades = []

    for d in deals:
        if d['type'] == 'balance':
            continue

        direction = d.get('direction', '')

        if direction == 'in' or (direction == '' and d['comment'] and not any(x in d['comment'].lower() for x in ['sl', 'tp', 'so'])):
            # Entry deal
            try:
                entry_price = float(d['price']) if d['price'] else 0
                vol_text = d['volume']
                vol = float(vol_text.split('/')[0]) if '/' in vol_text else (float(vol_text) if vol_text else 0)

                open_positions[d['order']] = {
                    'entry_time': d['time'],
                    'entry_price': entry_price,
                    'direction': d['type'],  # buy or sell
                    'volume': vol,
                    'symbol': d['symbol'],
                    'comment': d['comment'],
                    'ticket': d['ticket'],
                }
            except:
                pass

        elif direction == 'out' or (direction == '' and d.get('profit', '0') != '0'):
            # Exit deal
            try:
                pnl = float(d['profit']) if d['profit'] else 0
                swap = float(d['swap']) if d['swap'] else 0
                comm = float(d['commission']) if d['commission'] else 0
                exit_price = float(d['price']) if d['price'] else 0

                if abs(pnl) < 0.001:
                    continue

                # Find matching entry
                entry = open_positions.pop(d['order'], None)

                trade = {
                    'entry_time': entry['entry_time'] if entry else '',
                    'exit_time': d['time'],
                    'direction': entry['direction'] if entry else ('buy' if pnl > 0 else 'sell'),
                    'entry_price': entry['entry_price'] if entry else 0,
                    'exit_price': exit_price,
                    'volume': entry['volume'] if entry else 0,
                    'pnl': pnl + swap + comm,
                    'profit_raw': pnl,
                    'swap': swap,
                    'commission': comm,
                    'comment': d['comment'],
                    'entry_comment': entry['comment'] if entry else '',
                    'symbol': d['symbol'] if d['symbol'] else (entry['symbol'] if entry else ''),
                }

                # Calculate hold duration
                if trade['entry_time'] and trade['exit_time']:
                    try:
                        et = datetime.strptime(trade['entry_time'], '%Y.%m.%d %H:%M:%S')
                        xt = datetime.strptime(trade['exit_time'], '%Y.%m.%d %H:%M:%S')
                        trade['hold_minutes'] = (xt - et).total_seconds() / 60
                        trade['entry_dt'] = et
                        trade['exit_dt'] = xt
                        trade['entry_hour'] = et.hour
                        trade['exit_hour'] = xt.hour
                        trade['entry_dow'] = et.weekday()  # 0=Mon
                    except:
                        trade['hold_minutes'] = 0

                # Determine exit type from comment
                comment_lower = d['comment'].lower()
                if 'sl' in comment_lower:
                    trade['exit_type'] = 'SL'
                elif 'tp' in comment_lower:
                    trade['exit_type'] = 'TP'
                elif 'be' in comment_lower or abs(pnl) < 1.0:
                    trade['exit_type'] = 'BE'
                else:
                    trade['exit_type'] = 'OTHER'

                completed_trades.append(trade)
            except:
                pass

    return completed_trades


def analyze_trades(trades, ea_name):
    """Deep analysis of trade list."""
    if not trades:
        print(f"\n{ea_name}: No trades parsed")
        return

    n = len(trades)
    pnls = [t['pnl'] for t in trades]
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] < 0]

    print(f"\n{'=' * 70}")
    print(f" {ea_name} — TRADE FORENSICS ({n} trades)")
    print(f"{'=' * 70}")

    # Basic stats
    total_win = sum(t['pnl'] for t in wins)
    total_loss = abs(sum(t['pnl'] for t in losses))
    pf = total_win / max(total_loss, 0.01)
    wr = len(wins) / n * 100
    avg_win = np.mean([t['pnl'] for t in wins]) if wins else 0
    avg_loss = np.mean([t['pnl'] for t in losses]) if losses else 0

    print(f"\n  PF: {pf:.2f} | WR: {wr:.1f}% | Avg Win: ${avg_win:.0f} | Avg Loss: ${avg_loss:.0f}")
    print(f"  Win/Loss ratio: {abs(avg_win/avg_loss):.2f}R" if avg_loss != 0 else "  No losses")

    # Hold time analysis
    hold_times = [t.get('hold_minutes', 0) for t in trades if t.get('hold_minutes', 0) > 0]
    win_holds = [t.get('hold_minutes', 0) for t in wins if t.get('hold_minutes', 0) > 0]
    loss_holds = [t.get('hold_minutes', 0) for t in losses if t.get('hold_minutes', 0) > 0]

    if hold_times:
        print(f"\n  HOLD TIME:")
        print(f"    All:    median {np.median(hold_times):.0f}m, mean {np.mean(hold_times):.0f}m, max {max(hold_times):.0f}m")
        if win_holds:
            print(f"    Wins:   median {np.median(win_holds):.0f}m, mean {np.mean(win_holds):.0f}m")
        if loss_holds:
            print(f"    Losses: median {np.median(loss_holds):.0f}m, mean {np.mean(loss_holds):.0f}m")

        quick_losses = [t for t in losses if t.get('hold_minutes', 999) < 30]
        if quick_losses:
            ql_pnl = sum(t['pnl'] for t in quick_losses)
            print(f"    Quick losses (<30m): {len(quick_losses)} trades, ${ql_pnl:.0f} (bad entries?)")

    # Exit type breakdown
    exit_types = defaultdict(lambda: {'count': 0, 'pnl': 0})
    for t in trades:
        et = t.get('exit_type', 'UNKNOWN')
        exit_types[et]['count'] += 1
        exit_types[et]['pnl'] += t['pnl']

    print(f"\n  EXIT TYPE BREAKDOWN:")
    for et, data in sorted(exit_types.items()):
        pct = data['count'] / n * 100
        print(f"    {et:>8}: {data['count']:>4} ({pct:>5.1f}%)  P&L: ${data['pnl']:>+8.0f}")

    # Hour analysis
    hour_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0})
    for t in trades:
        h = t.get('entry_hour', -1)
        if h >= 0:
            if t['pnl'] > 0:
                hour_stats[h]['wins'] += 1
            else:
                hour_stats[h]['losses'] += 1
            hour_stats[h]['pnl'] += t['pnl']

    if hour_stats:
        print(f"\n  ENTRY HOUR BREAKDOWN:")
        for h in sorted(hour_stats.keys()):
            s = hour_stats[h]
            total = s['wins'] + s['losses']
            wr_h = s['wins'] / total * 100 if total > 0 else 0
            marker = '  <<<' if s['pnl'] < 0 and total >= 5 else ''
            print(f"    H{h:02d}: {total:>3}t  WR {wr_h:>5.1f}%  P&L ${s['pnl']:>+8.0f}{marker}")

    # Day of week
    dow_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    dow_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0})
    for t in trades:
        d = t.get('entry_dow', -1)
        if d >= 0:
            if t['pnl'] > 0:
                dow_stats[d]['wins'] += 1
            else:
                dow_stats[d]['losses'] += 1
            dow_stats[d]['pnl'] += t['pnl']

    if dow_stats:
        print(f"\n  DAY OF WEEK:")
        for d in sorted(dow_stats.keys()):
            s = dow_stats[d]
            total = s['wins'] + s['losses']
            wr_d = s['wins'] / total * 100 if total > 0 else 0
            marker = '  <<<' if s['pnl'] < 0 and total >= 5 else ''
            print(f"    {dow_names[d]}: {total:>3}t  WR {wr_d:>5.1f}%  P&L ${s['pnl']:>+8.0f}{marker}")

    # TOP 5 BIGGEST WINS
    sorted_by_pnl = sorted(trades, key=lambda t: t['pnl'], reverse=True)
    print(f"\n  TOP 5 BIGGEST WINS:")
    for t in sorted_by_pnl[:5]:
        hold = t.get('hold_minutes', 0)
        print(f"    {t.get('entry_time','')} {t['direction']:>4} ${t['pnl']:>+8.0f}  hold:{hold:>5.0f}m  exit:{t.get('exit_type','?')}  {t.get('entry_comment','')[:30]}")

    # TOP 5 BIGGEST LOSSES
    print(f"\n  TOP 5 BIGGEST LOSSES:")
    for t in sorted_by_pnl[-5:]:
        hold = t.get('hold_minutes', 0)
        print(f"    {t.get('entry_time','')} {t['direction']:>4} ${t['pnl']:>+8.0f}  hold:{hold:>5.0f}m  exit:{t.get('exit_type','?')}  {t.get('comment','')[:30]}")

    # Consecutive analysis
    streaks = []
    curr = 0
    for p in pnls:
        if p < 0:
            curr -= 1
        else:
            if curr < 0:
                streaks.append(curr)
            curr = 0
    if curr < 0:
        streaks.append(curr)

    if streaks:
        worst_streak = min(streaks)
        print(f"\n  LOSING STREAKS: worst={abs(worst_streak)}, avg={np.mean([abs(s) for s in streaks]):.1f}")

        # What happened during worst streak?
        idx = 0
        for i, p in enumerate(pnls):
            curr_s = 0
            for j in range(i, len(pnls)):
                if pnls[j] < 0:
                    curr_s -= 1
                    if curr_s == worst_streak:
                        print(f"    Worst streak trades ({i} to {j}):")
                        for k in range(i, j+1):
                            t = trades[k]
                            print(f"      {t.get('entry_time','')} {t['direction']:>4} ${t['pnl']:>+6.0f} exit:{t.get('exit_type','?')}")
                        idx = 1
                        break
                else:
                    break
            if idx:
                break

    # Yearly profit stability
    yearly = defaultdict(lambda: {'pnl': 0, 'n': 0, 'wins': 0})
    for t in trades:
        if 'entry_dt' in t:
            y = t['entry_dt'].year
            yearly[y]['pnl'] += t['pnl']
            yearly[y]['n'] += 1
            if t['pnl'] > 0:
                yearly[y]['wins'] += 1

    print(f"\n  YEARLY DETAIL:")
    for y in sorted(yearly.keys()):
        s = yearly[y]
        wr_y = s['wins'] / s['n'] * 100 if s['n'] > 0 else 0
        marker = ' <<<RED' if s['pnl'] < 0 else ''
        print(f"    {y}: {s['n']:>3}t  WR {wr_y:>5.1f}%  P&L ${s['pnl']:>+8.0f}{marker}")

    return trades


# ==========================================
# RUN FORENSICS
# ==========================================
print("TRADE FORENSICS — Understanding Every Trade")
print("=" * 70)

ea_reports = [
    ('EA_Cobra XAUUSD', os.path.join(BASE, 'runs/EA_Cobra/20260402_221001/report.html')),
    ('EA_SilverBullet USDJPY', os.path.join(BASE, 'runs/EA_SilverBullet/20260402_221105/report.html')),
    ('EA_Spark USDJPY', os.path.join(BASE, 'runs/EA_Spark/20260402_221310/report.html')),
    ('EA_Spark GBPUSD', os.path.join(BASE, 'runs/EA_Spark/20260402_221411/report.html')),
]

all_results = {}
for ea_name, path in ea_reports:
    trades = parse_trades_from_html(path)
    print(f"\n[PARSE] {ea_name}: {len(trades)} round-trip trades extracted")
    result = analyze_trades(trades, ea_name)
    all_results[ea_name] = result
