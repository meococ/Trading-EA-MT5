"""R83 s.83.4 ARM Y prefix-invariance (corrected comparator).

Project definition (_idchk_tt.py): canonical() at bar k inside the
full run == canonical() of the stop-at-k engine.  Run per arm:
  python _y_prefix.py 1|2
"""
import collections
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "evalcheck"))
sys.path.insert(0, HERE)

import eval as EV                      # noqa: E402
import cache as CA                     # noqa: E402
import engine as ENG                   # noqa: E402
import common as C                     # noqa: E402

P = json.load(open(os.path.join(HERE, "params_v1_1.json"),
                   encoding="utf8"))["params"]
DR = os.path.join(HERE, "deepresearch")


def main():
    flag = int(sys.argv[1])
    recs = list(C.load_tune())
    events = [json.loads(x) for x in open(
        os.path.join(DR, "DR_RULES_events.jsonl"), encoding="utf8")]
    obj_events = [e for e in events if e["is_tau_event"]]
    taus_by_panel = collections.defaultdict(set)
    for ev in obj_events:
        taus_by_panel[ev["panel"]].add(ev["tau"])

    n_ok = n_tot = 0
    for rec in recs[:20]:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        taus = sorted(taus_by_panel.get(rec["id"], ()))
        if not taus:
            continue
        # floor-bar per tau: the bar e_s sees last (m[j] <= tau)
        j_of_tau = {tau: int(np.where(m <= tau)[0][-1])
                    for tau in taus}
        snap_at = {j_of_tau[tau]: tau for tau in taus}
        idx = np.where(m <= w1)[0]
        e2 = ENG.PerceptionEngine(dict(P, box_yield=flag))
        e2.w0_min = int(w0)
        e2.cand_log = []
        snap = {}
        for j in idx:
            e2.update(int(t[j]), float(o[j]) * 1e-4, float(h[j]) * 1e-4,
                      float(l[j]) * 1e-4, float(c[j]) * 1e-4,
                      cet_min=int(m[j]))
            if j in snap_at:
                snap[snap_at[j]] = CA.canonical(e2)
        for tau in taus:
            eng = lambda: ENG.PerceptionEngine(  # noqa: E731
                dict(P, box_yield=flag))
            e_s = EV.run_engine(eng, m, t, o, h, l, c, tau, w0=w0)
            n_tot += 1
            ok = CA.canonical(e_s) == snap[tau]
            n_ok += bool(ok)
            if not ok:
                print("  PREFIX DIFF y%d %s@%d" % (flag, rec["id"], tau))
    print("y%d prefix invariance: %d/%d" % (flag, n_ok, n_tot))


if __name__ == "__main__":
    main()
