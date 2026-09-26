"""dr_arbiter_dump.py -- write the arbiter-fit dataset (one row per golden
cell): features of the keep-last-1 event pick + whether it hit + whether
the structural engines hit. For OFFLINE fitting elsewhere (Ruling 58:
no fitting on this PC)."""
import sys, os, pickle
HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PERC, "evalcheck"))

rows = pickle.load(open(os.path.join(HERE, "dr_rows.pkl"), "rb"))
d = pickle.load(open(os.path.join(PERC, "evalcheck",
                                  "_hybrid_rows_evalcheck.pkl"), "rb"))
key = lambda g: (g["panel"], g["tau"])
goldset = {key(r) for r in rows}
v1 = set(); hy = set(); v0 = set()
for cell in d["v1"]["tau"]:
    if (cell["panel"], cell["tau"]) in goldset and \
       cell["fhit"].get("box", {}).get(1):
        v1.add((cell["panel"], cell["tau"]))
for cell in d["hybrid"]["tau"]:
    if (cell["panel"], cell["tau"]) in goldset and \
       cell["fhit"].get("box", {}).get(1):
        hy.add((cell["panel"], cell["tau"]))
for cell in d["v0"]["tau"]:
    if (cell["panel"], cell["tau"]) in goldset and \
       cell["fhit"].get("box", {}).get(1):
        v0.add((cell["panel"], cell["tau"]))

out = []
for r in rows:
    p = [c for c in r["pool"] if c["avail"]]
    rec = {"panel": r["panel"], "tau": r["tau"],
           "n_avail": len(p), "abr_tau": r["abr_tau"],
           "v1_hit": key(r) in v1, "hy_hit": key(r) in hy,
           "v0_hit": key(r) in v0}
    if p:
        pick = max(p, key=lambda c: c["born"])
        rec.update({"ev_exists": 1, "ev_hit": int(pick["match"]),
                    "ev_age": pick["age_bars"], "ev_span": pick["span_bars"],
                    "ev_height": pick["height"], "ev_leg": pick["leg"],
                    "ev_prom": pick["prom"], "ev_route": pick["route"],
                    "ev_pxin": pick.get("px_in_box", 0),
                    "ev_bst": pick.get("bars_since_touch", 999),
                    "ev_ovl": pick.get("overlap_ratio", 0.0),
                    "ev_pxfrac": pick.get("px_frac", 0.5)})
    else:
        rec["ev_exists"] = 0
    out.append(rec)
with open(os.path.join(HERE, "arbiter_rows.pkl"), "wb") as fh:
    pickle.dump(out, fh, protocol=4)
print("rows:", len(out), "ev_hit:", sum(r.get("ev_hit", 0) for r in out),
      "v1:", sum(r["v1_hit"] for r in out),
      "hy:", sum(r["hy_hit"] for r in out),
      "v0:", sum(r["v0_hit"] for r in out))
