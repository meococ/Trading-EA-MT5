"""Shared inputs for the LINE-1 audit + snapshots (T-VPA-LINE-1).

Read-only vs the other lanes: this module only READS the burned-case trace,
the DR3 grading key and the M1 parquet cache.  It never writes outside
`PLAN/lines1/`.
"""

import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.abspath(os.path.join(HERE, "..", "lab"))
PKG = os.path.abspath(os.path.join(HERE, "..", ".."))          # .../EA_VolmanPA
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if LAB not in sys.path:
    sys.path.insert(0, LAB)

from vpa_data import load_m5_bars  # noqa: E402

OUT = os.path.join(PKG, "PLAN", "lines1")
SNAP = os.path.join(OUT, "snapshots")
DIAG = os.path.join(PKG, "PLAN", "diag_dr1")
GRADING = os.path.join(PKG, "PLAN", "grading")

#: the 60 burned DR1 cases live in the recall trace; A/B = 16 of them
BURNED_TRACE = os.path.join(DIAG, "RECALL_TRACE.csv")
KEY_HIDDEN = os.path.join(GRADING, "KEY_HIDDEN.csv")

SEED = 20260920
RANDOM_PER_YEAR = 4
BURN_EXCLUDE = 50          # bars around a burned case excluded from sampling

#: display palette (one colour per line type, used by the snapshots)
KIND_COLOR = {
    "level": "#0F766E",       # teal   - ceiling/floor that held (tr. 39-41)
    "box_top": "#7C3AED",     # violet - box boundary (tr. 156)
    "box_bottom": "#7C3AED",
    "trendline": "#2563EB",   # blue   - trendline (tr. 95, 109)
    "flag_upper": "#DB2777",  # pink   - flag boundary (tr. 113)
    "flag_lower": "#DB2777",
    "tri_upper": "#EA580C",   # orange - triangle boundary (tr. 101, 105)
    "tri_lower": "#EA580C",
    "round": "#6B7280",       # grey   - 00/50 (tr. 43)
    "pdh": "#CA8A04",         # gold   - prior-day high (tr. 42/44)
    "pdl": "#CA8A04",
    "sess_hi": "#0891B2",     # cyan   - session high (tr. 362)
    "sess_lo": "#0891B2",
}


def load_design(y0=2016, y1=2021):
    return load_m5_bars("EURUSD", y0, y1)


def burned_ab_cases():
    """The 16 Lead-A/B burned cases with their bar, side and broken boundary."""
    key = {r["case_id"]: r for r in csv.DictReader(open(KEY_HIDDEN, encoding="utf-8"))}
    out = []
    for r in csv.DictReader(open(BURNED_TRACE, encoding="utf-8")):
        if r["lead_grade"].strip().upper() not in ("A", "B"):
            continue
        cid = r["case_id"]
        k = key.get(cid, {})
        out.append({
            "case_id": cid,
            "grade": r["lead_grade"].strip().upper(),
            "bar_idx": int(r["bar_idx"]),
            "side": int(r["side"]),
            "setup": r["setup_v1"],
            "category": r["category"],
            "first_fail": r["first_fail"],
            "dr3_barrier": float(r["dr1_barrier"]) if r["dr1_barrier"] else None,
            "case_barrier": float(k["barrier_level"]) if k.get("barrier_level") else None,
            "touches": int(r["touches"]) if r["touches"] else None,
        })
    out.sort(key=lambda c: c["case_id"])
    return out


def burned_all_bars():
    return [int(r["bar_idx"]) for r in csv.DictReader(open(BURNED_TRACE, encoding="utf-8"))]


def random_design_bars(bars, n_per_year=RANDOM_PER_YEAR, seed=SEED):
    """Stratified random DESIGN in-session bars, 4 per year, excluding +-50
    bars around every burned case (same hygiene as the DR3 fidelity sample)."""
    rng = np.random.default_rng(seed)
    t = bars["t"]
    utc = bars["utc_min"]
    sess = ((utc >= 300) & (utc < 660)) | ((utc >= 690) & (utc < 1050))
    burned = np.array(sorted(burned_all_bars()), dtype=np.int64)
    years = np.array([year_of(x) for x in t])
    out = []
    for y in range(2016, 2022):
        idx = np.where(sess & (years == y))[0]
        # exclude +-BURN_EXCLUDE bars around any burned case
        keep = np.ones(len(idx), dtype=bool)
        for b in burned:
            keep &= np.abs(idx - b) > BURN_EXCLUDE
        idx = idx[keep]
        if len(idx) == 0:
            continue
        pick = rng.choice(len(idx), size=min(n_per_year, len(idx)), replace=False)
        for p in sorted(pick):
            out.append(int(idx[p]))
    return out


def year_of(ts):
    import datetime as _dt
    return _dt.datetime.fromtimestamp(int(ts), tz=_dt.timezone.utc).year


def utc_dt(ts):
    import datetime as _dt
    return _dt.datetime.fromtimestamp(int(ts), tz=_dt.timezone.utc)


def hhmm(bars, t):
    m = int(bars["utc_min"][t])
    return "%02d:%02d" % (m // 60, m % 60)
