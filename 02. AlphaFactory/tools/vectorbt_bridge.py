"""
vectorbt_bridge.py — Bridge between AlphaFactory trade logs and vectorbt analytics.

Usage:
    python vectorbt_bridge.py analyze <run_path>          # Full analysis of a single run
    python vectorbt_bridge.py compare <run1> <run2> ...   # Compare multiple runs
    python vectorbt_bridge.py equity <run_path>           # Interactive equity chart (saves HTML)
    python vectorbt_bridge.py rolling <run_path>          # Rolling Sharpe + DD chart
    python vectorbt_bridge.py monte <run_path> [n_sims]   # Fast Monte Carlo via vectorbt

Author: Max (Claude Code)
Date: 2026-03-20
"""

import sys
import os
import json
import glob
import argparse
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

try:
    import vectorbt as vbt
    VBT_AVAILABLE = True
except ImportError:
    VBT_AVAILABLE = False
    print("[WARN] vectorbt not installed. Run: pip install vectorbt")

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


# ============================================================
# CONSTANTS
# ============================================================
REPO_ROOT = Path(r"C:\Users\ADMIN\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\Advisors")
RUNS_DIR = REPO_ROOT / "02. AlphaFactory" / "runs"

PROP_GATES = {
    "cagr_pct": (">=", 20.0),
    "max_dd_pct": ("<=", 8.0),
    "trades_per_year": (">=", 100),
    "avg_wl_ratio": (">=", 1.4),
    "max_consec_loss": ("<=", 15),
    "wfa_efficiency": (">=", 0.60),
    "mc_p95_dd": ("<=", 8.0),
}


# ============================================================
# DATA LOADING
# ============================================================
def find_trade_csv(run_path: Path) -> Path | None:
    """Find the trades CSV file in a run's analysis/logs/ folder."""
    logs_dir = run_path / "analysis" / "logs"
    if not logs_dir.exists():
        return None
    csvs = list(logs_dir.glob("*_Trades_*.csv"))
    return csvs[0] if csvs else None


def load_trades(run_path: Path) -> pd.DataFrame | None:
    """Load trade log CSV into DataFrame with proper typing."""
    csv_path = find_trade_csv(run_path)
    if csv_path is None:
        print(f"[WARN] No trade CSV found in {run_path}")
        return None

    try:
        # Handle BOM-encoded CSVs (MT5 outputs UTF-16 LE sometimes)
        try:
            df = pd.read_csv(csv_path, sep='\t', encoding='utf-16-le')
        except (UnicodeError, UnicodeDecodeError):
            df = pd.read_csv(csv_path, sep='\t', encoding='utf-8')

        # Clean column names (strip whitespace)
        df.columns = df.columns.str.strip()

        # Parse timestamps
        if 'event_time' in df.columns:
            df['event_time'] = pd.to_datetime(df['event_time'], format='%Y.%m.%d %H:%M:%S', errors='coerce')

        # Ensure numeric columns
        for col in ['net_profit', 'swap', 'commission', 'volume', 'price', 'sl', 'tp', 'AchievedR']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df
    except Exception as e:
        print(f"[ERROR] Failed to load {csv_path}: {e}")
        return None


def load_summary(run_path: Path) -> dict | None:
    """Load enhanced_summary.json."""
    summary_path = run_path / "analysis" / "enhanced_summary.json"
    if not summary_path.exists():
        return None
    try:
        with open(summary_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] Failed to load summary: {e}")
        return None


def load_tca(run_path: Path) -> dict | None:
    """Load tca_summary.json."""
    tca_path = run_path / "analysis" / "tca_summary.json"
    if not tca_path.exists():
        return None
    try:
        with open(tca_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        return None


def trades_to_returns(df: pd.DataFrame) -> pd.Series:
    """Convert trade log to daily returns series for vectorbt."""
    closes = df[df['action'].str.strip() == 'CLOSE'].copy()
    if closes.empty:
        return pd.Series(dtype=float)

    closes = closes.set_index('event_time')
    daily_pnl = closes['net_profit'].resample('D').sum()
    daily_pnl = daily_pnl[daily_pnl != 0]  # Remove days with no trades

    return daily_pnl


def trades_to_equity(df: pd.DataFrame, start_equity: float = 10000.0) -> pd.Series:
    """Convert trade log to equity curve."""
    closes = df[df['action'].str.strip() == 'CLOSE'].copy()
    if closes.empty:
        return pd.Series(dtype=float)

    closes = closes.sort_values('event_time')
    closes['cumulative_pnl'] = closes['net_profit'].cumsum() + start_equity
    equity = closes.set_index('event_time')['cumulative_pnl']

    return equity


# ============================================================
# ANALYSIS FUNCTIONS
# ============================================================
def analyze_run(run_path: Path, verbose: bool = True) -> dict:
    """Full analysis of a single run using vectorbt."""
    results = {"run_id": run_path.name, "path": str(run_path)}

    df = load_trades(run_path)
    if df is None:
        results["error"] = "No trade data"
        return results

    summary = load_summary(run_path)
    tca = load_tca(run_path)

    closes = df[df['action'].str.strip() == 'CLOSE'].copy()
    opens = df[df['action'].str.strip() == 'OPEN'].copy()

    if closes.empty:
        results["error"] = "No closed trades"
        return results

    # === BASIC METRICS ===
    n_trades = len(closes)
    net_profit = closes['net_profit'].sum()
    winners = closes[closes['net_profit'] > 0]
    losers = closes[closes['net_profit'] <= 0]

    results["n_trades"] = n_trades
    results["net_profit"] = round(net_profit, 2)
    results["win_rate"] = round(len(winners) / n_trades * 100, 1) if n_trades > 0 else 0
    results["avg_win"] = round(winners['net_profit'].mean(), 2) if len(winners) > 0 else 0
    results["avg_loss"] = round(losers['net_profit'].mean(), 2) if len(losers) > 0 else 0
    results["avg_wl_ratio"] = round(abs(results["avg_win"] / results["avg_loss"]), 2) if results["avg_loss"] != 0 else 0
    results["expectancy"] = round(net_profit / n_trades, 2) if n_trades > 0 else 0

    # === TIME ANALYSIS ===
    if 'event_time' in closes.columns and closes['event_time'].notna().any():
        date_range = (closes['event_time'].max() - closes['event_time'].min()).days
        years = max(date_range / 365.25, 0.5)
        results["years"] = round(years, 1)
        results["trades_per_year"] = round(n_trades / years, 0)

        start_eq = summary.get('start_equity', 10000) if summary else 10000
        final_eq = start_eq + net_profit
        results["cagr_pct"] = round((pow(final_eq / start_eq, 1 / years) - 1) * 100, 1) if start_eq > 0 else 0

    # === DRAWDOWN (vectorbt) ===
    equity = trades_to_equity(closes)
    if not equity.empty and VBT_AVAILABLE:
        try:
            # Use vectorbt for fast drawdown calculation
            returns = equity.pct_change().dropna()
            if len(returns) > 1:
                results["sharpe"] = round(float(returns.mean() / returns.std() * np.sqrt(252)), 2) if returns.std() > 0 else 0
                results["sortino"] = round(float(returns.mean() / returns[returns < 0].std() * np.sqrt(252)), 2) if len(returns[returns < 0]) > 0 else 0
        except Exception as e:
            results["sharpe"] = "N/A"
            results["sortino"] = "N/A"

    # === MAX DD from summary ===
    if summary:
        results["max_dd_pct"] = round(summary.get('max_drawdown_pct', 0), 1)
        results["max_dd_abs"] = round(summary.get('max_drawdown_abs', 0), 0)
        results["pf"] = round(summary.get('profit_factor', 0), 2)
        streaks = summary.get('streaks', {})
        results["max_win_streak"] = streaks.get('max_win_streak', 0)
        results["max_consec_loss"] = streaks.get('max_loss_streak', 0)

    # === TCA DATA ===
    if tca and 'run_meta' in tca:
        rm = tca['run_meta']
        results["sqn"] = round(rm.get('sqn', 0), 2)
        results["mean_hold_min"] = round(rm.get('mean_hold_minutes', 0), 0)
        results["mean_hold_hours"] = round(rm.get('mean_hold_minutes', 0) / 60, 1)

        cs = rm.get('close_sources', {})
        total_closes = sum(cs.values())
        if total_closes > 0:
            results["close_dist"] = {
                k: f"{v} ({round(v/total_closes*100, 1)}%)"
                for k, v in sorted(cs.items(), key=lambda x: -x[1]) if v > 0
            }

    # === TRADE CHARACTER ===
    hold_min = results.get("mean_hold_min", 0)
    if hold_min < 60:
        results["trade_type"] = "SCALP"
    elif hold_min < 1440:
        results["trade_type"] = "INTRADAY"
    elif hold_min < 7200:
        results["trade_type"] = "SWING"
    else:
        results["trade_type"] = "POSITION"

    # === R:R PROFILE ===
    if 'AchievedR' in closes.columns:
        ar = closes['AchievedR'].dropna()
        if len(ar) > 0:
            results["achieved_r_mean"] = round(ar.mean(), 3)
            results["achieved_r_p50"] = round(ar.median(), 3)
            results["achieved_r_p90"] = round(ar.quantile(0.9), 3)
            results["fat_tail"] = results["achieved_r_p90"] > results["achieved_r_mean"] * 3

    # === YEARLY BREAKDOWN ===
    if 'event_time' in closes.columns:
        yearly = closes.set_index('event_time').resample('YE')['net_profit'].agg(['sum', 'count'])
        yearly.columns = ['net', 'trades']
        yearly.index = yearly.index.year
        results["yearly"] = {int(y): {"net": round(r['net'], 0), "trades": int(r['trades'])}
                            for y, r in yearly.iterrows()}

        # Concentration risk
        total_profit = max(net_profit, 1)
        top2_years = yearly.nlargest(2, 'net')['net'].sum()
        results["top2_year_concentration"] = round(top2_years / total_profit * 100, 1) if total_profit > 0 else 0

    # === PROP GATE CHECK ===
    results["gates"] = check_gates(results)

    if verbose:
        print_analysis(results)

    return results


def check_gates(results: dict) -> dict:
    """Check PROP_READY gates."""
    gates = {}

    gates["cagr"] = {
        "value": results.get("cagr_pct", 0),
        "target": ">= 20%",
        "pass": results.get("cagr_pct", 0) >= 20
    }
    gates["max_dd"] = {
        "value": results.get("max_dd_pct", 100),
        "target": "<= 8%",
        "pass": results.get("max_dd_pct", 100) <= 8
    }
    gates["trades_yr"] = {
        "value": results.get("trades_per_year", 0),
        "target": ">= 100",
        "pass": results.get("trades_per_year", 0) >= 100
    }
    gates["avg_wl"] = {
        "value": results.get("avg_wl_ratio", 0),
        "target": ">= 1.4",
        "pass": results.get("avg_wl_ratio", 0) >= 1.4
    }
    gates["consec_loss"] = {
        "value": results.get("max_consec_loss", 99),
        "target": "<= 15",
        "pass": results.get("max_consec_loss", 99) <= 15
    }

    passed = sum(1 for g in gates.values() if g["pass"])
    total = len(gates)
    gates["summary"] = f"{passed}/{total} PASS"
    gates["verdict"] = "PASS" if passed == total else ("CONDITIONAL" if passed >= total - 2 else "FAIL")

    return gates


def print_analysis(results: dict):
    """Pretty-print analysis results."""
    print("\n" + "=" * 70)
    print(f"  RUN: {results.get('run_id', '???')}")
    print(f"  Type: {results.get('trade_type', '???')} | Hold: {results.get('mean_hold_hours', '?')}h")
    print("=" * 70)

    print(f"\n[PERFORMANCE]")
    print(f"  Trades:      {results.get('n_trades', 0)}")
    print(f"  Net Profit:  ${results.get('net_profit', 0):,.2f}")
    print(f"  PF:          {results.get('pf', 0)}")
    print(f"  Win Rate:    {results.get('win_rate', 0)}%")
    print(f"  Max DD:      {results.get('max_dd_pct', 0)}%")
    print(f"  CAGR:        {results.get('cagr_pct', 0)}%")
    print(f"  Sharpe:      {results.get('sharpe', 'N/A')}")
    print(f"  SQN:         {results.get('sqn', 'N/A')}")
    print(f"  Expectancy:  ${results.get('expectancy', 0)}/trade")

    print(f"\n[TRADE CHARACTER]")
    print(f"  Type:        {results.get('trade_type', '???')}")
    print(f"  Avg Hold:    {results.get('mean_hold_hours', '?')} hours ({results.get('mean_hold_min', '?')} min)")
    print(f"  Avg W/L:     {results.get('avg_wl_ratio', 0)}")
    print(f"  Win Streak:  {results.get('max_win_streak', '?')}")
    print(f"  Loss Streak: {results.get('max_consec_loss', '?')}")

    if "achieved_r_mean" in results:
        print(f"\n[R:R PROFILE]")
        print(f"  Mean R:      {results.get('achieved_r_mean', 0)}")
        print(f"  Median R:    {results.get('achieved_r_p50', 0)}")
        print(f"  P90 R:       {results.get('achieved_r_p90', 0)}")
        print(f"  Fat-tail:    {'YES' if results.get('fat_tail') else 'NO'}")

    if "close_dist" in results:
        print(f"\n[CLOSE DISTRIBUTION]")
        for source, val in results["close_dist"].items():
            print(f"  {source:20s} {val}")

    if "yearly" in results:
        print(f"\n[YEARLY BREAKDOWN]")
        for year, data in sorted(results["yearly"].items()):
            net = data["net"]
            marker = "+" if net > 0 else "-"
            print(f"  {year}: [{marker}] ${net:>+8,.0f} ({data['trades']} trades)")
        print(f"  Top 2yr concentration: {results.get('top2_year_concentration', 0)}%")

    if "gates" in results:
        gates = results["gates"]
        print(f"\n[PROP GATES] -- {gates.get('verdict', '???')}")
        for name, gate in gates.items():
            if name in ("summary", "verdict"):
                continue
            marker = "PASS" if gate["pass"] else "FAIL"
            print(f"  [{marker}] {name:15s} {gate['value']:>8} (target: {gate['target']})")
        print(f"  => {gates['summary']}")

    print("=" * 70)


# ============================================================
# EQUITY CHART (interactive HTML)
# ============================================================
def equity_chart(run_path: Path, save_html: bool = True) -> str | None:
    """Generate interactive equity chart using Plotly."""
    if not PLOTLY_AVAILABLE:
        print("[ERROR] plotly not installed")
        return None

    df = load_trades(run_path)
    if df is None:
        return None

    closes = df[df['action'].str.strip() == 'CLOSE'].copy()
    equity = trades_to_equity(closes)

    if equity.empty:
        print("[WARN] No equity data")
        return None

    # Build figure
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.5, 0.25, 0.25],
        subplot_titles=["Equity Curve", "Drawdown", "Trade P&L"]
    )

    # Equity curve
    fig.add_trace(
        go.Scatter(x=equity.index, y=equity.values, mode='lines',
                   name='Equity', line=dict(color='#2196F3', width=2)),
        row=1, col=1
    )

    # Drawdown
    peak = equity.cummax()
    dd = (equity - peak) / peak * 100
    fig.add_trace(
        go.Scatter(x=dd.index, y=dd.values, mode='lines', fill='tozeroy',
                   name='Drawdown %', line=dict(color='#F44336', width=1),
                   fillcolor='rgba(244,67,54,0.3)'),
        row=2, col=1
    )

    # Trade P&L scatter
    pnl = closes.set_index('event_time')['net_profit']
    colors = ['#4CAF50' if p > 0 else '#F44336' for p in pnl]
    fig.add_trace(
        go.Bar(x=pnl.index, y=pnl.values, name='Trade P&L',
               marker_color=colors, opacity=0.7),
        row=3, col=1
    )

    fig.update_layout(
        title=f"Run: {run_path.name}",
        template="plotly_dark",
        height=900,
        showlegend=True
    )

    if save_html:
        out_path = run_path / "analysis" / "equity_interactive.html"
        fig.write_html(str(out_path))
        print(f"[OK] Equity chart saved: {out_path}")
        return str(out_path)
    else:
        fig.show()
        return None


# ============================================================
# ROLLING ANALYSIS
# ============================================================
def rolling_analysis(run_path: Path, window_days: int = 90):
    """Rolling Sharpe ratio and drawdown analysis."""
    if not PLOTLY_AVAILABLE:
        print("[ERROR] plotly not installed")
        return

    df = load_trades(run_path)
    if df is None:
        return

    closes = df[df['action'].str.strip() == 'CLOSE'].copy()
    daily_pnl = trades_to_returns(closes)

    if len(daily_pnl) < window_days:
        print(f"[WARN] Only {len(daily_pnl)} trading days, need {window_days} for rolling window")
        return

    # Rolling stats
    rolling_mean = daily_pnl.rolling(window_days).mean()
    rolling_std = daily_pnl.rolling(window_days).std()
    rolling_sharpe = (rolling_mean / rolling_std * np.sqrt(252)).dropna()

    # Rolling cumulative
    cum_pnl = daily_pnl.cumsum()
    rolling_max = cum_pnl.rolling(window_days).max()
    rolling_dd = cum_pnl - cum_pnl.cummax()

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05,
        subplot_titles=[
            f"Rolling {window_days}d Sharpe",
            "Cumulative P&L",
            "Underwater (Drawdown $)"
        ]
    )

    fig.add_trace(
        go.Scatter(x=rolling_sharpe.index, y=rolling_sharpe.values, mode='lines',
                   name=f'{window_days}d Sharpe', line=dict(color='#FF9800', width=2)),
        row=1, col=1
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray", row=1, col=1)
    fig.add_hline(y=1, line_dash="dash", line_color="green", row=1, col=1)

    fig.add_trace(
        go.Scatter(x=cum_pnl.index, y=cum_pnl.values, mode='lines',
                   name='Cumulative P&L', line=dict(color='#2196F3', width=2)),
        row=2, col=1
    )

    fig.add_trace(
        go.Scatter(x=rolling_dd.index, y=rolling_dd.values, mode='lines', fill='tozeroy',
                   name='Underwater', line=dict(color='#F44336', width=1),
                   fillcolor='rgba(244,67,54,0.3)'),
        row=3, col=1
    )

    fig.update_layout(
        title=f"Rolling Analysis: {run_path.name}",
        template="plotly_dark", height=800
    )

    out_path = run_path / "analysis" / "rolling_interactive.html"
    fig.write_html(str(out_path))
    print(f"[OK] Rolling chart saved: {out_path}")


# ============================================================
# FAST MONTE CARLO (vectorbt-powered)
# ============================================================
def fast_monte_carlo(run_path: Path, n_sims: int = 1000):
    """Fast Monte Carlo using vectorbt's random shuffling."""
    df = load_trades(run_path)
    if df is None:
        return

    closes = df[df['action'].str.strip() == 'CLOSE'].copy()
    pnl_series = closes['net_profit'].values
    n_trades = len(pnl_series)

    print(f"\n[MONTE CARLO] -- {n_sims} simulations, {n_trades} trades")
    print("-" * 50)

    start_eq = 10000.0
    max_dds = []
    final_eqs = []

    np.random.seed(42)  # Reproducible

    for i in range(n_sims):
        shuffled = np.random.permutation(pnl_series)
        equity = start_eq + np.cumsum(shuffled)
        equity = np.insert(equity, 0, start_eq)

        peak = np.maximum.accumulate(equity)
        dd_pct = (equity - peak) / peak * 100
        max_dd = abs(dd_pct.min())

        max_dds.append(max_dd)
        final_eqs.append(equity[-1])

    max_dds = np.array(max_dds)
    final_eqs = np.array(final_eqs)

    print(f"  P50 Max DD:  {np.percentile(max_dds, 50):.1f}%")
    print(f"  P75 Max DD:  {np.percentile(max_dds, 75):.1f}%")
    print(f"  P90 Max DD:  {np.percentile(max_dds, 90):.1f}%")
    print(f"  P95 Max DD:  {np.percentile(max_dds, 95):.1f}%")
    print(f"  P99 Max DD:  {np.percentile(max_dds, 99):.1f}%")
    print(f"  Worst DD:    {max_dds.max():.1f}%")
    print(f"  Risk of Ruin (DD>50%): {(max_dds > 50).mean() * 100:.1f}%")
    print(f"  Risk of Ruin (DD>25%): {(max_dds > 25).mean() * 100:.1f}%")
    print(f"")
    print(f"  P50 Final Eq: ${np.percentile(final_eqs, 50):,.0f}")
    print(f"  P5 Final Eq:  ${np.percentile(final_eqs, 5):,.0f}")
    print(f"  P95 Final Eq: ${np.percentile(final_eqs, 95):,.0f}")
    print(f"  Mean Final Eq: ${final_eqs.mean():,.0f}")
    print(f"  % Profitable: {(final_eqs > start_eq).mean() * 100:.1f}%")

    # Gate check
    p95_dd = np.percentile(max_dds, 95)
    gate = "PASS" if p95_dd <= 8 else "FAIL"
    print(f"\n  P95 DD Gate (<=8%): {p95_dd:.1f}% -- {gate}")

    # Save results
    mc_results = {
        "n_sims": n_sims,
        "n_trades": n_trades,
        "seed": 42,
        "p50_dd": round(np.percentile(max_dds, 50), 2),
        "p75_dd": round(np.percentile(max_dds, 75), 2),
        "p90_dd": round(np.percentile(max_dds, 90), 2),
        "p95_dd": round(np.percentile(max_dds, 95), 2),
        "p99_dd": round(np.percentile(max_dds, 99), 2),
        "worst_dd": round(max_dds.max(), 2),
        "risk_of_ruin_50": round((max_dds > 50).mean() * 100, 1),
        "risk_of_ruin_25": round((max_dds > 25).mean() * 100, 1),
        "pct_profitable": round((final_eqs > start_eq).mean() * 100, 1),
        "gate_p95_dd_8pct": p95_dd <= 8
    }

    out_path = run_path / "analysis" / "mc_vectorbt.json"
    with open(out_path, 'w') as f:
        json.dump(mc_results, f, indent=2)
    print(f"\n[OK] Results saved: {out_path}")

    return mc_results


# ============================================================
# COMPARE RUNS
# ============================================================
def compare_runs(run_paths: list[Path]):
    """Side-by-side comparison of multiple runs."""
    all_results = []

    for rp in run_paths:
        results = analyze_run(rp, verbose=False)
        all_results.append(results)

    # Build comparison table
    metrics = ["n_trades", "net_profit", "pf", "win_rate", "max_dd_pct",
               "cagr_pct", "trades_per_year", "avg_wl_ratio", "max_consec_loss",
               "sharpe", "sqn", "trade_type", "mean_hold_hours"]

    print("\n" + "=" * 90)
    print("  RUN COMPARISON")
    print("=" * 90)

    # Header
    header = f"{'Metric':25s}"
    for r in all_results:
        header += f" | {r.get('run_id', '???'):>18s}"
    print(header)
    print("-" * 90)

    for m in metrics:
        row = f"{m:25s}"
        for r in all_results:
            val = r.get(m, "N/A")
            if isinstance(val, float):
                row += f" | {val:>18.2f}"
            else:
                row += f" | {str(val):>18s}"
        print(row)

    # Gate summary
    print("-" * 90)
    row = f"{'GATE VERDICT':25s}"
    for r in all_results:
        gates = r.get("gates", {})
        row += f" | {gates.get('verdict', 'N/A'):>18s}"
    print(row)
    print("=" * 90)


# ============================================================
# CLI
# ============================================================
def resolve_run_path(run_id: str) -> Path | None:
    """Resolve a run ID to full path."""
    # Try direct path first
    p = Path(run_id)
    if p.exists():
        return p

    # Search in runs/
    for ea_dir in RUNS_DIR.iterdir():
        if ea_dir.is_dir():
            candidate = ea_dir / run_id
            if candidate.exists():
                return candidate

    # Glob search
    matches = list(RUNS_DIR.glob(f"*/{run_id}"))
    if matches:
        return matches[0]

    print(f"[ERROR] Run not found: {run_id}")
    return None


def main():
    parser = argparse.ArgumentParser(description="vectorbt Bridge for AlphaFactory")
    sub = parser.add_subparsers(dest="command")

    # analyze
    p_analyze = sub.add_parser("analyze", help="Full analysis of a run")
    p_analyze.add_argument("run", help="Run ID or path")

    # compare
    p_compare = sub.add_parser("compare", help="Compare multiple runs")
    p_compare.add_argument("runs", nargs="+", help="Run IDs or paths")

    # equity
    p_equity = sub.add_parser("equity", help="Interactive equity chart")
    p_equity.add_argument("run", help="Run ID or path")

    # rolling
    p_rolling = sub.add_parser("rolling", help="Rolling Sharpe + DD chart")
    p_rolling.add_argument("run", help="Run ID or path")
    p_rolling.add_argument("--window", type=int, default=90, help="Rolling window days")

    # monte
    p_monte = sub.add_parser("monte", help="Fast Monte Carlo")
    p_monte.add_argument("run", help="Run ID or path")
    p_monte.add_argument("--sims", type=int, default=1000, help="Number of simulations")

    args = parser.parse_args()

    if args.command == "analyze":
        rp = resolve_run_path(args.run)
        if rp:
            analyze_run(rp)
    elif args.command == "compare":
        paths = [resolve_run_path(r) for r in args.runs]
        paths = [p for p in paths if p is not None]
        if paths:
            compare_runs(paths)
    elif args.command == "equity":
        rp = resolve_run_path(args.run)
        if rp:
            equity_chart(rp)
    elif args.command == "rolling":
        rp = resolve_run_path(args.run)
        if rp:
            rolling_analysis(rp, args.window)
    elif args.command == "monte":
        rp = resolve_run_path(args.run)
        if rp:
            fast_monte_carlo(rp, args.sims)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
