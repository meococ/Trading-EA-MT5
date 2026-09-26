"""R83 s.83.4 ARM Y override writer (build-owned).

For the chosen variant flag (box_yield=N), run a fresh engine on each
of the 12 review panels (review/review_panels.json) and dump the full
drawn set at the review tau -> overrides/Y<n>_objects.jsonl in the
review/HOWTO.md schema (one row per panel, engine spelling =
Obj.to_dict() verbatim: day-bar indices, pips).

Usage: python _y_override.py 1|2
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "evalcheck"))
sys.path.insert(0, HERE)

import eval as EV                      # noqa: E402
import cache as CA                     # noqa: E402
import engine as ENG                   # noqa: E402
import common as C                     # noqa: E402

P = json.load(open(os.path.join(HERE, "params_v1_1.json"),
                   encoding="utf8"))["params"]


def main():
    flag = int(sys.argv[1])
    assert flag in (1, 2)
    panels = json.load(open(os.path.join(
        HERE, "review", "review_panels.json"), encoding="utf8"))
    recs = {r["id"]: r for r in C.load_tune()}
    out_dir = os.path.join(HERE, "overrides")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "Y%d_objects.jsonl" % flag)
    eng = lambda: ENG.PerceptionEngine(dict(P, box_yield=flag))  # noqa
    rows = []
    for p in panels["panels"]:
        rec = recs[p["panel"]]
        w0 = rec["window"]["x0"]
        tau = int(p["tau"])
        t, m, o, h, l, c = CA.bars(rec["date"])
        e = EV.run_engine(eng, m, t, o, h, l, c, tau, w0=w0)
        objs = [ob.to_dict() for ob in e.objects]
        rows.append(dict(panel=p["panel"], tau=tau, objects=objs))
        print("%-7s tau=%-4d objects=%d" % (p["panel"], tau, len(objs)))
    with open(out, "w", encoding="utf8") as f:
        for r in rows:
            f.write(json.dumps(r, default=str) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
