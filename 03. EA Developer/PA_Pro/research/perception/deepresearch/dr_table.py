"""dr_table.py -- emit the D2 per-golden markdown table (119 rows)."""
import pickle, re, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
import cache as CA  # noqa: E402

rows = pickle.load(open(os.path.join(HERE, "dr_rows.pkl"), "rb"))
SETUP = re.compile(r"\b(dd|fb|sb|bb|rb|irb|arb|pb|pbc|pbp|tff|pr)\b")


def tags_of(r):
    s = set()
    for mk in r["marks"]:
        s.update(SETUP.findall(mk["raw"].lower()))
    return sorted(s)


def frames(r):
    cl = (r["clause"] or "").lower()
    out = []
    if re.search(r"asia", cl):
        out.append("asia")
    if re.search(r"day.s range|the same range|whole \S* ?congestion", cl):
        out.append("day-range")
    if re.search(r"\bw\b|\bm\b|ww|mm|shs|bracket|triangle", cl):
        out.append("pattern")
    if re.search(r"base|post-|after|drop|spike|absorption", cl):
        out.append("post-leg")
    if re.search(r"second|another|new range|small|inner", cl):
        out.append("2nd/inner")
    if re.search(r"straddl|round number|on the 1[,.]|on 1[,.]\d\d|"
                 r"under the 1[,.]|just above 1[,.]|just below|"
                 r"centred on|the 1[,.]\d\d\b", cl):
        out.append("round")
    if re.search(r"kept|kept after|still|open to the right|continued",
                 cl):
        out.append("kept-past-break")
    if re.search(r"ema", cl):
        out.append("ema")
    if not out:
        out.append("congestion")
    return ",".join(out)


def edge_named(r):
    cl = (r["clause"] or "") + "|" + (r["lesson"] or "")
    hits = []
    for pat, lab in [
            (r"first touch", "first-touch"), (r"tease", "tease"),
            (r"spike", "spike"), (r"test", "test"),
            (r"breakout bar|break bar", "brk-bar"),
            (r"lows? (of|at|on) |highs? (of|at|on) ", "named-extreme"),
            (r"rebound|bounce|rejection", "bounce")]:
        if re.search(pat, cl, re.I):
            hits.append(lab)
    return ",".join(hits) if hits else "-"


def youngest_rank(r):
    p = [c for c in r["pool"] if c["avail"]]
    if not p:
        return "-"
    order = sorted(range(len(p)), key=lambda i: -p[i]["born"])
    rk = [k + 1 for k, i in enumerate(order) if p[i]["match"]]
    return str(min(rk)) if rk else "-"


out = []
out.append("| panel | tau | h(p) | span(m) | setup | frames | edge-named |"
           " reach | nM | yRank |")
out.append("|---|---|---|---|---|---|---|---|---|---|")
for r in sorted(rows, key=lambda x: (x["panel"], x["tau"])):
    h = r["g_hi"] - r["g_lo"]
    span = (r["g_t1"] - r["g_t0"]) if (r["g_t1"] and r["g_t0"]) else 0
    out.append("| %s | %d | %.0f | %d | %s | %s | %s | %s | %d | %s |"
               % (r["panel"], r["tau"], h, span,
                  ",".join(tags_of(r)) or "-", frames(r), edge_named(r),
                  "Y" if r["n_match"] else "n",
                  r["n_match"], youngest_rank(r)))
open(os.path.join(HERE, "d2_table.md"), "w", encoding="utf8").write(
    "\n".join(out))
print("rows:", len(out) - 2)
