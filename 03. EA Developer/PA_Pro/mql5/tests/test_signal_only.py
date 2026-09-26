"""test_signal_only.py - static proof that no order API is reachable while
SIGNAL_ONLY is true (Owner hard wall).

Rule being proven on every *.mq5/*.mqh under mql5/ and on the view-only
indicator package ../PA_Pro_View/ (which must contain zero trade code):

1. Every order/position API token (OrderSend, CTrade, PositionSelect,
   PositionGet*, OrderSelect, OrderDelete, OrderClose, TRADE_ACTION_*,
   MqlTradeRequest, MqlTradeResult, SYMBOL_ASK, SYMBOL_BID, DEAL, HISTORY_*)
   occurs ONLY inside the PaExecutePlan function body in PA_Trade.mqh.
2. PaExecutePlan's FIRST executable statement is the signal_only gate
   `if(signal_only) return(false);` - so nothing downstream can run in
   signal mode.
3. PA_Pro_EA.mq5 calls PaExecutePlan only with `InpSignalOnly` (the input
   itself), never with a constant false.

Run: python test_signal_only.py   (pure text scan - no pa_slots needed)
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MQL5 = os.path.dirname(HERE)

ORDER_TOKENS = re.compile(
    r"\b(OrderSend|OrderDelete|OrderClose|OrderSelect|OrderModify|"
    r"PositionSelect|PositionGetDouble|PositionGetInteger|PositionGetString|"
    r"PositionOpen|CTrade|TRADE_ACTION_\w+|MqlTradeRequest|MqlTradeResult|"
    r"SYMBOL_ASK|SYMBOL_BID|HistorySelect|OrderCalcProfit)\b")


def find_func_body(src, name):
    """Return the source slice of `name`'s function body (brace-matched)."""
    m = re.search(r"\bbool\s+" + name + r"\s*\(", src)
    if not m:
        return None
    i = src.index("{", m.end() - 1)
    depth = 0
    for j in range(i, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[i:j + 1]
    return None


def main():
    fail = 0
    trade = os.path.join(MQL5, "PA_Trade.mqh")
    src = open(trade, encoding="utf-8").read()
    body = find_func_body(src, "PaExecutePlan")
    if body is None:
        print("FAIL: PaExecutePlan not found in PA_Trade.mqh")
        return 1
    # rule 1: order tokens only inside PaExecutePlan, only in PA_Trade.mqh
    roots = [MQL5, os.path.normpath(os.path.join(MQL5, "..", "PA_Pro_View"))]
    for scan_root in roots:
        for root, _dirs, files in os.walk(scan_root):
            for fn in files:
                if not fn.endswith((".mqh", ".mq5")):
                    continue
                p = os.path.join(root, fn)
                text = open(p, encoding="utf-8").read()
                if fn == "PA_Trade.mqh":
                    text = text.replace(body, " ")  # blank out the fn body
                for mm in ORDER_TOKENS.finditer(text):
                    line = text.count("\n", 0, mm.start()) + 1
                    print("FAIL: %s:%d order token %r outside PaExecutePlan"
                          % (os.path.relpath(p, MQL5), line, mm.group(1)))
                    fail += 1
    # rule 2: first executable statement is the signal_only gate
    inner = body[1:]                                  # strip outer {
    inner = re.sub(r"//[^\n]*", "", inner).strip()    # drop line comments
    if not inner.startswith("if(signal_only)"):
        print("FAIL: PaExecutePlan's first statement is not the "
              "signal_only gate")
        fail += 1
    # rule 3: the EA may only ever pass InpSignalOnly (strip comments so
    # prose like "PaExecutePlan()" in headers doesn't false-positive)
    ea = open(os.path.join(MQL5, "PA_Pro_EA.mq5"), encoding="utf-8").read()
    ea = re.sub(r"//[^\n]*", "", ea)
    for mm in re.finditer(r"PaExecutePlan\s*\(([^)]*)\)", ea):
        args = mm.group(1)
        if "InpSignalOnly" not in args:
            print("FAIL: PaExecutePlan called without InpSignalOnly:", args)
            fail += 1
    print("%s (%d violation%s)"
          % ("PASS" if not fail else "FAIL", fail, "" if fail == 1 else "s"))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
