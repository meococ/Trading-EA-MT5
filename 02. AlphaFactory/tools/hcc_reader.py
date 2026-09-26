# hcc_reader — MT5 .hcc M1 bar reader with integrity flags.
#
# WARNING (2026-09-18, HYP-RGR-001 kill): the 60-byte phase-scan fabricates
# "bars" inside tick-burst regions (roll 00:00-00:10 server, news minutes).
# The .hcc stores bursts in a packed non-bar layout (marker records with
# absurd tv/range); the tester reconstructs real ticks from them, so real
# fills routinely land OUTSIDE the fabricated bar range. Suspect regions
# are flagged, never silently trusted — probe prices inside them are void.
import datetime as dt
from pathlib import Path

import numpy as np

HISTORY_DIR = Path(r"D:\Meta 5\Trading-EA-MT5\02. AlphaFactory\runtime\mt5-portable-mqdemo\bases\MetaQuotes-Demo\history")


def _scan(path):
    """Yield (phase, ctm, o, h, l, c, tv, sp) for every sanity-passing record."""
    d = np.fromfile(path, dtype=np.uint8)
    for phase in range(60):
        m = d[phase:]
        m = m[:len(m) - len(m) % 60]
        if len(m) < 60:
            continue
        rec = m.reshape(-1, 60)
        ctm = rec[:, 56:60].copy().view("<i4").ravel()
        ok_t = (ctm > 946684800) & (ctm < 2000000000)  # 2000-01-01 .. 2033
        if not ok_t.any():
            continue
        ohlc = rec[:, 4:36].copy().view("<f8")
        o, h, l, c = ohlc[:, 0], ohlc[:, 1], ohlc[:, 2], ohlc[:, 3]
        ok = (ok_t & np.isfinite(ohlc).all(axis=1)
              # absolute magnitude sanity: relative checks pass on uniformly
              # huge garbage records (o=3.5e121 satisfies h-l < 0.5*o).
              & (o > 0.01) & (o < 1e5) & (l > 0.01) & (h < 1e5)
              & (h >= l) & (o <= h) & (o >= l) & (c <= h) & (c >= l)
              & (h - l < 0.5 * o))
        idx = np.nonzero(ok)[0]
        tv = rec[idx, 36:44].copy().view("<i8").ravel()
        sp = rec[idx, 44:52].copy().view("<i8").ravel()
        for j, i in enumerate(idx):
            yield (phase, int(ctm[i]), float(o[i]), float(h[i]), float(l[i]),
                   float(c[i]), int(tv[j]), int(sp[j]))


def read_hcc_year_flagged(path):
    """Return (bars, suspect, report).

    bars    : {ctm: (o,h,l,c,tv,sp)} — best stream, ctm-deduped.
    suspect : set(ctm) — bars inside burst-structured regions; prices here
              are fabricated by the scan and MUST NOT be treated as tradable.
    report  : integrity stats dict.
    """
    raw = list(_scan(path))
    bars, rec_phase = {}, {}
    for phase, ctm, o, h, l, c, tv, sp in raw:
        if ctm not in bars:               # first-valid-wins per ctm
            bars[ctm] = (o, h, l, c, tv, sp)
            rec_phase[ctm] = phase
    ts = sorted(bars)
    # --- plausibility validation: garbage records mimic valid RELATIVE
    # --- structure at any magnitude (h>=l holds, h-l < 0.5*o holds when all
    # --- fields are uniformly huge/tiny). Magnitude bounds cannot separate
    # --- them; a rolling-median band can: real prices stay within ~3x of
    # --- the local median, corrupt records deviate wildly.
    if ts:
        import pandas as pd
        o_arr = np.array([bars[t][0] for t in ts])
        med = pd.Series(o_arr).rolling(2001, center=True,
                                       min_periods=200).median().to_numpy()
        bad = (o_arr > 3.0 * med) | (o_arr < med / 3.0)
        bad &= np.isfinite(med)
        for t in np.asarray(ts)[bad]:
            del bars[t]
        ts = [t for t in ts if t in bars]
    suspect = set()
    # --- burst markers: absurd tickvol or absurd range = packed non-bar
    # --- record type (the roll-burst marker, tv~50k vs median ~30).
    # --- sp==0 is a benign data characteristic in some years, NOT corruption.
    med_tv = np.median([bars[t][4] for t in ts]) if ts else 0
    for i, t in enumerate(ts):
        o, h, l, c, tv, sp = bars[t]
        rng = h - l
        if tv > max(2000, 50 * med_tv) or rng > 0.02 * o:
            suspect.add(t)
            # contaminate the following burst window (packed burst region
            # typically spans ~10 min after the marker)
            j = i + 1
            while j < len(ts) and ts[j] - t <= 900:
                suspect.add(ts[j])
                j += 1
    # --- single-bar jumps >0.8%: mostly real flash moves (SNB, covid) but
    # --- unverifiable as tradable prices on this plane -> suspect, not bars.
    c_arr = np.array([bars[t][3] for t in ts])
    jumps = np.abs(np.diff(c_arr)) > 0.008 * c_arr[:-1]
    for i in np.flatnonzero(jumps):
        suspect.add(ts[i])
        suspect.add(ts[i + 1])
    # --- ctm collisions across phases (same ctm, different prices) = fabricated
    seen = {}
    for phase, ctm, o, h, l, c, tv, sp in raw:
        if ctm in seen and abs(seen[ctm] - o) > 1e-9:
            suspect.add(ctm)
        seen.setdefault(ctm, o)
    report = {
        "bars": len(bars), "suspect": len(suspect),
        "suspect_share": len(suspect) / max(1, len(bars)),
        "raw_candidates": len(raw),
        "median_tickvol": float(med_tv),
    }
    return bars, suspect, report


def read_hcc_year(path):
    """Legacy API: {ctm: (o,h,l,c,tv,sp)} — includes suspect regions.
    Callers that need tradable-price truth must use read_hcc_year_flagged
    and drop `suspect` ctms."""
    bars, _, _ = read_hcc_year_flagged(path)
    return bars


def load_symbol(sym, y0=2010, y1=2026, flagged=False):
    """Concatenate M1 records across year files.
    flagged=True -> returns (bars, suspect_set, per_year_reports)."""
    base = HISTORY_DIR / sym
    all_bars, all_sus, reps = {}, set(), []
    for y in range(y0, y1 + 1):
        f = base / f"{y}.hcc"
        if not f.exists():
            continue
        try:
            b, s, r = read_hcc_year_flagged(f)
            r["year"] = y
            reps.append(r)
            all_bars.update(b)
            all_sus |= s
        except PermissionError:
            print(f"  {sym} {y}: locked, skipped")
    return (all_bars, all_sus, reps) if flagged else all_bars


if __name__ == "__main__":
    for sym in ["AUDUSD", "USDCHF"]:
        bars, sus, reps = load_symbol(sym, 2010, 2026, flagged=True)
        ts = sorted(bars)
        print(sym, len(bars), "bars",
              dt.datetime.utcfromtimestamp(ts[0]) if ts else "-",
              "->", dt.datetime.utcfromtimestamp(ts[-1]) if ts else "-",
              "| suspect:", len(sus), f"({len(sus)/max(1,len(bars)):.1%})")
        for r in reps:
            print(f"   {r['year']}: bars={r['bars']} suspect={r['suspect']} ({r['suspect_share']:.1%}) med_tv={r['median_tickvol']:.0f}")
