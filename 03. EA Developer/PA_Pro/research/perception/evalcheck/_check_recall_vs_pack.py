"""_check_recall_vs_pack.py — compare every per-family and snapshot
figure in a regenerated RECALL_AT_K draft against the embedded copies
inside GATE_PACK_9283b389.md (the numbers of record, R38 §38.1).

Usage: python evalcheck/_check_recall_vs_pack.py [draft_path]
Prints per-section MATCH/DIFF lines; exit 0 if all match.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.join(HERE, "GATE_PACK_9283b389.md")
DRAFT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    HERE, "_regen_recall_at_k.draft.md")


def sections(txt):
    """{header_title: [lines]} split on '## ' headers."""
    out = {}
    cur, buf = None, []
    for ln in txt.splitlines():
        if ln.startswith("## "):
            if cur:
                out[cur] = buf
            cur, buf = ln[3:].strip(), []
        elif cur:
            buf.append(ln.rstrip())
    if cur:
        out[cur] = buf
    return out


def norm(s):
    return re.sub(r"\s+", " ", s.strip())


def comparable(lines):
    """Table rows + provenance/footnote lines only."""
    return [norm(l) for l in lines
            if l.startswith(("|", "median", "ranking", "per-family",
                             "author per-family", "BRACKET column",
                             "†"))]


def sec_key(title):
    """Map a section header to a short key for pairing."""
    t = title.lower()
    for pat in ("v0", "linelab", "v1_stable", "reviveon", "markeron",
                "tailon", "budgetgold", "defended_origin", "defended_v2",
                "famledger_samehash", "famledgerv2"):
        if pat in t:
            return pat
    return t.split("(")[0].strip()


def main():
    pack = open(PACK, encoding="utf8").read()
    draft = open(DRAFT, encoding="utf8").read()
    P, D = sections(pack), sections(draft)
    pk, dk = {sec_key(k): v for k, v in P.items()}, \
             {sec_key(k): v for k, v in D.items()}
    # v0 appears twice in the pack (gate table + recall@k section);
    # the recall@k one has a "| k |" row.
    for k in list(pk):
        if not any(l.startswith("| k |") for l in pk[k]):
            del pk[k]
    allok = True
    for key in dk:
        if key not in pk:
            print("NO-PACK-SECTION  %s" % key)
            allok = False
            continue
        a, b = comparable(dk[key]), comparable(pk[key])
        if a == b:
            print("MATCH            %s (%d lines)" % (key, len(a)))
            continue
        allok = False
        print("DIFF             %s" % key)
        sa, sb = set(a), set(b)
        for l in a:
            if l not in sb:
                print("   draft : %s" % l)
        for l in b:
            if l not in sa:
                print("   pack  : %s" % l)
    for key in pk:
        if key not in dk:
            print("PACK-ONLY        %s (no draft section)" % key)
    print("ALL-MATCH" if allok else "MISMATCHES-FOUND")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
