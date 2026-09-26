"""R78 s.78.4(3) TT identity check: trade_tags ON vs OFF must be
byte-identical canonical() on every TUNE panel (facts excluded from
canonical, tags never alter objects).  Also verifies:
  - ON writes facts on live objects; OFF writes none.
  - prefix invariance on 5 real panels: facts at bar k identical
    whether the run stops at k or continues.
OFF == parent C-3 canonical is covered by _idchk_c3.py (default
params have trade_tags=0).
"""
import sys, os, re, glob
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "evalcheck"))
sys.path.insert(0, _HERE)
import eval as EV, engine as ENG, common as C, cache as CA
import numpy as np

import json
P = json.load(open(os.path.join(_HERE, "params_v1_1.json"),
                   encoding="utf8"))["params"]

PAT = re.compile(r"run_uip2_pbbirth_8361fe85e73f9437_"
                 r"(\d{4}-\d{2}-\d{2})_(\d+)\.pkl$")
# the canonical 623 TUNE windows (cache filename grid, same as
# _idchk_full.py - covers more than the 198 eval recs)
PANELS = sorted((m.group(1), int(m.group(2)))
                for m in (PAT.search(f) for f in glob.glob(
                    os.path.join(_HERE, "evalcheck", "_cache",
                                 "run_uip2_pbbirth_8361fe85e73f9437_"
                                 "*.pkl"))) if m)
W0 = {}                     # date -> w0_min from the ref pickle
import pickle
for _d, _w in PANELS:
    if _d not in W0:
        W0[_d] = {}


def run(date, w1, flag):
    t, m, o, h, l, c = EV.day_bars(date)
    e = ENG.PerceptionEngine(dict(P, trade_tags=flag))
    w0 = W0[date].get(w1)
    if w0 is None:
        f = os.path.join(_HERE, "evalcheck", "_cache",
                         "run_uip2_pbbirth_8361fe85e73f9437_%s_%s.pkl"
                         % (date, w1))
        try:
            ref = pickle.load(open(f, "rb"))
            w0 = getattr(ref, "w0_min", None)
        except Exception:
            w0 = None
        W0[date][w1] = w0
    e.w0_min = int(w0) if w0 is not None else None
    e.cand_log = []
    for j in np.where(m <= w1)[0]:
        e.update(int(t[j]), float(o[j]) * 1e4, float(h[j]) * 1e4,
                 float(l[j]) * 1e4, float(c[j]) * 1e4,
                 cet_min=int(m[j]))
    return e


ident = diff = 0
nfacts_on = nfacts_off = 0
print("panels:", len(PANELS))
for date, w1 in PANELS:
    e_on = run(date, w1, 1)
    e_off = run(date, w1, 0)
    if CA.canonical(e_on) == CA.canonical(e_off):
        ident += 1
    else:
        diff += 1
        print("DIFF ON/OFF", date, w1)
    nfacts_on += sum(1 for ob in e_on.objects
                     if ob.facts.get("trade_tags"))
    nfacts_off += sum(1 for ob in e_off.objects
                      if ob.facts.get("trade_tags"))
print("ON==OFF canonical:", ident, "| diff:", diff,
      "| facts on:", nfacts_on, "| facts off:", nfacts_off)

# ---- prefix invariance on 5 real panels --------------------------------
pin = 0
for date, w1 in PANELS[:5]:
    t, m, o, h, l, c = EV.day_bars(date)
    idx = np.where(m <= w1)[0]
    k = len(idx) // 2                      # mid-panel cutoff
    e = ENG.PerceptionEngine(dict(P, trade_tags=1))
    e.cand_log = []
    for j in idx[:k + 1]:
        e.update(int(t[j]), float(o[j]) * 1e4, float(h[j]) * 1e4,
                 float(l[j]) * 1e4, float(c[j]) * 1e4,
                 cet_min=int(m[j]))
    mid = {ob.id: ob.facts.get("trade_tags") for ob in e.active()}
    # replay the same prefix inside a full run
    e2 = ENG.PerceptionEngine(dict(P, trade_tags=1))
    e2.cand_log = []
    mid2 = None
    for j in idx:
        e2.update(int(t[j]), float(o[j]) * 1e4, float(h[j]) * 1e4,
                  float(l[j]) * 1e4, float(c[j]) * 1e4,
                  cet_min=int(m[j]))
        if j == idx[k]:
            mid2 = {ob.id: ob.facts.get("trade_tags")
                    for ob in e2.active()}
    assert mid == mid2, "prefix divergence %s %s" % (date, w1)
    pin += 1
print("prefix invariance panels:", pin, "PASS")
