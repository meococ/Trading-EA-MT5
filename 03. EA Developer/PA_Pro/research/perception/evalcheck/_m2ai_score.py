"""EVAL-AUDIT M2-AI scorer (R76 s.76.3): score the two blind AI judges
against the sealed key.  Also recomputes inter-judge kappa.

(a) per judge: precision on 48 engine items = yes/(yes+no), cant_tell
    reported separately AND counted as no (both variants printed);
    yes-rate on engine_hit (11) vs engine_fp (37).
(b) judge validity gates (pre-registered by Lead): golden yes-rate
    >= 0.60 AND negative no-rate >= 0.80 -> credible.
(c) Cohen's kappa, 3-class and yes-vs-not-yes; both-agree-vs-key.

Usage: python evalcheck/_m2ai_score.py
"""
import csv
import json
import math
import os
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
KEY = os.path.join(HERE, "_owner_judge_key", "m2_c3_key.json")
JDIR = os.path.join(PERC, "owner_pack", "ai_judges")
JUDGES = {"linh": "answers_linh.csv", "judgeB": "answers_judgeB.csv"}


def wilson(k, n, z=1.959964):
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (p, max(0.0, (c - h) / d), min(1.0, (c + h) / d))


def load_answers(path):
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out[row["seq"].strip()] = row["answer"].strip().lower()
    return out


def kappa(a, b, cats):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca = collections.Counter(a)
    cb = collections.Counter(b)
    pe = sum((ca[c] / n) * (cb[c] / n) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan"), po


def main():
    key = json.load(open(KEY))["key"]
    ans = {j: load_answers(os.path.join(JDIR, f)) for j, f in JUDGES.items()}

    def cls(seq):
        t = key[seq]["truth"]
        return "engine" if t.startswith("engine_") else t

    print("=== M2-AI (proxy, rubric v1) ===")
    for j, a in ans.items():
        eng = [a.get(s, "") for s in key if cls(s) == "engine"]
        gold = [a.get(s, "") for s in key if cls(s) == "golden"]
        neg = [a.get(s, "") for s in key if cls(s) == "negative"]
        yes = eng.count("yes"); no = eng.count("no"); ct = eng.count("cant_tell")
        p1, l1, h1 = wilson(yes, len(eng))                    # yes/all (cant_tell=no)
        p2, l2, h2 = wilson(yes, yes + no)                    # yes/(yes+no)
        gs, gl, gh = wilson(gold.count("yes"), len(gold))
        ns, nl, nh = wilson(neg.count("no"), len(neg))
        hit = [a.get(s, "") for s in key if key[s]["truth"] == "engine_hit"]
        fp = [a.get(s, "") for s in key if key[s]["truth"] == "engine_fp"]
        hp, hl, hh = wilson(hit.count("yes"), len(hit))
        fp_p, fp_l, fp_h = wilson(fp.count("yes"), len(fp))
        cred = gs >= 0.60 and ns >= 0.80
        print("\n-- judge %s --" % j)
        print("  precision yes/(yes+no) : %d/%d = %.3f [%.3f, %.3f]"
              % (yes, yes + no, p2, l2, h2))
        print("  precision yes/all (ct=no): %d/%d = %.3f [%.3f, %.3f] "
              "(cant_tell=%d)" % (yes, len(eng), p1, l1, h1, ct))
        print("  golden sens : %d/%d = %.3f [%.3f, %.3f]"
              % (gold.count("yes"), len(gold), gs, gl, gh))
        print("  neg spec    : %d/%d = %.3f [%.3f, %.3f]"
              % (neg.count("no"), len(neg), ns, nl, nh))
        print("  engine_hit yes : %d/%d = %.3f [%.3f, %.3f]"
              % (hit.count("yes"), len(hit), hp, hl, hh))
        print("  engine_fp  yes : %d/%d = %.3f [%.3f, %.3f]"
              % (fp.count("yes"), len(fp), fp_p, fp_l, fp_h))
        print("  CREDIBLE: %s (gates golden>=.60, neg>=.80)" % cred)

    seqs = sorted(key)
    a3 = [ans["linh"].get(s, "?") for s in seqs]
    b3 = [ans["judgeB"].get(s, "?") for s in seqs]
    k3, po3 = kappa(a3, b3, ["yes", "no", "cant_tell"])
    a2 = ["yes" if x == "yes" else "notyes" for x in a3]
    b2 = ["yes" if x == "yes" else "notyes" for x in b3]
    k2, po2 = kappa(a2, b2, ["yes", "notyes"])
    agree = sum(x == y for x, y in zip(a3, b3))
    print("\n== inter-judge ==")
    print("  agree %d/102 | kappa 3-class %.3f | kappa yes/notyes %.3f"
          % (agree, k3, k2))

    both_yes = [s for s, x, y in zip(seqs, a3, b3)
                if x == "yes" and y == "yes"]
    if both_yes:
        ek = sum(cls(s) == "engine" for s in both_yes)
        eh = sum(key[s]["truth"] == "engine_hit" for s in both_yes)
        print("  both-yes items: %d | engine %d | engine_hit %d | "
              "golden %d | negative %d"
              % (len(both_yes), ek, eh,
                 sum(cls(s) == "golden" for s in both_yes),
                 sum(cls(s) == "negative" for s in both_yes)))


if __name__ == "__main__":
    main()
