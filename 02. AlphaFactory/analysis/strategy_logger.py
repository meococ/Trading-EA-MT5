#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Strategy Logger - Tự động ghi kết quả backtest vào STRATEGY_LOG.md
==================================================================

MỤC ĐÍCH:
- Parse kết quả backtest/analysis
- Tự động append vào STRATEGY_LOG.md
- Đảm bảo mọi test đều được ghi lại

USAGE:
  python strategy_logger.py --name "Strategy Name" --results "path/to/results.json"
  python strategy_logger.py --name "SMA Crossover" --pf 1.25 --dd 18 --trades 150 --status "WEAK"

CHÚ Ý CHO AI:
- File này được gọi tự động sau mỗi lần backtest/analyze
- Kết quả sẽ append vào STRATEGY_LOG.md
- Không cần gọi thủ công trừ khi muốn ghi manual entry
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

# ==============================================================
# CONFIGURATION
# ==============================================================

ALPHA_ROOT = Path(__file__).parent.parent
STRATEGY_LOG = ALPHA_ROOT / "STRATEGY_LOG.md"

STATUS_EMOJI = {
    "PASSED": "✅",
    "WEAK": "⚠️",
    "FAILED": "❌",
    "TESTING": "🔬",
    "PROMISING": "🟢",
}

def determine_status(pf: float, dd: float, trades: int) -> str:
    """
    Classify quality with PF + DD + sample-size awareness.
    """
    low_sample = trades > 0 and trades < 100

    if pf >= 1.5 and dd <= 25 and not low_sample:
        return "PASSED"
    if pf >= 1.3 and dd <= 35:
        return "WEAK" if low_sample else "PASSED"
    if pf >= 1.1 and dd <= 45:
        return "WEAK"
    return "FAILED"

# ==============================================================
# CORE FUNCTIONS
# ==============================================================

def get_next_strategy_id() -> str:
    """
    Đọc STRATEGY_LOG.md và tìm ID tiếp theo.
    Format: S001, S002, S003...
    """
    if not STRATEGY_LOG.exists():
        return "S001"
    
    content = STRATEGY_LOG.read_text(encoding="utf-8")
    
    # Tìm tất cả ID pattern S\d{3}
    import re
    ids = re.findall(r'S(\d{3})', content)
    
    if not ids:
        return "S001"
    
    max_id = max(int(i) for i in ids)
    return f"S{max_id + 1:03d}"


def format_strategy_entry(
    strategy_id: str,
    name: str,
    status: str,
    pf: float,
    dd: float,
    trades: int,
    winrate: float = 0,
    notes: str = "",
    concept: str = "",
    lessons: str = "",
) -> str:
    """
    Format một entry mới cho STRATEGY_LOG.md
    """
    emoji = STATUS_EMOJI.get(status.upper(), "❓")
    date = datetime.now().strftime("%Y-%m-%d")
    
    entry = f"""
### {strategy_id}: {name}
**Date:** {date}  
**Status:** {emoji} {status.upper()}  

**Results:**
- Profit Factor: {pf:.2f}
- Max Drawdown: {dd:.1f}%
- Trades: {trades}
- Win Rate: {winrate:.1f}%

"""
    
    if concept:
        entry += f"""**Concept:**
{concept}

"""
    
    if notes:
        entry += f"""**Notes:**
{notes}

"""
    
    if lessons:
        entry += f"""**Lesson Learned:**
> {lessons}

"""
    
    entry += "---\n"
    return entry


def append_to_log(entry: str):
    """
    Append entry vào STRATEGY_LOG.md
    Chèn vào section "CHI TIẾT TỪNG CHIẾN LƯỢC"
    """
    if not STRATEGY_LOG.exists():
        print(f"ERROR: {STRATEGY_LOG} not found!")
        return False
    
    content = STRATEGY_LOG.read_text(encoding="utf-8")
    
    # Tìm vị trí cuối của section chi tiết
    marker = "## 🧠 BÀI HỌC TỔNG HỢP"
    
    if marker in content:
        # Chèn entry trước section "BÀI HỌC TỔNG HỢP"
        parts = content.split(marker)
        new_content = parts[0] + entry + "\n" + marker + parts[1]
    else:
        # Append cuối file nếu không tìm thấy marker
        new_content = content + "\n" + entry
    
    STRATEGY_LOG.write_text(new_content, encoding="utf-8")
    return True


def update_summary_table(
    strategy_id: str,
    name: str,
    status: str,
    pf: float,
    notes: str = ""
):
    """
    Cập nhật bảng tổng quan nhanh ở đầu file
    """
    if not STRATEGY_LOG.exists():
        return False
    
    content = STRATEGY_LOG.read_text(encoding="utf-8")
    emoji = STATUS_EMOJI.get(status.upper(), "❓")
    
    # Tìm vị trí kết thúc bảng
    table_end = "---\n\n## 📝 CHI TIẾT"
    
    # Tạo row mới
    short_notes = notes[:30] + "..." if len(notes) > 30 else notes
    new_row = f"| {strategy_id} | {name} | {emoji} {status.upper()} | {pf:.2f} | {short_notes} |\n"
    
    if table_end in content:
        # Chèn row mới trước table_end
        content = content.replace(table_end, new_row + table_end)
        STRATEGY_LOG.write_text(content, encoding="utf-8")
        return True
    
    return False


def log_from_json(results_path: str, name: str = ""):
    """
    Đọc kết quả từ JSON file và log vào STRATEGY_LOG
    """
    results = Path(results_path)
    if not results.exists():
        print(f"ERROR: Results file not found: {results}")
        return False
    
    with open(results, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Extract metrics (hỗ trợ nhiều format JSON)
    pf = data.get("profit_factor", data.get("pf", 0))
    dd = data.get("max_drawdown_pct", data.get("max_dd", data.get("dd", 0)))
    trades = data.get("total_trades", data.get("trades", data.get("n_trades", 0)))
    winrate = data.get("win_rate", data.get("win_rate_pct", 0))
    
    # Determine status from PF + DD + sample size
    status = determine_status(pf, dd, trades)
    
    strategy_id = get_next_strategy_id()
    strategy_name = name or data.get("strategy", data.get("name", "Unknown"))
    
    entry = format_strategy_entry(
        strategy_id=strategy_id,
        name=strategy_name,
        status=status,
        pf=pf,
        dd=dd,
        trades=trades,
        winrate=winrate,
        notes=f"Auto-logged from {results.name}",
    )
    
    if append_to_log(entry):
        update_summary_table(strategy_id, strategy_name, status, pf, "Auto-logged")
        print(f"✅ Logged {strategy_id}: {strategy_name} (PF={pf:.2f}, Status={status})")
        return True
    
    return False


# ==============================================================
# CLI INTERFACE
# ==============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Strategy Logger - Ghi kết quả vào STRATEGY_LOG.md",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Log từ JSON file
  python strategy_logger.py --results "analysis/results.json"
  
  # Log manual entry
  python strategy_logger.py --name "SMA Cross" --pf 1.25 --dd 18 --trades 150
  
  # Log với notes
  python strategy_logger.py --name "RSI Mean Reversion" --pf 1.35 --dd 12 --trades 200 --status PASSED --notes "Works well in ranging markets"
        """
    )
    
    parser.add_argument("--results", "-r", help="Path to JSON results file")
    parser.add_argument("--name", "-n", default="", help="Strategy name")
    parser.add_argument("--pf", type=float, default=0, help="Profit Factor")
    parser.add_argument("--dd", type=float, default=0, help="Max Drawdown %")
    parser.add_argument("--trades", type=int, default=0, help="Number of trades")
    parser.add_argument("--winrate", type=float, default=0, help="Win rate %")
    parser.add_argument("--status", default="", help="Status: PASSED/WEAK/FAILED/TESTING")
    parser.add_argument("--notes", default="", help="Additional notes")
    parser.add_argument("--concept", default="", help="Strategy concept description")
    parser.add_argument("--lessons", default="", help="Lessons learned")
    
    args = parser.parse_args()
    
    # Log từ JSON file
    if args.results:
        return 0 if log_from_json(args.results, args.name) else 1
    
    # Log manual entry
    if args.name and args.pf > 0:
        strategy_id = get_next_strategy_id()
        
        # Auto-determine status if not provided
        if not args.status:
            args.status = determine_status(args.pf, args.dd, args.trades)
        
        entry = format_strategy_entry(
            strategy_id=strategy_id,
            name=args.name,
            status=args.status,
            pf=args.pf,
            dd=args.dd,
            trades=args.trades,
            winrate=args.winrate,
            notes=args.notes,
            concept=args.concept,
            lessons=args.lessons,
        )
        
        if append_to_log(entry):
            update_summary_table(strategy_id, args.name, args.status, args.pf, args.notes)
            print(f"✅ Logged {strategy_id}: {args.name}")
            return 0
        return 1
    
    print("ERROR: Provide --results OR (--name + --pf)")
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
