"""gates.py — CET calendar gates and STAND_ASIDE primitives (DN_TF §5).

All times are CET minutes-of-day.  The engine never infers the clock
from bars; the caller supplies ``cet_min`` (feed-aware, D3).

Hard windows suppress *initiation*: no object is born or killed on the
window's bars alone, and a break/pierce triggered inside the window is
not counted as a structural break.  A traverse already underway keeps
running (evidence first, window second — DN_TF §6).
"""

# name -> (lo_cet_min, hi_cet_min, hardness)
WINDOWS = {
    "us_data": (855, 885, "hard"),     # 14:30 CET +-15  US data (ABDV)
    "ecb_fix": (845, 865, "hard"),     # 14:15 CET +-10  ECB fix (Krohn)
    "wmr_fix": (1010, 1030, "hard"),   # 16:50-17:10 CET WMR (Evans) — 17:00!
    "option_cut": (950, 970, "soft"),  # 16:00 CET +-10  NY option cut
    "tokyo_fix": (113, 117, "soft"),   # 01:55 CET +-2   Tokyo fix noise
}

ASIA = (0, 480)          # 00:00-08:00 CET — demote, not ban
EU_CORE = (480, 840)     # 08:00-14:00
US_CORE = (840, 1080)    # 14:00-18:00


def windows_at(cet_min):
    """Active window names at this CET minute."""
    return [n for n, (lo, hi, _h) in WINDOWS.items() if lo <= cet_min <= hi]


def hard_block(cet_min):
    """True inside a hard window (births/break-initiation suppressed)."""
    return any(lo <= cet_min <= hi and h == "hard"
               for n, (lo, hi, h) in WINDOWS.items())


def soft_block(cet_min):
    return any(lo <= cet_min <= hi and h == "soft"
               for n, (lo, hi, h) in WINDOWS.items())


def in_asia(cet_min):
    return ASIA[0] <= cet_min < ASIA[1]


def session_prior(cet_min, asia_demote=0.5):
    """Soft session prior for salience (EU/US > Asia)."""
    if in_asia(cet_min):
        return asia_demote
    return 1.0


class TodVol:
    """Rolling same-time-of-day range quantiles (DN_TF §5 abnormal-vol).

    One bucket per CET minute; each bucket keeps the last ``days`` daily
    observations of that minute's bar range.  ``alarm(rng)`` fires when
    the bar range exceeds the q-quantile of its own time bucket —
    scheduled-flow bars are not abnormal merely because 14:30 is jumpy.
    """

    def __init__(self, days=20, q=0.95, mult=3.0):
        self.days = days
        self.q = q
        self.mult = mult
        self.buckets = {}

    def update(self, cet_min, rng):
        q = None
        hist = self.buckets.get(cet_min)
        if hist and len(hist) >= 5:
            srt = sorted(hist)
            j = min(len(srt) - 1, int(self.q * len(srt)))
            q = srt[j]
        if hist is None:
            hist = self.buckets[cet_min] = []
        hist.append(rng)
        if len(hist) > self.days:
            hist.pop(0)
        return q

    def alarm(self, cet_min, rng, abr):
        hist = self.buckets.get(cet_min)
        if hist and len(hist) >= 5:
            srt = sorted(hist)
            j = min(len(srt) - 1, int(self.q * len(srt)))
            if rng > max(srt[j], self.mult * abr):
                return True
        return rng > self.mult * max(abr, 1e-9)
