"""_m2_tv_score.py — M2-TV scoring (amended plan §7).

M2-TV precision = yes / (yes + no) over the 30 engine items, Wilson
95% CI; threshold .60 (R34).  Sensitivity counts cant_tell as no.
Golden yes-rate and negative no-rate reported descriptively (not
validity gates).  Per-family precision on engine items.

Usage: python _m2_tv_score.py [ANSWERS.md]
"""
import collections
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
KEY = os.path.join(HERE, "_owner_judge_key", "m2_tv_key.json")
DEFAULT_ANS = os.path.join(PERC, "owner_pack", "ANSWERS.md")


def wilson(k, n, z=1.959964):
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (p, max(0.0, (c - h) / d), min(1.0, (c + h) / d))


def parse_answers(path):
    out = {}
    for ln in open(path, encoding="utf-8", errors="replace"):
        m = re.match(r"\s*-?\s*(p\d+)\s*:\s*(\w+)", ln)
        if m:
            out[m.group(1)] = m.group(2).strip().lower()
            continue
        m = re.match(r"\s*(p\d+)\s*,\s*(\w+)", ln)
        if m:
            out[m.group(1)] = m.group(2).strip().lower()
    return out


def main():
    ans_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ANS
    key_path = sys.argv[2] if len(sys.argv) > 2 else KEY
    blob = json.load(open(key_path, encoding="utf8"))
    key = blob["key"]
    ans = parse_answers(ans_path)
    print("answers file:", ans_path)
    print("answered %d / %d items" % (len(ans), len(key)))
    blank = [s for s in key
             if ans.get(s) not in ("yes", "no", "cant_tell")]
    if blank:
        print("UNANSWERED:", ", ".join(blank))

    eng = {s: k for s, k in key.items()
           if k["truth"] in ("engine_hit", "engine_fp")}
    gold = {s: k for s, k in key.items() if k["truth"] == "golden"}
    neg = {s: k for s, k in key.items() if k["truth"] == "negative"}

    # ---- M2-TV: engine precision ----------------------------------
    yes = sum(1 for s in eng if ans.get(s) == "yes")
    no = sum(1 for s in eng if ans.get(s) == "no")
    ct = sum(1 for s in eng if ans.get(s) == "cant_tell")
    n_v = yes + no
    p, lo, hi = wilson(yes, n_v)
    p_s, lo_s, hi_s = wilson(yes, n_v + ct)   # cant_tell as no
    print("\n== M2-TV (engine items, n=%d) ==" % len(eng))
    print("yes=%d no=%d cant_tell=%d" % (yes, no, ct))
    print("precision yes/(yes+no) = %.3f  Wilson95 [%.3f, %.3f]"
          % (p, lo, hi))
    print("strict (cant_tell=no)  = %.3f  Wilson95 [%.3f, %.3f]"
          % (p_s, lo_s, hi_s))
    print("threshold .60: %s" %
          ("MET" if (p == p and p >= 0.60) else "NOT MET"))

    # ---- per-family precision -------------------------------------
    fam = collections.defaultdict(lambda: [0, 0, 0])
    for s, k in eng.items():
        f = k.get("family") or "?"
        a = ans.get(s)
        fam[f][0] += a == "yes"
        fam[f][1] += a == "no"
        fam[f][2] += a == "cant_tell"
    print("\nper-family (engine):")
    for f in sorted(fam):
        y, n_, c_ = fam[f]
        pf = wilson(y, y + n_)
        print("  %-7s yes=%-2d no=%-2d ct=%-2d  prec %.3f "
              "[%.3f, %.3f]" % (f, y, n_, c_, pf[0], pf[1], pf[2]))

    # ---- descriptive controls -------------------------------------
    gy = sum(1 for s in gold if ans.get(s) == "yes")
    gn_ = sum(1 for s in gold if ans.get(s) == "no")
    gct = sum(1 for s in gold if ans.get(s) == "cant_tell")
    nn = sum(1 for s in neg if ans.get(s) == "no")
    ny = sum(1 for s in neg if ans.get(s) == "yes")
    nct = sum(1 for s in neg if ans.get(s) == "cant_tell")
    print("\ngolden yes-rate (descriptive): %d/%d = %.3f"
          % (gy, len(gold), gy / max(len(gold), 1)))
    print("  (no=%d cant_tell=%d; sens-with-ct-as-no %.3f)"
          % (gn_, gct, gy / max(len(gold), 1)))
    print("negative no-rate (descriptive): %d/%d = %.3f"
          % (nn, len(neg), nn / max(len(neg), 1)))
    print("  (yes=%d cant_tell=%d)" % (ny, nct))

    # ---- engine_hit / engine_fp split (diagnostic only) ------------
    eh = {s for s, k in eng.items() if k["truth"] == "engine_hit"}
    ef = set(eng) - eh
    print("\nengine_hit yes %d/%d | engine_fp yes %d/%d (diagnostic)"
          % (sum(1 for s in eh if ans.get(s) == "yes"), len(eh),
             sum(1 for s in ef if ans.get(s) == "yes"), len(ef)))


if __name__ == "__main__":
    main()
