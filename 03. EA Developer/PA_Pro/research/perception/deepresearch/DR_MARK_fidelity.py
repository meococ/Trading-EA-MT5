"""DR_MARK_fidelity.py — E3a: mark-family fidelity on TUNE.

Families: BRACKET, LABEL_TF, SQUEEZE, FALSE_EXT(bar_facts proxy).

Reuses the ruler (evalcheck/eval_v2.py via funnel.funnel_panel —
imported, never copied).  Per panel:
  * golden counts + engine counts + matched (ruler assignment)
  * miss taxonomy (funnel rows)
  * cand_log outcome histograms per mark kind (proposal funnel)
  * LABEL_TF born marks: letter distribution, T->F relabel events,
    parent-object type
  * bracket template stream: cand_log BRACKET rows split
    vetoed_irrelevant vs granted-path
  * FALSE_EXT: engine bar_facts false_high/low event times vs golden
    ARROW marks whose raw text says "false high/low" (research matcher,
    +-10 min — FALSE_EXT is NOT a ruler family)
  * nulls: cross-panel (golden marks/objects vs another panel's engine
    records) and time-shift (+30/+60 min) nulls.

Output: DR_MARK_fidelity.jsonl (one row per panel) + printed summary.
Research-only: writes nothing outside deepresearch/.
"""
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, PERC)
sys.path.insert(0, os.path.join(PERC, "golden"))
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
sys.path.insert(0, os.path.join(PERC, "..", "..", "lib"))

import numpy as np                      # noqa: E402

import eval as EV                      # noqa: E402
import eval_v2 as V2                   # noqa: E402
import common as C                     # noqa: E402
import funnel as F                     # noqa: E402
import engine as ENG                   # noqa: E402

OUT = os.path.join(HERE, "DR_MARK_fidelity.jsonl")
MARK_KINDS = ("BRACKET", "LABEL_TF", "SQUEEZE", "BAR_MARKER")


def panel_marks(e, m, w0, w1):
    """Born LABEL_TF objects + relabel events + parent kinds."""
    out = []
    id2type = {o.id: o.type for o in e.objects}
    for o in e.objects:
        if o.type != "LABEL_TF":
            continue
        tb = V2._min(m, o.t_birth)
        if not (w0 <= tb <= w1):
            continue
        rel = [ev for ev in o.events if ev[1] == "relabel"]
        out.append({
            "t": tb, "side": o.geometry.get("side"),
            "letter": o.geometry.get("letter"),
            "price": o.geometry.get("price"),
            "parent": id2type.get(o.role),
            "n_relabel": len(rel),
            "relabel_lag": (rel[-1][0] - o.t_birth) if rel else None,
        })
    return out


def false_ext_facts(e, m, w0, w1):
    """bar_facts false_high/false_low event times inside the window."""
    out = []
    for i, f in enumerate(e.bar_facts):
        if i >= len(m):
            break
        if w0 <= int(m[i]) <= w1:
            if "false_high" in f:
                out.append({"t": int(m[i]), "dir": "high"})
            if "false_low" in f:
                out.append({"t": int(m[i]), "dir": "low"})
    return out


def _hhmm(s):
    """'~HH:MM' / 'HH:MM' -> minute of day, or None."""
    m = re.match(r"~?(\d{1,2}):(\d{2})", str(s or ""))
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def gold_false_arrows(rec):
    """Golden references to a false high/low extreme, with times.

    Two golden channels carry them (no FALSE_EXT objects exist):
      * ARROW marks whose raw text says 'false' (t is 'HH:MM' text)
      * raw_marks/lesson text 'false (high|low)' near a ~HH:MM token
    """
    out = []
    for mk in rec.get("marks", []):
        if mk.get("kind") != "ARROW":
            continue
        raw = (mk.get("raw") or "").lower()
        if "false" not in raw:
            continue
        t = mk.get("t")
        t = _hhmm(t) if isinstance(t, str) else t
        d = "high" if re.search(r"high|top|above|↑", raw) else \
            ("low" if re.search(r"low|below|under|↓", raw) else None)
        out.append({"t": t, "dir": d, "raw": raw[:60]})
    txt = ((rec.get("raw_marks") or "") + "\n" + (rec.get("lesson") or "")
           ).lower()
    for m in re.finditer(r"false (high|low)[^.;~\n]{0,60}", txt):
        seg = m.group(0)
        tm = re.search(r"~?(\d{1,2}):(\d{2})", seg)
        out.append({"t": _hhmm(tm.group(0)) if tm else None,
                    "dir": m.group(1), "raw": seg[:60],
                    "src": "text"})
    return out


def run_panel(rec):
    """One TUNE panel: funnel (ruler) + mark internals."""
    engs = []

    def factory():
        e = ENG.PerceptionEngine()
        e.cand_log = []
        engs.append(e)
        return e

    fr = F.funnel_panel(rec, factory)
    e = engs[-1]
    w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
    _t, m, _o, _h, _l, _c = EV.day_bars(rec["date"])

    cand_out = {}
    for cd in e.cand_log or []:
        if cd["kind"] in MARK_KINDS:
            cand_out.setdefault(cd["kind"], collections.Counter())
            cand_out[cd["kind"]][cd.get("outcome") or "?"] += 1

    gobjs, _un, _to = EV.gold_objects(rec)
    gmarks = EV.gold_marks(rec)
    return {
        "id": rec["id"], "date": rec["date"], "w0": w0, "w1": w1,
        "miss": fr["miss"],
        "cand_outcomes": {k: dict(v) for k, v in cand_out.items()},
        "eobjs": V2.eng_objects(e, m, w0, w1),
        "gobjs": [{"spec_type": g["spec_type"], "t0": g.get("t0"),
                   "t1": g.get("t1"), "letter": g.get("letter"),
                   "scorable": V2.scorable(g, w0, w1)} for g in gobjs],
        "gmarks": [{"t": gm.get("t"), "side": gm.get("side"),
                    "letter": gm.get("letter"), "approx": gm.get("approx"),
                    "scorable": V2.scorable_mark(gm, w0, w1)}
                   for gm in gmarks],
        "marks_born": panel_marks(e, m, w0, w1),
        "fx_facts": false_ext_facts(e, m, w0, w1),
        "gold_false": gold_false_arrows(rec),
        "n_gold": fr["n_gold"], "n_eng": fr["n_eng"],
    }


def nulls(rows):
    """Cross-panel + time-shift nulls for LABEL_TF; cross-panel for
    BRACKET."""
    # LABEL_TF: golden marks vs the engine marks of the NEXT panel
    # (different day, same minute-of-day axis) — chance rate.
    cp_hit = cp_n = 0
    for k in range(len(rows) - 1):
        gms = [g for g in rows[k]["gmarks"] if g["scorable"]]
        ems = [{"type": "LABEL_TF", "t_birth": b["t"], "side": b["side"]}
               for b in rows[k + 1]["marks_born"]]
        for gm in gms:
            cp_n += 1
            if any(V2.match_mark(gm, em) for em in ems):
                cp_hit += 1
    # time-shift null: golden t +30 / +60 vs own panel's engine marks
    ts_hit = {30: [0, 0], 60: [0, 0]}
    for r in rows:
        ems = [{"type": "LABEL_TF", "t_birth": b["t"], "side": b["side"]}
               for b in r["marks_born"]]
        for gm in r["gmarks"]:
            if not gm["scorable"] or gm["t"] is None:
                continue
            for s in (30, 60):
                g2 = dict(gm); g2["t"] = gm["t"] + s
                ts_hit[s][1] += 1
                if any(V2.match_mark(g2, em) for em in ems):
                    ts_hit[s][0] += 1
    # BRACKET: golden brackets vs next panel's engine brackets
    cb_hit = cb_n = 0
    for k in range(len(rows) - 1):
        gbs = [g for g in rows[k]["gobjs"]
               if g["spec_type"] == "BRACKET" and g["scorable"]]
        ebs = [e for e in rows[k + 1]["eobjs"] if e["type"] == "BRACKET"]
        for g in gbs:
            cb_n += 1
            if any(V2.match(g, e, []) for e in ebs):
                cb_hit += 1
    return {"label_cross_panel": (cp_hit, cp_n),
            "label_shift30": tuple(ts_hit[30]),
            "label_shift60": tuple(ts_hit[60]),
            "bracket_cross_panel": (cb_hit, cb_n)}


def main():
    recs = C.load_tune()
    rows = []
    for k, rec in enumerate(recs):
        rows.append(run_panel(rec))
        if (k + 1) % 25 == 0:
            print("panel %d/%d" % (k + 1, len(recs)), flush=True)
    with open(OUT, "w", encoding="utf8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")

    fams = ("BRACKET", "LABEL_TF", "SQUEEZE")
    agg = {f: collections.Counter() for f in fams}
    miss_tax = {f: collections.Counter() for f in fams}
    cand_agg = collections.defaultdict(collections.Counter)
    letters = collections.Counter()
    glet = collections.Counter()
    relabels = []
    parents = collections.Counter()
    fx_n = gx_n = fx_hit = 0
    for r in rows:
        for mrow in r["miss"]:
            ty = mrow["type"]
            if ty in agg:
                agg[ty]["g"] += 1
                miss_tax[ty][mrow["cat"]] += 1
                if mrow["cat"] == "matched":
                    agg[ty]["m"] += 1
        for knd, outs in r["cand_outcomes"].items():
            for oc, n in outs.items():
                cand_agg[knd][oc] += n
        for bm in r["marks_born"]:
            letters[bm["letter"]] += 1
            parents[bm["parent"]] += 1
            if bm["n_relabel"]:
                relabels.append(bm["relabel_lag"])
        for g in r["gobjs"]:
            if g["spec_type"] == "BRACKET" and g["scorable"]:
                glet[g["letter"] or "?"] += 1
        fx_n += len(r["fx_facts"])
        for gf in r["gold_false"]:
            gx_n += 1
            if gf["t"] is not None and \
                    any(abs(fx["t"] - gf["t"]) <= 10 and
                        (gf["dir"] is None or gf["dir"] == fx["dir"])
                        for fx in r["fx_facts"]):
                fx_hit += 1

    print("\n=== fidelity (ruler, TUNE, scorable golden) ===")
    for f in fams:
        print("%-10s golden=%d matched=%d recall=%.3f  miss: %s"
              % (f, agg[f]["g"], agg[f]["m"],
                 agg[f]["m"] / max(agg[f]["g"], 1),
                 dict(miss_tax[f])))
    print("\n=== candidate outcomes (proposal funnel) ===")
    for knd, outs in cand_agg.items():
        print("%-10s total=%d  %s" % (knd, sum(outs.values()),
                                      dict(outs)))
    print("\n=== born LABEL_TF ===")
    print("letters:", dict(letters), " parents:", dict(parents))
    print("T->F relabels: n=%d lags=%s"
          % (len(relabels), sorted(set(relabels))[:10]))
    print("\n=== golden BRACKET letters ===", dict(glet))
    print("\n=== FALSE_EXT proxy ===")
    print("engine bar_facts events=%d  golden false-arrows=%d  "
          "golden matched=%d" % (fx_n, gx_n, fx_hit))
    print("\n=== nulls ===")
    for k, v in nulls(rows).items():
        print("%-20s %d/%d = %.3f" % (k, v[0], v[1], v[0] / max(v[1], 1)))


if __name__ == "__main__":
    main()
