"""Critical Portfolio Dashboard — Session 20 Honest Assessment"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from datetime import datetime
from bs4 import BeautifulSoup
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def parse_deals(path):
    with open(path, 'rb') as f:
        raw = f.read()
    try:
        text = raw.decode('utf-16')
    except:
        text = raw.decode('utf-8', errors='ignore')
    soup = BeautifulSoup(text, 'html.parser')
    deals = []
    for table in soup.find_all('table'):
        for row in table.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 12:
                try:
                    t = cells[3].get_text(strip=True).lower()
                    if t in ('buy', 'sell'):
                        pnl = float(cells[10].get_text(strip=True).replace(' ', '').replace('\xa0', ''))
                        if abs(pnl) > 0.001:
                            dt = datetime.strptime(cells[0].get_text(strip=True)[:19], '%Y.%m.%d %H:%M:%S')
                            deals.append((dt, pnl))
                except:
                    pass
    return deals

reports = [
    ('Cobra', os.path.join(BASE, 'runs/EA_Cobra/20260402_221001/report.html'), '#1565C0'),
    ('SilverBullet', os.path.join(BASE, 'runs/EA_SilverBullet/20260402_221105/report.html'), '#2E7D32'),
    ('Spark UJ', os.path.join(BASE, 'runs/EA_Spark/20260402_221310/report.html'), '#E65100'),
    ('Spark GU', os.path.join(BASE, 'runs/EA_Spark/20260402_221411/report.html'), '#6A1B9A'),
    ('IB UJ', os.path.join(BASE, 'runs/EA_InsideBar/20260402_221451/report.html'), '#C62828'),
    ('IB GU', os.path.join(BASE, 'runs/EA_InsideBar/20260402_221537/report.html'), '#00838F'),
]

all_ea_data = {}
for name, path, color in reports:
    all_ea_data[name] = parse_deals(path)
    print(f"{name}: {len(all_ea_data[name])} closing deals")

# ========== FIGURE 1: INDIVIDUAL EQUITY + DD OVERLAY ==========
fig1, axes = plt.subplots(3, 2, figsize=(20, 16))
fig1.suptitle('INDIVIDUAL EQUITY CURVES\nGreen = new equity high, Red = underwater',
              fontsize=14, fontweight='bold', y=0.99)

for idx, (name, path, color) in enumerate(reports):
    ax = axes[idx // 2][idx % 2]
    deals = all_ea_data[name]
    pnls = [d[1] for d in deals]
    dates = [d[0] for d in deals]
    n = len(pnls)

    equity = [10000.0]
    for p in pnls:
        equity.append(equity[-1] + p)
    eq_dates = [dates[0]] + dates

    peak = np.maximum.accumulate(equity)
    dd_pct = (np.array(equity) - peak) / peak * 100
    max_dd = float(min(dd_pct))

    # Green when at/near peak, red when underwater
    for i in range(1, len(equity)):
        c_line = '#4CAF50' if dd_pct[i] >= -0.5 else '#EF5350'
        ax.plot([eq_dates[i-1], eq_dates[i]], [equity[i-1], equity[i]], color=c_line, linewidth=1.0)

    # DD shading
    ax2 = ax.twinx()
    ax2.fill_between(eq_dates, dd_pct, 0, alpha=0.15, color='red')
    ax2.set_ylim(max_dd * 2, 3)
    ax2.set_ylabel('DD %', color='red', fontsize=7)
    ax2.tick_params(axis='y', labelcolor='red', labelsize=6)

    ax.axhline(y=10000, color='gray', linestyle='--', alpha=0.4)

    pf_val = sum(p for p in pnls if p > 0) / max(abs(sum(p for p in pnls if p < 0)), 0.01)
    wr_val = sum(1 for p in pnls if p > 0) / max(n, 1) * 100
    uw_pct = sum(1 for d in dd_pct if d < -0.5) / len(dd_pct) * 100

    flags = []
    if pf_val < 1.3: flags.append(f'PF {pf_val:.2f}')
    if uw_pct > 70: flags.append(f'UW {uw_pct:.0f}%')
    if n < 100: flags.append(f'{n}t')
    flag_str = ' | '.join(flags) if flags else 'OK'
    title_c = 'red' if len(flags) >= 2 else ('darkorange' if flags else 'green')

    ax.set_title(f'{name}  [{flag_str}]', fontsize=10, fontweight='bold', color=title_c)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.tick_params(labelsize=7)
    ax.grid(True, alpha=0.15)

    stats_txt = f"${equity[-1]:,.0f} | PF {pf_val:.2f} | DD {max_dd:.1f}%\n{n}t | WR {wr_val:.0f}% | UW {uw_pct:.0f}%"
    ax.annotate(stats_txt, xy=(0.02, 0.97), xycoords='axes fraction', fontsize=7.5,
                va='top', fontfamily='monospace',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.9))

plt.tight_layout(rect=[0, 0, 1, 0.96])
out1 = os.path.join(BASE, 'runs/critical_equity_curves_session20.png')
plt.savefig(out1, dpi=140, bbox_inches='tight')
print(f"Saved: {out1}")

# ========== FIGURE 2: YEARLY PF + MONTHLY HEATMAP ==========
fig2, (ax_ypf, ax_heat) = plt.subplots(2, 1, figsize=(20, 12),
                                        gridspec_kw={'height_ratios': [1, 1]})
fig2.suptitle('YEARLY PROFIT FACTOR + MONTHLY P&L HEATMAP\nBars below red = losing year | Red cells = losing month',
              fontsize=13, fontweight='bold', y=0.99)

# Yearly PF
yearly_pf_data = {}
for name, _, _ in reports:
    deals = all_ea_data[name]
    yearly = defaultdict(list)
    for dt, pnl in deals:
        yearly[dt.year].append(pnl)
    ypf = {}
    for y, ps in yearly.items():
        g = sum(p for p in ps if p > 0)
        l = abs(sum(p for p in ps if p < 0))
        ypf[y] = min(g / max(l, 0.01), 5.0)  # cap at 5 for display
    yearly_pf_data[name] = ypf

all_years = sorted(set(y for ypf in yearly_pf_data.values() for y in ypf.keys()))
x_pos = np.arange(len(all_years))
bar_w = 0.13

for i, (name, _, color) in enumerate(reports):
    pfs = [yearly_pf_data[name].get(y, 0) for y in all_years]
    ax_ypf.bar(x_pos + i * bar_w, pfs, bar_w, label=name, color=color, alpha=0.8)

ax_ypf.axhline(y=1.0, color='red', linewidth=2, linestyle='-', label='Breakeven')
ax_ypf.axhline(y=1.3, color='orange', linewidth=1, linestyle='--', alpha=0.6)
ax_ypf.set_xticks(x_pos + bar_w * 2.5)
ax_ypf.set_xticklabels(all_years, fontsize=10)
ax_ypf.set_ylabel('Profit Factor (capped 5)', fontsize=10)
ax_ypf.set_title('Yearly PF by EA', fontsize=11, fontweight='bold')
ax_ypf.legend(fontsize=7, ncol=6, loc='upper right')
ax_ypf.grid(True, alpha=0.2, axis='y')
ax_ypf.set_ylim(0, 5.5)

# Monthly heatmap
monthly_data = {}
for name, _, _ in reports:
    monthly = defaultdict(float)
    for dt, pnl in all_ea_data[name]:
        monthly[dt.strftime('%Y-%m')] += pnl
    monthly_data[name] = monthly

all_months = sorted(set(m for md in monthly_data.values() for m in md.keys()))
ea_names = [r[0] for r in reports]

matrix = np.zeros((len(ea_names), len(all_months)))
for i, name in enumerate(ea_names):
    for j, m in enumerate(all_months):
        matrix[i, j] = monthly_data[name].get(m, 0)

year_ticks = [j for j, m in enumerate(all_months) if m.endswith('-01')]
year_labels = [m[:4] for m in all_months if m.endswith('-01')]

vmax = max(abs(matrix.min()), matrix.max()) * 0.4
im = ax_heat.imshow(matrix, aspect='auto', cmap='RdYlGn', vmin=-vmax, vmax=vmax)
ax_heat.set_yticks(range(len(ea_names)))
ax_heat.set_yticklabels(ea_names, fontsize=9)
ax_heat.set_xticks(year_ticks)
ax_heat.set_xticklabels(year_labels, fontsize=9)
ax_heat.set_title('Monthly P&L Heatmap', fontsize=11, fontweight='bold')
plt.colorbar(im, ax=ax_heat, label='Monthly P&L ($)', shrink=0.5, pad=0.02)

plt.tight_layout(rect=[0, 0, 1, 0.96])
out2 = os.path.join(BASE, 'runs/critical_yearly_monthly_session20.png')
plt.savefig(out2, dpi=140, bbox_inches='tight')
print(f"Saved: {out2}")

# ========== FIGURE 3: DRAWDOWN OVERLAY + SUMMARY TABLE ==========
fig3, (ax_dd, ax_tbl) = plt.subplots(2, 1, figsize=(20, 12),
                                      gridspec_kw={'height_ratios': [1.5, 1]})
fig3.suptitle('DRAWDOWN COMPARISON + HONEST RISK ASSESSMENT',
              fontsize=14, fontweight='bold', y=0.99)

# DD overlay
for name, _, color in reports:
    deals = all_ea_data[name]
    pnls = [d[1] for d in deals]
    equity = [10000.0]
    for p in pnls:
        equity.append(equity[-1] + p)
    pk = np.maximum.accumulate(equity)
    dd = (np.array(equity) - pk) / pk * 100
    x = np.linspace(0, 100, len(dd))
    ax_dd.plot(x, dd, linewidth=1.2, color=color, label=name, alpha=0.85)

ax_dd.axhline(y=0, color='black', linewidth=0.5)
ax_dd.axhline(y=-5, color='orange', linestyle='--', linewidth=0.8, alpha=0.5, label='-5% (caution)')
ax_dd.axhline(y=-10, color='red', linestyle='--', linewidth=0.8, alpha=0.5, label='-10% (danger)')
ax_dd.fill_between([0, 100], 0, -5, alpha=0.03, color='green')
ax_dd.fill_between([0, 100], -5, -10, alpha=0.05, color='orange')
ax_dd.fill_between([0, 100], -10, -20, alpha=0.05, color='red')
ax_dd.set_ylabel('Drawdown %', fontsize=10)
ax_dd.set_xlabel('Trade Progress (%)', fontsize=10)
ax_dd.set_title('Drawdown Overlay (normalized)', fontsize=11, fontweight='bold')
ax_dd.legend(fontsize=8, ncol=4, loc='lower left')
ax_dd.grid(True, alpha=0.2)
ax_dd.set_ylim(-20, 2)

# Summary table
ax_tbl.axis('off')
header = ['EA', 'Trades', 'PF', 'Max DD', 'UW %', 'Red Yrs', 'OOS PF', 'Consec Loss', 'RISK FLAGS']
rows = []
for name, _, _ in reports:
    deals = all_ea_data[name]
    pnls = [d[1] for d in deals]
    n = len(pnls)
    wins_sum = sum(p for p in pnls if p > 0)
    loss_sum = abs(sum(p for p in pnls if p < 0))
    pf = wins_sum / max(loss_sum, 0.01)

    equity = [10000.0]
    for p in pnls:
        equity.append(equity[-1] + p)
    pk = np.maximum.accumulate(equity)
    dd_arr = (np.array(equity) - pk) / pk * 100
    max_dd = float(min(dd_arr))
    uw = sum(1 for d in dd_arr if d < -0.5) / len(dd_arr) * 100

    yearly = defaultdict(list)
    for dt, pnl in deals:
        yearly[dt.year].append(pnl)
    red_yrs = sum(1 for y, ps in yearly.items() if sum(ps) < 0)

    oos_n = max(n // 5, 5)
    oos = pnls[-oos_n:]
    oos_w = sum(p for p in oos if p > 0)
    oos_l = abs(sum(p for p in oos if p < 0))
    oos_pf = oos_w / max(oos_l, 0.01)

    cl = 0
    mcl = 0
    for p in pnls:
        if p < 0:
            cl += 1
            mcl = max(mcl, cl)
        else:
            cl = 0

    flags = []
    if pf < 1.3: flags.append('THIN-EDGE')
    if uw > 70: flags.append('UNDERWATER')
    if n < 100: flags.append('LOW-N')
    if red_yrs >= 2: flags.append('UNSTABLE')
    if oos_pf < 1.0: flags.append('OOS-FAIL')
    if mcl >= 8: flags.append(f'STREAK-{mcl}')

    rows.append([name, str(n), f'{pf:.2f}', f'{max_dd:.1f}%', f'{uw:.0f}%',
                 f'{red_yrs}/{len(yearly)}', f'{oos_pf:.2f}', str(mcl),
                 ', '.join(flags) if flags else 'CLEAN'])

table_data = [header] + rows
table = ax_tbl.table(cellText=table_data, loc='center', cellLoc='center',
                     colWidths=[0.11, 0.06, 0.05, 0.07, 0.05, 0.07, 0.06, 0.08, 0.24])
table.auto_set_font_size(False)
table.set_fontsize(9)
for j in range(len(header)):
    table[0, j].set_facecolor('#1565C0')
    table[0, j].set_text_props(color='white', fontweight='bold')
for i in range(1, len(rows) + 1):
    flag = rows[i - 1][-1]
    if 'OOS-FAIL' in flag or ('UNDERWATER' in flag and 'THIN' in flag):
        for j in range(len(header)):
            table[i, j].set_facecolor('#FFCDD2')
    elif 'THIN' in flag or 'LOW-N' in flag or 'UNDERWATER' in flag:
        for j in range(len(header)):
            table[i, j].set_facecolor('#FFF3E0')
    else:
        for j in range(len(header)):
            table[i, j].set_facecolor('#E8F5E9')
table.scale(1, 2.0)

plt.tight_layout(rect=[0, 0, 1, 0.96])
out3 = os.path.join(BASE, 'runs/critical_dd_summary_session20.png')
plt.savefig(out3, dpi=140, bbox_inches='tight')
print(f"Saved: {out3}")
print("\nDone. 3 critical charts generated.")
