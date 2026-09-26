"""EVAL-AUDIT M2 scorer (R73 s.73.5): scores the Owner's exported
answers against the sealed key.  Key stays outside the pack.

Metrics (M2_PACK_PLAN.md):
  precision   = yes / all answers on engine items
                (cant_tell counts as NOT yes; yes/(yes+no) alongside)
  sensitivity = yes / golden controls
  specificity = no  / audited negatives
  each with a Wilson 95% CI.

Usage:
    python evalcheck/_m2_score_c3.py [answers_file]
    # default: owner_pack/ANSWERS.md
"""
import json
import math
import os
import re
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
KEY = os.path.join(HERE, "_owner_judge_key", "m2_c3_key.json")
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
    """Return {seq: answer}; accepts '- p001: yes' (ANSWERS.md) and
    'p001,yes[,reason]' (ai_judges CSV)."""
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
    key = json.load(open(KEY))["key"]
    ans = parse_answers(ans_path)
    print("answers file:", ans_path)
    print("answered %d / %d items" % (len(ans), len(key)))

    blank = [s for s in key if ans.get(s) not in ("yes", "no", "cant_tell")]
    if blank:
        print("UNANSWERED/invalid: %d -> %s"
              % (len(blank), ",".join(sorted(blank)[:15])))

    def cls(seq):
        t = key[seq]["truth"]
        return "engine" if t.startswith("engine_") else t

    groups = collections.defaultdict(list)
    for seq, a in ans.items():
        if seq in key and a in ("yes", "no", "cant_tell"):
            groups[cls(seq)].append((seq, a))

    def rate(group, positive, denom_all=True):
        rows = groups[group]
        k = sum(1 for _, a in rows if a == positive)
        n = len(rows)
        return k, n, wilson(k, n)

    print("\n== M2 headline ==")
    for label, group, pos in [("precision  (engine top-k yes-rate)",
                               "engine", "yes"),
                              ("sensitivity (golden yes-rate)",
                               "golden", "yes"),
                              ("specificity (negative no-rate)",
                               "negative", "no")]:
        k, n, (p, lo, hi) = rate(group, pos)
        print("%s: %d/%d = %.3f  [%.3f, %.3f]" % (label, k, n, p, lo, hi))

    eng = groups["engine"]
    yn = [a for _, a in eng if a in ("yes", "no")]
    if yn:
        k2 = sum(1 for a in yn if a == "yes")
        p2, lo2, hi2 = wilson(k2, len(yn))
        print("precision alt yes/(yes+no): %d/%d = %.3f [%.3f, %.3f]"
              % (k2, len(yn), p2, lo2, hi2))
    ct = collections.Counter(a for _, a in eng)
    print("engine-item answers:", dict(ct))

    print("\n== engine items by family ==")
    byfam = collections.defaultdict(lambda: [0, 0])
    for seq, a in eng:
        f = key[seq]["family"]
        byfam[f][1] += 1
        byfam[f][0] += a == "yes"
    for f, (k, n) in sorted(byfam.items()):
        p, lo, hi = wilson(k, n)
        print("  %-8s %d/%d = %.3f [%.3f, %.3f]" % (f, k, n, p, lo, hi))

    print("\n== engine_hit vs engine_fp split ==")
    for t in ("engine_hit", "engine_fp"):
        rows = [(s, a) for s, a in eng if key[s]["truth"] == t]
        k = sum(1 for _, a in rows if a == "yes")
        n = len(rows)
        p, lo, hi = wilson(k, n)
        print("  %-10s yes %d/%d = %.3f [%.3f, %.3f]" % (t, k, n, p, lo, hi))


if __name__ == "__main__":
    main()
