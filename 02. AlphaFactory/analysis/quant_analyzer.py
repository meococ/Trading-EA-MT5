#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Heroic Quant Analyzer

Why?
- MT5 report gives headline metrics, but we need robustness diagnostics:
  rolling performance, trade distribution, streaks, Monte Carlo DD, etc.
- This script parses MT5 HTML report (ReportTester-*.html) and outputs:
  trades.csv, summary.json, monte_carlo.csv.

Design goals:
- Minimal dependencies (standard library only).
- Deterministic, transparent calculations (no "magic").

Usage (Windows PowerShell):
  python EA\\Heroic\\analysis\\heroic_quant_analyzer.py --report "AlphaFactory/04_LegacyDump/EA_Heroic_Backtest_legacy/ReportTester-98589835.html"
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import datetime as dt
import hashlib
import json
import math
import random
import re
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


@dataclasses.dataclass(frozen=True)
class Deal:
    time: dt.datetime
    deal_id: int
    symbol: str
    side: str           # "buy" / "sell" / "balance" ...
    direction: str      # "in" / "out" / "" (for balance)
    volume: float
    price: float
    order_id: Optional[int]
    commission: float
    swap: float
    profit: float
    balance: float
    comment: str


@dataclasses.dataclass(frozen=True)
class Trade:
    entry_time: dt.datetime
    exit_time: dt.datetime
    side: str  # buy/sell (entry side)
    profit: float
    n_out_deals: int
    exit_comment: str
    entry_comment: str

    @property
    def duration_minutes(self) -> float:
        return (self.exit_time - self.entry_time).total_seconds() / 60.0


def file_fingerprint(path: Path) -> dict:
    """
    Why?
    - Avoid analysis/report mismatch (common when users overwrite reports but keep same filename).
    - Make outputs auditable and reproducible.
    """
    raw = path.read_bytes()
    h = hashlib.sha256(raw).hexdigest()
    st = path.stat()
    return {
        "path": str(path),
        "sha256": h,
        "bytes": st.st_size,
        "mtime_utc": dt.datetime.fromtimestamp(st.st_mtime, dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
    }


def _parse_mt5_dt(s: str) -> dt.datetime:
    # Format: "2020.01.03 14:30:00"
    return dt.datetime.strptime(s.strip(), "%Y.%m.%d %H:%M:%S")


def _parse_number(s: str) -> float:
    # MT5 uses spaces as thousand separators: "10 000.00"
    ss = s.strip().replace(" ", "")
    if ss == "":
        return 0.0
    return float(ss)


def _extract_section_by_regex(html: str, start_re: re.Pattern) -> str:
    """Return substring starting at first regex match until next </table> after it."""
    m = start_re.search(html)
    if not m:
        raise ValueError(f"Marker regex not found: {start_re.pattern!r}")
    tail = html[m.start() :]
    end = tail.find("</table>")
    if end < 0:
        raise ValueError("Malformed report: missing </table> after marker")
    return tail[: end + len("</table>")]


def _decode_report_bytes(raw: bytes) -> str:
    # MT5 reports can be UTF-8 or UTF-16 depending on locale/build/export.
    if raw.startswith(b"\xff\xfe"):
        return raw.decode("utf-16-le", errors="ignore")
    if raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16-be", errors="ignore")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig", errors="ignore")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        # Fallback (rare)
        return raw.decode("cp1252", errors="ignore")


def parse_deals_from_html_report(report_path: Path) -> List[Deal]:
    # MT5 reports can be UTF-8 or UTF-16 depending on locale/build/export.
    raw = report_path.read_bytes()
    html = _decode_report_bytes(raw)

    # Deals table marker appears as: <b>Deals</b> (case-insensitive, allow whitespace/newlines)
    section = _extract_section_by_regex(html, re.compile(r"<b>\s*Deals\s*</b>", re.IGNORECASE))

    # Extract <tr>...</tr> rows after the header row.
    tr_re = re.compile(r"<tr[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
    td_re = re.compile(r"<td[^>]*>(.*?)</td>", re.IGNORECASE | re.DOTALL)

    rows = tr_re.findall(section)
    deals: List[Deal] = []
    for row in rows:
        tds = [re.sub(r"<[^>]+>", "", td).strip() for td in td_re.findall(row)]
        if not tds:
            continue
        # Header row contains labels like "Thời gian"
        if tds[0].lower().startswith("thời gian") or tds[0].lower().startswith("time"):
            continue

        # Expected columns (13):
        # 0 time, 1 deal, 2 symbol, 3 type, 4 dir, 5 vol, 6 price, 7 order,
        # 8 fee, 9 swap, 10 profit, 11 balance, 12 comment
        if len(tds) < 13:
            # Sometimes MT5 can emit shorter rows; skip conservatively.
            continue

        time_s = tds[0]
        deal_id_s = tds[1]
        symbol = tds[2]
        side = tds[3]
        direction = tds[4]

        volume = _parse_number(tds[5]) if tds[5] else 0.0
        price = _parse_number(tds[6]) if tds[6] else 0.0
        order_id = int(tds[7]) if tds[7].strip().isdigit() else None
        commission = _parse_number(tds[8])
        swap = _parse_number(tds[9])
        profit = _parse_number(tds[10])
        balance = _parse_number(tds[11])
        comment = tds[12]

        deal = Deal(
            time=_parse_mt5_dt(time_s),
            deal_id=int(deal_id_s) if deal_id_s.strip().isdigit() else -1,
            symbol=symbol,
            side=side,
            direction=direction,
            volume=volume,
            price=price,
            order_id=order_id,
            commission=commission,
            swap=swap,
            profit=profit,
            balance=balance,
            comment=comment,
        )
        deals.append(deal)

    # Sort by time then deal_id for deterministic sequencing
    deals.sort(key=lambda d: (d.time, d.deal_id))
    return deals


def parse_deals_from_md_report(report_path: Path) -> List[Deal]:
    """
    Parse deals from plain-text MT5 export (like `AlphaFactory/04_LegacyDump/EA_Heroic_Backtest_legacy/Backtest ea.MD` in this repo).
    Expected section format:
      Deals
      Time  Deal  Symbol  Type  Direction  Volume  Price  Order  Commission  Swap  Profit  Balance  Comment
      2020.01.01 00:00:00 ...
    Columns are TAB-separated.
    """
    raw = report_path.read_bytes()
    text = _decode_report_bytes(raw)
    lines = [ln.rstrip("\n\r") for ln in text.splitlines()]

    # Find "Deals" marker line
    marker_idx = -1
    for i, ln in enumerate(lines):
        if re.match(r"^\s*Deals\s*$", ln, flags=re.IGNORECASE):
            marker_idx = i
            break
    if marker_idx < 0:
        raise ValueError("Deals section not found in MD report")

    # Header is the next non-empty line
    j = marker_idx + 1
    while j < len(lines) and lines[j].strip() == "":
        j += 1
    if j >= len(lines):
        raise ValueError("Malformed MD report: missing Deals header row")

    header = [h.strip().lower() for h in lines[j].split("\t")]
    if len(header) < 10:
        raise ValueError("Malformed MD report: Deals header has too few columns")

    # We will use positional parse like MT5 standard export (13 cols), but tolerate extra cols.
    deals: List[Deal] = []
    for k in range(j + 1, len(lines)):
        ln = lines[k]
        if ln.strip() == "":
            # Stop at first blank line after data (common in exports)
            continue
        if re.match(r"^\s*(Orders|Lịch sử|History|Graph)\s*$", ln, flags=re.IGNORECASE):
            break
        if not re.match(r"^\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2}\t", ln):
            continue

        cols = [c.strip() for c in ln.split("\t")]
        if len(cols) < 12:
            continue

        # Pad to 13 columns
        while len(cols) < 13:
            cols.append("")

        time_s = cols[0]
        deal_id_s = cols[1]
        symbol = cols[2]
        side = cols[3]
        direction = cols[4]
        volume = _parse_number(cols[5]) if cols[5] else 0.0
        price = _parse_number(cols[6]) if cols[6] else 0.0
        order_id = int(cols[7]) if cols[7].strip().isdigit() else None
        commission = _parse_number(cols[8])
        swap = _parse_number(cols[9])
        profit = _parse_number(cols[10])
        balance = _parse_number(cols[11])
        comment = cols[12]

        deals.append(
            Deal(
                time=_parse_mt5_dt(time_s),
                deal_id=int(deal_id_s) if deal_id_s.strip().isdigit() else -1,
                symbol=symbol,
                side=side,
                direction=direction,
                volume=volume,
                price=price,
                order_id=order_id,
                commission=commission,
                swap=swap,
                profit=profit,
                balance=balance,
                comment=comment,
            )
        )

    deals.sort(key=lambda d: (d.time, d.deal_id))
    return deals


def parse_deals(report_path: Path) -> List[Deal]:
    suffix = report_path.suffix.lower()
    if suffix in (".html", ".htm"):
        return parse_deals_from_html_report(report_path)
    if suffix in (".md", ".txt"):
        return parse_deals_from_md_report(report_path)
    # Try MD parser as a fallback (plain text exports often have no extension)
    return parse_deals_from_md_report(report_path)


def deals_to_trades(deals: List[Deal]) -> List[Trade]:
    """
    Convert MT5 deals into approximate trade objects without assuming one position at a time.

    Matching policy:
    - Track open `in` deals as position inventory.
    - Match each `out` deal FIFO against open inventory on the same symbol.
    - Prefer the opposite entry side (e.g. `sell/out` closes prior `buy/in`).
    - Support partial exits by allocating exit profit proportionally by closed volume.

    This is still a heuristic because MT5 HTML reports do not expose all position-linking
    fields directly in the parsed structure here, but it is materially safer than the old
    one-position-at-a-time segmentation for overlapping or partial-close workflows.
    """
    trades: List[Trade] = []
    open_positions = []
    eps = 1e-9

    def _emit_trade(pos) -> None:
        entry_deal = pos["entry"]
        out_deals = pos["outs"]
        # Include swap + commission in trade P&L (v6.2 fix — previously only used raw profit)
        profit = sum(x.profit + x.swap + x.commission for x in out_deals)
        # Also add entry-side commission (MT5 charges commission on entry deal too)
        profit += entry_deal.commission
        exit_time = out_deals[-1].time if out_deals else entry_deal.time
        exit_comment = out_deals[-1].comment if out_deals else ""
        trades.append(
            Trade(
                entry_time=entry_deal.time,
                exit_time=exit_time,
                side=entry_deal.side,
                profit=profit,
                n_out_deals=len(out_deals),
                exit_comment=exit_comment,
                entry_comment=entry_deal.comment,
            )
        )

    def _target_entry_side_for_out(deal: Deal) -> Optional[str]:
        side = (deal.side or "").strip().lower()
        if side == "sell":
            return "buy"
        if side == "buy":
            return "sell"
        return None

    for d in deals:
        side = (d.side or "").strip().lower()
        direction = (d.direction or "").strip().lower()
        if side == "balance":
            continue

        if direction == "in":
            open_positions.append(
                {
                    "entry": d,
                    "remaining": abs(d.volume),
                    "outs": [],
                }
            )
            continue

        if direction != "out":
            continue

        remaining_out = abs(d.volume)
        if remaining_out <= eps:
            continue

        target_side = _target_entry_side_for_out(d)

        while remaining_out > eps and open_positions:
            pos_index = None
            for i, pos in enumerate(open_positions):
                if pos["entry"].symbol != d.symbol:
                    continue
                if target_side is not None and (pos["entry"].side or "").strip().lower() != target_side:
                    continue
                pos_index = i
                break

            if pos_index is None:
                for i, pos in enumerate(open_positions):
                    if pos["entry"].symbol == d.symbol:
                        pos_index = i
                        break
            if pos_index is None:
                break

            pos = open_positions[pos_index]
            alloc = min(pos["remaining"], remaining_out)
            ratio = (alloc / abs(d.volume)) if abs(d.volume) > eps else 1.0
            alloc_deal = dataclasses.replace(
                d,
                volume=alloc,
                profit=d.profit * ratio,
                commission=d.commission * ratio,
                swap=d.swap * ratio,
            )
            pos["outs"].append(alloc_deal)
            pos["remaining"] -= alloc
            remaining_out -= alloc

            if pos["remaining"] <= eps:
                _emit_trade(pos)
                open_positions.pop(pos_index)

    for pos in open_positions:
        _emit_trade(pos)

    # Filter out empty artifacts (if any)
    return [t for t in trades if t.entry_time != t.exit_time or t.profit != 0.0]


def compute_max_drawdown(equity: Iterable[float]) -> Tuple[float, float]:
    """Return (max_dd_abs, max_dd_pct) based on equity curve."""
    peak = -math.inf
    max_dd = 0.0
    max_dd_pct = 0.0
    for x in equity:
        peak = max(peak, x)
        dd = peak - x
        if dd > max_dd:
            max_dd = dd
            max_dd_pct = (dd / peak * 100.0) if peak > 0 else 0.0
    return max_dd, max_dd_pct


def profit_factor(trades: List[Trade]) -> float:
    gross_profit = sum(t.profit for t in trades if t.profit > 0)
    gross_loss = -sum(t.profit for t in trades if t.profit < 0)
    return (gross_profit / gross_loss) if gross_loss > 0 else 999.99  # v11.2: cap to avoid NaN


def bucket_stats(trades: List[Trade]) -> dict:
    profits = [t.profit for t in trades]
    wins = [p for p in profits if p > 0]
    losses = [p for p in profits if p < 0]

    gp = sum(wins)
    gl = -sum(losses)
    pf = (gp / gl) if gl > 0 else 999.99  # v11.2: cap to avoid NaN
    win_rate = (len(wins) / len(profits) * 100.0) if profits else 0.0
    avg_win = (sum(wins) / len(wins)) if wins else 0.0
    avg_loss = (sum(losses) / len(losses)) if losses else 0.0

    # Drawdown within the bucket (starting at 0).
    # NOTE: Percent DD at bucket-level is NOT meaningful (depends on bucket net/peak),
    # so we export ABS drawdown only.
    eq = []
    cur = 0.0
    for p in profits:
        cur += p
        eq.append(cur)
    dd_abs, _ = compute_max_drawdown([x + 1e-9 for x in eq])  # tiny offset to avoid peak==0

    return {
        "n": len(profits),
        "net_profit": sum(profits),
        "win_rate_pct": win_rate,
        "profit_factor": pf,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "max_dd_abs": dd_abs,
    }


def infer_exit_tag(t: Trade) -> str:
    c = (t.exit_comment or "").strip().lower()
    if c.startswith("sl"):
        return "sl"
    if c.startswith("tp"):
        return "tp"
    # Check exit_comment for specific exit types
    if "usclose" in c or "us_close" in c:
        return "close_22"
    if "hardexit" in c or "hard_exit" in c:
        return "hard_exit"
    if "rescue" in c:
        return "rescue"
    if "fridayclose" in c or "friday_close" in c:
        return "friday_close"
    # Time-based inference (fallback)
    if t.exit_time.hour in (22, 23) and t.exit_time.minute == 0 and t.exit_time.second == 0:
        return "close_22"
    if t.exit_time.weekday() == 4 and t.exit_time.hour >= 22:
        return "friday_close"
    if c:
        return "other_comment"
    # No comment = likely trailing SL hit or manual close
    return "trailing_sl"


def group_trades_by_exit(trades: List[Trade], key_func) -> List[tuple]:
    buckets = {}
    for t in trades:
        k = key_func(t.exit_time)
        buckets.setdefault(k, []).append(t)
    return [(k, buckets[k]) for k in sorted(buckets)]


def group_trades_by_entry_comment(trades: List[Trade]) -> List[tuple]:
    buckets = {}
    for t in trades:
        k = (t.entry_comment or "").strip()
        if not k:
            k = "UNKNOWN"
        buckets.setdefault(k, []).append(t)
    # Sort by net profit descending for quick signal
    def net_profit(ts: List[Trade]) -> float:
        return sum(x.profit for x in ts)
    return sorted(buckets.items(), key=lambda kv: net_profit(kv[1]), reverse=True)


def monte_carlo(trade_profits: List[float], start_equity: float, n_sims: int, seed: int = 42) -> List[dict]:
    rnd = random.Random(seed)
    res: List[dict] = []
    n = len(trade_profits)
    for i in range(n_sims):
        seq = [trade_profits[rnd.randrange(n)] for _ in range(n)]
        equity_curve = []
        cur = start_equity
        min_equity = start_equity
        for p in seq:
            cur += p
            equity_curve.append(cur)
            if cur < min_equity:
                min_equity = cur
        dd_abs, dd_pct = compute_max_drawdown(equity_curve)
        min_pct_from_initial = (min_equity / start_equity - 1.0) * 100.0 if start_equity else 0.0
        res.append(
            {
                "sim": i,
                "final_equity": cur,
                "max_dd_abs": dd_abs,
                "max_dd_pct": dd_pct,
                "min_equity": min_equity,
                "min_pct_from_initial": min_pct_from_initial,
            }
        )
    return res


def percentile(values: List[float], q: float) -> float:
    """Linear-interpolated percentile. q in [0,100]."""
    if not values:
        return 0.0
    xs = sorted(values)
    if q <= 0:
        return xs[0]
    if q >= 100:
        return xs[-1]
    k = (len(xs) - 1) * (q / 100.0)
    f = int(math.floor(k))
    c = int(math.ceil(k))
    if f == c:
        return xs[f]
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def ftmo_metrics_from_deals(deals: List[Deal], start_equity: float) -> dict:
    pts: List[Tuple[dt.datetime, float]] = [(d.time, d.balance) for d in deals if d.balance > 0]
    if not pts:
        return {
            "ftmo_min_balance": start_equity,
            "ftmo_max_loss_from_initial_abs": 0.0,
            "ftmo_max_loss_from_initial_pct": 0.0,
            "ftmo_worst_daily_loss_abs": 0.0,
            "ftmo_worst_daily_loss_pct": 0.0,
            "ftmo_worst_daily_date": "",
        }

    pts.sort(key=lambda x: x[0])
    min_balance = min(b for _, b in pts)
    max_loss_abs = max(0.0, start_equity - min_balance)
    max_loss_pct = (max_loss_abs / start_equity * 100.0) if start_equity else 0.0

    cur_balance = start_equity
    cur_date = pts[0][0].date()
    day_start = cur_balance
    day_min = cur_balance
    worst_pct = 0.0
    worst_abs = 0.0
    worst_day: Optional[dt.date] = None

    for t, b in pts:
        d = t.date()
        if d != cur_date:
            dd_abs = max(0.0, day_start - day_min)
            dd_pct = (dd_abs / day_start * 100.0) if day_start else 0.0
            if dd_pct > worst_pct:
                worst_pct = dd_pct
                worst_abs = dd_abs
                worst_day = cur_date

            cur_date = d
            day_start = cur_balance
            day_min = day_start

        cur_balance = b
        if b < day_min:
            day_min = b

    dd_abs = max(0.0, day_start - day_min)
    dd_pct = (dd_abs / day_start * 100.0) if day_start else 0.0
    if dd_pct > worst_pct:
        worst_pct = dd_pct
        worst_abs = dd_abs
        worst_day = cur_date

    return {
        "ftmo_min_balance": min_balance,
        "ftmo_max_loss_from_initial_abs": max_loss_abs,
        "ftmo_max_loss_from_initial_pct": max_loss_pct,
        "ftmo_worst_daily_loss_abs": worst_abs,
        "ftmo_worst_daily_loss_pct": worst_pct,
        "ftmo_worst_daily_date": worst_day.isoformat() if worst_day else "",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True, help="Path to MT5 report (.html/.htm or plain export .md/.txt)")
    ap.add_argument("--out", default="", help="Output directory (default: alongside report, ./analysis_output)")
    ap.add_argument("--mc-sims", type=int, default=5000, help="Monte Carlo simulations (default 5000)")
    ap.add_argument("--seed", type=int, default=42, help="Random seed for Monte Carlo")
    args = ap.parse_args()

    report_path = Path(args.report)
    if not report_path.exists():
        raise SystemExit(f"Report not found: {report_path}")

    out_dir = Path(args.out) if args.out else (report_path.parent / "analysis_output")
    out_dir.mkdir(parents=True, exist_ok=True)

    fp = file_fingerprint(report_path)
    deals = parse_deals(report_path)
    trades = deals_to_trades(deals)

    if not deals:
        raise SystemExit("No deals parsed. Check report format/encoding.")

    # --- Deal-level (MT5 "trades" often == OUT deals, inflated by partial closes)
    out_deals = [d for d in deals if d.direction == "out"]
    out_profits = [d.profit for d in out_deals]
    out_wins = [p for p in out_profits if p > 0]
    out_losses = [p for p in out_profits if p < 0]
    out_win_rate = (len(out_wins) / len(out_profits) * 100.0) if out_profits else 0.0
    out_pf = (sum(out_wins) / abs(sum(out_losses))) if out_losses else 999.99  # v11.2: cap

    # Starting equity: first balance row if present, else first deal balance
    # v11.0 FIX: Case-insensitive balance detection
    start_equity = next((d.balance for d in deals if (d.side or "").strip().lower() == "balance" and d.balance > 0), deals[0].balance)

    trade_profits = [t.profit for t in trades]
    final_equity = start_equity + sum(trade_profits)

    wins = [p for p in trade_profits if p > 0]
    losses = [p for p in trade_profits if p < 0]
    win_rate = (len(wins) / len(trade_profits) * 100.0) if trade_profits else 0.0
    avg_win = (sum(wins) / len(wins)) if wins else 0.0
    avg_loss = (sum(losses) / len(losses)) if losses else 0.0
    pf = profit_factor(trades)
    expectancy = (sum(trade_profits) / len(trade_profits)) if trade_profits else 0.0

    equity_curve = []
    balance_after_trades: List[float] = []
    cur = start_equity
    for p in trade_profits:
        cur += p
        equity_curve.append(cur)
        balance_after_trades.append(cur)
    dd_abs, dd_pct = compute_max_drawdown(equity_curve)

    # Write trades.csv
    trades_csv = out_dir / "trades.csv"
    with trades_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "entry_time",
                "exit_time",
                "side",
                "profit",
                "balance_after",
                "duration_minutes",
                "n_out_deals",
                "exit_tag",
                "exit_comment",
                "entry_comment",
            ]
        )
        for t, bal_after in zip(trades, balance_after_trades):
            w.writerow(
                [
                    t.entry_time.strftime("%Y-%m-%d %H:%M:%S"),
                    t.exit_time.strftime("%Y-%m-%d %H:%M:%S"),
                    t.side,
                    f"{t.profit:.2f}",
                    f"{bal_after:.2f}",
                    f"{t.duration_minutes:.1f}",
                    t.n_out_deals,
                    infer_exit_tag(t),
                    t.exit_comment,
                    t.entry_comment,
                ]
            )

    # Monte Carlo
    mc = monte_carlo(trade_profits, start_equity, n_sims=args.mc_sims, seed=args.seed)
    mc_csv = out_dir / "monte_carlo.csv"
    with mc_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["sim", "final_equity", "max_dd_abs", "max_dd_pct", "min_equity", "min_pct_from_initial"],
        )
        w.writeheader()
        for row in mc:
            w.writerow(row)

    # Summary
    mc_dd_pct = [row["max_dd_pct"] for row in mc]
    mc_dd_abs = [row["max_dd_abs"] for row in mc]
    mc_final = [row["final_equity"] for row in mc]
    mc_min_pct_initial = [row["min_pct_from_initial"] for row in mc]

    ftmo = ftmo_metrics_from_deals(deals, start_equity)
    mc_breach_10pct = 0.0
    if mc:
        thr = start_equity * 0.90
        mc_breach_10pct = sum(1 for row in mc if row["min_equity"] <= thr) / len(mc)

    summary = {
        "report": str(report_path),
        "report_fingerprint": fp,
        # Deal-level stats (to match/interpret MT5 headline "Total trades"/win-rate when partial closes exist)
        "n_deals_total": len([d for d in deals if d.side != "balance"]),
        "n_entry_deals_in": sum(1 for d in deals if d.direction == "in"),
        "n_exit_deals_out": sum(1 for d in deals if d.direction == "out"),
        "deal_win_rate_pct_out_deals": out_win_rate,
        "deal_profit_factor_out_deals": out_pf,
        "start_equity": start_equity,
        "final_equity": final_equity,
        "net_profit": final_equity - start_equity,
        # Position-level trades (preferred for quant evaluation)
        "n_trades": len(trades),
        "win_rate_pct": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": pf,
        "expectancy_per_trade": expectancy,
        "max_drawdown_abs": dd_abs,
        "max_drawdown_pct": dd_pct,
        **ftmo,
        "mc_sims": args.mc_sims,
        "mc_max_dd_pct_p50": percentile(mc_dd_pct, 50),
        "mc_max_dd_pct_p90": percentile(mc_dd_pct, 90),
        "mc_max_dd_pct_p95": percentile(mc_dd_pct, 95),
        "mc_max_dd_pct_p99": percentile(mc_dd_pct, 99),
        "mc_max_dd_abs_p95": percentile(mc_dd_abs, 95),
        "mc_min_pct_from_initial_p01": percentile(mc_min_pct_initial, 1),
        "mc_min_pct_from_initial_p05": percentile(mc_min_pct_initial, 5),
        "mc_min_pct_from_initial_p50": percentile(mc_min_pct_initial, 50),
        "mc_prob_breach_max_loss_10pct": mc_breach_10pct,
        "mc_final_equity_p05": percentile(mc_final, 5),
        "mc_final_equity_p50": percentile(mc_final, 50),
        "mc_final_equity_p95": percentile(mc_final, 95),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    # Yearly / Monthly breakdown (robustness across regimes)
    yearly = []
    for k, ts in group_trades_by_exit(trades, lambda d: d.year):
        s = bucket_stats(ts)
        s["year"] = k
        yearly.append(s)
    yearly_csv = out_dir / "yearly.csv"
    with yearly_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "year",
                "n",
                "net_profit",
                "profit_factor",
                "win_rate_pct",
                "avg_win",
                "avg_loss",
                "max_dd_abs",
            ],
        )
        w.writeheader()
        for r in yearly:
            w.writerow(r)

    monthly = []
    for k, ts in group_trades_by_exit(trades, lambda d: f"{d.year:04d}-{d.month:02d}"):
        s = bucket_stats(ts)
        s["month"] = k
        monthly.append(s)
    monthly_csv = out_dir / "monthly.csv"
    with monthly_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "month",
                "n",
                "net_profit",
                "profit_factor",
                "win_rate_pct",
                "avg_win",
                "avg_loss",
                "max_dd_abs",
            ],
        )
        w.writeheader()
        for r in monthly:
            w.writerow(r)

    # Weekly breakdown (KPI: trades/week)
    # We use ISO week to be consistent across years.
    weekly = []
    def _iso_week_key(d: dt.datetime) -> str:
        iso = d.isocalendar()
        return f"{iso.year:04d}-W{iso.week:02d}"

    for k, ts in group_trades_by_exit(trades, _iso_week_key):
        s = bucket_stats(ts)
        s["week"] = k
        weekly.append(s)

    weekly_csv = out_dir / "weekly.csv"
    with weekly_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "week",
                "n",
                "net_profit",
                "profit_factor",
                "win_rate_pct",
                "avg_win",
                "avg_loss",
                "max_dd_abs",
            ],
        )
        w.writeheader()
        for r in weekly:
            w.writerow(r)

    # Strategy breakdown (requires EA to embed strategy name in order comment)
    by_strategy = []
    for comment, ts in group_trades_by_entry_comment(trades):
        s = bucket_stats(ts)
        s["entry_comment"] = comment
        # Strategy-level drawdown is not meaningful (interleaving trades across strategies),
        # keep it as a diagnostic only.
        by_strategy.append(s)

    by_strategy_csv = out_dir / "by_strategy.csv"
    with by_strategy_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "entry_comment",
                "n",
                "net_profit",
                "profit_factor",
                "win_rate_pct",
                "avg_win",
                "avg_loss",
                "max_dd_abs",
            ],
        )
        w.writeheader()
        for r in by_strategy:
            w.writerow(r)

    by_exit_tag = []
    buckets = {}
    for t in trades:
        k = infer_exit_tag(t)
        buckets.setdefault(k, []).append(t)
    for k, ts in sorted(buckets.items()):
        s = bucket_stats(ts)
        s["exit_tag"] = k
        by_exit_tag.append(s)

    by_exit_tag_csv = out_dir / "by_exit_tag.csv"
    with by_exit_tag_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "exit_tag",
                "n",
                "net_profit",
                "profit_factor",
                "win_rate_pct",
                "avg_win",
                "avg_loss",
                "max_dd_abs",
            ],
        )
        w.writeheader()
        for r in by_exit_tag:
            w.writerow(r)

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(
        f"\nWrote:\n- {trades_csv}\n- {mc_csv}\n- {yearly_csv}\n- {monthly_csv}\n- {by_strategy_csv}\n- {by_exit_tag_csv}\n- {out_dir / 'summary.json'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


