"""
AlphaFactory Dashboard — EA Backtesting Workspace
Streamlit app: 4 pages — Leaderboard, Comparison, PROP_READY Gate, Strategy Profile
Launch: streamlit run "02. AlphaFactory/dashboard.py"
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import glob
import math
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = Path(__file__).resolve().parent / "runs"

PROP_GATES = {
    "CAGR >= 20%": {"key": "cagr", "op": ">=", "target": 20},
    "Max DD <= 8%": {"key": "max_drawdown_pct", "op": "<=", "target": 8},
    "Trades/year >= 100": {"key": "trades_per_year", "op": ">=", "target": 100},
    "Avg win/loss >= 1.4": {"key": "avg_win_loss_ratio", "op": ">=", "target": 1.4},
    "Max consec losses <= 15": {"key": "max_loss_streak", "op": "<=", "target": 15},
}

PROP_GATES_OPTIONAL = {
    "WFA efficiency >= 0.60": {"file": "wfa", "key": "efficiency_ratio", "op": ">=", "target": 0.60},
    "MC P95 DD <= 8%": {"file": "monte", "key": "mc_p95_dd", "op": "<=", "target": 8},
    "Robustness pass rate >= 60%": {"file": "robust", "key": "pass_rate", "op": ">=", "target": 60},
    "Param stability >= 50": {"file": "param", "key": "stability_score", "op": ">=", "target": 50},
}

# ---------------------------------------------------------------------------
# Helpers — data loading
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60)
def discover_runs() -> list[dict]:
    """Walk runs/ tree, find all enhanced_summary.json, return list of run info dicts."""
    runs = []
    if not RUNS_DIR.exists():
        return runs

    for summary_path in sorted(RUNS_DIR.rglob("enhanced_summary.json")):
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        # Derive run_id and ea_name from path
        # Pattern: runs/<ea_or_version>/<timestamp>/analysis/enhanced_summary.json
        # or:      runs/<ea_or_version>/<timestamp>/enhanced_summary.json (unlikely but handle)
        rel = summary_path.relative_to(RUNS_DIR)
        parts = list(rel.parts)

        # Find timestamp part (YYYYMMDD_HHMMSS pattern)
        run_id = None
        ea_name = None
        run_dir = summary_path.parent
        # Walk up to find the run root (the dir that contains analysis/ or is the timestamp dir)
        for p in summary_path.parents:
            if p == RUNS_DIR:
                break
            dirname = p.name
            if len(dirname) == 15 and dirname[8] == "_" and dirname[:8].isdigit():
                run_id = dirname
                run_dir = p
                # ea_name is the parent of this timestamp dir relative to RUNS_DIR
                ea_rel = p.parent.relative_to(RUNS_DIR)
                ea_name = str(ea_rel) if str(ea_rel) != "." else "unknown"
                break

        if run_id is None:
            # Fallback: use path parts
            if len(parts) >= 2:
                ea_name = parts[0]
                run_id = parts[1]
            else:
                run_id = parts[0] if parts else "unknown"
                ea_name = "unknown"

        # Calculate derived metrics
        start_eq = data.get("start_equity", 10000)
        final_eq = data.get("final_equity", start_eq)
        n_trades = data.get("n_trades", 0)
        net_profit = data.get("net_profit", 0)

        # Estimate years from run_dir config.ini or use 7 as default
        years = _estimate_years(run_dir)
        cagr = _calc_cagr(start_eq, final_eq, years)
        trades_per_year = n_trades / years if years > 0 else 0
        avg_win = abs(data.get("avg_win", 0))
        avg_loss = abs(data.get("avg_loss", 1))
        avg_win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0

        streaks = data.get("streaks", {})

        run_info = {
            "run_id": run_id,
            "ea_name": ea_name,
            "run_dir": str(run_dir),
            "summary_path": str(summary_path),
            "n_trades": n_trades,
            "net_profit": round(net_profit, 2),
            "profit_factor": round(data.get("profit_factor", 0), 3),
            "max_drawdown_pct": round(data.get("max_drawdown_pct", 0), 2),
            "max_drawdown_abs": round(data.get("max_drawdown_abs", 0), 2),
            "win_rate_pct": round(data.get("win_rate_pct", 0), 2),
            "expectancy": round(data.get("expectancy_per_trade", 0), 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "avg_win_loss_ratio": round(avg_win_loss_ratio, 2),
            "start_equity": start_eq,
            "final_equity": final_eq,
            "cagr": round(cagr, 2),
            "trades_per_year": round(trades_per_year, 1),
            "max_win_streak": streaks.get("max_win_streak", 0),
            "max_loss_streak": streaks.get("max_loss_streak", 0),
            "weaknesses_count": data.get("weaknesses_count", 0),
            "years": years,
        }
        runs.append(run_info)

    return runs


def _estimate_years(run_dir: Path) -> float:
    """Try to parse config.ini for date range, fallback to 7 years."""
    config_path = run_dir / "config.ini"
    if not config_path.exists():
        return 7.0
    try:
        # config.ini is UTF-16LE encoded (MT5 style)
        raw = config_path.read_bytes()
        # Try UTF-16 first, then UTF-8
        for enc in ["utf-16", "utf-16-le", "utf-8", "latin-1"]:
            try:
                text = raw.decode(enc)
                break
            except Exception:
                continue
        else:
            return 7.0

        from_date = None
        to_date = None
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("FromDate"):
                from_date = line.split("=", 1)[1].strip()
            elif line.startswith("ToDate"):
                to_date = line.split("=", 1)[1].strip()
        if from_date and to_date:
            d1 = datetime.strptime(from_date, "%Y.%m.%d")
            d2 = datetime.strptime(to_date, "%Y.%m.%d")
            return max((d2 - d1).days / 365.25, 0.5)
    except Exception:
        pass
    return 7.0


def _calc_cagr(start: float, end: float, years: float) -> float:
    if start <= 0 or end <= 0 or years <= 0:
        return 0.0
    return ((end / start) ** (1 / years) - 1) * 100


def load_json(path: str | Path) -> dict | None:
    """Load a JSON file, return None on failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def load_csv(path: str | Path) -> pd.DataFrame | None:
    """Load a CSV file, return None on failure."""
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def find_file_in_run(run_dir: str, filename: str) -> str | None:
    """Search for a file by name within a run directory tree."""
    for p in Path(run_dir).rglob(filename):
        return str(p)
    return None


def _load_optional_gate_data(run_dir: str) -> dict:
    """Load WFA, Monte Carlo, Robustness, Param data from a run."""
    result = {}

    # WFA
    wfa_path = find_file_in_run(run_dir, "wfa_results.json")
    if wfa_path:
        wfa = load_json(wfa_path)
        if wfa and "summary" in wfa:
            result["efficiency_ratio"] = wfa["summary"].get("efficiency_ratio", None)
            result["oos_profitable_ratio"] = wfa["summary"].get("oos_profitable_ratio", None)
            result["wfa_verdict"] = wfa.get("verdict", {}).get("level", "N/A")

    # Monte Carlo
    mc_path = find_file_in_run(run_dir, "monte_carlo_results.json")
    if mc_path:
        mc = load_json(mc_path)
        if mc and "max_drawdown_pct" in mc:
            result["mc_p95_dd"] = mc["max_drawdown_pct"].get("p95", None)
            result["mc_p99_dd"] = mc["max_drawdown_pct"].get("p99", None)
            result["mc_worst_dd"] = mc["max_drawdown_pct"].get("max", None)

    # Robustness
    rob_path = find_file_in_run(run_dir, "robustness_results.json")
    if rob_path:
        rob = load_json(rob_path)
        if rob and "summary" in rob:
            result["pass_rate"] = rob["summary"].get("pass_rate", None)
            result["rob_passed"] = rob["summary"].get("passed", None)
            result["rob_total"] = rob["summary"].get("total", None)
            # Check mandatory tests
            tests = rob.get("tests", {})
            result["rob_vs_random"] = tests.get("vs_random", {}).get("passed", None)
            result["rob_variance"] = tests.get("variance", {}).get("passed", None)

    # Param sensitivity
    param_path = find_file_in_run(run_dir, "sensitivity_results.json")
    if param_path:
        param = load_json(param_path)
        if param:
            result["stability_score"] = param.get("stability_score", None)
            stats = param.get("statistics", {})
            result["param_profitable_pct"] = stats.get("profitable_pct", None)

    return result


# ---------------------------------------------------------------------------
# UI Helpers
# ---------------------------------------------------------------------------

def pf_color(pf: float) -> str:
    if pf >= 1.5:
        return "🟢"
    elif pf >= 1.0:
        return "🟡"
    else:
        return "🔴"


def gate_icon(passed: bool | None) -> str:
    if passed is None:
        return "⚪"  # gray — not available
    return "🟢" if passed else "🔴"


def gate_check(value: float | None, op: str, target: float) -> bool | None:
    if value is None:
        return None
    if op == ">=":
        return value >= target
    elif op == "<=":
        return value <= target
    return None


def format_display_id(run: dict) -> str:
    return f"{run['ea_name']}/{run['run_id']}"


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AlphaFactory Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #333;
    }
    .gate-pass { color: #00ff88; font-weight: bold; }
    .gate-fail { color: #ff4444; font-weight: bold; }
    .gate-na { color: #888888; }
    div[data-testid="stMetric"] {
        background-color: rgba(28, 131, 225, 0.05);
        border: 1px solid rgba(28, 131, 225, 0.1);
        border-radius: 8px;
        padding: 12px 16px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 20px;
        border-radius: 8px 8px 0 0;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.title("📊 AlphaFactory")
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigation",
    ["🏆 Run Leaderboard", "⚖️ Run Comparison", "🎯 PROP_READY Gate", "🧬 Strategy Profile"],
    label_visibility="collapsed",
)

# Load all runs
all_runs = discover_runs()
runs_df = pd.DataFrame(all_runs) if all_runs else pd.DataFrame()

st.sidebar.markdown("---")
st.sidebar.caption(f"📁 {len(all_runs)} runs discovered")
st.sidebar.caption(f"📂 {RUNS_DIR}")

# ===========================================================================
# PAGE 1: Run Leaderboard
# ===========================================================================
if page == "🏆 Run Leaderboard":
    st.title("🏆 Run Leaderboard")

    if runs_df.empty:
        st.warning("No runs found. Check that `02. AlphaFactory/runs/` contains run folders with `analysis/enhanced_summary.json`.")
        st.stop()

    # Sidebar filters
    st.sidebar.markdown("### Filters")
    ea_names = sorted(runs_df["ea_name"].unique())
    selected_ea = st.sidebar.multiselect("EA Name", ea_names, default=ea_names)
    min_pf = st.sidebar.slider("Min Profit Factor", 0.0, 5.0, 0.0, 0.1)
    max_dd = st.sidebar.slider("Max Drawdown %", 0.0, 100.0, 100.0, 1.0)
    min_trades = st.sidebar.number_input("Min Trades", 0, 50000, 0, 50)
    sort_by = st.sidebar.selectbox("Sort by", ["profit_factor", "net_profit", "cagr", "expectancy", "n_trades", "max_drawdown_pct", "win_rate_pct"], index=0)
    sort_asc = st.sidebar.checkbox("Ascending", value=False)

    # Filter
    fdf = runs_df[
        (runs_df["ea_name"].isin(selected_ea))
        & (runs_df["profit_factor"] >= min_pf)
        & (runs_df["max_drawdown_pct"] <= max_dd)
        & (runs_df["n_trades"] >= min_trades)
    ].copy()

    fdf = fdf.sort_values(sort_by, ascending=sort_asc).reset_index(drop=True)

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Runs", len(fdf))
    col2.metric("Best PF", f"{fdf['profit_factor'].max():.3f}" if len(fdf) else "—")
    col3.metric("Best CAGR", f"{fdf['cagr'].max():.1f}%" if len(fdf) else "—")
    col4.metric("Avg Trades", f"{fdf['n_trades'].mean():.0f}" if len(fdf) else "—")

    st.markdown("---")

    # Build display table
    display_cols = ["ea_name", "run_id", "n_trades", "profit_factor", "net_profit",
                    "max_drawdown_pct", "win_rate_pct", "expectancy", "cagr", "trades_per_year",
                    "avg_win_loss_ratio", "max_loss_streak"]

    display_df = fdf[display_cols].copy()
    display_df.insert(0, "⚡", display_df["profit_factor"].apply(pf_color))

    # Rename columns for display
    col_rename = {
        "ea_name": "EA",
        "run_id": "Run ID",
        "n_trades": "Trades",
        "profit_factor": "PF",
        "net_profit": "Net Profit $",
        "max_drawdown_pct": "DD%",
        "win_rate_pct": "Win%",
        "expectancy": "Expect $",
        "cagr": "CAGR%",
        "trades_per_year": "Trades/yr",
        "avg_win_loss_ratio": "W/L Ratio",
        "max_loss_streak": "Max Loss Streak",
    }
    display_df = display_df.rename(columns=col_rename)

    # Color PF column
    def highlight_pf(val):
        if isinstance(val, (int, float)):
            if val >= 1.5:
                return "background-color: rgba(0,200,80,0.25); color: #00ff88"
            elif val >= 1.0:
                return "background-color: rgba(255,200,0,0.2); color: #ffc800"
            else:
                return "background-color: rgba(255,60,60,0.2); color: #ff4444"
        return ""

    styled = display_df.style.applymap(highlight_pf, subset=["PF"])

    st.dataframe(
        styled,
        use_container_width=True,
        height=min(600, 50 + len(display_df) * 35),
    )

    # Expandable details
    st.markdown("### 🔍 Run Details")
    if len(fdf) > 0:
        run_options = {format_display_id(r): i for i, r in fdf.iterrows()}
        selected_label = st.selectbox("Select run to inspect", list(run_options.keys()))
        if selected_label:
            idx = run_options[selected_label]
            run = fdf.loc[idx]
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Profit Factor", f"{run['profit_factor']:.3f}")
                st.metric("Net Profit", f"${run['net_profit']:,.2f}")
                st.metric("CAGR", f"{run['cagr']:.1f}%")
                st.metric("Start Equity", f"${run['start_equity']:,.0f}")
            with c2:
                st.metric("Total Trades", f"{run['n_trades']}")
                st.metric("Win Rate", f"{run['win_rate_pct']:.1f}%")
                st.metric("Expectancy", f"${run['expectancy']:.2f}")
                st.metric("Trades/Year", f"{run['trades_per_year']:.0f}")
            with c3:
                st.metric("Max DD%", f"{run['max_drawdown_pct']:.2f}%")
                st.metric("Max DD Abs", f"${run['max_drawdown_abs']:,.2f}")
                st.metric("W/L Ratio", f"{run['avg_win_loss_ratio']:.2f}")
                st.metric("Max Loss Streak", f"{run['max_loss_streak']}")

            # Show equity chart if available
            eq_img = find_file_in_run(run["run_dir"], "equity_diagnostics.png")
            if eq_img:
                st.image(eq_img, caption="Equity Curve", use_container_width=True)

            # Show weaknesses
            weak_path = find_file_in_run(run["run_dir"], "weaknesses.json")
            if weak_path:
                weaknesses = load_json(weak_path)
                if weaknesses and isinstance(weaknesses, list) and len(weaknesses) > 0:
                    st.markdown("#### ⚠️ Weaknesses")
                    for w in weaknesses:
                        sev = w.get("severity", "")
                        icon = "🔴" if sev == "HIGH" else "🟡" if sev == "MEDIUM" else "⚪"
                        st.markdown(f"{icon} **{w.get('area', '')}** — {w.get('metric', '')} | {w.get('recommendation', '')}")

    # Scatter plot: PF vs DD
    st.markdown("### 📈 PF vs Drawdown")
    if len(fdf) > 1:
        scatter_df = fdf.copy()
        scatter_df["label"] = scatter_df.apply(format_display_id, axis=1)
        fig = px.scatter(
            scatter_df,
            x="max_drawdown_pct",
            y="profit_factor",
            size="n_trades",
            color="ea_name",
            hover_name="label",
            hover_data=["net_profit", "cagr", "win_rate_pct"],
            labels={"max_drawdown_pct": "Max Drawdown %", "profit_factor": "Profit Factor"},
            template="plotly_dark",
        )
        fig.add_hline(y=1.0, line_dash="dash", line_color="red", opacity=0.5)
        fig.add_hline(y=1.5, line_dash="dash", line_color="green", opacity=0.3)
        fig.add_vline(x=8, line_dash="dash", line_color="orange", opacity=0.3)
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)


# ===========================================================================
# PAGE 2: Run Comparison
# ===========================================================================
elif page == "⚖️ Run Comparison":
    st.title("⚖️ Run Comparison")

    if runs_df.empty:
        st.warning("No runs found.")
        st.stop()

    run_labels = {format_display_id(r): i for i, r in runs_df.iterrows()}
    selected = st.multiselect(
        "Select 2-4 runs to compare",
        list(run_labels.keys()),
        max_selections=4,
    )

    if len(selected) < 2:
        st.info("Select at least 2 runs to compare.")
        st.stop()

    comp_runs = [runs_df.iloc[run_labels[s]] for s in selected]

    # Metrics comparison table
    st.markdown("### 📊 Metrics Comparison")
    metrics_to_show = [
        ("Trades", "n_trades", ""),
        ("Profit Factor", "profit_factor", ""),
        ("Net Profit", "net_profit", "$"),
        ("CAGR", "cagr", "%"),
        ("Max DD%", "max_drawdown_pct", "%"),
        ("Win Rate", "win_rate_pct", "%"),
        ("Expectancy", "expectancy", "$"),
        ("Avg W/L Ratio", "avg_win_loss_ratio", ""),
        ("Trades/Year", "trades_per_year", ""),
        ("Max Loss Streak", "max_loss_streak", ""),
        ("Start Equity", "start_equity", "$"),
        ("Final Equity", "final_equity", "$"),
    ]

    comp_data = {"Metric": [m[0] for m in metrics_to_show]}
    for run in comp_runs:
        col_name = f"{run['ea_name']}/{run['run_id']}"
        values = []
        for _, key, suffix in metrics_to_show:
            val = run.get(key, "—")
            if isinstance(val, float):
                if suffix == "$":
                    values.append(f"${val:,.2f}")
                elif suffix == "%":
                    values.append(f"{val:.2f}%")
                else:
                    values.append(f"{val:.3f}" if key == "profit_factor" else f"{val:.1f}")
            else:
                values.append(str(val))
        comp_data[col_name] = values

    st.dataframe(pd.DataFrame(comp_data).set_index("Metric"), use_container_width=True)

    # Equity curves
    st.markdown("### 📈 Equity Curves")
    has_any_equity = False
    cols = st.columns(min(len(comp_runs), 4))
    for i, run in enumerate(comp_runs):
        eq_img = find_file_in_run(run["run_dir"], "equity_diagnostics.png")
        if eq_img:
            has_any_equity = True
            with cols[i % len(cols)]:
                st.image(eq_img, caption=f"{run['ea_name']}/{run['run_id']}", use_container_width=True)
    if not has_any_equity:
        st.info("No equity curve images available for selected runs.")

    # Yearly breakdown comparison
    st.markdown("### 📅 Yearly Breakdown Comparison")
    yearly_dfs = []
    for run in comp_runs:
        yb_path = find_file_in_run(run["run_dir"], "yearly_breakdown.csv")
        if yb_path:
            df = load_csv(yb_path)
            if df is not None and "year" in df.columns:
                df["run"] = f"{run['ea_name']}/{run['run_id']}"
                yearly_dfs.append(df)

    if yearly_dfs:
        yearly_all = pd.concat(yearly_dfs, ignore_index=True)

        # Net profit by year
        if "net_profit" in yearly_all.columns:
            fig = px.bar(
                yearly_all,
                x="year",
                y="net_profit",
                color="run",
                barmode="group",
                title="Net Profit by Year",
                template="plotly_dark",
                labels={"net_profit": "Net Profit $", "year": "Year"},
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

        # PF by year
        if "profit_factor" in yearly_all.columns:
            fig2 = px.bar(
                yearly_all,
                x="year",
                y="profit_factor",
                color="run",
                barmode="group",
                title="Profit Factor by Year",
                template="plotly_dark",
                labels={"profit_factor": "Profit Factor", "year": "Year"},
            )
            fig2.add_hline(y=1.0, line_dash="dash", line_color="red", opacity=0.5)
            fig2.update_layout(height=400)
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No yearly breakdown data available for selected runs.")

    # Session / Weekday / Hour comparison
    for breakdown_name, filename, x_col in [
        ("Session", "by_session.csv", "session"),
        ("Weekday", "by_weekday.csv", "weekday"),
        ("Hour", "by_hour.csv", "hour"),
    ]:
        st.markdown(f"### 🕐 {breakdown_name} Breakdown")
        bd_dfs = []
        for run in comp_runs:
            bd_path = find_file_in_run(run["run_dir"], filename)
            if bd_path:
                df = load_csv(bd_path)
                if df is not None and x_col in df.columns:
                    df["run"] = f"{run['ea_name']}/{run['run_id']}"
                    bd_dfs.append(df)

        if bd_dfs:
            bd_all = pd.concat(bd_dfs, ignore_index=True)
            # Filter out zero-trade rows
            if "n" in bd_all.columns:
                bd_all = bd_all[bd_all["n"] > 0]

            if len(bd_all) > 0 and "net_profit" in bd_all.columns:
                fig = px.bar(
                    bd_all,
                    x=x_col,
                    y="net_profit",
                    color="run",
                    barmode="group",
                    title=f"Net Profit by {breakdown_name}",
                    template="plotly_dark",
                )
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"No {breakdown_name.lower()} data with trades found.")
        else:
            st.info(f"No {breakdown_name.lower()} breakdown files found.")


# ===========================================================================
# PAGE 3: PROP_READY Gate Check
# ===========================================================================
elif page == "🎯 PROP_READY Gate":
    st.title("🎯 PROP_READY Gate Check")

    if runs_df.empty:
        st.warning("No runs found.")
        st.stop()

    run_labels = {format_display_id(r): i for i, r in runs_df.iterrows()}
    selected = st.selectbox("Select run", list(run_labels.keys()))

    if not selected:
        st.stop()

    run = runs_df.iloc[run_labels[selected]]
    run_dir = run["run_dir"]

    # Load optional data
    opt_data = _load_optional_gate_data(run_dir)

    st.markdown("---")

    # Header metrics
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("PF", f"{run['profit_factor']:.3f}")
    c2.metric("CAGR", f"{run['cagr']:.1f}%")
    c3.metric("DD%", f"{run['max_drawdown_pct']:.2f}%")
    c4.metric("Trades", f"{run['n_trades']}")
    c5.metric("Net $", f"${run['net_profit']:,.0f}")

    st.markdown("---")
    st.markdown("### Core Gates")

    passed_count = 0
    failed_count = 0
    na_count = 0

    gate_results = []

    # Core gates
    for gate_name, gate_cfg in PROP_GATES.items():
        val = run.get(gate_cfg["key"])
        result = gate_check(val, gate_cfg["op"], gate_cfg["target"])
        icon = gate_icon(result)
        if result is True:
            passed_count += 1
        elif result is False:
            failed_count += 1
        else:
            na_count += 1
        display_val = f"{val:.2f}" if isinstance(val, float) else str(val)
        gate_results.append((icon, gate_name, display_val, gate_cfg["target"], result))

    # Display core gates in 2 columns
    col_left, col_right = st.columns(2)
    for i, (icon, name, val, target, result) in enumerate(gate_results):
        col = col_left if i % 2 == 0 else col_right
        status = "PASS" if result else "FAIL" if result is False else "N/A"
        col.markdown(f"{icon} **{name}** → `{val}` (target: `{target}`) — **{status}**")

    st.markdown("---")
    st.markdown("### Robustness Gates")

    opt_gate_results = []
    for gate_name, gate_cfg in PROP_GATES_OPTIONAL.items():
        val = opt_data.get(gate_cfg["key"])
        result = gate_check(val, gate_cfg["op"], gate_cfg["target"])
        icon = gate_icon(result)
        if result is True:
            passed_count += 1
        elif result is False:
            failed_count += 1
        else:
            na_count += 1
        if val is not None:
            display_val = f"{val:.2f}" if isinstance(val, float) else str(val)
        else:
            display_val = "N/A"
        opt_gate_results.append((icon, gate_name, display_val, gate_cfg["target"], result))

    col_left2, col_right2 = st.columns(2)
    for i, (icon, name, val, target, result) in enumerate(opt_gate_results):
        col = col_left2 if i % 2 == 0 else col_right2
        status = "PASS" if result else "FAIL" if result is False else "N/A"
        col.markdown(f"{icon} **{name}** → `{val}` (target: `{target}`) — **{status}**")

    # Mandatory robustness checks
    st.markdown("---")
    st.markdown("### Mandatory Robustness Sub-checks")
    rob_vs_random = opt_data.get("rob_vs_random")
    rob_variance = opt_data.get("rob_variance")

    c1, c2 = st.columns(2)
    c1.markdown(f"{gate_icon(rob_vs_random)} **Vs Random** — {'PASS' if rob_vs_random else 'FAIL' if rob_vs_random is False else 'N/A'}")
    c2.markdown(f"{gate_icon(rob_variance)} **Variance CI** — {'PASS' if rob_variance else 'FAIL' if rob_variance is False else 'N/A'}")

    if rob_vs_random is False:
        failed_count += 1  # mandatory gate
    elif rob_vs_random is True:
        passed_count += 1
    if rob_variance is False:
        failed_count += 1  # mandatory gate
    elif rob_variance is True:
        passed_count += 1

    # Overall verdict
    st.markdown("---")
    total = passed_count + failed_count + na_count

    if failed_count == 0 and na_count == 0:
        verdict = "✅ PASS"
        verdict_color = "green"
        verdict_desc = "All gates passed. Strategy meets PROP_READY requirements."
    elif failed_count == 0 and na_count > 0:
        verdict = "🟡 CONDITIONAL"
        verdict_color = "orange"
        verdict_desc = f"Core gates passed, but {na_count} gates have no data. Run missing analyses."
    else:
        verdict = "🔴 FAIL"
        verdict_color = "red"
        verdict_desc = f"{failed_count} gate(s) failed. Strategy NOT ready for prop."

    st.markdown(f"""
    <div style="text-align: center; padding: 24px; border-radius: 12px;
                border: 2px solid {verdict_color}; margin: 16px 0;">
        <h1 style="color: {verdict_color}; margin: 0;">{verdict}</h1>
        <p style="margin: 8px 0 0 0; font-size: 1.1em;">{verdict_desc}</p>
        <p style="margin: 4px 0 0 0; color: #888;">
            🟢 {passed_count} passed &nbsp; | &nbsp; 🔴 {failed_count} failed &nbsp; | &nbsp; ⚪ {na_count} N/A
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Gate summary bar
    if total > 0:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=[passed_count], y=["Gates"], orientation="h",
                             name="Pass", marker_color="#00ff88", text=[passed_count], textposition="inside"))
        fig.add_trace(go.Bar(x=[failed_count], y=["Gates"], orientation="h",
                             name="Fail", marker_color="#ff4444", text=[failed_count], textposition="inside"))
        fig.add_trace(go.Bar(x=[na_count], y=["Gates"], orientation="h",
                             name="N/A", marker_color="#666666", text=[na_count], textposition="inside"))
        fig.update_layout(barmode="stack", template="plotly_dark", height=120,
                          margin=dict(l=0, r=0, t=0, b=0), showlegend=True,
                          legend=dict(orientation="h", yanchor="bottom", y=1.02))
        st.plotly_chart(fig, use_container_width=True)


# ===========================================================================
# PAGE 4: Strategy Character Profile
# ===========================================================================
elif page == "🧬 Strategy Profile":
    st.title("🧬 Strategy Character Profile")

    if runs_df.empty:
        st.warning("No runs found.")
        st.stop()

    run_labels = {format_display_id(r): i for i, r in runs_df.iterrows()}
    selected = st.selectbox("Select run", list(run_labels.keys()))

    if not selected:
        st.stop()

    run = runs_df.iloc[run_labels[selected]]
    run_dir = run["run_dir"]

    # Load TCA
    tca_path = find_file_in_run(run_dir, "tca_summary.json")
    tca = load_json(tca_path) if tca_path else None

    # Load trades summary
    trades_path = find_file_in_run(run_dir, "trades_summary.json")
    trades_data = load_json(trades_path) if trades_path else None

    # Load breakdowns
    session_path = find_file_in_run(run_dir, "by_session.csv")
    session_df = load_csv(session_path) if session_path else None

    weekday_path = find_file_in_run(run_dir, "by_weekday.csv")
    weekday_df = load_csv(weekday_path) if weekday_path else None

    hour_path = find_file_in_run(run_dir, "by_hour.csv")
    hour_df = load_csv(hour_path) if hour_path else None

    # ---- Character Summary ----
    st.markdown("### 🏷️ Character Summary")

    run_meta = tca.get("run_meta", {}) if tca else {}
    close_sources = run_meta.get("close_sources", {})
    mean_hold = run_meta.get("mean_hold_minutes", 0)
    n_trades = run.get("n_trades", 0)

    # Determine type
    if mean_hold > 0 and mean_hold < 60:
        strat_type = "⚡ Scalp"
    elif mean_hold < 1440:
        strat_type = "📊 Intraday"
    elif mean_hold < 7200:
        strat_type = "📈 Swing"
    elif mean_hold > 0:
        strat_type = "🏦 Position"
    else:
        strat_type = "❓ Unknown"

    # Hold time human readable
    if mean_hold > 0:
        hours = mean_hold / 60
        if hours >= 24:
            hold_str = f"{hours/24:.1f} days ({mean_hold:.0f} min)"
        elif hours >= 1:
            hold_str = f"{hours:.1f} hours ({mean_hold:.0f} min)"
        else:
            hold_str = f"{mean_hold:.0f} min"
    else:
        hold_str = "N/A"

    # Friday flatten check
    friday_count = close_sources.get("friday_flatten", 0)
    has_friday = friday_count > 0
    weekend_hold = "No" if has_friday else "Possible"

    # TP hit rate
    tp_count = close_sources.get("take_profit", 0)
    tp_rate = (tp_count / n_trades * 100) if n_trades > 0 else 0

    # Scale-in (heuristic: check trades data or exec data for overlapping positions)
    # Without detailed exec data, we check tca exec section
    exec_data = tca.get("exec", {}) if tca else {}
    max_open = 1  # default
    phase_counts = exec_data.get("phase_counts", [])
    has_scale_in = "Unknown"

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Strategy Type", strat_type)
        st.metric("Avg Hold Time", hold_str)
    with col2:
        st.metric("Weekend Hold", weekend_hold)
        st.metric("TP Hit Rate", f"{tp_rate:.1f}%")
    with col3:
        st.metric("Friday Flatten", f"{friday_count} trades" if has_friday else "N/A")
        sqn = run_meta.get("sqn", 0)
        st.metric("SQN", f"{sqn:.2f}" if sqn else "N/A")

    st.markdown("---")

    # ---- Close Source Pie Chart ----
    if close_sources:
        st.markdown("### 🎯 Close Source Distribution")
        cs_filtered = {k: v for k, v in close_sources.items() if v > 0}
        if cs_filtered:
            # Friendly labels
            label_map = {
                "stop_loss": "Stop Loss",
                "take_profit": "Take Profit",
                "friday_flatten": "Friday Flatten",
                "market_exit": "Market Exit",
                "news_guard": "News Guard",
                "manual_close": "Manual Close",
                "stop_out": "Stop Out",
                "other": "Other",
            }
            labels = [label_map.get(k, k) for k in cs_filtered.keys()]
            values = list(cs_filtered.values())

            colors = {
                "Stop Loss": "#ff4444",
                "Take Profit": "#00ff88",
                "Friday Flatten": "#ffa500",
                "Market Exit": "#4488ff",
                "News Guard": "#aa44ff",
                "Manual Close": "#888888",
                "Stop Out": "#ff0000",
                "Other": "#666666",
            }
            color_list = [colors.get(l, "#888888") for l in labels]

            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=0.45,
                marker=dict(colors=color_list),
                textinfo="label+percent",
                textposition="outside",
            )])
            fig.update_layout(
                template="plotly_dark",
                height=400,
                showlegend=True,
                margin=dict(l=20, r=20, t=10, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Close source data not available (EA may not have DataLog enabled).")

    # ---- Achieved R Distribution ----
    st.markdown("### 📊 Achieved R Distribution")
    trades_section = tca.get("trades", {}) if tca else {}
    achieved_r = trades_section.get("achieved_r", {})
    if achieved_r and achieved_r.get("n", 0) > 0:
        # Show summary stats
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Count", achieved_r.get("n", "—"))
        c2.metric("Mean R", f"{achieved_r.get('mean', 0):.3f}")
        c3.metric("P10", f"{achieved_r.get('p10', 0):.3f}")
        c4.metric("P90", f"{achieved_r.get('p90', 0):.3f}")

        # Build a synthetic histogram from percentile data
        r_data = achieved_r
        if r_data.get("n", 0) > 0:
            st.caption("ℹ️ Distribution approximated from summary statistics. Full trade-level data would provide exact histogram.")
            # Show net profit distribution too
            net_prof = trades_section.get("net_profit", {})
            if net_prof and net_prof.get("n", 0) > 0:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Mean P/L", f"${net_prof.get('mean', 0):.2f}")
                c2.metric("P10 P/L", f"${net_prof.get('p10', 0):.2f}")
                c3.metric("Median P/L", f"${net_prof.get('p50', 0):.2f}")
                c4.metric("P90 P/L", f"${net_prof.get('p90', 0):.2f}")
    else:
        st.info("Achieved R distribution not available.")

    # ---- Session Breakdown ----
    st.markdown("### 🌍 Session Breakdown")
    if session_df is not None and "session" in session_df.columns:
        sdf = session_df[session_df["n"] > 0].copy() if "n" in session_df.columns else session_df
        if len(sdf) > 0:
            fig = make_subplots(rows=1, cols=2, subplot_titles=["Net Profit by Session", "Win Rate by Session"])

            fig.add_trace(
                go.Bar(x=sdf["session"], y=sdf["net_profit"],
                       marker_color=sdf["net_profit"].apply(lambda x: "#00ff88" if x > 0 else "#ff4444"),
                       name="Net Profit", showlegend=False),
                row=1, col=1,
            )
            if "win_rate_pct" in sdf.columns:
                fig.add_trace(
                    go.Bar(x=sdf["session"], y=sdf["win_rate_pct"],
                           marker_color="#4488ff", name="Win Rate %", showlegend=False),
                    row=1, col=2,
                )
                fig.add_hline(y=50, line_dash="dash", line_color="white", opacity=0.3, row=1, col=2)

            fig.update_layout(template="plotly_dark", height=350, margin=dict(t=40))
            st.plotly_chart(fig, use_container_width=True)

            # Session table
            st.dataframe(sdf, use_container_width=True, hide_index=True)
        else:
            st.info("No session data with trades.")
    else:
        st.info("Session breakdown not available.")

    # ---- Weekday Breakdown ----
    st.markdown("### 📅 Weekday Breakdown")
    if weekday_df is not None and "weekday" in weekday_df.columns:
        wdf = weekday_df[weekday_df["n"] > 0].copy() if "n" in weekday_df.columns else weekday_df
        if len(wdf) > 0:
            day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            wdf["weekday"] = pd.Categorical(wdf["weekday"], categories=day_order, ordered=True)
            wdf = wdf.sort_values("weekday")

            fig = make_subplots(rows=1, cols=2, subplot_titles=["Net Profit by Weekday", "Win Rate by Weekday"])

            fig.add_trace(
                go.Bar(x=wdf["weekday"], y=wdf["net_profit"],
                       marker_color=wdf["net_profit"].apply(lambda x: "#00ff88" if x > 0 else "#ff4444"),
                       name="Net Profit", showlegend=False),
                row=1, col=1,
            )
            if "win_rate_pct" in wdf.columns:
                fig.add_trace(
                    go.Bar(x=wdf["weekday"], y=wdf["win_rate_pct"],
                           marker_color="#ffa500", name="Win Rate %", showlegend=False),
                    row=1, col=2,
                )
                fig.add_hline(y=50, line_dash="dash", line_color="white", opacity=0.3, row=1, col=2)

            fig.update_layout(template="plotly_dark", height=350, margin=dict(t=40))
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(wdf, use_container_width=True, hide_index=True)
        else:
            st.info("No weekday data with trades.")
    else:
        st.info("Weekday breakdown not available.")

    # ---- Hour Breakdown ----
    st.markdown("### ⏰ Hourly Breakdown")
    if hour_df is not None and "hour" in hour_df.columns:
        hdf = hour_df[hour_df["n"] > 0].copy() if "n" in hour_df.columns else hour_df
        if len(hdf) > 0:
            hdf = hdf.sort_values("hour")

            fig = make_subplots(rows=1, cols=2, subplot_titles=["Net Profit by Hour", "Trade Count by Hour"])

            fig.add_trace(
                go.Bar(x=hdf["hour"], y=hdf["net_profit"],
                       marker_color=hdf["net_profit"].apply(lambda x: "#00ff88" if x > 0 else "#ff4444"),
                       name="Net Profit", showlegend=False),
                row=1, col=1,
            )
            fig.add_trace(
                go.Bar(x=hdf["hour"], y=hdf["n"],
                       marker_color="#8844ff", name="Trades", showlegend=False),
                row=1, col=2,
            )

            fig.update_layout(template="plotly_dark", height=350, margin=dict(t=40))
            fig.update_xaxes(dtick=1, row=1, col=1)
            fig.update_xaxes(dtick=1, row=1, col=2)
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(hdf, use_container_width=True, hide_index=True)
        else:
            st.info("No hourly data with trades.")
    else:
        st.info("Hourly breakdown not available.")

    # ---- Equity Image ----
    eq_img = find_file_in_run(run_dir, "equity_diagnostics.png")
    if eq_img:
        st.markdown("### 📈 Equity Curve")
        st.image(eq_img, use_container_width=True)
