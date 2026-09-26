"""DC state-machine pivot detector + prominence pruning (DN_SWING).

One directional-change detector at theta1 (micro); the structural set
is derived by a prominence floor, so it is a strict subset — the two
scales can never disagree (RT4 §6/§9.1).

Causal by construction: a pivot confirms only when price has retraced
theta beyond the leg extreme; `t_conf` is the confirmation bar.
All state uses bars <= t only.

Prominence-so-far (RT4 §9.1) is monotone non-decreasing until a
dominating same-side pivot arrives; the book updates it online via the
open set.  `prom` = latest known prominence; `prom_birth` = the value
at confirmation — the micro floor kills on `prom_birth` (DN_SWING §5:
"kill any theta1-pivot with prom < pmin at confirm time").
"""
from dataclasses import dataclass, field


@dataclass
class Pivot:
    t_ext: int          # bar index of the extreme
    t_conf: int         # bar index of confirmation
    price: float        # extreme price (pips)
    dir: int            # +1 = swing high, -1 = swing low
    theta: float        # retrace threshold that confirmed it
    prom: float = 0.0   # prominence-so-far (pips), live-updated
    prom_birth: float = 0.0  # prominence at confirm (frozen kill value)
    leg: float = 0.0    # leg amplitude that produced it (pips)
    lone_spike: bool = False  # extreme came from a spike bar

    @property
    def confirm_lag(self):
        return self.t_conf - self.t_ext


class DCStream:
    """Directional-change state machine at fixed threshold theta.

    Emits Pivot objects on confirm. Wick-tracked extremes; a pivot
    confirms when the bar's opposite wick retraces >= theta from the
    extreme (wick-retrace mode per DN_SWING default).
    """

    def __init__(self, theta_fn, spike_fn=None):
        # theta_fn(i) -> retrace threshold in pips at bar i (ABR-scaled)
        # spike_fn(i) -> True if bar i is a lone-spike bar (range >> ABR)
        self.theta_fn = theta_fn
        self.spike_fn = spike_fn or (lambda i: False)
        self.dir = 0                 # 0 unseeded, +1 up-leg, -1 down-leg
        self.ext_price = None        # running leg extreme
        self.ext_idx = -1
        self.leg_origin = None       # price of the last confirmed pivot
        self.pivots = []

    def update(self, i, hi, lo):
        out = []
        if self.ext_price is None:
            # seed on the first bar
            self.dir = 1
            self.ext_price = hi
            self.ext_idx = i
            self.leg_origin = lo
            return out
        theta = self.theta_fn(i)
        # an extreme made on THIS bar cannot also confirm this bar —
        # a wide-range bar both extends and retraces (intra-bar order
        # is unknown), so the retrace must come from a later bar.
        if self.dir == 1:
            if hi > self.ext_price:
                self.ext_price = hi
                self.ext_idx = i
            if self.ext_idx < i and lo <= self.ext_price - theta:
                out.append(self._emit(i, self.ext_idx, self.ext_price, +1))
                self.dir = -1
                self.ext_price = lo
                self.ext_idx = i
        else:
            if lo < self.ext_price:
                self.ext_price = lo
                self.ext_idx = i
            if self.ext_idx < i and hi >= self.ext_price + theta:
                out.append(self._emit(i, self.ext_idx, self.ext_price, -1))
                self.dir = 1
                self.ext_price = hi
                self.ext_idx = i
        return out

    def _emit(self, t_conf, t_ext, price, side):
        leg = abs(price - self.leg_origin) if self.leg_origin is not None else 0.0
        p = Pivot(t_ext=t_ext, t_conf=t_conf, price=price, dir=side,
                  theta=self.theta_fn(t_conf), leg=leg,
                  lone_spike=self.spike_fn(t_ext))
        self.leg_origin = price
        self.pivots.append(p)
        return p


class SwingBook:
    """Confirmed-pivot sequence with prominence-so-far.

    prominence(high pivot) = its height above the lowest opposite
    extreme between it and the most recent *higher* high (or stream
    start) — the merge-tree saddle level.  Computed by backward scan at
    confirm (all emitted pivots count as saddles, pruned or not), then
    updated online: each new opposite extreme deepens the saddle of
    every still-open opposite-side pivot.  A pivot leaves the open set
    when a dominating same-side pivot arrives — its prom is then final.
    """

    def __init__(self, pmin, pstruct, abr_fn=None):
        self.pmin = pmin          # micro floor: below -> dead on arrival
        self.pstruct = pstruct    # structural floor (~theta2 scale)
        # when abr_fn is given, pmin/pstruct are ABR *multiples* and the
        # per-pivot floor is frozen at confirmation in pips (causal);
        # when None they are literal pips (unit-test mode).
        self._abr_fn = abr_fn
        self.seq = []             # all emitted pivots (saddle evidence)
        self._open = {1: [], -1: []}   # undominated pivots by dir

    def _floors(self, p):
        if self._abr_fn is None:
            return self.pmin, self.pstruct
        a = self._abr_fn(p.t_conf)
        return self.pmin * a, self.pstruct * a

    def floor_min(self, p):
        return self._floors(p)[0]

    def floor_struct(self, p):
        return self._floors(p)[1]

    def is_structural(self, p):
        return p.prom >= self.floor_struct(p)

    def add(self, p):
        p.prom = self._prominence(p)
        p.prom_birth = p.prom
        self.seq.append(p)
        # a deeper opposite extreme widens the basin of every
        # still-open pivot on the other side
        for q in self._open[-p.dir]:
            q.prom = max(q.prom, (q.price - p.price) * q.dir)
        # domination on p's own side: less-extreme open peers close
        od = self._open[p.dir]
        while od and (p.price - od[-1].price) * p.dir > 0:
            od.pop()
        od.append(p)
        return p

    def _prominence(self, p):
        # walk back through emitted pivots to the most extreme
        # opposite price seen before a dominating same-side pivot
        opp = None
        for q in reversed(self.seq):
            if q.dir == p.dir:
                if (q.price - p.price) * p.dir > 0:
                    break  # dominating same-side pivot found
            elif opp is None or (q.price - opp) * p.dir < 0:
                opp = q.price
        if opp is None:
            return p.leg  # first pivot: prominence = whole leg
        return abs(p.price - opp)

    def alive(self):
        """Pivots that survived the micro floor AT CONFIRM TIME."""
        return [p for p in self.seq if p.prom_birth >= self.floor_min(p)]

    def structural(self):
        """Pivots surviving the structural floor — strict subset of
        the alive set.  Uses live prominence: a pivot can graduate when
        a deeper opposite extreme confirms (causal: consumers see the
        value current at their bar)."""
        return [p for p in self.alive() if self.is_structural(p)]

    def superseded(self, p):
        """DN_SWING aging: superseded for anchor purposes once a
        same-direction pivot with equal-or-higher prominence confirms
        after it."""
        return any(q.dir == p.dir and q.t_conf > p.t_conf
                   and q.prom >= p.prom for q in self.seq)

    def recent(self, i, max_age=None):
        """Alive pivots confirmed by bar i (optionally within max_age)."""
        out = [p for p in self.alive() if p.t_conf <= i]
        if max_age is not None:
            out = [p for p in out if i - p.t_conf <= max_age]
        return out

    def update_running(self, leg_dir, ext_price):
        """Deepen open opposite-side basins with the live leg extreme.

        The running extreme is observed (causal) even before its pivot
        confirms: a high pivot's saddle is the lowest low *seen so far*
        in its basin, which includes the in-progress leg.
        """
        if leg_dir == 0 or ext_price is None:
            return
        for q in self._open[-leg_dir]:
            q.prom = max(q.prom, (q.price - ext_price) * q.dir)
