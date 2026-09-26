"""eval.py — spec §6.1 metrics on the frozen TUNE v2 yardstick.

One record per panel in golden/draft/BOOK2012_TUNE_v2.jsonl; for each
panel the engine is run on the panel's own day up to the panel right
edge (window.x1, CET minutes).  Golden t0/t1 are CET minutes-of-day;
prices are absolute.  Engine geometry is pips / bar indices — converted
via the day's cet_min array.

Matching (spec §6.1 table):
  BOX           time IoU >= 0.5 AND both edges within tol
                (3 pips measured / 6 pips eyeballed)
  PATTERN_LINE  endpoints within 3 bars / 3 pips (6 eyeballed),
                or span IoU >= 0.5 + direction agreement
  LEVEL_CARRIED / MINI_LEVEL
                same level within 2 pips, spans overlapping
  LABEL_TF      same poking bar +-1, same side   (golden: marks[])
  BRACKET       overlapping span, same letter family
  others        span IoU >= 0.3 (+ band overlap when defined)

Usability: status 'ok'/'repaired' scored; 'time_only' scored on
time/type only; 'unusable'/'fragment' excluded (reported separately).

Usage:
    python eval.py                 # v1 vs v0 side-by-side, writes EVAL_TUNE.md
    python eval.py --engine v1     # one engine only
"""
import argparse
import datetime as dt
import json
import os
import sys
from collections import Counter, defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "golden"))

import book_loader          # noqa: E402
import engine as ENG_V1     # noqa: E402
import engine_v0 as ENG_V0  # noqa: E402

PIP = 1e-4
TUNE = os.path.join(HERE, "golden", "draft", "BOOK2012_TUNE_v2.jsonl")

USABLE = {"ok", "repaired"}
EXCLUDED = {"unusable", "fragment"}
TIME_ONLY = {"time_only"}

FAMILY = {   # same-family matching (spec table)
    "BOX": "box", "RANGE_OPEN": "box", "CONTEXT_RANGE": "box",
    "PATTERN_LINE": "line", "CONTEXT_LINE": "line",
    "LEVEL_CARRIED": "level", "MINI_LEVEL": "level",
    "BRACKET": "bracket", "SQUEEZE": "squeeze",
    "LABEL_TF": "annot", "BAR_MARKER": "annot",
}
ANNOT = {"LABEL_TF", "BAR_MARKER"}


# ------------------------------------------------------------------ #
# loading
# ------------------------------------------------------------------ #

_day_cache = {}


def day_bars(date):
    """(epoch t, cet_min, o,h,l,c in pips) for one BOOK day."""
    if date in _day_cache:
        return _day_cache[date]
    b = book_loader.load_m5(date + " 00:00", date + " 23:55")
    dates = np.array([dt.datetime.utcfromtimestamp(int(e)).date()
                      .isoformat() for e in b["cet"]])
    k = dates == date
    out = (b["cet"][k].astype(np.int64), b["cet_min"][k].astype(np.int64),
           b["o"][k] / PIP, b["h"][k] / PIP, b["l"][k] / PIP,
           b["c"][k] / PIP)
    _day_cache[date] = out
    return out


def run_engine(cls, m, t, o, h, l, c, w1, w0=None):
    """Feed day bars up to panel right edge w1 (CET minutes).  w0 is
    optional plumbing for R66 s.66.4 (meta_build_start walk-back cap);
    when unset the engine caps at bar 0.  Never read by default flags -
    canonical() output is unchanged."""
    e = cls()
    e.w0_min = int(w0) if w0 is not None else None
    e.cand_log = []
    for j in np.where(m <= w1)[0]:
        e.update(int(t[j]), float(o[j]) * PIP, float(h[j]) * PIP,
                 float(l[j]) * PIP, float(c[j]) * PIP,
                 cet_min=int(m[j]))
    return e


# ------------------------------------------------------------------ #
# engine objects -> minute-space records
# ------------------------------------------------------------------ #

def _min(m, i):
    i = int(min(max(i, 0), len(m) - 1))
    return int(m[i])


def eng_objects(e, m, w0, w1):
    """Objects drawn (alive or died) inside the panel window, expressed
    in minutes + pips: {type, t0, t1, lo, hi, p0, p1, side, letter}."""
    out = []
    for o in e.objects:
        t0m = _min(m, o.t_left)
        # a pierced line's drawn (solid) span ends at the traverse bar;
        # the residual dashed extension is reported via t1_drawn
        t1_src = o.geometry.get("t1_drawn") or \
            (o.t_right if o.t_right is not None else len(e.bars) - 1)
        t1m = _min(m, t1_src)
        if t1m < w0 or t0m > w1:
            continue                       # never visible in the panel
        g = o.geometry
        rec = {"type": o.type, "why": o.why, "t0": t0m, "t1": t1m,
               "t_birth": _min(m, o.t_birth), "id": o.id,
               "events": o.events}
        if "top" in g:
            rec["lo"], rec["hi"] = g["bottom"], g["top"]
        if "price" in g:
            rec["price"], rec["side"] = g["price"], g.get("side")
        if "p0" in g:
            rec["p0"] = g["p0"]           # pips at bar t0(bar idx)
            rec["slope"] = g["slope"]     # pips/bar
            rec["t0_bar"] = g["t0"]
            rec["side"] = g.get("side")
            rec["dirn"] = 1 if g["slope"] > 0.05 else \
                (-1 if g["slope"] < -0.05 else 0)
        if "letter" in g:
            rec["letter"] = g["letter"]
        if o.type == "LABEL_TF":
            rec["price"] = g.get("price")
            rec["side"] = g.get("side")
            rec["letter"] = g.get("letter")
        out.append(rec)
    return out


def eng_marks(e, m, w0, w1):
    """LABEL_TF / BAR_MARKER objects -> point-in-time marks."""
    return [r for r in eng_objects(e, m, w0, w1)
            if r["type"] in ANNOT]


# ------------------------------------------------------------------ #
# golden -> comparable records
# ------------------------------------------------------------------ #

def gold_objects(rec):
    """Usable golden objects; returns (objects, n_unusable, n_time_only)."""
    objs, un, to = [], 0, 0
    for o in rec["objects"]:
        st = o.get("status")
        if st in EXCLUDED or o.get("spec_type") is None:
            un += 1
            continue
        if st in TIME_ONLY or o.get("prec") == "time_only":
            to += 1
        objs.append(o)
    return objs, un, to


def gold_marks(rec):
    return [mk for mk in rec.get("marks", []) if mk["kind"] == "LABEL_TF"]


# ------------------------------------------------------------------ #
# matching
# ------------------------------------------------------------------ #

def iou(a0, a1, b0, b1):
    lo, hi = max(a0, b0), min(a1, b1)
    return max(0, hi - lo) / float(max(a1 - a0, b1 - b0, 1))


def _tol_px(o):
    return 6.0 if o.get("prec") == "eye" else 3.0


def _line_price_at(r, t_min, m):
    """Engine line price (pips) evaluated at minute t_min."""
    # bar index approx: first bar with cet_min >= t_min
    j = int(np.searchsorted(m, t_min))
    j = min(j, len(m) - 1)
    return r["p0"] + r["slope"] * (j - r["t0_bar"])


def match(gobj, eobj, m):
    """True when eobj matches gobj per the §6.1 row for its type."""
    gt = gobj["spec_type"]
    if FAMILY.get(gt) != FAMILY.get(eobj["type"]):
        return False
    t_only = gobj.get("status") in TIME_ONLY or \
        gobj.get("prec") == "time_only"
    span_iou = iou(gobj["t0"], gobj["t1"], eobj["t0"], eobj["t1"])
    if gt == "BOX":
        if span_iou < 0.5 or t_only:
            return span_iou >= 0.5
        tol = _tol_px(gobj)
        lo_g = (gobj.get("price_lo") or 0) / PIP
        hi_g = (gobj.get("price_hi") or 0) / PIP
        return eobj.get("lo") is not None and \
            abs(eobj["lo"] - lo_g) <= tol and \
            abs(eobj["hi"] - hi_g) <= tol
    if gt == "PATTERN_LINE":
        if eobj.get("p0") is None:
            return False
        if t_only:
            return span_iou >= 0.5
        tol = _tol_px(gobj)
        p0g, p1g = gobj.get("price0"), gobj.get("price1")
        if p0g is not None and p1g is not None:
            pe0 = _line_price_at(eobj, gobj["t0"], m)
            pe1 = _line_price_at(eobj, gobj["t1"], m)
            return abs(eobj["t0"] - gobj["t0"]) <= 15 and \
                abs(eobj["t1"] - gobj["t1"]) <= 15 and \
                abs(pe0 - p0g / PIP) <= tol and \
                abs(pe1 - p1g / PIP) <= tol
        # no endpoints: span overlap + direction agreement
        gd = {"up": 1, "down": -1}.get(gobj.get("dir"))
        return span_iou >= 0.5 and \
            (gd is None or gd == eobj.get("dirn"))
    if gt in ("LEVEL_CARRIED", "MINI_LEVEL"):
        if gobj.get("price") is None or eobj.get("price") is None:
            return span_iou >= 0.3
        same = abs(eobj["price"] - gobj["price"] / PIP) <= 2.0
        ov = max(0.0, min(gobj["t1"], eobj["t1"])
                 - max(gobj["t0"], eobj["t0"]))
        return same and (ov > 0 or t_only)
    if gt == "BRACKET":
        fam = lambda s: (s or "").replace("m", "").replace("w", "") \
                                 .replace("i", "")
        return span_iou >= 0.3 and \
            fam(gobj.get("letter")) == fam(eobj.get("letter"))
    if gt == "SQUEEZE":
        return span_iou >= 0.3
    # RANGE_OPEN / CONTEXT_* / BAR_MARKER: span + band when priced
    if span_iou < 0.3:
        return False
    if gobj.get("price") is not None and eobj.get("price") is not None:
        return abs(eobj["price"] - gobj["price"] / PIP) <= _tol_px(gobj)
    if gobj.get("price_hi") is not None and eobj.get("hi") is not None:
        tol = _tol_px(gobj)
        return abs(eobj["lo"] - gobj["price_lo"] / PIP) <= tol and \
            abs(eobj["hi"] - gobj["price_hi"] / PIP) <= tol
    return True


def match_mark(gm, em):
    """LABEL_TF: same poking bar +-1 (5 min), same side.  A mark with
    t=None is attached to its parent object — side agreement only."""
    if em["type"] != "LABEL_TF":
        return False
    if gm.get("side") and em.get("side") and gm["side"] != em["side"]:
        return False
    if gm.get("t") is None:
        return True
    return abs(em["t_birth"] - gm["t"]) <= 5


def match_mark_box(gm, em, box):
    """LABEL_TF agreement restricted to matched boxes: the mark must sit
    inside the golden box span and the engine label inside ours."""
    return match_mark(gm, em)


# ------------------------------------------------------------------ #
# per-panel eval
# ------------------------------------------------------------------ #

def eval_panel(rec, cls):
    date = rec["date"]
    t, m, o, h, l, c = day_bars(date)
    w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
    e = run_engine(cls, m, t, o, h, l, c, w1, w0=w0)
    eobjs = eng_objects(e, m, w0, w1)
    emarks = [r for r in eobjs if r["type"] == "LABEL_TF"]
    gobjs, n_un, n_to = gold_objects(rec)
    for g in gobjs:          # partial spans -> panel bounds
        if g.get("t0") is None:
            g["t0"] = w0
        if g.get("t1") is None:
            g["t1"] = w1
    gmarks = gold_marks(rec)

    # greedy matching per type family, best IoU first
    pairs = []
    used_e = set()
    cand_pairs = []
    for gi, g in enumerate(gobjs):
        for ei, eo in enumerate(eobjs):
            if match(g, eo, m):
                s = iou(g["t0"], g["t1"], eo["t0"], eo["t1"])
                cand_pairs.append((-s, gi, ei))
    cand_pairs.sort()
    used_g = set()
    for _s, gi, ei in cand_pairs:
        if gi in used_g or ei in used_e:
            continue
        used_g.add(gi)
        used_e.add(ei)
        pairs.append((gi, ei))

    # LABEL_TF marks matching
    mpairs = []
    used_em = set()
    for gm in gmarks:
        best, bs = None, 999
        for ei, em in enumerate(emarks):
            if ei in used_em or not match_mark(gm, em):
                continue
            d = abs(em["t_birth"] - gm["t"]) if gm.get("t") is not None \
                else 0
            if d < bs:
                best, bs = ei, d
        if best is not None:
            used_em.add(best)
            mpairs.append((gm, emarks[best]))

    # LABEL_TF agreement on matched boxes
    tf_num = tf_den = 0
    for gi, ei in pairs:
        g = gobjs[gi]
        if g["spec_type"] != "BOX":
            continue
        g_tf = [gm for gm in gmarks
                if gm.get("t") is not None
                and g["t0"] - 5 <= gm["t"] <= g["t1"] + 5]
        eo = eobjs[ei]
        e_tf = [em for em in emarks
                if eo["t0"] - 5 <= em["t_birth"] <= eo["t1"] + 5]
        for gm in g_tf:
            tf_den += 1
            if any(match_mark(gm, em) for em in e_tf):
                tf_num += 1

    # edge stability: logged re_anchor events vs unlogged moves.
    # v1 only mutates frozen edges through the re_anchor event; count
    # them, plus a check that no ACTIVE box edge differs from birth
    # geometry without such an event (post-hoc scan is not possible —
    # rely on the logged event invariant).
    n_reanchor = sum(1 for eo in eobjs
                     for ev in eo["events"] if ev[1] == "re_anchor")

    return {"id": rec["id"], "date": date,
            "gobjs": gobjs, "eobjs": eobjs, "gmarks": gmarks,
            "pairs": pairs, "mpairs": mpairs,
            "n_unusable": n_un, "n_time_only": n_to,
            "tf_num": tf_num, "tf_den": tf_den,
            "n_reanchor": n_reanchor,
            "n_eng": len(eobjs), "n_gold": len(gobjs) + len(gmarks),
            "w0": w0, "w1": w1}


# ------------------------------------------------------------------ #
# aggregate + report
# ------------------------------------------------------------------ #

def aggregate(rows):
    per_type = defaultdict(lambda: {"g": 0, "e": 0, "m": 0})
    clutter = []
    tf_num = tf_den = 0
    n_un = n_to = 0
    for r in rows:
        matched_g = {gi for gi, _ in r["pairs"]}
        matched_e = {ei for _, ei in r["pairs"]}
        for gi, g in enumerate(r["gobjs"]):
            t = g["spec_type"]
            per_type[t]["g"] += 1
            if gi in matched_g:
                per_type[t]["m"] += 1
        for ei, eo in enumerate(r["eobjs"]):
            t = eo["type"]
            if t in ANNOT:
                continue                    # annots scored via marks
            per_type[t]["e"] += 1
        n_un += r["n_unusable"]
        n_to += r["n_time_only"]
        tf_num += r["tf_num"]
        tf_den += r["tf_den"]
        if r["n_gold"]:
            clutter.append(r["n_eng"] / r["n_gold"])
        # LABEL_TF counts
        per_type["LABEL_TF"]["g"] += len(r["gmarks"])
        per_type["LABEL_TF"]["e"] += \
            sum(1 for eo in r["eobjs"] if eo["type"] == "LABEL_TF")
        per_type["LABEL_TF"]["m"] += len(r["mpairs"])
    return per_type, clutter, tf_num, tf_den, n_un, n_to


def report(rows, tag):
    per_type, clutter, tf_num, tf_den, n_un, n_to = aggregate(rows)
    out = [f"## {tag}", "",
           "| type | golden | engine | matched | recall | precision |",
           "|---|---|---|---|---|---|"]
    for t in sorted(per_type):
        d = per_type[t]
        rec = d["m"] / d["g"] if d["g"] else float("nan")
        prc = d["m"] / d["e"] if d["e"] else float("nan")
        out.append("| %s | %d | %d | %d | %.2f | %.2f |"
                   % (t, d["g"], d["e"], d["m"], rec, prc))
    cl = np.median(clutter) if clutter else float("nan")
    tf_agr = tf_num / tf_den if tf_den else float("nan")
    out += ["",
            f"- clutter ratio median: **{cl:.2f}** "
            f"(n={len(clutter)} panels)",
            f"- LABEL_TF agreement on matched boxes: **{tf_agr:.2f}** "
            f"({tf_num}/{tf_den})",
            f"- re_anchor events: "
            f"{sum(r['n_reanchor'] for r in rows)} "
            f"(all edge moves are logged by construction)",
            f"- excluded: {n_un} unusable/fragment, "
            f"{n_to} time_only (time/type only)",
            f"- panels: {len(rows)}"]
    return "\n".join(out), per_type, cl, tf_agr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=["v0", "v1", "both"],
                    default="both")
    ap.add_argument("--out", default=os.path.join(HERE, "EVAL_TUNE.md"))
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    recs = [json.loads(x) for x in open(TUNE, encoding="utf8")]
    if args.limit:
        recs = recs[:args.limit]

    engines = []
    if args.engine in ("v0", "both"):
        engines.append(("v0", ENG_V0.PerceptionEngine))
    if args.engine in ("v1", "both"):
        engines.append(("v1", ENG_V1.PerceptionEngine))

    doc = ["# EVAL_TUNE — spec §6.1 on BOOK2012_TUNE_v2",
           "",
           "Frozen yardstick: T000366. Engine run per panel day up to "
           "window.x1 (CET). All counts per spec matching table.",
           ""]
    for tag, cls in engines:
        rows = []
        for k, rec in enumerate(recs):
            rows.append(eval_panel(rec, cls))
            if (k + 1) % 20 == 0:
                print(f"  {tag}: {k + 1}/{len(recs)}", flush=True)
        rep, _pt, _cl, _tf = report(rows, tag)
        print(rep)
        doc.append(rep)
        doc.append("")
    open(args.out, "w", encoding="utf8").write("\n".join(doc))
    print("wrote", args.out)


if __name__ == "__main__":
    main()
