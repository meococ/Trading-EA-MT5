"""pa_costs — all-in round-turn cost table and cost tiers.

Provenance (READ-ONLY sources)
------------------------------
- ``03. EA Developer/EA_VolmanPA/PLAN/COST_FEASIBILITY.md:75-78`` — c_rt p90
  pips: EURUSD 1.0, GBPUSD 1.1, USDJPY 1.4, USDCHF 1.1 (USDCAD/AUDUSD/NZDUSD
  "NOT MEASURED", XAUUSD excluded by the charter).
- ``.../research/lab/vpa_random_baseline.py:41`` — ``C_RT_P90`` mirror.
- ``.../research/lab/vpa_econ1_costs.py:19`` — scenarios gross/x1/x1.5/x2.

Application semantics (frozen): the all-in round-turn cost is applied ONCE per
trade as an adverse shift of the fill price by ``c_rt * mult``.

AUDUSD / USDCAD / NZDUSD
------------------------
Charter section 3: derive from repo cost evidence with file:line provenance,
otherwise use 1.4 marked ``proxy``.  At import this module reads
``PA_Pro/docs/COSTS.md`` (written by sub-agent B) if it exists and accepts any
of: a fenced JSON block mapping symbol -> number (or {"c_rt_p90": x}), or
single ``SYMBOL: number`` / ``SYMBOL = number`` lines.  Until that evidence
lands the value is 1.4 and ``cost_source(sym) == "proxy"`` (TODO).
"""

import json
import os
import re

__all__ = [
    "C_RT_P90", "COST_SOURCE", "TIERS", "PIP", "pip_size", "cost_pips",
    "cost_price", "reload_costs", "cost_source", "COSTS_MD",
]

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
COSTS_MD = os.path.join(_ROOT, "docs", "COSTS.md")

PIP = {"USDJPY": 1e-2, "XAUUSD": 1e-1}

# Frozen, measured provenance.
C_RT_P90 = {
    "EURUSD": 1.0,     # COST_FEASIBILITY.md:75 / vpa_random_baseline.py:41
    "GBPUSD": 1.1,     # COST_FEASIBILITY.md:76
    "USDJPY": 1.4,     # COST_FEASIBILITY.md:77
    "USDCHF": 1.1,     # COST_FEASIBILITY.md:78
}
COST_SOURCE = {
    "EURUSD": "COST_FEASIBILITY.md:75",
    "GBPUSD": "COST_FEASIBILITY.md:76",
    "USDJPY": "COST_FEASIBILITY.md:77",
    "USDCHF": "COST_FEASIBILITY.md:78",
}

_PROXY_SYMBOLS = ("AUDUSD", "USDCAD", "NZDUSD")
_PROXY_VALUE = 1.4     # charter section 3 fallback; NOT a measured number
for _s in _PROXY_SYMBOLS:
    C_RT_P90[_s] = _PROXY_VALUE
    COST_SOURCE[_s] = "proxy"  # TODO: replace from docs/COSTS.md evidence

TIERS = {"gross": 0.0, "x1": 1.0, "x1.5": 1.5, "x2": 2.0}

_SYMBOL_RE = re.compile(r"^\s*([A-Z]{6})\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)\s*(?:#.*)?$", re.M)
_JSON_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.S)
_NUM_RE = re.compile(r"[0-9]+(?:\.[0-9]+)?$")


def _parse_costs_md(path):
    """Tolerant parse of the cost evidence file.  Returns {SYMBOL: c_rt_pips}."""
    out = {}
    if not os.path.exists(path):
        return out
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return out
    for m in _JSON_RE.finditer(text):
        try:
            obj = json.loads(m.group(1))
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        for k, v in obj.items():
            if not (isinstance(k, str) and re.fullmatch(r"[A-Z]{6}", k)):
                continue
            if isinstance(v, (int, float)):
                out[k] = float(v)
            elif isinstance(v, dict):
                for key in ("c_rt_p90", "c_rt", "cost_pips", "pips", "value"):
                    if isinstance(v.get(key), (int, float)):
                        out[k] = float(v[key])
                        break
    for m in _SYMBOL_RE.finditer(text):
        out.setdefault(m.group(1), float(m.group(2)))
    return out


def _parse_costs_table(path):
    """First markdown table row per symbol: (value, line_no, tag).

    Tag is "proxy" when any cell of the row contains the word proxy, else
    "docs".  This is the format sub-agent B publishes in docs/COSTS.md.
    """
    out = {}
    if not os.path.exists(path):
        return out
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return out
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if not cells:
            continue
        sym = cells[0].strip("* ")
        if not re.fullmatch(r"[A-Z]{6}", sym or ""):
            continue
        val = None
        for c in cells[1:]:
            c2 = c.replace("*", "").strip()
            if _NUM_RE.fullmatch(c2):
                val = float(c2)
                break
        if val is None:
            continue
        tag = "proxy" if any("proxy" in c.lower() for c in cells) else "docs"
        out.setdefault(sym, (val, i, tag))
    return out


def reload_costs():
    """(Re)load any values published in ``docs/COSTS.md``.  Proxy placeholders
    already marked ``proxy`` are overwritten only when the file has evidence
    for that symbol.  Returns the number of symbols updated."""
    parsed = _parse_costs_md(COSTS_MD)
    table = _parse_costs_table(COSTS_MD)
    n = 0
    for sym, val in parsed.items():
        if COST_SOURCE.get(sym) == "proxy" and sym in _PROXY_SYMBOLS:
            C_RT_P90[sym] = val
            COST_SOURCE[sym] = "docs/COSTS.md"
            n += 1
    for sym in _PROXY_SYMBOLS:
        if sym in table:
            val, line_no, tag = table[sym]
            C_RT_P90[sym] = val
            COST_SOURCE[sym] = f"docs/COSTS.md:{line_no} ({tag})"
            n += 1
    return n


reload_costs()


def pip_size(symbol):
    return PIP.get(symbol, 1e-4)


def cost_pips(symbol, mult):
    """All-in round-turn cost in pips for a tier multiplier."""
    if symbol not in C_RT_P90:
        raise KeyError(f"no c_rt for symbol {symbol!r}; known: {sorted(C_RT_P90)}")
    return C_RT_P90[symbol] * float(mult)


def cost_price(symbol, mult):
    """Price shift applied adversely to the fill: c_rt_pips * mult * pip."""
    return cost_pips(symbol, mult) * pip_size(symbol)


def cost_source(symbol):
    return COST_SOURCE.get(symbol, "unknown")
