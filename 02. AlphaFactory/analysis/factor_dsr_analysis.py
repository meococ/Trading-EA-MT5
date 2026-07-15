#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Factor Decomposition & Deflated Sharpe Ratio Analysis
=====================================================
The most important quant analysis for this portfolio.
Determines whether our "alpha" is real or just factor beta in disguise.

Part 1: Factor Decomposition (OLS regression of EA returns on market factors)
Part 2: Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014)
Part 3: Honest Summary Table
"""

import os
import sys
import io
import json
import warnings
from datetime import datetime, timedelta
from pathlib import Path

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

warnings.filterwarnings('ignore')

# Try importing optional packages
try:
    import statsmodels.api as sm
    HAS_SM = True
except ImportError:
    HAS_SM = False
    print("WARNING: statsmodels not available, using manual OLS")

try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False
    print("WARNING: yfinance not available, will construct factor proxies from trade data")


# ============================================================
# CONFIGURATION
# ============================================================
ROOT = Path(r"c:\Users\ADMIN\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\Advisors")
RUNS = ROOT / "02. AlphaFactory" / "runs"

# Trade data files (latest runs)
EA_FILES = {
    "Cobra_XAUUSD":       RUNS / "EA_Cobra/20260402_225139/analysis/trades_detail.csv",
    "SilverBullet_USDJPY": RUNS / "EA_SilverBullet/20260402_225249/analysis/trades_detail.csv",
    "Spark_USDJPY":       RUNS / "EA_Spark/20260402_225410/analysis/trades_detail.csv",
    "Spark_GBPUSD":       RUNS / "EA_Spark/20260402_221411/analysis/trades_detail.csv",
    "InsideBar_USDJPY":   RUNS / "EA_InsideBar/20260402_225507/analysis/trades_detail.csv",
    "InsideBar_GBPUSD":   RUNS / "EA_InsideBar/20260402_225542/analysis/trades_detail.csv",
    "ITSM_USDJPY":        RUNS / "EA_ITSM/20260403_022055/analysis/trades_detail.csv",
    "LondonNY_USDJPY":    RUNS / "EA_LondonNY/20260403_022234/analysis/trades_detail.csv",
    "Gotobi_USDJPY":      RUNS / "EA_Gotobi/20260403_022500/analysis/trades_detail.csv",
}

# Number of variants tested per EA (honest count for DSR)
EA_VARIANTS = {
    "Cobra_XAUUSD":        10,
    "SilverBullet_USDJPY": 30,
    "Spark_USDJPY":        15,
    "Spark_GBPUSD":        15,
    "InsideBar_USDJPY":    20,
    "InsideBar_GBPUSD":    20,
    "ITSM_USDJPY":         15,
    "LondonNY_USDJPY":     10,
    "Gotobi_USDJPY":        5,
}

TOTAL_BACKTESTS = 220

EA_ASSET = {
    "Cobra_XAUUSD":        "XAUUSD",
    "SilverBullet_USDJPY": "USDJPY",
    "Spark_USDJPY":        "USDJPY",
    "Spark_GBPUSD":        "GBPUSD",
    "InsideBar_USDJPY":    "USDJPY",
    "InsideBar_GBPUSD":    "GBPUSD",
    "ITSM_USDJPY":         "USDJPY",
    "LondonNY_USDJPY":     "USDJPY",
    "Gotobi_USDJPY":       "USDJPY",
}


# ============================================================
# STEP 1: LOAD ALL TRADE DATA
# ============================================================
def load_trades():
    trades = {}
    for name, fpath in EA_FILES.items():
        if not fpath.exists():
            print(f"  WARNING: {fpath} not found, skipping {name}")
            continue
        df = pd.read_csv(fpath)
        for col in ['entry_time', 'exit_time']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], format='%Y.%m.%d %H:%M:%S', errors='coerce')
        trades[name] = df
        print(f"  Loaded {name}: {len(df)} trades, "
              f"{df['entry_time'].min().strftime('%Y-%m') if pd.notna(df['entry_time'].min()) else '?'} to "
              f"{df['entry_time'].max().strftime('%Y-%m') if pd.notna(df['entry_time'].max()) else '?'}")
    return trades


def trades_to_monthly(trades_dict):
    """Aggregate trade P&L to monthly returns per EA.
    Key: Use YYYYMM string keys for alignment with factor data."""
    monthly = {}
    for name, df in trades_dict.items():
        df = df.dropna(subset=['exit_time', 'net_profit_usd'])
        df['ym'] = df['exit_time'].dt.to_period('M')
        m = df.groupby('ym')['net_profit_usd'].sum()
        # Convert Period index to string YYYY-MM for safe alignment
        m.index = m.index.astype(str)
        monthly[name] = m
    return monthly


# ============================================================
# STEP 2: DOWNLOAD / CONSTRUCT FACTOR DATA
# ============================================================
def download_factors(start_date, end_date):
    tickers = {
        'GLD': 'GLD',
        'USDJPY': 'USDJPY=X',
        'GBPUSD': 'GBPUSD=X',
        'VIX': '^VIX',
        'TNX': '^TNX',
    }
    data = {}
    for label, ticker in tickers.items():
        try:
            df = yf.download(ticker, start=start_date, end=end_date, auto_adjust=True, progress=False)
            if len(df) > 0:
                # Handle multi-level columns from yfinance
                if isinstance(df.columns, pd.MultiIndex):
                    close = df['Close'].iloc[:, 0] if df['Close'].shape[1] > 0 else df['Close']
                else:
                    close = df['Close']
                data[label] = close.dropna()
                print(f"  Downloaded {label} ({ticker}): {len(data[label])} bars")
            else:
                print(f"  WARNING: No data for {label} ({ticker})")
        except Exception as e:
            print(f"  WARNING: Failed to download {label}: {e}")
    return data


def construct_factors_from_market(market_data):
    """Build monthly factor proxies from downloaded market data.
    Key: Use YYYY-MM string index for alignment with EA returns."""
    factors = {}

    # Gold Momentum: 12-month rolling return (exclude last month per academic standard)
    if 'GLD' in market_data:
        gld_m = market_data['GLD'].resample('ME').last()
        gold_mom = gld_m.pct_change(11).shift(1)
        for dt, val in gold_mom.items():
            ym = dt.strftime('%Y-%m')
            if ym not in factors:
                factors[ym] = {}
            factors[ym]['Gold_Mom'] = val

    # FX Momentum USDJPY
    if 'USDJPY' in market_data:
        uj_m = market_data['USDJPY'].resample('ME').last()
        fx_mom = uj_m.pct_change(11).shift(1)
        for dt, val in fx_mom.items():
            ym = dt.strftime('%Y-%m')
            if ym not in factors:
                factors[ym] = {}
            factors[ym]['FX_Mom_USDJPY'] = val

    # FX Momentum GBPUSD
    if 'GBPUSD' in market_data:
        gu_m = market_data['GBPUSD'].resample('ME').last()
        gu_mom = gu_m.pct_change(11).shift(1)
        for dt, val in gu_mom.items():
            ym = dt.strftime('%Y-%m')
            if ym not in factors:
                factors[ym] = {}
            factors[ym]['FX_Mom_GBPUSD'] = val

    # Volatility Factor: Monthly change in VIX
    if 'VIX' in market_data:
        vix_m = market_data['VIX'].resample('ME').last()
        vol_chg = vix_m.diff()
        for dt, val in vol_chg.items():
            ym = dt.strftime('%Y-%m')
            if ym not in factors:
                factors[ym] = {}
            factors[ym]['Vol_Change'] = val

    # Carry Proxy: Change in US 10yr yield
    if 'TNX' in market_data:
        tnx_m = market_data['TNX'].resample('ME').last()
        carry = tnx_m.diff()
        for dt, val in carry.items():
            ym = dt.strftime('%Y-%m')
            if ym not in factors:
                factors[ym] = {}
            factors[ym]['Carry_Proxy'] = val

    # Gold realized volatility
    if 'GLD' in market_data:
        gld_ret = market_data['GLD'].pct_change()
        gld_vol = gld_ret.rolling(21).std() * np.sqrt(252)
        gld_vol_m = gld_vol.resample('ME').last()
        for dt, val in gld_vol_m.items():
            ym = dt.strftime('%Y-%m')
            if ym not in factors:
                factors[ym] = {}
            factors[ym]['Gold_Vol'] = val

    # USDJPY realized volatility
    if 'USDJPY' in market_data:
        uj_ret = market_data['USDJPY'].pct_change()
        uj_vol = uj_ret.rolling(21).std() * np.sqrt(252)
        uj_vol_m = uj_vol.resample('ME').last()
        for dt, val in uj_vol_m.items():
            ym = dt.strftime('%Y-%m')
            if ym not in factors:
                factors[ym] = {}
            factors[ym]['USDJPY_Vol'] = val

    # Convert to DataFrame with YYYY-MM string index
    factor_df = pd.DataFrame.from_dict(factors, orient='index')
    factor_df.index.name = 'ym'
    factor_df = factor_df.sort_index()
    return factor_df


def construct_factors_from_trades(monthly_returns):
    """Fallback: construct basic factor proxies from the trade data itself."""
    all_months = set()
    for name, series in monthly_returns.items():
        all_months.update(series.index)
    all_months = sorted(all_months)

    total_pnl = pd.Series(0.0, index=all_months)
    for name, series in monthly_returns.items():
        total_pnl = total_pnl.add(series.reindex(all_months, fill_value=0), fill_value=0)

    factor_df = pd.DataFrame(index=all_months)
    factor_df.index.name = 'ym'
    factor_df['Agg_Mom'] = total_pnl.rolling(3).mean().shift(1)
    factor_df['Agg_Vol'] = total_pnl.rolling(6).std()
    return factor_df


# ============================================================
# STEP 3: FACTOR DECOMPOSITION (OLS)
# ============================================================
def run_factor_regression(ea_returns, factors, ea_name, ea_asset):
    """Run OLS regression of EA monthly returns on factor proxies.
    Both ea_returns and factors use YYYY-MM string index."""

    # Select relevant factors based on asset
    if ea_asset == "XAUUSD":
        factor_cols = [c for c in ['Gold_Mom', 'Gold_Vol', 'Vol_Change', 'Carry_Proxy'] if c in factors.columns]
    elif ea_asset == "USDJPY":
        factor_cols = [c for c in ['FX_Mom_USDJPY', 'USDJPY_Vol', 'Vol_Change', 'Carry_Proxy'] if c in factors.columns]
    elif ea_asset == "GBPUSD":
        factor_cols = [c for c in ['FX_Mom_GBPUSD', 'Vol_Change', 'Carry_Proxy'] if c in factors.columns]
    else:
        # MIXED / portfolio: use all factors
        factor_cols = [c for c in factors.columns]

    if not factor_cols:
        factor_cols = list(factors.columns)

    # Align by YYYY-MM string index
    common_idx = sorted(set(ea_returns.index) & set(factors.index))

    if len(common_idx) < 6:
        return {
            'ea_name': ea_name,
            'n_months': len(common_idx),
            'r_squared': np.nan,
            'alpha': np.nan,
            'alpha_tstat': np.nan,
            'alpha_pvalue': np.nan,
            'betas': {},
            'note': f'Insufficient aligned data ({len(common_idx)} months < 6 minimum). '
                    f'EA months: {len(ea_returns)}, Factor months: {len(factors)}'
        }

    Y = ea_returns.reindex(common_idx).values.astype(float)
    X = factors.loc[common_idx, factor_cols].values.astype(float)

    # Remove any rows with NaN
    mask = np.isfinite(Y) & np.all(np.isfinite(X), axis=1)
    Y = Y[mask]
    X = X[mask]
    n = len(Y)

    if n < 6:
        return {
            'ea_name': ea_name,
            'n_months': n,
            'r_squared': np.nan,
            'alpha': np.nan,
            'alpha_tstat': np.nan,
            'alpha_pvalue': np.nan,
            'betas': {},
            'note': f'After NaN removal only {n} obs remain (<6)'
        }

    if HAS_SM:
        X_const = sm.add_constant(X)
        try:
            model = sm.OLS(Y, X_const).fit()
            result = {
                'ea_name': ea_name,
                'n_months': n,
                'r_squared': float(model.rsquared),
                'adj_r_squared': float(model.rsquared_adj),
                'alpha': float(model.params[0]),
                'alpha_tstat': float(model.tvalues[0]),
                'alpha_pvalue': float(model.pvalues[0]),
                'betas': {},
                'f_stat': float(model.fvalue) if not np.isnan(model.fvalue) else None,
                'f_pvalue': float(model.f_pvalue) if not np.isnan(model.f_pvalue) else None,
                'durbin_watson': float(sm.stats.stattools.durbin_watson(model.resid)),
            }
            for i, col in enumerate(factor_cols):
                result['betas'][col] = {
                    'coeff': float(model.params[i+1]),
                    'tstat': float(model.tvalues[i+1]),
                    'pvalue': float(model.pvalues[i+1]),
                }
            return result
        except Exception as e:
            print(f"  statsmodels OLS error for {ea_name}: {e}, falling back to manual")

    # Manual OLS fallback
    X_const = np.column_stack([np.ones(n), X])
    k = X.shape[1]
    try:
        beta, residuals, rank, sv = np.linalg.lstsq(X_const, Y, rcond=None)
        Y_hat = X_const @ beta
        ss_res = np.sum((Y - Y_hat) ** 2)
        ss_tot = np.sum((Y - np.mean(Y)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        adj_r2 = 1 - (1 - r2) * (n - 1) / (n - k - 1) if n > k + 1 else r2

        mse = ss_res / (n - k - 1) if n > k + 1 else ss_res / max(n - 1, 1)
        try:
            cov = mse * np.linalg.inv(X_const.T @ X_const)
            se = np.sqrt(np.diag(cov))
        except:
            se = np.full(k + 1, np.nan)

        t_stats = beta / se
        p_values = [float(2 * (1 - sp_stats.t.cdf(abs(t), df=max(n - k - 1, 1)))) for t in t_stats]

        result = {
            'ea_name': ea_name,
            'n_months': n,
            'r_squared': float(r2),
            'adj_r_squared': float(adj_r2),
            'alpha': float(beta[0]),
            'alpha_tstat': float(t_stats[0]),
            'alpha_pvalue': float(p_values[0]),
            'betas': {},
        }
        for i, col in enumerate(factor_cols):
            result['betas'][col] = {
                'coeff': float(beta[i+1]),
                'tstat': float(t_stats[i+1]),
                'pvalue': float(p_values[i+1]),
            }
        return result
    except Exception as e:
        return {
            'ea_name': ea_name,
            'n_months': n,
            'r_squared': np.nan,
            'alpha': np.nan,
            'alpha_tstat': np.nan,
            'alpha_pvalue': np.nan,
            'betas': {},
            'note': f'Regression failed: {e}'
        }


# ============================================================
# STEP 4: DEFLATED SHARPE RATIO
# ============================================================
def compute_dsr(monthly_returns_series, n_variants, ea_name):
    """
    Compute Deflated Sharpe Ratio per Bailey & Lopez de Prado (2014).

    The Probabilistic Sharpe Ratio (PSR) tests whether an observed SR exceeds
    a reference SR*, accounting for non-normality of returns:
        PSR(SR*) = Phi[(SR_hat - SR*) * sqrt(T-1) / sqrt(1 - g3*SR + (g4-1)/4*SR^2)]

    For the Deflated Sharpe Ratio, SR* = SR_0 = expected max SR from N trials under null.
    Under the null (true SR=0), SR_hat ~ N(0, 1/T) approximately.
    Therefore E[max of N null SR estimates] = E[max(Z)] / sqrt(T)
    where E[max(Z)] = sqrt(2*ln(N)) * (1 - gamma_euler/(2*ln(N)) + gamma_euler/(4*ln(N)^2))
    """
    EULER_MASCHERONI = 0.5772156649

    returns = np.array(monthly_returns_series.dropna(), dtype=float)
    T = len(returns)

    if T < 3:
        return {
            'ea_name': ea_name,
            'n_months': T,
            'raw_sharpe_monthly': np.nan,
            'raw_sharpe_annual': np.nan,
            'sr_0': np.nan,
            'dsr': np.nan,
            'note': f'Insufficient data ({T} months)'
        }

    # Raw Sharpe (monthly, then annualized)
    std_ret = np.std(returns, ddof=1)
    sr_monthly = np.mean(returns) / std_ret if std_ret > 0 else 0
    sr_annual = sr_monthly * np.sqrt(12)

    # Return distribution moments
    gamma3 = float(sp_stats.skew(returns))           # skewness
    gamma4 = float(sp_stats.kurtosis(returns, fisher=False))  # raw kurtosis (normal=3)

    # Expected maximum of N standard normal variables
    N = max(n_variants, 2)
    ln_N = np.log(N)
    e_max_z = np.sqrt(2 * ln_N) * (1 - EULER_MASCHERONI / (2 * ln_N) + EULER_MASCHERONI / (4 * ln_N**2))

    # SR_0: Expected max Sharpe from N independent trials under null
    # Under null, SR_hat has std ~ 1/sqrt(T), so E[max(SR)] = E[max(Z)] / sqrt(T)
    sr_0_monthly = e_max_z / np.sqrt(T)

    # DSR computation using PSR formula with SR* = SR_0
    numerator = (sr_monthly - sr_0_monthly) * np.sqrt(T - 1)

    denom_sq = 1 - gamma3 * sr_monthly + ((gamma4 - 1) / 4) * sr_monthly**2

    if denom_sq <= 0:
        dsr = 0.0
        z_score = -999.0
    else:
        denominator = np.sqrt(denom_sq)
        z_score = numerator / denominator
        dsr = float(sp_stats.norm.cdf(z_score))

    return {
        'ea_name': ea_name,
        'n_months': int(T),
        'n_variants_tested': int(N),
        'mean_monthly_return': float(np.mean(returns)),
        'std_monthly_return': float(std_ret),
        'raw_sharpe_monthly': float(sr_monthly),
        'raw_sharpe_annual': float(sr_annual),
        'skewness': float(gamma3),
        'kurtosis_raw': float(gamma4),
        'e_max_z': float(e_max_z),
        'sr_0_monthly': float(sr_0_monthly),
        'sr_0_annual': float(sr_0_monthly * np.sqrt(12)),
        'z_score': float(z_score),
        'dsr': float(dsr),
    }


# ============================================================
# STEP 5: VERDICT LOGIC
# ============================================================
def compute_verdict(factor_result, dsr_result):
    r2 = factor_result.get('r_squared', np.nan)
    alpha_p = factor_result.get('alpha_pvalue', np.nan)
    alpha_val = factor_result.get('alpha', np.nan)
    dsr = dsr_result.get('dsr', np.nan)
    sr = dsr_result.get('raw_sharpe_annual', np.nan)

    if np.isnan(r2) or np.isnan(dsr):
        if not np.isnan(dsr):
            if dsr >= 0.95:
                return "DSR PASS (no factor data)"
            elif dsr >= 0.50:
                return "INCONCLUSIVE (no factor data)"
            else:
                return "LIKELY OVERFIT (no factor data)"
        return "INSUFFICIENT DATA"

    alpha_sig = (not np.isnan(alpha_p)) and alpha_p < 0.10
    alpha_strong = (not np.isnan(alpha_p)) and alpha_p < 0.05
    alpha_positive = (not np.isnan(alpha_val)) and alpha_val > 0

    # Negative Sharpe = unprofitable, regardless of factor or DSR
    if not np.isnan(sr) and sr < 0:
        return "UNPROFITABLE"

    # Decision matrix
    if r2 > 0.50 and not alpha_sig:
        return "FACTOR BETA"
    elif r2 > 0.50 and alpha_sig and not alpha_positive:
        return "FACTOR BETA (neg alpha)"
    elif r2 > 0.50 and alpha_strong and alpha_positive and dsr >= 0.50:
        return "FACTOR BETA + RESIDUAL ALPHA"
    elif r2 > 0.50 and alpha_sig and alpha_positive and dsr < 0.50:
        return "LIKELY OVERFIT"
    elif r2 <= 0.15 and alpha_positive and dsr >= 0.95:
        return "GENUINE ALPHA"
    elif r2 <= 0.15 and alpha_positive and dsr >= 0.50:
        return "PROBABLE ALPHA"
    elif r2 <= 0.30 and alpha_strong and alpha_positive and dsr >= 0.95:
        return "GENUINE ALPHA"
    elif r2 <= 0.30 and alpha_sig and alpha_positive and dsr >= 0.50:
        return "PROBABLE ALPHA"
    elif r2 <= 0.30 and alpha_positive and dsr >= 0.50:
        return "ALPHA (FACTOR-INDEPENDENT)"
    elif r2 <= 0.30 and dsr < 0.50:
        return "LIKELY OVERFIT"
    elif 0.30 < r2 <= 0.50 and alpha_sig and alpha_positive and dsr >= 0.50:
        return "PROBABLE ALPHA"
    elif 0.30 < r2 <= 0.50 and not alpha_sig:
        return "INCONCLUSIVE"
    else:
        return "INCONCLUSIVE"


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 80)
    print("FACTOR DECOMPOSITION & DEFLATED SHARPE RATIO ANALYSIS")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    # --- Load trade data ---
    print("[1/5] Loading trade data...")
    trades = load_trades()
    if not trades:
        print("FATAL: No trade data found. Aborting.")
        sys.exit(1)

    # --- Convert to monthly returns ---
    print("\n[2/5] Aggregating to monthly returns...")
    monthly = trades_to_monthly(trades)
    for name, series in monthly.items():
        total = series.sum()
        n_months = len(series)
        avg = series.mean()
        print(f"  {name}: {n_months} months, total ${total:,.0f}, avg ${avg:,.0f}/month")

    # --- Get market factor data ---
    print("\n[3/5] Constructing factor proxies...")

    all_dates = []
    for name, df in trades.items():
        all_dates.extend(df['entry_time'].dropna().tolist())
    min_date = min(all_dates) - timedelta(days=400)
    max_date = max(all_dates) + timedelta(days=30)

    factors = None
    market_data = None

    if HAS_YF:
        print(f"  Downloading market data: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")
        market_data = download_factors(min_date.strftime('%Y-%m-%d'), max_date.strftime('%Y-%m-%d'))
        if market_data and len(market_data) >= 2:
            factors = construct_factors_from_market(market_data)
            print(f"  Factor matrix: {len(factors)} months, {list(factors.columns)}")
            print(f"  Factor index sample: {list(factors.index[:3])} ... {list(factors.index[-3:])}")
        else:
            print("  WARNING: Insufficient market data downloaded")

    if factors is None or len(factors.dropna()) < 6:
        print("  Falling back to trade-derived factor proxies...")
        factors = construct_factors_from_trades(monthly)
        print(f"  Factor matrix (trade-derived): {len(factors)} months, {list(factors.columns)}")

    # Check alignment
    sample_ea = list(monthly.keys())[0]
    sample_ea_idx = set(monthly[sample_ea].index)
    sample_factor_idx = set(factors.index)
    overlap = sample_ea_idx & sample_factor_idx
    print(f"\n  Alignment check: {sample_ea} has {len(sample_ea_idx)} months, factors have {len(sample_factor_idx)} months, overlap={len(overlap)}")
    if overlap:
        print(f"  Sample overlap: {sorted(overlap)[:3]}")

    print(f"\n  Factor data preview (last 5 rows):")
    print(factors.dropna().tail().to_string())
    print()

    # --- PART 1: Factor Decomposition ---
    print("\n" + "=" * 80)
    print("PART 1: FACTOR DECOMPOSITION")
    print("=" * 80)

    factor_results = {}
    for name, series in monthly.items():
        asset = EA_ASSET.get(name, "UNKNOWN")
        result = run_factor_regression(series, factors, name, asset)
        factor_results[name] = result

        r2 = result.get('r_squared', np.nan)
        alpha = result.get('alpha', np.nan)
        alpha_t = result.get('alpha_tstat', np.nan)
        alpha_p = result.get('alpha_pvalue', np.nan)

        print(f"\n--- {name} ({asset}) ---")
        print(f"  N months: {result['n_months']}")

        if 'note' in result:
            print(f"  NOTE: {result['note']}")
            continue

        print(f"  R-squared: {r2:.4f}  (adj: {result.get('adj_r_squared', np.nan):.4f})")
        print(f"  Alpha (intercept): ${alpha:,.2f}/month  [t={alpha_t:.2f}, p={alpha_p:.4f}]")

        sig_marker = ""
        if not np.isnan(alpha_p):
            if alpha_p < 0.01: sig_marker = " ***"
            elif alpha_p < 0.05: sig_marker = " **"
            elif alpha_p < 0.10: sig_marker = " *"
        print(f"  Alpha significance: {'YES' if not np.isnan(alpha_p) and alpha_p < 0.10 else 'NO'}{sig_marker}")

        if r2 > 0.50:
            print(f"  >> WARNING: R-sq > 0.50 -- most returns explained by known factors!")
        elif r2 < 0.15:
            print(f"  >> GOOD: R-sq < 0.15 -- returns are largely factor-independent")
        elif r2 < 0.30:
            print(f"  >> OK: R-sq < 0.30 -- mostly factor-independent")

        if 'durbin_watson' in result:
            dw = result['durbin_watson']
            print(f"  Durbin-Watson: {dw:.3f} {'(autocorrelation concern)' if dw < 1.5 or dw > 2.5 else '(OK)'}")

        for fname, fbeta in result.get('betas', {}).items():
            sig = ""
            if fbeta['pvalue'] < 0.01: sig = "***"
            elif fbeta['pvalue'] < 0.05: sig = "**"
            elif fbeta['pvalue'] < 0.10: sig = "*"
            print(f"    {fname}: beta={fbeta['coeff']:.4f} [t={fbeta['tstat']:.2f}, p={fbeta['pvalue']:.4f}] {sig}")

    # Portfolio regression
    print(f"\n--- PORTFOLIO (ALL EAs COMBINED) ---")
    all_ym = set()
    for s in monthly.values():
        all_ym.update(s.index)
    all_ym = sorted(all_ym)
    port_returns = pd.Series(0.0, index=all_ym)
    for s in monthly.values():
        port_returns = port_returns.add(s.reindex(all_ym, fill_value=0), fill_value=0)

    port_factor = run_factor_regression(port_returns, factors, "PORTFOLIO", "MIXED")
    factor_results["PORTFOLIO"] = port_factor

    r2 = port_factor.get('r_squared', np.nan)
    alpha = port_factor.get('alpha', np.nan)
    alpha_t = port_factor.get('alpha_tstat', np.nan)
    alpha_p = port_factor.get('alpha_pvalue', np.nan)
    print(f"  N months: {port_factor['n_months']}")
    if 'note' in port_factor:
        print(f"  NOTE: {port_factor['note']}")
    else:
        print(f"  R-squared: {r2:.4f}  (adj: {port_factor.get('adj_r_squared', np.nan):.4f})")
        print(f"  Alpha (intercept): ${alpha:,.2f}/month  [t={alpha_t:.2f}, p={alpha_p:.4f}]")
        if 'durbin_watson' in port_factor:
            print(f"  Durbin-Watson: {port_factor['durbin_watson']:.3f}")
        for fname, fbeta in port_factor.get('betas', {}).items():
            sig = ""
            if fbeta['pvalue'] < 0.01: sig = "***"
            elif fbeta['pvalue'] < 0.05: sig = "**"
            elif fbeta['pvalue'] < 0.10: sig = "*"
            print(f"    {fname}: beta={fbeta['coeff']:.4f} [t={fbeta['tstat']:.2f}, p={fbeta['pvalue']:.4f}] {sig}")

    # --- PART 2: Deflated Sharpe Ratio ---
    print("\n\n" + "=" * 80)
    print("PART 2: DEFLATED SHARPE RATIO (Bailey & Lopez de Prado 2014)")
    print("=" * 80)

    dsr_results = {}
    for name, series in monthly.items():
        n_var = EA_VARIANTS.get(name, 10)
        result = compute_dsr(series, n_var, name)
        dsr_results[name] = result

        print(f"\n--- {name} (N_variants={n_var}) ---")
        if 'note' in result:
            print(f"  NOTE: {result['note']}")
            continue
        print(f"  Months: {result['n_months']}")
        print(f"  Mean return: ${result['mean_monthly_return']:,.2f}/month")
        print(f"  Std return:  ${result['std_monthly_return']:,.2f}/month")
        print(f"  Skewness:    {result['skewness']:.3f}")
        print(f"  Kurtosis:    {result['kurtosis_raw']:.3f}  (normal=3)")
        print(f"  Raw Sharpe (annual): {result['raw_sharpe_annual']:.3f}")
        print(f"  SR_0 hurdle (annual, for {n_var} trials): {result['sr_0_annual']:.3f}")
        print(f"  z-score: {result['z_score']:.3f}")
        print(f"  DSR: {result['dsr']:.4f}")

        if result['dsr'] >= 0.95:
            print(f"  >> PASS: DSR >= 0.95 -- Edge survives multiple testing correction")
        elif result['dsr'] >= 0.50:
            print(f"  >> MIXED: DSR in [0.50, 0.95] -- Cannot rule out luck")
        else:
            print(f"  >> FAIL: DSR < 0.50 -- Likely selection artifact")

    # Portfolio DSR
    print(f"\n--- PORTFOLIO (N_variants={TOTAL_BACKTESTS}) ---")
    port_dsr = compute_dsr(port_returns, TOTAL_BACKTESTS, "PORTFOLIO")
    dsr_results["PORTFOLIO"] = port_dsr
    if 'note' not in port_dsr:
        print(f"  Months: {port_dsr['n_months']}")
        print(f"  Mean return: ${port_dsr['mean_monthly_return']:,.2f}/month")
        print(f"  Std return:  ${port_dsr['std_monthly_return']:,.2f}/month")
        print(f"  Skewness:    {port_dsr['skewness']:.3f}")
        print(f"  Kurtosis:    {port_dsr['kurtosis_raw']:.3f}")
        print(f"  Raw Sharpe (annual): {port_dsr['raw_sharpe_annual']:.3f}")
        print(f"  SR_0 hurdle (annual, for {TOTAL_BACKTESTS} trials): {port_dsr['sr_0_annual']:.3f}")
        print(f"  z-score: {port_dsr['z_score']:.3f}")
        print(f"  DSR: {port_dsr['dsr']:.4f}")
    else:
        print(f"  NOTE: {port_dsr['note']}")

    # --- PART 3: Summary Table ---
    print("\n\n" + "=" * 80)
    print("PART 3: HONEST SUMMARY TABLE")
    print("=" * 80)

    header = f"{'EA':<25} {'Raw SR':>8} {'R-sq':>8} {'Alpha $/mo':>12} {'a t-stat':>10} {'a p-val':>9} {'DSR':>8} {'VERDICT':<28}"
    sep = "-" * len(header)
    print(header)
    print(sep)

    verdicts = {}
    all_names = list(monthly.keys()) + ["PORTFOLIO"]

    for name in all_names:
        fr = factor_results.get(name, {})
        dr = dsr_results.get(name, {})

        sr_a = dr.get('raw_sharpe_annual', np.nan)
        r2 = fr.get('r_squared', np.nan)
        alpha = fr.get('alpha', np.nan)
        alpha_t = fr.get('alpha_tstat', np.nan)
        alpha_p = fr.get('alpha_pvalue', np.nan)
        dsr = dr.get('dsr', np.nan)

        verdict = compute_verdict(fr, dr)
        verdicts[name] = verdict

        sr_str = f"{sr_a:.2f}" if not np.isnan(sr_a) else "N/A"
        r2_str = f"{r2:.3f}" if not np.isnan(r2) else "N/A"
        a_str = f"${alpha:,.0f}" if not np.isnan(alpha) else "N/A"
        at_str = f"{alpha_t:.2f}" if not np.isnan(alpha_t) else "N/A"
        ap_str = f"{alpha_p:.4f}" if not np.isnan(alpha_p) else "N/A"
        dsr_str = f"{dsr:.3f}" if not np.isnan(dsr) else "N/A"

        print(f"{name:<25} {sr_str:>8} {r2_str:>8} {a_str:>12} {at_str:>10} {ap_str:>9} {dsr_str:>8} {verdict:<28}")

    # --- FINAL INTERPRETATION ---
    print("\n\n" + "=" * 80)
    print("FINAL INTERPRETATION")
    print("=" * 80)

    genuine = [n for n, v in verdicts.items() if "GENUINE" in v or "PROBABLE" in v or "FACTOR-INDEPENDENT" in v]
    factor_beta = [n for n, v in verdicts.items() if "FACTOR BETA" in v and "RESIDUAL" not in v]
    overfit = [n for n, v in verdicts.items() if "OVERFIT" in v]
    inconclusive = [n for n, v in verdicts.items() if "INCONCLUSIVE" in v]
    insufficient = [n for n, v in verdicts.items() if "INSUFFICIENT" in v]
    unprofitable = [n for n, v in verdicts.items() if "UNPROFITABLE" in v]

    print(f"\n  GENUINE/PROBABLE ALPHA: {genuine if genuine else 'NONE'}")
    print(f"  FACTOR BETA (no alpha): {factor_beta if factor_beta else 'NONE'}")
    print(f"  LIKELY OVERFIT:         {overfit if overfit else 'NONE'}")
    print(f"  UNPROFITABLE:           {unprofitable if unprofitable else 'NONE'}")
    print(f"  INCONCLUSIVE:           {inconclusive if inconclusive else 'NONE'}")
    print(f"  INSUFFICIENT DATA:      {insufficient if insufficient else 'NONE'}")

    port_verdict = verdicts.get("PORTFOLIO", "UNKNOWN")
    port_dsr_val = dsr_results.get("PORTFOLIO", {}).get('dsr', np.nan)
    port_r2 = factor_results.get("PORTFOLIO", {}).get('r_squared', np.nan)
    port_alpha = factor_results.get("PORTFOLIO", {}).get('alpha', np.nan)
    port_alpha_p = factor_results.get("PORTFOLIO", {}).get('alpha_pvalue', np.nan)

    print(f"\n  PORTFOLIO BOTTOM LINE:")
    print(f"    Factor R-sq = {port_r2:.3f}" if not np.isnan(port_r2) else "    Factor R-sq = N/A")
    print(f"    Monthly Alpha = ${port_alpha:,.0f} (p={port_alpha_p:.4f})" if not np.isnan(port_alpha) else "    Monthly Alpha = N/A")
    print(f"    DSR = {port_dsr_val:.3f}" if not np.isnan(port_dsr_val) else "    DSR = N/A")
    print(f"    Verdict: {port_verdict}")

    print(f"\n  KEY QUESTION: 'After removing known factor exposures, does residual alpha remain?'")
    if not np.isnan(port_r2) and port_r2 < 0.30:
        print(f"  ANSWER: YES -- Only {port_r2*100:.1f}% of portfolio returns explained by known factors.")
        print(f"          The remaining {(1-port_r2)*100:.1f}% is idiosyncratic to strategy mechanisms.")
    elif not np.isnan(port_r2) and port_r2 < 0.50:
        print(f"  ANSWER: PARTIALLY -- {port_r2*100:.1f}% explained by factors, {(1-port_r2)*100:.1f}% residual.")
    elif not np.isnan(port_r2):
        print(f"  ANSWER: CAUTION -- {port_r2*100:.1f}% of returns explained by known factors.")
    else:
        print(f"  ANSWER: Cannot determine (insufficient aligned data)")

    if not np.isnan(port_dsr_val):
        if port_dsr_val >= 0.95:
            print(f"  DSR confirms the Sharpe ratio survives correction for {TOTAL_BACKTESTS} backtests.")
        elif port_dsr_val >= 0.50:
            print(f"  DSR is inconclusive -- Sharpe could partially be selection artifact from {TOTAL_BACKTESTS} tests.")
        else:
            print(f"  DSR suggests portfolio Sharpe is LIKELY a selection artifact from {TOTAL_BACKTESTS} tests.")

    # --- CRITICAL NOTES ---
    print(f"\n  CRITICAL NOTES ON DSR INTERPRETATION:")
    print(f"  - SR_0 assumes all N trials are INDEPENDENT with zero true Sharpe under null")
    print(f"  - Our 220 backtests include many correlated variants (same mechanism, different params)")
    print(f"  - True effective N is lower than 220 -- perhaps 30-50 independent hypotheses")
    print(f"  - With N_eff=40, the hurdle drops significantly")

    # Recompute portfolio DSR with estimated effective N
    N_eff = 40
    port_dsr_adj = compute_dsr(port_returns, N_eff, "PORTFOLIO_adjusted")
    print(f"\n  ADJUSTED DSR (N_eff={N_eff} independent hypotheses):")
    if 'note' not in port_dsr_adj:
        print(f"    SR_0 hurdle (annual): {port_dsr_adj['sr_0_annual']:.3f}")
        print(f"    Adjusted DSR: {port_dsr_adj['dsr']:.4f}")
        if port_dsr_adj['dsr'] >= 0.95:
            print(f"    --> PASSES even with adjusted N")
        elif port_dsr_adj['dsr'] >= 0.50:
            print(f"    --> Inconclusive with adjusted N")
        else:
            print(f"    --> Still fails with adjusted N")

    # --- Save artifacts ---
    print("\n\n[5/5] Saving artifacts...")

    def clean_for_json(obj):
        if isinstance(obj, dict):
            return {k: clean_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean_for_json(v) for v in obj]
        elif isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            v = float(obj)
            return v if not np.isnan(v) else None
        elif isinstance(obj, np.ndarray):
            return [clean_for_json(x) for x in obj.tolist()]
        elif isinstance(obj, float) and np.isnan(obj):
            return None
        return obj

    json_output = {
        'timestamp': datetime.now().isoformat(),
        'methodology': {
            'factor_decomposition': 'OLS regression of monthly EA returns on market factor proxies',
            'dsr': 'Bailey & Lopez de Prado (2014) Deflated Sharpe Ratio',
            'factors_used': list(factors.columns),
            'market_data_source': 'yfinance' if (HAS_YF and market_data) else 'trade-derived proxies',
        },
        'factor_results': {},
        'dsr_results': {},
        'verdicts': verdicts,
        'portfolio_summary': {
            'r_squared': clean_for_json(port_r2),
            'alpha_monthly': clean_for_json(port_alpha),
            'alpha_pvalue': clean_for_json(port_alpha_p),
            'dsr': clean_for_json(port_dsr_val),
            'dsr_adjusted_n40': clean_for_json(port_dsr_adj.get('dsr', np.nan)),
            'verdict': port_verdict,
            'total_backtests': TOTAL_BACKTESTS,
            'estimated_effective_n': N_eff,
        }
    }

    for name in all_names:
        if name in factor_results:
            json_output['factor_results'][name] = clean_for_json(factor_results[name])
        if name in dsr_results:
            json_output['dsr_results'][name] = clean_for_json(dsr_results[name])

    json_path = RUNS / "factor_dsr_analysis.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_output, f, indent=2, default=str, ensure_ascii=False)
    print(f"  JSON saved: {json_path}")

    # Human-readable summary
    summary_lines = []
    summary_lines.append("=" * 80)
    summary_lines.append("FACTOR DECOMPOSITION & DEFLATED SHARPE RATIO -- HONEST SUMMARY")
    summary_lines.append(f"Generated: {datetime.now().isoformat()}")
    summary_lines.append("=" * 80)
    summary_lines.append("")
    summary_lines.append(header)
    summary_lines.append(sep)

    for name in all_names:
        fr = factor_results.get(name, {})
        dr = dsr_results.get(name, {})
        sr_a = dr.get('raw_sharpe_annual', np.nan)
        r2 = fr.get('r_squared', np.nan)
        alpha = fr.get('alpha', np.nan)
        alpha_t = fr.get('alpha_tstat', np.nan)
        alpha_p = fr.get('alpha_pvalue', np.nan)
        dsr = dr.get('dsr', np.nan)
        verdict = verdicts.get(name, "?")
        sr_str = f"{sr_a:.2f}" if not np.isnan(sr_a) else "N/A"
        r2_str = f"{r2:.3f}" if not np.isnan(r2) else "N/A"
        a_str = f"${alpha:,.0f}" if not np.isnan(alpha) else "N/A"
        at_str = f"{alpha_t:.2f}" if not np.isnan(alpha_t) else "N/A"
        ap_str = f"{alpha_p:.4f}" if not np.isnan(alpha_p) else "N/A"
        dsr_str = f"{dsr:.3f}" if not np.isnan(dsr) else "N/A"
        summary_lines.append(f"{name:<25} {sr_str:>8} {r2_str:>8} {a_str:>12} {at_str:>10} {ap_str:>9} {dsr_str:>8} {verdict:<28}")

    summary_lines.append("")
    summary_lines.append("INTERPRETATION KEY:")
    summary_lines.append("  R-sq < 0.15 = returns almost entirely factor-independent (good)")
    summary_lines.append("  R-sq < 0.30 = returns mostly factor-independent (good)")
    summary_lines.append("  R-sq > 0.50 = returns mostly explained by known market factors (bad)")
    summary_lines.append("  Alpha p-val < 0.05 = statistically significant residual return (good)")
    summary_lines.append("  DSR > 0.95 = Sharpe survives multiple testing correction (good)")
    summary_lines.append("  DSR < 0.50 = Sharpe likely a selection artifact (bad)")
    summary_lines.append("")
    summary_lines.append(f"FACTORS: {list(factors.columns)}")
    summary_lines.append(f"MARKET DATA SOURCE: {'yfinance' if (HAS_YF and market_data) else 'trade-derived'}")
    summary_lines.append(f"TOTAL BACKTESTS (for portfolio DSR): {TOTAL_BACKTESTS}")
    summary_lines.append(f"ADJUSTED N_eff for DSR: {N_eff}")

    txt_path = RUNS / "factor_dsr_summary.txt"
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(summary_lines))
    print(f"  Summary saved: {txt_path}")

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

    return json_output


if __name__ == '__main__':
    result = main()
