"""mock_snapshot.py - provisional perception snapshot for PA_Pro_View.

Writes a perception_csv_v1 file covering EVERY object type of spec
VOLMAN_PERCEPTION_SPEC_v1.md section 2 (schema perception_v1.json),
anchored on real EURUSD M5 bars of one DESIGN week, so the viewer
grammar can be checked end to end on the Owner's chart before the
PERCEPTION lane's engine exists.

This is a MOCK: coordinates are fabricated (plausible, not perceived).
The real snapshots come from research/perception after P-FREEZE.

    python mock_snapshot.py [symbol] [out_csv] [week_start YYYY-MM-DD]

Row schema (see PA_Perception.mqh header):
    id,type,state,role,t_birth,t1,t2,p1,p2,letter,side,why

Times are server epochs == MqlRates.time == pa_data bar `t`; ids are
schema-style strings; state/role use the schema enum values.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MQL5 = os.path.dirname(HERE)
PA_PRO = os.path.dirname(MQL5)
for _p in (os.path.join(PA_PRO, "struct", "zones"),
           os.path.join(PA_PRO, "lib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pa_data  # noqa: E402
import pa_slots  # noqa: E402

COLS = "id,type,state,role,t_birth,t1,t2,p1,p2,letter,side,why"


def _row(oid, typ, state, role, tb, t1, t2, p1, p2, letter, side, why):
    return "%s,%s,%s,%s,%d,%d,%d,%.5f,%.5f,%s,%s,%s" % (
        oid, typ, state, role, int(tb), int(t1), int(t2 or 0),
        float(p1 or 0.0), float(p2 or 0.0), letter, side, why)


def build(symbol, week_start):
    """Fabricate one object of every type on real bars of the week."""
    import datetime as dt
    import numpy as np

    m1 = pa_data.load_m1(symbol, split="DESIGN", warmup_days=0)
    m5 = pa_data.resample(m1, "M5")
    t0 = int(dt.datetime.strptime(week_start, "%Y-%m-%d")
             .replace(tzinfo=dt.timezone.utc).timestamp())
    # server feed ~ UTC+2/+3; take the calendar week as UTC, generous
    t1 = t0 + 7 * 86400
    m = (m5["t"] >= t0 - 86400) & (m5["t"] < t1)
    idx = np.flatnonzero(m)
    if len(idx) < 400:
        raise SystemExit("week too short: %d bars" % len(idx))
    b = {k: np.asarray(m5[k])[idx] for k in ("t", "o", "h", "l", "c")}
    n = len(b["t"])
    pip = float(m5["pip"])
    abr = float(np.median(b["h"] - b["l"]))
    rows = []
    cnt = {}

    def put(typ, *a):
        cnt[typ] = cnt.get(typ, 0) + 1
        oid = "%s_%d" % (typ.lower(), cnt[typ])
        rows.append(_row(oid, typ, *a))

    # --- RANGE_OPEN over the first night's drift, then a BOX ----------
    i0 = 60
    lo = float(b["l"][i0:i0 + 30].min())
    hi = float(b["h"][i0:i0 + 30].max())
    put("RANGE_OPEN", "ACTIVE", "PRIMARY", b["t"][i0],
        b["t"][i0], b["t"][i0 + 30], lo, hi, "", "", "BIRTH_ASIA")
    i1 = i0 + 40
    lo2 = float(b["l"][i1:i1 + 24].min())
    hi2 = float(b["h"][i1:i1 + 24].max())
    put("BOX", "CONFIRMED", "PRIMARY", b["t"][i1],
        b["t"][i1], b["t"][i1 + 60], lo2, hi2, "", "", "BIRTH_PULLBACK")

    # --- CONTEXT_RANGE around a 00/50 gridline -------------------------
    mid = 0.5 * (float(b["h"][i1:i1 + 90].max())
                 + float(b["l"][i1:i1 + 90].min()))
    grid = 50 * pip
    lvl = round(mid / grid) * grid
    put("CONTEXT_RANGE", "ACTIVE", "CONTEXT", b["t"][i0],
        b["t"][i0], b["t"][min(n - 1, i1 + 120)],
        lvl - 0.0015, lvl + 0.0015, "", "", "RN_BATTLE")

    # --- PATTERN_LINE through two rising lows --------------------------
    j0, j1 = i1 + 70, i1 + 90
    p0 = float(b["l"][j0]) - pip
    p1 = float(b["l"][j1]) - pip
    slope = (p1 - p0) / (j1 - j0)
    j2 = min(n - 1, j1 + 25)
    put("PATTERN_LINE", "ACTIVE", "TRIGGER", b["t"][j0],
        b["t"][j0], b["t"][j2], p0, p0 + slope * (j2 - j0), "", "",
        "MW_TRIGGER")

    # --- CONTEXT_LINE: long dotted diagonal over ~5 h ------------------
    k0, k1 = i0, i0 + 60
    q0 = float(b["h"][k0]) + 2 * pip
    q1 = float(b["h"][k1]) + 2 * pip
    put("CONTEXT_LINE", "ACTIVE", "CONTEXT", b["t"][k0],
        b["t"][k0], b["t"][k1], q0, q1, "", "", "SESSION_GUIDE")

    # --- LEVEL_CARRIED: prior swing, projected right -------------------
    lv = float(b["h"][i0 - 20:i0].max())
    put("LEVEL_CARRIED", "ACTIVE", "CARRIED", b["t"][i0],
        b["t"][i0], 0, lv, 0.0, "", "", "ROLE_REVERSAL")
    lv2 = float(b["l"][i1 + 60:i1 + 70].min())
    put("LEVEL_CARRIED", "CONSUMED", "CARRIED", b["t"][i1 + 60],
        b["t"][i1 + 60], 0, lv2, 0.0, "", "", "CEILING_TEST")

    # --- MINI_LEVEL: 4-bar floor --------------------------------------
    m0 = i1 + 100
    ml = float(b["l"][m0:m0 + 4].min())
    put("MINI_LEVEL", "ACTIVE", "TRIGGER", b["t"][m0],
        b["t"][m0], b["t"][m0 + 4], ml, 0.0, "", "", "ZIGZAG_FLOOR")

    # --- SQUEEZE: first run of >=3 bars each <= 0.8*ABR ---------------
    sq = None
    for s in range(i1, n - 6):
        if np.all((b["h"][s:s + 3] - b["l"][s:s + 3]) <= 0.8 * abr):
            sq = s
            break
    if sq is None:
        sq = i1 + 110
    put("SQUEEZE", "ACTIVE", "TRIGGER", b["t"][sq],
        b["t"][sq], b["t"][sq + 3],
        float(b["l"][sq:sq + 3].min()) - 2 * pip,
        float(b["h"][sq:sq + 3].max()) + 2 * pip, "", "", "WALLS_NARROW")

    # --- LABEL_TF: T at a poke above the box, F at a deeper false poke
    poke = i1 + 30
    put("LABEL_TF", "ACTIVE", "", b["t"][poke],
        b["t"][poke], 0, float(b["h"][poke]) + 2 * pip, 0.0,
        "T", "above", "POKE_HI")
    poke2 = i1 + 45
    put("LABEL_TF", "ACTIVE", "", b["t"][poke2],
        b["t"][poke2], 0, float(b["l"][poke2]) - 2 * pip, 0.0,
        "F", "below", "POKE_LO_FAILED")

    # --- BRACKET: "M" over a double-top span ---------------------------
    b0 = i1 + 120
    put("BRACKET", "ACTIVE", "CONTEXT", b["t"][b0],
        b["t"][b0], b["t"][b0 + 16],
        float(b["h"][b0:b0 + 16].max()) + 3 * pip, 0.0, "M", "above",
        "M_SPAN")
    b1 = i1 + 140
    put("BRACKET", "ACTIVE", "CONTEXT", b["t"][b1],
        b["t"][b1], b["t"][b1 + 12],
        float(b["l"][b1:b1 + 12].min()) - 3 * pip, 0.0, "Ww", "below",
        "WW_SPAN")

    # --- FALSE_EXT: tick at an isolated spike wick ---------------------
    fe = i1 + 55
    put("FALSE_EXT", "ACTIVE", "", b["t"][fe],
        b["t"][fe], 0, float(b["h"][fe]) + pip, 0.0, "", "above",
        "SPIKE_WICK")

    # --- STAND_ASIDE over a chop segment -------------------------------
    sa = i1 + 160
    put("STAND_ASIDE", "ACTIVE", "", b["t"][sa],
        b["t"][sa], b["t"][sa + 20], float(b["c"][sa]), 0.0, "", "",
        "CHOP")

    return rows


def main():
    symbol = sys.argv[1] if len(sys.argv) > 1 else "EURUSD"
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        HERE, "out", "perception_%s.csv" % symbol)
    week = sys.argv[3] if len(sys.argv) > 3 else "2019-03-04"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with pa_slots.slot("pa_pro mock_snapshot %s" % symbol):
        rows = build(symbol, week)
    with open(out, "w", encoding="ascii", newline="") as f:
        f.write(COLS + "\n")
        for r in rows:
            f.write(r + "\n")
    print("wrote %s (%d objects)" % (out, len(rows)))


if __name__ == "__main__":
    main()
