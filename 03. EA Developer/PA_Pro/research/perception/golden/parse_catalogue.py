"""parse_catalogue.py — P1.1: parse the casebook figure catalogue
(notes_09/10/11, section B) into ``golden/draft/BOOK2012_draft.jsonl``.

One JSON record per panel:
    {fig, panel, page, date, x0, x1, bars_from, y_labels[],
     objects[], marks[], raw_drawn, raw_marks, lesson}

Object record (golden grammar; spec_type = the §2 family it maps to):
    {type, spec_type, style, dir, t0, t1, price, price2, span_pips,
     meas, note, prec}
Every field may be null; ``prec`` is "eye" (±5 p / ±10 min) or "meas"
(±1-2 p).  ``t0/t1``/``price`` strings keep the raw '~' flag in ``approx``.

Marks: {kind: T|F|ARROW|SKIP|SESSION|NOTE, ...} — arrows are kept for
context only (they are entry annotations, never scored as objects).
"""

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
NOTES_DIR = os.path.abspath(os.path.join(
    HERE, "..", "..", "..", "..", "EA_VolmanPA", "PLAN", "book",
    "_private", "notes_perception"))
OUT = os.path.join(HERE, "draft", "BOOK2012_draft.jsonl")

MONTHS = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
          "june": 6, "july": 7, "august": 8, "september": 9,
          "october": 10, "november": 11, "december": 12}

TIME_RE = re.compile(r"~?(\d{1,2}):(\d{2})")
PRICE_RE = re.compile(r"≈?\(?~?(1[.,]\d{3,4})\)?")
MEAS_RE = re.compile(r"\[meas[^\]]*\]|≈?\(?~?(\d+(?:\.\d+)?)\s*(?:pips?|p)\)?")

# ---- object phrase classification -------------------------------------

def _times(text):
    """All ~HH:MM in order; returns (times, approx_flags)."""
    out = []
    for m in re.finditer(r"(~?)(\d{1,2}):(\d{2})", text):
        out.append((f"{int(m.group(2)):02d}:{m.group(3)}",
                    bool(m.group(1))))
    return out


def _prices(text):
    """All price tokens, in order (floats like 1.3315)."""
    out = []
    for m in re.finditer(r"(≈?)(1[.,]\d{3,4})", text):
        p = float(m.group(2).replace(",", "."))
        # sanity: EURUSD 2012 range 1.20-1.35
        if 1.15 < p < 1.40:
            out.append((p, bool(m.group(1))))
    return out


def _span_pips(text):
    m = re.search(r"\[meas\s*≈?~?(\d+(?:\.\d+)?)", text)
    if m:
        return float(m.group(1)), True
    m = re.search(r"[~(≈]*\(?(\d+(?:\.\d+)?)\s*(?:pips?|p\b)", text)
    if m:
        return float(m.group(1)), False
    return None, False


def classify_clause(clause):
    """Map one Drawn clause to an object dict (or None)."""
    c = clause.strip().rstrip(".")
    low = c.lower()
    if not c or len(c) < 4:
        return None
    if re.search(r"\bnothing\b|^none\b|stubs?\b\.?$|^stubs$|only the|"
                 r"continued\b\.?$|^the carried|^the same (solid|dotted)|"
                 r"^previous|^previous tl|^the old|^day-box stub|"
                 r"^asian-box stub|^box stub|^flag-line stub|^tl stub|"
                 r"^m[mk]?-?box stub|extended\b\.?$|"
                 r"^-?\s*the (carried|same|old)\b|^-?\s*(day-|asian-)?"
                 r"(box|tl|flag|pennant|base)[ -]?stub", low):
        # continuations of objects born in an earlier panel — recorded as
        # CARRY marks, not new objects
        if "nothing" in low or low in ("stubs", "stubs."):
            return {"type": "NONE", "note": c}
        return {"type": "CARRY", "note": c}

    style = "solid"
    if "dotted" in low or "fine-dotted" in low:
        style = "dotted"
    elif "dashed" in low or "dash " in low or re.match(r"^dash\b", low):
        style = "long_dashed"
    elif "long-dashed" in low:
        style = "long_dashed"

    direction = None
    if re.search(r"rising|ascending|tl↗|up[- ]?line|gently rising", low):
        direction = "up"
    elif re.search(r"falling|descending|tl↘|down[- ]?line|declining",
                   low):
        direction = "down"

    times = _times(c)
    prices = _prices(c)
    span, meas = _span_pips(c)

    obj = {"type": None, "spec_type": None, "style": style,
           "dir": direction,
           "t0": times[0][0] if times else None,
           "t1": times[1][0] if len(times) > 1 else None,
           "t_extra": [t for t, _ in times[2:]],
           "approx_time": any(a for _, a in times),
           "price": prices[0][0] if prices else None,
           "price2": prices[1][0] if len(prices) > 1 else None,
           "approx_price": any(a for _, a in prices),
           "span_pips": span, "meas": meas,
           "note": c, "prec": "meas" if meas else "eye"}

    is_box = re.search(r"\bbox\b|rectangle", low)
    is_open = re.search(r"open|two (long |parallel )?h edges|two parallel|"
                        r"pair of (range )?lines|open box", low)
    is_bracket = re.search(
        r"\b(m|w|mm|ww|shs|h&s)[ -]?(span|bracket|segment|marker)s?\b|"
        r"\b(m|w|mm|ww|shs) (span|segments?)\b", low)
    is_squeeze = "squeeze" in low or "ellipse" in low
    is_dash_h = style == "long_dashed" and re.search(
        r"horizontal|dash\b|level|support|resistance|low|high|floor|top|"
        r"edge|middle", low)
    is_line = re.search(r"\bline\b|\btl\b|neckline|trendline|edge\b|"
                        r"\bbase\b|\broof\b|\bflag\b|pennant|triangle",
                        low)
    is_h = re.search(r"horizontal|h[ -]line|\bh\b|support|resistance|"
                     r"ceiling|floor|neckline", low)

    if is_box and style == "dotted":
        obj["type"], obj["spec_type"] = "CONTEXT_RANGE", "CONTEXT_RANGE"
    elif is_box and is_open:
        obj["type"], obj["spec_type"] = "RANGE_OPEN", "RANGE_OPEN"
    elif is_box:
        obj["type"], obj["spec_type"] = "BOX", "BOX"
    elif is_open and ("parallel" in low or "open" in low):
        obj["type"], obj["spec_type"] = "RANGE_OPEN", "RANGE_OPEN"
    elif is_bracket:
        m = re.search(r"\b(mm|ww|shs|m|w|h&s)\b", low)
        letter = (m.group(1) if m else "?").upper().replace("H&S", "SHS")
        obj["type"], obj["spec_type"] = "BRACKET", "BRACKET"
        obj["letter"] = letter
        obj["side"] = "below" if letter.startswith("W") or (
            letter == "SHS" and "inverse" in low) else "above"
    elif is_squeeze:
        obj["type"], obj["spec_type"] = "SQUEEZE", "SQUEEZE"
    elif style == "long_dashed":
        obj["type"], obj["spec_type"] = "LEVEL_CARRIED", "LEVEL_CARRIED"
    elif is_h and not is_line:
        short = bool(re.search(r"short|tiny|mini|small|little", low))
        obj["type"] = "MINI_LEVEL" if short else "H_LEVEL"
        obj["spec_type"] = "MINI_LEVEL" if short else "LEVEL_CARRIED"
    elif is_line or is_h:
        # horizontal-ish solid line with a single price and no slope words
        if (direction is None and prices and
                re.search(r"horizontal|support|resistance|ceiling|floor|"
                          r"neckline", low)):
            short = bool(re.search(r"short|tiny|mini|small", low))
            obj["type"] = "MINI_LEVEL" if short else "H_LEVEL"
            obj["spec_type"] = "MINI_LEVEL" if short else "LEVEL_CARRIED"
        else:
            obj["type"], obj["spec_type"] = (
                ("CONTEXT_LINE", "CONTEXT_LINE") if style == "dotted"
                else ("PATTERN_LINE", "PATTERN_LINE"))
    else:
        obj["type"] = "OTHER"
        obj["spec_type"] = None
    return obj


def parse_marks(text):
    """Marks clause -> T/F letters, arrows, session labels, misc."""
    out = []
    if not text:
        return out
    # T/F letters: each T/F token owns the ~HH:MM times that follow it
    # within its sentence segment ("T under the ~07:15 and ~07:35 lows").
    for m in re.finditer(r"\b(T|F)\b([^.;]{0,80})", text):
        letter, seg = m.group(1), m.group(2)
        side = ("below" if re.search(r"under|below|low", seg)
                else "above" if re.search(r"above|over|high|top", seg)
                else None)
        ts = _times(seg.split("T")[0].split("F")[0])  # up to next letter
        if ts:
            for tm, approx in ts:
                out.append({"kind": "LABEL_TF", "letter": letter,
                            "t": tm, "side": side, "approx": approx})
        else:
            out.append({"kind": "LABEL_TF", "letter": letter,
                        "t": None, "side": side, "approx": True})
    for m in re.finditer(
            r"(@\s*)?(pb|pbp|pbc|pr|tff)(\s*/\s*(pb|pbp|pbc|pr|tff))*\s*"
            r"([↑↓]|down-arrow|up-arrow)?[^.;]{0,40}", text, re.I):
        seg = m.group(0)
        ts = _times(seg)
        out.append({"kind": "ARROW",
                    "label": re.sub(r"\s+", "", m.group(0).split(" ")[0]),
                    "bold": bool(m.group(1)),
                    "dir": ("down" if ("↓" in seg or "down" in seg)
                            else "up" if ("↑" in seg or "up" in seg)
                            else None),
                    "t": ts[0][0] if ts else None,
                    "raw": seg.strip()[:80]})
    for m in re.finditer(r"\[(skip|stay out)[^\]]*\]|\bskip\b|bỏ qua|"
                         r"đứng ngoài|stand aside", text, re.I):
        ts = _times(text[m.start():m.end() + 40])
        out.append({"kind": "SKIP", "t": ts[0][0] if ts else None})
    for m in re.finditer(
            r"(EU|UK|US)[ -]open|ECB|news|NFP|US data|lunch", text, re.I):
        out.append({"kind": "SESSION", "label": m.group(0)})
    return out


# ---- per-format panel splitting ----------------------------------------

FIG_HEAD_09 = re.compile(r"### Fig (9\.\d+) — p\.(\d+) — (\w+) (\d+)-(\d{4})")
FIG_HEAD_1011 = re.compile(
    r"### p(\d+) — Fig (9\.\d+) — (?:date: )?(?:.*?"
    r"(?:(\w+) (\d{1,2})[-–](\d{4})|(\d{4})-(\d{2})-(\d{2})))?.*?(\w{3})?\)?$")
PANEL_09 = re.compile(r"- \*\*(9\.\d+)([abc])\*\*\s*$")
PANEL_10 = re.compile(r"- \*\*(9\.\d+)([abc])\*\*")
PANEL_11 = re.compile(r"- \*\*(9\.\d+)([abc])\*\*")


def _date_from(month_name, day, year):
    return f"{int(year):04d}-{MONTHS[month_name.lower()]:02d}-{int(day):02d}"


def split_panels(text, fmt):
    """Yield (figid, panel, page, date_str_or_None, block_text)."""
    lines = text.split("\n")
    # find section B start
    bstart = 0
    for i, ln in enumerate(lines):
        if re.match(r"## B\.", ln):
            bstart = i
            break
    lines = lines[bstart:]

    heads = []   # (line_idx, fig, page, date)
    if fmt == 9:
        for i, ln in enumerate(lines):
            m = FIG_HEAD_09.search(ln)
            if m:
                fig, page, mon, day, yr = m.groups()
                heads.append((i, fig, int(page),
                              _date_from(mon, day, yr)))
    else:
        for i, ln in enumerate(lines):
            m = FIG_HEAD_1011.match(ln)
            if m:
                page, fig = m.group(1), m.group(2)
                if m.group(3):            # "July 02-2012"
                    date = _date_from(m.group(3), m.group(4), m.group(5))
                elif m.group(6):          # ISO "2012-06-27"
                    date = f"{m.group(6)}-{m.group(7)}-{m.group(8)}"
                else:
                    date = None
                heads.append((i, fig, int(page), date))
    panels = []
    cur_fig = cur_page = cur_date = None
    for hi, (li, fig, page, date) in enumerate(heads):
        end = heads[hi + 1][0] if hi + 1 < len(heads) else len(lines)
        body = lines[li + 1:end]
        # split body on panel markers
        cur = None
        for ln in body:
            pm = re.match(r"- \*\*(9\.\d+)([abc])\*\*", ln)
            if pm and pm.group(1) == fig:
                if cur:
                    panels.append(cur)
                cur = {"fig": fig, "panel": pm.group(2), "page": page,
                       "date": date, "lines": [ln]}
            elif cur:
                cur["lines"].append(ln)
        if cur:
            panels.append(cur)
    return panels


def parse_panel(p, fmt):
    block = "\n".join(p["lines"])
    head = p["lines"][0]
    out = {"fig": p["fig"], "panel": p["panel"], "page": p["page"],
           "date": p["date"], "id": f"{p['fig']}{p['panel']}"}

    # x range — may sit on the head line (notes 10/11) or the first
    # sub-bullet (notes 09: "- x 04:00–10:00 (bars from ~03:30); y ...")
    xtext = head if fmt != 9 else block
    mx = re.search(r"x[ :]+~?(\d{1,2}):(\d{2})\s*[–—→-]\s*~?(\d{1,2}):(\d{2})",
                   xtext)
    if not mx:
        mx = re.search(r"\|\s*~?(\d{1,2}):(\d{2})\s*(?:→|–|-)\s*~?(\d{1,2})"
                       r":(\d{2})", xtext)
    if mx:
        out["x0"] = f"{int(mx.group(1)):02d}:{mx.group(2)}"
        out["x1"] = f"{int(mx.group(3)):02d}:{mx.group(4)}"
    else:
        out["x0"] = out["x1"] = None
    mb = re.search(r"(?:from|bars from)\s*~?(\d{1,2}):(\d{2})", xtext)
    out["bars_from"] = (f"{int(mb.group(1)):02d}:{mb.group(2)}"
                        if mb else None)

    # y labels
    my = re.search(r"y[ :]+([0-9,./ ·]+?)(?:\s*[·|]|\s*$|\s*\(|;|\n)",
                   xtext)
    ylab = []
    if my:
        for tok in re.finditer(r"1[.,]\d{2,4}", my.group(1)):
            v = float(tok.group(0).replace(",", "."))
            if 1.15 < v < 1.40:
                ylab.append(v)
    out["y_labels"] = ylab

    # drawn / marks text
    dm = re.search(r"Drawn:\s*(.*?)(?=\n?\s*-?\s*(?:\*\*)?Marks?:|\n\s*-?\s*"
                   r"(?:\*\*)?(?:Callout|Note|Lesson)\b|\Z)",
                   block, re.S | re.I)
    mk = re.search(r"Marks?:\s*(.*?)(?=\n\s*-?\s*(?:\*\*)?(?:Callouts?|Notes?|"
                   r"Lesson|\*Lesson)\b|\Z)", block, re.S | re.I)
    drawn_txt = dm.group(1).strip() if dm else ""
    marks_txt = mk.group(1).strip() if mk else ""
    out["raw_drawn"] = drawn_txt
    out["raw_marks"] = marks_txt

    # split drawn into clauses on ';' and on newline bullets
    clauses = []
    for piece in re.split(r";|\n\s*-\s+", drawn_txt):
        piece = piece.strip()
        if piece:
            clauses.append(piece)
    # clauses of the form "X ... ~t0→~t1 and ~t2→~t3" describe two
    # parallel objects — split on the second range
    split_clauses = []
    for cl in clauses:
        rngs = list(re.finditer(r"~?\d{1,2}:\d{2}\s*[→–—-]\s*~?\d{1,2}:\d{2}",
                                cl))
        if len(rngs) >= 2 and re.search(r"\b(and|,)\s*$",
                                        cl[:rngs[1].start()]):
            split_clauses.append(cl[:rngs[1].start()].rstrip(" ,and"))
            split_clauses.append(cl[rngs[1].start():])
        else:
            split_clauses.append(cl)
    clauses = split_clauses
    # notes_10 one-line style: "Drawn: X; Y. Marks:" also splits on
    # '); ' handled above. Some entries use ', then' — leave.
    objs = []
    for cl in clauses:
        o = classify_clause(cl)
        if o is None:
            continue
        # orphan fragment left by the range-split ("~t0→~t1, extended..."):
        # inherit the previous object's class
        if o["type"] == "OTHER" and objs and re.match(
                r"^[~(\d]|^extended|^continued", cl.strip()):
            prev = objs[-1]
            o.update({"type": prev["type"], "spec_type": prev["spec_type"],
                      "style": prev["style"], "dir": prev["dir"],
                      "inherited": True})
        if o["type"] not in ("CARRY", "NONE"):
            objs.append(o)
    out["objects"] = objs
    out["marks"] = parse_marks(marks_txt)
    lm = re.search(r"(?:\*?Lesson\*?:)\s*(.*)", block, re.S)
    out["lesson"] = (lm.group(1).strip()[:300] if lm else "")
    return out


def main():
    files = {9: "notes_09_p266-311.md", 10: "notes_10_p312-357.md",
             11: "notes_11_p358-402.md"}
    all_panels = []
    for fmt, fname in files.items():
        path = os.path.join(NOTES_DIR, fname)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        panels = split_panels(text, fmt)
        recs = [parse_panel(p, fmt) for p in panels]
        n_obj = sum(len(r["objects"]) for r in recs)
        print(f"{fname}: {len(recs)} panels, {n_obj} objects parsed")
        all_panels.extend(recs)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for r in all_panels:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"wrote {OUT}: {len(all_panels)} panels")


if __name__ == "__main__":
    main()
