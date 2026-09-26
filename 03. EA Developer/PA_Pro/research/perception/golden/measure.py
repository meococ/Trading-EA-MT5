"""Q2 — TUNE measurements and drawn-vs-not-drawn candidate tables.

Two outputs per split:
  * golden measurements: per-object distributions in pips AND in ABR
    (height, span, touches, age, distance-to-price, slope, pokes) —
    the design notes' part (iv) input.
  * candidate scan: every structure the CURRENT engine produces on the
    panel's day up to the panel's right edge, labelled drawn/not-drawn
    by overlap with the repaired golden object.  The separation table
    (recency, distance, touches, EMA relation, session, lead-up move)
    is the DN_SALIENCE input.

Run:  python measure.py TUNE
"""
import json, os, sys, collections
import numpy as np

import validate as V
import textfeat as TF
import book_loader
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
import engine as ENG                             # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DRAFT = os.path.join(HERE, "draft")

LINE_TYPES = ("PATTERN_LINE", "CONTEXT_LINE")
BOX_TYPES = ("BOX", "RANGE_OPEN", "CONTEXT_RANGE")
LEVEL_TYPES = ("LEVEL_CARRIED", "MINI_LEVEL")


def abr20(day):
    r = day.h - day.l
    k = np.minimum(20, np.arange(1, len(day) + 1))
    cs = np.cumsum(r)
    out = np.empty(len(day))
    out[:20] = cs[:20] / np.arange(1, min(21, len(day) + 1))
    if len(day) > 20:
        out[20:] = (cs[20:] - cs[:-20]) / 20.0
    return out


def sess(m):
    return ("asia" if m < 480 else "eu_am" if m < 780 else "us"
            if m < 1020 else "late")


# ------------------------------------------------------------------ #
# golden measurements
# ------------------------------------------------------------------ #

def touches_on(day, idx, price, which):
    ext = day.h[idx] if which == "hi" else day.l[idx]
    return int((np.abs(ext - price) <= V.TOUCH_TOL).sum())


def golden_row(rec, o, day, abr):
    t0, t1 = o.get("t0"), o.get("t1")
    row = {"id": rec["id"], "type": o["spec_type"], "status": o["status"],
           "repair": o.get("repair_method"), "t0": t0, "t1": t1,
           "session": sess(t0) if t0 is not None else None,
           "span_min": (t1 - t0) if None not in (t0, t1) else None}
    j0 = day.idx(t0) if t0 is not None else None
    row["abr_birth"] = float(abr[j0]) if j0 is not None else None
    ty = o["spec_type"]
    if ty in BOX_TYPES and o.get("price_lo") is not None:
        lo, hi = o["price_lo"] / V.PIP, o["price_hi"] / V.PIP
        row["height_pips"] = hi - lo
        if row["abr_birth"]:
            row["height_abr"] = row["height_pips"] / row["abr_birth"]
        bs = o.get("build_start") or t0
        be = o.get("build_end") or t1
        idx = np.where(day.span(bs, be))[0]
        row["build_min"] = (be - bs) if None not in (bs, be) else None
        if len(idx):
            row["touch_top"] = touches_on(day, idx, hi, "hi")
            row["touch_bot"] = touches_on(day, idx, lo, "lo")
            pokes = int(((day.h[idx] > hi + V.TOUCH_TOL)
                         | (day.l[idx] < lo - V.TOUCH_TOL)).sum())
            row["n_pokes"] = pokes
            row["dist_edge_to_last"] = min(
                abs(day.c[idx[-1]] - lo), abs(day.c[idx[-1]] - hi))
    elif ty in LINE_TYPES and o.get("price0") is not None \
            and t0 is not None and t1 and t1 > t0:
        p0, p1 = o["price0"] / V.PIP, o["price1"] / V.PIP
        row["slope_pips"] = p1 - p0
        row["slope_per_hr"] = (p1 - p0) * 60.0 / max(t1 - t0, 1)
        if row["abr_birth"]:
            row["slope_abr"] = row["slope_pips"] / row["abr_birth"]
        idx = np.where(day.span(t0, t1))[0]
        if len(idx) >= 3:
            ts = day.m[idx].astype(float)
            vals = p0 + (p1 - p0) * (ts - t0) / (t1 - t0)
            d = np.minimum(np.abs(day.l[idx] - vals),
                           np.abs(day.h[idx] - vals))
            row["touches"] = int((d <= V.TOUCH_TOL).sum())
            row["dist_to_last"] = float(abs(day.c[idx[-1]] - vals[-1]))
    elif ty in LEVEL_TYPES and o.get("price") is not None:
        row["price"] = o["price"] / V.PIP
    return row


def q(x, ps=(10, 25, 50, 75, 90)):
    a = np.asarray([v for v in x if v is not None and np.isfinite(v)],
                   float)
    if not len(a):
        return None
    return {("p%d" % p): round(float(np.percentile(a, p)), 2)
            for p in ps} | {"n": len(a),
                            "mean": round(float(a.mean()), 2)}


# ------------------------------------------------------------------ #
# engine candidate scan
# ------------------------------------------------------------------ #

_TYPE_GROUPS = {
    "BOX": BOX_TYPES, "RANGE_OPEN": BOX_TYPES, "CONTEXT_RANGE": BOX_TYPES,
    "PATTERN_LINE": LINE_TYPES, "CONTEXT_LINE": LINE_TYPES,
    "LEVEL_CARRIED": LEVEL_TYPES, "MINI_LEVEL": LEVEL_TYPES,
    "BRACKET": ("BRACKET",), "SQUEEZE": ("SQUEEZE",),
    "LABEL_TF": ("BAR_MARKER", "LABEL_TF"),
}


def _overlap(a0, a1, b0, b1):
    lo, hi = max(a0, b0), min(a1, b1)
    return max(0, hi - lo) / float(max(a1 - a0, b1 - b0, 1))


def run_engine(day, w1):
    """Feed bars up to the panel edge.  Engine wants epochs where
    t%86400 == CET wall minute; the BOOK feed IS Berlin wall (D3), so a
    synthetic epoch cet_min*60 + day_base works.  cand_log captures the
    full evaluated-candidate universe (born + vetoed + dedup)."""
    e = ENG.PerceptionEngine()
    e.cand_log = []
    idx = np.where(day.m <= w1)[0]
    for j in idx:
        t = int(day.m[j]) * 60           # epoch-like: %86400 -> cet_min
        e.update(t, day.o[j] * V.PIP, day.h[j] * V.PIP, day.l[j] * V.PIP,
                 day.c[j] * V.PIP, cet_min=int(day.m[j]))
    return e


def _barmin(day, i):
    i = int(min(max(i, 0), len(day.m) - 1))
    return int(day.m[i])


_POINT_KINDS = {"LEVEL_CARRIED", "MINI_LEVEL", "LABEL_TF", "BAR_MARKER"}


def cand_span(day, c):
    """Candidate geometry (bar indices) -> wall-minute span."""
    idx = c["idx"]
    t0 = c.get("t_left", c.get("t0", idx))
    t1 = c.get("t1", idx)
    return _barmin(day, t0), _barmin(day, t1)


def cand_band(c):
    """Candidate price band in pips, or (None, None)."""
    k = c["kind"]
    if c.get("lo") is not None:
        return c["lo"], c["hi"]
    if c.get("bottom") is not None:
        return c["bottom"], c["top"]
    if c.get("price") is not None:
        return c["price"], c["price"]
    if c.get("level") is not None:
        return c["level"], c["level"]
    if c.get("p0") is not None:
        p1 = c["p0"] + c.get("slope", 0.0) * (c["idx"] - c.get("t0",
                                                              c["idx"]))
        return min(c["p0"], p1), max(c["p0"], p1)
    return None, None


def _gold_prices(g):
    return [p / V.PIP for p in
            (g.get("price_lo"), g.get("price_hi"), g.get("price"),
             g.get("price0"), g.get("price1")) if p is not None]


def _price_near(band, gp, tol=4.0):
    lo, hi = band
    if lo is None or not gp:
        return False
    if any(lo <= p <= hi for p in gp):
        return True
    return min(min(abs(lo - p), abs(hi - p)) for p in gp) <= tol


def candidate_rows(rec, day, gold):
    """Label every evaluated candidate (cand_log) against the golden
    set: drawn iff a usable golden object of the same type-group shares
    the span and price zone.

    fwd_* analysis labels (post-birth forward range/move) were WITHDRAWN
    under Addendum 4 A4.2 (Ruling 5b): forward-move measurements on BOOK
    bars are outcome-type and forbidden.  Columns removed; the causal
    salience correlates (compression, n_active, session) remain."""
    w1 = rec["window"]["x1"] or 1439
    e = run_engine(day, w1)
    last_close = float(day.c[np.where(day.m <= w1)[0][-1]])
    rows = []
    for c in (e.cand_log or []):
        m0, m1 = cand_span(day, c)
        mb = c.get("cet_min") or _barmin(day, c["idx"])
        plo, phi = cand_band(c)
        group = _TYPE_GROUPS.get(c["kind"], (c["kind"],))
        point = c["kind"] in _POINT_KINDS
        best_iou, hit = 0.0, None
        for gi, g in enumerate(gold):
            if g["spec_type"] not in group or g["status"] == "unusable":
                continue
            gt0 = g.get("t0")
            gt1 = g.get("t1") or gt0
            if gt0 is None:
                continue
            gp = _gold_prices(g)
            pok = _price_near((plo, phi), gp)
            if point:
                iou = 0.0
                tok = (gt0 - 90) <= mb <= (gt1 + 90)
                ok = tok and pok
            else:
                iou = _overlap(m0, m1, gt0, gt1)
                ok = iou >= 0.25 or (iou > 0 and pok)
            if ok and (hit is None or iou > best_iou or pok):
                best_iou = max(best_iou, iou)
                hit = (gi, g["spec_type"])
        row = {
            "id": rec["id"], "date": rec["date"], "kind": c["kind"],
            "route": c["route"],
            "outcome": c["outcome"], "m0": m0, "m1": m1, "mb": mb,
            "span_min": m1 - m0, "session": sess(mb),
            "plo": plo, "phi": phi, "abr": c.get("abr"),
            "ema_gap": (round((plo + phi) / 2 - c["ema"], 2)
                        if plo is not None and c.get("ema") is not None
                        else None),
            "since_birth_min": c.get("since_birth_min"),
            "n_active": c.get("n_active"),
            "nearest_struct_pips": c.get("nearest_struct_pips"),
            "dist_to_price": (min(abs(last_close - plo),
                                  abs(last_close - phi))
                              if plo is not None else None),
            "n_touches": c.get("n_touches"),
            "drawn": hit is not None,
            "gold": "%s#%d(%s)" % (rec["id"], hit[0], hit[1])
            if hit else None,
            "iou": round(best_iou, 2),
        }
        # edge touches over the candidate's own span (causal, bar-based)
        if plo is not None and not point:
            idx2 = np.where(day.span(m0, m1))[0]
            if len(idx2):
                row["edge_touches"] = int(
                    (np.abs(day.h[idx2] - phi) <= V.TOUCH_TOL).sum() +
                    (np.abs(day.l[idx2] - plo) <= V.TOUCH_TOL).sum())
        rows.append(row)
    return rows


# ------------------------------------------------------------------ #

def main(argv):
    split = (argv[0] if argv else "TUNE").upper()
    s, e = V.SPLITS[split]
    recs = [json.loads(l) for l in
            open(os.path.join(DRAFT, "BOOK2012_%s_v2.jsonl" % split),
                 encoding="utf8")]
    days = V.load_days(s, e)

    grows, crows = [], []
    for rec in recs:
        day = days.get(rec["date"])
        if day is None or not len(day):
            continue
        abr = abr20(day)
        gold = [o for o in rec["objects"]
                if o["status"] in ("ok", "repaired", "time_only")]
        for o in rec["objects"]:
            if o["status"] in ("ok", "repaired"):
                grows.append(golden_row(rec, o, day, abr))
        crows.extend(candidate_rows(rec, day, gold))

    with open(os.path.join(DRAFT, "measure_%s.jsonl" % split), "w",
              encoding="utf8") as f:
        for r in grows:
            f.write(json.dumps(r) + "\n")
    with open(os.path.join(DRAFT, "candidates_%s.jsonl" % split), "w",
              encoding="utf8") as f:
        for r in crows:
            f.write(json.dumps(r) + "\n")

    # ---- print the two tables ------------------------------------ #
    print("== GOLDEN measurements (%s) ==" % split)
    by = collections.defaultdict(list)
    for r in grows:
        by[r["type"]].append(r)
    for ty in sorted(by):
        rows = by[ty]
        print("\n### %s (n=%d)" % (ty, len(rows)))
        for k in ("height_pips", "height_abr", "span_min", "build_min",
                  "touch_top", "touch_bot", "n_pokes", "dist_edge_to_last",
                  "slope_pips", "slope_per_hr", "slope_abr", "touches",
                  "dist_to_last", "abr_birth"):
            qq = q([r.get(k) for r in rows])
            if qq:
                print("  %-18s %s" % (k, qq))

    print("\n== CANDIDATE UNIVERSE (%s) ==" % split)
    # panels share days: dedupe the same physical evaluation counted
    # once per overlapping panel run (identical day/kind/bar/outcome)
    seen = {}
    for r in crows:
        key = (r["date"], r["kind"], r["mb"], r["route"],
               round(r["plo"] or 0, 1), round(r["phi"] or 0, 1))
        if key in seen:
            seen[key]["drawn"] = seen[key]["drawn"] or r["drawn"]
        else:
            seen[key] = r
    urows = list(seen.values())
    print("(raw %d rows -> %d unique day-candidates)"
          % (len(crows), len(urows)))
    by = collections.defaultdict(list)
    for r in urows:
        by[r["kind"]].append(r)
    for ty in sorted(by):
        rows = by[ty]
        oc = collections.Counter(r["outcome"] for r in rows)
        print("\n### %s  n=%d  %s" % (ty, len(rows), dict(oc)))
        rt = collections.defaultdict(collections.Counter)
        for r in rows:
            rt[r["route"]][r["outcome"]] += 1
        for route in sorted(rt):
            print("  %-28s %s" % (route, dict(rt[route])))
        for outcome in sorted(oc):
            sel = [r for r in rows if r["outcome"] == outcome]
            nd = sum(r["drawn"] for r in sel)
            print("  %-28s n=%-4d drawn=%-4d (%.0f%%)"
                  % ("  " + outcome, len(sel), nd,
                     100.0 * nd / max(1, len(sel))))

    print("\n== DRAWN vs NOT-DRAWN (born objects, %s) ==" % split)
    by = collections.defaultdict(lambda: {"d": [], "n": []})
    for r in urows:
        if r["outcome"] != "born":
            continue
        by[r["kind"]]["d" if r["drawn"] else "n"].append(r)
    for ty in sorted(by):
        d, n = by[ty]["d"], by[ty]["n"]
        print("\n### %s  drawn=%d ignored=%d" % (ty, len(d), len(n)))
        for k in ("span_min", "n_touches", "edge_touches", "abr",
                  "ema_gap", "dist_to_price", "since_birth_min",
                  "n_active", "nearest_struct_pips"):
            print("  %-20s drawn %s | ignored %s"
                  % (k, q([r.get(k) for r in d]),
                     q([r.get(k) for r in n])))
        sd = collections.Counter(r["session"] for r in d)
        sn = collections.Counter(r["session"] for r in n)
        print("  session        drawn %s | ignored %s"
              % (dict(sd), dict(sn)))

    # golden coverage: usable golden object -> any candidate matched it
    print("\n== GOLDEN COVERAGE (%s) ==" % split)
    cov = collections.defaultdict(lambda: [0, 0])
    covered = set(r["gold"] for r in crows if r["gold"])
    for rec in recs:
        gold = [o for o in rec["objects"]
                if o["status"] in ("ok", "repaired", "time_only")]
        for gi, o in enumerate(gold):
            cov[o["spec_type"]][1] += 1
            if "%s#%d(%s)" % (rec["id"], gi, o["spec_type"]) in covered:
                cov[o["spec_type"]][0] += 1
    for ty in sorted(cov):
        n, tot = cov[ty]
        print("  %-16s covered %d/%d (%.0f%%)"
              % (ty, n, tot, 100.0 * n / max(1, tot)))


if __name__ == "__main__":
    main(sys.argv[1:])
