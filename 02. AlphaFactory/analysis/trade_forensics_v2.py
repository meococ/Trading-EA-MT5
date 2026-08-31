"""Cobra + SilverBullet deep trade pairing & forensics."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
from bs4 import BeautifulSoup
from datetime import datetime
import numpy as np
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def parse_paired_trades(path):
    with open(path, 'rb') as f:
        raw = f.read()
    try:
        text = raw.decode('utf-16')
    except:
        text = raw.decode('utf-8', errors='ignore')
    soup = BeautifulSoup(text, 'html.parser')
    tables = soup.find_all('table')
    if len(tables) < 2:
        return []

    # Table 0: Orders (entries have SL/TP in cols 6,7)
    order_info = {}
    for row in tables[0].find_all('tr'):
        cells = row.find_all('td')
        if len(cells) >= 10:
            try:
                typ = cells[3].get_text(strip=True).lower()
                if typ in ('buy', 'sell'):
                    sl_text = cells[6].get_text(strip=True).replace(' ', '')
                    tp_text = cells[7].get_text(strip=True).replace(' ', '')
                    sl = float(sl_text) if sl_text else 0
                    tp = float(tp_text) if tp_text else 0
                    oid = cells[1].get_text(strip=True)
                    comment = cells[10].get_text(strip=True) if len(cells) > 10 else ''
                    if sl > 0:  # entries have SL set
                        order_info[oid] = {'sl': sl, 'tp': tp, 'comment': comment, 'type': typ}
            except:
                pass

    # Table 1: Deals
    deals = []
    for row in tables[1].find_all('tr'):
        cells = row.find_all('td')
        if len(cells) >= 12:
            try:
                typ = cells[3].get_text(strip=True).lower()
                if typ in ('buy', 'sell'):
                    direction = cells[4].get_text(strip=True).lower()
                    pnl_t = cells[10].get_text(strip=True).replace(' ', '').replace('\xa0', '')
                    pnl = float(pnl_t) if pnl_t else 0
                    price_t = cells[6].get_text(strip=True).replace(' ', '').replace('\xa0', '')
                    price = float(price_t) if price_t else 0
                    deals.append({
                        'time': cells[0].get_text(strip=True)[:19],
                        'type': typ,
                        'direction': direction,
                        'price': price,
                        'order': cells[7].get_text(strip=True),
                        'pnl': pnl,
                        'comment': cells[12].get_text(strip=True) if len(cells) > 12 else '',
                    })
            except:
                pass

    entries = [d for d in deals if d['direction'] == 'in']
    exits = [d for d in deals if d['direction'] == 'out']

    trades = []
    exit_idx = 0
    for entry in entries:
        if exit_idx >= len(exits):
            break
        ex = exits[exit_idx]
        exit_idx += 1

        et = datetime.strptime(entry['time'], '%Y.%m.%d %H:%M:%S')
        xt = datetime.strptime(ex['time'], '%Y.%m.%d %H:%M:%S')
        hold_min = (xt - et).total_seconds() / 60

        oi = order_info.get(entry['order'], {})
        sl = oi.get('sl', 0)
        tp = oi.get('tp', 0)
        comment = oi.get('comment', entry.get('comment', ''))

        comment_lower = ex['comment'].lower()
        if 'sl' in comment_lower:
            exit_type = 'SL'
        elif 'tp' in comment_lower:
            exit_type = 'TP'
        elif abs(ex['pnl']) < 1.0:
            exit_type = 'BE'
        else:
            exit_type = 'TIME'

        # SL distance
        if entry['type'] == 'sell' and sl > 0:
            sl_dist = sl - entry['price']
        elif entry['type'] == 'buy' and sl > 0:
            sl_dist = entry['price'] - sl
        else:
            sl_dist = 0

        trades.append({
            'entry_time': et,
            'exit_time': xt,
            'direction': entry['type'],
            'entry_price': entry['price'],
            'exit_price': ex['price'],
            'sl': sl,
            'tp': tp,
            'sl_dist': abs(sl_dist),
            'hold_min': hold_min,
            'pnl': ex['pnl'],
            'exit_type': exit_type,
            'comment': comment,
            'hour': et.hour,
            'dow': et.weekday(),
            'year': et.year,
            'month': et.month,
        })

    return trades


def deep_analyze(trades, name):
    n = len(trades)
    if n == 0:
        print(f"{name}: No trades")
        return
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    pnls = [t['pnl'] for t in trades]
    gross_win = sum(t['pnl'] for t in wins)
    gross_loss = abs(sum(t['pnl'] for t in losses))
    pf = gross_win / max(gross_loss, 0.01)
    wr = len(wins) / n * 100

    print(f"\n{'=' * 70}")
    print(f" {name} — {n} trades | PF {pf:.2f} | WR {wr:.1f}%")
    print(f"{'=' * 70}")

    # 1. HOLD TIME
    win_h = [t['hold_min'] for t in wins if t['hold_min'] > 0]
    loss_h = [t['hold_min'] for t in losses if t['hold_min'] > 0]
    print(f"\n[1] HOLD TIME (minutes):")
    if win_h:
        print(f"  Winners:  median={np.median(win_h):.0f}  mean={np.mean(win_h):.0f}  max={max(win_h):.0f}")
    if loss_h:
        print(f"  Losers:   median={np.median(loss_h):.0f}  mean={np.mean(loss_h):.0f}  max={max(loss_h):.0f}")
    if win_h and loss_h:
        if np.median(loss_h) < np.median(win_h):
            print(f"  -> Losers die FAST ({np.median(loss_h):.0f}m) vs winners survive ({np.median(win_h):.0f}m)")
        else:
            print(f"  -> Losers linger LONGER = market grinds against position slowly")

    # Quick SL
    quick_sl = [t for t in losses if t['hold_min'] < 15]
    if quick_sl:
        pct = len(quick_sl) / len(losses) * 100
        dmg = sum(t['pnl'] for t in quick_sl)
        print(f"  Quick losses (<15m): {len(quick_sl)} ({pct:.0f}% of losses), damage=${dmg:,.0f}")

    # 2. EXIT TYPE
    print(f"\n[2] EXIT TYPE:")
    exit_stats = defaultdict(lambda: {'n': 0, 'pnl': 0, 'wins': 0})
    for t in trades:
        et = t['exit_type']
        exit_stats[et]['n'] += 1
        exit_stats[et]['pnl'] += t['pnl']
        if t['pnl'] > 0:
            exit_stats[et]['wins'] += 1
    for et in ['TP', 'SL', 'BE', 'TIME']:
        if et in exit_stats:
            s = exit_stats[et]
            wr_e = s['wins'] / s['n'] * 100 if s['n'] > 0 else 0
            print(f"  {et:>5}: {s['n']:>4} ({s['n']/n*100:>5.1f}%)  P&L ${s['pnl']:>+9,.0f}  WR {wr_e:>5.1f}%")

    # 3. SETUP TYPE (from comment)
    print(f"\n[3] SETUP TYPE (from entry comment):")
    setup_map = defaultdict(lambda: {'n': 0, 'pnl': 0, 'wins': 0})
    for t in trades:
        c = t['comment'].upper()
        if 'BREAK_ASIA' in c:
            s = 'BREAK_ASIA'
        elif 'BREAK_PREV' in c:
            s = 'BREAK_PREV'
        elif 'FVG' in c or 'DISPLACEMENT' in c:
            s = 'FVG_ENTRY'
        elif 'ASIAN' in c or 'RANGE' in c:
            s = 'RANGE_BREAK'
        elif 'LDN' in c or 'LONDON' in c:
            s = 'LDN_SESSION'
        elif 'NY' in c:
            s = 'NY_SESSION'
        elif 'SB' in c:
            s = 'SB_SIGNAL'
        else:
            s = c[:25] if c else 'UNKNOWN'
        setup_map[s]['n'] += 1
        setup_map[s]['pnl'] += t['pnl']
        if t['pnl'] > 0:
            setup_map[s]['wins'] += 1

    for s, data in sorted(setup_map.items(), key=lambda x: -x[1]['n']):
        wr_s = data['wins'] / data['n'] * 100 if data['n'] > 0 else 0
        pf_s = sum(t['pnl'] for t in trades if t['pnl'] > 0 and s in t['comment'].upper()) / max(abs(sum(t['pnl'] for t in trades if t['pnl'] <= 0 and s in t['comment'].upper())), 0.01)
        marker = ' <<<WEAK' if data['pnl'] < 0 and data['n'] >= 5 else ''
        print(f"  {s:>25}: {data['n']:>4}t  WR {wr_s:>5.1f}%  P&L ${data['pnl']:>+8,.0f}{marker}")

    # 4. DIRECTION
    print(f"\n[4] DIRECTION BIAS:")
    for d in ['buy', 'sell']:
        dt = [t for t in trades if t['direction'] == d]
        if dt:
            d_pnl = sum(t['pnl'] for t in dt)
            d_wr = sum(1 for t in dt if t['pnl'] > 0) / len(dt) * 100
            d_gw = sum(t['pnl'] for t in dt if t['pnl'] > 0)
            d_gl = abs(sum(t['pnl'] for t in dt if t['pnl'] <= 0))
            d_pf = d_gw / max(d_gl, 0.01)
            marker = ' <<<WEAK' if d_pnl < 0 else ''
            print(f"  {d.upper():>5}: {len(dt):>4}t  WR {d_wr:>5.1f}%  PF {d_pf:.2f}  P&L ${d_pnl:>+8,.0f}{marker}")

    # 5. HOUR BREAKDOWN
    print(f"\n[5] ENTRY HOUR:")
    hour_stats = defaultdict(lambda: {'n': 0, 'pnl': 0, 'wins': 0})
    for t in trades:
        h = t['hour']
        hour_stats[h]['n'] += 1
        hour_stats[h]['pnl'] += t['pnl']
        if t['pnl'] > 0:
            hour_stats[h]['wins'] += 1
    for h in sorted(hour_stats.keys()):
        s = hour_stats[h]
        wr_h = s['wins'] / s['n'] * 100 if s['n'] > 0 else 0
        marker = '  <<<RED' if s['pnl'] < 0 and s['n'] >= 5 else ''
        print(f"  H{h:02d}: {s['n']:>3}t  WR {wr_h:>5.1f}%  P&L ${s['pnl']:>+8,.0f}{marker}")

    # 6. DAY OF WEEK
    dow_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
    print(f"\n[6] DAY OF WEEK:")
    for d in range(5):
        dt = [t for t in trades if t['dow'] == d]
        if dt:
            d_pnl = sum(t['pnl'] for t in dt)
            d_wr = sum(1 for t in dt if t['pnl'] > 0) / len(dt) * 100
            marker = '  <<<RED' if d_pnl < 0 and len(dt) >= 5 else ''
            print(f"  {dow_names[d]}: {len(dt):>3}t  WR {d_wr:>5.1f}%  P&L ${d_pnl:>+8,.0f}{marker}")

    # 7. TOP WINS AND LOSSES
    sorted_trades = sorted(trades, key=lambda x: x['pnl'], reverse=True)
    print(f"\n[7] TOP 5 WINS:")
    for t in sorted_trades[:5]:
        print(f"  {t['entry_time'].strftime('%Y-%m-%d %H:%M')} {t['direction']:>4} @{t['entry_price']:.2f} -> {t['exit_price']:.2f}")
        print(f"    ${t['pnl']:>+.0f} | SL={t['sl']:.2f} | Hold {t['hold_min']:.0f}m | {t['exit_type']} | {t['comment'][:40]}")

    print(f"\n[8] TOP 5 LOSSES:")
    for t in sorted_trades[-5:]:
        print(f"  {t['entry_time'].strftime('%Y-%m-%d %H:%M')} {t['direction']:>4} @{t['entry_price']:.2f} -> {t['exit_price']:.2f}")
        print(f"    ${t['pnl']:>+.0f} | SL={t['sl']:.2f} | Hold {t['hold_min']:.0f}m | {t['exit_type']} | {t['comment'][:40]}")

    # 8. YEARLY
    print(f"\n[9] YEARLY DETAIL:")
    yearly = defaultdict(lambda: {'n': 0, 'pnl': 0, 'wins': 0})
    for t in trades:
        yearly[t['year']]['n'] += 1
        yearly[t['year']]['pnl'] += t['pnl']
        if t['pnl'] > 0:
            yearly[t['year']]['wins'] += 1
    for y in sorted(yearly.keys()):
        s = yearly[y]
        wr_y = s['wins'] / s['n'] * 100
        marker = ' <<<RED' if s['pnl'] < 0 else ''
        print(f"  {y}: {s['n']:>3}t  WR {wr_y:>5.1f}%  P&L ${s['pnl']:>+8,.0f}{marker}")

    # 9. CONCENTRATION
    top10n = max(1, len(wins) // 10)
    top10_pnl = sum(t['pnl'] for t in sorted(wins, key=lambda x: x['pnl'], reverse=True)[:top10n])
    conc = top10_pnl / max(gross_win, 0.01) * 100
    print(f"\n[10] PROFIT CONCENTRATION: top {top10n} wins = ${top10_pnl:,.0f} = {conc:.0f}% of gross profit")

    return trades


# =================== RUN ===================
ea_files = [
    ('COBRA XAUUSD', os.path.join(BASE, 'runs/EA_Cobra/20260402_221001/report.html')),
    ('SILVERBULLET USDJPY', os.path.join(BASE, 'runs/EA_SilverBullet/20260402_221105/report.html')),
    ('SPARK USDJPY', os.path.join(BASE, 'runs/EA_Spark/20260402_221310/report.html')),
    ('SPARK GBPUSD', os.path.join(BASE, 'runs/EA_Spark/20260402_221411/report.html')),
]

print("DEEP TRADE FORENSICS — Understanding every trade")
print("=" * 70)

for name, path in ea_files:
    trades = parse_paired_trades(path)
    print(f"\n[PARSE] {name}: {len(trades)} paired trades")
    deep_analyze(trades, name)
