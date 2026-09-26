"""run_kat.py — shared known-answer suite (mandate item 5).

Two uses of the same fixtures:

  RULER test (gates at 100%): expected objects, converted to engine
  records, must ALL match themselves under eval_v2; every listed
  negative must NOT match.  Checks the ruler's discrimination, not the
  engine's.

  ENGINE test (reported, non-gating): each engine runs the fixture
  bars; pass = every expected object/mark matched by born output under
  eval_v2 AND no born output matches any negative.

Usage: python evalcheck/kat/run_kat.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))       # evalcheck/
sys.path.insert(0, os.path.join(os.path.dirname(HERE), ".."))

import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import eval_v2 as V2                            # noqa: E402
import fixtures as F                            # noqa: E402


def _as_engine(g, m, w0, w1):
    e = C.gold_as_engine(g, m)
    e["w0"], e["w1"] = w0, w1
    return e


def _as_mark_engine(gm, w0):
    return {"type": "LABEL_TF", "t_birth": gm["t"], "side": gm["side"],
            "price": None, "letter": gm.get("letter"),
            "w0": w0, "w1": 10 ** 9}


def ruler_check(fx):
    t, m, o, h, l, c = fx["series"]
    w0, w1 = int(m[0]), int(m[-1])
    ok, fail = [], []
    for g in fx["expected"]:
        e = _as_engine(g, m, w0, w1)
        (ok if V2.match(g, e, m) else fail).append(
            ("pos", g["spec_type"]))
    for gm in fx.get("expected_marks", []):
        em = _as_mark_engine(gm, w0)
        (ok if V2.match_mark(gm, em) else fail).append(
            ("pos", "LABEL_TF"))
    for g in fx.get("negatives", []):
        e = _as_engine(g, m, w0, w1)
        for gpos in fx["expected"]:
            if EV.FAMILY.get(gpos["spec_type"]) != \
                    EV.FAMILY.get(g["spec_type"]):
                continue
            if V2.match(gpos, e, m):
                fail.append(("neg", g["spec_type"]))
    for gm in fx.get("neg_marks", []):
        em = _as_mark_engine(gm, w0)
        for gpos in fx.get("expected_marks", []):
            if V2.match_mark(gpos, em):
                fail.append(("neg", "LABEL_TF"))
    return ok, fail


def engine_check(fx, cls):
    t, m, o, h, l, c = fx["series"]
    w1 = int(m[-1])
    w0 = int(m[0])
    e = EV.run_engine(cls, m, t, o, h, l, c, w1)
    eobjs = V2.eng_objects(e, m, w0, w1)
    emarks = [r for r in eobjs if r["type"] == "LABEL_TF"]
    eboxes = [r for r in eobjs if r["type"] != "LABEL_TF"]
    misses, hits = [], 0
    for g in fx["expected"]:
        if any(V2.match(g, er, m) for er in eboxes):
            hits += 1
        else:
            misses.append(g["spec_type"])
    for gm in fx.get("expected_marks", []):
        if any(V2.match_mark(gm, em) for em in emarks):
            hits += 1
        else:
            misses.append("LABEL_TF:" + str(gm.get("letter")))
    fp = []
    for g in fx.get("negatives", []):
        ge = _as_engine(g, m, w0, w1)
        for er in eboxes:
            if EV.FAMILY.get(er["type"]) != EV.FAMILY.get(g["spec_type"]):
                continue
            if V2.match(g, er, m):
                fp.append((g["spec_type"], er.get("id")))
    for gm in fx.get("neg_marks", []):
        em = _as_mark_engine(gm, w0)
        for er in emarks:
            if V2.match_mark(gm, er):
                fp.append(("LABEL_TF", er.get("id")))
    return hits, misses, fp, len(eobjs)


def main():
    import engine as ENG_V1
    import engine_v0 as ENG_V0

    print("=" * 60)
    print("KAT — ruler test (gates at 100%)")
    print("=" * 60)
    all_ok = True
    for f in F.FIXTURES:
        fx = f()
        ok, fail = ruler_check(fx)
        status = "PASS" if not fail else "FAIL %s" % fail
        all_ok &= not fail
        print("  %-14s pos=%d neg-probes ok   %s"
              % (fx["name"], len(ok), status))
    print("ruler: %s" % ("ALL PASS" if all_ok else "FAILURES ^^"))

    print()
    print("=" * 60)
    print("KAT — engine test (diagnostic, non-gating)")
    print("=" * 60)
    for tag, cls in (("v0", ENG_V0.PerceptionEngine),
                     ("v1", ENG_V1.PerceptionEngine)):
        for f in F.FIXTURES:
            fx = f()
            hits, misses, fp, nobj = engine_check(fx, cls)
            n_exp = len(fx["expected"]) + len(fx.get("expected_marks",
                                                   []))
            status = "pass" if hits == n_exp and not fp else "FAIL"
            print("  %s %-14s %s  expected %d/%d  miss=%s  fp=%s  "
                  "objects=%d"
                  % (tag, fx["name"], status, hits, n_exp,
                     misses or "-", fp or "-", nobj))


if __name__ == "__main__":
    main()
