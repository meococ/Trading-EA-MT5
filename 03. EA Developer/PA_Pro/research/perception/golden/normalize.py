"""normalize — draft catalogue -> spec-typed records (P1.4a).

Resolves the parser's untyped (spec_type=None) fragments:
  - continuation notes ("its top ...", "touches at ...") fold into the
    previous object's `notes`;
  - lessons / news / skip marks become panel `annotations`;
  - real objects get a spec type: line(s) -> PATTERN_LINE/CONTEXT_LINE,
    "dotted range" -> CONTEXT_RANGE, M/W/SHS span -> BRACKET,
    "T/F above|under|over|below" -> LABEL_TF (moved to `marks`),
    star/tick markers -> BAR_MARKER.
Every emitted object gets `needs_refine` when its time/price is approx.
"""

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DRAFT = os.path.join(HERE, "draft")

ANN_RE = re.compile(
    r"lesson|callout|news|release|\[skip|\[stay|don't trade|do not trade|"
    r"US news|EU |scalp|possible|stall|pressure|bulls|numbered", re.I)
CONT_RE = re.compile(
    r"^(its |the |a |an |caption|bottom |top |continued|stub|closed|"
    r"extended|second |same |left |right |wick|ticks|touch|break)", re.I)
TF_RE = re.compile(r"^\s*([TF])\s+(above|below|over|under|at)\b", re.I)
BRK_RE = re.compile(r"\b(SHS|M|W)[-\s]?(?:type\s+)?span\b|\b(M|W|SHS)\s+"
                    r"(?:bracket|pattern)\b", re.I)
RANGE_RE = re.compile(r"dotted range|context range|range\b", re.I)
LINE_RE = re.compile(r"\blines?\b|segment", re.I)
MARK_RE = re.compile(r"star|marker|tick(s)? (over|under|above|below)",
                     re.I)


def classify_note(note, prev_obj):
    """Return (spec_type, style) or ('_merge'|'_ann'|'_mark', payload)."""
    t = note.strip()
    m = TF_RE.match(t)
    if m:
        return ("_mark", {"kind": "LABEL_TF", "letter": m.group(1),
                          "side": m.group(2)})
    if BRK_RE.search(t):
        k = BRK_RE.search(t)
        kind = k.group(1) or k.group(2)
        return ("BRACKET", "bracket_" + kind)
    if RANGE_RE.search(t) and "dotted" in t:
        return ("CONTEXT_RANGE", "dotted")
    if LINE_RE.search(t):
        style = "dotted" if "dotted" in t else "solid"
        ty = "CONTEXT_LINE" if style == "dotted" else "PATTERN_LINE"
        return (ty, style)
    if MARK_RE.search(t):
        return ("BAR_MARKER", "marker")
    if ANN_RE.search(t):
        return ("_ann", None)
    if CONT_RE.match(t) and prev_obj is not None:
        return ("_merge", None)
    return ("_merge" if prev_obj is not None else "_ann", None)


def norm_object(o):
    out = dict(o)
    out.pop("note", None)
    out["raw_note"] = o.get("note")
    out.setdefault("needs_refine", bool(
        o.get("approx_time") or o.get("approx_price")))
    return out


def main():
    src = os.path.join(DRAFT, "BOOK2012_draft.jsonl")
    dst = os.path.join(DRAFT, "BOOK2012_norm.jsonl")
    n_obj = n_merge = n_ann = n_mark = 0
    with open(src, encoding="utf8") as f, \
            open(dst, "w", encoding="utf8") as fo:
        for line in f:
            r = json.loads(line)
            objs = []
            anns = []
            for o in r.get("objects", []):
                if o.get("spec_type"):
                    objs.append(norm_object(o))
                    continue
                note = (o.get("note") or "").strip()
                ty, style = classify_note(note, objs[-1] if objs else None)
                if ty == "_merge":
                    objs[-1].setdefault("notes", []).append(note)
                    n_merge += 1
                elif ty == "_ann":
                    anns.append(note)
                    n_ann += 1
                elif ty == "_mark":
                    mk = dict(style)
                    mk["t"] = o.get("t")
                    mk["approx"] = True
                    r.setdefault("marks", []).append(mk)
                    n_mark += 1
                else:
                    o["spec_type"] = ty
                    o["style"] = style
                    objs.append(norm_object(o))
                    n_obj += 1
            r["objects"] = objs
            r["annotations"] = anns
            fo.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("objects kept %d + typed %d, merged %d, annotations %d, "
          "marks added %d" % (n_obj, n_obj, n_merge, n_ann, n_mark))


if __name__ == "__main__":
    main()
