"""objects.py — Obj record + ObjectStore (ARCH MIGRATION_PLAN A2).

Pure move from engine.py: the Obj record and the object-store
mechanics (_mk/_birth/active + the ACTIVE index).  The engine holds
`self.store` and delegates; `e.objects`, `e._act`, `e.active`,
`e._mk`, `e._birth` keep working via shims so no call site moves.
Obj._eng still points at the engine (close-veto logging, _cand).
"""


class Obj:
    """One drawn (or stored-fact) object — schema per
    schema/perception_v1.json."""

    def __init__(self, otype, style, t_birth, geometry, why, role="",
                 oid=None):
        self.id = oid or "%s?" % otype[:3]
        self.type = otype
        self.style = style
        self.t_birth = t_birth          # bar index of first ink
        self.t_left = t_birth           # drawn span start
        self.t_right = None             # bar idx when closed
        self.geometry = geometry        # dict, pips / bar indices
        self._state = "ACTIVE"
        self.touches = []
        self.events = []                # (bar_idx, code, detail)
        self.role = role
        self.why = why
        self.priority = 5
        self.score = None               # live salience score (output only)
        self.facts = {}                 # R78 TT: observability facts
                                        # (trade_tags) - never read by
                                        # engine, never in canonical()

    # `state` is a property so the engine's _act index tracks every
    # transition, including direct "o.state = ..." writes and revivals.
    # Bare Obj instances (no _eng back-ref) behave exactly as before.
    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, v):
        self._state = v
        eng = getattr(self, "_eng", None)
        if eng is not None:
            if v == "ACTIVE":
                eng._act[self._oi] = self
            else:
                eng._act.pop(self._oi, None)

    def __setstate__(self, d):
        # legacy pickles (pre-property) carry "state" in __dict__
        self.__dict__.update(d)
        if "_state" not in self.__dict__:
            self._state = self.__dict__.pop("state", "ACTIVE")
        if "facts" not in self.__dict__:
            self.facts = {}

    def close(self, i, why):
        if self.geometry.get("meta_uip_persist"):
            # R62 s.62.4 UIP-rd persistent object: the family's ONE
            # object is exempt from every kill path (eviction,
            # supersede, retire, break-close) so the rd-mutation
            # stream can keep rewriting its edges - v0's governing
            # box economy.  The veto is logged for audit.
            self.events.append((i, "close_veto", why))
            return
        if self.geometry.get("meta_v0_port"):
            # R63 s.63.4 option-B mirror: a v0 box-family object's
            # lifecycle is governed by the v0 sub-engine, not v1 -
            # every v1 kill path is vetoed; _v0_sync applies v0's own
            # state transitions each bar.  (Mirror events are
            # overwritten by the sync, so the veto goes to cand_log.)
            if getattr(self, "_eng", None) is not None:
                self._eng._cand(self.type, i, "v0_port",
                                "close_veto:" + str(why))
            return
        self.t_right = i
        self.state = "CLOSED"
        self.events.append((i, "close", why))

    def event(self, i, code, detail=""):
        self.events.append((i, code, detail))

    def to_dict(self):
        return {"id": self.id, "type": self.type, "style": self.style,
                "t_birth": self.t_birth, "t_left": self.t_left,
                "t_right": self.t_right, "geometry": self.geometry,
                "state": self.state, "touches": self.touches,
                "events": self.events, "role": self.role,
                "why": self.why, "priority": self.priority,
                "score": self.score, "facts": self.facts}


class ObjectStore:
    """The engine's object registry: every drawn object (birth order,
    ids = append order) plus the ACTIVE index that Obj.state keeps
    in sync.  `eng` is the owning engine — birth needs its boxes book
    (live_tracker) and its birth-index trackers."""

    def __init__(self, eng):
        self.eng = eng
        self.all = []                   # all objects ever drawn
        self._act = {}                  # ACTIVE objects keyed by all idx

    def active(self, otype=None):
        # _act keys are objects-list indices -> sorting them reproduces
        # objects-order exactly (incl. revivals), keeping tie-breaks
        # identical to the old full-list scan.
        if otype is None:
            return [self._act[k] for k in sorted(self._act)]
        return [o for k in sorted(self._act)
                for o in [self._act[k]] if o.type == otype]

    def mk(self, otype, style, t_birth, geometry, why, role=""):
        o = Obj(otype, style, t_birth, geometry, why, role,
                oid="%s%04d" % (otype[:3], len(self.all)))
        o._oi = len(self.all)
        o._eng = self.eng
        self.all.append(o)
        self._act[o._oi] = o
        self.eng._prev_birth_i, self.eng._last_birth_i = \
            self.eng._last_birth_i, t_birth
        return o

    def birth(self, cand, i, score):
        """Candidate wins a slot -> object ink.  Geometry is frozen."""
        eng = self.eng
        g = dict(cand.geom)
        g["sali"] = {"feats": dict(cand.feats), "score": score,
                     "consumed": 0}
        style = {"BOX": "solid", "RANGE_OPEN": "open_lines",
                 "CONTEXT_RANGE": "dotted", "PATTERN_LINE": "solid",
                 "CONTEXT_LINE": "dotted", "LEVEL_CARRIED": "long_dashed",
                 "MINI_LEVEL": "dashed", "BRACKET": "bracket",
                 "SQUEEZE": "dashed_ellipse", "LABEL_TF": "letter",
                 "BAR_MARKER": "tick"}.get(cand.kind, "solid")
        o = self.mk(cand.kind, style, i, g, why=cand.route,
                    role=str(cand.meta.get("parent", "")))
        o.t_left = cand.t0
        o.score = score
        o.priority = {"BOX": 1, "PATTERN_LINE": 2, "SQUEEZE": 3,
                      "LEVEL_CARRIED": 3, "MINI_LEVEL": 3,
                      "BRACKET": 4, "RANGE_OPEN": 2,
                      "CONTEXT_RANGE": 2, "CONTEXT_LINE": 2,
                      "LABEL_TF": 4, "BAR_MARKER": 4}.get(cand.kind, 5)
        for k, v in cand.meta.items():
            if k == "parent":
                continue
            g.setdefault("meta_" + k, v)
        if cand.meta.get("live_tracker") and eng.boxes._asia:
            eng.boxes._asia["ro"] = o
        if cand.kind == "BOX" and cand.meta.get("thin"):
            o.event(i, "thin_range", "false-break prone (9.40a)")
        o.event(i, "born", "%s score=%.2f" % (cand.route, score))
        return o
