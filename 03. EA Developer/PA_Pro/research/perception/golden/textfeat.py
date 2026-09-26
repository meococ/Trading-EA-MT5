"""textfeat — read the catalogue note as a specification, not as prose.

Ruling 2 §2.1 requires every golden object to be checked against the
catalogue TEXT and the real bars.  The text is the author's statement of
intent: which structure, which side of price, which way it slopes, which
bar it is anchored to.  This module turns that prose into machine-checkable
constraints; `validate.py` tests geometry against them and `repair.py`
rebuilds geometry that contradicts them.

Everything here was derived by reading the actual TUNE corpus (198 panels,
~600 notes), not from guesses about how the notes might be phrased.  The
vocabulary that mattered:

- slope: "rising"/"falling" (106 notes) but ALSO the shorthand ``tl↗`` /
  ``tl↘`` (51 notes) which an earlier slope check missed completely, plus
  "nearly flat"/"horizontal" (8+) and the intensifiers "steep"/"gently".
- side: "under the lows", "across the highs", "over a congestion",
  "along the Asian congestion lows", "roof", "ceiling", "floor", "base".
- anchors: "from the ~14:45 low to ~18:10", "from the 09:05 tease high",
  bare spans "~04:30–07:05" and "~10:25→11:50".
- flag family: "bear-flag" lines RISE (counter-trend inside a downtrend),
  "bull-flag" lines FALL.  Used only as a cross-check on an explicit
  slope word, never to override it.

**Slope is a bounded interval, not a sign.**  "nearly flat tl↗ under the
10:10–13:45 lows" is both flat and rising: over 3.5 h it may legitimately
drift +5 pips.  A bare sign test would reject the author's own drawing, so
each slope cue maps to (lo_pips, hi_pips) bounds over the object's span.
"""

import re

# ------------------------------------------------------------------ #
# context stripping
# ------------------------------------------------------------------ #

# A slope or side word can belong to a DIFFERENT object mentioned in the
# same note — almost always the EMA25.  "long nearly flat tl↗ under the
# 10:10-13:45 lows (falling ema above)" describes a gently RISING line;
# the words "falling" and "above" belong to the EMA.  8 TUNE notes do
# this and 3 of them produced spurious slope mismatches before this was
# handled, so the clause is removed before any cue is read.
_EMA_CLAUSE = re.compile(
    r"(?:\b(?:above|below|under|over|against|as|with)\b\s+)?"
    r"(?:\b(?:a|the)\b\s+)?"
    r"(?:\b(?:rising|falling|flat|flattening)\b\s+)?"
    r"\bema\b(?:\s*\d+)?"
    r"(?:\s+\b(?:above|below|inside|flattens|flattening|rising|falling)\b)?")


def strip_context(note):
    """Remove clauses that describe objects other than this one."""
    return _EMA_CLAUSE.sub(" ", (note or "").lower())


# ------------------------------------------------------------------ #
# slope
# ------------------------------------------------------------------ #

_UP = re.compile(r"\brising\b|\brises\b|\bascending\b|\bclimbing\b"
                 r"|\bup-?sloping\b|\bsloping up\b|↗")
_DOWN = re.compile(r"\bfalling\b|\bfalls\b|\bdescending\b|\bdeclining\b"
                   r"|\bdown-?sloping\b|\bsloping down\b|↘")
_FLAT = re.compile(r"\bnearly flat\b|\bnear-flat\b|\bflat\b|\bhorizontal\b"
                   r"|\blevel\b")
_STEEP = re.compile(r"\bsteep\b|\bsharp\b")
_GENTLE = re.compile(r"\bgently\b|\bgentle\b|\bshallow\b|\bslight\b")

# pip bounds over the whole span for each cue combination
_SLOPE_BOUNDS = {
    # 'flat/nearly flat/horizontal' is the author's eyeball call: on a
    # ~60-pip chart a line drifting < ~10p over a 2h span reads flat
    # (~3 deg of slope).  flat_up/flat_down = "nearly flat tlX".
    "up":        (1.0, None),
    "down":      (None, -1.0),
    "flat":      (-10.0, 10.0),
    "flat_up":   (0.0, 20.0),
    "flat_down": (-20.0, 0.0),
    "steep_up":   (8.0, None),
    "steep_down": (None, -8.0),
}


def slope_cue(note):
    """-> (label, (lo_pips, hi_pips)) or (None, None).

    Bounds are the permitted TOTAL price change from the first anchor to
    the last, in pips, sign included.  ``None`` means unbounded.
    """
    n = note.lower()
    up, dn, flat = bool(_UP.search(n)), bool(_DOWN.search(n)), \
        bool(_FLAT.search(n))
    if up and dn:
        return None, None                      # e.g. a converging pair
    if flat and up:
        return "flat_up", _SLOPE_BOUNDS["flat_up"]
    if flat and dn:
        return "flat_down", _SLOPE_BOUNDS["flat_down"]
    if up:
        if _STEEP.search(n):
            return "steep_up", _SLOPE_BOUNDS["steep_up"]
        return "up", _SLOPE_BOUNDS["up"]
    if dn:
        if _STEEP.search(n):
            return "steep_down", _SLOPE_BOUNDS["steep_down"]
        return "down", _SLOPE_BOUNDS["down"]
    if flat:
        return "flat", _SLOPE_BOUNDS["flat"]
    return None, None


def slope_cues(note):
    """All slope bound-sets the note permits, in preference order.

    A note that names two slopes ("a converging pair: a falling line ...
    and a rising line ...") describes a PAIR; the drawn object may be
    either member, so both bounds are admissible candidates.
    """
    n = note.lower()
    up, dn, flat = bool(_UP.search(n)), bool(_DOWN.search(n)), \
        bool(_FLAT.search(n))
    if up and dn:
        return [_SLOPE_BOUNDS["up"], _SLOPE_BOUNDS["down"]]
    lab, b = slope_cue(note)
    return [b] if b else []


_CLAUSE_SPLIT = re.compile(r"\s*(?:\bplus\b|;|\(|\)|,\s*(?=[a-z]*\s*(?:line|tl|box|level|horizontal|support|resistance)\b))\s*",
                           re.I)


_OBJ_NOUN = re.compile(r"\b(line|tl|box|bracket|horizontal|level|range|"
                       r"support|resistance|neckline|edge|floor|ceiling)\b",
                       re.I)


def split_clauses(note):
    """A compound note describes several drawn objects: 'a steep rising
    line, plus a short horizontal', '(a falling line ..., a nearly flat
    line ...)'.  Split it into per-object clauses so each object is
    parsed against its own words only.  Bare measurement fragments
    ('(~13 pips, straddling 1.26)') are modifiers of the clause before
    them, not objects — merge them back."""
    parts = [p.strip(" ,.-") for p in _CLAUSE_SPLIT.split(note or "")]
    parts = [p for p in parts if len(p) > 3]
    out = []
    for p in parts:
        bare_to = bool(re.match(r"^to ~?\d{1,2}:\d{2}$", p))
        if out and (bare_to or (not times(p) and not prices(p)
                                and slope_cue(p)[0] is None
                                and not _UP.search(p)
                                and not _DOWN.search(p))):
            out[-1] = out[-1] + " " + p
        else:
            out.append(p)
    return out


def clause_for(note, d, ord_idx=0):
    """Pick the clause describing draft object *d*: prefer the clause
    containing the object's own t0, then one matching its dir, else the
    clause at the object's ordinal position among same-note objects."""
    cl = split_clauses(note)
    if len(cl) < 2:
        return note

    def enrich(c):
        # a bare time/side fragment inherits the shared description in
        # the head clause ("two rising bear-flag lines inside it
        # (~10:25→11:50, ~11:55→13:05)")
        if slope_cue(c)[0] is None and not _UP.search(c) \
                and not _DOWN.search(c) and cl[0] is not c \
                and (slope_cue(cl[0])[0] is not None
                     or _UP.search(cl[0]) or _DOWN.search(cl[0])):
            return cl[0] + " " + c
        return c

    t0 = _hhmm(d.get("t0"))
    # a clause quoting the object's own text price wins outright
    if d.get("price") is not None:
        for c in cl:
            if any(abs(p - d["price"]) < 5e-4 for p in prices(c)):
                return enrich(c)
    if t0 is not None:
        for c in cl:
            if t0 in times(c):
                return enrich(c)
    want = {"up": _UP, "down": _DOWN}.get(d.get("dir"))
    if want is not None:
        hits = [c for c in cl if want.search(c.lower())
                and not (_UP.search(c.lower()) and _DOWN.search(c.lower()))]
        if hits:
            return hits[0]
    return cl[min(ord_idx, len(cl) - 1)]


# ------------------------------------------------------------------ #
# side of price
# ------------------------------------------------------------------ #

_UNDER = re.compile(r"\bunder\b|\bbeneath\b|\bbelow\b|\balong the .{0,30}lows"
                    r"|\bfloor\b|\bbase\b|\bsupport\b|\bunder-?side\b")
_OVER = re.compile(r"\bover\b|\babove\b|\bacross the highs\b|\broof\b"
                   r"|\bceiling\b|\bresistance\b|\bover-?head\b"
                   r"|\bat (?:its |the )?top\b|\btops of\b")


def side_cue(note):
    """'under' | 'over' | None — which side of the bars the object sits.

    'under' means the object should sit at/below the bar lows in its span
    (a line under the lows, a floor, a support); 'over' means at/above the
    highs.  Both present -> None (ambiguous, e.g. "a top line over a
    congestion and a rising line under it" parsed as one note).
    """
    n = note.lower()
    u, o = bool(_UNDER.search(n)), bool(_OVER.search(n))
    if u and o:
        return None
    return "under" if u else ("over" if o else None)


# ------------------------------------------------------------------ #
# level reference (for horizontals with no price)
# ------------------------------------------------------------------ #

_REF_HIGH = re.compile(r"\btops?\b|\bceiling\b|\broof\b|\bhighs?\b"
                       r"|\bresistance\b|\bover\b|\babove\b|\bmiddle\b")
_REF_LOW = re.compile(r"\bfloor\b|\bbase\b|\bsupport\b|\blows?\b"
                      r"|\bbottoms?\b|\bunder\b|\bbeneath\b|\bbelow\b")


def level_ref(note):
    """For a horizontal with no catalogue price: does the text anchor it to
    the HIGHS or the LOWS of the bars it names?  Returns 'high'|'low'|None.

    Precedence matters: "a long-dashed horizontal from the 14:00-14:40
    congestion lows" contains no 'top' word, so -> 'low'.  Where both
    appear ("a horizontal under the tops of the 08:15-08:35 bars") the
    explicit extreme word ('tops') wins over the positional word
    ('under'), because the price is set by the extreme it is drawn at.
    """
    n = note.lower()
    h, l = bool(_REF_HIGH.search(n)), bool(_REF_LOW.search(n))
    if h and not l:
        return "high"
    if l and not h:
        return "low"
    if h and l:
        # whichever extreme word appears first governs the price
        mh, ml = _REF_HIGH.search(n), _REF_LOW.search(n)
        return "high" if mh.start() < ml.start() else "low"
    return None


# ------------------------------------------------------------------ #
# times, anchors, spans, prices
# ------------------------------------------------------------------ #

_TIME = re.compile(r"(\d{1,2}):(\d{2})")
# "from the ~14:45 low", "off the 09:05 tease high", "at the 10:20 top"
_ANCHOR = re.compile(
    r"(?:from|off|at|on|=|sits? on)\s+(?:the\s+)?~?(\d{1,2}):(\d{2})\s*"
    r"(?:tease\s+|spike\s+|test\s+|news\s+|data\s+)?"
    r"(high|low|top|bottom|wick)?")
# spans: "~04:30-07:05", "10:25->11:50", "08:15-08:35"
_SPAN = re.compile(r"~?(\d{1,2}):(\d{2})\s*(?:[-–—]|→|\bto\b)\s*~?"
                   r"(\d{1,2}):(\d{2})")
_PRICE = re.compile(r"1[.,](\d{4})\b|1[.,](\d{3})\b")
# big-figure references: "under the 1.30", "straddling 1.26" -> 1.3000
_ROUND = re.compile(r"\b1[.,](\d{2})\b")


def _m(h, mi):
    return int(h) * 60 + int(mi)


def _hhmm(s):
    m = re.match(r"^\s*(\d{1,2}):(\d{2})", str(s or ""))
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def times(note):
    """Every clock time in the note, in CET minutes, in order."""
    return [_m(h, mi) for h, mi in _TIME.findall(note)]


def anchors(note):
    """[(cet_minute, 'high'|'low'|None)] for explicitly anchored ends.

    'top'/'bottom' are normalised to 'high'/'low'.
    """
    out = []
    for h, mi, kind in _ANCHOR.findall(note.lower()):
        k = {"top": "high", "bottom": "low", "wick": None
             }.get(kind, kind) or None
        out.append((_m(h, mi), k))
    return out


def spans(note):
    """[(m0, m1)] for every explicit time range in the note."""
    return [(_m(a, b), _m(c, d)) for a, b, c, d in _SPAN.findall(note)]


def prices(note):
    """Price literals as floats.  Handles '1.3318', '1,3318' and the
    3-decimal chart-axis form '1,335' -> 1.3350."""
    out = []
    for four, three in _PRICE.findall(note):
        if four:
            out.append(float("1." + four))
        elif three:
            out.append(float("1." + three + "0"))
    return out


def round_refs(note):
    """Big-figure price references as floats: 'the 1.30', 'straddling
    1.26', 'above 1.25' -> 1.3000 / 1.2600 / 1.2500."""
    return [float("1." + g + "00") for g in _ROUND.findall(note)]


# ------------------------------------------------------------------ #
# break / tease vocabulary and flags
# ------------------------------------------------------------------ #

_BROKEN = re.compile(r"\bbroken\b|\bbreaks?\b|\bbreached\b|\bcut\b")
_PIERCED = re.compile(r"\bpierced\b|\bpokes?\b|\bpoked\b|\bdips?\b"
                      r"|\bdipped\b")
_TEASED = re.compile(r"\bteased?\b|\btease\b")
_FLAG = re.compile(r"\b(bull|bear)[- ]?flag\b")


def parse(note, spec_type=None):
    """All constraints the text imposes on one object."""
    n = strip_context(note)
    lab, bounds = slope_cue(n)
    fl = _FLAG.search(n)
    return {
        "slope": lab,
        "slope_bounds": bounds,
        "slope_cues": slope_cues(n),
        "steep": bool(_STEEP.search(n)),
        "gentle": bool(_GENTLE.search(n)),
        "side": side_cue(n),
        "level_ref": level_ref(n),
        "anchors": anchors(n),
        "spans": spans(n),
        "times": times(n),
        "prices": prices(n),
        "round_refs": round_refs(n),
        "broken": bool(_BROKEN.search(n)),
        "straddle": bool(re.search(r"\bstraddl|\baround\b|\bacross\b", n)),
        "pierced": bool(_PIERCED.search(n)),
        "teased": bool(_TEASED.search(n)),
        "flag": fl.group(1) if fl else None,
        "spec_type": spec_type,
    }


def flag_expected_slope(flag):
    """A bear flag is a RISING counter-trend channel inside a downtrend; a
    bull flag FALLS.  Cross-check only — an explicit slope word wins."""
    return {"bear": "up", "bull": "down"}.get(flag)
