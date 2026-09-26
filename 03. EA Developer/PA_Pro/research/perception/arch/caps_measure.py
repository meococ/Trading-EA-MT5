"""caps_measure.py — ARCH rev2, review item 9 (measured maxima for caps).

Read-only count over the cached STABLE C-3 arm engines
(run_uip2_pbbirth_8361fe85e73f9437_*, 623 TUNE panel pickles in
evalcheck/_cache).  Unpickles each engine (post-A2 __setstate__ bridge
makes pre-A1 pickles load on the current tree) and reports per-run
maxima for every capacity the port plan proposes:

  n_objects        -> m_obj sizing (ids are append-order; never reuse)
  max_live         -> EDGE_BOARD / live arrays (reconstructed from
                      t_birth + first 'close' event per object)
  pool_end         -> per-family pool caps (residual) + proposals-per-
                      24-bar-window upper bound from cand_log
                      (TTL=24 stock; a cand occupies pool <= ttl bars)
  book.seq / alive -> pivot ring sizing
  origins          -> defended-origin registry sizing (never expires
                      for theta origins — review (f) item 1)
  births_per_bar   -> event-queue depth proxy (spawns+labels are
                      synchronous emissions inside one maintain call)
  labels_per_day   -> annot ledger sizing
  watch/hidden_ctx -> dict-order contract arrays

Run:  python heavy_run-wrapped:
  python tools/heavy_run.py --lane arch -- python arch/caps_measure.py
"""
import os
import pickle
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
sys.path.insert(0, PERC)

CACHE = os.path.join(PERC, "evalcheck", "_cache")
TAG = "run_uip2_pbbirth_8361fe85e73f9437_"
TTL = 24  # salience.cand_ttl_bars stock value (box.wait_ttl OFF)

FAM = {"BOX": "box", "RANGE_OPEN": "box", "CONTEXT_RANGE": "ctx",
       "PATTERN_LINE": "line", "CONTEXT_LINE": "ctx",
       "LEVEL_CARRIED": "level", "MINI_LEVEL": "level",
       "BRACKET": "bracket", "SQUEEZE": "squeeze",
       "LABEL_TF": "annot", "BAR_MARKER": "annot"}


def close_bar(o, n_bars):
    for ev in o.events:
        if ev[1] == "close":
            return ev[0]
    return n_bars


def main():
    files = sorted(f for f in os.listdir(CACHE)
                   if f.startswith(TAG) and f.endswith(".pkl"))
    agg = defaultdict(int)
    type_tot = Counter()
    per_run = []
    for f in files:
        e = pickle.load(open(os.path.join(CACHE, f), "rb"))
        n_bars = len(e.bars)
        agg["n_bars"] = max(agg["n_bars"], n_bars)
        agg["n_objects"] = max(agg["n_objects"], len(e.objects))
        agg["pool_end"] = max(agg["pool_end"], len(e.salience.pool))
        agg["seq"] = max(agg["seq"], len(e.book.seq))
        agg["alive"] = max(agg["alive"], len(e.book.alive()))
        agg["origins"] = max(agg["origins"], len(e.levels.origins))
        agg["watch"] = max(agg["watch"], len(e.boxes._watch))
        agg["hidden_ctx"] = max(agg["hidden_ctx"],
                               len(e.salience._hidden_ctx))
        for o in e.objects:
            type_tot[o.type] += 1

        # max concurrent ACTIVE: sweep birth/close intervals
        pts = []
        for o in e.objects:
            pts.append((o.t_birth, 1))
            pts.append((close_bar(o, n_bars), -1))
        pts.sort()
        cur = mx = 0
        for _, d in pts:
            cur += d
            mx = max(mx, cur)
        agg["max_live"] = max(agg["max_live"], mx)

        # births per bar per family -> event-queue depth proxy
        bpb = Counter()
        for o in e.objects:
            bpb[(o.t_birth, FAM.get(o.type, o.type))] += 1
        agg["births_bar"] = max(agg["births_bar"], max(bpb.values() or [0]))

        # pool-depth bound: proposals in any TTL-bar window, per family
        rows = [r for r in e.cand_log]
        byfam = defaultdict(list)
        for r in rows:
            byfam[FAM.get(r["kind"], r["kind"])].append(r["idx"])
        for fam, idxs in byfam.items():
            idxs.sort()
            j = 0
            for k, i in enumerate(idxs):
                while idxs[j] <= i - TTL:
                    j += 1
                agg["pool24_" + fam] = max(agg["pool24_" + fam], k - j + 1)

        # labels/day
        lab = sum(1 for o in e.objects if o.type == "LABEL_TF")
        agg["labels_run"] = max(agg["labels_run"], lab)
        per_run.append((f, len(e.objects), mx))

    per_run.sort(key=lambda r: -r[1])
    print("files:", len(files))
    for k in sorted(agg):
        print("%-14s %d" % (k, agg[k]))
    print("top object counts:", type_tot.most_common())
    print("worst runs (objects):", per_run[:5])


if __name__ == "__main__":
    main()
