"""kernel.py — candidate + geometry kernel (ARCH MIGRATION_PLAN A1).

Pure move from salience.py: the budget-class maps, the Candidate
record, band/footprint geometry helpers, and the signature helpers.
No logic change; salience.py imports and re-exports these names so
every call site stays unchanged (R67 §67.3, step A1).
"""

SIGNAL = {"BOX", "PATTERN_LINE", "LEVEL_CARRIED", "MINI_LEVEL",
          "BRACKET"}
CONTEXT = {"RANGE_OPEN", "CONTEXT_RANGE", "CONTEXT_LINE"}
# SQUEEZE is annotation ink (a marked compression between walls), not
# a barrier — it annotates the story of the walls, like LABEL_TF.
ANNOT = {"LABEL_TF", "BAR_MARKER", "SQUEEZE"}

FAMILY = {
    "BOX": "box", "RANGE_OPEN": "box", "CONTEXT_RANGE": "box",
    "PATTERN_LINE": "line", "CONTEXT_LINE": "line",
    "LEVEL_CARRIED": "level", "MINI_LEVEL": "level",
    "BRACKET": "bracket", "SQUEEZE": "squeeze",
    "LABEL_TF": "annot", "BAR_MARKER": "annot",
}


def budget_class(otype):
    if otype in SIGNAL:
        return "signal"
    if otype in CONTEXT:
        return "context"
    return "annot"


class Candidate:
    """A structure under evaluation — geometry frozen at proposal."""

    __slots__ = ("kind", "route", "geom", "born_i", "t0", "t1",
                 "feats", "meta", "score", "comps", "expires", "side",
                 "fam", "_logged")

    def __init__(self, kind, route, geom, born_i, feats=None,
                 meta=None, ttl=24):
        self.kind = kind
        self.route = route
        self.geom = dict(geom)          # pips / bar idx, frozen
        self.born_i = born_i
        self.t0 = geom.get("t0", born_i)
        self.t1 = geom.get("t1", born_i)
        self.feats = dict(feats or {})  # generation-time features
        self.meta = dict(meta or {})    # route payload for birth
        self.score = None
        self.comps = {}
        self.expires = born_i + ttl
        self.side = geom.get("side")
        # A5 (MIGRATION_PLAN): per-family tag — shadow data only,
        # not read by any logic yet.  Pre-A5 pickled Candidates carry
        # no `fam` slot — readers must use getattr(c, "fam", None)
        # (ARCH_REVIEW A5 fix note).
        self.fam = FAMILY.get(kind)
        self._logged = set()     # outcomes already written to cand_log

    def band(self, i):
        """(lo, hi) price band of the candidate at bar i."""
        g = self.geom
        if "bottom" in g and "top" in g:
            return g["bottom"], g["top"]
        for k in ("price", "level", "mid"):
            if g.get(k) is not None:
                return g[k], g[k]
        if g.get("p0") is not None:
            p = g["p0"] + g.get("slope", 0.0) * (i - g["t0"])
            return p, p
        return None, None


def footprint_overlap(a_band, a_span, b_band, b_span, iou_thresh):
    """Type-family-agnostic overlap: price-band overlap AND span IoU."""
    if a_band is None or b_band is None:
        return False
    if a_band[1] < b_band[0] or b_band[1] < a_band[0]:
        return False
    a0, a1 = a_span
    b0, b1 = b_span
    inter = max(0, min(a1, b1) - max(a0, b0))
    union = max(a1, b1) - min(a0, b0)
    return union > 0 and inter / union >= iou_thresh


def band_of(kind, g, i):
    """Object band at bar i — the body of the former Salience._band_of;
    pure function (kind unused, kept for the documented signature)."""
    if "bottom" in g and "top" in g:
        return g["bottom"], g["top"]
    for k in ("price", "level", "mid"):
        if g.get(k) is not None:
            return g[k], g[k]
    if g.get("p0") is not None:
        p = g["p0"] + g.get("slope", 0.0) * (i - g["t0"])
        return p, p
    return None, None


def sig(e, c):
    """Candidate signature — the body of the former Salience._sig;
    takes the engine for _tol()."""
    ptol = e._tol()
    out = [c.kind, c.route]
    for k in ("top", "bottom", "price", "p0", "level"):
        v = c.geom.get(k)
        out.append(None if v is None else round(float(v) / ptol))
    v = c.geom.get("slope")
    out.append(None if v is None else round(float(v) / 0.05))
    return tuple(out)


def sig_obj(e, o):
    """Same signature space for a live/dead object — lets a killed
    structure keep its evaluation window (no instant re-birth)."""
    ptol = e._tol()
    g = o.geometry
    out = [o.type, o.why]
    for k in ("top", "bottom", "price", "p0", "level"):
        v = g.get(k)
        out.append(None if v is None else round(float(v) / ptol))
    v = g.get("slope")
    out.append(None if v is None else round(float(v) / 0.05))
    return tuple(out)
