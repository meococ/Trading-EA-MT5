"""scoreboard.py — mandate 3, Z4: append-only scoreboard.

One row per run, appended to SCOREBOARD.md (table) and
_scoreboard_rows.jsonl (machine-readable).  History is NEVER
rewritten: the script only appends.

Row contents (mandate Z4):
  utc, engine tag + code hash, ruler (eval_v2) hash,
  recall+precision per gated type (BOX, PATTERN_LINE, LEVEL_CARRIED),
  BOX `located`, funnel oracle BOX / PATTERN_LINE,
  live clutter (median live signal objects at golden decision times),
  snapshot recall (all types pooled).

Runtime: <= 2 min on a warm cache (full-panel eval runs + tau
snapshot runs are all cached under the engine hash).  `--quick`
skips the snapshot columns (em dashes) for a cold engine.

Usage:
  python evalcheck/scoreboard.py v0 | v1 | linelab [--quick]
"""
import argparse
import collections
import datetime
import json
import os
import sys
import types

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)

import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import eval_v2 as V2                            # noqa: E402
import cache as CA                              # noqa: E402
import funnel as F                              # noqa: E402
import pa_slots                                 # noqa: E402
from snapshot import tau_of, live_records, file_hash  # noqa: E402

MD = os.path.join(HERE, "SCOREBOARD.md")
ROWS = os.path.join(HERE, "_scoreboard_rows.jsonl")
GATED = ("BOX", "PATTERN_LINE", "LEVEL_CARRIED")

HDR = ("| utc | engine | eng_hash | ruler | BOX r/p | PL r/p | "
       "LC r/p | located | orcBOX | orcPL | clutter | snapR | "
       "lane | variant |")
SEP = "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"


def engine_for(tag):
    if tag == "v0":
        import engine_v0
        return engine_v0.PerceptionEngine, F.code_hash(F.V0_FILES)
    if tag == "v1":
        import engine
        return engine.PerceptionEngine, F.code_hash(F.V1_FILES)
    if tag == "linelab":
        sys.path.insert(0, os.path.join(PERC, "linelab"))
        import lines_lab
        return lines_lab.LineLabEngine, file_hash(
            os.path.join(PERC, "linelab", "lines_lab.py"))
    raise SystemExit("unknown engine tag %r" % tag)


def panel_cands(e, m, w0, w1):
    """cand_log -> engine-like records (same as box_ceiling)."""
    out = []
    for cd in e.cand_log or []:
        if cd["kind"] == "LABEL_TF":
            continue
        r = F.cand_as_record(cd, m, w0, w1)
        if r is not None:
            out.append(r)
    return out


def measure(cls, eng_hash, recs, quick=False, variant=""):
    """One engine over all panels -> scoreboard row dict."""
    gold_n = collections.Counter()
    hit_g = collections.Counter()
    eng_n = collections.Counter()
    hit_e = collections.Counter()
    loc_n = collections.Counter()
    loc_hit = collections.Counter()
    orc = collections.Counter()
    orc_g = collections.Counter()
    clutter = []
    snap_g = 0
    snap_h = 0
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        e = CA.run(eng_hash, cls, rec, variant=variant)
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        eobjs = V2.eng_objects(e, m, w0, w1)
        eboxes = [r for r in eobjs if r["type"] != "LABEL_TF"]
        pairs, _mp = C.match_panel(g2, eboxes, [], [], m,
                                   V2.match, V2.match_mark, V2.score)
        hg = {gi for gi, _ in pairs}
        he = {ei for _, ei in pairs}
        for gi, g in enumerate(g2):
            st = g["spec_type"]
            gold_n[st] += 1
            hit_g[st] += gi in hg
        for ei, er in enumerate(eboxes):
            eng_n[er["type"]] += 1
            hit_e[er["type"]] += ei in he
        for gi, g in enumerate(g2):
            if g["spec_type"] == "BOX" and gi not in hg:
                loc_n["BOX"] += 1
                loc_hit["BOX"] += any(
                    V2.box_located(g, er, m) for er in eboxes)
            elif g["spec_type"] == "BOX":
                loc_n["BOX"] += 1
                loc_hit["BOX"] += 1
        # funnel oracle: right proposal (cand_right) OR born-matched
        cands = panel_cands(e, m, w0, w1)
        for gi, g in enumerate(g2):
            st = g["spec_type"]
            if st not in ("BOX", "PATTERN_LINE"):
                continue
            orc_g[st] += 1
            same = [r for r in cands
                    if EV.FAMILY.get(r["type"]) ==
                    EV.FAMILY.get(st)]
            orc[st] += (gi in hg) or any(
                F.cand_right(g, r, m) for r in same)
        if quick:
            continue
        # snapshot recall + clutter at golden decision times
        by_tau = collections.defaultdict(list)
        for g in g2:
            tau = tau_of(g)
            if tau is None or tau < w0:
                continue
            by_tau[min(tau, w1)].append(g)
        for tau, gs in by_tau.items():
            rec_t = dict(rec)
            rec_t["window"] = dict(rec["window"], x1=tau)
            e_t = CA.run(eng_hash, cls, rec_t, variant=variant)
            eboxes_t, _em = live_records(e_t, m, w0, tau)
            clutter.append(len(eboxes_t))
            for g in gs:
                snap_g += 1
                snap_h += any(V2.match(g, er, m) for er in eboxes_t)
    row = {"rec": {}, "prec": {}, "located": {}, "oracle": {}}
    for st in sorted(set(gold_n) | set(eng_n)):
        row["rec"][st] = hit_g[st] / gold_n[st] if gold_n[st] else None
        row["prec"][st] = hit_e[st] / eng_n[st] if eng_n[st] else None
    for st in loc_n:
        row["located"][st] = loc_hit[st] / loc_n[st]
    for st in orc_g:
        row["oracle"][st] = orc[st] / orc_g[st]
    row["clutter"] = float(np.median(clutter)) if clutter else None
    row["snap_recall"] = (snap_h / snap_g) if snap_g else None
    return row


def fmt(v):
    return "%.2f" % v if v is not None else "—"


def rp(row, st):
    return "%s/%s" % (fmt(row["rec"].get(st)), fmt(row["prec"].get(st)))


def append_row(utc, tag, eng_hash, ruler_hash, row,
               lane="", variant=""):
    line = "| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |"\
        " %s | %s |" % (
            utc, tag, eng_hash[:8], ruler_hash[:8],
            rp(row, "BOX"), rp(row, "PATTERN_LINE"),
            rp(row, "LEVEL_CARRIED"),
            fmt(row["located"].get("BOX")),
            fmt(row["oracle"].get("BOX")),
            fmt(row["oracle"].get("PATTERN_LINE")),
            fmt(row["clutter"]), fmt(row["snap_recall"]),
            lane or "—", variant or "—")
    if not os.path.exists(MD):
        open(MD, "w", encoding="utf8").write(
            "# SCOREBOARD — append-only (mandate Z4)\n\n"
            "Command: `python evalcheck/scoreboard.py <v0|v1|linelab>"
            " [--quick]`  (add one row; history is never rewritten)\n\n"
            + HDR + "\n" + SEP + "\n")
    with open(MD, "a", encoding="utf8") as fh:
        fh.write(line + "\n")
    with open(ROWS, "a", encoding="utf8") as fh:
        fh.write(json.dumps({"utc": utc, "engine": tag,
                             "engine_hash": eng_hash,
                             "ruler_hash": ruler_hash,
                             "lane": lane, "variant": variant,
                             **row}) + "\n")
    return line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("engine", choices=["v0", "v1", "linelab"])
    ap.add_argument("--quick", action="store_true",
                    help="skip snapshot/clutter columns (cold engine)")
    ap.add_argument("--lane", default="",
                    help="owning lane (R14 §14.2), e.g. BUILD, LINE-LAB")
    ap.add_argument("--variant", default="",
                    help="A/B arm label; also keys the run cache")
    args = ap.parse_args()
    cls, eng_hash = engine_for(args.engine)
    ruler_hash = file_hash(os.path.join(HERE, "eval_v2.py"))
    recs = C.load_tune()
    with pa_slots.slot("evalcheck-scoreboard", timeout=600):
        row = measure(cls, eng_hash, recs, quick=args.quick,
                      variant=args.variant)
    utc = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%MZ")
    line = append_row(utc, args.engine, eng_hash, ruler_hash, row,
                      lane=args.lane, variant=args.variant)
    print(line)


if __name__ == "__main__":
    main()
