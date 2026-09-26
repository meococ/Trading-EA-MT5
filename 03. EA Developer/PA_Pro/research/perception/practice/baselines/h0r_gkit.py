"""h0r_gkit.py — R82 s82.6 step 5: G-KIT override for a passing H0-R
arm.

For each of the 12 fixed review panels (review/review_panels.json):
base = exactly the objects in review/sets/c3/<panel>.json with the
substituted family removed, plus the arm's LIVE objects at the review
tau (die rules applied; the arm's own pick gate applied — an object
failing C1@1.0 is not an arm object).

Base objects are carried verbatim (id/type/geometry/times), only
re-spelled from the c3-set schema to the override item spelling
(HOWTO.md): kind, t0/t1 CET minutes, raw prices, letter/side.

Usage (PA_Pro cwd):
  python research/perception/practice/baselines/h0r_gkit.py a
Output: practice/H0R_<arm>_objects.jsonl
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PRACTICE = os.path.dirname(HERE)
PERC = os.path.dirname(PRACTICE)
for _p in (os.path.join(PERC, "evalcheck"), PERC,
           os.path.join(PERC, "deepresearch"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import eval as EV                               # noqa: E402
import cache as CA                              # noqa: E402
import DR_RULES_measure as M                    # noqa: E402
import DR_RULES_baselines as FB                 # noqa: E402
import h0_hybrid as H0                          # noqa: E402
import h0r_hybrid as HR                         # noqa: E402

PIP = 1e-4
REVIEW = os.path.join(PERC, "review")
ARMS = {"a": {"level": ("donchian", "C1@1.0")},
        "b": {"line": ("tdlines", "C7@2")},
        "c": {"level": ("donchian", "C1@1.0"),
              "line": ("tdlines", "C7@2")}}


def set_to_item(o):
    """c3-set object -> override item spelling (verbatim carry)."""
    it = {"kind": o["type"], "id": o.get("id"),
          "state": o.get("state", "ACTIVE"),
          "t0": o.get("t0_min"), "t1": o.get("t1_min")}
    for k in ("letter", "side"):
        if o.get(k) is not None:
            it[k] = o[k]
    if o.get("lo_raw") is not None:
        it["lo"], it["hi"] = o["lo_raw"], o["hi_raw"]
    if o.get("price_raw") is not None:
        it["price"] = o["price_raw"]
    if o.get("p0_raw") is not None:
        it["p0"] = o["p0_raw"]
        if o.get("slope") is not None:
            it["slope"] = o["slope"]
            it["t0_bar"] = o.get("anchor_bar", 0)
        elif o.get("p1_raw") is not None:
            it["p1"] = o["p1_raw"]
    return it


def arm_item(x, fam, tau):
    """Baseline died object -> override item spelling."""
    it = {"kind": x["type"], "id": x.get("id", "h0r"),
          "state": "ACTIVE",
          "t0": int(x["birth_drawn"]),
          "t1": int(min(x["die"], tau) if x["die"] is not None
                    else tau)}
    if x.get("side") is not None:
        it["side"] = x["side"]
    if fam == "level":
        it["price"] = x["price"] * PIP
    else:
        it["p0"] = x["p0"] * PIP
        it["slope"] = x["slope"]
        it["t0_bar"] = x["t0_bar"]
    return it


def main(arm):
    panels = json.load(open(os.path.join(REVIEW, "review_panels.json"),
                            encoding="utf8"))["panels"]
    subs = ARMS[arm]
    day_cache = {}
    rows = []
    for p in panels:
        pid, date, tau = p["panel"], p["date"], p["tau"]
        base = json.load(open(os.path.join(REVIEW, "sets", "c3",
                                           pid + ".json"),
                              encoding="utf8"))
        fams = set(subs)
        keep = [o for o in base["objects"]
                if EV.FAMILY.get(o["type"]) not in fams]
        objs = [set_to_item(o) for o in keep]
        # ---- arm live objects at tau -------------------------------
        if date not in day_cache:
            abr50 = CA.abr(date)
            t, m, o, h, l, c = CA.bars(date)
            day_cache[date] = {
                nm: fn(t, np.asarray(m), o, h, l, c, abr50) or []
                for nm, fn in H0.EMITS.items()}
        e = M.pickled(date, tau)
        n_added = 0
        if e is not None:
            mp = np.array([b["cet_min"] for b in e.bars])
            hp = np.array([b["h"] for b in e.bars])
            lp = np.array([b["l"] for b in e.bars])
            cp = np.array([b["c"] for b in e.bars])
            abr = np.asarray(e.abr)
            ema = np.asarray(e.ema)
            pivots = e.book.seq
            nfed = len(e.bars) - 1
            j1 = min(M.jle(mp, tau), nfed)
            for fam, (src, rule) in subs.items():
                died, _v = HR.apply_dies(day_cache[date][src], fam,
                                         mp, hp, lp, cp, abr)
                for x in died:
                    if x["birth"] > tau or (x["die"] is not None
                                            and x["die"] <= tau):
                        continue
                    ft = FB.feats(x, fam, j1, mp, cp, ema, abr,
                                  pivots, nfed)
                    if ft is not None and not FB.passes(
                            ft, fam, rule, {}):
                        continue
                    objs.append(arm_item(x, fam, tau))
                    n_added += 1
        rows.append({"panel": pid, "tau": int(tau), "objects": objs})
        print("%s: %d base kept, +%d arm objects (total %d)"
              % (pid, len(keep), n_added, len(objs)))
    out = os.path.join(PRACTICE, "H0R_%s_objects.jsonl" % arm)
    with open(out, "w", encoding="utf8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "a")
