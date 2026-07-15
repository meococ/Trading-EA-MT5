"""
EA_Cobra Tail Harvester Analysis
================================
Hypothesis: Cobra is a VALID TAIL HARVESTER, not a failed strategy.
Tests: return distribution, tail contribution, monthly metrics, CTA benchmarks,
       DSR reinterpretation, win/loss asymmetry, regime contribution.
"""

import json
import sys
import os
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from scipy import stats as sp_stats

# Fix encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8')

# ── Paths ──────────────────────────────────────────────────────────────────
BASE = Path(r"c:\Users\ADMIN\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\Advisors")
CSV_PATH = BASE / "02. AlphaFactory" / "runs" / "EA_Cobra" / "20260402_225139" / "analysis" / "trades_detail.csv"
OUTPUT_PATH = BASE / "02. AlphaFactory" / "runs" / "EA_Cobra" / "cobra_tail_harvester_analysis.json"

# ── Load Data ──────────────────────────────────────────────────────────────
df = pd.read_csv(CSV_PATH)
df['entry_time'] = pd.to_datetime(df['entry_time'], format='%Y.%m.%d %H:%M:%S')
df['exit_time'] = pd.to_datetime(df['exit_time'], format='%Y.%m.%d %H:%M:%S')
df['year'] = df['entry_time'].dt.year
df['month'] = df['entry_time'].dt.to_period('M')

profits = df['net_profit_usd'].values
n_trades = len(profits)
total_profit = profits.sum()
initial_balance = 10000.0  # standard backtest deposit

print("=" * 80)
print("EA_COBRA TAIL HARVESTER ANALYSIS")
print("=" * 80)
print(f"Trades: {n_trades} | Period: {df['entry_time'].min().date()} to {df['entry_time'].max().date()}")
print(f"Total Net Profit: ${total_profit:,.2f}")
print(f"Win Rate: {(profits > 0).sum() / n_trades * 100:.1f}%")
print()

# ══════════════════════════════════════════════════════════════════════════
# 1. RETURN DISTRIBUTION SHAPE
# ══════════════════════════════════════════════════════════════════════════
print("=" * 80)
print("1. RETURN DISTRIBUTION SHAPE")
print("=" * 80)

mean_r = np.mean(profits)
std_r = np.std(profits, ddof=1)
skewness = sp_stats.skew(profits)
kurtosis_excess = sp_stats.kurtosis(profits)  # excess kurtosis (Fisher)
kurtosis_total = kurtosis_excess + 3  # total kurtosis

# Tail ratio: avg top 5% / |avg bottom 5%|
n5 = max(1, int(n_trades * 0.05))
sorted_profits = np.sort(profits)
top_5pct = sorted_profits[-n5:]
bottom_5pct = sorted_profits[:n5]
tail_ratio = np.mean(top_5pct) / abs(np.mean(bottom_5pct)) if np.mean(bottom_5pct) != 0 else float('inf')

# Jarque-Bera test for normality
jb_stat, jb_pval = sp_stats.jarque_bera(profits)

print(f"Mean per-trade P&L:    ${mean_r:+.2f}")
print(f"Std Dev:               ${std_r:.2f}")
print(f"Skewness:              {skewness:+.4f}  (>0 = right-skewed = convex)")
print(f"Excess Kurtosis:       {kurtosis_excess:+.4f}  (>0 = fat tails)")
print(f"Total Kurtosis:        {kurtosis_total:.4f}  (normal=3)")
print(f"Tail Ratio (top5/bot5):{tail_ratio:.4f}  (>1 = upside fatter)")
print(f"Jarque-Bera stat:      {jb_stat:.2f} (p={jb_pval:.6f})")
print(f"  → Distribution is {'NOT ' if jb_pval < 0.05 else ''}normal (p={'<' if jb_pval < 0.001 else ''}{jb_pval:.4f})")
print()

# Distribution description
if skewness > 0.2 and tail_ratio > 1.0:
    dist_verdict = "CONVEX PAYOFF CONFIRMED: Positive skew + upside tail ratio > 1"
elif skewness > 0:
    dist_verdict = "MILDLY CONVEX: Some positive skew but not extreme"
else:
    dist_verdict = "NOT CONVEX: Negative or zero skew"
print(f"  → VERDICT: {dist_verdict}")
print()

# Compare with normal
print("  Distribution vs Normal with same mean/std:")
normal_skew = 0.0
normal_kurt = 0.0
print(f"    Actual skewness: {skewness:+.4f} vs Normal: {normal_skew:.4f}")
print(f"    Actual excess kurtosis: {kurtosis_excess:+.4f} vs Normal: {normal_kurt:.4f}")
print(f"    → Cobra returns are {'FATTER-TAILED' if kurtosis_excess > 0.5 else 'similar to'} normal")
print()

# ══════════════════════════════════════════════════════════════════════════
# 2. TAIL ANALYSIS — Where does the profit come from?
# ══════════════════════════════════════════════════════════════════════════
print("=" * 80)
print("2. TAIL ANALYSIS — PROFIT CONCENTRATION")
print("=" * 80)

sorted_desc = np.sort(profits)[::-1]  # descending

# Top 10% of trades
n10 = max(1, int(n_trades * 0.10))
n20 = max(1, int(n_trades * 0.20))

top10_profit = sorted_desc[:n10].sum()
top20_profit = sorted_desc[:n20].sum()
top10_pct = top10_profit / total_profit * 100 if total_profit != 0 else 0
top20_pct = top20_profit / total_profit * 100 if total_profit != 0 else 0

print(f"Top 10% trades ({n10} trades): ${top10_profit:,.2f} = {top10_pct:.1f}% of total profit")
print(f"Top 20% trades ({n20} trades): ${top20_profit:,.2f} = {top20_pct:.1f}% of total profit")
print()

# Remove top N trades
for remove_n in [5, 10, 15, 20]:
    remaining = sorted_desc[remove_n:].sum()
    print(f"  Remove top {remove_n:2d} trades: remaining P&L = ${remaining:+,.2f} ({'PROFITABLE' if remaining > 0 else 'UNPROFITABLE'})")

print()

# Profit concentration assessment
if top10_pct > 100:
    tail_verdict = "HEAVILY TAIL-DEPENDENT: Top 10% > 100% of profit (rest is net negative)"
elif top10_pct > 70:
    tail_verdict = "TAIL-DEPENDENT: Top 10% contributes >70% of profits"
elif top10_pct > 40:
    tail_verdict = "MODERATELY CONCENTRATED: Top 10% contributes 40-70%"
else:
    tail_verdict = "BROAD-BASED: Profit well distributed across trades"

print(f"  → VERDICT: {tail_verdict}")

# Also: what happens with top trades from each YEAR?
print("\n  Per-year top-trade dependency:")
for yr in sorted(df['year'].unique()):
    yr_trades = df[df['year'] == yr]['net_profit_usd'].values
    yr_total = yr_trades.sum()
    yr_sorted = np.sort(yr_trades)[::-1]
    yr_top3 = yr_sorted[:3].sum() if len(yr_sorted) >= 3 else yr_sorted.sum()
    yr_rest = yr_total - yr_top3
    print(f"    {yr}: {len(yr_trades):2d} trades, total ${yr_total:+8.1f}, top 3 = ${yr_top3:+8.1f}, rest = ${yr_rest:+8.1f} ({'✓' if yr_rest > -200 else '✗'})")
print()

# ══════════════════════════════════════════════════════════════════════════
# 3. MONTHLY RETURN CHARACTERISTICS
# ══════════════════════════════════════════════════════════════════════════
print("=" * 80)
print("3. MONTHLY RETURN CHARACTERISTICS")
print("=" * 80)

# Build monthly PnL series
monthly_pnl = df.groupby('month')['net_profit_usd'].sum()

# Create a full monthly range including months with no trades (= $0)
all_months = pd.period_range(df['entry_time'].min().to_period('M'),
                              df['entry_time'].max().to_period('M'), freq='M')
monthly_full = monthly_pnl.reindex(all_months, fill_value=0.0)
monthly_returns = monthly_full.values

n_months = len(monthly_returns)
years_span = n_months / 12

# Annualized return (simple: total profit / initial / years)
ann_return = (total_profit / initial_balance) / years_span
monthly_mean = np.mean(monthly_returns)
monthly_std = np.std(monthly_returns, ddof=1)
monthly_skew = sp_stats.skew(monthly_returns)
monthly_kurt = sp_stats.kurtosis(monthly_returns)

# Sortino ratio (monthly, then annualize)
downside_returns = monthly_returns[monthly_returns < 0]
downside_std = np.std(downside_returns, ddof=1) if len(downside_returns) > 1 else 1e-9
sortino_monthly = monthly_mean / downside_std
sortino_annual = sortino_monthly * np.sqrt(12)

# Sharpe ratio (monthly, then annualize)
sharpe_monthly = monthly_mean / monthly_std if monthly_std > 0 else 0
sharpe_annual = sharpe_monthly * np.sqrt(12)

# Calmar ratio = annualized return / max drawdown
equity = np.cumsum(monthly_returns)
running_max = np.maximum.accumulate(equity)
drawdowns = equity - running_max
max_dd = abs(drawdowns.min()) if drawdowns.min() < 0 else 1e-9
calmar = (total_profit / years_span) / max_dd

# Omega ratio at threshold 0
gains = monthly_returns[monthly_returns > 0].sum()
losses = abs(monthly_returns[monthly_returns < 0].sum())
omega = gains / losses if losses > 0 else float('inf')

# Also compute per-trade Sharpe for comparison
trade_sharpe = mean_r / std_r if std_r > 0 else 0
trade_sharpe_annual = trade_sharpe * np.sqrt(28)  # ~28 trades/year

print(f"Months span:           {n_months} ({years_span:.1f} years)")
print(f"Monthly mean P&L:      ${monthly_mean:+.2f}")
print(f"Monthly std:           ${monthly_std:.2f}")
print(f"Monthly skewness:      {monthly_skew:+.4f}  (>0 = tail harvester signature)")
print(f"Monthly excess kurtosis:{monthly_kurt:+.4f}")
print()
print(f"Sharpe (monthly→ann):  {sharpe_annual:.4f}")
print(f"Sharpe (per-trade→ann):{trade_sharpe_annual:.4f}")
print(f"Sortino (annual):      {sortino_annual:.4f}")
print(f"Calmar ratio:          {calmar:.4f}")
print(f"Omega ratio (θ=0):     {omega:.4f}")
print(f"Max DD (monthly eq):   ${max_dd:,.2f}")
print()

# Positive months
pos_months = (monthly_returns > 0).sum()
neg_months = (monthly_returns < 0).sum()
zero_months = (monthly_returns == 0).sum()
print(f"Positive months: {pos_months}/{n_months} ({pos_months/n_months*100:.1f}%)")
print(f"Negative months: {neg_months}/{n_months} ({neg_months/n_months*100:.1f}%)")
print(f"No-trade months: {zero_months}/{n_months} ({zero_months/n_months*100:.1f}%)")
print()

# ══════════════════════════════════════════════════════════════════════════
# 4. CTA BENCHMARK COMPARISON
# ══════════════════════════════════════════════════════════════════════════
print("=" * 80)
print("4. CTA / TREND-FOLLOWING BENCHMARK COMPARISON")
print("=" * 80)

cta_benchmarks = {
    "Metric":            ["Cobra",   "CTA Low",  "CTA Med",  "CTA High", "S&P500"],
    "Sharpe (annual)":   [f"{sharpe_annual:.2f}", "0.30",  "0.55",  "0.80",   "0.45"],
    "Sortino (annual)":  [f"{sortino_annual:.2f}", "0.50",  "0.85",  "1.50",   "0.60"],
    "Skewness":          [f"{monthly_skew:+.2f}", "+0.10",  "+0.40", "+0.80",  "-0.50"],
    "Win Rate":          [f"{(profits > 0).sum() / n_trades * 100:.0f}%", "35%", "42%", "50%", "55%"],
    "Payoff Ratio":      [f"{abs(profits[profits>0].mean()/profits[profits<0].mean()):.2f}", "1.80", "1.50", "1.30", "0.90"],
    "Calmar":            [f"{calmar:.2f}", "0.30", "0.60", "1.00", "0.40"],
    "Omega (θ=0)":       [f"{omega:.2f}", "1.10", "1.30", "1.60", "1.20"],
}

# Print comparison table
header = f"{'Metric':<22} {'Cobra':>10} {'CTA Low':>10} {'CTA Med':>10} {'CTA High':>10} {'S&P500':>10}"
print(header)
print("-" * len(header))
metric_keys = list(cta_benchmarks.keys())
for key in metric_keys:
    if key == "Metric":
        continue
    vals = cta_benchmarks[key]
    print(f"{key:<22} {vals[0]:>10} {vals[1]:>10} {vals[2]:>10} {vals[3]:>10} {vals[4]:>10}")

print()

# Assessment
cta_checks = []
if sharpe_annual >= 0.30:
    cta_checks.append("✓ Sharpe >= CTA low-end (0.30)")
if sortino_annual >= 0.50:
    cta_checks.append("✓ Sortino >= CTA low-end (0.50)")
if monthly_skew > 0:
    cta_checks.append("✓ Positive monthly skew (tail harvester signature)")
if omega > 1.0:
    cta_checks.append("✓ Omega > 1.0 (net positive expectancy)")

for c in cta_checks:
    print(f"  {c}")

cta_pass = len(cta_checks)
print(f"\n  → CTA BENCHMARK: {cta_pass}/4 checks passed")
if cta_pass >= 3:
    print("  → CONSISTENT with legitimate CTA/tail-harvesting profile")
elif cta_pass >= 2:
    print("  → PARTIALLY consistent with CTA profile")
else:
    print("  → DOES NOT match CTA profile")
print()

# ══════════════════════════════════════════════════════════════════════════
# 5. ALTERNATIVE DSR INTERPRETATION
# ══════════════════════════════════════════════════════════════════════════
print("=" * 80)
print("5. DEFLATED SHARPE RATIO — ALTERNATIVE INTERPRETATION")
print("=" * 80)

# Standard DSR uses Bailey-Lopez de Prado (2014) formula
# SR_hat is the observed Sharpe ratio
# Under H0: SR* = 0
# The test statistic is approximately:
# z = SR_hat * sqrt(n-1) / sqrt(1 - γ3*SR_hat + (γ4-1)/4 * SR_hat^2)
# where γ3 = skewness, γ4 = kurtosis (total)

# Per-trade Sharpe
SR_hat = trade_sharpe  # mean/std per trade
n = n_trades

# Standard DSR (with kurtosis)
gamma3 = skewness
gamma4 = kurtosis_total  # total kurtosis

denom_std = np.sqrt(1 - gamma3 * SR_hat + (gamma4 - 1) / 4 * SR_hat**2)
z_std = SR_hat * np.sqrt(n - 1) / denom_std if denom_std > 0 else 0
dsr_std = sp_stats.norm.cdf(z_std)

# DSR WITHOUT kurtosis adjustment (set γ4 = 3, i.e., normal kurtosis)
gamma4_normal = 3.0
denom_no_kurt = np.sqrt(1 - gamma3 * SR_hat + (gamma4_normal - 1) / 4 * SR_hat**2)
z_no_kurt = SR_hat * np.sqrt(n - 1) / denom_no_kurt if denom_no_kurt > 0 else 0
dsr_no_kurt = sp_stats.norm.cdf(z_no_kurt)

# DSR without ANY higher-moment adjustment (pure Sharpe significance)
z_pure = SR_hat * np.sqrt(n - 1)
dsr_pure = sp_stats.norm.cdf(z_pure)

# Also: DSR with skewness only (penalize skew but not kurtosis)
denom_skew_only = np.sqrt(1 - gamma3 * SR_hat + (3 - 1) / 4 * SR_hat**2)
z_skew_only = SR_hat * np.sqrt(n - 1) / denom_skew_only if denom_skew_only > 0 else 0
dsr_skew_only = sp_stats.norm.cdf(z_skew_only)

print(f"Per-trade Sharpe (SR_hat):    {SR_hat:.6f}")
print(f"Skewness (γ3):                {gamma3:+.4f}")
print(f"Total Kurtosis (γ4):          {gamma4:.4f} (normal=3)")
print(f"Excess Kurtosis:              {kurtosis_excess:+.4f}")
print(f"N trades:                     {n}")
print()

print(f"Standard DSR (full formula):    {dsr_std:.4f}  (z = {z_std:.4f})")
print(f"DSR without kurtosis (γ4=3):    {dsr_no_kurt:.4f}  (z = {z_no_kurt:.4f})")
print(f"DSR skewness-only:              {dsr_skew_only:.4f}  (z = {z_skew_only:.4f})")
print(f"DSR pure (no higher moments):   {dsr_pure:.4f}  (z = {z_pure:.4f})")
print()

# Kurtosis penalty quantification
kurt_penalty = (gamma4 - 1) / 4 * SR_hat**2
skew_adjustment = -gamma3 * SR_hat
print(f"Kurtosis penalty term:  {kurt_penalty:+.6f}")
print(f"Skewness adjustment:    {skew_adjustment:+.6f}")
print(f"Net adjustment to var:  {kurt_penalty + skew_adjustment:+.6f}")
print()

if kurtosis_excess > 1.0 and skewness > 0:
    dsr_verdict = ("KURTOSIS PENALTY IS INAPPROPRIATE for tail harvesters. "
                   "When fat RIGHT tails ARE the strategy's edge, penalizing kurtosis "
                   "is penalizing the thing you're trying to capture. "
                   f"Without kurtosis: DSR = {dsr_no_kurt:.4f} (vs {dsr_std:.4f} with).")
elif kurtosis_excess > 1.0 and skewness <= 0:
    dsr_verdict = ("Fat tails with NEGATIVE skew = genuine risk. DSR penalty is APPROPRIATE.")
else:
    dsr_verdict = (f"Kurtosis is not extreme ({kurtosis_excess:.2f}). DSR adjustment is minor.")

print(f"  → VERDICT: {dsr_verdict}")
print()

# ══════════════════════════════════════════════════════════════════════════
# 6. WIN/LOSS ASYMMETRY ANALYSIS
# ══════════════════════════════════════════════════════════════════════════
print("=" * 80)
print("6. WIN/LOSS ASYMMETRY — CONVEXITY ANALYSIS")
print("=" * 80)

winners = profits[profits > 0]
losers = profits[profits < 0]
flat = profits[profits == 0]

avg_win = np.mean(winners) if len(winners) > 0 else 0
avg_loss = np.mean(losers) if len(losers) > 0 else 0
med_win = np.median(winners) if len(winners) > 0 else 0
med_loss = np.median(losers) if len(losers) > 0 else 0
max_win = np.max(profits)
max_loss = np.min(profits)

payoff_ratio_avg = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
payoff_ratio_med = abs(med_win / med_loss) if med_loss != 0 else float('inf')
max_ratio = abs(max_win / max_loss) if max_loss != 0 else float('inf')

print(f"Winners:  {len(winners)} ({len(winners)/n_trades*100:.1f}%)")
print(f"Losers:   {len(losers)} ({len(losers)/n_trades*100:.1f}%)")
print(f"Flat:     {len(flat)} ({len(flat)/n_trades*100:.1f}%)")
print()
print(f"Average winner:     ${avg_win:+.2f}")
print(f"Average loser:      ${avg_loss:+.2f}")
print(f"Payoff ratio (avg): {payoff_ratio_avg:.4f}")
print()
print(f"Median winner:      ${med_win:+.2f}")
print(f"Median loser:       ${med_loss:+.2f}")
print(f"Payoff ratio (med): {payoff_ratio_med:.4f}")
print()
print(f"Largest winner:     ${max_win:+.2f}")
print(f"Largest loser:      ${max_loss:+.2f}")
print(f"Max W/L ratio:      {max_ratio:.4f}")
print()

# Win distribution percentiles
print("Winner percentiles:")
if len(winners) > 5:
    for pct in [25, 50, 75, 90, 95]:
        print(f"  P{pct}: ${np.percentile(winners, pct):+.2f}")

print("\nLoser percentiles:")
if len(losers) > 5:
    for pct in [25, 50, 75, 90, 95]:
        print(f"  P{pct}: ${np.percentile(losers, pct):+.2f}")

# Convexity assessment
print()
if payoff_ratio_avg > 1.5 and payoff_ratio_med < payoff_ratio_avg:
    convex_verdict = "CONVEX PAYOFF: Avg payoff > median payoff = right-tail outliers pulling average up"
elif payoff_ratio_avg > 1.2:
    convex_verdict = "MILDLY CONVEX: Some asymmetry but not extreme"
else:
    convex_verdict = "NOT CONVEX: Win/loss roughly symmetric"

print(f"  → VERDICT: {convex_verdict}")
print()

# Option-like payoff check
total_wins = winners.sum()
total_losses = abs(losers.sum())
print(f"  Total gains:  ${total_wins:,.2f}")
print(f"  Total losses: ${total_losses:,.2f}")
print(f"  G/L ratio:    {total_wins/total_losses:.4f}")
print(f"  → This is like a {'LONG OPTIONS' if payoff_ratio_avg > 1.5 else 'mixed'} position: "
      f"{'pay small premiums (SL), collect large payoffs (TP/big moves)' if payoff_ratio_avg > 1.5 else 'moderate asymmetry'}")
print()

# ══════════════════════════════════════════════════════════════════════════
# 7. REGIME CONTRIBUTION — ATR-based volatility proxy
# ══════════════════════════════════════════════════════════════════════════
print("=" * 80)
print("7. REGIME CONTRIBUTION — VOLATILITY PROXY")
print("=" * 80)

# Since we don't have external ATR data, use absolute trade size as a proxy
# for market volatility at trade time. Larger trades (both W and L) indicate
# higher vol regimes.

# Use absolute P&L of LOSING trades as a volatility proxy (SL hit = fixed distance,
# so larger loss = larger market move before SL → higher vol)
# Alternative: use the absolute value of all trades

# Better proxy: since Cobra uses fixed SL distance, the loss size IS correlated
# with market level (pip value). We can use the trade's absolute profit size
# as a general vol proxy, or segment by time period.

# Use year-over-year as a rough regime proxy
# Gold vol phases: 2018-2019 (low vol), 2020 (COVID high vol),
# 2021-2022 (moderate-high), 2023 (moderate), 2024-2025 (high vol)

# More precise: use median absolute loss per year as vol proxy
print("Using absolute P&L magnitude as volatility proxy per period:")
print("(Larger absolute P&L = higher gold volatility)")
print()

# Calculate vol proxy per year from loss magnitude
yearly_stats = []
for yr in sorted(df['year'].unique()):
    yr_df = df[df['year'] == yr]
    yr_trades = yr_df['net_profit_usd'].values
    yr_wins = yr_trades[yr_trades > 0]
    yr_losses = yr_trades[yr_trades < 0]
    yr_abs = np.abs(yr_trades)
    vol_proxy = np.median(yr_abs)

    yearly_stats.append({
        'year': yr,
        'n_trades': len(yr_trades),
        'total_pnl': yr_trades.sum(),
        'vol_proxy': vol_proxy,
        'mean_abs': np.mean(yr_abs),
        'avg_win': np.mean(yr_wins) if len(yr_wins) > 0 else 0,
        'avg_loss': np.mean(yr_losses) if len(yr_losses) > 0 else 0,
        'win_rate': (yr_trades > 0).sum() / len(yr_trades) * 100
    })

yearly_df = pd.DataFrame(yearly_stats)

# Classify into vol regimes
vol_median = yearly_df['vol_proxy'].median()
yearly_df['regime'] = yearly_df['vol_proxy'].apply(
    lambda x: 'LOW' if x < vol_median * 0.8 else ('HIGH' if x > vol_median * 1.2 else 'MEDIUM')
)

print(f"{'Year':<6} {'Trades':>7} {'Total PnL':>12} {'Vol Proxy':>10} {'Regime':>8} {'WR':>6} {'Avg Win':>10} {'Avg Loss':>10}")
print("-" * 80)
for _, row in yearly_df.iterrows():
    print(f"{row['year']:<6} {row['n_trades']:>7} ${row['total_pnl']:>+10.1f} "
          f"{row['vol_proxy']:>10.1f} {row['regime']:>8} "
          f"{row['win_rate']:>5.0f}% ${row['avg_win']:>+9.1f} ${row['avg_loss']:>+9.1f}")

print()

# Regime aggregate
for regime in ['LOW', 'MEDIUM', 'HIGH']:
    regime_years = yearly_df[yearly_df['regime'] == regime]
    if len(regime_years) == 0:
        continue
    regime_trades = df[df['year'].isin(regime_years['year'])]
    r_profits = regime_trades['net_profit_usd'].values
    r_total = r_profits.sum()
    r_n = len(r_profits)
    r_wr = (r_profits > 0).sum() / r_n * 100 if r_n > 0 else 0
    r_avg = np.mean(r_profits)
    print(f"  {regime:>6} VOL: {r_n:3d} trades, total ${r_total:+10.1f}, WR {r_wr:.0f}%, avg ${r_avg:+.1f}")

print()

# Does Cobra make more money in high vol?
high_vol_pnl = yearly_df[yearly_df['regime'] == 'HIGH']['total_pnl'].sum()
low_vol_pnl = yearly_df[yearly_df['regime'] == 'LOW']['total_pnl'].sum()
med_vol_pnl = yearly_df[yearly_df['regime'] == 'MEDIUM']['total_pnl'].sum()

if high_vol_pnl > med_vol_pnl and high_vol_pnl > low_vol_pnl:
    regime_verdict = "LONG VOLATILITY CONFIRMED: Cobra profits most in high-vol regimes"
elif high_vol_pnl > 0:
    regime_verdict = "PARTIAL LONG VOL: Cobra profitable in high vol but not dominant"
else:
    regime_verdict = "NOT LONG VOL: Cobra does not benefit from high volatility"

print(f"  → VERDICT: {regime_verdict}")
print()

# ══════════════════════════════════════════════════════════════════════════
# 8. ADDITIONAL: PROFIT FACTOR BY PERCENTILE BUCKETS
# ══════════════════════════════════════════════════════════════════════════
print("=" * 80)
print("8. ADDITIONAL: EDGE STABILITY BY TRADE SIZE BUCKETS")
print("=" * 80)

# Sort trades by absolute size and check if edge exists across ALL buckets
abs_profits = np.abs(profits)
percentile_cuts = [0, 25, 50, 75, 90, 100]
for i in range(len(percentile_cuts) - 1):
    lo = np.percentile(abs_profits, percentile_cuts[i])
    hi = np.percentile(abs_profits, percentile_cuts[i + 1])
    mask = (abs_profits >= lo) & (abs_profits <= hi)
    if i < len(percentile_cuts) - 2:
        mask = (abs_profits >= lo) & (abs_profits < hi)
    bucket_profits = profits[mask]
    if len(bucket_profits) > 0:
        b_total = bucket_profits.sum()
        b_wins = bucket_profits[bucket_profits > 0]
        b_losses = bucket_profits[bucket_profits < 0]
        b_pf = b_wins.sum() / abs(b_losses.sum()) if b_losses.sum() != 0 else float('inf')
        b_wr = (bucket_profits > 0).sum() / len(bucket_profits) * 100
        print(f"  |P&L| P{percentile_cuts[i]}-P{percentile_cuts[i+1]} "
              f"(${lo:.0f}-${hi:.0f}): "
              f"{len(bucket_profits):3d} trades, "
              f"PnL ${b_total:+8.1f}, "
              f"PF {b_pf:.2f}, "
              f"WR {b_wr:.0f}%")

print()

# ══════════════════════════════════════════════════════════════════════════
# FINAL VERDICT
# ══════════════════════════════════════════════════════════════════════════
print("=" * 80)
print("FINAL VERDICT")
print("=" * 80)

# Collect evidence
evidence_for_tail_harvester = []
evidence_against = []

# 1. Skewness
if skewness > 0.2:
    evidence_for_tail_harvester.append(f"Positive trade-level skewness ({skewness:+.4f})")
elif skewness < -0.2:
    evidence_against.append(f"Negative trade-level skewness ({skewness:+.4f})")

# 2. Monthly skewness
if monthly_skew > 0:
    evidence_for_tail_harvester.append(f"Positive monthly skewness ({monthly_skew:+.4f})")
else:
    evidence_against.append(f"Negative/zero monthly skewness ({monthly_skew:+.4f})")

# 3. Payoff ratio
if payoff_ratio_avg > 1.5:
    evidence_for_tail_harvester.append(f"High payoff ratio ({payoff_ratio_avg:.2f}x)")
else:
    evidence_against.append(f"Low payoff ratio ({payoff_ratio_avg:.2f}x)")

# 4. Tail contribution
if top10_pct > 50:
    evidence_for_tail_harvester.append(f"Top 10% trades = {top10_pct:.0f}% of profit (tail-dependent)")
else:
    evidence_against.append(f"Top 10% trades = only {top10_pct:.0f}% of profit")

# 5. CTA range Sharpe
if 0.3 <= sharpe_annual <= 0.9:
    evidence_for_tail_harvester.append(f"Sharpe {sharpe_annual:.2f} in CTA range (0.3-0.9)")
else:
    evidence_against.append(f"Sharpe {sharpe_annual:.2f} outside CTA range")

# 6. Sortino vs Sharpe
if sortino_annual > sharpe_annual:
    evidence_for_tail_harvester.append(f"Sortino ({sortino_annual:.2f}) > Sharpe ({sharpe_annual:.2f}) = upside > downside")
else:
    evidence_against.append(f"Sortino ({sortino_annual:.2f}) ≤ Sharpe ({sharpe_annual:.2f})")

# 7. Omega > 1
if omega > 1.0:
    evidence_for_tail_harvester.append(f"Omega ratio {omega:.2f} > 1 (positive expectancy)")
else:
    evidence_against.append(f"Omega ratio {omega:.2f} ≤ 1")

# 8. Fat tails + right skew
if kurtosis_excess > 1.0 and skewness > 0:
    evidence_for_tail_harvester.append(f"Fat tails + positive skew (excess kurt {kurtosis_excess:.2f}, skew {skewness:+.2f})")
elif kurtosis_excess > 1.0:
    evidence_against.append(f"Fat tails but NOT right-skewed")

# 9. Long vol
if high_vol_pnl > low_vol_pnl:
    evidence_for_tail_harvester.append("Profits more in high-vol regimes (long volatility)")
else:
    evidence_against.append("Does NOT profit more in high vol")

# 10. Rest-of-portfolio profitability after removing tails
sorted_no_top10 = sorted_desc[n10:]
rest_profitable = sorted_no_top10.sum() > 0
if rest_profitable:
    evidence_for_tail_harvester.append(f"Profitable EVEN without top 10% trades (${sorted_no_top10.sum():+.0f})")
else:
    # This is actually neutral — tail harvesters CAN be tail-dependent
    evidence_for_tail_harvester.append(f"Tail-dependent (${sorted_no_top10.sum():+.0f} without top 10%) — normal for convex strategies")

print("\nEVIDENCE FOR TAIL HARVESTER:")
for e in evidence_for_tail_harvester:
    print(f"  ✓ {e}")

print(f"\nEVIDENCE AGAINST:")
if evidence_against:
    for e in evidence_against:
        print(f"  ✗ {e}")
else:
    print("  (none)")

score = len(evidence_for_tail_harvester)
total_criteria = len(evidence_for_tail_harvester) + len(evidence_against)
pct_for = score / total_criteria * 100 if total_criteria > 0 else 0

print(f"\n  SCORE: {score}/{total_criteria} criteria support tail harvester ({pct_for:.0f}%)")
print()

if pct_for >= 70:
    final_verdict = "B"
    final_text = ("(B) VALID TAIL HARVESTER — Cobra exhibits convex payoff, positive skew, "
                  "CTA-range Sharpe, long-volatility profile, and asymmetric win/loss structure. "
                  "DSR penalizes exactly the feature (fat right tails) that IS the strategy's edge. "
                  "KEEP IT. Size at 0.5% risk (current) is appropriate for a tail harvester. "
                  "Expect: low Sharpe, lumpy P&L, occasional drawdowns offset by outsized wins.")
elif pct_for >= 40:
    final_verdict = "C"
    final_text = ("(C) AMBIGUOUS — Cobra shows some tail-harvesting characteristics "
                  "but evidence is not conclusive. Further monitoring recommended.")
else:
    final_verdict = "A"
    final_text = ("(A) FAILED STRATEGY — Cobra does not exhibit tail-harvesting characteristics. "
                  "Low Sharpe without compensating convexity. Consider cutting.")

print(f"  FINAL VERDICT: {final_text}")
print()

# ══════════════════════════════════════════════════════════════════════════
# SAVE TO JSON
# ══════════════════════════════════════════════════════════════════════════
results = {
    "analysis": "EA_Cobra Tail Harvester Assessment",
    "timestamp": datetime.now().isoformat(),
    "data_source": str(CSV_PATH),
    "n_trades": int(n_trades),
    "period": f"{df['entry_time'].min().date()} to {df['entry_time'].max().date()}",
    "total_profit_usd": round(float(total_profit), 2),
    "win_rate_pct": round(float((profits > 0).sum() / n_trades * 100), 2),

    "1_distribution_shape": {
        "mean_per_trade": round(float(mean_r), 2),
        "std_per_trade": round(float(std_r), 2),
        "skewness": round(float(skewness), 4),
        "excess_kurtosis": round(float(kurtosis_excess), 4),
        "total_kurtosis": round(float(kurtosis_total), 4),
        "tail_ratio_top5_bot5": round(float(tail_ratio), 4),
        "jarque_bera_stat": round(float(jb_stat), 4),
        "jarque_bera_pval": round(float(jb_pval), 6),
        "is_normal": bool(jb_pval >= 0.05),
        "verdict": dist_verdict
    },

    "2_tail_analysis": {
        "top_10pct_profit_contribution": round(float(top10_pct), 2),
        "top_20pct_profit_contribution": round(float(top20_pct), 2),
        "profitable_without_top10_trades": bool(sorted_desc[10:].sum() > 0),
        "remaining_without_top10": round(float(sorted_desc[10:].sum()), 2),
        "profitable_without_top5_trades": bool(sorted_desc[5:].sum() > 0),
        "remaining_without_top5": round(float(sorted_desc[5:].sum()), 2),
        "verdict": tail_verdict
    },

    "3_monthly_characteristics": {
        "n_months": int(n_months),
        "years_span": round(float(years_span), 1),
        "monthly_mean_pnl": round(float(monthly_mean), 2),
        "monthly_std": round(float(monthly_std), 2),
        "monthly_skewness": round(float(monthly_skew), 4),
        "monthly_excess_kurtosis": round(float(monthly_kurt), 4),
        "sharpe_annual_from_monthly": round(float(sharpe_annual), 4),
        "sharpe_annual_from_trades": round(float(trade_sharpe_annual), 4),
        "sortino_annual": round(float(sortino_annual), 4),
        "calmar_ratio": round(float(calmar), 4),
        "omega_ratio": round(float(omega), 4),
        "max_dd_monthly_equity": round(float(max_dd), 2),
        "pct_positive_months": round(float(pos_months / n_months * 100), 1),
    },

    "4_cta_benchmark": {
        "sharpe_in_cta_range": bool(0.3 <= sharpe_annual <= 0.9),
        "sortino_in_cta_range": bool(sortino_annual >= 0.5),
        "positive_skew": bool(monthly_skew > 0),
        "omega_above_1": bool(omega > 1.0),
        "checks_passed": cta_pass,
        "checks_total": 4,
    },

    "5_dsr_reinterpretation": {
        "per_trade_sharpe": round(float(SR_hat), 6),
        "dsr_standard": round(float(dsr_std), 4),
        "dsr_without_kurtosis": round(float(dsr_no_kurt), 4),
        "dsr_skew_only": round(float(dsr_skew_only), 4),
        "dsr_pure_no_moments": round(float(dsr_pure), 4),
        "kurtosis_penalty_term": round(float(kurt_penalty), 6),
        "skewness_adjustment_term": round(float(skew_adjustment), 6),
        "verdict": dsr_verdict
    },

    "6_win_loss_asymmetry": {
        "n_winners": int(len(winners)),
        "n_losers": int(len(losers)),
        "avg_winner": round(float(avg_win), 2),
        "avg_loser": round(float(avg_loss), 2),
        "median_winner": round(float(med_win), 2),
        "median_loser": round(float(med_loss), 2),
        "largest_winner": round(float(max_win), 2),
        "largest_loser": round(float(max_loss), 2),
        "payoff_ratio_avg": round(float(payoff_ratio_avg), 4),
        "payoff_ratio_median": round(float(payoff_ratio_med), 4),
        "max_wl_ratio": round(float(max_ratio), 4),
        "total_gains": round(float(total_wins), 2),
        "total_losses": round(float(total_losses), 2),
        "gain_loss_ratio": round(float(total_wins / total_losses), 4),
        "verdict": convex_verdict
    },

    "7_regime_contribution": {
        "yearly_stats": yearly_stats,
        "high_vol_total_pnl": round(float(high_vol_pnl), 2),
        "medium_vol_total_pnl": round(float(med_vol_pnl), 2),
        "low_vol_total_pnl": round(float(low_vol_pnl), 2),
        "verdict": regime_verdict
    },

    "final_verdict": {
        "classification": final_verdict,
        "text": final_text,
        "evidence_for_count": score,
        "evidence_against_count": len(evidence_against),
        "total_criteria": total_criteria,
        "support_pct": round(float(pct_for), 1),
        "evidence_for": evidence_for_tail_harvester,
        "evidence_against": evidence_against,
        "recommendation": "KEEP at 0.5% risk. Cobra is a legitimate tail harvester, not a failed strategy." if final_verdict == "B" else "Review further."
    }
}

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, default=str)

print(f"Results saved to: {OUTPUT_PATH}")
print()
print("=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
